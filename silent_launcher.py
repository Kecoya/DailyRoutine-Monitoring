"""
静默启动器 - 用于自启动时隐藏控制台窗口
使用 pythonw.exe 启动主程序，避免显示控制台窗口
"""
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime


def ensure_log_dir():
    """确保日志目录存在"""
    log_dir = Path(__file__).parent.absolute() / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir


def write_log(log_dir, filename, message):
    """写入日志文件"""
    log_file = log_dir / filename
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def main():
    """静默启动主程序"""
    try:
        script_dir = Path(__file__).parent.absolute()
        main_script = script_dir / "main.py"
        log_dir = ensure_log_dir()

        # 检查主程序是否存在
        if not main_script.exists():
            write_log(log_dir, "silent_launcher_error.log",
                      f"主程序文件不存在: {main_script}")
            return

        # 获取 pythonw.exe 路径（Python 的无窗口版本）
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

        # CREATE_NO_WINDOW 防止创建控制台窗口
        creation_flags = 0
        if hasattr(subprocess, 'CREATE_NO_WINDOW'):
            creation_flags = subprocess.CREATE_NO_WINDOW

        # DETACHED_PROCESS 使子进程独立于父进程（父进程退出后子进程继续运行）
        if hasattr(subprocess, 'DETACHED_PROCESS'):
            creation_flags |= subprocess.DETACHED_PROCESS

        process = subprocess.Popen(
            [pythonw_exe, str(main_script)],
            cwd=str(script_dir),
            startupinfo=startupinfo,
            creationflags=creation_flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        write_log(log_dir, "silent_launcher.log",
                  f"主程序启动成功，PID: {process.pid}")

    except Exception as e:
        log_dir = ensure_log_dir()
        write_log(log_dir, "silent_launcher_error.log", f"启动失败: {e}")


if __name__ == "__main__":
    main()
