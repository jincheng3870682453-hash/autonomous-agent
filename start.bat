@echo off
chcp 65001 >nul
title Autonomous Agent - API Server

echo ========================================
echo   Autonomous Agent - API Server
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Checking dependencies...
pip install -r requirements.txt -q 2>nul
if %errorlevel% neq 0 (
    echo Failed to install dependencies, please check network
    pause
    exit /b 1
)

echo [2/2] Starting API server...
echo.
echo   URL: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Dashboard: http://localhost:8000/dashboard
echo   AI Test Page: http://localhost:8000/dashboard/test_ai.html
echo.
echo   Press Ctrl+C to stop server
echo ========================================
echo.

python run.py api

pause
