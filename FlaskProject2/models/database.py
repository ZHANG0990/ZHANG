from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import pytz

db = SQLAlchemy()

# 设置中国时区
china_tz = pytz.timezone('Asia/Shanghai')

def get_china_time():
    """获取中国当前时间"""
    return datetime.now(china_tz).replace(tzinfo=None)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    register_time = db.Column(db.DateTime, default=get_china_time)
    last_login = db.Column(db.DateTime)

class TrafficData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    source_ip = db.Column(db.String(50), nullable=False)
    dest_ip = db.Column(db.String(50), nullable=False)
    traffic_type = db.Column(db.String(20), nullable=False)
    predicted_type = db.Column(db.String(20))  # AI预测结果
    timestamp = db.Column(db.DateTime, default=get_china_time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class FileAnalysis(db.Model):
    """文件分析模型"""
    __tablename__ = 'file_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    is_white_traffic = db.Column(db.Boolean, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    analysis_time = db.Column(db.DateTime, default=get_china_time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    def __repr__(self):
        return f'<FileAnalysis {self.original_name}>'

class WhiteRule(db.Model):
    """白流量规则模型"""
    __tablename__ = 'white_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    rule_type = db.Column(db.String(20), nullable=False)  # ip, domain, port, protocol
    rule_value = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_china_time)
    updated_at = db.Column(db.DateTime, default=get_china_time, onupdate=get_china_time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<WhiteRule {self.name}>'

class Alert(db.Model):
    """告警信息模型"""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)  # danger, warning, info
    status = db.Column(db.String(20), default='pending')  # pending, resolved, ignored
    source_ip = db.Column(db.String(45))
    dest_ip = db.Column(db.String(45))
    traffic_id = db.Column(db.Integer, db.ForeignKey('traffic_data.id'))  # 关联流量记录
    created_at = db.Column(db.DateTime, default=get_china_time)
    resolved_at = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # 建立与TrafficData的关系
    traffic = db.relationship('TrafficData', backref=db.backref('alerts', lazy=True))
    
    def __repr__(self):
        return f'<Alert {self.title}>'

class SystemSetting(db.Model):
    """系统设置模型"""
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=get_china_time, onupdate=get_china_time)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<SystemSetting {self.key}>'

class UserProfile(db.Model):
    """用户配置模型"""
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    avatar = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=get_china_time)
    updated_at = db.Column(db.DateTime, default=get_china_time, onupdate=get_china_time)
    
    # 建立与User的关系
    user = db.relationship('User', backref=db.backref('profile', uselist=False))
    
    def __repr__(self):
        return f'<UserProfile {self.user_id}>'