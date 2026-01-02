# 路由模块初始化文件
from .auth import auth_bp
from .main import main_bp
from .api import api_bp
from .file_drop import file_drop_bp

def register_blueprints(app):
    """注册所有蓝图"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(file_drop_bp)