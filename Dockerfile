FROM python:3.11-slim

# Install system dependencies and Nginx
RUN apt-get update && \
    apt-get install -y nginx && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files (including main.py, app.py, graph.py, and your ML models)
COPY . .

# Make the start script executable
RUN chmod +x start.sh

# Expose the master port expected by Render and Nginx
ENV PORT=10000
EXPOSE 10000

CMD ["./start.sh"]
