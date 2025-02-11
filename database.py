from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def init_app(app):
    """初始化数据库应用"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

class Note(db.Model):
    """社交媒体笔记表"""
    __tablename__ = 'notes'
    
    note_id = db.Column(db.String(50), primary_key=True)
    description = db.Column(db.Text)
    note_url = db.Column(db.String(255))
    create_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联票务信息
    tickets = db.relationship('Ticket', backref='note', lazy=True)

class Ticket(db.Model):
    """票务信息表"""
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.String(50), db.ForeignKey('notes.note_id'))
    is_ticket_resale = db.Column(db.Boolean, default=True)
    event_name = db.Column(db.String(100))
    city = db.Column(db.String(50))
    event_date = db.Column(db.Date)
    area = db.Column(db.String(50))
    price = db.Column(db.String(100))
    quantity = db.Column(db.String(50))
    contact = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WorkflowExecution(db.Model):
    """工作流执行记录表"""
    __tablename__ = 'workflow_executions'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer)
    cost = db.Column(db.String(50))
    msg = db.Column(db.Text)
    status = db.Column(db.String(20), default='running')
    raw_response = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def init_db():
    """初始化数据库表"""
    db.create_all()

def save_note(note_data):
    """保存社交媒体笔记"""
    note = Note.query.get(note_data['note_id'])
    if note:
        # 更新现有记录
        for key, value in note_data.items():
            setattr(note, key, value)
    else:
        # 创建新记录
        note = Note(**note_data)
        db.session.add(note)
    
    db.session.commit()
    return note

def save_ticket_info(note_id, ticket_info):
    """保存票务分析结果"""
    ticket = Ticket.query.filter_by(note_id=note_id).first()
    if ticket:
        # 更新现有记录
        for key, value in ticket_info.items():
            setattr(ticket, key, value)
    else:
        # 创建新记录
        ticket_info['note_id'] = note_id
        ticket = Ticket(**ticket_info)
        db.session.add(ticket)
    
    db.session.commit()
    return ticket

def get_unprocessed_notes():
    """获取未处理的笔记"""
    # 查找没有关联票务信息的笔记
    return Note.query.outerjoin(Ticket).filter(Ticket.id == None).all()

def get_ticket_by_event(event_name):
    """根据演出名称查询票务信息"""
    return Ticket.query.filter(Ticket.event_name.ilike(f'%{event_name}%')).all()

def get_tickets_by_date_range(start_date, end_date):
    """根据日期范围查询票务信息"""
    return Ticket.query.filter(
        Ticket.event_date >= start_date,
        Ticket.event_date <= end_date
    ).all()

def get_recent_tickets(limit=10):
    """获取最近的票务信息"""
    return Ticket.query.order_by(Ticket.created_at.desc()).limit(limit).all()

def search_tickets(query):
    """搜索票务信息"""
    return Ticket.query.filter(
        db.or_(
            Ticket.event_name.ilike(f'%{query}%'),
            Ticket.area.ilike(f'%{query}%'),
            Ticket.notes.ilike(f'%{query}%')
        )
    ).all()

def get_note_by_id(note_id):
    """根据ID获取笔记"""
    return Note.query.get(note_id)

def get_ticket_by_note_id(note_id):
    """根据笔记ID获取票务信息"""
    return Ticket.query.filter_by(note_id=note_id).first()

def clear_all():
    """清空所有数据（仅用于测试）"""
    db.drop_all()
    db.create_all() 