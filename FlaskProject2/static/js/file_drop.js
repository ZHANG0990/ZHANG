// 文件拖放过滤功能的JavaScript代码
class FileDropManager {
    constructor() {
        this.selectedFiles = [];
        this.maxFileSize = 100 * 1024 * 1024; // 100MB
        this.allowedTypes = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/avi', 'video/mov',
            'audio/mp3', 'audio/wav', 'audio/flac',
            'application/pdf',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain', 'text/csv',
            'application/zip', 'application/x-rar-compressed'
        ];
        
        this.initializeElements();
        this.bindEvents();
    }
    
    initializeElements() {
        this.dropArea = document.getElementById('file-drop-area');
        this.fileInput = document.getElementById('file-input');
        this.fileList = document.getElementById('file-list');
        this.emptyState = document.getElementById('empty-file-state');
        this.fileCount = document.getElementById('file-count');
        this.clearBtn = document.getElementById('clear-files-btn');
        this.applyBtn = document.getElementById('apply-file-filter-btn');
    }
    
    bindEvents() {
        // 拖放事件
        this.dropArea.addEventListener('dragover', this.handleDragOver.bind(this));
        this.dropArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.dropArea.addEventListener('drop', this.handleDrop.bind(this));
        
        // 文件选择事件
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // 按钮事件
        this.clearBtn.addEventListener('click', this.clearAllFiles.bind(this));
        this.applyBtn.addEventListener('click', this.applyFileFilter.bind(this));
        
        // 阻止默认拖放行为
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.dropArea.addEventListener(eventName, this.preventDefaults, false);
            document.body.addEventListener(eventName, this.preventDefaults, false);
        });
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    handleDragOver(e) {
        this.dropArea.classList.add('border-primary', 'bg-primary/5');
    }
    
    handleDragLeave(e) {
        this.dropArea.classList.remove('border-primary', 'bg-primary/5');
    }
    
    handleDrop(e) {
        this.dropArea.classList.remove('border-primary', 'bg-primary/5');
        const files = e.dataTransfer.files;
        this.handleFiles(files);
    }
    
    handleFileSelect(e) {
        const files = e.target.files;
        this.handleFiles(files);
        // 重置input以允许重复选择同一文件
        e.target.value = '';
    }
    
    handleFiles(files) {
        const fileArray = Array.from(files);
        const validFiles = [];
        const errors = [];
        
        fileArray.forEach(file => {
            // 检查文件大小
            if (file.size > this.maxFileSize) {
                errors.push(`${file.name}: 文件过大（超过100MB）`);
                return;
            }
            
            // 检查文件类型
            if (!this.isAllowedType(file)) {
                errors.push(`${file.name}: 不支持的文件类型`);
                return;
            }
            
            // 检查是否重复
            if (this.isDuplicate(file)) {
                errors.push(`${file.name}: 文件已存在`);
                return;
            }
            
            validFiles.push(file);
        });
        
        // 显示错误信息
        if (errors.length > 0) {
            this.showToast(errors.join('\n'), 'error');
        }
        
        // 添加有效文件
        if (validFiles.length > 0) {
            this.selectedFiles = [...this.selectedFiles, ...validFiles];
            this.updateFileList();
            this.showToast(`成功添加 ${validFiles.length} 个文件`);
        }
    }
    
    isAllowedType(file) {
        return this.allowedTypes.includes(file.type) || 
               this.allowedTypes.some(type => file.name.toLowerCase().endsWith(type.split('/')[1]));
    }
    
    isDuplicate(file) {
        return this.selectedFiles.some(f => 
            f.name === file.name && f.size === file.size
        );
    }
    
    updateFileList() {
        // 更新文件计数
        this.fileCount.textContent = `${this.selectedFiles.length} 个文件`;
        
        // 显示/隐藏空状态
        if (this.selectedFiles.length === 0) {
            this.emptyState.classList.remove('hidden');
            return;
        } else {
            this.emptyState.classList.add('hidden');
        }
        
        // 清空当前列表（保留空状态元素）
        const fileItems = this.fileList.querySelectorAll('.file-item');
        fileItems.forEach(item => item.remove());
        
        // 添加文件项
        this.selectedFiles.forEach((file, index) => {
            const fileItem = this.createFileItem(file, index);
            this.fileList.appendChild(fileItem);
        });
    }
    
    createFileItem(file, index) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item py-3 flex items-center justify-between group border-b border-light-2 last:border-b-0';
        
        const fileIcon = this.getFileIcon(file);
        const fileSize = this.formatFileSize(file.size);
        const fileType = this.getFileType(file);
        
        fileItem.innerHTML = `
            <div class="flex items-center">
                <i class="fa ${fileIcon} text-primary mr-3 text-lg"></i>
                <div>
                    <p class="font-medium truncate max-w-md">${file.name}</p>
                    <p class="text-sm text-dark-2">${fileSize} · ${fileType}</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                <span class="text-xs px-2 py-1 bg-light-1 rounded-full text-dark-2">待分析</span>
                <button class="remove-file-btn text-dark-2 hover:text-danger transition-colors opacity-0 group-hover:opacity-100" 
                        data-index="${index}">
                    <i class="fa fa-times"></i>
                </button>
            </div>
        `;
        
        // 绑定删除事件
        const removeBtn = fileItem.querySelector('.remove-file-btn');
        removeBtn.addEventListener('click', () => this.removeFile(index));
        
        return fileItem;
    }
    
    getFileIcon(file) {
        const type = file.type.toLowerCase();
        const name = file.name.toLowerCase();
        
        if (type.startsWith('image/')) return 'fa-file-image-o';
        if (type.startsWith('video/')) return 'fa-file-video-o';
        if (type.startsWith('audio/')) return 'fa-file-audio-o';
        if (type.includes('pdf')) return 'fa-file-pdf-o';
        if (type.includes('word') || name.endsWith('.doc') || name.endsWith('.docx')) return 'fa-file-word-o';
        if (type.includes('excel') || name.endsWith('.xls') || name.endsWith('.xlsx')) return 'fa-file-excel-o';
        if (type.includes('zip') || type.includes('rar') || name.endsWith('.7z')) return 'fa-file-archive-o';
        if (name.endsWith('.csv')) return 'fa-file-text-o';
        
        return 'fa-file-o';
    }
    
    getFileType(file) {
        const type = file.type;
        if (type) return type;
        
        const ext = file.name.split('.').pop().toLowerCase();
        const typeMap = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png', 'gif': 'image/gif',
            'mp4': 'video/mp4', 'avi': 'video/avi', 'mov': 'video/mov',
            'mp3': 'audio/mp3', 'wav': 'audio/wav',
            'pdf': 'application/pdf',
            'doc': 'application/msword', 'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel', 'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain', 'csv': 'text/csv',
            'zip': 'application/zip', 'rar': 'application/x-rar-compressed'
        };
        
        return typeMap[ext] || '未知类型';
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    removeFile(index) {
        const removedFile = this.selectedFiles.splice(index, 1)[0];
        this.updateFileList();
        this.showToast(`已移除 ${removedFile.name}`);
    }
    
    clearAllFiles() {
        if (this.selectedFiles.length === 0) {
            this.showToast('没有可清空的文件', 'error');
            return;
        }
        
        if (confirm('确定要清空所有已选择的文件吗？')) {
            this.selectedFiles = [];
            this.updateFileList();
            this.showToast('已清空所有文件');
        }
    }
    
    async applyFileFilter() {
        // 检查是否有分析结果
        const analysisResults = document.getElementById('analysis-results');
        if (analysisResults && analysisResults.children.length > 0) {
            this.showToast('文件已分析完成，结果已保存到数据库');
            return;
        }
        
        if (this.selectedFiles.length === 0) {
            this.showToast('请先添加文件再应用过滤', 'error');
            return;
        }
        
        // 显示加载状态
        this.setLoading(this.applyBtn, true);
        this.showToast('正在进行AI分析...');
        
        try {
            // 创建FormData
            const formData = new FormData();
            this.selectedFiles.forEach(file => {
                formData.append('files', file);
            });
            
            // 发送请求
            const response = await fetch('/file-drop', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.displayAnalysisResults(result.results);
                this.showToast(result.message);
                
                // 分析完成后清空文件列表
                this.selectedFiles = [];
                this.updateFileList();
                
                // 更新按钮文本
                this.applyBtn.innerHTML = '<i class="fa fa-check"></i> 分析完成';
                setTimeout(() => {
                    this.applyBtn.innerHTML = '<i class="fa fa-filter"></i> AI分析';
                }, 3000);
            } else {
                this.showToast(result.error || '分析失败', 'error');
            }
            
        } catch (error) {
            console.error('文件分析错误:', error);
            this.showToast('网络错误，请重试', 'error');
        } finally {
            this.setLoading(this.applyBtn, false);
        }
    }
    
    displayAnalysisResults(results) {
        // 创建结果展示区域
        let resultArea = document.getElementById('analysis-results');
        if (!resultArea) {
            resultArea = document.createElement('div');
            resultArea.id = 'analysis-results';
            resultArea.className = 'card mt-6 fade-in';
            this.fileList.parentNode.insertBefore(resultArea, this.fileList.nextSibling);
        }
        
        resultArea.innerHTML = `
            <div class="flex items-center justify-between mb-4">
                <h3 class="font-bold">AI分析结果</h3>
                <div class="flex items-center gap-2">
                    <span class="status-dot online"></span>
                    <span class="text-sm text-success">分析完成</span>
                </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${results.map(result => this.createResultCard(result)).join('')}
            </div>
        `;
    }
    
    createResultCard(result) {
        if (result.error) {
            return `
                <div class="p-4 bg-danger/5 border border-danger/20 rounded-lg">
                    <div class="flex items-center gap-2 mb-2">
                        <i class="fa fa-exclamation-triangle text-danger"></i>
                        <span class="font-medium text-danger">分析失败</span>
                    </div>
                    <p class="text-sm text-dark-2 mb-1">${result.filename}</p>
                    <p class="text-xs text-danger">${result.error}</p>
                </div>
            `;
        }
        
        const isWhite = result.is_white_traffic;
        const confidence = (result.confidence * 100).toFixed(1);
        const riskScore = result.risk_score || 0;
        const riskFactors = result.risk_factors || [];
        
        // 根据风险评分确定颜色
        let cardClass, iconClass, textClass, riskLevel;
        if (riskScore >= 50) {
            cardClass = 'bg-danger/5 border-danger/20';
            iconClass = 'fa-exclamation-circle text-danger';
            textClass = 'text-danger';
            riskLevel = '高风险';
        } else if (riskScore >= 30) {
            cardClass = 'bg-warning/5 border-warning/20';
            iconClass = 'fa-exclamation-triangle text-warning';
            textClass = 'text-warning';
            riskLevel = '中风险';
        } else {
            cardClass = 'bg-success/5 border-success/20';
            iconClass = 'fa-check-circle text-success';
            textClass = 'text-success';
            riskLevel = '低风险';
        }
        
        const riskFactorsHtml = riskFactors.length > 0 ? 
            `<div class="mt-2 pt-2 border-t border-light-2">
                <p class="text-xs text-dark-2 mb-1">风险因素:</p>
                ${riskFactors.map(factor => `<span class="inline-block text-xs px-2 py-1 bg-light-1 rounded-full mr-1 mb-1">${factor}</span>`).join('')}
            </div>` : '';
        
        return `
            <div class="p-4 ${cardClass} border rounded-lg">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center gap-2">
                        <i class="fa ${iconClass}"></i>
                        <span class="font-medium ${textClass}">
                            ${isWhite ? '白流量' : '可疑流量'}
                        </span>
                    </div>
                    <span class="text-xs px-2 py-1 bg-light-1 rounded-full">${riskLevel}</span>
                </div>
                <p class="text-sm text-dark-2 mb-1 truncate">${result.filename}</p>
                <div class="flex justify-between text-xs text-dark-2 mb-1">
                    <span>${result.type}</span>
                    <span>置信度: ${confidence}%</span>
                </div>
                <div class="flex justify-between text-xs text-dark-2">
                    <span>风险评分: ${riskScore}分</span>
                    <span>${result.details ? result.details.split('，')[0] : ''}</span>
                </div>
                ${riskFactorsHtml}
            </div>
        `;
    }
    
    setLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            button.innerHTML = '<i class="fa fa-spinner fa-spin"></i> 分析中...';
        } else {
            button.disabled = false;
            button.innerHTML = '<i class="fa fa-filter"></i> 应用过滤';
        }
    }
    
    showToast(message, type = 'success') {
        // 使用全局的showToast函数
        if (typeof showToast === 'function') {
            showToast(message, type === 'error');
        } else {
            // 备用方案
            console.log(`${type.toUpperCase()}: ${message}`);
            alert(message);
        }
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    new FileDropManager();
});