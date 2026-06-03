#!/bin/bash
# RMIAS Hetzner Smoke Test Script
# Usage: BASE_URL=https://radio.example.com ./hetzner-smoke-test.sh

set -e

URL="${BASE_URL:-http://localhost:8000}"

echo "Running smoke test against $URL..."

if ! RESPONSE=$(curl -sf "$URL/health"); then
  echo "ERROR: Health check failed to respond"
  exit 1
fi

echo "Response received: $RESPONSE"

STATUS=$(echo "$RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
SCHEDULER=$(echo "$RESPONSE" | grep -o '"scheduler":"[^"]*"' | cut -d'"' -f4)

if [ "$STATUS" != "ok" ]; then
  echo "ERROR: App health status is '$STATUS', expected 'ok'"
  exit 1
fi

echo "SUCCESS: App health is OK"

if [ "$SCHEDULER" != "stopped" ]; then
  echo "WARNING: Scheduler is '$SCHEDULER', expected 'stopped' during initial clean deployment"
fi

exit 0
