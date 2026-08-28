@echo off
chcp 65001 >nul
title Setup - Dependencies

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

echo ================================
echo   Installing Dependencies
echo ================================

where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] uv not found. Install: https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/3] Syncing backend dependencies...
cd /d "%ROOT_DIR%"
uv sync
if %errorlevel% neq 0 (
    echo [ERROR] Backend sync failed!
    pause
    exit /b 1
)

echo [2/3] Installing frontend dependencies...
cd /d "%ROOT_DIR%\frontend"
npm install
if %errorlevel% neq 0 (
    echo [ERROR] Frontend install failed!
    pause
    exit /b 1
)

echo [3/3] Verifying installation...
cd /d "%ROOT_DIR%"
.venv\Scripts\python.exe -c "import fastapi, uvicorn, sqlalchemy, pydantic, pandas, requests, pytest; print('All packages OK')"
if %errorlevel% neq 0 (
    echo [ERROR] Verification failed!
    pause
    exit /b 1
)

echo.
echo ================================
echo   Dependencies installed
echo ================================
pause
