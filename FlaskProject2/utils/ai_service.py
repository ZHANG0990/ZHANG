import joblib
import pandas as pd
import numpy as np
import re
import ipaddress
from models.database import db, TrafficData, WhiteRule

class AIService:
    """AI服务类，处理机器学习预测"""
    
    def __init__(self):
        """初始化AI模型"""
        try:
            import os
            
            # 优先使用新的高级模型
            if (os.path.exists('static/models/advanced_traffic_model.pkl') and 
                os.path.exists('static/models/label_encoder.pkl') and
                os.path.exists('static/models/feature_scaler.pkl') and
                os.path.exists('static/models/categorical_encoders.pkl')):
                
                print("[INFO] 加载高级AI模型...")
                self.model = joblib.load('static/models/advanced_traffic_model.pkl')
                self.label_encoder = joblib.load('static/models/label_encoder.pkl')
                self.feature_scaler = joblib.load('static/models/feature_scaler.pkl')
                self.categorical_encoders = joblib.load('static/models/categorical_encoders.pkl')
                
                # 加载模型信息
                model_info = joblib.load('static/models/model_info.pkl')
                self.feature_names = model_info['feature_names']
                
                self.use_advanced_model = True
                print(f"[INFO] 高级模型加载成功，支持的标签: {list(self.label_encoder.classes_)}")
                print(f"[INFO] 模型准确率: {model_info.get('accuracy', 0):.4f}")
                
            else:
                # 回退到原始模型
                print("[INFO] 高级模型不存在，使用原始模型...")
                possible_paths = [
                    ('static/models/traffic_model.pkl', 'static/models/label_encoders.pkl'),
                    ('utils/static/models/traffic_model.pkl', 'utils/static/models/label_encoders.pkl')
                ]
                
                model_path = None
                encoder_path = None
                
                for mp, ep in possible_paths:
                    if os.path.exists(mp) and os.path.exists(ep):
                        model_path = mp
                        encoder_path = ep
                        break
                
                if not model_path or not encoder_path:
                    raise FileNotFoundError("模型文件不存在")
                    
                self.model = joblib.load(model_path)
                self.label_encoders = joblib.load(encoder_path)
                self.use_advanced_model = False
                
                print(f"[INFO] 原始模型加载成功，支持的标签: {list(self.label_encoders['标签'].classes_)}")
            
        except FileNotFoundError:
            raise RuntimeError("请先运行 quick_train_model.py 或 utils/train_model.py 生成 AI 模型文件！")
    
    def check_white_rules(self, source_ip, dest_ip, traffic_type, content, user_id):
        """检查是否匹配白流量规则"""
        # 获取用户的活跃白流量规则
        rules = WhiteRule.query.filter_by(user_id=user_id, is_active=True).all()
        
        for rule in rules:
            if self._match_rule(rule, source_ip, dest_ip, traffic_type, content):
                return True, rule.name
        
        return False, None
    
    def _match_rule(self, rule, source_ip, dest_ip, traffic_type, content):
        """匹配单个规则"""
        rule_type = rule.rule_type
        rule_value = rule.rule_value
        
        if rule_type == 'ip':
            return self._match_ip_rule(source_ip, rule_value) or self._match_ip_rule(dest_ip, rule_value)
        elif rule_type == 'domain':
            return self._match_domain_rule(dest_ip, rule_value) or self._match_domain_rule(content, rule_value)
        elif rule_type == 'port':
            return self._match_port_rule(content, rule_value)
        elif rule_type == 'protocol':
            return self._match_protocol_rule(traffic_type, rule_value)
        
        return False
    
    def _match_ip_rule(self, ip, rule_value):
        """匹配IP规则"""
        try:
            # 支持多个IP或IP段，用逗号分隔
            ip_patterns = [pattern.strip() for pattern in rule_value.split(',')]
            
            for pattern in ip_patterns:
                if not pattern:
                    continue
                    
                # 检查是否是IP段（CIDR格式）
                if '/' in pattern:
                    try:
                        network = ipaddress.ip_network(pattern, strict=False)
                        if ipaddress.ip_address(ip) in network:
                            return True
                    except (ipaddress.AddressValueError, ValueError):
                        continue
                else:
                    # 精确匹配
                    if pattern == ip:
                        return True
                    # 支持简单的通配符匹配
                    if '*' in pattern:
                        regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
                        if re.match(f'^{regex_pattern}$', ip):
                            return True
        except Exception:
            pass
        
        return False
    
    def _match_domain_rule(self, text, rule_value):
        """匹配域名规则"""
        try:
            # 支持多个域名，用逗号分隔
            domain_patterns = [pattern.strip() for pattern in rule_value.split(',')]
            
            for pattern in domain_patterns:
                if not pattern:
                    continue
                    
                # 支持通配符匹配
                if '*' in pattern:
                    regex_pattern = pattern.replace('.', r'\.').replace('*', '.*')
                    if re.search(regex_pattern, text, re.IGNORECASE):
                        return True
                else:
                    # 精确匹配或包含匹配
                    if pattern.lower() in text.lower():
                        return True
        except Exception:
            pass
        
        return False
    
    def _match_port_rule(self, content, rule_value):
        """匹配端口规则"""
        try:
            # 支持多个端口或端口范围，用逗号分隔
            port_patterns = [pattern.strip() for pattern in rule_value.split(',')]
            
            for pattern in port_patterns:
                if not pattern:
                    continue
                    
                # 检查是否是端口范围
                if '-' in pattern:
                    try:
                        start_port, end_port = map(int, pattern.split('-'))
                        # 在内容中查找端口号
                        port_matches = re.findall(r':(\d+)', content)
                        for port_str in port_matches:
                            port = int(port_str)
                            if start_port <= port <= end_port:
                                return True
                    except ValueError:
                        continue
                else:
                    # 精确端口匹配
                    if f':{pattern}' in content or f' {pattern} ' in content:
                        return True
        except Exception:
            pass
        
        return False
    
    def _match_protocol_rule(self, traffic_type, rule_value):
        """匹配协议规则"""
        try:
            # 支持多个协议，用逗号分隔
            protocols = [protocol.strip().upper() for protocol in rule_value.split(',')]
            return traffic_type.upper() in protocols
        except Exception:
            pass
        
        return False
    
    def predict_single(self, source_ip, dest_ip, traffic_type, content, user_id=None):
        """预测单条流量数据"""
        # 首先检查白流量规则
        if user_id:
            is_white, matched_rule = self.check_white_rules(source_ip, dest_ip, traffic_type, content, user_id)
            if is_white:
                return f'白流量 (匹配规则: {matched_rule})'
        
        # 使用高级模型进行预测
        if self.use_advanced_model:
            try:
                prediction = self._predict_with_advanced_model(source_ip, dest_ip, traffic_type, content)
                return prediction
            except Exception as e:
                print(f"[WARNING] 高级模型预测失败: {e}，回退到规则预测")
                return self._intelligent_rule_prediction(source_ip, dest_ip, traffic_type, content)
        else:
            # 使用原始模型或规则预测
            if traffic_type == '恶意流量':
                return self._intelligent_rule_prediction(source_ip, dest_ip, traffic_type, content)
            elif traffic_type in ['可疑流量', '白流量']:
                return traffic_type
            
            return self._intelligent_rule_prediction(source_ip, dest_ip, traffic_type, content)
    
    def _predict_with_advanced_model(self, source_ip, dest_ip, traffic_type, content):
        """使用高级模型进行预测"""
        # 构造特征数据
        data = {
            'src_ip': source_ip,
            'dst_ip': dest_ip,
            'protocol': traffic_type,
            'packet_count': 50,  # 默认值
            'byte_count': 3000,  # 默认值
            'duration': 2.5,     # 默认值
            'packets_per_second': 20,
            'bytes_per_packet': 60,
            'bytes_per_second': 1200,
            'hour_of_day': 14,   # 默认值
            'is_weekend': 0      # 默认值
        }
        
        # 预处理数据
        df = pd.DataFrame([data])
        
        # 编码分类特征
        for feature, encoder in self.categorical_encoders.items():
            if feature in df.columns:
                encoded_feature = feature + '_encoded'
                try:
                    df[encoded_feature] = encoder.transform(df[feature].astype(str))
                except ValueError:
                    # 处理未见过的类别
                    df[encoded_feature] = 0
        
        # 选择特征
        available_features = [f for f in self.feature_names if f in df.columns]
        X = df[available_features].fillna(0)
        
        # 标准化
        X_scaled = self.feature_scaler.transform(X)
        
        # 预测
        prediction = self.model.predict(X_scaled)
        probability = self.model.predict_proba(X_scaled)
        
        # 解码标签
        predicted_label = self.label_encoder.inverse_transform(prediction)[0]
        confidence = float(np.max(probability))
        
        # 映射到项目使用的标签格式
        label_mapping = {
            'Normal': '正常流量',
            'DDoS': '恶意流量',
            'Port_Scan': '可疑流量',
            'Brute_Force': '恶意流量',
            'SQL_Injection': '恶意流量',
            'Malware': '恶意流量'
        }
        
        mapped_label = label_mapping.get(predicted_label, predicted_label)
        
        # 如果置信度较低，降级处理
        if confidence < 0.7 and mapped_label == '恶意流量':
            mapped_label = '可疑流量'
        
        return mapped_label
    
    def _intelligent_rule_prediction(self, source_ip, dest_ip, traffic_type, content):
        """智能规则预测（基于CSV数据优化的逻辑）"""
        risk_score = 20  # 降低基础分数，让更多流量被判定为正常
        risk_factors = []
        
        # 1. 根据流量类型进行基础评分
        if traffic_type == '视频流量':
            risk_score = 10  # 视频流量通常是正常的
        elif traffic_type in ['HTTP', 'HTTPS']:
            risk_score = 15  # HTTP/HTTPS通常是正常的
        elif traffic_type == 'DNS':
            risk_score = 8   # DNS通常是正常的
        elif traffic_type == '恶意流量':
            # 重新评估，不直接判定为恶意
            risk_score = 35
        else:
            risk_score = 25  # 其他协议需要关注
        
        # 2. 白名单状态分析（基于CSV中的白名单字段）
        # 这里需要检查CSV中的"是否在白名单"字段
        # 由于我们没有直接访问这个字段，暂时跳过
        
        # 3. 基于URL内容的分析
        if content:
            content_lower = content.lower()
            
            # 正常应用路径（降低风险）
            normal_paths = ['app', 'blog', 'category', 'main', 'posts', 'tags', 'list', 'categories']
            normal_count = sum(1 for path in normal_paths if path in content_lower)
            if normal_count > 0:
                risk_score -= min(normal_count * 5, 15)  # 增加正常路径的权重
            
            # 可疑路径模式
            if 'wp-content' in content_lower:
                risk_score += 8
                risk_factors.append('包含wp-content路径')
            
            # 深层路径结构
            path_depth = content.count('/')
            if path_depth >= 4:  # 提高阈值
                risk_score += 10
                risk_factors.append(f'深层路径结构: {path_depth}层')
            elif path_depth <= 1:
                risk_score -= 5  # 简单路径降低风险
        
        # 4. IP地址分析
        # 内网到内网的通信通常是正常的
        if self._is_private_ip(source_ip) and self._is_private_ip(dest_ip):
            risk_score -= 10
        
        # 外网到内网需要评估，但不一定是恶意的
        elif not self._is_private_ip(source_ip) and self._is_private_ip(dest_ip):
            risk_score += 8  # 降低外网访问内网的风险评分
        
        # 5. 基于源IP的简单风险评估
        # 移除硬编码的恶意IP判断，改为更温和的评估
        
        # 6. 最终判定（调整阈值，让更多流量被判定为正常）
        if risk_score <= 12:
            return '白流量'
        elif risk_score <= 25:
            return '正常流量'
        elif risk_score <= 40:
            return '可疑流量'
        else:
            return '恶意流量'
    
    def _simple_rule_prediction(self, source_ip, dest_ip, traffic_type, content):
        """简单的规则预测（当AI模型不可用时）"""
        # 使用智能预测作为备用方案
        return self._intelligent_rule_prediction(source_ip, dest_ip, traffic_type, content)
    
    def _is_private_ip(self, ip):
        """判断是否为私有IP"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private
        except:
            return False
    
    def process_csv_data(self, df, user_id):
        """处理CSV文件数据"""
        count = 0
        required_columns = ['源IP', '目标IP', '流量类型', '请求内容摘要']
        
        # 列名映射
        column_mapping = {
            'source_ip': '源IP', 'src_ip': '源IP', 
            'dest_ip': '目标IP', 'destination_ip': '目标IP', 
            'traffic_type': '流量类型', 
            'content': '请求内容摘要', 'request': '请求内容摘要'
        }
        df = df.rename(columns=column_mapping)
        
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f'CSV 文件必须包含以下列：{required_columns}')

        for _, row in df.iterrows():
            try:
                predicted_type = self.predict_single(
                    str(row['源IP']), str(row['目标IP']), 
                    str(row['流量类型']), str(row['请求内容摘要'])
                )
                
                new_traffic = TrafficData(
                    source_ip=str(row['源IP']), 
                    dest_ip=str(row['目标IP']), 
                    traffic_type=str(row['流量类型']), 
                    predicted_type=predicted_type, 
                    user_id=user_id
                )
                db.session.add(new_traffic)
                count += 1
            except Exception as e:
                print(f"处理行时出错: {str(e)}")
                continue
        
        db.session.commit()
        return count
    
    def process_text_data(self, content, user_id):
        """处理文本文件数据"""
        count = 0
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            try:
                parts = line.split(',')
                if len(parts) < 4:
                    continue
                
                source_ip = parts[1].strip() if len(parts) > 1 else ''
                dest_ip = parts[2].strip() if len(parts) > 2 else ''
                traffic_type = parts[3].strip() if len(parts) > 3 else ''
                request_content = parts[4].strip() if len(parts) > 4 else ''
                
                predicted_type = self.predict_single(source_ip, dest_ip, traffic_type, request_content)
                
                new_traffic = TrafficData(
                    source_ip=source_ip, 
                    dest_ip=dest_ip, 
                    traffic_type=traffic_type, 
                    predicted_type=predicted_type, 
                    user_id=user_id
                )
                db.session.add(new_traffic)
                count += 1
            except Exception as e:
                print(f"处理行时出错: {str(e)}")
                continue
        
        db.session.commit()
        return count