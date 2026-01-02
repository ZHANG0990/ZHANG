#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络流量分类模型训练脚本
支持数据生成、模型训练、评估和优化
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib
import os
from datetime import datetime, timedelta
import random
import warnings
warnings.filterwarnings('ignore')

# 可选依赖
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("提示: XGBoost未安装，可运行 'pip install xgboost' 安装以获得更好性能")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False
    print("提示: matplotlib/seaborn未安装，将跳过可视化功能")

class TrafficDataGenerator:
    """网络流量数据生成器"""
    
    def __init__(self):
        # 常见端口和协议
        self.common_ports = {
            'HTTP': [80, 8080, 8000, 3000],
            'HTTPS': [443, 8443],
            'SSH': [22],
            'FTP': [21, 20],
            'DNS': [53],
            'SMTP': [25, 587],
            'POP3': [110, 995],
            'IMAP': [143, 993],
            'TELNET': [23],
            'SNMP': [161, 162]
        }
        
        # 攻击类型和特征
        self.attack_patterns = {
            'DDoS': {
                'packet_count_range': (10000, 100000),
                'byte_count_range': (1000000, 50000000),
                'duration_range': (1, 30),
                'protocols': ['TCP', 'UDP', 'ICMP'],
                'port_scan': False
            },
            'Port_Scan': {
                'packet_count_range': (100, 1000),
                'byte_count_range': (5000, 50000),
                'duration_range': (10, 300),
                'protocols': ['TCP'],
                'port_scan': True
            },
            'Brute_Force': {
                'packet_count_range': (50, 500),
                'byte_count_range': (2000, 20000),
                'duration_range': (60, 1800),
                'protocols': ['TCP'],
                'port_scan': False
            },
            'SQL_Injection': {
                'packet_count_range': (10, 100),
                'byte_count_range': (1000, 10000),
                'duration_range': (1, 60),
                'protocols': ['TCP'],
                'port_scan': False
            },
            'Malware': {
                'packet_count_range': (100, 2000),
                'byte_count_range': (10000, 200000),
                'duration_range': (30, 600),
                'protocols': ['TCP', 'UDP'],
                'port_scan': False
            }
        }
    
    def generate_ip(self, is_internal=True):
        """生成IP地址"""
        if is_internal:
            # 内网IP
            networks = ['192.168.', '10.', '172.16.']
            network = random.choice(networks)
            if network == '192.168.':
                return f"{network}{random.randint(1, 255)}.{random.randint(1, 254)}"
            elif network == '10.':
                return f"{network}{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 254)}"
            else:
                return f"{network}{random.randint(16, 31)}.{random.randint(1, 254)}"
        else:
            # 外网IP
            return f"{random.randint(1, 223)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 254)}"
    
    def generate_normal_traffic(self, count):
        """生成正常流量数据"""
        data = []
        
        for _ in range(count):
            protocol = random.choice(['TCP', 'UDP', 'ICMP'])
            
            # 选择常见端口
            service = random.choice(list(self.common_ports.keys()))
            dst_port = random.choice(self.common_ports[service])
            src_port = random.randint(1024, 65535)
            
            # 正常流量特征
            packet_count = random.randint(1, 1000)
            byte_count = random.randint(64, 100000)
            duration = random.uniform(0.1, 300)
            
            # 计算衍生特征
            packets_per_second = packet_count / max(duration, 0.1)
            bytes_per_packet = byte_count / max(packet_count, 1)
            bytes_per_second = byte_count / max(duration, 0.1)
            
            data.append({
                'timestamp': datetime.now() - timedelta(seconds=random.randint(0, 86400)),
                'src_ip': self.generate_ip(True),
                'dst_ip': self.generate_ip(random.choice([True, False])),
                'src_port': src_port,
                'dst_port': dst_port,
                'protocol': protocol,
                'packet_count': packet_count,
                'byte_count': byte_count,
                'duration': round(duration, 2),
                'packets_per_second': round(packets_per_second, 2),
                'bytes_per_packet': round(bytes_per_packet, 2),
                'bytes_per_second': round(bytes_per_second, 2),
                'is_weekend': random.choice([0, 1]),
                'hour_of_day': random.randint(0, 23),
                'label': 'Normal'
            })
        
        return data
    
    def generate_attack_traffic(self, attack_type, count):
        """生成攻击流量数据"""
        data = []
        pattern = self.attack_patterns[attack_type]
        
        for _ in range(count):
            protocol = random.choice(pattern['protocols'])
            
            # 攻击流量特征
            packet_count = random.randint(*pattern['packet_count_range'])
            byte_count = random.randint(*pattern['byte_count_range'])
            duration = random.uniform(*pattern['duration_range'])
            
            # 端口扫描特征
            if pattern['port_scan']:
                dst_port = random.randint(1, 65535)
                src_port = random.randint(1024, 65535)
            else:
                # 针对常见服务的攻击
                service = random.choice(list(self.common_ports.keys()))
                dst_port = random.choice(self.common_ports[service])
                src_port = random.randint(1024, 65535)
            
            # 计算衍生特征
            packets_per_second = packet_count / max(duration, 0.1)
            bytes_per_packet = byte_count / max(packet_count, 1)
            bytes_per_second = byte_count / max(duration, 0.1)
            
            data.append({
                'timestamp': datetime.now() - timedelta(seconds=random.randint(0, 86400)),
                'src_ip': self.generate_ip(False),  # 攻击通常来自外网
                'dst_ip': self.generate_ip(True),   # 目标通常是内网
                'src_port': src_port,
                'dst_port': dst_port,
                'protocol': protocol,
                'packet_count': packet_count,
                'byte_count': byte_count,
                'duration': round(duration, 2),
                'packets_per_second': round(packets_per_second, 2),
                'bytes_per_packet': round(bytes_per_packet, 2),
                'bytes_per_second': round(bytes_per_second, 2),
                'is_weekend': random.choice([0, 1]),
                'hour_of_day': random.randint(0, 23),
                'label': attack_type
            })
        
        return data
    
    def generate_dataset(self, total_samples=10000):
        """生成完整数据集"""
        print(f"正在生成 {total_samples} 条流量数据...")
        
        # 数据分布：70%正常流量，30%攻击流量
        normal_count = int(total_samples * 0.7)
        attack_count = total_samples - normal_count
        
        # 生成正常流量
        data = self.generate_normal_traffic(normal_count)
        print(f"生成正常流量: {normal_count} 条")
        
        # 生成各种攻击流量
        attack_types = list(self.attack_patterns.keys())
        attack_per_type = attack_count // len(attack_types)
        
        for attack_type in attack_types:
            attack_data = self.generate_attack_traffic(attack_type, attack_per_type)
            data.extend(attack_data)
            print(f"生成 {attack_type} 攻击流量: {attack_per_type} 条")
        
        # 转换为DataFrame并打乱顺序
        df = pd.DataFrame(data)
        df = df.sample(frac=1).reset_index(drop=True)
        
        print(f"数据集生成完成，总计 {len(df)} 条记录")
        print(f"标签分布:\n{df['label'].value_counts()}")
        
        return df

class AdvancedTrafficClassifier:
    """高级网络流量分类器"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.label_encoder = LabelEncoder()
        self.feature_importance = {}
        self.best_model = None
        self.best_score = 0
        
    def load_and_preprocess_data(self, data_path=None, df=None):
        """加载和预处理数据"""
        if df is not None:
            print("使用提供的DataFrame...")
        else:
            print("正在加载数据...")
            df = pd.read_csv(data_path)
        
        # 处理时间特征
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # IP地址特征工程
        if 'src_ip' in df.columns:
            df['src_ip_class'] = df['src_ip'].apply(self.get_ip_class)
            df['src_ip_private'] = df['src_ip'].apply(self.is_private_ip).astype(int)
        
        if 'dst_ip' in df.columns:
            df['dst_ip_class'] = df['dst_ip'].apply(self.get_ip_class)
            df['dst_ip_private'] = df['dst_ip'].apply(self.is_private_ip).astype(int)
        
        # 端口特征
        if 'dst_port' in df.columns:
            df['is_common_port'] = df['dst_port'].apply(self.is_common_port).astype(int)
            df['port_category'] = df['dst_port'].apply(self.categorize_port)
        
        # 流量统计特征
        if 'packets_per_second' in df.columns:
            df['pps_log'] = np.log1p(df['packets_per_second'])
        if 'bytes_per_second' in df.columns:
            df['bps_log'] = np.log1p(df['bytes_per_second'])
        
        return df
    
    def get_ip_class(self, ip):
        """获取IP地址类别"""
        try:
            first_octet = int(ip.split('.')[0])
            if 1 <= first_octet <= 126:
                return 'A'
            elif 128 <= first_octet <= 191:
                return 'B'
            elif 192 <= first_octet <= 223:
                return 'C'
            else:
                return 'Other'
        except:
            return 'Invalid'
    
    def is_private_ip(self, ip):
        """判断是否为私有IP"""
        try:
            octets = ip.split('.')
            first = int(octets[0])
            second = int(octets[1])
            
            if first == 10:
                return True
            elif first == 172 and 16 <= second <= 31:
                return True
            elif first == 192 and second == 168:
                return True
            elif ip == '127.0.0.1':
                return True
            return False
        except:
            return False
    
    def is_common_port(self, port):
        """判断是否为常见端口"""
        common_ports = {80, 443, 22, 21, 25, 53, 110, 143, 993, 995, 587, 465}
        return port in common_ports
    
    def categorize_port(self, port):
        """端口分类"""
        if port < 1024:
            return 'system'
        elif port < 49152:
            return 'registered'
        else:
            return 'dynamic'
    
    def prepare_features(self, df):
        """准备特征数据"""
        # 选择数值特征
        numeric_features = ['packet_count', 'byte_count', 'duration', 
                          'packets_per_second', 'bytes_per_packet', 'bytes_per_second',
                          'hour_of_day', 'is_weekend']
        
        # 选择分类特征
        categorical_features = ['protocol', 'src_ip_class', 'dst_ip_class', 'port_category']
        
        # 添加新特征
        if 'pps_log' in df.columns:
            numeric_features.append('pps_log')
        if 'bps_log' in df.columns:
            numeric_features.append('bps_log')
        if 'src_ip_private' in df.columns:
            numeric_features.append('src_ip_private')
        if 'dst_ip_private' in df.columns:
            numeric_features.append('dst_ip_private')
        if 'is_common_port' in df.columns:
            numeric_features.append('is_common_port')
        
        # 处理缺失值
        for feature in numeric_features:
            if feature in df.columns:
                df[feature] = df[feature].fillna(df[feature].median())
        
        # 编码分类特征
        for feature in categorical_features:
            if feature in df.columns:
                if feature not in self.scalers:
                    self.scalers[feature] = LabelEncoder()
                    df[feature] = self.scalers[feature].fit_transform(df[feature].astype(str))
                else:
                    df[feature] = self.scalers[feature].transform(df[feature].astype(str))
        
        # 选择最终特征
        available_features = [f for f in numeric_features + categorical_features if f in df.columns]
        X = df[available_features]
        
        return X, available_features
    
    def train_models(self, X, y):
        """训练多个模型"""
        print("正在训练多个模型...")
        
        # 数据标准化
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        self.scalers['feature_scaler'] = scaler
        
        # 分割数据
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # 定义模型
        models = {
            'RandomForest': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
            'GradientBoosting': GradientBoostingClassifier(random_state=42),
            'LogisticRegression': LogisticRegression(random_state=42, max_iter=1000),
            'SVM': SVC(random_state=42, probability=True),
            'NeuralNetwork': MLPClassifier(random_state=42, max_iter=300)
        }
        
        # 添加XGBoost（如果可用）
        if HAS_XGBOOST:
            models['XGBoost'] = xgb.XGBClassifier(random_state=42, eval_metric='mlogloss')
        
        # 训练和评估每个模型
        results = {}
        for name, model in models.items():
            print(f"训练 {name}...")
            
            # 训练模型
            model.fit(X_train, y_train)
            
            # 预测
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # 交叉验证
            cv_scores = cross_val_score(model, X_train, y_train, cv=3)
            
            # 保存结果
            results[name] = {
                'model': model,
                'accuracy': accuracy,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            }
            
            # 保存模型
            self.models[name] = model
            
            print(f"{name} - 准确率: {accuracy:.4f}, 交叉验证: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
            
            # 更新最佳模型
            if cv_scores.mean() > self.best_score:
                self.best_score = cv_scores.mean()
                self.best_model = name
        
        print(f"\n最佳模型: {self.best_model} (交叉验证得分: {self.best_score:.4f})")
        
        return results, X_test, y_test
    
    def save_models(self):
        """保存模型"""
        os.makedirs('static/models', exist_ok=True)
        
        # 保存最佳模型
        best_model = self.models[self.best_model]
        joblib.dump(best_model, 'static/models/advanced_traffic_model.pkl')
        
        # 保存编码器和缩放器
        joblib.dump(self.scalers, 'static/models/categorical_encoders.pkl')
        joblib.dump(self.label_encoder, 'static/models/label_encoder.pkl')
        
        # 单独保存特征缩放器
        if 'feature_scaler' in self.scalers:
            joblib.dump(self.scalers['feature_scaler'], 'static/models/feature_scaler.pkl')
        
        # 保存模型信息
        model_info = {
            'best_model': self.best_model,
            'best_score': self.best_score,
            'feature_names': getattr(self, 'feature_names', []),
            'accuracy': self.best_score,
            'classes': self.label_encoder.classes_.tolist()
        }
        joblib.dump(model_info, 'static/models/model_info.pkl')
        
        print(f"模型已保存到 static/models/")

def main(data_size=10000, use_existing_data=False):
    """主函数"""
    print("🚀 开始训练高级网络流量分类模型")
    print("=" * 50)
    
    # 1. 生成或加载数据
    if use_existing_data and os.path.exists('traffic_training_data.csv'):
        print("📊 使用现有训练数据...")
        classifier = AdvancedTrafficClassifier()
        df = classifier.load_and_preprocess_data('traffic_training_data.csv')
    else:
        print("📊 生成新的训练数据...")
        generator = TrafficDataGenerator()
        dataset = generator.generate_dataset(data_size)
        dataset.to_csv('traffic_training_data.csv', index=False)
        
        # 2. 训练高级模型
        classifier = AdvancedTrafficClassifier()
        df = classifier.load_and_preprocess_data(df=dataset)
    
    print("\n🤖 初始化高级分类器")
    
    # 3. 准备特征
    print("🔧 数据预处理和特征工程...")
    X, feature_names = classifier.prepare_features(df)
    classifier.feature_names = feature_names
    
    # 编码标签
    y = classifier.label_encoder.fit_transform(df['label'])
    
    print(f"特征维度: {X.shape}")
    print(f"类别分布: {dict(zip(classifier.label_encoder.classes_, np.bincount(y)))}")
    
    # 4. 训练模型
    print("\n🎯 训练多种机器学习模型...")
    results, X_test, y_test = classifier.train_models(X, y)
    
    # 5. 保存模型
    print("\n💾 保存训练好的模型...")
    classifier.save_models()
    
    print("\n🎉 模型训练完成!")
    print("=" * 50)
    print(f"最佳模型: {classifier.best_model}")
    print(f"交叉验证得分: {classifier.best_score:.4f}")
    print("模型文件保存在: static/models/")
    
    return classifier

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='训练网络流量分类模型')
    parser.add_argument('--size', type=int, default=10000, help='训练数据大小 (默认: 10000)')
    parser.add_argument('--use-existing', action='store_true', help='使用现有的训练数据文件')
    
    args = parser.parse_args()
    
    main(data_size=args.size, use_existing_data=args.use_existing)