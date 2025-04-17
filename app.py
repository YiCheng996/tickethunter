"""
TicketHunter - 票务监控系统

业务流程：
1. 用户搜索流程
   - 用户输入关键词进行搜索
   - 系统创建搜索任务并记录到数据库
   - 调用COZE API获取小红书笔记列表
   - 使用通义千问AI分析笔记内容，提取票务信息
   - 实时推送分析结果到前端展示

2. 数据处理流程
   - 解析API返回的笔记数据
   - 过滤已存在的笔记，避免重复处理
   - 使用AI模型分析笔记内容，识别票务信息
   - 将票务信息保存到数据库
   - 通过SSE推送新数据到前端

3. 实时通信机制
   - 使用Server-Sent Events (SSE)实现服务器推送
   - 支持任务状态实时更新
   - 支持票务信息实时展示
   - 自动重连机制确保连接稳定


主要组件：
1. Monitor类：负责任务管理和监控
2. 数据模型：Note（笔记）和Ticket（票务）
3. WorkflowExecution：任务执行记录
4. EventQueue：实时消息队列

技术栈：
- Flask：Web框架
- SQLite：数据存储
- 通义千问：AI分析
- SSE：实时通信
- Bootstrap：前端UI
"""

import os
import sys
import socket
import platform
import subprocess
import time
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
import requests
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import re
from flask_login import LoginManager, UserMixin, login_required
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
from logging.handlers import RotatingFileHandler
from database import db, Note, Ticket, WorkflowExecution, init_db
from queue import Queue, Empty
import threading
import dashscope
from dashscope import Generation

# 创建事件队列
event_queue = Queue()

# 创建扩展对象
cache = Cache()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)

# 配置日志
def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler('log/tickethunter.log', maxBytes=1024*1024, backupCount=5, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    # 初始化各种扩展
    db.init_app(app)
    cache.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    
    return app

# 创建应用实例
app = create_app()

# 设置通义千问API密钥
dashscope.api_key = app.config['DASHSCOPE_API_KEY']

# 监控类
class Monitor:
    def __init__(self):
        self.keywords = set()
        self.is_running = False
        self.scheduler = BackgroundScheduler()
        
    def start(self):
        """启动监控"""
        if not self.is_running:
            self.is_running = True
            # 启动调度器
            self.scheduler.start()
            # 为每个已有的关键词添加定时任务
            for keyword in self.keywords:
                self._add_scheduled_task(keyword)
            app.logger.info("监控服务已启动")
            
    def stop(self):
        """停止监控"""
        if self.is_running:
            self.is_running = False
            self.scheduler.shutdown()
            app.logger.info("监控服务已停止")
            
    def add_keyword(self, keyword):
        """添加监控关键词"""
        self.keywords.add(keyword)
        # 如果监控服务正在运行，立即为新关键词添加定时任务
        if self.is_running:
            self._add_scheduled_task(keyword)
        app.logger.info(f"已添加监控关键词: {keyword}")
        
    def remove_keyword(self, keyword):
        """移除监控关键词"""
        if keyword in self.keywords:
            self.keywords.remove(keyword)
            # 移除对应的定时任务
            job_id = f"monitor_{keyword}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            app.logger.info(f"已移除监控关键词: {keyword}")
            
    def _add_scheduled_task(self, keyword):
        """添加定时任务"""
        job_id = f"monitor_{keyword}"
        # 如果任务已存在，先移除
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        # 添加新的定时任务，每10分钟执行一次
        self.scheduler.add_job(
            execute_search_task,
            'interval',
            minutes=10,
            id=job_id,
            args=[keyword],
            replace_existing=True
        )
        app.logger.info(f"已为关键词 {keyword} 添加定时任务")

# 创建监控实例
monitor = Monitor()

def analyze_ticket_content(note_desc):
    """使用通义千问分析笔记内容中的票务信息"""
    app.logger.info(f"开始分析笔记内容: {note_desc}")
    prompt = f"""
请分析以下小红书笔记内容，判断是否涉及演出票务转售。如果涉及，请提取以下信息：
1. 是否转售票务（true/false）
2. 演出名称（如：上海Major）
3. 城市（如：上海）
4. 场次日期（如：2024-12-15）
5. 区域位置（如：B区）
6. 票价信息（如：1000元/张）
7. 数量（如：2张）
8. 联系方式（如：私信）
9. 其他备注（如：可刀）

原文：{note_desc}

请直接返回JSON格式数据，不要包含任何其他说明文字：
{{
    "is_ticket_resale": true/false,
    "event_name": "演出名称",
    "city": "城市",
    "event_date": "yyyy-mm-dd",
    "area": "区域位置",
    "price": "票价信息",
    "quantity": "数量",
    "contact": "联系方式",
    "notes": "其他备注"
}}

如果不是票务转售内容，只返回 {{"is_ticket_resale": false}}，不要返回多余解释
"""
    try:
        app.logger.info("开始调用通义千问API")
        response = Generation.call(
            model='qwen-turbo',
            prompt=prompt,
            temperature=0.1,
            top_p=0.8,
            result_format='text'
        )
        
        app.logger.info(f"通义千问API响应: {response.output.text}")
        
        if response.status_code == 200:
            try:
                # 尝试从响应文本中提取JSON部分
                text = response.output.text
                json_start = text.find('{')
                json_end = text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = text[json_start:json_end]
                    result = json.loads(json_str)
                    app.logger.info(f"解析票务信息结果: {json.dumps(result, ensure_ascii=False)}")
                    return result
                else:
                    app.logger.error("未找到JSON数据")
                    return {"is_ticket_resale": False}
            except json.JSONDecodeError as e:
                app.logger.error(f"解析JSON失败: {str(e)}, 原文: {response.output.text}")
                return {"is_ticket_resale": False}
        else:
            app.logger.error(f"通义千问API调用失败: {response.status_code}")
            return {"is_ticket_resale": False}
            
    except Exception as e:
        app.logger.error(f"调用AI服务出错: {str(e)}")
        return {"is_ticket_resale": False}

def execute_search_task(keyword):
    """执行搜索任务"""
    app.logger.info(f"开始执行搜索任务，关键词: {keyword}")
    workflow_execution = None
    
    try:
        # 检查cookie是否过期
        try:
            update_time = datetime.strptime(app.config['XIAOHONGSHU_COOKIE_UPDATE_TIME'], '%Y-%m-%d')
            days_passed = (datetime.now() - update_time).days
            if days_passed >= app.config['XIAOHONGSHU_COOKIE_EXPIRE_DAYS']:
                app.logger.error(f"Cookie已过期{days_passed}天，请更新Cookie")
                workflow_execution = WorkflowExecution(
                    code=400,
                    msg=f"Cookie已过期{days_passed}天，请更新Cookie",
                    status='failed'
                )
                db.session.add(workflow_execution)
                db.session.commit()
                notify_clients('task_update', {
                    'task_id': workflow_execution.id,
                    'status': 'failed',
                    'message': f"Cookie已过期{days_passed}天，请更新Cookie"
                })
                return False
        except Exception as e:
            app.logger.error(f"检查Cookie更新时间时出错: {str(e)}")
        
        app.logger.info("开始调用COZE API")
        # 调用COZE API
        url = "https://api.coze.cn/v1/workflow/run"
        headers = {
            "Authorization": f"Bearer {app.config['COZE_API_KEY']}",
            "Content-Type": "application/json"
        }
        data = {
            "parameters": {
                "input": keyword,
                "cookie": app.config['XIAOHONGSHU_COOKIE']
            },
            "workflow_id": app.config['COZE_WORKFLOW_ID']
        }

        app.logger.info(f"发送请求到COZE API，数据: {json.dumps(data)}")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        response_data = response.json()
        app.logger.info(f"COZE API响应: {json.dumps(response_data)}")
        
        # 保存工作流执行记录
        workflow_execution = WorkflowExecution(
            code=response_data.get('status_code', 200),
            cost=response_data.get('usage', {}).get('total_tokens', 0),
            msg=keyword,
            status='running',
            raw_response=response_data
        )
        db.session.add(workflow_execution)
        db.session.commit()
        
        # 通知客户端任务开始
        notify_clients('task_update', {
            'task_id': workflow_execution.id,
            'status': 'running',
            'message': f'正在搜索：{keyword}'
        })
        
        # 处理返回的数据
        content_data = json.loads(response_data['data'])
        notes_data = content_data.get('output', [])
        
        if not notes_data:
            workflow_execution.status = 'completed'
            db.session.commit()
            notify_clients('task_update', {
                'task_id': workflow_execution.id,
                'status': 'completed',
                'message': '未找到相关数据'
            })
            return False
            
        total_notes = len(notes_data)
        processed_notes = 0
        
        for note_item in notes_data:
            note_data = note_item['note']
            processed_notes += 1
            
            # 检查笔记是否已存在
            existing_note = db.session.get(Note, note_data.get('note_id'))
            if existing_note:
                app.logger.info(f"笔记已存在，跳过: {note_data.get('note_id')}")
                continue
            
            # 创建新笔记
            note = Note(
                note_id=note_data.get('note_id'),
                description=note_data.get('note_desc'),
                note_url=note_data.get('note_url'),
                create_time=datetime.strptime(note_data.get('note_create_time', ''), '%Y-%m-%d %H:%M:%S')
                if note_data.get('note_create_time') else None
            )
            db.session.add(note)
            db.session.commit()
            
            app.logger.info(f"正在处理第 {processed_notes}/{total_notes} 条笔记")
            
            # 分析票务信息
            ticket_info = analyze_ticket_content(note.description)
            app.logger.info(f"票务分析结果: {json.dumps(ticket_info, ensure_ascii=False)}")
            
            if ticket_info.get('is_ticket_resale'):
                # 创建票务信息
                ticket = Ticket(
                    note_id=note.note_id,
                    is_ticket_resale=ticket_info.get('is_ticket_resale', True),
                    event_name=ticket_info.get('event_name', ''),
                    city=ticket_info.get('city', ''),
                    event_date=datetime.strptime(ticket_info['event_date'], '%Y-%m-%d').date()
                    if ticket_info.get('event_date') else None,
                    area=ticket_info.get('area', ''),
                    price=ticket_info.get('price', ''),
                    quantity=ticket_info.get('quantity', ''),
                    contact=ticket_info.get('contact', ''),
                    notes=ticket_info.get('notes', '')
                )
                db.session.add(ticket)
                db.session.commit()
                
                # 通知客户端新票务信息
                notify_clients('ticket_update', {
                    'task_id': workflow_execution.id,
                    'ticket': {
                        'event_name': ticket.event_name,
                        'city': ticket.city,
                        'event_date': ticket.event_date.strftime('%Y-%m-%d') if ticket.event_date else None,
                        'price': ticket.price,
                        'area': ticket.area,
                        'quantity': ticket.quantity,
                        'contact': ticket.contact,
                        'notes': ticket.notes,
                        'note_url': note.note_url
                    }
                })
                
                # 更新任务状态，显示处理进度
                notify_clients('task_update', {
                    'task_id': workflow_execution.id,
                    'status': 'running',
                    'message': f'已处理 {processed_notes}/{total_notes} 条数据'
                })
            else:
                app.logger.info(f"非票务信息，跳过: {note.note_id}")
        
        workflow_execution.status = 'completed'
        db.session.commit()
        notify_clients('task_update', {
            'task_id': workflow_execution.id,
            'status': 'completed',
            'message': f'搜索完成，共处理 {total_notes} 条数据'
        })
        return True
        
    except Exception as e:
        logger.error(f"执行搜索任务失败: {str(e)}")
        if workflow_execution:
            workflow_execution.status = 'failed'
            db.session.commit()
            notify_clients('task_update', {
                'task_id': workflow_execution.id,
                'status': 'failed',
                'message': str(e)
            })
        return False

# 路由和视图函数
class User(UserMixin):
    pass

@login_manager.user_loader
def load_user(user_id):
    return User()

@app.route('/')
def index():
    """首页"""
    recent_tickets = Ticket.query.order_by(Ticket.created_at.desc()).limit(10).all()
    return render_template('index.html', tickets=recent_tickets)

@app.route('/search', methods=['POST'])
@limiter.limit("10 per minute")
def search():
    """搜索并创建新任务"""
    keyword = request.form.get('keyword', '')
    app.logger.info(f"收到搜索请求，关键词: {keyword}")
    
    try:
        app.logger.info("开始执行搜索任务")
        result = execute_search_task(keyword)  # 直接同步执行
        return jsonify({'success': result})
    except Exception as e:
        app.logger.error(f"搜索请求处理失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/tickets', methods=['GET'])
@cache.cached(timeout=60)
def get_tickets():
    """获取票务信息API"""
    try:
        task_id = request.args.get('task_id')
        query = Ticket.query.join(Note)
        
        if task_id:
            task = WorkflowExecution.query.get(task_id)
            if task and task.created_at:
                query = query.filter(Ticket.created_at >= task.created_at)
        
        tickets = query.order_by(Ticket.created_at.desc()).limit(50).all()
        return jsonify([{
            'id': t.id,
            'event_name': t.event_name,
            'city': t.city,
            'event_date': t.event_date.strftime('%Y-%m-%d') if t.event_date else None,
            'area': t.area,
            'price': t.price,
            'quantity': t.quantity,
            'contact': t.contact,
            'notes': t.notes,
            'note_url': t.note.note_url if t.note else None,
            'created_at': t.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for t in tickets])
    except Exception as e:
        app.logger.error(f"获取票务信息失败: {str(e)}")
        return jsonify([])

@app.route('/api/monitor/start', methods=['POST'])
@login_required
def start_monitor():
    """启动监控"""
    monitor.start()
    return jsonify({"status": "success", "message": "Monitor started"})

@app.route('/api/monitor/stop', methods=['POST'])
@login_required
def stop_monitor():
    """停止监控"""
    monitor.stop()
    return jsonify({"status": "success", "message": "Monitor stopped"})

@app.route('/api/monitor/add_keyword', methods=['POST'])
def add_monitor_keyword():
    """添加监控关键词"""
    keyword = request.form.get('keyword', '')
    if not keyword:
        return jsonify({'success': False, 'error': '关键词不能为空'})
    
    try:
        monitor.add_keyword(keyword)
        return jsonify({'success': True, 'message': f'已添加关键词：{keyword}'})
    except Exception as e:
        app.logger.error(f"添加监控关键词失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/monitor/remove_keyword', methods=['POST'])
def remove_monitor_keyword():
    """移除监控关键词"""
    keyword = request.form.get('keyword', '')
    if not keyword:
        return jsonify({'success': False, 'error': '关键词不能为空'})
    
    try:
        monitor.remove_keyword(keyword)
        return jsonify({'success': True, 'message': f'已移除关键词：{keyword}'})
    except Exception as e:
        app.logger.error(f"移除监控关键词失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/stream')
def stream():
    """事件流接口"""
    def event_stream():
        try:
            while True:
                try:
                    # 每30秒发送一次心跳包
                    message = event_queue.get(timeout=30)
                    if message:
                        yield f"data: {json.dumps(message)}\n\n"
                except Empty:
                    # 发送心跳包保持连接
                    yield ": heartbeat\n\n"
                    continue
                except Exception as e:
                    app.logger.error(f"事件流处理错误: {str(e)}")
                    break
        except GeneratorExit:
            app.logger.info("客户端断开连接")
        except Exception as e:
            app.logger.error(f"事件流发生错误: {str(e)}")
    
    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # 禁用 Nginx 缓冲
        }
    )

def notify_clients(event_type, data):
    """向所有连接的客户端发送事件"""
    message = {
        'type': event_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    event_queue.put(message)

@app.route('/tasks', methods=['GET'])
def get_tasks():
    """获取任务列表"""
    try:
        tasks = WorkflowExecution.query.order_by(
            WorkflowExecution.created_at.desc()
        ).limit(20).all()
        
        return jsonify([{
            'id': task.id,
            'code': task.code or 200,
            'cost': task.cost,
            'msg': task.msg or '搜索任务',
            'status': task.status or 'completed',
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for task in tasks])
    except Exception as e:
        app.logger.error(f"获取任务列表失败: {str(e)}")
        return jsonify([])

@app.route('/tasks/<int:task_id>/stop', methods=['POST'])
def stop_task(task_id):
    """停止任务"""
    try:
        workflow_execution = WorkflowExecution.query.get(task_id)
        if workflow_execution:
            workflow_execution.status = 'stopped'
            db.session.commit()
            notify_clients('task_update', {'task_id': task_id, 'status': 'stopped'})
            return jsonify({'success': True, 'message': '任务已停止'})
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """删除任务及相关数据"""
    try:
        workflow_execution = WorkflowExecution.query.get(task_id)
        if workflow_execution:
            # 获取任务创建时间，用于查找相关数据
            task_created_at = workflow_execution.created_at
            
            # 查找在任务创建时间之后创建的票务信息
            tickets = Ticket.query.join(Note).filter(
                Ticket.created_at >= task_created_at
            ).all()
            
            # 收集所有相关的note_ids
            note_ids = set(ticket.note_id for ticket in tickets)
            
            # 删除票务信息
            for ticket in tickets:
                db.session.delete(ticket)
            
            # 删除相关的笔记
            for note_id in note_ids:
                note = Note.query.get(note_id)
                if note:
                    db.session.delete(note)
            
            # 删除任务记录
            if workflow_execution.status == 'running':
                workflow_execution.status = 'stopped'
            db.session.delete(workflow_execution)
            
            # 提交所有更改
            db.session.commit()
            
            # 通知客户端
            notify_clients('task_update', {'task_id': task_id, 'action': 'deleted'})
            return jsonify({'success': True, 'message': '任务及相关数据已删除'})
            
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    except Exception as e:
        app.logger.error(f"删除任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

def update_task_status(task_id, status, message=None):
    """更新任务状态并通知客户端"""
    try:
        workflow_execution = WorkflowExecution.query.get(task_id)
        if workflow_execution:
            workflow_execution.status = status
            if message:
                workflow_execution.msg = message
            db.session.commit()
            notify_clients('task_update', {
                'task_id': task_id,
                'status': status,
                'message': message
            })
    except Exception as e:
        app.logger.error(f"更新任务状态失败: {str(e)}")

def main():
    """主函数"""
    logger.info("开始启动TicketHunter服务...")
    
    # 初始化数据库
    with app.app_context():
        db.create_all()
    
    # 启动服务
    try:
        app.run(host='0.0.0.0', port=5000, debug=app.config['DEBUG'])
    except Exception as e:
        logger.error(f"Flask应用启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("正在停止服务...")
        sys.exit(0) 