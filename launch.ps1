$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "BNet + Twitch Account Management Suite"

Write-Host "============================================"
Write-Host " BNet + Twitch Account Management Suite"
Write-Host "============================================"
Write-Host ""

try {
    $pyVersion = (python --version 2>&1)
    Write-Host "Found $pyVersion"
} catch {
    Write-Host "ERROR: Python not found. Please install Python 3.12+ from python.org" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

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
Write-Host "Press Ctrl+C to stop"
Write-Host ""

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765 --reload
