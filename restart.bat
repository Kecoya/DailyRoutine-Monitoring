@echo off
chcp 65001 >nul
echo ============================================
echo 重启系统监控服务
echo ============================================

echo 正在查找并停止监控服务进程...

REM 只停止与本项目相关的 Python 进程（通过窗口标题和命令行参数匹配）
REM 先尝试找到运行 main.py 的进程
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" /FO LIST ^| find "PID"') do (
    wmic process where "ProcessId=%%a and CommandLine like '%%main.py%%'" get ProcessId 2>nul | find "%%a" >nul && (
        echo 停止监控进程 PID: %%a
        taskkill /F /PID %%a 2>nul
    )
)

for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq pythonw.exe" /FO LIST ^| find "PID"') do (
    wmic process where "ProcessId=%%a and CommandLine like '%%main.py%%'" get ProcessId 2>nul | find "%%a" >nul && (
        echo 停止监控进程 PID: %%a
        taskkill /F /PID %%a 2>nul
    )
)

REM 等待进程完全退出
timeout /t 3 /nobreak >nul

REM 删除残留的锁文件
if exist "%~dp0.monitor.lock" (
    echo 清理残留锁文件...
    del /f "%~dp0.monitor.lock" 2>nul
)

echo.
echo 正在启动监控服务...
echo.

REM 使用 pythonw 后台运行（无窗口）
start "" /min pythonw "%~dp0main.py"

echo 服务已启动！
echo.
echo 请等待3-5秒后刷新浏览器页面 (Ctrl+F5)
echo Web界面地址: http://127.0.0.1:5000
echo.

pause
