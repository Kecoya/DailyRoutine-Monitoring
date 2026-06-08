"""
系统监控与作息分析程序 - 主入口
"""
import sys
import os
import time
import signal
import logging
import threading
from datetime import datetime

# 修复 pythonw.exe 环境下 stdout/stderr 为 None 的问题
# 必须在 print() 或 logging 之前执行
def _fix_stdio():
    """确保 sys.stdout/stderr 可用（pythonw.exe 下它们为 None）"""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')

_fix_stdio()

from monitor_service import ActivityMonitor
from web_app import run_in_thread
from config import LOG_FILE, LOG_FORMAT, LOG_LEVEL, WEB_HOST, WEB_PORT

# 单实例锁文件路径
LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.monitor.lock')


def _setup_logging():
    """配置日志（只配置一次，避免重复 handler）"""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return  # 已经配置过，跳过

    root_logger.setLevel(getattr(logging, LOG_LEVEL))

    formatter = logging.Formatter(LOG_FORMAT)

    # 文件 handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    # 控制台 handler（仅在 stdout 可用时添加）
    try:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
    except Exception:
        pass


logger = logging.getLogger(__name__)

# 全局变量
monitor = None
web_thread = None


class SingleInstance:
    """单实例检测，防止程序多开"""

    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.lock_fd = None

    def acquire(self) -> bool:
        """尝试获取实例锁，返回是否成功"""
        try:
            # 尝试以独占方式创建/打开锁文件
            import msvcrt
            self.lock_fd = open(self.lock_file, 'w')
            msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            return True
        except (IOError, OSError):
            if self.lock_fd:
                self.lock_fd.close()
            return False

    def release(self):
        """释放实例锁"""
        try:
            if self.lock_fd:
                import msvcrt
                msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                self.lock_fd.close()
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except Exception:
            pass


def signal_handler(sig, frame):
    """信号处理器（用于优雅退出）"""
    logger.info("收到退出信号，正在关闭程序...")

    if monitor:
        monitor.stop()

    logger.info("程序已退出")
    sys.exit(0)


def print_banner():
    """打印欢迎信息"""
    banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        系统监控与作息分析程序 v1.1.0                        ║
║                                                           ║
║        实时监控 | 数据分析 | 作息追踪                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  日志文件: {LOG_FILE}")
    print()


def main():
    """主函数"""
    global monitor, web_thread

    # 单实例检测
    instance = SingleInstance(LOCK_FILE)
    if not instance.acquire():
        print("程序已在运行中，不可重复启动！", file=sys.stderr)
        # 即使是 pythonw 模式，也尝试弹窗提示
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, "系统监控程序已在运行中！\n如需重启请先关闭已有进程。", "提示", 0x30
            )
        except Exception:
            pass
        sys.exit(1)

    try:
        # 配置日志
        _setup_logging()

        # 打印欢迎信息
        print_banner()

        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 创建并启动监控服务
        logger.info("正在初始化监控服务...")
        monitor = ActivityMonitor()
        monitor.start()

        # 等待监控服务完全启动
        time.sleep(2)

        # 启动Web服务器
        logger.info("正在启动Web服务器...")
        web_thread = run_in_thread(monitor)

        print("  系统监控服务已启动")
        print(f"  Web界面: http://{WEB_HOST}:{WEB_PORT}")
        print("  实时监控中...")
        print()
        print("  按 Ctrl+C 停止程序")
        print("=" * 60)
        print()

        # 保持程序运行
        while True:
            time.sleep(60)

            # 每小时输出一次状态
            now = datetime.now()
            if now.minute == 0:
                if monitor:
                    status = monitor.get_current_status()
                    logger.info(f"每小时状态报告 - "
                                f"按键: {status['keyboard_presses']}, "
                                f"点击: {status['mouse_clicks']}, "
                                f"窗口切换: {status['window_switches']}")

    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")

    except Exception as e:
        logger.error(f"程序运行出错: {e}", exc_info=True)

    finally:
        # 清理资源
        if monitor:
            logger.info("正在停止监控服务...")
            monitor.stop()

        # 释放单实例锁
        instance.release()

        logger.info("程序已完全退出")


if __name__ == '__main__':
    main()
