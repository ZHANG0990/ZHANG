from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models.database import db, TrafficData, WhiteRule, Alert, SystemSetting, UserProfile
from utils.ai_service import AIService
from utils.alert_service import AlertService
import pandas as pd
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """仪表盘路由"""
    traffic_data = db.session.query(TrafficData).order_by(TrafficData.timestamp.desc()).limit(10).all()
    
    # 为每条流量数据添加匹配规则信息和告警状态
    for traffic in traffic_data:
        # 获取用户名
        from models.database import User
        user = User.query.filter_by(id=traffic.user_id).first()
        traffic.username = user.username if user else f'用户{traffic.user_id}'
        
        traffic.matched_rule = None
        traffic.has_rule_match = False
        traffic.display_predicted_type = traffic.predicted_type
        
        # 检查是否匹配白名单规则
        # 获取用户的白流量规则
        rules = WhiteRule.query.filter_by(user_id=current_user.id, is_active=True).all()
        
        for rule in rules:
            if rule.rule_type == 'ip':
                # 简单的IP匹配逻辑
                ip_ranges = rule.rule_value.split(',')
                for ip_range in ip_ranges:
                    if traffic.source_ip.startswith(ip_range.split('/')[0][:3]):
                        traffic.matched_rule = rule.name
                        traffic.has_rule_match = True
                        traffic.display_predicted_type = f"{traffic.predicted_type} (匹配规则: {rule.name})"
                        break
                if traffic.has_rule_match:
                    break
        
        # 查询关联的告警状态（与traffic_monitor中的逻辑保持一致）
        # 使用新的traffic_id外键直接查询关联的告警
        alert = Alert.query.filter_by(
            user_id=current_user.id,
            traffic_id=traffic.id
        ).first()
        
        # 如果没有直接关联的告警，则尝试旧的IP匹配方式（向后兼容）
        if not alert:
            from datetime import timedelta
            time_window = timedelta(minutes=5)
            alert = Alert.query.filter(
                Alert.user_id == current_user.id,
                Alert.source_ip == traffic.source_ip,
                Alert.dest_ip == traffic.dest_ip,
                Alert.created_at >= traffic.timestamp - time_window,
                Alert.created_at <= traffic.timestamp + time_window
            ).first()
        
        # 设置告警状态
        traffic.alert_status = None
        if alert:
            traffic.alert_status = alert.status  # pending, resolved, ignored
    
    return render_template('dashboard.html', traffic_data=traffic_data, title='仪表盘')

@main_bp.route('/file-drop', methods=['GET', 'POST'])
@login_required
def file_drop():
    """文件拖放过滤路由"""
    if request.method == 'POST':
        ai_service = AIService()
        
        # 处理文件上传（AJAX请求）
        if 'files' in request.files:
            files = request.files.getlist('files')
            results = []
            
            try:
                import tempfile
                from werkzeug.utils import secure_filename
                
                for file in files:
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        temp_dir = tempfile.gettempdir()
                        temp_path = os.path.join(temp_dir, filename)
                        file.save(temp_path)
                        
                        try:
                            # 根据文件类型进行AI分析
                            file_ext = os.path.splitext(filename)[1].lower()
                            
                            if file_ext == '.csv':
                                # 分析CSV文件
                                df = pd.read_csv(temp_path)
                                
                                # 智能分析网络流量特征
                                risk_score = 0
                                risk_factors = []
                                
                                # 1. 检查RST包比例（高RST比例可能是端口扫描）
                                if 'Info' in df.columns:
                                    rst_count = df['Info'].str.contains('RST', na=False).sum()
                                    rst_ratio = rst_count / len(df) if len(df) > 0 else 0
                                    if rst_ratio > 0.3:  # RST包超过30%
                                        risk_score += 30
                                        risk_factors.append(f'高RST包比例({rst_ratio:.1%})')
                                
                                # 2. 检查端口扫描特征
                                if 'Info' in df.columns:
                                    syn_count = df['Info'].str.contains('SYN', na=False).sum()
                                    syn_ratio = syn_count / len(df) if len(df) > 0 else 0
                                    if syn_ratio > 0.5:  # SYN包超过50%
                                        risk_score += 25
                                        risk_factors.append(f'疑似端口扫描({syn_ratio:.1%} SYN包)')
                                
                                # 3. 检查连接频率（短时间内大量连接）
                                if len(df) > 50:  # 大量连接记录
                                    risk_score += 20
                                    risk_factors.append(f'高频连接({len(df)}条记录)')
                                
                                # 4. 检查IP地址模式
                                if 'Source' in df.columns and 'Destination' in df.columns:
                                    # 检查是否有多个目标端口（端口扫描特征）
                                    unique_connections = df.groupby(['Source', 'Destination']).size()
                                    if len(unique_connections) > 10:
                                        risk_score += 15
                                        risk_factors.append('多目标连接模式')
                                    
                                    # 检查本地回环地址大量连接
                                    localhost_count = ((df['Source'] == '127.0.0.1') & (df['Destination'] == '127.0.0.1')).sum()
                                    if localhost_count > 20:
                                        risk_score += 10
                                        risk_factors.append('本地大量连接')
                                
                                # 5. 检查协议分布
                                if 'Protocol' in df.columns:
                                    tcp_count = (df['Protocol'] == 'TCP').sum()
                                    if tcp_count == len(df) and len(df) > 30:  # 全是TCP且数量多
                                        risk_score += 10
                                        risk_factors.append('单一TCP协议大量连接')
                                
                                # 根据风险评分判断
                                is_white = risk_score < 30  # 风险评分低于30认为是白流量
                                confidence = min(0.95, 0.6 + (risk_score / 100))  # 风险越高置信度越高
                                predicted_type = '白流量' if is_white else '可疑流量'
                                
                                # 如果检测到高风险，自动创建告警
                                if risk_score >= 50:  # 高风险阈值
                                    AlertService.create_traffic_risk_alert(
                                        risk_score=risk_score,
                                        risk_factors=risk_factors,
                                        source_ip='文件分析',
                                        dest_ip=filename,
                                        user_id=current_user.id
                                    )
                                
                                # 保存文件分析结果到数据库
                                malicious_alerts_created = 0
                                for index, row in df.iterrows():
                                    # 移除10条限制，处理所有CSV数据
                                    
                                    # 从CSV中提取流量数据（使用正确的列名）
                                    source_ip = row.get('源IP', row.get('Source', '127.0.0.1'))
                                    dest_ip = row.get('目标IP', row.get('Destination', '192.168.1.1'))
                                    traffic_type = row.get('流量类型', row.get('Protocol', 'TCP'))
                                    url = row.get('URL', row.get('Info', ''))
                                    
                                    # 如果CSV中已经标记了流量类型（恶意流量、白流量等），直接使用
                                    if traffic_type in ['恶意流量', '可疑流量', '白流量', '正常流量']:
                                        predicted_type = traffic_type
                                    else:
                                        # 使用AI服务进行预测（包含白流量规则检查）
                                        predicted_type = ai_service.predict_single(
                                            str(source_ip), str(dest_ip), traffic_type, url, current_user.id
                                        )
                                    
                                    # 创建流量数据记录
                                    traffic_data = TrafficData(
                                        source_ip=str(source_ip),
                                        dest_ip=str(dest_ip),
                                        traffic_type=traffic_type,
                                        predicted_type=predicted_type,
                                        user_id=current_user.id
                                    )
                                    db.session.add(traffic_data)
                                    
                                    # 先提交以获取traffic_data的ID
                                    db.session.flush()
                                    
                                    # 为所有可疑流量、恶意流量、危险流量等创建告警
                                    should_create_alert = (
                                        '可疑' in predicted_type or 
                                        '恶意' in predicted_type or 
                                        '危险' in predicted_type or
                                        predicted_type in ['恶意流量', '可疑流量', '危险流量', '异常流量']
                                    )
                                    
                                    if should_create_alert:
                                        # 创建告警
                                        alert = AlertService.create_alert(
                                            title=f"CSV文件中检测到{predicted_type}",
                                            message=f"""在导入的CSV文件中检测到{predicted_type}：

流量信息:
• 源IP: {source_ip}
• 目标IP: {dest_ip}
• 流量类型: {traffic_type}
• 预测结果: {predicted_type}
• URL/内容: {url[:100]}{'...' if len(url) > 100 else ''}

建议进一步分析该流量的详细特征和行为模式。""",
                                            alert_type='danger' if '恶意' in predicted_type else 'warning',
                                            source_ip=str(source_ip),
                                            dest_ip=str(dest_ip),
                                            user_id=current_user.id,
                                            traffic_id=traffic_data.id
                                        )
                                        
                                        if alert:
                                            malicious_alerts_created += 1
                                
                                analysis_result = {
                                    'filename': filename,
                                    'type': 'CSV数据文件',
                                    'is_white_traffic': is_white,
                                    'confidence': confidence,
                                    'risk_score': risk_score,
                                    'risk_factors': risk_factors,
                                    'details': f'检测到 {len(df)} 条记录，风险评分: {risk_score}分，已保存到数据库，创建了 {malicious_alerts_created} 条恶意流量告警'
                                }
                            else:
                                # 其他文件类型的通用分析
                                file_size = os.path.getsize(temp_path)
                                is_white = file_size < 1024 * 1024  # 小于1MB认为是白流量
                                confidence = 0.85
                                predicted_type = '白流量' if is_white else '可疑流量'
                                
                                # 为其他文件类型创建一条分析记录
                                traffic_data = TrafficData(
                                    source_ip='文件分析',
                                    dest_ip='本地系统',
                                    traffic_type=f'{file_ext.upper()}文件',
                                    predicted_type=predicted_type,
                                    user_id=current_user.id
                                )
                                db.session.add(traffic_data)
                                
                                analysis_result = {
                                    'filename': filename,
                                    'type': f'{file_ext.upper()} 文件',
                                    'is_white_traffic': is_white,
                                    'confidence': confidence,
                                    'details': f'文件大小: {file_size} bytes，已保存分析结果到数据库'
                                }
                            
                            results.append(analysis_result)
                            
                        except Exception as analysis_error:
                            results.append({
                                'filename': filename,
                                'error': f'分析失败: {str(analysis_error)}'
                            })
                        finally:
                            # 清理临时文件
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                
                # 提交数据库更改
                db.session.commit()
                
                return jsonify({
                    'success': True, 
                    'results': results,
                    'message': f'成功分析 {len(results)} 个文件并保存到数据库'
                })
                
            except Exception as e:
                return jsonify({'success': False, 'error': f'文件处理失败: {str(e)}'})

        # 处理手动输入
        source_ip = request.form.get('source_ip')
        dest_ip = request.form.get('dest_ip')
        traffic_type = request.form.get('traffic_type')
        content = request.form.get('content')

        try:
            predicted_type = ai_service.predict_single(source_ip, dest_ip, traffic_type, content, current_user.id)
            
            new_traffic = TrafficData(
                source_ip=source_ip, 
                dest_ip=dest_ip, 
                traffic_type=traffic_type, 
                predicted_type=predicted_type, 
                user_id=current_user.id
            )
            db.session.add(new_traffic)
            db.session.commit()

            # 检查是否需要创建告警（与CSV导入逻辑保持一致）
            should_create_alert = (
                '可疑' in predicted_type or 
                '恶意' in predicted_type or 
                '危险' in predicted_type or
                predicted_type in ['恶意流量', '可疑流量', '危险流量', '异常流量']
            )
            
            if should_create_alert:
                # 创建告警
                AlertService.create_alert(
                    title=f"手动输入检测到{predicted_type}",
                    message=f"""手动输入的流量数据被AI判定为{predicted_type}：

流量信息:
• 源IP: {source_ip}
• 目标IP: {dest_ip}
• 流量类型: {traffic_type}
• AI预测结果: {predicted_type}
• 请求内容: {content[:100]}{'...' if len(content) > 100 else ''}

建议进一步分析该流量的详细特征和行为模式。""",
                    alert_type='danger' if '恶意' in predicted_type else 'warning',
                    source_ip=source_ip,
                    dest_ip=dest_ip,
                    user_id=current_user.id,
                    traffic_id=new_traffic.id
                )
                flash(f'AI 预测结果：{predicted_type} - 已自动创建告警通知', 'warning')
            else:
                flash(f'AI 预测结果：{predicted_type}', 'info')
                
        except Exception as e:
            # 先创建流量记录，然后创建告警
            try:
                new_traffic = TrafficData(
                    source_ip=source_ip, 
                    dest_ip=dest_ip, 
                    traffic_type=traffic_type, 
                    predicted_type='分析失败', 
                    user_id=current_user.id
                )
                db.session.add(new_traffic)
                db.session.commit()
                
                # AI预测失败也创建告警
                AlertService.create_alert(
                    title="手动输入流量分析失败",
                    message=f"""手动输入的流量数据分析过程中发生错误：

流量信息:
• 源IP: {source_ip}
• 目标IP: {dest_ip}
• 流量类型: {traffic_type}
• 错误信息: {str(e)}

请检查输入数据格式或联系系统管理员。""",
                    alert_type='danger',
                    source_ip=source_ip,
                    dest_ip=dest_ip,
                    user_id=current_user.id,
                    traffic_id=new_traffic.id
                )
            except Exception as inner_e:
                # 如果连创建流量记录都失败了，就不传traffic_id
                AlertService.create_alert(
                    title="手动输入流量分析失败",
                    message=f"""手动输入的流量数据分析过程中发生错误：

流量信息:
• 源IP: {source_ip}
• 目标IP: {dest_ip}
• 流量类型: {traffic_type}
• 错误信息: {str(e)}

请检查输入数据格式或联系系统管理员。""",
                    alert_type='danger',
                    source_ip=source_ip,
                    dest_ip=dest_ip,
                    user_id=current_user.id
                )
            flash(f'预测失败：{str(e)} - 已创建错误告警', 'danger')
        
        return redirect(url_for('main.file_drop'))

    traffic_data = db.session.query(TrafficData).order_by(TrafficData.timestamp.desc()).limit(10).all()
    
    return render_template('file_drop.html', traffic_data=traffic_data, title='流量数据分析')

@main_bp.route('/traffic-monitor')
@login_required
def traffic_monitor():
    """流量监控路由"""
    traffic_list = db.session.query(TrafficData).order_by(TrafficData.timestamp.desc()).all()
    
    # 为每条流量数据添加匹配规则信息和告警状态
    for traffic in traffic_list:
        traffic.matched_rule = None
        traffic.has_rule_match = False
        traffic.display_predicted_type = traffic.predicted_type
        
        # 检查是否匹配白名单规则
        # 获取用户的白流量规则
        rules = WhiteRule.query.filter_by(user_id=current_user.id, is_active=True).all()
        
        for rule in rules:
            if rule.rule_type == 'ip':
                # 简单的IP匹配逻辑
                ip_ranges = rule.rule_value.split(',')
                for ip_range in ip_ranges:
                    if traffic.source_ip.startswith(ip_range.split('/')[0][:3]):
                        traffic.matched_rule = rule.name
                        traffic.has_rule_match = True
                        traffic.display_predicted_type = f"{traffic.predicted_type} (匹配规则: {rule.name})"
                        print(f"[DEBUG] 匹配规则: {traffic.source_ip} -> {rule.name}, has_rule_match={traffic.has_rule_match}")
                        break
                if traffic.has_rule_match:
                    break
        
        # 查询关联的告警状态（与API中的逻辑保持一致）
        # 使用新的traffic_id外键直接查询关联的告警
        alert = Alert.query.filter_by(
            user_id=current_user.id,
            traffic_id=traffic.id
        ).first()
        
        # 如果没有直接关联的告警，则尝试旧的IP匹配方式（向后兼容）
        if not alert:
            from datetime import timedelta
            time_window = timedelta(minutes=5)
            alert = Alert.query.filter(
                Alert.user_id == current_user.id,
                Alert.source_ip == traffic.source_ip,
                Alert.dest_ip == traffic.dest_ip,
                Alert.created_at >= traffic.timestamp - time_window,
                Alert.created_at <= traffic.timestamp + time_window
            ).first()
        
        # 设置告警状态
        traffic.alert_status = None
        if alert:
            traffic.alert_status = alert.status  # pending, resolved, ignored
    
    # 添加调试信息
    import json
    debug_info = []
    for traffic in traffic_list[:5]:  # 只显示前5条记录的调试信息
        debug_info.append({
            'id': traffic.id,
            'source_ip': traffic.source_ip,
            'predicted_type': traffic.predicted_type,
            'display_predicted_type': traffic.display_predicted_type,
            'has_rule_match': traffic.has_rule_match,
            'alert_status': getattr(traffic, 'alert_status', None)
        })
    print(f"[DEBUG] 流量数据调试信息: {json.dumps(debug_info, ensure_ascii=False)}")
    
    return render_template('traffic_monitor.html', traffic_list=traffic_list, title='流量监控')

@main_bp.route('/white-rules')
@login_required
def white_rules():
    """白流量规则管理路由"""
    rules_query = WhiteRule.query.order_by(WhiteRule.created_at.desc()).all()
    
    # 将数据库对象转换为字典格式，便于JSON序列化
    rules = []
    for rule in rules_query:
        # 获取创建者用户名
        from models.database import User
        creator = User.query.filter_by(id=rule.user_id).first()
        creator_name = creator.username if creator else f'用户{rule.user_id}'
        
        rules.append({
            'id': rule.id,
            'name': rule.name,
            'description': rule.description or '',
            'rule_type': rule.rule_type,
            'rule_value': rule.rule_value,
            'is_active': rule.is_active,
            'created_at': rule.created_at.strftime('%Y-%m-%d %H:%M:%S') if rule.created_at else '',
            'updated_at': rule.updated_at.strftime('%Y-%m-%d %H:%M:%S') if rule.updated_at else '',
            'creator_name': creator_name,
            'user_id': rule.user_id,
            'is_own_rule': rule.user_id == current_user.id  # 标记是否为当前用户创建的规则
        })
    
    return render_template('white_rules.html', rules=rules, title='白流量规则管理')

@main_bp.route('/white-rules/add', methods=['POST'])
@login_required
def add_white_rule():
    """添加白流量规则"""
    try:
        name = request.form.get('name')
        description = request.form.get('description', '')
        rule_type = request.form.get('rule_type')
        rule_value = request.form.get('rule_value')
        
        new_rule = WhiteRule(
            name=name,
            description=description,
            rule_type=rule_type,
            rule_value=rule_value,
            user_id=current_user.id
        )
        
        db.session.add(new_rule)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '规则添加成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'})

@main_bp.route('/white-rules/toggle/<int:rule_id>', methods=['POST'])
@login_required
def toggle_white_rule(rule_id):
    """切换规则状态"""
    try:
        rule = WhiteRule.query.filter_by(id=rule_id).first()
        if not rule:
            return jsonify({'success': False, 'message': '规则不存在'})
        
        # 检查权限：只能操作自己创建的规则
        if rule.user_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限操作此规则，只能操作自己创建的规则'})
        
        rule.is_active = not rule.is_active
        db.session.commit()
        return jsonify({'success': True, 'is_active': rule.is_active})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@main_bp.route('/white-rules/edit/<int:rule_id>', methods=['POST'])
@login_required
def edit_white_rule(rule_id):
    """编辑白流量规则"""
    try:
        rule = WhiteRule.query.filter_by(id=rule_id).first()
        if not rule:
            return jsonify({'success': False, 'message': '规则不存在'})
        
        # 检查权限：只能编辑自己创建的规则
        if rule.user_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限编辑此规则，只能编辑自己创建的规则'})
        
        name = request.form.get('name')
        description = request.form.get('description', '')
        rule_type = request.form.get('rule_type')
        rule_value = request.form.get('rule_value')
        
        rule.name = name
        rule.description = description
        rule.rule_type = rule_type
        rule.rule_value = rule_value
        rule.updated_at = db.func.now()
        
        db.session.commit()
        
        # 创建规则变更告警
        AlertService.create_white_rule_alert(name, 'updated', current_user.id)
        
        return jsonify({'success': True, 'message': '规则更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@main_bp.route('/white-rules/delete/<int:rule_id>', methods=['POST'])
@login_required
def delete_white_rule(rule_id):
    """删除规则"""
    try:
        rule = WhiteRule.query.filter_by(id=rule_id).first()
        if not rule:
            return jsonify({'success': False, 'message': '规则不存在'})
        
        # 检查权限：只能删除自己创建的规则
        if rule.user_id != current_user.id:
            return jsonify({'success': False, 'message': '无权限删除此规则，只能删除自己创建的规则'})
        
        rule_name = rule.name  # 保存规则名称用于告警
        db.session.delete(rule)
        db.session.commit()
        
        # 创建规则删除告警
        AlertService.create_white_rule_alert(rule_name, 'deleted', current_user.id)
        
        return jsonify({'success': True, 'message': '规则删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@main_bp.route('/alerts')
@login_required
def alerts():
    """告警中心路由"""
    alerts_list = Alert.query.order_by(Alert.created_at.desc()).all()
    
    # 统计数据
    total_alerts = len(alerts_list)
    pending_alerts = len([a for a in alerts_list if a.status == 'pending'])
    resolved_alerts = len([a for a in alerts_list if a.status == 'resolved'])
    
    stats = {
        'total': total_alerts,
        'pending': pending_alerts,
        'resolved': resolved_alerts,
        'ignored': total_alerts - pending_alerts - resolved_alerts
    }
    
    return render_template('alerts.html', alerts=alerts_list, stats=stats, title='告警中心')

@main_bp.route('/alerts/resolve/<int:alert_id>', methods=['POST'])
@login_required
def resolve_alert(alert_id):
    """解决告警"""
    try:
        alert = Alert.query.filter_by(id=alert_id).first()
        if alert:
            alert.status = 'resolved'
            alert.resolved_at = db.func.now()
            
            # 创建操作记录告警，记录真实用户名
            from models.database import User
            operator_user = User.query.filter_by(id=current_user.id).first()
            operator_name = operator_user.username if operator_user else f'用户{current_user.id}'
            
            # 创建操作日志告警
            AlertService.create_alert(
                title=f"告警已处理",
                message=f"""告警处理记录：

原告警信息：
• 标题：{alert.title}
• 类型：{alert.alert_type}
• 状态：已解决

操作信息：
• 操作者：{operator_name}
• 操作时间：{db.func.now()}
• 操作类型：标记为已解决""",
                alert_type='info',
                user_id=current_user.id
            )
            
            db.session.commit()
            return jsonify({'success': True, 'message': f'告警已标记为已解决（操作者：{operator_name}）'})
        return jsonify({'success': False, 'message': '告警不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@main_bp.route('/alerts/ignore/<int:alert_id>', methods=['POST'])
@login_required
def ignore_alert(alert_id):
    """忽略告警"""
    try:
        alert = Alert.query.filter_by(id=alert_id).first()
        if alert:
            alert.status = 'ignored'
            
            # 创建操作记录告警，记录真实用户名
            from models.database import User
            operator_user = User.query.filter_by(id=current_user.id).first()
            operator_name = operator_user.username if operator_user else f'用户{current_user.id}'
            
            # 创建操作日志告警
            AlertService.create_alert(
                title=f"告警已忽略",
                message=f"""告警处理记录：

原告警信息：
• 标题：{alert.title}
• 类型：{alert.alert_type}
• 状态：已忽略

操作信息：
• 操作者：{operator_name}
• 操作时间：{db.func.now()}
• 操作类型：标记为忽略""",
                alert_type='info',
                user_id=current_user.id
            )
            
            db.session.commit()
            return jsonify({'success': True, 'message': f'告警已忽略（操作者：{operator_name}）'})
        return jsonify({'success': False, 'message': '告警不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@main_bp.route('/settings')
@login_required
def settings():
    """系统设置路由"""
    user_settings = {}
    settings_list = SystemSetting.query.filter_by(user_id=current_user.id).all()
    
    for setting in settings_list:
        user_settings[setting.key] = setting.value
    
    # 如果用户没有设置，使用默认值
    default_settings = {
        'filter_mode': 'ai_auto',
        'filter_precision': 'balanced',
        'traffic_types': 'HTTP,HTTPS,TCP,UDP',
        'ai_model_update': 'auto',
        'performance_mode': 'standard'
    }
    
    for key, default_value in default_settings.items():
        if key not in user_settings:
            user_settings[key] = default_value
    
    return render_template('settings.html', settings=user_settings, title='系统设置')

@main_bp.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """更新系统设置"""
    try:
        settings_data = request.get_json()
        
        for key, value in settings_data.items():
            setting = SystemSetting.query.filter_by(key=key, user_id=current_user.id).first()
            
            if setting:
                setting.value = value
            else:
                setting = SystemSetting(key=key, value=value, user_id=current_user.id)
                db.session.add(setting)
        
        db.session.commit()
        return jsonify({'success': True, 'message': '设置保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'})

@main_bp.route('/profile')
@login_required
def profile():
    """个人中心路由"""
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    
    if not user_profile:
        # 创建默认用户配置
        user_profile = UserProfile(user_id=current_user.id)
        db.session.add(user_profile)
        db.session.commit()
    
    # 获取用户统计数据
    traffic_count = TrafficData.query.filter_by(user_id=current_user.id).count()
    rules_count = WhiteRule.query.filter_by(user_id=current_user.id).count()
    alerts_count = Alert.query.filter_by(user_id=current_user.id).count()
    
    stats = {
        'traffic_count': traffic_count,
        'rules_count': rules_count,
        'alerts_count': alerts_count
    }
    
    return render_template('profile.html', profile=user_profile, stats=stats, title='个人中心')

@main_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """更新个人信息"""
    try:
        print("=" * 50)
        print("[PROFILE UPDATE] 路由被调用!")
        print("=" * 50)
        
        print(f"[DEBUG] 开始处理用户 {current_user.id} 的个人信息更新请求")
        print(f"[DEBUG] Request method: {request.method}")
        print(f"[DEBUG] Content-Type: {request.content_type}")
        print(f"[DEBUG] Form data: {dict(request.form)}")
        
        # 检查数据库连接
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            print("[DEBUG] 数据库连接正常")
        except Exception as db_error:
            print(f"[ERROR] 数据库连接失败: {db_error}")
            return jsonify({
                'success': False, 
                'message': '数据库连接失败'
            }), 500
        
        # 获取或创建用户配置
        user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        
        if not user_profile:
            print("[DEBUG] 用户配置不存在，创建新的配置")
            user_profile = UserProfile(user_id=current_user.id)
            db.session.add(user_profile)
            try:
                db.session.flush()
                print(f"[DEBUG] 新用户配置创建成功，ID: {user_profile.id}")
            except Exception as flush_error:
                print(f"[ERROR] 创建用户配置失败: {flush_error}")
                db.session.rollback()
                return jsonify({
                    'success': False, 
                    'message': f'创建用户配置失败: {str(flush_error)}'
                }), 500
        else:
            print(f"[DEBUG] 找到现有用户配置，ID: {user_profile.id}")
        
        # 获取表单数据
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        position = request.form.get('position', '').strip()
        
        print(f"[DEBUG] 接收到的数据: phone='{phone}', department='{department}', position='{position}'")
        
        # 数据验证
        if phone and len(phone) > 20:
            return jsonify({
                'success': False, 
                'message': '手机号码长度不能超过20个字符'
            }), 400
            
        if department and len(department) > 100:
            return jsonify({
                'success': False, 
                'message': '部门名称长度不能超过100个字符'
            }), 400
            
        if position and len(position) > 100:
            return jsonify({
                'success': False, 
                'message': '职位名称长度不能超过100个字符'
            }), 400
        
        # 更新基本信息
        user_profile.phone = phone if phone else None
        user_profile.department = department if department else None
        user_profile.position = position if position else None
        
        print("[DEBUG] 开始提交数据库更改...")
        try:
            db.session.commit()
            print("[DEBUG] 数据库提交成功")
        except Exception as commit_error:
            print(f"[ERROR] 数据库提交失败: {commit_error}")
            db.session.rollback()
            return jsonify({
                'success': False, 
                'message': f'数据保存失败: {str(commit_error)}'
            }), 500
        
        response_data = {
            'success': True, 
            'message': '个人信息更新成功',
            'data': {
                'phone': user_profile.phone or '',
                'department': user_profile.department or '',
                'position': user_profile.position or ''
            }
        }
        print(f"[DEBUG] 返回响应: {response_data}")
        return jsonify(response_data), 200
        
    except Exception as e:
        # 确保回滚数据库
        try:
            db.session.rollback()
        except Exception as rollback_error:
            print(f"[ERROR] 数据库回滚失败: {rollback_error}")
            
        print(f"[ERROR] 更新个人信息失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 始终返回JSON格式的错误响应
        return jsonify({
            'success': False, 
            'message': f'更新失败: {str(e)}'
        }), 500

@main_bp.route('/profile/avatar', methods=['POST'])
@login_required
def upload_avatar():
    """单独的头像上传接口"""
    try:
        print("=" * 50)
        print("[AVATAR UPLOAD] 头像上传路由被调用!")
        print("=" * 50)
        
        print(f"[DEBUG] 开始处理用户 {current_user.id} 的头像上传请求")
        print(f"[DEBUG] Request files: {list(request.files.keys())}")
        
        # 检查数据库连接
        try:
            from sqlalchemy import text
            db.session.execute(text('SELECT 1'))
            print("[DEBUG] 数据库连接正常")
        except Exception as db_error:
            print(f"[ERROR] 数据库连接失败: {db_error}")
            return jsonify({
                'success': False, 
                'message': '数据库连接失败'
            }), 500
        
        if 'avatar' not in request.files:
            print("[ERROR] 请求中没有avatar文件")
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        avatar_file = request.files['avatar']
        print(f"[DEBUG] 接收到文件: {avatar_file.filename}")
        
        if not avatar_file or not avatar_file.filename:
            print("[ERROR] 文件为空或没有文件名")
            return jsonify({'success': False, 'message': '没有选择文件'})
        
        # 检查文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        if '.' not in avatar_file.filename:
            print("[ERROR] 文件没有扩展名")
            return jsonify({'success': False, 'message': '文件格式不正确'})
            
        file_ext = avatar_file.filename.rsplit('.', 1)[1].lower()
        print(f"[DEBUG] 文件扩展名: {file_ext}")
        
        if file_ext not in allowed_extensions:
            print(f"[ERROR] 不支持的文件格式: {file_ext}")
            return jsonify({'success': False, 'message': f'不支持的文件格式，仅支持: {", ".join(allowed_extensions)}'})
        
        # 检查文件大小 (2MB)
        avatar_file.seek(0, 2)  # 移到文件末尾
        file_size = avatar_file.tell()
        avatar_file.seek(0)  # 重置到开头
        print(f"[DEBUG] 文件大小: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
        
        if file_size > 2 * 1024 * 1024:  # 2MB限制
            print("[ERROR] 文件大小超过限制")
            return jsonify({'success': False, 'message': '文件大小不能超过2MB'})
        
        if file_size == 0:
            print("[ERROR] 文件为空")
            return jsonify({'success': False, 'message': '文件为空，请选择有效的图片文件'})
        
        # 获取或创建用户配置
        user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        if not user_profile:
            print("[DEBUG] 用户配置不存在，创建新的配置")
            user_profile = UserProfile(user_id=current_user.id)
            db.session.add(user_profile)
            try:
                db.session.flush()
                print(f"[DEBUG] 新用户配置创建成功，ID: {user_profile.id}")
            except Exception as flush_error:
                print(f"[ERROR] 创建用户配置失败: {flush_error}")
                db.session.rollback()
                return jsonify({
                    'success': False, 
                    'message': f'创建用户配置失败: {str(flush_error)}'
                }), 500
        else:
            print(f"[DEBUG] 找到现有用户配置，ID: {user_profile.id}")
        
        # 创建头像目录
        avatar_dir = os.path.join('static', 'avatars')
        try:
            os.makedirs(avatar_dir, exist_ok=True)
            print(f"[DEBUG] 头像目录已创建/确认存在: {avatar_dir}")
        except Exception as dir_error:
            print(f"[ERROR] 创建头像目录失败: {dir_error}")
            return jsonify({'success': False, 'message': '创建上传目录失败'})
        
        # 生成唯一文件名
        import uuid
        import time
        timestamp = int(time.time())
        filename = f"{current_user.id}_{timestamp}_{uuid.uuid4().hex[:8]}.{file_ext}"
        avatar_path = os.path.join(avatar_dir, filename)
        print(f"[DEBUG] 生成的文件路径: {avatar_path}")
        
        # 删除旧头像
        if user_profile.avatar:
            old_avatar_path = user_profile.avatar
            print(f"[DEBUG] 准备删除旧头像: {old_avatar_path}")
            if os.path.exists(old_avatar_path):
                try:
                    os.remove(old_avatar_path)
                    print("[DEBUG] 旧头像删除成功")
                except Exception as remove_error:
                    print(f"[WARNING] 删除旧头像失败: {remove_error}")
            else:
                print("[DEBUG] 旧头像文件不存在，跳过删除")
        
        # 保存新头像
        try:
            avatar_file.save(avatar_path)
            print(f"[DEBUG] 头像文件保存成功: {avatar_path}")
            
            # 验证文件是否真的保存成功
            if not os.path.exists(avatar_path):
                print("[ERROR] 文件保存后不存在")
                return jsonify({'success': False, 'message': '文件保存失败'})
                
            saved_size = os.path.getsize(avatar_path)
            print(f"[DEBUG] 保存后文件大小: {saved_size} bytes")
            
        except Exception as save_error:
            print(f"[ERROR] 保存头像文件失败: {save_error}")
            return jsonify({'success': False, 'message': f'保存文件失败: {str(save_error)}'})
        
        # 更新数据库
        user_profile.avatar = avatar_path
        
        try:
            db.session.commit()
            print("[DEBUG] 数据库更新成功")
        except Exception as commit_error:
            print(f"[ERROR] 数据库提交失败: {commit_error}")
            db.session.rollback()
            # 删除已保存的文件
            try:
                os.remove(avatar_path)
            except:
                pass
            return jsonify({
                'success': False, 
                'message': f'数据保存失败: {str(commit_error)}'
            }), 500
        
        # 生成访问URL
        avatar_url = f'/{avatar_path.replace(os.sep, "/")}'
        print(f"[DEBUG] 头像访问URL: {avatar_url}")
        
        response_data = {
            'success': True, 
            'message': '头像上传成功',
            'avatar_url': avatar_url,
            'filename': filename
        }
        print(f"[DEBUG] 返回响应: {response_data}")
        return jsonify(response_data), 200
        
    except Exception as e:
        # 确保回滚数据库
        try:
            db.session.rollback()
        except Exception as rollback_error:
            print(f"[ERROR] 数据库回滚失败: {rollback_error}")
            
        print(f"[ERROR] 头像上传失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False, 
            'message': f'上传失败: {str(e)}'
        }), 500

@main_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    return jsonify(response_data), 200

@main_bp.route('/help')
@login_required
def help():
    """帮助中心路由"""
    return render_template('help.html', title='帮助中心')
