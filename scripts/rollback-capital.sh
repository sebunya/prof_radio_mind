#!/bin/bash
# Rollback script to disable Capital FM UK collector

ENV_FILE="/opt/rmias/.env.production"

if [ -f "$ENV_FILE" ]; then
    # Modify ENABLE_CAPITAL_COLLECTOR=true to ENABLE_CAPITAL_COLLECTOR=false
    sed -i 's/ENABLE_CAPITAL_COLLECTOR=true/ENABLE_CAPITAL_COLLECTOR=false/g' "$ENV_FILE"
    echo "Disabled Capital FM UK collector in .env.production"

    # Force-recreate app container so the updated env file is re-read.
    # `restart` does NOT reload env vars — `up --force-recreate` does.
    docker compose -f /opt/rmias/docker-compose.hetzner.yml --env-file "$ENV_FILE" up -d --force-recreate app
    echo "App container force-recreated successfully (env vars reloaded)"
else
    echo "Error: .env.production not found at $ENV_FILE"
    exit 1
fi
