@echo off
chcp 65001 >nul
title Asset Management System

set "ROOT_DIR=%~dp0"
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"

echo ================================
echo   Asset Management System
echo ================================

if not exist "%ROOT_DIR%\.venv\Scripts\uvicorn.exe" (
    echo [ERROR] Backend not installed. Run setup.bat first.
    pause
    exit /b 1
)

if not exist "%ROOT_DIR%\frontend\node_modules" (
    echo [ERROR] Frontend not installed. Run setup.bat first.
    pause
    exit /b 1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [WARNING] Port 8000 already in use. Stopping...
    taskkill /pid %%a /f >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5173" ^| findstr "LISTENING"') do (
    echo [WARNING] Port 5173 already in use. Stopping...
    taskkill /pid %%a /f >nul 2>&1
)

echo [1/2] Starting backend...
cd /d "%ROOT_DIR%"
start "uvicorn" cmd /k "cd /d %ROOT_DIR% && .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo [2/2] Starting frontend...
cd /d "%ROOT_DIR%\frontend"
start "vite" cmd /k "cd /d "%ROOT_DIR%\frontend" && npm run dev"

echo    Waiting for services...
timeout /t 6 /nobreak >nul
echo.
echo ================================
echo   Services started
echo ================================
echo   Frontend:    http://localhost:5173
echo   Backend:     http://localhost:8000
echo   API Docs:    http://localhost:8000/docs
echo   Login:       root / 101704
echo ================================
echo.
echo Press any key to stop all services...
pause >nul

taskkill /fi "WINDOWTITLE eq uvicorn" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq vite" /f >nul 2>&1
echo Services stopped.
timeout /t 2 >nul
