@echo off
title BNet + Twitch Account Management Suite
echo ============================================
echo  BNet + Twitch Account Management Suite
echo ============================================
echo.

REM --- Python check ---
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.12+ from python.org
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Found Python %PYVER%

REM --- .env check ---
if not exist .env (
    if exist .env.example (
        echo WARNING: No .env file found. Copying .env.example to .env
        copy .env.example .env >nul
        echo Please edit .env with your actual configuration values.
        echo.
    ) else (
        echo WARNING: No .env or .env.example found. Using default settings.
        echo.
    )
)

REM --- Virtual environment ---
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
echo.

REM --- Start server in background, poll health, open browser ---
start /b python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765 --reload

echo Waiting for server to become healthy (up to 30s)...
set /a TRIES=0
:healthloop
if %TRIES% geq 15 (
    echo WARNING: Server did not respond within 30s. It may still be starting.
    echo Open http://127.0.0.1:8765 manually when ready.
    goto waitloop
)
timeout /t 2 /nobreak >nul
curl -sf http://127.0.0.1:8765/api/v1/health >nul 2>nul
if %errorlevel% equ 0 (
    echo Server is healthy!
    echo Opening browser...
    start http://127.0.0.1:8765
    goto waitloop
)
set /a TRIES+=1
goto healthloop

:waitloop
echo.
echo Press Ctrl+C to stop the server.
echo.
REM Keep the window open so uvicorn stays running
cmd /k
