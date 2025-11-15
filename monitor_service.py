"""
系统监控服务
实时监控鼠标、键盘、窗口和系统活动
"""
import time
import logging
import threading
from datetime import datetime
from typing import Optional
import psutil
from pynput import mouse, keyboard
import win32gui
import win32process

from database import Database
from config import (
    MONITOR_INTERVAL, IDLE_THRESHOLD, 
    BUSY_WEIGHTS, LOG_FILE, LOG_FORMAT, LOG_LEVEL
)

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


class ActivityMonitor:
    """活动监控器"""
    
    def __init__(self):
        self.db = Database()
        self.session_id = None
        
        # 活动计数器
        self.mouse_distance = 0.0
        self.mouse_clicks = 0
        self.mouse_moves = 0
        self.keyboard_presses = 0
        self.window_switches = 0
        
        # 鼠标位置追踪
        self.last_mouse_pos = None
        self.last_active_window = None
        
        # 监听器
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # 运行标志
        self.running = False
        self.monitor_thread = None
        
        # 最后活动时间
        self.last_activity_time = datetime.now()
    
    def on_mouse_move(self, x, y):
        """鼠标移动事件"""
        if self.last_mouse_pos:
            distance = ((x - self.last_mouse_pos[0]) ** 2 + 
                       (y - self.last_mouse_pos[1]) ** 2) ** 0.5
            self.mouse_distance += distance
        
        self.last_mouse_pos = (x, y)
        self.mouse_moves += 1
        self.last_activity_time = datetime.now()
    
    def on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        if pressed:
            self.mouse_clicks += 1
            self.last_activity_time = datetime.now()
    
    def on_key_press(self, key):
        """键盘按键事件"""
        self.keyboard_presses += 1
        self.last_activity_time = datetime.now()
    
    def get_active_window_info(self) -> tuple:
        """获取活动窗口信息"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(hwnd)
            
            # 检测窗口切换
            if self.last_active_window and self.last_active_window != window_title:
                self.window_switches += 1
            
            self.last_active_window = window_title
            
            # 获取窗口数量（所有可见窗口）
            window_count = 0
            
            def enum_handler(hwnd, ctx):
                nonlocal window_count
                if win32gui.IsWindowVisible(hwnd):
                    window_count += 1
            
            win32gui.EnumWindows(enum_handler, None)
            
            return window_title, window_count
        except Exception as e:
            logger.error(f"获取窗口信息失败: {e}")
            return "", 0
    
    def get_system_usage(self) -> tuple:
        """获取系统资源使用情况"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            return cpu_percent, memory_percent
        except Exception as e:
            logger.error(f"获取系统资源失败: {e}")
            return 0, 0
    
    def calculate_busy_index(self, mouse_activity: float, keyboard_activity: float,
                            window_activity: float, system_activity: float) -> float:
        """
        计算忙碌指数（0-100）
        """
        busy_index = (
            mouse_activity * BUSY_WEIGHTS['mouse_activity'] +
            keyboard_activity * BUSY_WEIGHTS['keyboard_activity'] +
            window_activity * BUSY_WEIGHTS['window_switches'] +
            system_activity * BUSY_WEIGHTS['system_usage']
        )
        return min(100, max(0, busy_index))
    
    def is_idle(self) -> bool:
        """判断是否处于空闲状态"""
        time_since_activity = (datetime.now() - self.last_activity_time).total_seconds()
        return time_since_activity > IDLE_THRESHOLD
    
    def collect_and_save_data(self):
        """收集并保存数据"""
        try:
            # 获取窗口信息
            active_window, window_count = self.get_active_window_info()
            
            # 获取系统资源使用
            cpu_usage, memory_usage = self.get_system_usage()
            
            # 标准化活动指标（基于MONITOR_INTERVAL的期望值）
            # 计算每秒的期望值，然后乘以实际间隔
            interval_factor = MONITOR_INTERVAL / 60  # 相对于1分钟的系数
            
            # 假设正常工作状态（每分钟）：
            # - 鼠标移动约1000-5000像素
            # - 鼠标点击约10-50次
            # - 键盘按键约50-300次
            # - 窗口切换约0-10次
            
            mouse_activity_score = min(100, (
                (self.mouse_distance / (5000 * interval_factor) * 50) +
                (self.mouse_clicks / (50 * interval_factor) * 30) +
                (self.mouse_moves / (500 * interval_factor) * 20)
            ))
            
            keyboard_activity_score = min(100, self.keyboard_presses / (300 * interval_factor) * 100)
            
            window_activity_score = min(100, self.window_switches / (10 * interval_factor) * 100)
            
            system_activity_score = (cpu_usage + memory_usage) / 2
            
            # 计算忙碌指数
            busy_index = self.calculate_busy_index(
                mouse_activity_score,
                keyboard_activity_score,
                window_activity_score,
                system_activity_score
            )
            
            # 判断是否空闲
            is_idle = self.is_idle()
            
            # 如果空闲，忙碌指数设为0
            if is_idle:
                busy_index = 0
            
            # 准备记录数据
            record = {
                'timestamp': datetime.now(),
                'mouse_distance': round(self.mouse_distance, 2),
                'mouse_clicks': self.mouse_clicks,
                'mouse_moves': self.mouse_moves,
                'keyboard_presses': self.keyboard_presses,
                'window_switches': self.window_switches,
                'active_windows': window_count,
                'cpu_usage': round(cpu_usage, 2),
                'memory_usage': round(memory_usage, 2),
                'busy_index': round(busy_index, 2),
                'is_idle': is_idle,
                'active_window_title': active_window[:200]  # 限制长度
            }
            
            # 保存到数据库
            self.db.save_activity_record(record)
            
            logger.info(f"数据已保存({MONITOR_INTERVAL}s) - 忙碌指数: {busy_index:.2f}, "
                       f"鼠标: {self.mouse_clicks}次点击/{self.mouse_distance:.0f}px, "
                       f"键盘: {self.keyboard_presses}次按键, "
                       f"窗口切换: {self.window_switches}次")
            
            # 重置计数器
            self.reset_counters()
            
        except Exception as e:
            logger.error(f"收集和保存数据失败: {e}", exc_info=True)
    
    def reset_counters(self):
        """重置计数器"""
        self.mouse_distance = 0.0
        self.mouse_clicks = 0
        self.mouse_moves = 0
        self.keyboard_presses = 0
        self.window_switches = 0
    
    def monitor_loop(self):
        """监控循环"""
        logger.info("监控循环开始")
        
        while self.running:
            try:
                # 收集并保存数据
                self.collect_and_save_data()
                
                # 每小时更新一次每日统计
                now = datetime.now()
                if now.minute == 0 and now.second < MONITOR_INTERVAL:  # 每小时的第0分钟
                    self.db.update_daily_stats(now.date())
                
                # 等待到下一个监控间隔
                time.sleep(MONITOR_INTERVAL)
                
            except Exception as e:
                logger.error(f"监控循环错误: {e}", exc_info=True)
                time.sleep(MONITOR_INTERVAL)
    
    def start(self):
        """启动监控服务"""
        if self.running:
            logger.warning("监控服务已在运行")
            return
        
        logger.info("正在启动监控服务...")
        
        # 创建新会话
        self.session_id = self.db.start_session()
        if self.session_id < 0:
            logger.error("创建会话失败")
            return
        
        # 启动鼠标监听器
        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click
        )
        self.mouse_listener.start()
        
        # 启动键盘监听器
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press
        )
        self.keyboard_listener.start()
        
        # 启动监控线程
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"监控服务已启动 - 会话ID: {self.session_id}")
    
    def stop(self):
        """停止监控服务"""
        if not self.running:
            logger.warning("监控服务未运行")
            return
        
        logger.info("正在停止监控服务...")
        
        # 停止监控循环
        self.running = False
        
        # 保存最后一次数据
        self.collect_and_save_data()
        
        # 结束会话
        if self.session_id:
            self.db.end_session(self.session_id)
            
            # 更新今日统计
            self.db.update_daily_stats(datetime.now().date())
        
        # 停止监听器
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        # 等待监控线程结束
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("监控服务已停止")
    
    def get_current_status(self) -> dict:
        """获取当前状态"""
        return {
            'running': self.running,
            'session_id': self.session_id,
            'mouse_clicks': self.mouse_clicks,
            'keyboard_presses': self.keyboard_presses,
            'window_switches': self.window_switches,
            'is_idle': self.is_idle(),
            'last_activity': self.last_activity_time.isoformat()
        }


def main():
    """主函数（用于测试）"""
    monitor = ActivityMonitor()
    
    try:
        monitor.start()
        logger.info("监控服务正在运行，按 Ctrl+C 停止...")
        
        # 保持运行
        while True:
            time.sleep(10)
            status = monitor.get_current_status()
            logger.info(f"当前状态: {status}")
    
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    
    finally:
        monitor.stop()


if __name__ == '__main__':
    main()

