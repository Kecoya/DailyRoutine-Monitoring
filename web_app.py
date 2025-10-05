"""
Web应用 - Flask服务器
提供美观的Web界面查看统计结果
"""
import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file
import threading

from database import Database
from analyzer import DataAnalyzer
from monitor_service import ActivityMonitor
from config import WEB_HOST, WEB_PORT, DEBUG_MODE, STATIC_DIR, TEMPLATES_DIR, DATA_DIR

logger = logging.getLogger(__name__)

app = Flask(__name__, 
           static_folder=STATIC_DIR,
           template_folder=TEMPLATES_DIR)

# 全局变量
monitor = None
analyzer = DataAnalyzer()
db = Database()


@app.route('/')
def index():
    """首页"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """获取当前监控状态"""
    if monitor:
        status = monitor.get_current_status()
        return jsonify({
            'success': True,
            'data': status
        })
    else:
        return jsonify({
            'success': False,
            'message': '监控服务未启动'
        })


@app.route('/api/today')
def get_today():
    """获取今日数据"""
    try:
        summary = analyzer.get_today_summary()
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logger.error(f"获取今日数据失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/week')
def get_week():
    """获取周报"""
    try:
        report = analyzer.get_week_report()
        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        logger.error(f"获取周报失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/month')
def get_month():
    """获取月报"""
    try:
        year = request.args.get('year', type=int)
        month = request.args.get('month', type=int)
        
        report = analyzer.get_month_report(year, month)
        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        logger.error(f"获取月报失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/custom')
def get_custom():
    """获取自定义时间段报表"""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        
        report = analyzer.get_custom_report(start_date, end_date)
        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        logger.error(f"获取自定义报表失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/chart/busy_curve')
def get_busy_curve():
    """获取忙碌度曲线图"""
    try:
        date_str = request.args.get('date')
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = datetime.now().date()
        
        chart_path = analyzer.generate_busy_curve(date)
        
        if chart_path and os.path.exists(chart_path):
            return jsonify({
                'success': True,
                'data': {
                    'url': f'/static/{os.path.basename(chart_path)}'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '生成图表失败或无数据'
            })
    except Exception as e:
        logger.error(f"生成忙碌度曲线图失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/chart/heatmap')
def get_heatmap():
    """获取热力图"""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if start_str and end_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
        
        chart_path = analyzer.generate_heatmap(start_date, end_date)
        
        if chart_path and os.path.exists(chart_path):
            return jsonify({
                'success': True,
                'data': {
                    'url': f'/static/{os.path.basename(chart_path)}'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '生成图表失败或无数据'
            })
    except Exception as e:
        logger.error(f"生成热力图失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/chart/trend')
def get_trend():
    """获取趋势图"""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        if start_str and end_str:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        else:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
        
        chart_path = analyzer.generate_trend_chart(start_date, end_date)
        
        if chart_path and os.path.exists(chart_path):
            return jsonify({
                'success': True,
                'data': {
                    'url': f'/static/{os.path.basename(chart_path)}'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '生成图表失败或无数据'
            })
    except Exception as e:
        logger.error(f"生成趋势图失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/export/csv')
def export_csv():
    """导出CSV"""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        
        filename = f'activity_report_{start_date}_{end_date}.csv'
        output_path = os.path.join(DATA_DIR, filename)
        
        success = analyzer.export_to_csv(start_date, end_date, output_path)
        
        if success:
            return send_file(output_path, 
                           as_attachment=True,
                           download_name=filename)
        else:
            return jsonify({
                'success': False,
                'message': '导出失败'
            })
    except Exception as e:
        logger.error(f"导出CSV失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


@app.route('/api/export/excel')
def export_excel():
    """导出Excel"""
    try:
        start_str = request.args.get('start')
        end_str = request.args.get('end')
        
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
        
        filename = f'activity_report_{start_date}_{end_date}.xlsx'
        output_path = os.path.join(DATA_DIR, filename)
        
        success = analyzer.export_to_excel(start_date, end_date, output_path)
        
        if success:
            return send_file(output_path,
                           as_attachment=True,
                           download_name=filename)
        else:
            return jsonify({
                'success': False,
                'message': '导出失败'
            })
    except Exception as e:
        logger.error(f"导出Excel失败: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        })


def start_web_server(monitor_instance):
    """启动Web服务器"""
    global monitor
    monitor = monitor_instance
    
    logger.info(f"Web服务器启动于 http://{WEB_HOST}:{WEB_PORT}")
    app.run(host=WEB_HOST, port=WEB_PORT, debug=DEBUG_MODE, use_reloader=False)


def run_in_thread(monitor_instance):
    """在独立线程中运行Web服务器"""
    thread = threading.Thread(target=start_web_server, args=(monitor_instance,), daemon=True)
    thread.start()
    return thread


if __name__ == '__main__':
    # 仅用于测试
    start_web_server(None)

