"""
Web应用 - Flask服务器
提供美观的Web界面查看统计结果
"""
import os
import socket
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file, send_from_directory, Response
import threading

from database import Database
from analyzer import DataAnalyzer
from monitor_service import ActivityMonitor
from audio_service import AudioService
from config import WEB_HOST, WEB_PORT, DEBUG_MODE, STATIC_DIR, TEMPLATES_DIR, DATA_DIR, \
    CAPTURE_TEMP_DIR, CAPTURE_PERMANENT_DIR, CAPTURE_GIF_DIR, AUDIO_SESSIONS_DIR

logger = logging.getLogger(__name__)

app = Flask(__name__,
            static_folder=STATIC_DIR,
            template_folder=TEMPLATES_DIR)

# 全局变量
monitor = None
analyzer = DataAnalyzer()
db = Database()
audio_service = AudioService()


def is_port_in_use(host: str, port: int) -> bool:
    """检测端口是否被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


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

        if month is not None and (month < 1 or month > 12):
            return jsonify({'success': False, 'message': '月份必须在 1-12 之间'})
        if year is not None and year < 2000:
            return jsonify({'success': False, 'message': '年份不合法'})

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

        if not start_str or not end_str:
            return jsonify({
                'success': False,
                'message': '请提供 start 和 end 日期参数'
            })

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

        if not start_str or not end_str:
            return jsonify({'success': False, 'message': '请提供日期参数'})

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

        if not start_str or not end_str:
            return jsonify({'success': False, 'message': '请提供日期参数'})

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


# ===== 摄像头抓拍 API =====

@app.route('/api/camera/status')
def get_camera_status():
    """获取摄像头抓拍服务状态"""
    if monitor and hasattr(monitor, 'camera_service'):
        return jsonify({
            'success': True,
            'data': monitor.camera_service.get_status()
        })
    return jsonify({'success': False, 'message': '摄像头服务未初始化'})


@app.route('/api/camera/captures')
def get_captures():
    """获取抓拍图片列表"""
    capture_type = request.args.get('type', 'temp')  # temp | permanent
    limit = request.args.get('limit', 20, type=int)

    if not monitor or not hasattr(monitor, 'camera_service'):
        return jsonify({'success': False, 'message': '摄像头服务未初始化'})

    files = monitor.camera_service.get_recent_captures(capture_type, limit)
    return jsonify({'success': True, 'data': files})


@app.route('/api/camera/gifs')
def get_gifs():
    """获取 GIF 动图列表"""
    limit = request.args.get('limit', 20, type=int)

    if not monitor or not hasattr(monitor, 'camera_service'):
        return jsonify({'success': False, 'message': '摄像头服务未初始化'})

    files = monitor.camera_service.get_recent_gifs(limit)
    return jsonify({'success': True, 'data': files})


@app.route('/api/camera/capture_now', methods=['POST'])
def capture_now():
    """手动立即抓拍一张照片（按需打开/释放摄像头）"""
    if not monitor or not getattr(monitor, 'camera_service', None):
        return jsonify({'success': False, 'message': '摄像头服务未初始化'})

    is_permanent = request.args.get('permanent', 'false').lower() == 'true'
    try:
        result = monitor.camera_service.capture_now(is_permanent=is_permanent)
        return jsonify(result)
    except Exception as e:
        logger.error(f"立即抓拍失败: {e}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)})


@app.route('/captures/<path:filename>')
def serve_capture(filename):
    """提供抓拍图片/GIF文件服务"""
    # 防止路径遍历：只允许文件名，不允许包含目录分隔符
    safe_name = os.path.basename(filename)
    if safe_name != filename:
        return jsonify({'success': False, 'message': '非法文件名'}), 400
    for directory in [CAPTURE_PERMANENT_DIR, CAPTURE_TEMP_DIR, CAPTURE_GIF_DIR]:
        filepath = os.path.join(directory, safe_name)
        if os.path.exists(filepath):
            return send_from_directory(directory, safe_name)
    return jsonify({'success': False, 'message': '文件不存在'}), 404


# ===== 在场检测 API =====

@app.route('/api/camera/presence/status')
def presence_status():
    """获取在场检测状态"""
    if not monitor or not getattr(monitor, 'camera_service', None):
        return jsonify({'success': False, 'message': '摄像头服务未初始化'})
    return jsonify({'success': True, 'data': monitor.camera_service.get_presence_status()})


@app.route('/api/camera/presence/on', methods=['POST'])
def presence_on():
    """开启在场检测"""
    if not monitor or not getattr(monitor, 'camera_service', None):
        return jsonify({'success': False, 'message': '摄像头服务未初始化'})
    return jsonify(monitor.camera_service.start_presence_detection())


@app.route('/api/camera/presence/off', methods=['POST'])
def presence_off():
    """停止在场检测"""
    if not monitor or not getattr(monitor, 'camera_service', None):
        return jsonify({'success': False, 'message': '摄像头服务未初始化'})
    return jsonify(monitor.camera_service.stop_presence_detection())


# ===== 音频监听 API =====

@app.route('/api/audio/status')
def get_audio_status():
    """获取音频监听服务状态"""
    return jsonify({'success': True, 'data': audio_service.get_status()})


@app.route('/api/audio/devices')
def list_audio_devices():
    """列出可用输入设备"""
    return jsonify({'success': True, 'data': audio_service.list_input_devices()})


@app.route('/api/audio/start', methods=['POST'])
def audio_start():
    """开始监听。可选 ?device=<索引> 指定输入设备"""
    device = request.args.get('device', type=int)
    result = audio_service.start_listening(device=device)
    return jsonify(result)


@app.route('/api/audio/asr/on', methods=['POST'])
def audio_asr_on():
    """开启实时转写"""
    return jsonify(audio_service.enable_asr())


@app.route('/api/audio/asr/off', methods=['POST'])
def audio_asr_off():
    """关闭实时转写"""
    return jsonify(audio_service.disable_asr())


@app.route('/api/audio/sound/on', methods=['POST'])
def audio_sound_on():
    """开启声音触发模式（检测到声音自动转写）"""
    return jsonify(audio_service.enable_sound_activated())


@app.route('/api/audio/sound/off', methods=['POST'])
def audio_sound_off():
    """关闭声音触发模式"""
    return jsonify(audio_service.disable_sound_activated())


@app.route('/api/audio/stop', methods=['POST'])
def audio_stop():
    """停止监听"""
    result = audio_service.stop_listening()
    return jsonify(result)


@app.route('/api/audio/stream')
def audio_stream():
    """
    实时事件流（SSE）：推送音频块（event:audio）、转写文本（event:transcript）、
    段开始/状态变更等事件。浏览器用 EventSource 订阅。
    """
    q = audio_service.subscribe()

    def generate():
        try:
            while True:
                try:
                    msg = q.get(timeout=15)
                    yield msg
                except Exception:
                    # 队列空超时，发 keepalive 保持连接
                    yield ': ping\n\n'
        finally:
            audio_service.unsubscribe(q)

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive',
    }
    return Response(generate(), mimetype='text/event-stream', headers=headers)


@app.route('/audio_sessions/<path:filename>')
def serve_audio_file(filename):
    """提供音频会话文件服务（WAV / transcript.txt），带路径遍历防护"""
    safe = os.path.normpath(filename)
    # 只允许 <session_id>/<file> 形式，禁止再上溯
    if safe.startswith('..') or os.path.isabs(safe):
        return jsonify({'success': False, 'message': '非法路径'}), 400
    full = os.path.join(AUDIO_SESSIONS_DIR, safe)
    if not os.path.abspath(full).startswith(os.path.abspath(AUDIO_SESSIONS_DIR)):
        return jsonify({'success': False, 'message': '非法路径'}), 400
    if os.path.exists(full) and os.path.isfile(full):
        directory = os.path.dirname(full)
        base = os.path.basename(full)
        return send_from_directory(directory, base)
    return jsonify({'success': False, 'message': '文件不存在'}), 404


def start_web_server(monitor_instance):
    """启动Web服务器"""
    global monitor
    monitor = monitor_instance

    # 检测端口占用
    if is_port_in_use(WEB_HOST, WEB_PORT):
        logger.error(f"端口 {WEB_PORT} 已被占用，Web服务器无法启动！"
                      f"请检查是否有其他实例在运行。")
        return

    logger.info(f"Web服务器启动于 http://{WEB_HOST}:{WEB_PORT}")
    # threaded=True 必需：SSE 是长连接，每个连接占用一个线程
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False, use_reloader=False, threaded=True)


def run_in_thread(monitor_instance):
    """在独立线程中运行Web服务器"""
    thread = threading.Thread(target=start_web_server, args=(monitor_instance,), daemon=True)
    thread.start()
    return thread


if __name__ == '__main__':
    # 仅用于测试
    start_web_server(None)
