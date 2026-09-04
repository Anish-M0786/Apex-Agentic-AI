param(
    [switch]$NoModelPull
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$frontendRoot = Join-Path $projectRoot 'frontend'
$envFile = Join-Path $projectRoot '.env'

function Get-EnvValue([string]$name, [string]$fallback) {
    if (Test-Path -LiteralPath $envFile) {
        $line = Get-Content -LiteralPath $envFile |
            Where-Object { $_ -match "^\s*$([regex]::Escape($name))\s*=" } |
            Select-Object -First 1
        if ($line) { return (($line -split '=', 2)[1]).Trim().Trim('"').Trim("'") }
    }
    return $fallback
}

function Test-HttpEndpoint([string]$url) {
    try { Invoke-RestMethod -Uri $url -TimeoutSec 2 | Out-Null; return $true }
    catch { return $false }
}

function Wait-ForEndpoint([string]$url, [int]$seconds = 30) {
    for ($attempt = 0; $attempt -lt $seconds; $attempt++) {
        if (Test-HttpEndpoint $url) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw 'Ollama is not installed or is not available on PATH. Install Ollama, then run this script again.'
}

$ollamaHost = Get-EnvValue 'OLLAMA_HOST' 'http://localhost:11434'
$model = Get-EnvValue 'OLLAMA_MODEL' 'qwen2.5:3b'
$tagsUrl = "$($ollamaHost.TrimEnd('/'))/api/tags"

function Test-OllamaReady {
    if (Test-HttpEndpoint $tagsUrl) { return $true }
    $null = & ollama list 2>$null
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-OllamaReady)) {
    Write-Host 'Starting Ollama...' -ForegroundColor Cyan
    Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden | Out-Null
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        if (Test-OllamaReady) { $ready = $true; break }
    }
    if (-not $ready) { throw "Ollama did not become ready at $ollamaHost. Try running 'ollama serve' once, then rerun this command." }
}

if (-not $NoModelPull) {
    $installedModels = & ollama list 2>$null
    if (-not ($installedModels | Select-String -SimpleMatch $model)) {
        Write-Host "Downloading model $model (first run only)..." -ForegroundColor Yellow
        & ollama pull $model
        if ($LASTEXITCODE -ne 0) { throw "Ollama could not download model $model." }
    }
}

if (-not (Test-Path -LiteralPath $python)) { throw "Python virtual environment not found at $python." }

if (-not (Test-HttpEndpoint 'http://127.0.0.1:8000/')) {
    Write-Host 'Starting Apex backend...' -ForegroundColor Cyan
    Start-Process -FilePath $python -ArgumentList '-m', 'uvicorn', 'backend.main:app', '--reload' -WorkingDirectory $projectRoot
} else { Write-Host 'Apex backend is already running.' -ForegroundColor DarkGray }

if (-not (Wait-ForEndpoint 'http://127.0.0.1:8000/' 30)) {
    throw 'Apex backend did not become ready at http://127.0.0.1:8000.'
}

if (-not (Test-HttpEndpoint 'http://localhost:3000/')) {
    Write-Host 'Starting Apex frontend...' -ForegroundColor Cyan
    Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' -WorkingDirectory $frontendRoot
} else { Write-Host 'Apex frontend is already running.' -ForegroundColor DarkGray }

if (-not (Wait-ForEndpoint 'http://localhost:3000/' 30)) {
    throw 'Apex frontend did not become ready at http://localhost:3000.'
}

Start-Process 'http://localhost:3000'

Write-Host ''
Write-Host 'Apex is ready. The browser has been opened.' -ForegroundColor Green
