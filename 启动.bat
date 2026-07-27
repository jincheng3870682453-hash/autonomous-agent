@echo off
chcp 65001 >nul
title Autonomous Agent - API Server

echo ========================================
echo   Autonomous Agent - API Server
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 检查依赖...
pip install -r requirements.txt -q 2>nul
if %errorlevel% neq 0 (
    echo 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)

echo [2/2] 启动 API 服务器...
echo.
echo   地址: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo   仪表盘: http://localhost:8000/dashboard
echo   测试页面: http://localhost:8000/dashboard/test_ai.html
echo.
echo   按 Ctrl+C 停止服务器
echo ========================================
echo.

python run.py api

pause
