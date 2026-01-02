from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models.database import db, User, get_china_time

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    """根路径路由：跳转登录页"""
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录路由"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db.session.query(User).filter(User.username == username, User.password == password).first()
        if user:
            login_user(user)
            user.last_login = get_china_time()
            db.session.commit()
            flash('登录成功！', 'success')
            return redirect(url_for('main.dashboard'))
        flash('用户名或密码错误，请重试', 'danger')
    return render_template('login.html', title='登录')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """注册路由"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        existing_user = db.session.query(User).filter(User.username == username).first()
        if existing_user:
            flash('用户名已存在，请更换', 'danger')
            return redirect(url_for('auth.register'))
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='注册')

@auth_bp.route('/logout')
@login_required
def logout():
    """退出登录路由"""
    logout_user()
    flash('已安全退出登录', 'success')
    return redirect(url_for('auth.login'))