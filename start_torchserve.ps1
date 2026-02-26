$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$tsDir = Join-Path $PSScriptRoot "torchserve"
$adDir = $PSScriptRoot
$baseImage = "docker_torchserve"
$apiImage = "docker_torchserve_api"
$containerName = "docker_torchserve"
$apiDockerfile = Join-Path $tsDir "Dockerfile.api"

if (-not (Test-Path $tsDir)) {
    Write-Host "Cartella $tsDir non trovata."
    exit 1
}
if (-not (Test-Path $apiDockerfile)) {
    Write-Host "File $apiDockerfile non trovato."
    exit 1
}

function Test-TorchServeHealthy {
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:8080/ping" -TimeoutSec 2 -ErrorAction Stop
        return $r.status -eq "Healthy"
    } catch {
        return $false
    }
}

function Test-ApiHealthy {
    try {
        $r = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop
        return $r.status -eq "ok"
    } catch {
        return $false
    }
}

function Wait-Services {
    Write-Host "Attendo che TorchServe risponda..."
    for ($i = 1; $i -le 30; $i++) {
        if (Test-TorchServeHealthy) { Write-Host "TorchServe OK."; break }
        Start-Sleep -Seconds 2
    }
    Write-Host "Attendo che API risponda..."
    for ($i = 1; $i -le 30; $i++) {
        if (Test-ApiHealthy) {
            Write-Host "API OK."
            Write-Host "Swagger: http://localhost:8000/docs"
            return $true
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "API non ha risposto in tempo. Controlla: docker logs $containerName"
    return $false
}

$containers = docker ps -a --format "{{.Names}}" 2>$null
$running = docker ps --format "{{.Names}}" 2>$null
if ($containers -match "^$containerName$" -or $containers -match $containerName) {
    if ($running -notmatch "^$containerName$" -and $running -notmatch $containerName) {
        Write-Host "Avvio container $containerName..."
        docker start $containerName | Out-Null
    } else {
        Write-Host "Container già in esecuzione ($containerName)."
    }
    if (Wait-Services) { exit 0 } else { exit 1 }
}

$useGpu = $false
try {
    nvidia-smi | Out-Null
    $useGpu = $true
} catch {
    $useGpu = $false
}

$images = docker images --format "{{.Repository}}" 2>$null
if ($images -match "^$apiImage$" -or $images -match $apiImage) {
    Write-Host "Avvio container API..."
    if ($useGpu) {
        docker run -d --name $containerName --gpus all -p 8000:8000 -p 8080:8080 -p 8081:8081 $apiImage | Out-Null
    } else {
        docker run -d --name $containerName -p 8000:8000 -p 8080:8080 -p 8081:8081 $apiImage | Out-Null
    }
    if (Wait-Services) { exit 0 } else { exit 1 }
}

Write-Host "Build immagini Docker (può richiedere vari minuti)..."
Write-Host "Se fallisce con memoria insufficiente: Docker Desktop -> Settings -> Resources -> Memory -> 16GB"

if (-not ($images -match "^$baseImage$" -or $images -match $baseImage)) {
    Write-Host "Build immagine base $baseImage..."
    Push-Location $tsDir
    try {
        docker build --platform linux/amd64 -t $baseImage .
    } catch {
        Write-Host "Build base fallita."
        exit 1
    } finally {
        Pop-Location
    }
}

Write-Host "Build immagine API $apiImage..."
docker build --platform linux/amd64 -f $apiDockerfile -t $apiImage $adDir

Write-Host "Avvio container $containerName..."
try { docker rm -f $containerName | Out-Null } catch {}
if ($useGpu) {
    docker run -d --name $containerName --gpus all -p 8000:8000 -p 8080:8080 -p 8081:8081 $apiImage | Out-Null
} else {
    docker run -d --name $containerName -p 8000:8000 -p 8080:8080 -p 8081:8081 $apiImage | Out-Null
}

if (Wait-Services) { exit 0 } else { exit 1 }
