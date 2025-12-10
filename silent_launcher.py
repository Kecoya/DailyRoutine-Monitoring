"""
静默启动器 - 用于自启动时隐藏控制台窗口
使用 pythonw.exe 启动主程序，避免显示控制台窗口
"""
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

def main():
    """静默启动主程序"""
    try:
        # 获取当前脚本目录
        script_dir = Path(__file__).parent.absolute()
        main_script = script_dir / "main.py"

        # 检查主程序是否存在
        if not main_script.exists():
            # 如果没有日志目录，创建一个
            log_dir = script_dir / "logs"
            log_dir.mkdir(exist_ok=True)

            # 写入错误日志
            error_log = log_dir / "silent_launcher_error.log"
            with open(error_log, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] 主程序文件不存在: {main_script}\n")
            return

        # 获取 pythonw.exe 路径（Python的无窗口版本）
        python_exe = sys.executable
        pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")

        # 如果没有 pythonw.exe，使用 python.exe 但隐藏窗口
        if not os.path.exists(pythonw_exe):
            pythonw_exe = python_exe

        # 启动主程序，不创建窗口
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        # 启动主程序
        creation_flags = 0
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creation_flags = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(
            [pythonw_exe, str(main_script)],
            cwd=str(script_dir),
            startupinfo=startupinfo,
            creationflags=creation_flags
        )

        # 记录启动成功
        log_dir = script_dir / "logs"
        log_dir.mkdir(exist_ok=True)

        success_log = log_dir / "silent_launcher.log"
        with open(success_log, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] 主程序启动成功，PID: {process.pid}\n")

    except Exception as e:
        # 记录错误
        script_dir = Path(__file__).parent.absolute()
        log_dir = script_dir / "logs"
        log_dir.mkdir(exist_ok=True)

        error_log = log_dir / "silent_launcher_error.log"
        with open(error_log, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] 启动失败: {e}\n")

if __name__ == "__main__":
    main()