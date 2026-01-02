"""
告警服务模块
用于自动创建和管理告警
"""
from models.database import db, Alert, get_china_time
from flask_login import current_user

class AlertService:
    """告警服务类"""
    
    @staticmethod
    def create_alert(title, message, alert_type='warning', source_ip=None, dest_ip=None, user_id=None, traffic_id=None):
        """
        创建新告警
        
        Args:
            title: 告警标题
            message: 告警详细信息
            alert_type: 告警类型 (danger, warning, info)
            source_ip: 源IP地址
            dest_ip: 目标IP地址
            user_id: 用户ID
            traffic_id: 关联的流量记录ID
        
        Returns:
            Alert: 创建的告警对象
        """
        try:
            if user_id is None and current_user.is_authenticated:
                user_id = current_user.id
            
            alert = Alert(
                title=title,
                message=message,
                alert_type=alert_type,
                source_ip=source_ip,
                dest_ip=dest_ip,
                user_id=user_id,
                traffic_id=traffic_id,
                status='pending'
            )
            
            db.session.add(alert)
            db.session.commit()
            
            print(f"[ALERT] 创建告警成功: {title} (用户: {user_id}, 流量ID: {traffic_id})")
            return alert
            
        except Exception as e:
            print(f"[ERROR] 创建告警失败: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def create_traffic_risk_alert(risk_score, risk_factors, source_ip=None, dest_ip=None, user_id=None, traffic_id=None):
        """
        创建流量风险告警
        
        Args:
            risk_score: 风险评分
            risk_factors: 风险因素列表
            source_ip: 源IP地址
            dest_ip: 目标IP地址
            user_id: 用户ID
            traffic_id: 关联的流量记录ID
        """
        # 降低告警创建阈值，确保可疑流量都能创建告警
        if risk_score < 25:  # 低于25分不创建告警（与AI预测的可疑流量阈值一致）
            return None
        
        # 根据风险评分确定告警级别
        if risk_score >= 80:
            alert_type = 'danger'
            level_text = '高风险'
        elif risk_score >= 60:
            alert_type = 'warning'
            level_text = '中风险'
        else:
            alert_type = 'info'
            level_text = '低风险'
        
        title = f"检测到{level_text}流量异常"
        
        message = f"""系统检测到可疑流量活动，风险评分: {risk_score}分

检测到的风险因素:
{chr(10).join(f'• {factor}' for factor in risk_factors)}

建议立即检查相关网络活动并采取必要的安全措施。"""
        
        return AlertService.create_alert(
            title=title,
            message=message,
            alert_type=alert_type,
            source_ip=source_ip,
            dest_ip=dest_ip,
            user_id=user_id,
            traffic_id=traffic_id
        )
    
    @staticmethod
    def create_file_analysis_alert(filename, file_type, confidence, is_white_traffic, user_id=None):
        """
        创建文件分析告警
        
        Args:
            filename: 文件名
            file_type: 文件类型
            confidence: 置信度
            is_white_traffic: 是否为白流量
            user_id: 用户ID
        """
        if is_white_traffic and confidence > 0.8:  # 高置信度的白流量不创建告警
            return None
        
        if not is_white_traffic:
            alert_type = 'warning' if confidence > 0.7 else 'info'
            title = f"检测到可疑文件: {filename}"
            message = f"""文件分析结果显示该文件可能存在安全风险:

文件信息:
• 文件名: {filename}
• 文件类型: {file_type}
• 风险评估: 可疑文件
• 置信度: {confidence:.1%}

建议对该文件进行进一步的安全检查。"""
        else:
            alert_type = 'info'
            title = f"文件分析完成: {filename}"
            message = f"""文件分析结果:

文件信息:
• 文件名: {filename}
• 文件类型: {file_type}
• 安全评估: 安全文件
• 置信度: {confidence:.1%}

该文件已通过安全检查。"""
        
        return AlertService.create_alert(
            title=title,
            message=message,
            alert_type=alert_type,
            user_id=user_id
        )
    
    @staticmethod
    def create_ai_model_alert(error_message, user_id=None):
        """
        创建AI模型相关告警
        
        Args:
            error_message: 错误信息
            user_id: 用户ID
        """
        title = "AI模型运行异常"
        message = f"""AI预测模型运行时发生异常:

错误信息: {error_message}

这可能影响流量分析的准确性，建议检查模型文件和相关配置。"""
        
        return AlertService.create_alert(
            title=title,
            message=message,
            alert_type='warning',
            user_id=user_id
        )
    
    @staticmethod
    def create_white_rule_alert(rule_name, action, user_id=None):
        """
        创建白流量规则相关告警
        
        Args:
            rule_name: 规则名称
            action: 操作类型 (created, updated, deleted)
            user_id: 用户ID
        """
        action_text = {
            'created': '创建',
            'updated': '更新', 
            'deleted': '删除'
        }.get(action, '修改')
        
        title = f"白流量规则{action_text}: {rule_name}"
        message = f"白流量规则 '{rule_name}' 已被{action_text}，这可能影响流量过滤结果。"
        
        return AlertService.create_alert(
            title=title,
            message=message,
            alert_type='info',
            user_id=user_id
        )