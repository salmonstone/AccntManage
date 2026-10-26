@echo off
title BNet + Twitch Account Management Suite
echo ============================================
echo  BNet + Twitch Account Management Suite
echo ============================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.12+ from python.org
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Found Python %PYVER%

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -e ".[dev]" --quiet
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

if not exist data mkdir data
if not exist logs mkdir logs

echo.
echo Starting server on http://127.0.0.1:8765
echo API docs: http://127.0.0.1:8765/api/docs
echo Press Ctrl+C to stop
echo.

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765 --reload

pause
