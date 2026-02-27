# Build immagine RunPod e push su Docker Registry (Docker Hub, GHCR, ecc.).
# Uso: .\build-and-push.ps1 [-Image] REGISTRY/IMAGE [-Tag] TAG
# Esempio: .\build-and-push.ps1 miouser/animated-drawings-api
#          .\build-and-push.ps1 ghcr.io/miouser/animated-drawings-api -Tag v1
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string] $Image,
    [string] $Tag = "latest"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$AnimatedDir = Split-Path -Parent $ScriptDir

$FullImage = if ($Tag) { "${Image}:${Tag}" } else { $Image }

Write-Host "Build da contesto: $AnimatedDir"
Write-Host "Immagine finale:   $FullImage"
docker build -f "$ScriptDir\Dockerfile.runpod" -t $FullImage $AnimatedDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Push su registry..."
docker push $FullImage
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Fatto. Su RunPod usa: $FullImage"
