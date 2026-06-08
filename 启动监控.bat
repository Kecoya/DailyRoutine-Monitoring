@echo off
chcp 65001 >nul
title 系统监控与作息分析程序

echo.
echo   ==========================================
echo     系统监控与作息分析程序
echo   ==========================================
echo.
echo   正在启动监控服务...
echo.

python main.py

if %errorlevel% neq 0 (
    echo.
    echo   ❌ 启动失败！
    echo.
    echo   可能的原因：
    echo   1. 未安装 Python 或 Python 不在系统 PATH 中
    echo   2. 未安装依赖库，请运行：pip install -r requirements.txt
    echo   3. 程序已在运行中（检查端口 5000 是否被占用）
    echo   4. 权限不足
    echo.
    pause
    exit /b 1
)

pause
