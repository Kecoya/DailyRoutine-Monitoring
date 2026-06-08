"""
数据分析模块
生成统计报告和可视化图表
"""
import os
import logging
import calendar
import glob
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('Agg')  # 使用非 GUI 后端

import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from database import Database
from config import CHART_DPI, CHART_FIGSIZE, HEATMAP_FIGSIZE, STATIC_DIR, PIXELS_PER_METER, LAB_WORK_HOURS

logger = logging.getLogger(__name__)

# 设置 seaborn 风格（必须在字体设置之前，否则会覆盖字体配置）
sns.set_style("whitegrid")
sns.set_palette("husl")

# 设置中文字体（必须在 seaborn 初始化之后，否则会被 seaborn 覆盖）
# 优先使用 SimHei（黑体），备选微软雅黑
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'KaiTi', 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 清理计数器，用于可靠地触发图片清理（替代 hash % 10 这种不可靠方式）
_cleanup_counter = 0
_CLEANUP_INTERVAL = 10  # 每生成 10 张图清理一次


class DataAnalyzer:
    """数据分析器"""

    def __init__(self):
        self.db = Database()

    def _maybe_cleanup_images(self):
        """可靠的图片清理触发器"""
        global _cleanup_counter
        _cleanup_counter += 1
        if _cleanup_counter >= _CLEANUP_INTERVAL:
            _cleanup_counter = 0
            self.cleanup_old_images()

    def cleanup_old_images(self, days_to_keep: int = 7):
        """清理 static 目录中的旧图片文件"""
        try:
            image_patterns = [
                os.path.join(STATIC_DIR, 'busy_curve_*.png'),
                os.path.join(STATIC_DIR, 'trend_*.png'),
                os.path.join(STATIC_DIR, 'heatmap_*.png'),
                os.path.join(STATIC_DIR, 'calendar_*.png')
            ]

            files_to_check = []
            for pattern in image_patterns:
                files_to_check.extend(glob.glob(pattern))

            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0

            for file_path in files_to_check:
                if file_path.endswith('.gitkeep'):
                    continue

                try:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))

                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Deleted old image: {os.path.basename(file_path)}")

                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleanup completed: deleted {deleted_count} old image files")

            return deleted_count

        except Exception as e:
            logger.error(f"Image cleanup failed: {e}")
            return 0

    def get_today_summary(self) -> Dict:
        """获取今日概要数据"""
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
                'avg_busy_index': 0,
                'work_completion_rate': 0
            }

        stat = stats[0]

        # 计算鼠标移动距离（像素 → 米）
        mouse_distance_m = stat.get('total_mouse_distance', 0) / PIXELS_PER_METER if PIXELS_PER_METER > 0 else 0

        # 计算工作达成率
        active_hours = stat['total_active_minutes'] / 60
        work_completion_rate = (active_hours / LAB_WORK_HOURS) * 100 if LAB_WORK_HOURS > 0 else 0

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
            'total_mouse_distance': round(mouse_distance_m, 2),
            'avg_busy_index': stat['average_busy_index'],
            'max_busy_index': stat['max_busy_index'],
            'work_sessions': stat['work_sessions'],
            'work_completion_rate': round(work_completion_rate, 1)
        }

    def get_week_report(self, end_date: datetime.date = None) -> Dict:
        """获取周报（从本周周一到今天）"""
        today = datetime.now().date()
        days_since_monday = today.weekday()
        start_date = today - timedelta(days=days_since_monday)

        if end_date is None:
            end_date = today

        return self._generate_period_report(start_date, end_date, '周报')

    def get_month_report(self, year: int = None, month: int = None) -> Dict:
        """获取月报"""
        if year is None or month is None:
            now = datetime.now()
            year, month = now.year, now.month

        start_date = datetime(year, month, 1).date()

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
        """生成周期报表"""
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

        # 过滤无活动天数
        df = df[df['total_active_minutes'] > 0]

        if df.empty:
            return {
                'report_type': report_type,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_days': len(stats),
                'work_days': 0,
                'total_active_hours': 0,
                'avg_daily_active_hours': 0,
                'avg_busy_index': 0,
                'regularity_score': 0
            }

        # IQR 异常值过滤
        active_minutes = df['total_active_minutes']
        Q1 = active_minutes.quantile(0.25)
        Q3 = active_minutes.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        df_filtered = df[(active_minutes >= lower_bound) & (active_minutes <= upper_bound)]

        work_days = len(df_filtered)
        total_active_minutes = df_filtered['total_active_minutes'].sum()
        total_active_hours = total_active_minutes / 60
        avg_daily_active_hours = total_active_hours / work_days if work_days > 0 else 0

        original_total_active_minutes = df['total_active_minutes'].sum()
        original_total_active_hours = original_total_active_minutes / 60

        avg_busy_index = df_filtered['average_busy_index'].mean()

        # 规律性评分
        regularity_score = 0
        earliest_boot = 0
        latest_boot = 0
        avg_boot_time = 0

        if 'first_boot_time' in df_filtered.columns and df_filtered['first_boot_time'].notna().any():
            try:
                df_filtered_copy = df_filtered.copy()
                df_filtered_copy['first_boot_hour'] = pd.to_datetime(
                    df_filtered_copy['first_boot_time'], errors='coerce'
                ).dt.hour + pd.to_datetime(
                    df_filtered_copy['first_boot_time'], errors='coerce'
                ).dt.minute / 60

                valid_boots = df_filtered_copy['first_boot_hour'].dropna()
                if len(valid_boots) > 0:
                    boot_time_std = valid_boots.std()
                    regularity_score = max(0, 100 - boot_time_std * 10)
                    earliest_boot = valid_boots.min()
                    latest_boot = valid_boots.max()
                    avg_boot_time = valid_boots.mean()
            except Exception as e:
                logger.warning(f"计算规律性评分失败: {e}")

        # 活动统计
        total_clicks = df_filtered['total_mouse_clicks'].sum()
        total_presses = df_filtered['total_key_presses'].sum()
        total_switches = df_filtered['total_window_switches'].sum()

        # 鼠标移动距离
        if 'total_mouse_distance' in df_filtered.columns:
            total_mouse_distance = df_filtered['total_mouse_distance'].sum() / PIXELS_PER_METER
        else:
            total_mouse_distance = 0

        # 工作强度指标
        df_filtered = df_filtered.copy()
        df_filtered['work_intensity'] = (
            (df_filtered['total_active_minutes'] / 60) *
            df_filtered['average_busy_index'] / 100
        )
        avg_work_intensity = df_filtered['work_intensity'].mean()
        max_work_intensity = df_filtered['work_intensity'].max()

        # 专注度
        active_hours_series = df_filtered['total_active_minutes'] / 60
        df_filtered['focus_score'] = 100 - (
            df_filtered['total_window_switches'] / active_hours_series.clip(lower=0.1)
        ).clip(0, 100)
        avg_focus_score = df_filtered['focus_score'].mean()

        # 效率指标
        df_filtered['efficiency_score'] = (
            (df_filtered['total_mouse_clicks'] + df_filtered['total_key_presses']) /
            (df_filtered['total_active_minutes'] + 1)
        ).clip(0, 100)
        avg_efficiency = df_filtered['efficiency_score'].mean()

        return {
            'report_type': report_type,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_days': (end_date - start_date).days + 1,
            'total_raw_days': len(stats),
            'work_days': work_days,
            'excluded_zero_activity_days': len(stats) - len(df),
            'excluded_outlier_days': len(df) - len(df_filtered),
            'total_active_hours': round(total_active_hours, 2),
            'total_raw_active_hours': round(original_total_active_hours, 2),
            'avg_daily_active_hours': round(avg_daily_active_hours, 2),
            'avg_busy_index': round(avg_busy_index, 2) if not pd.isna(avg_busy_index) else 0,
            'avg_work_intensity': round(avg_work_intensity, 2),
            'max_work_intensity': round(max_work_intensity, 2),
            'avg_focus_score': round(avg_focus_score, 2),
            'avg_efficiency': round(avg_efficiency, 2),
            'regularity_score': round(regularity_score, 2),
            'earliest_boot_hour': round(earliest_boot, 2),
            'latest_boot_hour': round(latest_boot, 2),
            'avg_boot_hour': round(avg_boot_time, 2),
            'total_mouse_clicks': int(total_clicks),
            'total_key_presses': int(total_presses),
            'total_window_switches': int(total_switches),
            'total_mouse_distance_m': round(total_mouse_distance, 2),
            'daily_stats': stats
        }

    def generate_busy_curve(self, date: datetime.date, save_path: str = None) -> Optional[str]:
        """生成忙碌度曲线图
        包含第二天凌晨 0:00-2:00 的数据
        """
        start_time = datetime.combine(date, datetime.min.time())
        next_day = date + timedelta(days=1)
        end_time = datetime.combine(next_day, datetime.min.time()) + timedelta(hours=2)

        records = self.db.get_activity_records(start_time, end_time)

        if not records:
            logger.warning(f"No data found for {date}")
            return None

        df = pd.DataFrame(records)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        # 将第二天凌晨 0-2 点的时间转换为 24-26 点显示
        df['time_decimal'] = df.apply(
            lambda row: row['hour'] + row['minute'] / 60 if row['timestamp'].date() == date
            else 24 + row['hour'] + row['minute'] / 60,
            axis=1
        )

        # 创建图表
        fig, ax = plt.subplots(figsize=CHART_FIGSIZE, dpi=CHART_DPI)

        # 绘制忙碌曲线（用线+点）
        ax.plot(df['time_decimal'], df['busy_index'], '-',
                linewidth=1.5, color='#3498db', alpha=0.8, label='忙碌指数')
        ax.scatter(df['time_decimal'], df['busy_index'],
                   s=10, color='#2980b9', alpha=0.5)

        # 填充区域
        ax.fill_between(df['time_decimal'], 0, df['busy_index'],
                         alpha=0.2, color='#3498db')

        # 标记空闲时段
        idle_periods = df[df['is_idle'] == 1]
        if not idle_periods.empty:
            ax.scatter(idle_periods['time_decimal'],
                       idle_periods['busy_index'],
                       color='#e74c3c', s=20, alpha=0.5, label='空闲时段', zorder=5)

        # 设置图表属性
        ax.set_xlabel('时间', fontsize=12)
        ax.set_ylabel('忙碌指数', fontsize=12)
        ax.set_title(f'{date} 忙碌度曲线 (含次日凌晨2点前)', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 26)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right')

        # X 轴刻度
        hour_ticks = list(range(0, 27, 2))
        hour_labels = []
        for h in hour_ticks:
            if h < 24:
                hour_labels.append(f'{h:02d}:00')
            else:
                hour_labels.append(f'次日{h - 24:02d}:00')
        ax.set_xticks(hour_ticks)
        ax.set_xticklabels(hour_labels, rotation=45)

        plt.tight_layout()

        # 保存图表
        if save_path is None:
            save_path = os.path.join(STATIC_DIR, f'busy_curve_{date}.png')

        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close('all')

        self._maybe_cleanup_images()

        logger.info(f"Busy curve chart generated: {save_path}")
        return save_path

    def generate_heatmap(self, start_date: datetime.date,
                          end_date: datetime.date, save_path: str = None) -> Optional[str]:
        """生成日历热力图"""
        # 使用包含 start_date 的月份
        year, month = start_date.year, start_date.month

        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)

        stats = self.db.get_daily_stats(first_day, last_day)

        # 创建日期到数据的映射
        data_dict = {}
        if stats:
            for stat in stats:
                date_str = stat['stat_date']
                # stat_date 可能是字符串或 date 对象
                if isinstance(date_str, str):
                    date_str = date_str
                else:
                    date_str = date_str.isoformat()
                active_hours = stat['total_active_minutes'] / 60
                work_completion_rate = (active_hours / LAB_WORK_HOURS) * 100 if LAB_WORK_HOURS > 0 else 0
                data_dict[date_str] = {
                    'active_hours': active_hours,
                    'completion_rate': work_completion_rate
                }

        # 创建日历网格
        cal = calendar.monthcalendar(year, month)
        today = datetime.now().date()

        # 创建图表
        fig, ax = plt.subplots(figsize=(16, 10), dpi=CHART_DPI)
        ax.set_xlim(0, 7)
        ax.set_ylim(0, len(cal) + 1)
        ax.axis('off')

        # 标题
        month_name = calendar.month_name[month]
        ax.text(3.5, len(cal) + 0.8, f'{year}年{month}月 活动日历',
                fontsize=20, fontweight='bold', ha='center')

        # 星期标题
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        for i, day_name in enumerate(weekday_names):
            ax.text(i + 0.5, len(cal) - 0.2, day_name,
                    fontsize=12, ha='center', fontweight='bold')

        # 绘制日历格子
        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day == 0:
                    continue

                current_date = datetime(year, month, day).date()
                date_str = current_date.isoformat()

                # 确定单元格颜色
                if current_date > today:
                    bg_color = '#f0f0f0'
                    text_color = '#cccccc'
                elif current_date == today:
                    bg_color = '#fff3e0'
                    text_color = '#e65100'
                else:
                    bg_color = '#ffffff'
                    text_color = '#333333'

                # 绘制背景
                rect = plt.Rectangle((day_num, len(cal) - week_num - 1), 1, 1,
                                      facecolor=bg_color, edgecolor='#dddddd', linewidth=1)
                ax.add_patch(rect)

                # 日期数字
                ax.text(day_num + 0.5, len(cal) - week_num - 0.5, str(day),
                        fontsize=16, ha='center', va='center',
                        fontweight='bold', color=text_color)

                # 活动数据
                if current_date <= today and date_str in data_dict:
                    data = data_dict[date_str]
                    active_hours = data['active_hours']
                    completion_rate = data.get('completion_rate', None)

                    if completion_rate is not None:
                        info_text = f'{active_hours:.1f}h\n{completion_rate:.0f}%'
                    else:
                        info_text = f'{active_hours:.1f}h\nN/A'

                    ax.text(day_num + 0.85, len(cal) - week_num - 0.15, info_text,
                            fontsize=12, ha='right', va='top',
                            color=text_color, alpha=0.9, fontweight='bold')

        # 图例
        legend_y = -0.5
        ax.text(0, legend_y, '图例:', fontsize=10, fontweight='bold')
        ax.text(0, legend_y - 0.3, '● 灰色: 未来日期', fontsize=9, color='#666666')
        ax.text(2.5, legend_y - 0.3, '● 橙色: 今天', fontsize=9, color='#666666')
        ax.text(4.5, legend_y - 0.3, f'● 标准工时: {LAB_WORK_HOURS}h/天', fontsize=9, color='#666666')

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(STATIC_DIR, f'calendar_{year}_{month:02d}.png')

        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close('all')

        self._maybe_cleanup_images()

        logger.info(f"Calendar heatmap generated: {save_path}")
        return save_path

    def generate_trend_chart(self, start_date: datetime.date,
                              end_date: datetime.date, save_path: str = None) -> Optional[str]:
        """生成趋势图"""
        stats = self.db.get_daily_stats(start_date, end_date)

        if not stats:
            logger.warning(f"No data found from {start_date} to {end_date}")
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
        ax1.set_ylabel('活动时长 (小时)', fontsize=12)
        ax1.set_title('每日活动时长趋势', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)

        avg_hours = df['active_hours'].mean()
        ax1.axhline(y=avg_hours, color='red', linestyle='--',
                     linewidth=2, label=f'平均: {avg_hours:.2f} 小时')
        ax1.axhline(y=LAB_WORK_HOURS, color='orange', linestyle='-.',
                     linewidth=2, label=f'标准工时: {LAB_WORK_HOURS:.1f} 小时')
        ax1.legend(loc='upper right')

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

        avg_busy = df['average_busy_index'].mean()
        ax2.axhline(y=avg_busy, color='blue', linestyle='--',
                     linewidth=2, label=f'平均: {avg_busy:.2f}')
        ax2.legend(loc='upper right')

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(STATIC_DIR,
                                      f'trend_{start_date}_{end_date}.png')

        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close('all')

        self._maybe_cleanup_images()

        logger.info(f"Trend chart generated: {save_path}")
        return save_path

    def export_to_csv(self, start_date: datetime.date,
                       end_date: datetime.date, output_path: str) -> bool:
        """导出数据到 CSV"""
        try:
            stats = self.db.get_daily_stats(start_date, end_date)

            if not stats:
                logger.warning("No data to export")
                return False

            df = pd.DataFrame(stats)
            df.to_csv(output_path, index=False, encoding='utf-8-sig')

            logger.info(f"Data exported to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return False

    def export_to_excel(self, start_date: datetime.date,
                         end_date: datetime.date, output_path: str) -> bool:
        """导出数据到 Excel"""
        try:
            daily_stats = self.db.get_daily_stats(start_date, end_date)

            if not daily_stats:
                logger.warning("No data to export")
                return False

            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df_daily = pd.DataFrame(daily_stats)
                df_daily['active_hours'] = df_daily['total_active_minutes'] / 60
                df_daily['idle_hours'] = df_daily['total_idle_minutes'] / 60

                df_daily.to_excel(writer, sheet_name='每日统计', index=False)

                # 汇总统计
                week_report = self.get_custom_report(start_date, end_date)
                df_summary = pd.DataFrame([{
                    '统计项': '有效工作天数',
                    '值': week_report['work_days']
                }, {
                    '统计项': '总活动时长(小时)',
                    '值': week_report['total_active_hours']
                }, {
                    '统计项': '日均活动时长(小时)',
                    '值': week_report['avg_daily_active_hours']
                }, {
                    '统计项': '平均忙碌指数',
                    '值': week_report['avg_busy_index']
                }, {
                    '统计项': '平均工作强度',
                    '值': week_report['avg_work_intensity']
                }, {
                    '统计项': '平均专注度',
                    '值': week_report['avg_focus_score']
                }, {
                    '统计项': '平均效率指数',
                    '值': week_report['avg_efficiency']
                }, {
                    '统计项': '作息规律性',
                    '值': week_report['regularity_score']
                }, {
                    '统计项': '鼠标移动总距离(米)',
                    '值': week_report['total_mouse_distance_m']
                }])

                df_summary.to_excel(writer, sheet_name='汇总统计', index=False)

            logger.info(f"Data exported to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            return False


def main():
    """主函数（测试用）"""
    analyzer = DataAnalyzer()

    today_summary = analyzer.get_today_summary()
    print("Today's Summary:", today_summary)

    week_report = analyzer.get_week_report()
    print("\nWeekly Report:", week_report)

    today = datetime.now().date()
    analyzer.generate_busy_curve(today)
    analyzer.generate_trend_chart(today - timedelta(days=7), today)
    analyzer.generate_heatmap(today - timedelta(days=30), today)


if __name__ == '__main__':
    main()
