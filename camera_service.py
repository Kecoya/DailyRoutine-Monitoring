"""
摄像头抓拍服务
提供时间段定时抓拍、固定时间点永久抓拍、GIF动图生成等功能。
从 standalone 抓拍工具移植，去掉 GUI/CLI/托盘等独立运行组件，
适配监控系统的 config 常量和日志模式。
"""
import os
import glob
import time
import logging
import threading
import schedule
import numpy as np
from datetime import datetime, time as dt_time, timedelta

import cv2
from PIL import Image, ImageDraw, ImageFont

from config import (
    CAPTURE_ENABLED, CAPTURE_CAMERA_ID,
    CAPTURE_TEMP_DIR, CAPTURE_PERMANENT_DIR, CAPTURE_GIF_DIR,
    CAPTURE_TIME_RANGES, CAPTURE_FIXED_TIMES,
    CAPTURE_MAX_TEMP_FILES, CAPTURE_AUTO_CLEANUP, CAPTURE_CLEANUP_DAYS,
    CAPTURE_GIF_FPS, CAPTURE_WARMUP_FRAMES,
    CAPTURE_TIMESTAMP_ENABLED, CAPTURE_TIMESTAMP_SCALE,
)

logger = logging.getLogger(__name__)


class CameraService:
    """摄像头抓拍服务"""

    def __init__(self):
        self.camera = None
        self.camera_lock = threading.Lock()
        self.is_running = False
        self.capture_threads = []
        self.schedule_thread = None
        self._cleanup_done_this_hour = False
        self._main_thread = None
        # 抓拍进行中标志（仅在 _capture_one 执行期间为 True，供 get_status 反映状态）
        self._capture_in_progress = False

    # ================================================================
    #  摄像头抓拍（每次独立开关，全程持锁）
    # ================================================================

    def _capture_one(self, is_permanent, timestamp=None):
        """
        原子地完成一次抓拍：打开 → 预热 → 拍照 → 保存 → 释放。

        全程持有 camera_lock，保证与其他抓拍（时间段/固定时间/手动）互斥，
        互不打断。关键设计：每次抓拍都重新打开并立即释放摄像头，使摄像头
        活动指示灯只在抓拍瞬间（约 1-2 秒）点亮，而非整个时间段持续长亮。

        Returns:
            (filepath, timestamp): 成功；失败返回 (None, None)
        """
        if timestamp is None:
            timestamp = datetime.now()

        frame = self._grab_frame()
        if frame is None:
            return None, None

        filepath = self.save_image(frame, timestamp=timestamp, is_permanent=is_permanent)
        return filepath, timestamp

    def _grab_frame(self):
        """打开 → 预热 → 读取一帧 → 释放，全程持锁。失败返回 None。"""
        with self.camera_lock:
            try:
                cap = cv2.VideoCapture(CAPTURE_CAMERA_ID)
                if not cap.isOpened():
                    logger.error(f"无法打开摄像头 {CAPTURE_CAMERA_ID}")
                    try:
                        cap.release()
                    except Exception:
                        pass
                    return None

                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_FPS, 30)
                self.camera = cap
                self._capture_in_progress = True

                try:
                    # 预热：丢弃若干帧让自动曝光/白平衡稳定，避免首帧过暗
                    for _ in range(CAPTURE_WARMUP_FRAMES):
                        cap.read()
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        logger.error("无法读取摄像头画面")
                        return None
                    return frame
                finally:
                    self._capture_in_progress = False
                    try:
                        cap.release()
                    except Exception:
                        pass
                    self.camera = None
            except Exception as e:
                logger.error(f"摄像头抓取失败：{e}")
                self._capture_in_progress = False
                self.camera = None
                return None

    def release_camera(self):
        """释放摄像头资源（线程安全）。stop() 时兜底调用。"""
        with self.camera_lock:
            if self.camera:
                try:
                    self.camera.release()
                    logger.info("摄像头资源已释放")
                except Exception as e:
                    logger.error(f"释放摄像头时出错：{e}")
                finally:
                    self.camera = None

    # ================================================================
    #  图片处理
    # ================================================================

    def _get_font(self, size):
        """加载 TrueType 字体，按优先级尝试常见字体，失败则回退默认字体"""
        for name in ('arial.ttf', 'ARIAL.TTF', 'msyh.ttc', 'simhei.ttf',
                     'DejaVuSans.ttf'):
            try:
                return ImageFont.truetype(name, size)
            except (IOError, OSError):
                continue
        return ImageFont.load_default()

    def add_timestamp(self, frame, timestamp=None):
        """
        在照片顶部拼接一层白带显示拍摄时间，不在照片本体上做任何标注。
        白带在上、照片在下，整体高度 = 白带高度 + 原图高度。
        """
        if not CAPTURE_TIMESTAMP_ENABLED:
            return frame

        if timestamp is None:
            timestamp = datetime.now()

        # OpenCV 帧 (BGR) -> PIL 图像 (RGB)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        photo = Image.fromarray(rgb)
        w, h = photo.size

        # 字号按图像宽度自适应，CAPTURE_TIMESTAMP_SCALE 可微调
        font_size = max(14, int(w * 0.035 * CAPTURE_TIMESTAMP_SCALE))
        font = self._get_font(font_size)

        text = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        band_height = max(text_h + 16, int(h * 0.05))

        # 白带 + 黑色文字（左对齐、垂直居中）
        band = Image.new('RGB', (w, band_height), color='white')
        draw = ImageDraw.Draw(band)
        text_y = (band_height - text_h) // 2 - bbox[1]
        draw.text((12, text_y), text, fill='black', font=font)

        # 拼接：白带在上，照片在下
        combined = Image.new('RGB', (w, h + band_height), color='white')
        combined.paste(band, (0, 0))
        combined.paste(photo, (0, band_height))

        # 转回 BGR 以便后续 cv2.imencode 保存
        return cv2.cvtColor(np.array(combined), cv2.COLOR_RGB2BGR)

    def save_image(self, frame, timestamp=None, is_permanent=False):
        """
        保存图片到本地

        Returns:
            str: 保存的文件路径，失败返回 None
        """
        if timestamp is None:
            timestamp = datetime.now()

        frame_with_timestamp = self.add_timestamp(frame, timestamp)

        save_dir = CAPTURE_PERMANENT_DIR if is_permanent else CAPTURE_TEMP_DIR
        prefix = "permanent" if is_permanent else "temp"
        filename = f"{prefix}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(save_dir, filename)

        try:
            # 注意：cv2.imwrite 在 Windows 上对含非 ASCII 字符的路径（如中文）会静默失败。
            # 改用 imencode + numpy.tofile 绕过 OpenCV 的文件 I/O。
            success, buffer = cv2.imencode('.jpg', frame_with_timestamp)
            if not success:
                logger.error(f"保存图片失败：cv2.imencode 失败（路径：{filepath}）")
                return None
            buffer.tofile(filepath)
            save_type = "永久" if is_permanent else "临时"
            logger.info(f"{save_type}图片已保存：{filepath}")
            return filepath
        except Exception as e:
            logger.error(f"保存图片失败：{e}")
            return None

    # ================================================================
    #  GIF 生成
    # ================================================================

    def create_gif_from_images(self, time_range, session_start):
        """从临时图片创建 GIF 动图"""
        try:
            logger.info(f"开始生成GIF，时间段：{time_range['start']}-{time_range['end']}")

            pattern = os.path.join(CAPTURE_TEMP_DIR,
                                   f"temp_{session_start.strftime('%Y%m%d')}*.jpg")
            image_files = glob.glob(pattern)
            image_files.sort()

            if len(image_files) < 2:
                logger.warning(f"时间段 {time_range['start']}-{time_range['end']} "
                               f"图片数量不足（{len(image_files)}），无法生成GIF")
                return None

            # 过滤出该时间段内的图片
            start_time = dt_time.fromisoformat(time_range["start"])
            end_time = dt_time.fromisoformat(time_range["end"])
            session_date = session_start.date()

            filtered_files = []
            for filepath in image_files:
                try:
                    filename = os.path.basename(filepath)
                    if filename.startswith('temp_') and filename.endswith('.jpg'):
                        time_part = filename[5:-4]
                        file_datetime = datetime.strptime(time_part, '%Y%m%d_%H%M%S')
                        file_time = file_datetime.time()
                        file_date = file_datetime.date()

                        if file_date == session_date and start_time <= file_time <= end_time:
                            filtered_files.append(filepath)
                except (IndexError, ValueError):
                    continue

            if len(filtered_files) < 2:
                logger.warning(f"时间段 {time_range['start']}-{time_range['end']} "
                               f"有效图片数量不足（{len(filtered_files)}），无法生成GIF")
                return None

            # 读取图片并转换为 PIL 格式
            images = []
            for filepath in filtered_files:
                try:
                    # 注意：cv2.imread 在 Windows 上对含非 ASCII 字符的路径会返回 None。
                    # 改用 np.fromfile + cv2.imdecode 绕过 OpenCV 的文件 I/O。
                    data = np.fromfile(filepath, dtype=np.uint8)
                    cv_img = cv2.imdecode(data, cv2.IMREAD_COLOR) if data.size else None
                    if cv_img is not None:
                        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
                        pil_img = Image.fromarray(rgb_img)

                        # 调整大小以减小 GIF 文件体积
                        width, height = pil_img.size
                        if width > 800:
                            new_width = 800
                            new_height = int(height * new_width / width)
                            pil_img = pil_img.resize(
                                (new_width, new_height), Image.Resampling.LANCZOS
                            )

                        images.append(pil_img)
                except Exception as e:
                    logger.error(f"处理图片时出错：{e}")
                    continue

            if len(images) < 2:
                logger.warning(f"时间段 {time_range['start']}-{time_range['end']} "
                               f"成功处理的图片数量不足")
                return None

            # 生成 GIF
            gif_filename = (f"gif_{session_start.strftime('%Y%m%d')}_"
                            f"{time_range['start'].replace(':', '')}_"
                            f"{time_range['end'].replace(':', '')}.gif")
            gif_filepath = os.path.join(CAPTURE_GIF_DIR, gif_filename)

            duration = int(1000 / CAPTURE_GIF_FPS)  # 毫秒

            images[0].save(
                gif_filepath,
                format='GIF',
                append_images=images[1:],
                save_all=True,
                duration=duration,
                loop=0
            )

            logger.info(f"GIF动图已生成：{gif_filepath}（包含 {len(images)} 帧）")
            return gif_filepath

        except Exception as e:
            logger.error(f"生成GIF时出错：{e}", exc_info=True)
            return None

    # ================================================================
    #  时间判断与文件清理
    # ================================================================

    def is_within_time_ranges(self):
        """检查当前时间是否在任何配置的时间段内"""
        current_time = datetime.now().time()

        for time_range in CAPTURE_TIME_RANGES:
            start_time = dt_time.fromisoformat(time_range["start"])
            end_time = dt_time.fromisoformat(time_range["end"])

            # 处理跨天的情况
            if start_time > end_time:
                if current_time >= start_time or current_time <= end_time:
                    return True, time_range
            else:
                if start_time <= current_time <= end_time:
                    return True, time_range

        return False, None

    def cleanup_old_files(self):
        """清理过期的临时文件"""
        if not CAPTURE_AUTO_CLEANUP:
            return

        cutoff_date = datetime.now() - timedelta(days=CAPTURE_CLEANUP_DAYS)
        deleted_count = 0

        try:
            for filename in os.listdir(CAPTURE_TEMP_DIR):
                filepath = os.path.join(CAPTURE_TEMP_DIR, filename)
                if os.path.isfile(filepath):
                    try:
                        date_part = filename.split('_')[1:3]
                        file_date = datetime.strptime('_'.join(date_part), '%Y%m%d_%H%M%S')

                        if file_date < cutoff_date:
                            os.remove(filepath)
                            deleted_count += 1
                    except (IndexError, ValueError):
                        continue

            if deleted_count > 0:
                logger.info(f"已清理 {deleted_count} 个过期临时文件")

        except Exception as e:
            logger.error(f"清理文件时出错：{e}")

    # ================================================================
    #  抓拍工作线程
    # ================================================================

    def temporary_capture_worker(self, time_range):
        """
        时间段抓拍工作线程：每 interval 秒抓拍一张。
        每次抓拍独立打开→预热→拍照→释放摄像头，使指示灯只在抓拍瞬间点亮
        （约 1-2 秒），而非整个时间段持续长亮。
        """
        interval = time_range["interval"]
        capture_count = 0
        session_start = datetime.now()

        logger.info(f"开始时间段抓拍：{time_range['start']}-{time_range['end']}，"
                     f"间隔{interval}秒（每次抓拍独立开关摄像头）")

        try:
            while self.is_running:
                in_range, current_range = self.is_within_time_ranges()
                if not in_range or current_range["start"] != time_range["start"]:
                    logger.info(f"时间段 {time_range['start']}-{time_range['end']} 结束")
                    break

                if capture_count >= CAPTURE_MAX_TEMP_FILES:
                    logger.info(f"已达到最大临时抓拍数量 {CAPTURE_MAX_TEMP_FILES}")
                    break

                filepath, _ = self._capture_one(is_permanent=False)
                if filepath:
                    capture_count += 1

                time.sleep(interval)

        finally:
            if capture_count >= 2:
                logger.info(f"开始为时间段 {time_range['start']}-{time_range['end']} 生成GIF...")
                gif_path = self.create_gif_from_images(time_range, session_start)
                if gif_path:
                    logger.info(f"时间段 {time_range['start']}-{time_range['end']} GIF已保存")
                else:
                    logger.warning(f"时间段 {time_range['start']}-{time_range['end']} GIF生成失败")
            else:
                logger.info(f"时间段 {time_range['start']}-{time_range['end']} "
                            f"图片数量不足（{capture_count}），跳过GIF生成")

    def fixed_time_capture(self, time_info):
        """固定时间点拍照（永久保存）"""
        logger.info(f"执行固定时间拍照：{time_info['time']} - {time_info['description']}")
        filepath, _ = self._capture_one(is_permanent=True)
        if filepath:
            logger.info("固定时间拍照完成")
        else:
            logger.error(f"固定时间拍照失败：{time_info['time']}")

    def capture_now(self, is_permanent=False):
        """
        手动立即抓拍一张（供 Web "立即抓拍" 按钮调用）。
        独立打开→预热→拍照→释放，与时间段/固定时间抓拍通过 camera_lock 互斥，互不打断。

        Returns:
            dict: 成功时含 filename/url/timestamp；失败时含 success=False 和 message
        """
        timestamp = datetime.now()
        filepath, ts = self._capture_one(is_permanent=is_permanent, timestamp=timestamp)
        if not filepath:
            return {'success': False, 'message': '抓拍失败（摄像头可能被占用或设备不存在）'}

        filename = os.path.basename(filepath)
        logger.info(f"手动立即抓拍成功：{filepath}")
        return {
            'success': True,
            'filename': filename,
            'url': f'/captures/{filename}',
            'timestamp': ts.isoformat(),
            'capture_type': 'permanent' if is_permanent else 'temp',
        }

    def _setup_schedule(self):
        """设置固定时间拍照计划"""
        schedule.clear()

        for time_info in CAPTURE_FIXED_TIMES:
            schedule.every().day.at(time_info["time"]).do(
                self.fixed_time_capture, time_info=time_info
            )
            logger.info(f"已设置固定拍照时间：{time_info['time']} - {time_info['description']}")

    def _schedule_worker(self):
        """调度工作线程"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)

    def _main_loop(self):
        """
        主循环：监控时间段状态，按需启动抓拍线程。
        注：摄像头现由 _capture_one 每次独立开关，本循环不再负责摄像头的
        打开/释放（既避免了长时间长亮指示灯，也消除了相关的竞态）。
        """
        logger.info("摄像头抓拍主循环已启动")

        try:
            while self.is_running:
                in_range, time_range = self.is_within_time_ranges()

                if in_range:
                    thread_already_running = any(
                        t.is_alive() for t in self.capture_threads
                        if hasattr(t, 'time_range_start')
                        and t.time_range_start == time_range["start"]
                    )

                    if not thread_already_running:
                        logger.info(f"进入抓拍时间段 {time_range['start']}-{time_range['end']}，"
                                    f"启动抓拍线程")
                        thread = threading.Thread(
                            target=self.temporary_capture_worker,
                            args=(time_range,),
                            daemon=True
                        )
                        thread.time_range_start = time_range["start"]
                        thread.start()
                        self.capture_threads.append(thread)

                # 清理已结束的线程
                self.capture_threads = [t for t in self.capture_threads if t.is_alive()]

                # 每小时清理一次过期文件
                current_min = datetime.now().minute
                if current_min == 0 and not self._cleanup_done_this_hour:
                    self.cleanup_old_files()
                    self._cleanup_done_this_hour = True
                elif current_min != 0:
                    self._cleanup_done_this_hour = False

                time.sleep(30)

        except Exception as e:
            logger.error(f"摄像头抓拍主循环异常：{e}", exc_info=True)

    # ================================================================
    #  服务生命周期
    # ================================================================

    def start(self):
        """启动摄像头抓拍服务"""
        if not CAPTURE_ENABLED:
            logger.info("摄像头抓拍功能已禁用（CAPTURE_ENABLED = False）")
            return

        if self.is_running:
            logger.warning("摄像头抓拍服务已在运行")
            return

        self.is_running = True

        # 设置固定时间拍照调度
        self._setup_schedule()
        self.schedule_thread = threading.Thread(
            target=self._schedule_worker, daemon=True
        )
        self.schedule_thread.start()

        # 启动主循环线程
        self._main_thread = threading.Thread(
            target=self._main_loop, daemon=True
        )
        self._main_thread.start()

        logger.info("摄像头抓拍服务已启动")

    def stop(self):
        """停止摄像头抓拍服务"""
        if not self.is_running:
            return

        logger.info("正在停止摄像头抓拍服务...")
        self.is_running = False

        # 清理调度任务
        schedule.clear()

        # 等待线程结束
        for thread in self.capture_threads:
            if thread.is_alive():
                thread.join(timeout=2)
        if self._main_thread and self._main_thread.is_alive():
            self._main_thread.join(timeout=5)
        if self.schedule_thread and self.schedule_thread.is_alive():
            self.schedule_thread.join(timeout=2)

        # 释放摄像头
        self.release_camera()

        cv2.destroyAllWindows()
        logger.info("摄像头抓拍服务已停止")

    # ================================================================
    #  状态查询（供 Flask API 使用）
    # ================================================================

    def get_status(self) -> dict:
        """获取当前抓拍服务状态。camera_ready 仅在抓拍瞬间（持锁期间）为 True。"""
        return {
            'enabled': CAPTURE_ENABLED,
            'running': self.is_running,
            'active_threads': sum(1 for t in self.capture_threads if t.is_alive()),
            'camera_ready': self._capture_in_progress,
        }

    def get_recent_captures(self, capture_type='temp', limit=20):
        """获取最近的抓拍文件列表"""
        if capture_type == 'permanent':
            directory = CAPTURE_PERMANENT_DIR
            prefix = 'permanent_'
        else:
            directory = CAPTURE_TEMP_DIR
            prefix = 'temp_'

        if not os.path.exists(directory):
            return []

        pattern = os.path.join(directory, f'{prefix}*.jpg')
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)
        files = files[:limit]

        result = []
        for f in files:
            filename = os.path.basename(f)
            stat = os.stat(f)
            try:
                time_part = filename[len(prefix):-4]
                ts = datetime.strptime(time_part, '%Y%m%d_%H%M%S')
            except ValueError:
                ts = None

            result.append({
                'filename': filename,
                'url': f'/captures/{filename}',
                'timestamp': ts.isoformat() if ts else None,
                'size_kb': round(stat.st_size / 1024, 1),
                'type': capture_type,
            })
        return result

    def get_recent_gifs(self, limit=20):
        """获取最近的 GIF 动图列表"""
        if not os.path.exists(CAPTURE_GIF_DIR):
            return []

        pattern = os.path.join(CAPTURE_GIF_DIR, 'gif_*.gif')
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)
        files = files[:limit]

        result = []
        for f in files:
            filename = os.path.basename(f)
            stat = os.stat(f)
            result.append({
                'filename': filename,
                'url': f'/captures/{filename}',
                'size_kb': round(stat.st_size / 1024, 1),
            })
        return result
