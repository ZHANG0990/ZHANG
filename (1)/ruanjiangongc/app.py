# app.py - 修复数据库初始化问题
import os
import datetime
import random
import time
import ctypes
import winsound
import subprocess
import threading
import signal
import sys
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from faker import Faker

app = Flask(__name__)
app.config['SECRET_KEY'] = 'final-complete-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///smartlock_final.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
fake = Faker('zh_CN')


# --- 数据库模型 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    color = db.Column(db.String(20), default='primary')


class Device(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    mac = db.Column(db.String(20))
    location = db.Column(db.String(100), default="家庭")
    status = db.Column(db.String(20), default='locked')
    battery = db.Column(db.Integer, default=90)
    firmware_ver = db.Column(db.String(20), default='1.0.0')
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))


class SharedKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_name = db.Column(db.String(100))
    key_type = db.Column(db.String(20))
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)


class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('device.id'))
    user_name = db.Column(db.String(100))
    action = db.Column(db.String(100))
    icon = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.now)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def log_action(device_id, user_name, action, icon='info'):
    log = ActivityLog(device_id=device_id, user_name=user_name, action=action, icon=icon)
    db.session.add(log)
    db.session.commit()


# --- 锁状态检测函数 ---
def check_system_locked():
    """检查Windows系统是否被锁定"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq LogonUI.exe'],
            capture_output=True,
            text=True,
            shell=True
        )
        return 'LogonUI.exe' in result.stdout
    except:
        return False


# --- 路由 ---
@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('device_list'))
    return redirect(url_for('intro'))


@app.route('/intro')
def intro():
    return render_template('intro.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('device_list'))
        flash('账号或密码错误')
    return render_template('auth/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form.get('username')).first():
            flash('用户名已存在')
            return redirect(url_for('register'))
        c = random.choice(['primary', 'success', 'warning', 'info', 'dark'])
        user = User(
            username=request.form.get('username'),
            password=generate_password_hash(request.form.get('password')),
            color=c
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('device_list'))
    return render_template('auth/register.html')


@app.route('/devices')
@login_required
def device_list():
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    return render_template('device_list.html', devices=devices)


@app.route('/control/<int:device_id>')
@login_required
def device_control(device_id):
    device = Device.query.get_or_404(device_id)
    if device.owner_id != current_user.id:
        return redirect(url_for('device_list'))

    logs = ActivityLog.query.filter_by(device_id=device.id).order_by(ActivityLog.timestamp.desc()).limit(5).all()

    return render_template('device_control.html',
                           device=device,
                           logs=logs,
                           device_id=device_id)


@app.route('/keys/<int:device_id>', methods=['GET', 'POST'])
@login_required
def keys(device_id):
    device = Device.query.get_or_404(device_id)
    if request.method == 'POST':
        new_key = SharedKey(
            recipient_name=request.form.get('name'),
            key_type=request.form.get('type'),
            device_id=device.id
        )
        db.session.add(new_key)
        log_action(device.id, current_user.username, f"发送 {new_key.key_type} 钥匙给 {new_key.recipient_name}", "key")
        db.session.commit()
        return redirect(url_for('keys', device_id=device.id))

    shared_keys = SharedKey.query.filter_by(device_id=device.id).order_by(SharedKey.created_at.desc()).all()
    return render_template('keys.html', device=device, keys=shared_keys)


@app.route('/all_keys')
@login_required
def all_keys():
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    return render_template('all_keys.html', devices=devices)


@app.route('/all_history')
@login_required
def all_history():
    logs = db.session.query(ActivityLog, Device.name).join(Device).filter(Device.owner_id == current_user.id).order_by(
        ActivityLog.timestamp.desc()).all()
    return render_template('all_history.html', logs=logs)


@app.route('/app_settings')
@login_required
def app_settings():
    return render_template('app_settings.html')


@app.route('/add_device')
@login_required
def add_device():
    return render_template('add_device.html')


@app.route('/history/<int:device_id>')
@login_required
def history(device_id):
    device = Device.query.get_or_404(device_id)
    logs = ActivityLog.query.filter_by(device_id=device.id).order_by(ActivityLog.timestamp.desc()).all()
    return render_template('history.html', device=device, logs=logs)


@app.route('/settings/<int:device_id>')
@login_required
def settings(device_id):
    device = Device.query.get_or_404(device_id)
    return render_template('settings.html', device=device)


@app.route('/delete_device/<int:device_id>', methods=['POST'])
@login_required
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    if device.owner_id == current_user.id:
        ActivityLog.query.filter_by(device_id=device.id).delete()
        SharedKey.query.filter_by(device_id=device.id).delete()
        db.session.delete(device)
        db.session.commit()
    return redirect(url_for('device_list'))


@app.route('/dashboard')
@login_required
def dashboard():
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    if devices:
        return redirect(url_for('device_control', device_id=devices[0].id))
    return redirect(url_for('device_list'))


# --- API 接口 ---
@app.route('/api/bind', methods=['POST'])
@login_required
def api_bind():
    data = request.get_json()
    new_dev = Device(
        name=data.get('name'),
        mac=fake.mac_address(),
        location="已激活 " + datetime.datetime.now().strftime("%Y/%m/%d"),
        owner_id=current_user.id
    )
    db.session.add(new_dev)
    db.session.commit()
    return jsonify({'success': True, 'device_id': new_dev.id})


@app.route('/api/toggle/<int:device_id>', methods=['POST'])
@login_required
def api_toggle(device_id):
    device = Device.query.get(device_id)

    if device.status == 'locked':
        device.status = 'unlocked'
        log_action(device.id, current_user.username, "远程解锁", "unlock")

        try:
            winsound.Beep(1000, 100)
            winsound.Beep(2000, 200)
        except:
            pass
    else:
        device.status = 'locked'
        log_action(device.id, current_user.username, "远程锁定电脑", "lock")

        try:
            ctypes.windll.user32.LockWorkStation()
        except:
            pass

    device.battery = max(0, device.battery - 1)
    db.session.commit()

    return jsonify({'status': device.status})


@app.route('/api/check_status/<int:device_id>')
@login_required
def api_check_status(device_id):
    """实时检查状态API"""
    device = Device.query.get_or_404(device_id)

    if device.owner_id != current_user.id:
        return jsonify({'error': '无权访问'}), 403

    is_locked = check_system_locked()
    expected_status = 'locked' if is_locked else 'unlocked'

    if device.status != expected_status:
        old_status = device.status
        device.status = expected_status

        if old_status == 'locked' and expected_status == 'unlocked':
            log_action(device.id, "系统", "检测到密码解锁", "unlock")
        elif old_status == 'unlocked' and expected_status == 'locked':
            log_action(device.id, "系统", "检测到系统锁定", "lock")

        db.session.commit()

    return jsonify({
        'status': device.status,
        'system_locked': is_locked,
        'battery': device.battery,
        'timestamp': datetime.datetime.now().isoformat()
    })


@app.route('/api/get_realtime_status/<int:device_id>')
@login_required
def api_get_realtime_status(device_id):
    """长轮询获取实时状态"""
    device = Device.query.get_or_404(device_id)

    if device.owner_id != current_user.id:
        return jsonify({'error': '无权访问'}), 403

    start_time = time.time()
    initial_status = device.status

    while time.time() - start_time < 25:
        is_locked = check_system_locked()
        expected_status = 'locked' if is_locked else 'unlocked'

        if expected_status != device.status:
            old_status = device.status
            device.status = expected_status

            if old_status == 'locked' and expected_status == 'unlocked':
                log_action(device.id, "系统", "实时检测到解锁", "unlock")
            elif old_status == 'unlocked' and expected_status == 'locked':
                log_action(device.id, "系统", "实时检测到锁定", "lock")

            db.session.commit()

            return jsonify({
                'status': device.status,
                'system_locked': is_locked,
                'changed': True,
                'timestamp': datetime.datetime.now().isoformat()
            })

        time.sleep(0.5)

    return jsonify({
        'status': device.status,
        'system_locked': check_system_locked(),
        'changed': False,
        'timeout': True,
        'timestamp': datetime.datetime.now().isoformat()
    })


@app.route('/api/update/<int:device_id>', methods=['POST'])
@login_required
def api_update(device_id):
    time.sleep(1.5)
    device = Device.query.get(device_id)
    device.firmware_ver = "2.5.0"
    db.session.commit()
    return jsonify({'success': True})


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('intro'))


def init_database():
    """初始化数据库 - 更安全的方法"""
    # 确保目录存在
    if not os.path.exists('instance'):
        os.makedirs('instance')

    db_path = 'instance/smartlock_final.db'

    # 先尝试创建数据库
    try:
        with app.app_context():
            db.create_all()
            print("数据库表创建成功！")

            # 创建测试用户
            if not User.query.first():
                test_user = User(
                    username="admin",
                    password=generate_password_hash("admin123"),
                    color="primary"
                )
                db.session.add(test_user)
                db.session.commit()
                print("测试用户已创建: admin / admin123")

    except Exception as e:
        print(f"创建数据库时出错: {e}")
        print("尝试删除旧数据库文件...")

        try:
            # 如果数据库文件被占用，尝试重命名
            if os.path.exists(db_path):
                import time
                timestamp = int(time.time())
                backup_path = f'{db_path}.backup.{timestamp}'
                os.rename(db_path, backup_path)
                print(f"已备份旧数据库到: {backup_path}")

                # 重新创建数据库
                with app.app_context():
                    db.create_all()
                    print("数据库表创建成功！")

                    # 创建测试用户
                    test_user = User(
                        username="admin",
                        password=generate_password_hash("admin123"),
                        color="primary"
                    )
                    db.session.add(test_user)
                    db.session.commit()
                    print("测试用户已创建: admin / admin123")

        except Exception as e2:
            print(f"无法删除或重命名数据库文件: {e2}")
            print("请手动关闭所有使用数据库的程序，然后重新运行。")
            sys.exit(1)


if __name__ == '__main__':
    print("正在启动智能锁系统...")

    # 初始化数据库
    init_database()

    print("\n" + "=" * 50)
    print("智能锁系统启动成功！")
    print("访问地址: http://localhost:5000")
    print("测试账号: admin / admin123")
    print("按 Ctrl+C 停止")
    print("=" * 50 + "\n")

    try:
        app.run(debug=False, port=5000, host='0.0.0.0')  # 关闭debug模式，避免自动重载
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"启动失败: {e}")