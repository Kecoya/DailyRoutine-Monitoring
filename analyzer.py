"""
数据分析模块
生成统计报表和可视化图表
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 使用非GUI后端
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.font_manager import FontProperties

from database import Database
from config import CHART_DPI, CHART_FIGSIZE, HEATMAP_FIGSIZE, STATIC_DIR

logger = logging.getLogger(__name__)

# 设置中文字体（Windows）
try:
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
except:
    logger.warning("无法设置中文字体，图表可能显示异常")

# 设置seaborn样式
sns.set_style("whitegrid")
sns.set_palette("husl")


class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self):
        self.db = Database()
    
    def get_today_summary(self) -> Dict:
        """获取今日汇总数据"""
        today = datetime.now().date()
        stats = self.db.get_daily_stats(today, today)
        
        if not stats:
            return {
                'date': today.isoformat(),
                'first_boot': None,
                'last_shutdown': None,
                'active_minutes': 0,
                'idle_minutes': 0,
                'total_clicks': 0,
                'total_presses': 0,
                'avg_busy_index': 0
            }
        
        stat = stats[0]
        return {
            'date': stat['stat_date'],
            'first_boot': stat['first_boot_time'],
            'last_shutdown': stat['last_shutdown_time'],
            'active_minutes': stat['total_active_minutes'],
            'idle_minutes': stat['total_idle_minutes'],
            'nap_minutes': stat['nap_minutes'],
            'total_clicks': stat['total_mouse_clicks'],
            'total_presses': stat['total_key_presses'],
            'total_switches': stat['total_window_switches'],
            'avg_busy_index': stat['average_busy_index'],
            'max_busy_index': stat['max_busy_index'],
            'work_sessions': stat['work_sessions']
        }
    
    def get_week_report(self, end_date: datetime.date = None) -> Dict:
        """获取周报"""
        if end_date is None:
            end_date = datetime.now().date()
        
        start_date = end_date - timedelta(days=6)
        return self._generate_period_report(start_date, end_date, '周报')
    
    def get_month_report(self, year: int = None, month: int = None) -> Dict:
        """获取月报"""
        if year is None or month is None:
            now = datetime.now()
            year, month = now.year, now.month
        
        start_date = datetime(year, month, 1).date()
        
        # 计算月末
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        return self._generate_period_report(start_date, end_date, '月报')
    
    def get_custom_report(self, start_date: datetime.date, end_date: datetime.date) -> Dict:
        """获取自定义时间段报表"""
        return self._generate_period_report(start_date, end_date, '自定义报表')
    
    def _generate_period_report(self, start_date: datetime.date, 
                               end_date: datetime.date, report_type: str) -> Dict:
        """生成时间段报表"""
        stats = self.db.get_daily_stats(start_date, end_date)
        
        if not stats:
            return {
                'report_type': report_type,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_days': 0,
                'work_days': 0,
                'total_active_hours': 0,
                'avg_daily_active_hours': 0,
                'avg_busy_index': 0,
                'regularity_score': 0
            }
        
        df = pd.DataFrame(stats)
        
        # 基础统计
        work_days = len(df)
        total_active_minutes = df['total_active_minutes'].sum()
        total_active_hours = total_active_minutes / 60
        avg_daily_active_hours = total_active_hours / work_days if work_days > 0 else 0
        
        avg_busy_index = df['average_busy_index'].mean()
        
        # 计算作息规律性得分（基于开机时间的标准差，越小越规律）
        df['first_boot_hour'] = pd.to_datetime(df['first_boot_time']).dt.hour + \
                                pd.to_datetime(df['first_boot_time']).dt.minute / 60
        boot_time_std = df['first_boot_hour'].std()
        regularity_score = max(0, 100 - boot_time_std * 10)  # 标准差越大，规律性越低
        
        # 最早和最晚的开机时间
        earliest_boot = df['first_boot_hour'].min()
        latest_boot = df['first_boot_hour'].max()
        avg_boot_time = df['first_boot_hour'].mean()
        
        # 总活动统计
        total_clicks = df['total_mouse_clicks'].sum()
        total_presses = df['total_key_presses'].sum()
        total_switches = df['total_window_switches'].sum()
        
        return {
            'report_type': report_type,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_days': (end_date - start_date).days + 1,
            'work_days': work_days,
            'total_active_hours': round(total_active_hours, 2),
            'avg_daily_active_hours': round(avg_daily_active_hours, 2),
            'avg_busy_index': round(avg_busy_index, 2),
            'regularity_score': round(regularity_score, 2),
            'earliest_boot_hour': round(earliest_boot, 2),
            'latest_boot_hour': round(latest_boot, 2),
            'avg_boot_hour': round(avg_boot_time, 2),
            'total_mouse_clicks': int(total_clicks),
            'total_key_presses': int(total_presses),
            'total_window_switches': int(total_switches),
            'daily_stats': stats
        }
    
    def generate_busy_curve(self, date: datetime.date, save_path: str = None) -> str:
        """生成忙碌度曲线图"""
        start_time = datetime.combine(date, datetime.min.time())
        end_time = datetime.combine(date, datetime.max.time())
        
        records = self.db.get_activity_records(start_time, end_time)
        
        if not records:
            logger.warning(f"没有找到 {date} 的数据")
            return None
        
        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        df['time_decimal'] = df['hour'] + df['minute'] / 60
        
        # 创建图表
        fig, ax = plt.subplots(figsize=CHART_FIGSIZE, dpi=CHART_DPI)
        
        # 绘制忙碌度曲线
        ax.plot(df['time_decimal'], df['busy_index'], 
               linewidth=2, color='#3498db', label='忙碌指数')
        
        # 填充区域
        ax.fill_between(df['time_decimal'], 0, df['busy_index'], 
                        alpha=0.3, color='#3498db')
        
        # 标记空闲时段
        idle_periods = df[df['is_idle'] == 1]
        if not idle_periods.empty:
            ax.scatter(idle_periods['time_decimal'], 
                      idle_periods['busy_index'],
                      color='red', s=20, alpha=0.5, label='空闲时段')
        
        # 设置图表属性
        ax.set_xlabel('时间', fontsize=12)
        ax.set_ylabel('忙碌指数', fontsize=12)
        ax.set_title(f'{date} 忙碌度曲线图', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 24)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # 设置X轴刻度
        ax.set_xticks(range(0, 25, 2))
        ax.set_xticklabels([f'{h:02d}:00' for h in range(0, 25, 2)], rotation=45)
        
        plt.tight_layout()
        
        # 保存图表
        if save_path is None:
            save_path = os.path.join(STATIC_DIR, f'busy_curve_{date}.png')
        
        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close()
        
        logger.info(f"忙碌度曲线图已生成: {save_path}")
        return save_path
    
    def generate_heatmap(self, start_date: datetime.date, 
                        end_date: datetime.date, save_path: str = None) -> str:
        """生成活动热力图"""
        stats = self.db.get_daily_stats(start_date, end_date)
        
        if not stats:
            logger.warning(f"没有找到 {start_date} 到 {end_date} 的数据")
            return None
        
        df = pd.DataFrame(stats)
        df['stat_date'] = pd.to_datetime(df['stat_date'])
        df['weekday'] = df['stat_date'].dt.dayofweek
        df['week'] = df['stat_date'].dt.isocalendar().week
        
        # 创建透视表
        pivot = df.pivot_table(
            values='total_active_minutes',
            index='weekday',
            columns='week',
            aggfunc='sum',
            fill_value=0
        )
        
        # 转换为小时
        pivot = pivot / 60
        
        # 创建图表
        fig, ax = plt.subplots(figsize=HEATMAP_FIGSIZE, dpi=CHART_DPI)
        
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlOrRd',
                   cbar_kws={'label': '活动时长（小时）'},
                   linewidths=0.5, ax=ax)
        
        ax.set_xlabel('周数', fontsize=12)
        ax.set_ylabel('星期', fontsize=12)
        ax.set_title(f'{start_date} 至 {end_date} 活动热力图', 
                    fontsize=14, fontweight='bold')
        ax.set_yticklabels(['周一', '周二', '周三', '周四', '周五', '周六', '周日'])
        
        plt.tight_layout()
        
        # 保存图表
        if save_path is None:
            save_path = os.path.join(STATIC_DIR, 
                                    f'heatmap_{start_date}_{end_date}.png')
        
        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close()
        
        logger.info(f"活动热力图已生成: {save_path}")
        return save_path
    
    def generate_trend_chart(self, start_date: datetime.date,
                            end_date: datetime.date, save_path: str = None) -> str:
        """生成趋势图"""
        stats = self.db.get_daily_stats(start_date, end_date)
        
        if not stats:
            logger.warning(f"没有找到 {start_date} 到 {end_date} 的数据")
            return None
        
        df = pd.DataFrame(stats)
        df['stat_date'] = pd.to_datetime(df['stat_date'])
        df['active_hours'] = df['total_active_minutes'] / 60
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), dpi=CHART_DPI)
        
        # 活动时长趋势
        ax1.plot(df['stat_date'], df['active_hours'], 
                marker='o', linewidth=2, markersize=6, color='#2ecc71')
        ax1.fill_between(df['stat_date'], 0, df['active_hours'], 
                        alpha=0.3, color='#2ecc71')
        ax1.set_xlabel('日期', fontsize=12)
        ax1.set_ylabel('活动时长（小时）', fontsize=12)
        ax1.set_title('每日活动时长趋势', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # 添加平均线
        avg_hours = df['active_hours'].mean()
        ax1.axhline(y=avg_hours, color='red', linestyle='--', 
                   linewidth=2, label=f'平均: {avg_hours:.2f}小时')
        ax1.legend()
        
        # 忙碌指数趋势
        ax2.plot(df['stat_date'], df['average_busy_index'],
                marker='s', linewidth=2, markersize=6, color='#e74c3c')
        ax2.fill_between(df['stat_date'], 0, df['average_busy_index'],
                        alpha=0.3, color='#e74c3c')
        ax2.set_xlabel('日期', fontsize=12)
        ax2.set_ylabel('忙碌指数', fontsize=12)
        ax2.set_title('每日平均忙碌指数趋势', fontsize=14, fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
        
        # 添加平均线
        avg_busy = df['average_busy_index'].mean()
        ax2.axhline(y=avg_busy, color='blue', linestyle='--',
                   linewidth=2, label=f'平均: {avg_busy:.2f}')
        ax2.legend()
        
        plt.tight_layout()
        
        # 保存图表
        if save_path is None:
            save_path = os.path.join(STATIC_DIR,
                                    f'trend_{start_date}_{end_date}.png')
        
        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close()
        
        logger.info(f"趋势图已生成: {save_path}")
        return save_path
    
    def export_to_csv(self, start_date: datetime.date,
                     end_date: datetime.date, output_path: str) -> bool:
        """导出数据为CSV"""
        try:
            stats = self.db.get_daily_stats(start_date, end_date)
            
            if not stats:
                logger.warning("没有数据可导出")
                return False
            
            df = pd.DataFrame(stats)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            logger.info(f"数据已导出到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return False
    
    def export_to_excel(self, start_date: datetime.date,
                       end_date: datetime.date, output_path: str) -> bool:
        """导出数据为Excel"""
        try:
            # 获取每日统计
            daily_stats = self.db.get_daily_stats(start_date, end_date)
            
            if not daily_stats:
                logger.warning("没有数据可导出")
                return False
            
            # 创建Excel写入器
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # 每日统计表
                df_daily = pd.DataFrame(daily_stats)
                df_daily['active_hours'] = df_daily['total_active_minutes'] / 60
                df_daily['idle_hours'] = df_daily['total_idle_minutes'] / 60
                
                df_daily.to_excel(writer, sheet_name='每日统计', index=False)
                
                # 周报表
                week_report = self.get_custom_report(start_date, end_date)
                df_summary = pd.DataFrame([{
                    '统计项': '总工作天数',
                    '数值': week_report['work_days']
                }, {
                    '统计项': '总活动时长（小时）',
                    '数值': week_report['total_active_hours']
                }, {
                    '统计项': '日均活动时长（小时）',
                    '数值': week_report['avg_daily_active_hours']
                }, {
                    '统计项': '平均忙碌指数',
                    '数值': week_report['avg_busy_index']
                }, {
                    '统计项': '作息规律性得分',
                    '数值': week_report['regularity_score']
                }])
                
                df_summary.to_excel(writer, sheet_name='汇总统计', index=False)
            
            logger.info(f"数据已导出到: {output_path}")
            return True
        except Exception as e:
            logger.error(f"导出Excel失败: {e}")
            return False


def main():
    """主函数（用于测试）"""
    analyzer = DataAnalyzer()
    
    # 测试今日汇总
    today_summary = analyzer.get_today_summary()
    print("今日汇总:", today_summary)
    
    # 测试周报
    week_report = analyzer.get_week_report()
    print("\n周报:", week_report)
    
    # 生成图表
    today = datetime.now().date()
    analyzer.generate_busy_curve(today)
    analyzer.generate_trend_chart(today - timedelta(days=7), today)
    analyzer.generate_heatmap(today - timedelta(days=30), today)


if __name__ == '__main__':
    main()

