#!/bin/bash
# Entrypoint script to start both Flask API and download handler

set -e

# Start the download handler in the background
echo "Starting download handler..."
python3 scripts/download_handler.py > logs/download_handler.log 2>&1 &
DOWNLOAD_HANDLER_PID=$!
echo "Download handler started with PID: $DOWNLOAD_HANDLER_PID"

# Function to handle shutdown gracefully
shutdown() {
    echo "Shutting down services..."
    if kill -0 $DOWNLOAD_HANDLER_PID 2>/dev/null; then
        echo "Stopping download handler (PID: $DOWNLOAD_HANDLER_PID)"
        kill $DOWNLOAD_HANDLER_PID
    fi
    exit 0
}

# Trap SIGTERM and SIGINT for graceful shutdown
trap shutdown SIGTERM SIGINT

# Start the Flask application (this will run in foreground)
echo "Starting Flask API..."
exec python -m app.sync.sync_api
