"""
Data Analysis Module
Generate statistical reports and visualization charts
"""
import os
import logging
import calendar
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np

import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')  # Use non-GUI backend

# Set font for Chinese characters
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

import seaborn as sns
from database import Database
from config import CHART_DPI, CHART_FIGSIZE, HEATMAP_FIGSIZE, STATIC_DIR, PIXELS_PER_METER, LAB_WORK_HOURS

logger = logging.getLogger(__name__)


# Set seaborn style
sns.set_style("whitegrid")
sns.set_palette("husl")


class DataAnalyzer:
    """Data Analyzer"""
    
    def __init__(self):
        self.db = Database()
    
    def cleanup_old_images(self, days_to_keep: int = 7):
        """Clean up old image files in static directory"""
        try:
            # Get all image files in static directory
            image_patterns = [
                os.path.join(STATIC_DIR, 'busy_curve_*.png'),
                os.path.join(STATIC_DIR, 'trend_*.png'),
                os.path.join(STATIC_DIR, 'heatmap_*.png'),
                os.path.join(STATIC_DIR, 'calendar_*.png')
            ]
            
            files_to_check = []
            for pattern in image_patterns:
                files_to_check.extend(glob.glob(pattern))
            
            # Calculate cutoff time
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0
            
            for file_path in files_to_check:
                # Skip .gitkeep file
                if file_path.endswith('.gitkeep'):
                    continue
                
                try:
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # Delete if file is older than cutoff
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Deleted old image: {os.path.basename(file_path)}")
                        
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
            
            if deleted_count > 0:
                logger.info(f"Cleanup completed: deleted {deleted_count} old image files")
            else:
                logger.info("Cleanup completed: no old files to delete")
                
            return deleted_count
            
        except Exception as e:
            logger.error(f"Image cleanup failed: {e}")
            return 0
    
    def get_today_summary(self) -> Dict:
        """Get today's summary data"""
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
                'work_completion_rate': 0  # 新增：工作达成率
            }

        stat = stats[0]

        # 计算鼠标移动距离（像素 → 米）
        # 使用配置的换算系数（PIXELS_PER_METER）
        mouse_distance_m = stat.get('total_mouse_distance', 0) / PIXELS_PER_METER

        # 计算工作达成率（活动时长 / 实验室标准工作时长）
        active_hours = stat['total_active_minutes'] / 60
        work_completion_rate = (active_hours / LAB_WORK_HOURS) * 100

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
            'total_mouse_distance': round(mouse_distance_m, 2),  # 米
            'avg_busy_index': stat['average_busy_index'],
            'max_busy_index': stat['max_busy_index'],
            'work_sessions': stat['work_sessions'],
            'work_completion_rate': round(work_completion_rate, 1)  # 工作达成率(%)
        }
    
    def get_week_report(self, end_date: datetime.date = None) -> Dict:
        """Get weekly report"""
        if end_date is None:
            end_date = datetime.now().date()
        
        start_date = end_date - timedelta(days=6)
        return self._generate_period_report(start_date, end_date, 'Weekly Report')
    
    def get_month_report(self, year: int = None, month: int = None) -> Dict:
        """Get monthly report"""
        if year is None or month is None:
            now = datetime.now()
            year, month = now.year, now.month
        
        start_date = datetime(year, month, 1).date()
        
        # Calculate end of month
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        return self._generate_period_report(start_date, end_date, 'Monthly Report')
    
    def get_custom_report(self, start_date: datetime.date, end_date: datetime.date) -> Dict:
        """Get custom period report"""
        return self._generate_period_report(start_date, end_date, 'Custom Report')
    
    def _generate_period_report(self, start_date: datetime.date, 
                               end_date: datetime.date, report_type: str) -> Dict:
        """Generate period report"""
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
        
        # Basic statistics
        work_days = len(df)
        total_active_minutes = df['total_active_minutes'].sum()
        total_active_hours = total_active_minutes / 60
        avg_daily_active_hours = total_active_hours / work_days if work_days > 0 else 0
        
        avg_busy_index = df['average_busy_index'].mean()
        
        # Calculate regularity score (based on standard deviation of boot time, smaller is more regular)
        df['first_boot_hour'] = pd.to_datetime(df['first_boot_time']).dt.hour + \
                                pd.to_datetime(df['first_boot_time']).dt.minute / 60
        boot_time_std = df['first_boot_hour'].std()
        regularity_score = max(0, 100 - boot_time_std * 10)  # Larger standard deviation means lower regularity
        
        # Earliest and latest boot times
        earliest_boot = df['first_boot_hour'].min()
        latest_boot = df['first_boot_hour'].max()
        avg_boot_time = df['first_boot_hour'].mean()
        
        # Total activity statistics
        total_clicks = df['total_mouse_clicks'].sum()
        total_presses = df['total_key_presses'].sum()
        total_switches = df['total_window_switches'].sum()
        # 鼠标移动距离：像素 → 米
        total_mouse_distance = df.get('total_mouse_distance', pd.Series([0])).sum() / PIXELS_PER_METER
        
        # 计算工作强度指标（相对于平均值）
        # 工作强度 = (活动时长 × 忙碌指数) / 平均活动时长
        df['work_intensity'] = (df['total_active_minutes'] / 60) * df['average_busy_index'] / 100
        avg_work_intensity = df['work_intensity'].mean()
        max_work_intensity = df['work_intensity'].max()
        
        # 计算专注度（基于窗口切换频率，切换越少越专注）
        df['focus_score'] = 100 - (df['total_window_switches'] / (df['total_active_minutes'] / 60)).clip(0, 100)
        avg_focus_score = df['focus_score'].mean()
        
        # 计算效率指标（键盘+鼠标活动 / 活动时长）
        df['efficiency_score'] = ((df['total_mouse_clicks'] + df['total_key_presses']) / 
                                   (df['total_active_minutes'] + 1)).clip(0, 100)
        avg_efficiency = df['efficiency_score'].mean()
        
        return {
            'report_type': report_type,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_days': (end_date - start_date).days + 1,
            'work_days': work_days,
            'total_active_hours': round(total_active_hours, 2),
            'avg_daily_active_hours': round(avg_daily_active_hours, 2),
            'avg_busy_index': round(avg_busy_index, 2),
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
            'total_mouse_distance_m': round(total_mouse_distance, 2),  # 米
            'daily_stats': stats
        }
    
    def generate_busy_curve(self, date: datetime.date, save_path: str = None) -> str:
        """Generate busy curve chart
        注意：包含第二天凌晨0:00-2:00的数据
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
        # 将第二天凌晨0-2点的时间转换为24-26点显示
        df['time_decimal'] = df.apply(
            lambda row: row['hour'] + row['minute'] / 60 if row['timestamp'].date() == date 
            else 24 + row['hour'] + row['minute'] / 60, 
            axis=1
        )
        
        # Create chart
        fig, ax = plt.subplots(figsize=CHART_FIGSIZE, dpi=CHART_DPI)
        
        # Plot busy curve
        ax.plot(df['time_decimal'], df['busy_index'], '.',
               linewidth=2, color='#3498db', label='Busy Index')
        
        # Fill area
        ax.fill_between(df['time_decimal'], 0, df['busy_index'], 
                        alpha=0.3, color='#3498db')
        
        # Mark idle periods
        idle_periods = df[df['is_idle'] == 1]
        if not idle_periods.empty:
            ax.scatter(idle_periods['time_decimal'], 
                      idle_periods['busy_index'],
                      color='red', s=20, alpha=0.5, label='Idle Period')
        
        # Set chart properties
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Busy Index', fontsize=12)
        ax.set_title(f'{date} Busy Curve Chart (含次日凌晨2点前)', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 26)
        ax.set_ylim(0, 105)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Set X-axis ticks (0-26点，即到第二天凌晨2点)
        hour_ticks = list(range(0, 27, 2))
        hour_labels = []
        for h in hour_ticks:
            if h < 24:
                hour_labels.append(f'{h:02d}:00')
            else:
                hour_labels.append(f'次日{h-24:02d}:00')
        ax.set_xticks(hour_ticks)
        ax.set_xticklabels(hour_labels, rotation=45)
        
        plt.tight_layout()
        
        # Save chart
        if save_path is None:
            save_path = os.path.join(STATIC_DIR, f'busy_curve_{date}.png')
        
        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close()
        
        # Clean up old images periodically (every 10th call)
        if hash(save_path) % 10 == 0:
            self.cleanup_old_images()
        
        logger.info(f"Busy curve chart generated: {save_path}")
        return save_path
    
    def generate_heatmap(self, start_date: datetime.date, 
                        end_date: datetime.date, save_path: str = None) -> str:
        """Generate calendar-style activity heatmap"""
        # Get calendar data for the month containing start_date
        if start_date.month != end_date.month:
            # If spanning multiple months, use the first month
            year, month = start_date.year, start_date.month
        else:
            year, month = start_date.year, start_date.month
        
        # Get first and last day of the month
        first_day = datetime(year, month, 1).date()
        if month == 12:
            last_day = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            last_day = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        # Get stats for the month
        stats = self.db.get_daily_stats(first_day, last_day)
        
        # Create date to data mapping
        data_dict = {}
        if stats:
            for stat in stats:
                date_str = stat['stat_date']
                active_hours = stat['total_active_minutes'] / 60
                work_completion_rate = (active_hours / LAB_WORK_HOURS) * 100
                data_dict[date_str] = {
                    'active_hours': active_hours,
                    'completion_rate': work_completion_rate
                }
        
        # Create calendar grid
        cal = calendar.monthcalendar(year, month)
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(16, 10), dpi=CHART_DPI)
        ax.set_xlim(0, 7)
        ax.set_ylim(0, len(cal) + 1)
        ax.axis('off')
        
        # Title
        month_name = calendar.month_name[month]
        ax.text(3.5, len(cal) + 0.8, f'{month_name} {year} Activity Calendar', 
                fontsize=20, fontweight='bold', ha='center')
        
        # Weekday headers
        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day_name in enumerate(weekday_names):
            ax.text(i + 0.5, len(cal) - 0.2, day_name, 
                    fontsize=12, ha='center', fontweight='bold')
        
        # Draw calendar days
        for week_num, week in enumerate(cal):
            for day_num, day in enumerate(week):
                if day == 0:
                    continue  # Empty day (padding)
                
                current_date = datetime(year, month, day).date()
                date_str = current_date.isoformat()
                
                # Determine cell color
                if current_date > today:
                    # Future dates - light gray
                    bg_color = '#f0f0f0'
                    text_color = '#cccccc'
                elif current_date == today:
                    # Today - light red
                    bg_color = '#ffebee'
                    text_color = '#c62828'
                else:
                    # Past dates - normal white
                    bg_color = '#ffffff'
                    text_color = '#333333'
                
                # Draw cell background
                rect = plt.Rectangle((day_num, len(cal) - week_num - 1), 1, 1, 
                                   facecolor=bg_color, edgecolor='#dddddd', linewidth=1)
                ax.add_patch(rect)
                
                # Draw day number
                ax.text(day_num + 0.5, len(cal) - week_num - 0.5, str(day), 
                        fontsize=16, ha='center', va='center', 
                        fontweight='bold', color=text_color)
                
                # Draw activity data for past dates
                if current_date <= today and date_str in data_dict:
                    data = data_dict[date_str]
                    active_hours = data['active_hours']
                    completion_rate = data.get('completion_rate', None)
                    
                    # Add activity info in the top-right of the cell
                    if completion_rate is not None:
                        info_text = f'{active_hours:.1f}h\n{completion_rate:.0f}%'
                    else:
                        info_text = f'{active_hours:.1f}h\nN/A'
                    
                    ax.text(day_num + 0.85, len(cal) - week_num - 0.15, info_text, 
                            fontsize=12, ha='right', va='top', 
                            color=text_color, alpha=0.9, fontweight='bold')
        
        # Add legend
        legend_y = -0.5
        ax.text(0, legend_y, 'Legend:', fontsize=10, fontweight='bold')
        ax.text(0, legend_y - 0.3, '• Light Gray: Future dates', fontsize=9, color='#666666')
        ax.text(3, legend_y - 0.3, '• Light Red: Today', fontsize=9, color='#666666')
        ax.text(5.5, legend_y - 0.3, f'• Standard: {LAB_WORK_HOURS}h/day', fontsize=9, color='#666666')
        
        plt.tight_layout()
        
        # Save chart
        if save_path is None:
            save_path = os.path.join(STATIC_DIR, f'calendar_{year}_{month:02d}.png')
        
        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close()
        
        # Clean up old images periodically (every 10th call)
        if hash(save_path) % 10 == 0:
            self.cleanup_old_images()
        
        logger.info(f"Calendar heatmap generated: {save_path}")
        return save_path
    
    def generate_trend_chart(self, start_date: datetime.date,
                            end_date: datetime.date, save_path: str = None) -> str:
        """Generate trend chart"""
        stats = self.db.get_daily_stats(start_date, end_date)
        
        if not stats:
            logger.warning(f"No data found from {start_date} to {end_date}")
            return None
        
        df = pd.DataFrame(stats)
        df['stat_date'] = pd.to_datetime(df['stat_date'])
        df['active_hours'] = df['total_active_minutes'] / 60
        
        # Create chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), dpi=CHART_DPI)
        
        # Activity duration trend
        ax1.plot(df['stat_date'], df['active_hours'], 
                marker='o', linewidth=2, markersize=6, color='#2ecc71')
        ax1.fill_between(df['stat_date'], 0, df['active_hours'], 
                        alpha=0.3, color='#2ecc71')
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Activity Duration (hours)', fontsize=12)
        ax1.set_title('Daily Activity Duration Trend', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # Add average line
        avg_hours = df['active_hours'].mean()
        ax1.axhline(y=avg_hours, color='red', linestyle='--', 
                   linewidth=2, label=f'Average: {avg_hours:.2f} hours')
        
        # Add work hours baseline (LAB_WORK_HOURS)
        ax1.axhline(y=LAB_WORK_HOURS, color='orange', linestyle='-.', 
                   linewidth=2, label=f'Standard Work Hours: {LAB_WORK_HOURS:.1f} hours')
        
        ax1.legend()
        
        # Busy index trend
        ax2.plot(df['stat_date'], df['average_busy_index'],
                marker='s', linewidth=2, markersize=6, color='#e74c3c')
        ax2.fill_between(df['stat_date'], 0, df['average_busy_index'],
                        alpha=0.3, color='#e74c3c')
        ax2.set_xlabel('Date', fontsize=12)
        ax2.set_ylabel('Busy Index', fontsize=12)
        ax2.set_title('Daily Average Busy Index Trend', fontsize=14, fontweight='bold')
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
        
        # Add average line
        avg_busy = df['average_busy_index'].mean()
        ax2.axhline(y=avg_busy, color='blue', linestyle='--',
                   linewidth=2, label=f'Average: {avg_busy:.2f}')
        ax2.legend()
        
        plt.tight_layout()
        
        # Save chart
        if save_path is None:
            save_path = os.path.join(STATIC_DIR,
                                    f'trend_{start_date}_{end_date}.png')
        
        plt.savefig(save_path, dpi=CHART_DPI, bbox_inches='tight')
        plt.close()
        
        # Clean up old images periodically (every 10th call)
        if hash(save_path) % 10 == 0:
            self.cleanup_old_images()
        
        logger.info(f"Trend chart generated: {save_path}")
        return save_path
    
    def export_to_csv(self, start_date: datetime.date,
                     end_date: datetime.date, output_path: str) -> bool:
        """Export data to CSV"""
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
        """Export data to Excel"""
        try:
            # Get daily statistics
            daily_stats = self.db.get_daily_stats(start_date, end_date)
            
            if not daily_stats:
                logger.warning("No data to export")
                return False
            
            # Create Excel writer
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                # Daily statistics sheet
                df_daily = pd.DataFrame(daily_stats)
                df_daily['active_hours'] = df_daily['total_active_minutes'] / 60
                df_daily['idle_hours'] = df_daily['total_idle_minutes'] / 60
                
                df_daily.to_excel(writer, sheet_name='Daily Statistics', index=False)
                
                # Summary statistics sheet
                week_report = self.get_custom_report(start_date, end_date)
                df_summary = pd.DataFrame([{
                    'Statistic': 'Total Work Days',
                    'Value': week_report['work_days']
                }, {
                    'Statistic': 'Total Active Hours',
                    'Value': week_report['total_active_hours']
                }, {
                    'Statistic': 'Average Daily Active Hours',
                    'Value': week_report['avg_daily_active_hours']
                }, {
                    'Statistic': 'Average Busy Index',
                    'Value': week_report['avg_busy_index']
                }, {
                    'Statistic': 'Average Work Intensity',
                    'Value': week_report['avg_work_intensity']
                }, {
                    'Statistic': 'Average Focus Score',
                    'Value': week_report['avg_focus_score']
                }, {
                    'Statistic': 'Average Efficiency',
                    'Value': week_report['avg_efficiency']
                }, {
                    'Statistic': 'Regularity Score',
                    'Value': week_report['regularity_score']
                }, {
                    'Statistic': 'Total Mouse Distance (m)',
                    'Value': week_report['total_mouse_distance_m']
                }])
                
                df_summary.to_excel(writer, sheet_name='Summary Statistics', index=False)
            
            logger.info(f"Data exported to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Excel export failed: {e}")
            return False


def main():
    """Main function (for testing)"""
    analyzer = DataAnalyzer()
    
    # Test today's summary
    today_summary = analyzer.get_today_summary()
    print("Today's Summary:", today_summary)
    
    # Test weekly report
    week_report = analyzer.get_week_report()
    print("\nWeekly Report:", week_report)
    
    # Generate charts
    today = datetime.now().date()
    analyzer.generate_busy_curve(today)
    analyzer.generate_trend_chart(today - timedelta(days=7), today)
    analyzer.generate_heatmap(today - timedelta(days=30), today)


if __name__ == '__main__':
    main()
