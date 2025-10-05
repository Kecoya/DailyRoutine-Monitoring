"""
系统监控与作息分析程序 - 主入口
"""
import sys
import time
import signal
import logging
from datetime import datetime

from monitor_service import ActivityMonitor
from web_app import run_in_thread
from config import LOG_FILE, LOG_FORMAT, LOG_LEVEL

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# 全局变量
monitor = None
web_thread = None


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
║        系统监控与作息分析程序 v1.0.0                        ║
║                                                           ║
║        实时监控 | 数据分析 | 作息追踪                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""
    print(banner)
    print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 日志文件: {LOG_FILE}")
    print()


def main():
    """主函数"""
    global monitor, web_thread
    
    # 打印欢迎信息
    print_banner()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 创建并启动监控服务
        logger.info("正在初始化监控服务...")
        monitor = ActivityMonitor()
        monitor.start()
        
        # 等待监控服务完全启动
        time.sleep(2)
        
        # 启动Web服务器
        logger.info("正在启动Web服务器...")
        web_thread = run_in_thread(monitor)
        
        print("✅ 系统监控服务已启动")
        print(f"🌐 Web界面: http://127.0.0.1:5000")
        print("📊 实时监控中...")
        print()
        print("按 Ctrl+C 停止程序")
        print("=" * 60)
        print()
        
        # 保持程序运行
        while True:
            time.sleep(60)
            
            # 每小时输出一次状态
            now = datetime.now()
            if now.minute == 0:
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
        
        logger.info("程序已完全退出")


if __name__ == '__main__':
    main()

