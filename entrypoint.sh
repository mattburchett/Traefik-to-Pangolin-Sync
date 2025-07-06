#!/bin/bash

# Default schedule interval is 5 minutes (300 seconds)
SCHEDULE_INTERVAL=${SCHEDULE_INTERVAL:-300}

echo "Starting Traefik to Pangolin Sync with schedule interval: ${SCHEDULE_INTERVAL} seconds"

# Function to run the sync
run_sync() {
    echo "$(date): Starting sync..."
    python3 main.py
    echo "$(date): Sync completed"
}

# Run initial sync
run_sync

# Schedule subsequent runs
while true; do
    echo "$(date): Sleeping for ${SCHEDULE_INTERVAL} seconds..."
    sleep ${SCHEDULE_INTERVAL}
    run_sync
done