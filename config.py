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

# 鼠标距离计算配置
# 基于典型24寸 1920×1080显示器（宽约53cm）的经验值
# 可根据实际显示器调整此值
PIXELS_PER_METER = 5200  # 像素/米（约 1像素 = 0.28mm）

