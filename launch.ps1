$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "BNet + Twitch Account Management Suite"

Write-Host "============================================"
Write-Host " BNet + Twitch Account Management Suite"
Write-Host "============================================"
Write-Host ""

# --- Python check ---
try {
    $pyVersion = (python --version 2>&1)
    Write-Host "Found $pyVersion"
} catch {
    Write-Host "ERROR: Python not found. Please install Python 3.12+ from python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# --- .env check ---
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "WARNING: No .env file found. Copying .env.example to .env" -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "Please edit .env with your actual configuration values."
        Write-Host ""
    } else {
        Write-Host "WARNING: No .env or .env.example found. Using default settings." -ForegroundColor Yellow
        Write-Host ""
    }
}

# --- Virtual environment ---
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

Write-Host "Installing dependencies..."
pip install -e ".[dev]" --quiet

if (-not (Test-Path "data")) { New-Item -ItemType Directory -Path "data" | Out-Null }
if (-not (Test-Path "logs")) { New-Item -ItemType Directory -Path "logs" | Out-Null }

Write-Host ""
Write-Host "Starting server on http://127.0.0.1:8765"
Write-Host "API docs: http://127.0.0.1:8765/api/docs"
Write-Host ""

# --- Start server as background job ---
$serverJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    & .\.venv\Scripts\Activate.ps1
    python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765 --reload
}

# --- Health polling (30s timeout) ---
Write-Host "Waiting for server to become healthy (up to 30s)..."
$healthy = $false
for ($i = 0; $i -lt 15; $i++) {
    Start-Sleep -Seconds 2
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/v1/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($resp.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {}
}

if ($healthy) {
    Write-Host "Server is healthy!" -ForegroundColor Green
    Write-Host "Opening browser..."
    Start-Process "http://127.0.0.1:8765"
} else {
    Write-Host "WARNING: Server did not respond within 30s. It may still be starting." -ForegroundColor Yellow
    Write-Host "Open http://127.0.0.1:8765 manually when ready."
}

Write-Host ""
Write-Host "Press Ctrl+C to stop the server."
Write-Host ""

# Keep running and relay server output
try {
    while ($true) {
        Receive-Job -Job $serverJob -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
} finally {
    Stop-Job -Job $serverJob -ErrorAction SilentlyContinue
    Remove-Job -Job $serverJob -Force -ErrorAction SilentlyContinue
}
