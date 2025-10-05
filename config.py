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
MONITOR_INTERVAL = 60  # 监控间隔（秒），每分钟记录一次
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

