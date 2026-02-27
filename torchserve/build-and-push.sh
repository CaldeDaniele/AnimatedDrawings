#!/usr/bin/env bash
# Build dell'immagine RunPod e push su Docker Registry (Docker Hub, GHCR, ecc.).
# Uso: ./build-and-push.sh [REGISTRY/]IMAGE [:TAG]
# Esempio: ./build-and-push.sh miouser/animated-drawings-api
#          ./build-and-push.sh ghcr.io/miouser/animated-drawings-api :v1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ANIMATED_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

IMAGE_SPEC="${1:-}"
TAG="${2:-:latest}"

if [[ -z "$IMAGE_SPEC" ]]; then
  echo "Uso: $0 REGISTRY/IMAGE [TAG]"
  echo "  REGISTRY/IMAGE  es. docker.io/miouser/animated-drawings-api  o  ghcr.io/org/repo"
  echo "  TAG             es. :v1  (default :latest)"
  exit 1
fi

# Se il secondo argomento non inizia con :, è parte del nome immagine
if [[ -n "${2:-}" && "$2" != :* ]]; then
  IMAGE_SPEC="$1:$2"
  TAG=""
fi

FULL_IMAGE="${IMAGE_SPEC}${TAG}"

echo "Build da contesto: $ANIMATED_DIR"
echo "Immagine finale:   $FULL_IMAGE"
docker build -f "$SCRIPT_DIR/Dockerfile.runpod" -t "$FULL_IMAGE" "$ANIMATED_DIR"

echo "Push su registry..."
docker push "$FULL_IMAGE"
echo "Fatto. Su RunPod usa: $FULL_IMAGE"
