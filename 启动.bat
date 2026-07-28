@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Autonomous Agent - Launcher

echo =========================================
echo   Autonomous Agent - Launcher
echo =========================================
echo.
echo Please select launch mode:
echo   1) Web Mode (Browser)
echo   2) Desktop Mode (Electron)
echo   3) CLI Mode (Terminal)
echo   4) Install / Update Dependencies
echo   0) Exit
echo.
set /p MODE="Enter your choice [0-4] (default 1): "
if "%MODE%"=="" set MODE=1
if "%MODE%"=="0" exit /b
if "%MODE%"=="1" goto web
if "%MODE%"=="2" goto desktop
if "%MODE%"=="3" goto cli
if "%MODE%"=="4" goto install
goto menu

:web
echo.
echo =========================================
echo   Web Mode - Starting API Server
echo   Backend:  http://localhost:8000
echo   Dashboard: http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   AI Test:   http://localhost:8000/test_ai.html
echo =========================================
echo.

cd /d "%~dp0"

echo [Check] Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python 3.9+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do echo         %%i

echo [Check] Dependencies...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [Install] Installing dependencies...
    python -m pip install -r requirements.txt --quiet 2>nul
    if %errorlevel% neq 0 (
        echo [Retry] Using Tsinghua mirror...
        python -m pip install -r requirements.txt --quiet -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul
    )
)

echo [Start] API Server...
start "Autonomous Agent API" cmd /c "cd /d %~dp0 && python run.py api"

echo [Wait] Server starting (3s)...
timeout /t 3 /nobreak >nul

echo [Open] Browser...
start http://localhost:8000

echo.
echo Server is running. Close this window to keep server alive, or press any key to exit and stop server.
echo.
pause
exit /b

:desktop
echo.
echo =========================================
echo   Desktop Mode - Electron App
echo =========================================
echo.

cd /d "%~dp0"

echo [Check] Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

echo [Check] Node.js environment...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Node.js not found. Desktop mode requires Node.js 18+
    echo Download: https://nodejs.org/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do echo         Node.js %%i

echo [Start] API Server (background)...
start "Autonomous Agent API" cmd /c "cd /d %~dp0 && python run.py api"

echo [Wait] Server starting (3s)...
timeout /t 3 /nobreak >nul

if not exist "%~dp0electron" (
    echo [Error] electron/ folder not found. Desktop mode is not configured.
    echo         Run option 4 first to install dependencies.
    pause
    exit /b 1
)

cd /d "%~dp0electron"

if not exist "node_modules" (
    echo [Install] Electron dependencies...
    call npm install
)

echo [Launch] Electron Desktop App...
call npx electron main.js

exit /b

:cli
echo.
echo =========================================
echo   CLI Mode - Interactive Terminal
echo =========================================
echo.

cd /d "%~dp0"

echo [Check] Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

echo [Check] Dependencies...
python -c "import fastapi" >nul 2>&1
if %errorlevel% neq 0 (
    echo [Install] Installing dependencies...
    python -m pip install -r requirements.txt --quiet 2>nul
)

echo [Start] CLI Mode...
echo.
python run.py cli

pause
exit /b

:install
echo.
echo =========================================
echo   Install / Update Dependencies
echo =========================================
echo.

cd /d "%~dp0"

echo [1/3] Installing Python dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [Retry] Using Tsinghua mirror...
    python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)
echo         Done.

echo [2/3] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo         Node.js not found, skipping frontend install.
    echo         Download: https://nodejs.org/
) else (
    if exist "%~dp0electron" (
        echo [3/3] Installing Electron dependencies...
        cd /d "%~dp0electron"
        call npm install
        echo         Done.
    )
)

echo.
echo All dependencies installed successfully.
echo.
pause
exit /b

:menu
echo Invalid choice, please try again.
goto web
