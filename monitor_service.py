"""
系统监控服务
实时监控鼠标、键盘、窗口和系统活动

关键设计：pynput 使用 Windows 底层钩子 (SetWindowsHookEx)，
钩子回调必须尽快返回，否则会阻塞整个系统的鼠标/键盘输入。
因此 on_mouse_move / on_mouse_click / on_key_press 回调
必须做到极致轻量：不加锁、不调用 datetime、不做任何耗时操作。

计数器使用「双缓冲」模式：
- pynput 回调写入 _active 缓冲区（无锁，纯 += 操作）
- monitor_loop 通过交换引用来原子地切换缓冲区，然后处理旧数据
- 这样回调永远不会被阻塞，数据也零丢失
"""
import time
import logging
import threading
from datetime import datetime
from typing import Optional
import psutil
from pynput import mouse, keyboard
import win32gui

from database import Database
try:
    from camera_service import CameraService
except ImportError:
    CameraService = None
from config import (
    MONITOR_INTERVAL, IDLE_THRESHOLD,
    BUSY_WEIGHTS
)

logger = logging.getLogger(__name__)


class _CounterBuffer:
    """轻量级计数器缓冲区（单线程写入，无需加锁）"""
    __slots__ = ('mouse_distance', 'mouse_clicks', 'mouse_moves',
                 'keyboard_presses', 'window_switches', 'window_title')

    def __init__(self):
        self.mouse_distance = 0.0
        self.mouse_clicks = 0
        self.mouse_moves = 0
        self.keyboard_presses = 0
        self.window_switches = 0
        self.window_title = ''

    def reset(self):
        self.mouse_distance = 0.0
        self.mouse_clicks = 0
        self.mouse_moves = 0
        self.keyboard_presses = 0
        self.window_switches = 0


class ActivityMonitor:
    """活动监控器"""

    def __init__(self):
        self.db = Database()
        self.session_id = None

        # ===== 双缓冲计数器 =====
        # _active: pynput 回调写入（无锁）
        # _pending: monitor_loop 读取后处理
        # 切换通过交换引用完成（Python 赋值是原子的）
        self._active = _CounterBuffer()
        self._pending = _CounterBuffer()

        # 鼠标位置追踪（仅在 pynput 回调中使用）
        self._last_mouse_pos = None

        # 窗口追踪
        self._last_active_window = None

        # 监听器
        self.mouse_listener = None
        self.keyboard_listener = None

        # 运行标志
        self.running = False
        self.monitor_thread = None

        # 最后活动时间戳（monotonic 比 datetime.now 快几十倍）
        self._last_activity_ts = time.monotonic()

        # 用于 stop() 时保护 collect_and_save_data 不与 monitor_loop 并发
        self._save_lock = threading.Lock()

        # 摄像头抓拍服务（opencv-python 未安装时为 None）
        self.camera_service = CameraService() if CameraService else None

    # ================================================================
    #  pynput 回调 —— 必须极致轻量，不加锁、不调 datetime
    #  Windows 底层钩子是同步的，回调阻塞 = 系统鼠标/键盘卡死
    # ================================================================

    def on_mouse_move(self, x, y):
        """鼠标移动事件（每秒数百次调用，必须尽快返回）"""
        buf = self._active  # 局部变量加速
        if self._last_mouse_pos:
            dx = x - self._last_mouse_pos[0]
            dy = y - self._last_mouse_pos[1]
            buf.mouse_distance += (dx * dx + dy * dy) ** 0.5
        self._last_mouse_pos = (x, y)
        buf.mouse_moves += 1
        self._last_activity_ts = time.monotonic()

    def on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        if pressed:
            self._active.mouse_clicks += 1
            self._last_activity_ts = time.monotonic()

    def on_key_press(self, key):
        """键盘按键事件"""
        self._active.keyboard_presses += 1
        self._last_activity_ts = time.monotonic()

    # ================================================================
    #  以下方法不在 pynput 回调中调用
    # ================================================================

    def _detect_window_switch(self):
        """检测窗口切换（在 monitor_loop 线程中调用）"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd) or ''
            if self._last_active_window and self._last_active_window != title:
                self._active.window_switches += 1
            self._last_active_window = title
            return title
        except Exception:
            return ''

    def _get_window_count(self) -> int:
        """获取可见窗口数量"""
        try:
            count = 0

            def enum_handler(hwnd, ctx):
                nonlocal count
                if win32gui.IsWindowVisible(hwnd):
                    count += 1

            win32gui.EnumWindows(enum_handler, None)
            return count
        except Exception:
            return 0

    def get_system_usage(self) -> tuple:
        """获取系统资源使用情况（非阻塞）"""
        try:
            return psutil.cpu_percent(interval=None), psutil.virtual_memory().percent
        except Exception:
            return 0, 0

    def calculate_busy_index(self, mouse_activity: float, keyboard_activity: float,
                             window_activity: float, system_activity: float) -> float:
        """计算忙碌指数（0-100）"""
        return min(100, max(0, (
            mouse_activity * BUSY_WEIGHTS['mouse_activity'] +
            keyboard_activity * BUSY_WEIGHTS['keyboard_activity'] +
            window_activity * BUSY_WEIGHTS['window_switches'] +
            system_activity * BUSY_WEIGHTS['system_usage']
        )))

    def is_idle(self) -> bool:
        """判断是否处于空闲状态"""
        return (time.monotonic() - self._last_activity_ts) > IDLE_THRESHOLD

    def _swap_buffers(self):
        """原子交换活跃/待处理缓冲区"""
        old = self._active
        self._active = self._pending
        self._pending = old
        return old

    def collect_and_save_data(self):
        """收集并保存数据（线程安全：通过 _save_lock 防止 stop 和 monitor_loop 并发调用）"""
        if not self._save_lock.acquire(blocking=False):
            return  # 另一个线程正在保存，跳过本次

        try:
            # 检测窗口切换
            active_window = self._detect_window_switch()

            # 获取系统资源
            cpu_usage, memory_usage = self.get_system_usage()

            # 交换缓冲区（原子操作，pynput 回调立即开始写入新的 _active）
            buf = self._swap_buffers()

            # 处理旧缓冲区数据
            window_count = self._get_window_count()

            interval_factor = MONITOR_INTERVAL / 60

            mouse_activity_score = min(100, (
                (buf.mouse_distance / (5000 * interval_factor) * 50) +
                (buf.mouse_clicks / (50 * interval_factor) * 30) +
                (buf.mouse_moves / (500 * interval_factor) * 20)
            ))

            keyboard_activity_score = min(100, buf.keyboard_presses / (300 * interval_factor) * 100)
            window_activity_score = min(100, buf.window_switches / (10 * interval_factor) * 100)
            system_activity_score = (cpu_usage + memory_usage) / 2

            busy_index = self.calculate_busy_index(
                mouse_activity_score, keyboard_activity_score,
                window_activity_score, system_activity_score
            )

            is_idle = self.is_idle()
            if is_idle:
                busy_index = 0

            record = {
                'timestamp': datetime.now(),
                'mouse_distance': round(buf.mouse_distance, 2),
                'mouse_clicks': buf.mouse_clicks,
                'mouse_moves': buf.mouse_moves,
                'keyboard_presses': buf.keyboard_presses,
                'window_switches': buf.window_switches,
                'active_windows': window_count,
                'cpu_usage': round(cpu_usage, 2),
                'memory_usage': round(memory_usage, 2),
                'busy_index': round(busy_index, 2),
                'is_idle': is_idle,
                'active_window_title': (active_window or '')[:200]
            }

            self.db.save_activity_record(record)

            logger.info(f"数据已保存({MONITOR_INTERVAL}s) - 忙碌指数: {busy_index:.2f}, "
                        f"鼠标: {buf.mouse_clicks}次点击/{buf.mouse_distance:.0f}px, "
                        f"键盘: {buf.keyboard_presses}次按键, "
                        f"窗口切换: {buf.window_switches}次")

            # 清空旧缓冲区以备下次交换使用
            buf.reset()

        except Exception as e:
            logger.error(f"收集和保存数据失败: {e}", exc_info=True)
        finally:
            self._save_lock.release()

    def monitor_loop(self):
        """监控循环"""
        logger.info("监控循环开始")
        psutil.cpu_percent(interval=None)

        while self.running:
            try:
                self.collect_and_save_data()

                now = datetime.now()
                if now.minute == 0 and now.second < MONITOR_INTERVAL:
                    self.db.update_daily_stats(now.date())

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

        self.session_id = self.db.start_session()
        if self.session_id < 0:
            logger.error("创建会话失败")
            return

        self.mouse_listener = mouse.Listener(
            on_move=self.on_mouse_move,
            on_click=self.on_mouse_click
        )
        self.mouse_listener.start()

        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press
        )
        self.keyboard_listener.start()

        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()

        # 启动摄像头抓拍服务
        if self.camera_service:
            self.camera_service.start()

        logger.info(f"监控服务已启动 - 会话ID: {self.session_id}")

    def stop(self):
        """停止监控服务"""
        if not self.running:
            logger.warning("监控服务未运行")
            return

        logger.info("正在停止监控服务...")

        self.running = False

        # 先等 monitor_loop 退出，避免并发 collect_and_save_data
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)

        # 停止摄像头抓拍服务
        if self.camera_service:
            self.camera_service.stop()

        # 保存最后一次数据（此时 monitor_loop 已停止，无并发风险）
        self.collect_and_save_data()

        # 结束会话
        if self.session_id is not None and self.session_id > 0:
            self.db.end_session(self.session_id)
            self.db.update_daily_stats(datetime.now().date())

        # 停止监听器
        for listener in (self.mouse_listener, self.keyboard_listener):
            if listener:
                try:
                    listener.stop()
                except Exception:
                    pass

        logger.info("监控服务已停止")

    def get_current_status(self) -> dict:
        """获取当前状态"""
        buf = self._active
        camera_status = self.camera_service.get_status() if self.camera_service else {
            'enabled': False, 'running': False, 'active_threads': 0, 'camera_ready': False
        }
        return {
            'running': self.running,
            'session_id': self.session_id,
            'mouse_clicks': buf.mouse_clicks,
            'keyboard_presses': buf.keyboard_presses,
            'window_switches': buf.window_switches,
            'is_idle': self.is_idle(),
            'last_activity': datetime.now().isoformat(),
            'camera': camera_status,
        }


def main():
    """主函数（用于测试）"""
    monitor = ActivityMonitor()

    try:
        monitor.start()
        logger.info("监控服务正在运行，按 Ctrl+C 停止...")

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
