@echo off
chcp 65001 >nul
title 安装依赖库

echo ╔═══════════════════════════════════════════════════════════╗
echo ║                                                           ║
echo ║        系统监控与作息分析程序 - 依赖安装                    ║
echo ║                                                           ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

echo 正在检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo.
    echo ❌ 未找到Python！
    echo 请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Python环境正常
echo.

echo 正在安装依赖库...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ❌ 安装失败！
    echo 请检查网络连接或手动安装
    echo.
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════
echo ✅ 所有依赖已成功安装！
echo ═══════════════════════════════════════════════════════════
echo.
echo 接下来你可以：
echo 1. 双击"启动监控.bat"启动程序
echo 2. 运行"setup_autostart.py"设置开机自启动
echo.

pause

