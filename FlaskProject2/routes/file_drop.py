from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import mimetypes
from datetime import datetime
from models.database import db, FileAnalysis
import logging

file_drop_bp = Blueprint('file_drop', __name__)

# 配置上传文件夹和允许的文件类型
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 
    'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar', '7z',
    'mp4', 'avi', 'mov', 'mp3', 'wav', 'csv'
}

def allowed_file(filename):
    """检查文件类型是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_category(filename):
    """根据文件扩展名获取文件类别"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
        return '图片'
    elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv']:
        return '视频'
    elif ext in ['mp3', 'wav', 'flac', 'aac', 'm4a']:
        return '音频'
    elif ext in ['doc', 'docx', 'txt', 'rtf']:
        return '文档'
    elif ext in ['xls', 'xlsx', 'csv']:
        return '表格'
    elif ext in ['pdf']:
        return 'PDF'
    elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
        return '压缩包'
    else:
        return '其他'

def analyze_file_with_ai(file_path, filename):
    """使用AI分析文件是否为白流量相关"""
    # 这里模拟AI分析逻辑
    # 实际应用中可以集成机器学习模型
    
    file_category = get_file_category(filename)
    file_size = os.path.getsize(file_path)
    
    # 简单的规则判断（实际应该使用训练好的模型）
    confidence = 0.0
    is_white_traffic = False
    
    # 基于文件类型和大小的简单判断逻辑
    if file_category in ['图片', '视频', '音频']:
        if file_size < 100 * 1024 * 1024:  # 小于100MB
            is_white_traffic = True
            confidence = 0.85
        else:
            is_white_traffic = False
            confidence = 0.65
    elif file_category in ['文档', 'PDF']:
        if file_size < 10 * 1024 * 1024:  # 小于10MB
            is_white_traffic = True
            confidence = 0.90
        else:
            is_white_traffic = False
            confidence = 0.70
    elif file_category == '压缩包':
        is_white_traffic = False
        confidence = 0.75
    else:
        is_white_traffic = True
        confidence = 0.60
    
    return {
        'is_white_traffic': is_white_traffic,
        'confidence': confidence,
        'category': file_category,
        'analysis_time': datetime.now()
    }

@file_drop_bp.route('/file-drop', methods=['GET', 'POST'])
@login_required
def file_drop():
    """文件拖放过滤页面"""
    if request.method == 'POST':
        try:
            # 处理文件上传
            if 'files' not in request.files:
                return jsonify({'error': '没有文件被上传'}), 400
            
            files = request.files.getlist('files')
            results = []
            
            for file in files:
                if file.filename == '':
                    continue
                
                if file and allowed_file(file.filename):
                    # 保存文件
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                    unique_filename = timestamp + filename
                    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                    
                    # 确保上传目录存在
                    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                    file.save(file_path)
                    
                    # AI分析
                    analysis_result = analyze_file_with_ai(file_path, filename)
                    
                    # 保存到数据库
                    file_analysis = FileAnalysis(
                        filename=unique_filename,
                        original_name=filename,
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        file_type=analysis_result['category'],
                        is_white_traffic=analysis_result['is_white_traffic'],
                        confidence=analysis_result['confidence'],
                        user_id=current_user.id
                    )
                    
                    db.session.add(file_analysis)
                    db.session.commit()
                    
                    results.append({
                        'filename': filename,
                        'size': os.path.getsize(file_path),
                        'type': analysis_result['category'],
                        'is_white_traffic': analysis_result['is_white_traffic'],
                        'confidence': analysis_result['confidence']
                    })
                else:
                    results.append({
                        'filename': file.filename,
                        'error': '不支持的文件类型'
                    })
            
            return jsonify({
                'success': True,
                'results': results,
                'message': f'成功分析了 {len(results)} 个文件'
            })
            
        except Exception as e:
            logging.error(f"文件处理错误: {str(e)}")
            return jsonify({'error': '文件处理失败'}), 500
    
    # GET请求 - 显示页面和历史记录
    try:
        # 获取最近的分析记录
        file_records = FileAnalysis.query.filter_by(user_id=current_user.id)\
                                        .order_by(FileAnalysis.analysis_time.desc())\
                                        .limit(20).all()
        
        return render_template('file_drop.html', file_records=file_records)
        
    except Exception as e:
        logging.error(f"获取文件记录错误: {str(e)}")
        return render_template('file_drop.html', file_records=[])

@file_drop_bp.route('/api/file-analysis/<int:file_id>')
@login_required
def get_file_analysis(file_id):
    """获取单个文件的分析详情"""
    try:
        record = FileAnalysis.query.filter_by(id=file_id, user_id=current_user.id).first()
        
        if record:
            return jsonify({
                'id': record.id,
                'filename': record.filename,
                'original_name': record.original_name,
                'file_path': record.file_path,
                'file_size': record.file_size,
                'file_type': record.file_type,
                'is_white_traffic': record.is_white_traffic,
                'confidence': record.confidence,
                'analysis_time': record.analysis_time.isoformat()
            })
        else:
            return jsonify({'error': '文件记录不存在'}), 404
            
    except Exception as e:
        logging.error(f"获取文件分析错误: {str(e)}")
        return jsonify({'error': '获取文件分析失败'}), 500

@file_drop_bp.route('/api/clear-files', methods=['POST'])
@login_required
def clear_files():
    """清空所有文件记录"""
    try:
        # 获取所有文件路径用于删除物理文件
        file_records = FileAnalysis.query.filter_by(user_id=current_user.id).all()
        
        # 删除物理文件
        for record in file_records:
            try:
                if os.path.exists(record.file_path):
                    os.remove(record.file_path)
            except Exception as e:
                logging.warning(f"删除文件失败: {record.file_path}, 错误: {str(e)}")
        
        # 清空数据库记录
        FileAnalysis.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '已清空所有文件记录'
        })
        
    except Exception as e:
        logging.error(f"清空文件错误: {str(e)}")
        return jsonify({'error': '清空文件失败'}), 500