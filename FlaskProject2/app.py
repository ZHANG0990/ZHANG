from flask import Flask, jsonify
from flask_login import LoginManager
from config.settings import config
from models import db, User
from routes import register_blueprints
import os

def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 确保上传目录存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 初始化数据库
    db.init_app(app)
    
    # 初始化 Flask-Login
    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))
    
    # 添加全局错误处理
    @app.errorhandler(500)
    def internal_error(error):
        print(f"[ERROR] 500错误: {error}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500
    
    @app.errorhandler(404)
    def not_found_error(error):
        print(f"[ERROR] 404错误: {error}")
        return jsonify({
            'success': False,
            'message': '页面未找到'
        }), 404
    
    # 注册蓝图
    register_blueprints(app)
    
    # 初始化数据库（首次运行时创建表）
    with app.app_context():
        try:
            db.create_all()
            print("[INFO] 数据库表创建/检查完成")
        except Exception as e:
            print(f"[ERROR] 数据库初始化失败: {e}")
    
    return app

# 创建应用实例
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)