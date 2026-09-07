# 🌊 Dark Fleet AI Monitor: Real-Time Maritime Anomaly Detection

**Author:** Arya Patil  
**Institution:** Imarticus Learning (Postgraduate Program in Data Science & Analytics)  

---

### 🚀 Live Web Application
**[👉 CLICK HERE TO ACCESS THE LIVE TACTICAL PORTAL](https://dark-fleet-ai-monitor.onrender.com/)**

> **⚠️ IMPORTANT CLOUD HOSTING NOTICE:**  
> This application is hosted on a free cloud tier to demonstrate deployment architecture. **If the link is inactive, please wait 60 to 90 seconds and refresh.** The server automatically goes to sleep to conserve compute hours when not in use and requires a minute to wake up and reconnect to the live satellite feed.

---

### 📺 Live System Demonstration
**[👉 CLICK HERE TO WATCH THE CLOUD DEPLOYMENT & UI DEMO](link_to_your_google_drive_folder_here)**
* **Video Verification Data:** The live demonstration utilizes real-world, real-time unencrypted Automatic Identification System (AIS) telemetry sourced directly from global maritime satellites via **[AISStream.io](https://aisstream.io/)** to validate the model's live ingestion and classification efficiency.

---

## 🚢 Problem Statement
Illegal maritime activities—such as dark fleet oil smuggling, illegal fishing, and sanctions evasion—rely on transponder manipulation (turning off tracking devices or spoofing GPS coordinates). Monitoring these events across global shipping lanes generates an overwhelming volume of continuous, high-velocity streaming data. Processing this continuously without crashing standard web servers or overwhelming analysts requires highly optimized memory management and automated machine learning triage.

## 🚀 Overall Solution Approach
Dark Fleet AI Monitor is an end-to-end continuous cloud portal designed to ingest live satellite streams and automate the first-pass triage of suspicious vessel behavior.
* **Live Telemetry:** Utilizes the WebSocket protocol to stream continuous coordinate and timestamp data directly from the AISStream API.
* **Unsupervised Machine Learning:** Because illegal behavior is inherently unlabeled and constantly evolving, the system uses **Unsupervised ML** instead of traditional classification.
* **Spatial Profiling:** Applies **K-Means Clustering** to assign incoming vessel trajectory vectors (implied speed, time gaps, distance) to historical maritime behavioral clusters.
* **Threat Detection:** Uses **DBSCAN Density Metrics** to evaluate the Euclidean distance of a vessel's behavior to pre-computed core clusters (`eps: 0.3`). Points isolated from core navigation patterns are mathematically flagged as threats.
* **Optimized Architecture:** Deployed a Python FastAPI backend on Docker that utilizes a strict **50-Ping Rolling Memory Window**. This auto-cleans the state buffer, capping server RAM under 20MB even during peak vessel throughput to prevent free-tier cloud crashes.

## 📊 Key Findings & Architectural Decisions
In real-time streaming architectures, balancing machine learning accuracy with server memory footprint is the highest priority to prevent system failure.
* **Handling Stream Amnesia:** We designed an auto-healing reconnection loop. If the external satellite API drops the connection, the Python `asyncio` task automatically kills the dead thread and rebuilds the WebSocket within 5 seconds without crashing the server.
* **Rejecting Stateful Databases for Free Tiers:** Traditional systems log every ping to a database. To maintain 24/7 continuous operation on a $0 budget, we rejected heavy PostgreSQL integrations. Instead, we utilized in-memory Python dictionaries with automated FIFO (First-In-First-Out) queueing, treating the 50-ping window as a rolling "statute of limitations."
* **Forensic Threat Diagnostics:** The system doesn't just flag a ship; it retains the specific algorithmic reasoning (e.g., *Transponder Blackout: 180 min silence* or *Unrealistic Speed: 45 knots*) in a persistent JavaScript Set, ensuring analysts know exactly *why* a ship was flagged long after the initial anomaly occurred.

## 💻 Tactical Monitoring UI (Frontend)
The web application provides instant situational awareness via:
1. **Dynamic Bounding Boxes:** Dropdown selector to switch monitoring zones (Singapore, English Channel, Gulf of Mexico) on the fly. This intentionally severs and rebuilds the satellite connection to prevent the browser from rendering the entire ocean at once and freezing.
2. **Forensic Inspector Panel:** Translates the real-time ping array into a clickable directory, isolating a target ship's historical trajectory on an ArcGIS Canvas Dark tile map.
3. **ML Threat Simulator:** A built-in manual testing console that allows recruiters/analysts to inject synthetic navigation data (e.g., 4-hour blackout, GPS teleportation) directly into the StandardScaler and DBSCAN pipeline to verify algorithmic sensitivity.

## 📁 Repository Structure
* [`main.py`](./main.py): The FastAPI cloud server, ML inference pipeline, and WebSocket hub.
* [`index.html`](./index.html): The interactive Leaflet.js frontend dashboard and forensic panel.
* [`Dockerfile`](./Dockerfile): Production container definition configured for Render's dynamic port binding.
* [`scaler.pkl`](./scaler.pkl): The serialized `StandardScaler` transformation object.
* [`kmeans.pkl`](./kmeans.pkl): The fitted K-Means behavioral clustering model.
* [`dbscan_core_points.npy`](./dbscan_core_points.npy): Precomputed DBSCAN dense cluster core representations for rapid proximity checks.
* [`requirements.txt`](./requirements.txt): Required Python dependencies for Docker cloud deployment.

## 🔮 Future Scope
* **Persistent Criminal Ledger:** Upgrade the architecture from ephemeral memory to an Oracle Cloud VM running PostgreSQL to maintain permanent records of suspect vessels even after browser refreshes.
* **Multi-Modal Detection:** Integrate visual satellite imagery APIs (like Sentinel-1 SAR) to cross-reference AIS blackout zones with physical radar reflections to confirm dark fleet presence.

## ⚙️ How to Run the Project Locally

1. Clone this repository to your local machine.
2. Create a `.env` file in the root directory and add your free AISStream API Key: `AISSTREAM_API_KEY=your_key_here`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the local server: `uvicorn main:app --host 0.0.0.0 --port 8000`
5. Open your browser and navigate to `http://localhost:8000`.
