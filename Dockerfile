# Use official lightweight Python image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install system dependencies if required and Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application assets into the container
COPY . .

# Run Uvicorn binding to Render's dynamic $PORT (fallback to 8000)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}