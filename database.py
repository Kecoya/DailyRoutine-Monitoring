"""
数据库模型和数据访问层
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建活动记录表（每分钟一条记录）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                mouse_distance REAL DEFAULT 0,
                mouse_clicks INTEGER DEFAULT 0,
                mouse_moves INTEGER DEFAULT 0,
                keyboard_presses INTEGER DEFAULT 0,
                window_switches INTEGER DEFAULT 0,
                active_windows INTEGER DEFAULT 0,
                cpu_usage REAL DEFAULT 0,
                memory_usage REAL DEFAULT 0,
                busy_index REAL DEFAULT 0,
                is_idle BOOLEAN DEFAULT 0,
                active_window_title TEXT,
                UNIQUE(timestamp)
            )
        ''')
        
        # 创建会话表（开机/关机记录）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_date DATE NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                duration_minutes INTEGER,
                active_minutes INTEGER,
                idle_minutes INTEGER,
                nap_minutes INTEGER DEFAULT 0,
                total_mouse_clicks INTEGER DEFAULT 0,
                total_key_presses INTEGER DEFAULT 0,
                average_busy_index REAL DEFAULT 0
            )
        ''')
        
        # 创建每日统计表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stat_date DATE UNIQUE NOT NULL,
                first_boot_time DATETIME,
                last_shutdown_time DATETIME,
                total_active_minutes INTEGER DEFAULT 0,
                total_idle_minutes INTEGER DEFAULT 0,
                nap_minutes INTEGER DEFAULT 0,
                total_mouse_clicks INTEGER DEFAULT 0,
                total_key_presses INTEGER DEFAULT 0,
                total_window_switches INTEGER DEFAULT 0,
                total_mouse_distance REAL DEFAULT 0,
                average_busy_index REAL DEFAULT 0,
                max_busy_index REAL DEFAULT 0,
                work_sessions INTEGER DEFAULT 0
            )
        ''')
        
        # 检查并添加 total_mouse_distance 列（兼容旧数据库）
        cursor.execute("PRAGMA table_info(daily_stats)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'total_mouse_distance' not in columns:
            cursor.execute('ALTER TABLE daily_stats ADD COLUMN total_mouse_distance REAL DEFAULT 0')
            logger.info("已添加 total_mouse_distance 列到 daily_stats 表")
        
        # 创建索引以提高查询性能
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_activity_timestamp 
            ON activity_records(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_date 
            ON sessions(session_date)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_daily_date 
            ON daily_stats(stat_date)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("数据库初始化完成")
    
    def save_activity_record(self, record: Dict) -> bool:
        """保存活动记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO activity_records (
                    timestamp, mouse_distance, mouse_clicks, mouse_moves,
                    keyboard_presses, window_switches, active_windows,
                    cpu_usage, memory_usage, busy_index, is_idle,
                    active_window_title
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.get('timestamp'),
                record.get('mouse_distance', 0),
                record.get('mouse_clicks', 0),
                record.get('mouse_moves', 0),
                record.get('keyboard_presses', 0),
                record.get('window_switches', 0),
                record.get('active_windows', 0),
                record.get('cpu_usage', 0),
                record.get('memory_usage', 0),
                record.get('busy_index', 0),
                record.get('is_idle', False),
                record.get('active_window_title', '')
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"保存活动记录失败: {e}")
            return False
    
    def start_session(self) -> int:
        """开始新会话（开机）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            cursor.execute('''
                INSERT INTO sessions (session_date, start_time)
                VALUES (?, ?)
            ''', (now.date(), now))
            
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"新会话开始: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"开始会话失败: {e}")
            return -1
    
    def end_session(self, session_id: int) -> bool:
        """结束会话（关机）"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取会话开始时间
            cursor.execute('''
                SELECT start_time FROM sessions WHERE id = ?
            ''', (session_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            start_time = datetime.fromisoformat(result['start_time'])
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() / 60)
            
            # 统计会话期间的活动
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_records,
                    SUM(CASE WHEN is_idle = 0 THEN 1 ELSE 0 END) as active_minutes,
                    SUM(CASE WHEN is_idle = 1 THEN 1 ELSE 0 END) as idle_minutes,
                    SUM(mouse_clicks) as total_clicks,
                    SUM(keyboard_presses) as total_presses,
                    AVG(busy_index) as avg_busy
                FROM activity_records
                WHERE timestamp BETWEEN ? AND ?
            ''', (start_time, end_time))
            
            stats = cursor.fetchone()
            
            # 更新会话记录
            cursor.execute('''
                UPDATE sessions SET
                    end_time = ?,
                    duration_minutes = ?,
                    active_minutes = ?,
                    idle_minutes = ?,
                    total_mouse_clicks = ?,
                    total_key_presses = ?,
                    average_busy_index = ?
                WHERE id = ?
            ''', (
                end_time,
                duration,
                stats['active_minutes'] or 0,
                stats['idle_minutes'] or 0,
                stats['total_clicks'] or 0,
                stats['total_presses'] or 0,
                stats['avg_busy'] or 0,
                session_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"会话结束: {session_id}, 时长: {duration}分钟")
            return True
        except Exception as e:
            logger.error(f"结束会话失败: {e}")
            return False
    
    def update_daily_stats(self, date: datetime.date) -> bool:
        """更新每日统计
        注意：将第二天凌晨0:00-2:00的活动也计入当天
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 定义工作日的实际时间范围：
            # 当天 00:00:00 到第二天 02:00:00
            start_of_day = datetime.combine(date, datetime.min.time())
            next_day = date + timedelta(days=1)
            end_of_day = datetime.combine(next_day, datetime.min.time()) + timedelta(hours=2)
            
            # 获取当天的所有会话（包括跨日的会话）
            cursor.execute('''
                SELECT 
                    MIN(start_time) as first_boot,
                    MAX(CASE 
                        WHEN end_time IS NULL THEN NULL
                        WHEN end_time <= ? THEN end_time
                        ELSE ?
                    END) as last_shutdown,
                    COUNT(*) as session_count
                FROM sessions
                WHERE (session_date = ? OR 
                       (session_date = ? AND 
                        strftime('%H', start_time) < '02'))
            ''', (end_of_day, end_of_day, date, next_day))
            
            session_info = cursor.fetchone()
            
            # 获取当天的活动统计（包括第二天凌晨2点前的数据）
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN is_idle = 0 THEN 1 ELSE 0 END) as active_minutes,
                    SUM(CASE WHEN is_idle = 1 THEN 1 ELSE 0 END) as idle_minutes,
                    SUM(mouse_clicks) as total_clicks,
                    SUM(keyboard_presses) as total_presses,
                    SUM(window_switches) as total_switches,
                    SUM(mouse_distance) as total_distance,
                    AVG(busy_index) as avg_busy,
                    MAX(busy_index) as max_busy
                FROM activity_records
                WHERE timestamp >= ? AND timestamp < ?
            ''', (start_of_day, end_of_day))
            
            activity_stats = cursor.fetchone()
            
            # 检测午休时间
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN is_idle = 1 
                        AND CAST(strftime('%H', timestamp) AS INTEGER) BETWEEN 12 AND 14
                        THEN 1 ELSE 0 END) as nap_minutes
                FROM activity_records
                WHERE timestamp BETWEEN ? AND ?
            ''', (start_of_day, end_of_day))
            
            nap_info = cursor.fetchone()
            
            # 插入或更新每日统计
            cursor.execute('''
                INSERT OR REPLACE INTO daily_stats (
                    stat_date, first_boot_time, last_shutdown_time,
                    total_active_minutes, total_idle_minutes, nap_minutes,
                    total_mouse_clicks, total_key_presses, total_window_switches,
                    total_mouse_distance, average_busy_index, max_busy_index, work_sessions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date,
                session_info['first_boot'],
                session_info['last_shutdown'],
                activity_stats['active_minutes'] or 0,
                activity_stats['idle_minutes'] or 0,
                nap_info['nap_minutes'] or 0,
                activity_stats['total_clicks'] or 0,
                activity_stats['total_presses'] or 0,
                activity_stats['total_switches'] or 0,
                activity_stats['total_distance'] or 0,
                activity_stats['avg_busy'] or 0,
                activity_stats['max_busy'] or 0,
                session_info['session_count'] or 0
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"每日统计已更新: {date}")
            return True
        except Exception as e:
            logger.error(f"更新每日统计失败: {e}")
            return False
    
    def get_activity_records(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """获取指定时间段的活动记录"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM activity_records
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        ''', (start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_daily_stats(self, start_date: datetime.date, end_date: datetime.date) -> List[Dict]:
        """获取指定日期范围的每日统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM daily_stats
            WHERE stat_date BETWEEN ? AND ?
            ORDER BY stat_date
        ''', (start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_current_session_id(self) -> Optional[int]:
        """获取当前未结束的会话ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM sessions
            WHERE end_time IS NULL
            ORDER BY start_time DESC
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        return result['id'] if result else None
    
    def cleanup_old_data(self, days: int = 365):
        """清理旧数据"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                DELETE FROM activity_records WHERE timestamp < ?
            ''', (cutoff_date,))
            
            cursor.execute('''
                DELETE FROM sessions WHERE session_date < ?
            ''', (cutoff_date.date(),))
            
            cursor.execute('''
                DELETE FROM daily_stats WHERE stat_date < ?
            ''', (cutoff_date.date(),))
            
            conn.commit()
            deleted = cursor.rowcount
            conn.close()
            
            logger.info(f"清理了 {deleted} 条旧数据")
            return True
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return False

