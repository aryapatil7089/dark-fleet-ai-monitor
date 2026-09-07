import os
import asyncio
import json
import math
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import websockets

# Load environment variables
load_dotenv()
AISSTREAM_API_KEY = os.getenv("AISSTREAM_API_KEY")

if not AISSTREAM_API_KEY:
    raise ValueError("Missing AISSTREAM_API_KEY. Please check your .env file.")

app = FastAPI()

print("Loading models...")
scaler = joblib.load('scaler.pkl')
kmeans = joblib.load('kmeans.pkl')
dbscan_core_points = np.load('dbscan_core_points.npy')
print("Models loaded successfully!")

# --- STATE MANAGEMENT ---
active_ships = {}      
ship_history = {}      
html_clients = set()
current_ais_task = None
current_bbox = [[[1.15, 103.6], [1.35, 104.0]]] # Default to Singapore

def haversine(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2.0)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2.0)**2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c

def process_and_score(ping):
    mmsi = ping['mmsi']
    time_str = ping['time'][:19]
    current_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    lat, lon = ping['lat'], ping['lon']

    if mmsi not in active_ships:
        active_ships[mmsi] = {'time': current_time, 'lat': lat, 'lon': lon}
        return None 

    prev = active_ships[mmsi]
    time_gap_minutes = (current_time - prev['time']).total_seconds() / 60.0
    
    if time_gap_minutes <= 0:
        return None 
        
    distance_gap_km = haversine(prev['lat'], prev['lon'], lat, lon)
    implied_speed_knots = (distance_gap_km / (time_gap_minutes / 60.0)) / 1.852

    features = pd.DataFrame([[time_gap_minutes, distance_gap_km, implied_speed_knots]], 
                            columns=['Time_Gap_Minutes', 'Distance_Gap_km', 'Implied_Speed_knots'])
    scaled_features = scaler.transform(features)

    cluster = int(kmeans.predict(scaled_features)[0])
    distances = np.linalg.norm(dbscan_core_points - scaled_features, axis=1)
    min_distance = float(np.min(distances))
    is_anomaly = bool(min_distance > 0.3) 

    active_ships[mmsi] = {'time': current_time, 'lat': lat, 'lon': lon}

    result = {
        "mmsi": mmsi,
        "ship_name": ping.get('ship_name', 'Unknown Vessel'),
        "time": time_str,
        "lat": lat,
        "lon": lon,
        "time_gap": round(time_gap_minutes, 2),
        "distance_gap": round(distance_gap_km, 2),
        "speed": round(implied_speed_knots, 2),
        "kmeans_cluster": cluster,
        "dbscan_dist": round(min_distance, 3),
        "is_anomaly": is_anomaly
    }
    
    # Store in memory bank (Max 50)
    if mmsi not in ship_history:
        ship_history[mmsi] = []
    ship_history[mmsi].append(result)
    if len(ship_history[mmsi]) > 50:
        ship_history[mmsi].pop(0)
        
    return result

class ManualPing(BaseModel):
    speed: float
    time_gap: float
    distance_gap: float

@app.post("/api/manual_score")
async def manual_score(ping: ManualPing):
    features = pd.DataFrame([[ping.time_gap, ping.distance_gap, ping.speed]], 
                            columns=['Time_Gap_Minutes', 'Distance_Gap_km', 'Implied_Speed_knots'])
    scaled_features = scaler.transform(features)
    distances = np.linalg.norm(dbscan_core_points - scaled_features, axis=1)
    min_distance = float(np.min(distances))
    is_anomaly = bool(min_distance > 0.3) 
    
    reasons = []
    if is_anomaly:
        if ping.speed > 30: reasons.append(f"Unrealistic Speed: {ping.speed} kn")
        if ping.time_gap > 30: reasons.append(f"Transponder Blackout: {ping.time_gap} min")
        if min_distance > 0.3: reasons.append(f"DBSCAN Flag: Density distance ({round(min_distance, 3)}) > eps:0.3")

    return {"is_anomaly": is_anomaly, "dbscan_dist": round(min_distance, 3), "reasons": reasons}

# --- DYNAMIC AISSTREAM CONNECTION (24/7 AUTO-RECONNECT) ---
async def ais_loop():
    """Runs the websocket feed with an auto-reconnect loop for 24/7 stability."""
    while True:
        try:
            async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
                subscribe_message = {
                    "APIKey": AISSTREAM_API_KEY,
                    "BoundingBoxes": current_bbox,
                    "FilterMessageTypes": ["PositionReport"]
                }
                await websocket.send(json.dumps(subscribe_message))
                print(f"Connected! Listening to Bounding Box: {current_bbox}")

                async for message_json in websocket:
                    message = json.loads(message_json)
                    if message["MessageType"] == "PositionReport":
                        mmsi = message["MetaData"]["MMSI"]
                        ping = {
                            "mmsi": mmsi,
                            "ship_name": message["MetaData"].get("ShipName", "Unknown Vessel").strip(),
                            "time": message["MetaData"]["time_utc"],
                            "lat": message["Message"]["PositionReport"]["Latitude"],
                            "lon": message["Message"]["PositionReport"]["Longitude"],
                        }
                        result = process_and_score(ping)
                        if result and html_clients:
                            for client in html_clients:
                                try:
                                    await client.send_json(result)
                                except:
                                    pass
        except asyncio.CancelledError:
            print("AIS feed task cancelled to switch regions.")
            break 
        except Exception as e:
            print(f"Connection dropped. Reconnecting in 5 seconds... (Error: {e})")
            await asyncio.sleep(5)

async def restart_ais(new_bbox):
    """Kills the current stream and starts a new one"""
    global current_ais_task, current_bbox, active_ships, ship_history
    
    # Wipe memory clean for the new region to prevent RAM crash
    active_ships.clear()
    ship_history.clear()
    current_bbox = new_bbox
    
    if current_ais_task:
        current_ais_task.cancel()
        
    current_ais_task = asyncio.create_task(ais_loop())

@app.on_event("startup")
async def startup_event():
    global current_ais_task
    current_ais_task = asyncio.create_task(ais_loop())

@app.websocket("/ws/frontend")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    html_clients.add(websocket)
    
    # Memory Dump: Send saved history to newly refreshed browsers
    for mmsi, history in ship_history.items():
        for saved_ping in history:
            await websocket.send_json(saved_ping)

    try:
        while True:
            data = await websocket.receive_text()
            command = json.loads(data)
            if command.get("action") == "change_region":
                await restart_ais(command.get("bbox"))
    except WebSocketDisconnect:
        html_clients.remove(websocket)

@app.get("/")
async def get():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())