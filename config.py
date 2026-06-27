"""
配置文件
"""
import os

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# 摄像头抓拍目录
CAPTURE_TEMP_DIR = os.path.join(DATA_DIR, 'captures', 'temp_captures')
CAPTURE_PERMANENT_DIR = os.path.join(DATA_DIR, 'captures', 'permanent_captures')
CAPTURE_GIF_DIR = os.path.join(DATA_DIR, 'captures', 'gif_animations')
os.makedirs(CAPTURE_TEMP_DIR, exist_ok=True)
os.makedirs(CAPTURE_PERMANENT_DIR, exist_ok=True)
os.makedirs(CAPTURE_GIF_DIR, exist_ok=True)

# 音频监听目录（每次监听一个会话子目录，含 WAV 段 + transcript.txt）
AUDIO_SESSIONS_DIR = os.path.join(DATA_DIR, 'audio_sessions')
os.makedirs(AUDIO_SESSIONS_DIR, exist_ok=True)

# Vosk 本地 ASR 模型目录（放在 data/asr_models/ 下）
AUDIO_ASR_MODELS_DIR = os.path.join(DATA_DIR, 'asr_models')
os.makedirs(AUDIO_ASR_MODELS_DIR, exist_ok=True)

# 数据库配置
DATABASE_PATH = os.path.join(DATA_DIR, 'activity.db')

# 监控配置
# 注意：鼠标监听器是实时工作的，MONITOR_INTERVAL只影响数据保存频率
# 鼠标移动距离在每次移动时都会实时累加，不受此间隔影响
MONITOR_INTERVAL = 60  # 监控间隔（秒），数据保存频率
IDLE_THRESHOLD = 10 * 60  # 空闲阈值（秒），10分钟无活动视为空闲
NAP_TIME_START = 13  # 午休开始时间（小时）
NAP_TIME_END = 14.5  # 午休结束时间（小时）

# Web服务配置
WEB_HOST = '127.0.0.1'
WEB_PORT = 5000
DEBUG_MODE = True

# 忙碌度计算权重配置
BUSY_WEIGHTS = {
    'mouse_activity': 0.30,  # 鼠标活动权重
    'keyboard_activity': 0.30,  # 键盘活动权重
    'window_switches': 0.20,  # 窗口切换权重
    'system_usage': 0.20  # 系统资源使用权重
}

# 日志配置
LOG_FILE = os.path.join(LOG_DIR, 'monitor.log')
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 报表配置
CHART_DPI = 100
CHART_FIGSIZE = (12, 6)
HEATMAP_FIGSIZE = (14, 8)

# 数据保留配置
DATA_RETENTION_DAYS = 365  # 数据保留天数，默认保留一年

# 实验室坐班时长配置（小时）
# 用户可自定义每日标准工作时长，默认8.5小时
# 用于计算工作效率和打卡情况分析
LAB_WORK_HOURS = 8.5  # 默认实验室坐班时长（小时）

# 鼠标距离计算配置
# 基于典型24寸 1920×1080显示器（宽约53cm）的经验值
# 可根据实际显示器调整此值
PIXELS_PER_METER = 5200  # 像素/米（约 1像素 = 0.28mm）

# ===== 摄像头抓拍配置 =====
CAPTURE_ENABLED = True          # 是否启用摄像头抓拍功能
CAPTURE_CAMERA_ID = 0           # 摄像头设备 ID

# 时间段抓拍（在指定时间段内按指定间隔抓拍，保存为临时文件，结束时生成GIF）
CAPTURE_TIME_RANGES = [
    {"start": "11:30", "end": "14:30", "interval": 60},
    {"start": "17:30", "end": "18:30", "interval": 60},
    {"start": "21:30", "end": "23:59", "interval": 60},
]

# 固定时间点抓拍（永久保存）
CAPTURE_FIXED_TIMES = [
    {"time": "08:50", "description": "morning"},
    {"time": "14:50", "description": "noon"},
    {"time": "19:50", "description": "night"},
]

# 临时文件管理
CAPTURE_MAX_TEMP_FILES = 1000      # 单个时间段最大临时抓拍数量
CAPTURE_AUTO_CLEANUP = True        # 是否自动清理过期临时文件
CAPTURE_CLEANUP_DAYS = 7           # 临时文件保留天数

# GIF 动图配置
CAPTURE_GIF_FPS = 24               # GIF 帧率

# 摄像头预热帧数
# 摄像头刚打开时自动曝光/白平衡/补光灯尚未稳定，首帧往往过暗。
# 抓拍前读取并丢弃若干帧可解决。每帧约 33ms，25 帧 ≈ 0.8 秒。
CAPTURE_WARMUP_FRAMES = 25

# 时间信息标注配置
# 在照片顶部拼接一层白带显示拍摄时间（不在照片本体上做任何标注）
CAPTURE_TIMESTAMP_ENABLED = True           # 是否拼接时间信息白带
CAPTURE_TIMESTAMP_SCALE = 1.0              # 白带文字字号缩放（相对自适应基准）

# ===== 音频监听配置 =====
# 用户可控的开始/停止监听；实时音频推流到浏览器 + 实时中文转写
AUDIO_ENABLED = True                       # 是否启用音频监听功能
AUDIO_DEVICE = None                        # 输入设备索引；None=系统默认。可在 Web 界面下拉选择
AUDIO_SAMPLE_RATE = 16000                  # 采样率（16kHz 足够语音识别）
AUDIO_CHANNELS = 1                         # 声道数（单声道即可）
AUDIO_CHUNK_MS = 100                       # 每个音频块时长（毫秒），用于推流和 VAD

# VAD（语音活动检测）由 Vosk 模型内置处理，以下为录音分段与转写的辅助参数
AUDIO_MIN_SEGMENT_SEC = 0.3                # 单段最小时长（秒），过短不存盘（仍显示文字）

# ASR（语音识别）参数 —— Vosk 本地模型（无 torch 依赖，Python 3.13 友好）
AUDIO_MODEL_DIR = 'vosk-model-small-cn-0.22'  # 中文模型目录名；改 'vosk-model-cn-0.22' 可用大模型(更准,1.3GB)
AUDIO_PARTIAL_RESULTS = True               # 是否推送实时部分识别结果（边说边显示）

# 声音触发转写：监听期间持续 RMS 检测，检测到较大声音自动开启转写，
# 静音超过冷却时间自动关闭转写（省算力）。需先开始监听。
AUDIO_SOUND_TRIGGER = 0.05                 # RMS 阈值(0-1)，超过视为"有较大声音"，触发转写
AUDIO_SOUND_COOLDOWN = 3.0                 # 连续静音多少秒后自动关闭转写

# ===== 在场检测配置（摄像头） =====
# 开启后每隔 N 秒拍一张照，用 Haar 级联(纯CPU,无深度学习)检测是否有人脸正对屏幕。
PRESENCE_DIR = os.path.join(DATA_DIR, 'presence')
os.makedirs(PRESENCE_DIR, exist_ok=True)
PRESENCE_INTERVAL_SEC = 10                 # 检测间隔（秒）
PRESENCE_FRAME_WIDTH = 480                 # 检测前缩放宽度（越小越省CPU，480足够识别人脸）
PRESENCE_FACE_MINSIZE = 30                 # 人脸检测最小尺寸（像素，缩放后坐标系）

