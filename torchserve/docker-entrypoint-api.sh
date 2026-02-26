#!/usr/bin/env bash
set -euo pipefail

echo "Starting TorchServe..."
/opt/conda/bin/torchserve --start --disable-token-auth --ts-config /home/torchserve/config.properties

echo "Waiting for TorchServe health endpoint..."
for i in $(seq 1 60); do
  if curl -s http://localhost:8080/ping 2>/dev/null | grep -q Healthy; then
    echo "TorchServe healthy."
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "TorchServe did not become healthy in time."
    exit 1
  fi
  sleep 2
done

echo "Starting GIF API on :8000..."
cd /app/AnimatedDrawings
exec uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 1
