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

