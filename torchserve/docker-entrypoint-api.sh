#!/usr/bin/env bash
set -euo pipefail

# Force GPU 0 for this container so TorchServe backend workers see it (WSL2/Docker sometimes need this).
export CUDA_VISIBLE_DEVICES=0

echo "=== GPU check (container must be run with --gpus all) ==="
if command -v nvidia-smi &>/dev/null; then
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
  if /opt/conda/bin/python -c "import torch; print('PyTorch CUDA available:', torch.cuda.is_available()); print('Device count:', torch.cuda.device_count())" 2>/dev/null; then
    :
  else
    echo "WARNING: PyTorch or CUDA check failed; inference may run on CPU."
  fi
else
  echo "WARNING: nvidia-smi not found. Start the container with: docker run --gpus all ..."
fi

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
# 2 workers allow one request to run while another is queued (TorchServe stays single-worker per model).
exec uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 2
