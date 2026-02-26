#!/usr/bin/env bash
# Avvia container Docker all-in-one: TorchServe + GIF API (FastAPI + Swagger).
# Alla prima esecuzione builda:
# 1) immagine base TorchServe (docker_torchserve)
# 2) immagine API (docker_torchserve_api)

set -e
cd "$(dirname "$0")"
TS_DIR="torchserve"
AD_DIR="."
BASE_IMAGE="docker_torchserve"
API_IMAGE="docker_torchserve_api"
CONTAINER_NAME="docker_torchserve"
API_DOCKERFILE="$TS_DIR/Dockerfile.api"

if [ ! -d "$TS_DIR" ]; then
  echo "Cartella $TS_DIR non trovata."
  exit 1
fi
if [ ! -f "$API_DOCKERFILE" ]; then
  echo "File $API_DOCKERFILE non trovato."
  exit 1
fi

wait_for_services() {
  echo "Attendo che TorchServe risponda..."
  for i in $(seq 1 30); do
    if curl -s http://localhost:8080/ping 2>/dev/null | grep -q Healthy; then
      echo "TorchServe OK."
      break
    fi
    sleep 2
  done

  echo "Attendo che API risponda..."
  for i in $(seq 1 30); do
    if curl -s http://localhost:8000/health 2>/dev/null | grep -q '"status":"ok"'; then
      echo "API OK."
      echo "Swagger: http://localhost:8000/docs"
      return 0
    fi
    sleep 2
  done
  echo "API non ha risposto in tempo. Controlla: docker logs $CONTAINER_NAME"
  return 1
}

if docker ps -a --format "{{.Names}}" 2>/dev/null | grep -qx "$CONTAINER_NAME"; then
  if [ "$(uname -m)" = "arm64" ] && [ "$(uname -s)" = "Darwin" ]; then
    echo "Suggerimento: su Mac Apple Silicon abilita Rosetta in Docker Desktop (Settings → General)."
  fi
  if ! docker ps --format "{{.Names}}" 2>/dev/null | grep -qx "$CONTAINER_NAME"; then
    echo "Avvio container $CONTAINER_NAME..."
    docker start "$CONTAINER_NAME"
  else
    echo "Container già in esecuzione ($CONTAINER_NAME)."
  fi
  wait_for_services
  exit $?
fi

USE_GPU=""
if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null; then
  USE_GPU="--gpus all"
fi
if docker images --format "{{.Repository}}" 2>/dev/null | grep -qx "$API_IMAGE"; then
  echo "Avvio container API..."
  if ! docker run -d --name "$CONTAINER_NAME" $USE_GPU -p 8000:8000 -p 8080:8080 -p 8081:8081 "$API_IMAGE" 2>/dev/null; then
    echo "Riprovo senza GPU..."
    docker run -d --name "$CONTAINER_NAME" -p 8000:8000 -p 8080:8080 -p 8081:8081 "$API_IMAGE"
  fi
  wait_for_services
  exit $?
fi

if [ "$(uname -m)" = "arm64" ] && [ "$(uname -s)" = "Darwin" ]; then
  echo "Mac Apple Silicon: immagine amd64 emulata. Per performance migliori abilita Rosetta in Docker Desktop."
fi
echo "Build immagini Docker (può richiedere vari minuti)..."
echo "Se fallisce con memoria insufficiente: Docker Desktop → Settings → Resources → Memory → 16GB"

if ! docker images --format "{{.Repository}}" 2>/dev/null | grep -qx "$BASE_IMAGE"; then
  echo "Build immagine base $BASE_IMAGE..."
  (
    cd "$TS_DIR"
    docker build --platform linux/amd64 -t "$BASE_IMAGE" .
  ) || {
    echo "Build base fallita."
    exit 1
  }
fi

echo "Build immagine API $API_IMAGE..."
docker build --platform linux/amd64 -f "$API_DOCKERFILE" -t "$API_IMAGE" "$AD_DIR" || {
  echo "Build API fallita."
  exit 1
}

echo "Avvio container $CONTAINER_NAME..."
if ! docker run -d --name "$CONTAINER_NAME" $USE_GPU -p 8000:8000 -p 8080:8080 -p 8081:8081 "$API_IMAGE" 2>/dev/null; then
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
  docker run -d --name "$CONTAINER_NAME" -p 8000:8000 -p 8080:8080 -p 8081:8081 "$API_IMAGE"
fi

wait_for_services
