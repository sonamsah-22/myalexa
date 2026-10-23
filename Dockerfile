FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY daybreak/requirements.txt /app/daybreak/requirements.txt
RUN pip install --no-cache-dir -r /app/daybreak/requirements.txt

# Copy application source code
COPY daybreak /app/daybreak
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV STORAGE=memory
ENV PORT=8000
ENV UI_PORT=3000

# Expose MCP Server (8000) and Web UI (3000)
EXPOSE 8000 3000

# Default entrypoint runs both services
CMD ["/app/start.sh"]
