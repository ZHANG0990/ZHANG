/**
 * 告警中心JavaScript模块
 */
class AlertsManager {
  constructor() {
    this.alerts = [];
    this.filteredAlerts = [];
    this.init();
  }

  init() {
    this.bindElements();
    this.bindEvents();
    this.loadAlerts();
    
    // 每30秒自动刷新一次
    setInterval(() => {
      this.loadAlerts();
    }, 30000);
  }

  bindElements() {
    this.elements = {
      alertTypeFilter: document.getElementById('alert-type-filter'),
      alertStatusFilter: document.getElementById('alert-status-filter'),
      searchInput: document.getElementById('search-alerts'),
      refreshBtn: document.getElementById('refresh-alerts'),
      alertsContainer: document.getElementById('alerts-container'),
      emptyState: document.getElementById('empty-alerts-state'),
      
      // 统计元素
      pendingAlerts: document.getElementById('pending-alerts'),
      processingAlerts: document.getElementById('processing-alerts'),
      resolvedAlerts: document.getElementById('resolved-alerts'),
      todayAlerts: document.getElementById('today-alerts'),
      
      // 模态框元素
      alertModal: document.getElementById('alert-detail-modal'),
      alertModalContent: document.getElementById('alert-modal-content'),
      alertDetailContent: document.getElementById('alert-detail-content'),
      closeAlertModalBtn: document.getElementById('close-alert-modal'),
      alertModalBackdrop: document.getElementById('alert-modal-backdrop'),
      markProcessingBtn: document.getElementById('mark-processing'),
      markResolvedBtn: document.getElementById('mark-resolved')
    };
  }

  bindEvents() {
    // 筛选和搜索事件
    this.elements.alertTypeFilter.addEventListener('change', () => this.filterAlerts());
    this.elements.alertStatusFilter.addEventListener('change', () => this.filterAlerts());
    this.elements.searchInput.addEventListener('input', () => this.filterAlerts());
    
    // 刷新按钮
    this.elements.refreshBtn.addEventListener('click', () => this.loadAlerts());
    
    // 模态框事件
    this.elements.closeAlertModalBtn.addEventListener('click', () => this.closeModal());
    this.elements.alertModalBackdrop.addEventListener('click', () => this.closeModal());
    
    // ESC键关闭模态框
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !this.elements.alertModal.classList.contains('hidden')) {
        this.closeModal();
      }
    });
  }

  async loadAlerts() {
    try {
      const response = await fetch('/api/alerts');
      const data = await response.json();
      
      if (data.success) {
        this.alerts = data.alerts;
        this.updateStats();
        this.filterAlerts();
      } else {
        this.showToast('加载告警数据失败: ' + data.message, 'error');
      }
    } catch (error) {
      console.error('加载告警失败:', error);
      this.showToast('网络错误，无法加载告警数据', 'error');
    }
  }

  updateStats() {
    const pending = this.alerts.filter(a => a.status === 'pending').length;
    const processing = this.alerts.filter(a => a.status === 'processing').length;
    const resolved = this.alerts.filter(a => a.status === 'resolved').length;
    
    // 计算今日新增
    const today = new Date().toDateString();
    const todayCount = this.alerts.filter(a => {
      const alertDate = new Date(a.created_at).toDateString();
      return alertDate === today;
    }).length;
    
    this.elements.pendingAlerts.textContent = pending;
    this.elements.processingAlerts.textContent = processing;
    this.elements.resolvedAlerts.textContent = resolved;
    this.elements.todayAlerts.textContent = todayCount;
  }

  filterAlerts() {
    const typeFilter = this.elements.alertTypeFilter.value;
    const statusFilter = this.elements.alertStatusFilter.value;
    const searchTerm = this.elements.searchInput.value.toLowerCase();
    
    this.filteredAlerts = this.alerts.filter(alert => {
      // 类型筛选
      if (typeFilter && alert.alert_type !== typeFilter) {
        return false;
      }
      
      // 状态筛选
      if (statusFilter && alert.status !== statusFilter) {
        return false;
      }
      
      // 搜索筛选
      if (searchTerm) {
        const searchableText = [
          alert.title,
          alert.message,
          alert.source_ip || '',
          alert.dest_ip || ''
        ].join(' ').toLowerCase();
        
        if (!searchableText.includes(searchTerm)) {
          return false;
        }
      }
      
      return true;
    });
    
    this.renderAlerts();
  }

  renderAlerts() {
    if (this.filteredAlerts.length === 0) {
      this.elements.emptyState.classList.remove('hidden');
      this.elements.alertsContainer.innerHTML = '';
      this.elements.alertsContainer.appendChild(this.elements.emptyState);
      return;
    }
    
    this.elements.emptyState.classList.add('hidden');
    
    const alertsHtml = this.filteredAlerts.map(alert => this.renderAlertItem(alert)).join('');
    this.elements.alertsContainer.innerHTML = alertsHtml;
  }

  renderAlertItem(alert) {
    const severityMap = {
      'danger': { color: 'danger', text: '高', icon: 'fa-exclamation-triangle' },
      'warning': { color: 'warning', text: '中', icon: 'fa-exclamation-circle' },
      'info': { color: 'primary', text: '低', icon: 'fa-info-circle' }
    };
    
    const statusMap = {
      'pending': { color: 'danger', text: '未处理', icon: 'fa-clock-o' },
      'processing': { color: 'warning', text: '处理中', icon: 'fa-spinner' },
      'resolved': { color: 'success', text: '已解决', icon: 'fa-check-circle' }
    };
    
    const severity = severityMap[alert.alert_type] || { color: 'primary', text: '未知', icon: 'fa-question-circle' };
    const status = statusMap[alert.status] || { color: 'secondary', text: '未知', icon: 'fa-question-circle' };
    
    // 解析流量信息（简化版）
    const trafficInfo = this.parseTrafficInfo(alert.message);
    
    return `
      <div class="alert-item ${alert.status === 'pending' ? 'unread' : ''}" data-alert-id="${alert.id}">
        <div class="alert-item-header">
          <div class="alert-severity-indicator">
            <i class="fa ${severity.icon} text-${severity.color}"></i>
          </div>
          <div class="alert-item-content">
            <div class="alert-title-row">
              ${alert.status === 'pending' ? '<span class="alert-unread-dot"></span>' : ''}
              <h4 class="alert-title">${this.escapeHtml(alert.title)}</h4>
              <div class="alert-tags">
                <span class="alert-tag ${severity.color}">
                  <i class="fa ${severity.icon}"></i> ${severity.text}级
                </span>
                <span class="alert-tag ${status.color}">
                  <i class="fa ${status.icon}"></i> ${status.text}
                </span>
              </div>
            </div>
            
            ${trafficInfo ? this.renderTrafficInfoPreview(trafficInfo) : `
              <div class="alert-description">
                <p>${this.escapeHtml(alert.message)}</p>
              </div>
            `}
            
            <div class="alert-meta-info">
              <div class="alert-meta-row">
                <span class="alert-meta-item">
                  <i class="fa fa-clock-o"></i>
                  <span>创建: ${this.formatTime(alert.created_at)}</span>
                </span>
                ${alert.resolved_at ? `
                  <span class="alert-meta-item">
                    <i class="fa fa-check"></i>
                    <span>解决: ${this.formatTime(alert.resolved_at)}</span>
                  </span>
                ` : ''}
                ${alert.source_ip ? `
                  <span class="alert-meta-item">
                    <i class="fa fa-server"></i>
                    <span>来源: ${alert.source_ip}</span>
                  </span>
                ` : ''}
              </div>
            </div>
          </div>
          <div class="alert-actions">
            <button class="alert-action-btn primary" onclick="alertsManager.viewDetail(${alert.id})" title="查看详情">
              <i class="fa fa-eye"></i>
            </button>
            ${alert.status === 'pending' ? `
              <button class="alert-action-btn success" onclick="alertsManager.updateStatus(${alert.id}, 'resolved')" title="标记已解决">
                <i class="fa fa-check"></i>
              </button>
            ` : ''}
            <button class="alert-action-btn secondary" onclick="alertsManager.copyAlertInfo(${alert.id})" title="复制信息">
              <i class="fa fa-copy"></i>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  renderTrafficInfoPreview(trafficInfo) {
    const getPredictionColor = (prediction) => {
      if (prediction && prediction.includes('可疑')) return 'warning';
      if (prediction && prediction.includes('恶意')) return 'danger';
      if (prediction && prediction.includes('正常')) return 'success';
      return 'primary';
    };
    
    const predictionColor = getPredictionColor(trafficInfo.aiPrediction);
    
    return `
      <div class="traffic-preview">
        <div class="traffic-preview-header">
          <i class="fa fa-shield text-warning"></i>
          <span class="traffic-preview-title">流量威胁检测</span>
        </div>
        <div class="traffic-preview-content">
          <div class="traffic-preview-row">
            ${trafficInfo.sourceIp ? `
              <div class="traffic-preview-item">
                <i class="fa fa-arrow-right text-primary"></i>
                <span class="traffic-preview-label">源IP:</span>
                <code class="traffic-preview-value">${this.escapeHtml(trafficInfo.sourceIp)}</code>
              </div>
            ` : ''}
            ${trafficInfo.destIp ? `
              <div class="traffic-preview-item">
                <i class="fa fa-bullseye text-success"></i>
                <span class="traffic-preview-label">目标IP:</span>
                <code class="traffic-preview-value">${this.escapeHtml(trafficInfo.destIp)}</code>
              </div>
            ` : ''}
            ${trafficInfo.trafficType ? `
              <div class="traffic-preview-item">
                <i class="fa fa-exchange text-info"></i>
                <span class="traffic-preview-label">类型:</span>
                <span class="traffic-preview-value">${this.escapeHtml(trafficInfo.trafficType)}</span>
              </div>
            ` : ''}
          </div>
          ${trafficInfo.aiPrediction ? `
            <div class="traffic-prediction">
              <i class="fa fa-brain text-${predictionColor}"></i>
              <span class="traffic-prediction-label">AI预测:</span>
              <span class="alert-tag ${predictionColor}">${this.escapeHtml(trafficInfo.aiPrediction)}</span>
            </div>
          ` : ''}
          ${trafficInfo.requestContent ? `
            <div class="traffic-request-preview">
              <i class="fa fa-code text-danger"></i>
              <span class="traffic-request-label">检测到恶意载荷:</span>
              <code class="traffic-request-snippet">${this.escapeHtml(trafficInfo.requestContent.substring(0, 50))}${trafficInfo.requestContent.length > 50 ? '...' : ''}</code>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  formatTime(timeString) {
    const date = new Date(timeString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
    
    return date.toLocaleDateString('zh-CN');
  }

  copyAlertInfo(alertId) {
    const alert = this.alerts.find(a => a.id === alertId);
    if (!alert) return;
    
    const info = `告警信息:
标题: ${alert.title}
类型: ${this.getAlertTypeText(alert.alert_type)}
状态: ${alert.status}
创建时间: ${alert.created_at}
${alert.source_ip ? `来源IP: ${alert.source_ip}` : ''}
${alert.dest_ip ? `目标IP: ${alert.dest_ip}` : ''}
详细信息: ${alert.message}`;
    
    navigator.clipboard.writeText(info).then(() => {
      this.showToast('告警信息已复制到剪贴板', 'success');
    }).catch(() => {
      this.showToast('复制失败，请手动复制', 'error');
    });
  }

  getAlertTypeText(type) {
    const typeMap = {
      'danger': '危险告警',
      'warning': '警告告警',
      'info': '信息告警'
    };
    return typeMap[type] || '未知类型';
  }

  async viewDetail(alertId) {
    const alert = this.alerts.find(a => a.id === alertId);
    if (!alert) return;
    
    const severityMap = {
      'danger': { color: 'danger', text: '高' },
      'warning': { color: 'warning', text: '中' },
      'info': { color: 'primary', text: '低' }
    };
    
    const statusMap = {
      'pending': { color: 'danger', text: '未处理' },
      'processing': { color: 'warning', text: '处理中' },
      'resolved': { color: 'success', text: '已解决' }
    };
    
    const severity = severityMap[alert.alert_type] || { color: 'primary', text: '未知' };
    const status = statusMap[alert.status] || { color: 'secondary', text: '未知' };
    
    // 解析流量信息（如果存在）
    const trafficInfo = this.parseTrafficInfo(alert.message);
    
    this.elements.alertDetailContent.innerHTML = `
      <div class="space-y-4">
        <div class="flex items-center gap-3">
          <h4 class="text-lg font-medium">${this.escapeHtml(alert.title)}</h4>
          <span class="alert-tag ${severity.color}">${severity.text}级</span>
          <span class="alert-tag ${status.color}">${status.text}</span>
        </div>
        
        ${trafficInfo ? this.renderTrafficInfoCard(trafficInfo) : ''}
        
        <div class="alert-detail-grid">
          <div class="alert-detail-field">
            <label class="alert-detail-label">告警类型</label>
            <p class="alert-detail-value">${this.getAlertTypeText(alert.alert_type)}</p>
          </div>
          ${alert.source_ip ? `
            <div class="alert-detail-field">
              <label class="alert-detail-label">来源地址</label>
              <p class="alert-detail-value">${alert.source_ip}</p>
            </div>
          ` : ''}
          ${alert.dest_ip ? `
            <div class="alert-detail-field">
              <label class="alert-detail-label">目标地址</label>
              <p class="alert-detail-value">${alert.dest_ip}</p>
            </div>
          ` : ''}
          <div class="alert-detail-field">
            <label class="alert-detail-label">创建时间</label>
            <p class="alert-detail-value">${alert.created_at}</p>
          </div>
          ${alert.resolved_at ? `
            <div class="alert-detail-field">
              <label class="alert-detail-label">解决时间</label>
              <p class="alert-detail-value">${alert.resolved_at}</p>
            </div>
          ` : ''}
        </div>
        
        ${!trafficInfo ? `
          <div>
            <label class="alert-detail-label">详细描述</label>
            <div class="alert-description-box">${this.escapeHtml(alert.message)}</div>
          </div>
        ` : ''}
        
        <div>
          <label class="alert-detail-label">建议处理方案</label>
          <div class="alert-suggestions-box">
            <ul class="alert-suggestions-list">
              ${trafficInfo ? `
                <li>立即检查该流量的详细特征和行为模式</li>
                <li>分析请求内容是否包含恶意代码或攻击载荷</li>
                <li>检查源IP是否为已知恶意地址</li>
                <li>考虑添加防护规则阻止类似攻击</li>
              ` : `
                <li>检查相关系统组件运行状态</li>
                <li>查看详细日志信息确定根本原因</li>
                <li>根据告警类型执行相应的修复操作</li>
              `}
              <li>验证问题是否已解决并更新告警状态</li>
            </ul>
          </div>
        </div>
      </div>
    `;
    
    // 设置按钮事件
    this.elements.markProcessingBtn.onclick = () => this.updateStatus(alertId, 'processing');
    this.elements.markResolvedBtn.onclick = () => this.updateStatus(alertId, 'resolved');
    
    // 根据状态显示/隐藏按钮
    if (alert.status === 'resolved') {
      this.elements.markProcessingBtn.style.display = 'none';
      this.elements.markResolvedBtn.style.display = 'none';
    } else {
      this.elements.markProcessingBtn.style.display = alert.status === 'processing' ? 'none' : 'block';
      this.elements.markResolvedBtn.style.display = 'block';
    }
    
    this.openModal();
  }

  parseTrafficInfo(message) {
    // 解析流量信息的正则表达式
    const patterns = {
      sourceIp: /源IP[：:]\s*([^\s•]+)/,
      destIp: /目标IP[：:]\s*([^\s•]+)/,
      trafficType: /流量类型[：:]\s*([^\s•]+)/,
      aiPrediction: /AI预测结果[：:]\s*([^\s•]+)/,
      requestContent: /请求内容[：:]\s*([^\n]+)/
    };
    
    const info = {};
    let hasTrafficInfo = false;
    
    for (const [key, pattern] of Object.entries(patterns)) {
      const match = message.match(pattern);
      if (match) {
        info[key] = match[1].trim();
        hasTrafficInfo = true;
      }
    }
    
    return hasTrafficInfo ? info : null;
  }

  renderTrafficInfoCard(trafficInfo) {
    const getPredictionColor = (prediction) => {
      if (prediction && prediction.includes('可疑')) return 'warning';
      if (prediction && prediction.includes('恶意')) return 'danger';
      if (prediction && prediction.includes('正常')) return 'success';
      return 'primary';
    };
    
    const predictionColor = getPredictionColor(trafficInfo.aiPrediction);
    
    return `
      <div class="traffic-info-card">
        <div class="traffic-info-header">
          <i class="fa fa-shield text-warning"></i>
          <h5 class="font-medium">流量详细信息</h5>
        </div>
        
        <div class="traffic-info-grid">
          ${trafficInfo.sourceIp ? `
            <div class="traffic-info-item">
              <div class="traffic-info-icon">
                <i class="fa fa-arrow-right text-primary"></i>
              </div>
              <div>
                <label class="traffic-info-label">源IP地址</label>
                <p class="traffic-info-value">${this.escapeHtml(trafficInfo.sourceIp)}</p>
              </div>
            </div>
          ` : ''}
          
          ${trafficInfo.destIp ? `
            <div class="traffic-info-item">
              <div class="traffic-info-icon">
                <i class="fa fa-bullseye text-success"></i>
              </div>
              <div>
                <label class="traffic-info-label">目标IP地址</label>
                <p class="traffic-info-value">${this.escapeHtml(trafficInfo.destIp)}</p>
              </div>
            </div>
          ` : ''}
          
          ${trafficInfo.trafficType ? `
            <div class="traffic-info-item">
              <div class="traffic-info-icon">
                <i class="fa fa-exchange text-info"></i>
              </div>
              <div>
                <label class="traffic-info-label">流量类型</label>
                <p class="traffic-info-value">${this.escapeHtml(trafficInfo.trafficType)}</p>
              </div>
            </div>
          ` : ''}
          
          ${trafficInfo.aiPrediction ? `
            <div class="traffic-info-item">
              <div class="traffic-info-icon">
                <i class="fa fa-brain text-${predictionColor}"></i>
              </div>
              <div>
                <label class="traffic-info-label">AI预测结果</label>
                <p class="traffic-info-value">
                  <span class="alert-tag ${predictionColor}">${this.escapeHtml(trafficInfo.aiPrediction)}</span>
                </p>
              </div>
            </div>
          ` : ''}
        </div>
        
        ${trafficInfo.requestContent ? `
          <div class="traffic-request-content">
            <label class="traffic-info-label">
              <i class="fa fa-code text-danger mr-1"></i>
              请求内容分析
            </label>
            <div class="traffic-request-box">
              <code class="traffic-request-code">${this.escapeHtml(trafficInfo.requestContent)}</code>
              ${this.analyzeRequestContent(trafficInfo.requestContent)}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  analyzeRequestContent(content) {
    const threats = [];
    
    // 检测常见攻击模式
    if (content.includes('<script>')) threats.push('XSS脚本注入');
    if (content.includes('alert(')) threats.push('JavaScript执行');
    if (content.includes('SELECT') && content.includes('FROM')) threats.push('SQL注入');
    if (content.includes('../')) threats.push('路径遍历');
    if (content.includes('eval(')) threats.push('代码执行');
    
    if (threats.length === 0) return '';
    
    return `
      <div class="threat-analysis">
        <p class="threat-analysis-title">
          <i class="fa fa-exclamation-triangle text-danger"></i>
          检测到威胁特征:
        </p>
        <div class="threat-tags">
          ${threats.map(threat => `<span class="alert-tag danger">${threat}</span>`).join('')}
        </div>
      </div>
    `;
  }

  async updateStatus(alertId, newStatus) {
    try {
      const response = await fetch(`/api/alerts/update/${alertId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus })
      });
      
      const data = await response.json();
      
      if (data.success) {
        this.showToast(data.message, 'success');
        this.closeModal();
        this.loadAlerts(); // 重新加载数据
      } else {
        this.showToast('更新失败: ' + data.message, 'error');
      }
    } catch (error) {
      console.error('更新告警状态失败:', error);
      this.showToast('网络错误，更新失败', 'error');
    }
  }

  openModal() {
    this.elements.alertModal.classList.remove('hidden');
    setTimeout(() => {
      this.elements.alertModalContent.classList.add('show');
    }, 50);
  }

  closeModal() {
    this.elements.alertModalContent.classList.remove('show');
    setTimeout(() => {
      this.elements.alertModal.classList.add('hidden');
    }, 200);
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  showToast(message, type = 'info') {
    // 如果存在全局toast函数，使用它
    if (typeof showToast === 'function') {
      showToast(message, type);
    } else {
      // 简单的alert替代
      alert(message);
    }
  }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
  window.alertsManager = new AlertsManager();
});