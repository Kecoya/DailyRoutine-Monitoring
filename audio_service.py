"""
音频监听服务
- 用户可控的开始/停止监听
- 实时音频流推送至浏览器（SSE）
- Vosk 本地中文流式识别（内置 VAD，实时输出部分/最终结果）
- 保存每段语音(WAV) + 汇总文本(transcript.txt) 到会话目录

线程模型：
- sounddevice 回调线程：仅「拷贝并入队」，绝不阻塞
- 流式工作线程：消费队列 → 推流浏览器 + 喂给 Vosk 识别器 + 处理 partial/final
  （Vosk accept_waveform 是非阻塞且极快的，无需独立 ASR 线程）

Vosk 选用原因：纯本地、无 torch 依赖（Python 3.13 上 torch 的 c10.dll 易崩）、
内置 VAD 与流式识别、实时输出部分结果，适合实时监听场景。
"""
import os
import wave
import json
import time
import base64
import logging
import threading
import queue
from datetime import datetime

import numpy as np

from config import (
    AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_CHUNK_MS,
    AUDIO_ASR_MODELS_DIR, AUDIO_MODEL_DIR,
    AUDIO_PARTIAL_RESULTS,
    AUDIO_SESSIONS_DIR,
)

logger = logging.getLogger(__name__)


class AudioService:
    """音频监听服务（Vosk 后端）"""

    def __init__(self):
        self.is_listening = False

        # sounddevice 输入流
        self.stream = None

        # 音频块队列（回调 → 工作线程）
        self._audio_queue = None
        self._worker_thread = None

        # Vosk 识别器（仅工作线程访问）
        self._model = None
        self._recognizer = None
        self._model_lock = threading.Lock()
        self._model_loaded = False

        # SSE 订阅者
        self._subscribers = []
        self._sub_lock = threading.Lock()

        # 当前一句话的音频累积（用于最终落盘 WAV）
        self._utterance_chunks = []
        self._in_utterance = False
        self._utterance_start = None
        self._utterance_counter = 0

        # 会话状态
        self.session_id = None
        self.session_dir = None
        self.transcript_path = None

    # ================================================================
    #  SSE 订阅
    # ================================================================

    def subscribe(self):
        """订阅实时事件流，返回一个 queue（元素为已格式化的 SSE 字符串）"""
        q = queue.Queue(maxsize=1000)
        with self._sub_lock:
            self._subscribers.append(q)
        self._emit_to(q, 'status', self.get_status())
        return q

    def unsubscribe(self, q):
        with self._sub_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def _broadcast(self, event, data):
        msg = self._format_sse(event, data)
        with self._sub_lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass

    def _emit_to(self, q, event, data):
        try:
            q.put_nowait(self._format_sse(event, data))
        except queue.Full:
            pass

    @staticmethod
    def _format_sse(event, data):
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    # ================================================================
    #  Vosk 模型
    # ================================================================

    def _resolve_model_path(self):
        """
        返回传给 Vosk 的模型路径。
        注意：Vosk(Kaldi) 在 Windows 上对含非 ASCII 字符（如中文）的「绝对路径」会加载失败，
        但相对路径不受影响。项目路径含中文，故优先返回相对 cwd 的 ASCII 相对路径。
        """
        abs_path = os.path.join(AUDIO_ASR_MODELS_DIR, AUDIO_MODEL_DIR)
        try:
            rel = os.path.relpath(abs_path, os.getcwd())
            if rel.isascii():
                return rel
        except Exception:
            pass
        return abs_path

    def _ensure_model(self):
        """加载 Vosk 模型（仅一次）。模型不存在时抛出带提示的异常。"""
        with self._model_lock:
            if self._model_loaded:
                return
            path = self._resolve_model_path()
            if not os.path.isdir(path):
                raise FileNotFoundError(
                    f"Vosk 中文模型未找到：{path}\n"
                    f"请下载 {AUDIO_MODEL_DIR}.zip 解压到 {AUDIO_ASR_MODELS_DIR}/\n"
                    f"下载地址：https://alphacephei.com/vosk/models/{AUDIO_MODEL_DIR}.zip"
                )
            from vosk import Model
            logger.info(f"正在加载 Vosk 模型：{path}")
            self._model = Model(path)
            self._model_loaded = True
            logger.info("Vosk 模型加载完成")
            self._broadcast('status', self.get_status())

    # ================================================================
    #  生命周期
    # ================================================================

    def start_listening(self):
        if self.is_listening:
            return {'success': False, 'message': '已在监听中'}
        if not self._check_sounddevice():
            return {'success': False, 'message': '未安装 sounddevice（pip install sounddevice）'}

        # 先确保模型可用
        try:
            self._ensure_model()
        except Exception as e:
            logger.error(f"模型加载失败：{e}")
            return {'success': False, 'message': str(e)}

        from vosk import KaldiRecognizer
        self._recognizer = KaldiRecognizer(self._model, AUDIO_SAMPLE_RATE)

        # 会话目录
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_dir = os.path.join(AUDIO_SESSIONS_DIR, self.session_id)
        os.makedirs(self.session_dir, exist_ok=True)
        self.transcript_path = os.path.join(self.session_dir, 'transcript.txt')

        # 重置状态
        self._utterance_chunks = []
        self._in_utterance = False
        self._utterance_start = None
        self._utterance_counter = 0

        self._audio_queue = queue.Queue(maxsize=200)

        try:
            import sounddevice as sd
            block = int(AUDIO_SAMPLE_RATE * AUDIO_CHUNK_MS / 1000)
            self.stream = sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype='int16',
                blocksize=block,
                callback=self._audio_callback,
            )
            self.stream.start()
        except Exception as e:
            logger.error(f"打开麦克风失败：{e}", exc_info=True)
            self.is_listening = False
            self._recognizer = None
            return {'success': False, 'message': f'打开麦克风失败：{e}'}

        self.is_listening = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        logger.info(f"音频监听已开始，会话: {self.session_id}")
        self._broadcast('status', self.get_status())
        return {
            'success': True,
            'session_id': self.session_id,
            'session_dir': self.session_dir,
        }

    def stop_listening(self):
        if not self.is_listening:
            return {'success': False, 'message': '未在监听'}

        self.is_listening = False

        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.error(f"关闭音频流失败：{e}")
            self.stream = None

        if self._audio_queue is not None:
            self._audio_queue.put(None)

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        self._worker_thread = None

        # 刷新识别器内可能残留的最终结果
        if self._recognizer is not None:
            try:
                final = json.loads(self._recognizer.FinalResult())
                text = (final.get('text') or '').strip()
                if text:
                    self._commit_utterance(text)
            except Exception:
                pass
            self._recognizer = None

        logger.info("音频监听已停止")
        self._broadcast('status', self.get_status())
        return {'success': True}

    @staticmethod
    def _check_sounddevice():
        try:
            import sounddevice  # noqa: F401
            return True
        except ImportError:
            return False

    # ================================================================
    #  音频回调（必须极轻量）
    # ================================================================

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_listening:
            return
        try:
            self._audio_queue.put_nowait(indata[:, 0].copy())
        except queue.Full:
            pass

    # ================================================================
    #  工作线程：推流 + Vosk 识别
    # ================================================================

    def _worker_loop(self):
        while self.is_listening:
            try:
                chunk = self._audio_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            if chunk is None:
                break

            # 1) 推流到浏览器
            try:
                b64 = base64.b64encode(chunk.tobytes()).decode('ascii')
                self._broadcast('audio', {'data': b64, 'sr': AUDIO_SAMPLE_RATE})
            except Exception as e:
                logger.error(f"推送音频流失败：{e}")

            # 2) 喂给 Vosk
            if self._recognizer is None:
                continue
            try:
                chunk_bytes = chunk.tobytes()
                if self._recognizer.AcceptWaveform(chunk_bytes):
                    # 一句话结束 → 最终结果
                    result = json.loads(self._recognizer.Result())
                    text = (result.get('text') or '').strip()
                    if text:
                        self._commit_utterance(text, tail_chunk=chunk)
                    else:
                        # 空最终结果（噪声/静音段），丢弃累积
                        self._utterance_chunks = []
                        self._in_utterance = False
                        self._utterance_start = None
                else:
                    # 部分结果
                    if AUDIO_PARTIAL_RESULTS:
                        partial = json.loads(self._recognizer.PartialResult()).get('partial', '')
                        if partial:
                            if not self._in_utterance:
                                self._in_utterance = True
                                self._utterance_start = datetime.now()
                                self._utterance_chunks = []
                            self._utterance_chunks.append(chunk)
                            self._broadcast('partial', {
                                'text': partial,
                                'timestamp': self._utterance_start.strftime('%H:%M:%S'),
                            })
                        else:
                            # 静音中：若之前在说话但还没 final，继续累积（保留自然停顿）
                            if self._in_utterance:
                                self._utterance_chunks.append(chunk)
            except Exception as e:
                logger.error(f"识别处理失败：{e}", exc_info=True)

    def _commit_utterance(self, text, tail_chunk=None):
        """一句话结束：保存 WAV + 写文本 + 推送最终文字"""
        self._utterance_counter += 1
        idx = self._utterance_counter
        start_ts = self._utterance_start or datetime.now()

        audio = (np.concatenate(self._utterance_chunks).astype(np.int16)
                 if self._utterance_chunks else np.zeros(0, dtype=np.int16))

        # 重置
        self._utterance_chunks = []
        self._in_utterance = False
        self._utterance_start = None

        # 存 WAV（过短的段跳过存盘但仍显示文字）
        wav_name = None
        if len(audio) >= int(AUDIO_SAMPLE_RATE * 0.3):
            wav_name = f"seg_{idx:04d}_{start_ts.strftime('%H%M%S')}.wav"
            wav_path = os.path.join(self.session_dir, wav_name)
            try:
                with wave.open(wav_path, 'wb') as wf:
                    wf.setnchannels(AUDIO_CHANNELS)
                    wf.setsampwidth(2)
                    wf.setframerate(AUDIO_SAMPLE_RATE)
                    wf.writeframes(audio.tobytes())
            except Exception as e:
                logger.error(f"保存 WAV 失败：{e}")
                wav_name = None

        # 写文本
        line = f"[{start_ts.strftime('%H:%M:%S')}] {text}\n"
        try:
            with open(self.transcript_path, 'a', encoding='utf-8') as f:
                f.write(line)
        except Exception as e:
            logger.error(f"写入文本失败：{e}")

        # 推送最终文字
        self._broadcast('transcript', {
            'timestamp': start_ts.strftime('%H:%M:%S'),
            'text': text,
            'index': idx,
            'audio_url': f"/audio_sessions/{self.session_id}/{wav_name}" if wav_name else None,
        })
        dur = len(audio) / AUDIO_SAMPLE_RATE
        logger.info(f"转写段 {idx} ({dur:.1f}s): {text[:80]}")

    # ================================================================
    #  状态查询
    # ================================================================

    def get_status(self):
        return {
            'enabled': True,
            'listening': self.is_listening,
            'session_id': self.session_id,
            'session_dir': self.session_dir,
            'model_loaded': self._model_loaded,
        }
