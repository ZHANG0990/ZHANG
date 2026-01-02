/**
 * 白流量规则管理 JavaScript
 */

class WhiteRulesManager {
    constructor() {
        this.rules = [];
        this.filteredRules = [];
        this.currentEditId = null;
        
        this.initElements();
        this.bindEvents();
        this.loadRulesData();
    }
    
    initElements() {
        // 模态框相关元素
        this.modal = document.getElementById('rule-modal');
        this.modalContent = document.getElementById('modal-content');
        this.modalTitle = document.getElementById('modal-title');
        this.addRuleBtn = document.getElementById('add-rule-btn');
        this.closeModalBtn = document.getElementById('close-modal');
        this.cancelRuleBtn = document.getElementById('cancel-rule');
        this.modalBackdrop = document.getElementById('modal-backdrop');
        
        // 表单相关元素
        this.ruleForm = document.getElementById('rule-form');
        this.ruleNameInput = document.getElementById('rule-name');
        this.ruleTypeSelect = document.getElementById('rule-type');
        this.ruleConditionInput = document.getElementById('rule-condition');
        this.ruleEnableCheckbox = document.getElementById('rule-enable');
        
        // 搜索和筛选元素
        this.searchInput = document.getElementById('search-rules');
        this.filterSelect = document.getElementById('filter-status');
        
        // 统计元素
        this.totalRulesEl = document.getElementById('total-rules');
        this.activeRulesEl = document.getElementById('active-rules');
        this.disabledRulesEl = document.getElementById('disabled-rules');
        
        // 规则容器
        this.rulesContainer = document.getElementById('rules-container');
        this.emptyState = document.getElementById('empty-rules-state');
        
        // 条件按钮
        this.conditionBtns = document.querySelectorAll('.condition-btn');
    }
    
    bindEvents() {
        // 模态框事件
        this.addRuleBtn?.addEventListener('click', () => this.openModal());
        this.closeModalBtn?.addEventListener('click', () => this.closeModal());
        this.cancelRuleBtn?.addEventListener('click', () => this.closeModal());
        this.modalBackdrop?.addEventListener('click', () => this.closeModal());
        
        // 表单提交
        this.ruleForm?.addEventListener('submit', (e) => this.handleFormSubmit(e));
        
        // 搜索和筛选
        this.searchInput?.addEventListener('input', () => this.filterRules());
        this.filterSelect?.addEventListener('change', () => this.filterRules());
        
        // 条件按钮切换
        this.conditionBtns.forEach(btn => {
            btn.addEventListener('click', () => this.handleConditionBtnClick(btn));
        });
        
        // 键盘事件
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.modal.classList.contains('hidden')) {
                this.closeModal();
            }
        });
    }
    
    loadRulesData() {
        try {
            const rulesDataScript = document.getElementById('rules-data');
            if (rulesDataScript) {
                const backendRules = JSON.parse(rulesDataScript.textContent);
                this.rules = backendRules.map(rule => ({
                    id: rule.id,
                    name: rule.name,
                    type: rule.rule_type,
                    condition: rule.rule_value,
                    enabled: rule.is_active,
                    createTime: rule.created_at,
                    description: rule.description || '',
                    creatorName: rule.creator_name || '未知用户',
                    isOwnRule: rule.is_own_rule || false
                }));
            }
            
            this.updateStats();
            this.renderRules();
        } catch (error) {
            console.error('加载规则数据失败:', error);
            this.showToast('加载规则数据失败', 'error');
        }
    }
    
    updateStats() {
        const total = this.rules.length;
        const active = this.rules.filter(r => r.enabled).length;
        const disabled = total - active;
        
        if (this.totalRulesEl) this.totalRulesEl.textContent = total;
        if (this.activeRulesEl) this.activeRulesEl.textContent = active;
        if (this.disabledRulesEl) this.disabledRulesEl.textContent = disabled;
    }
    
    renderRules(rulesToRender = this.rules) {
        if (!this.rulesContainer) return;
        
        if (rulesToRender.length === 0) {
            this.showEmptyState();
            return;
        }
        
        this.hideEmptyState();
        
        const rulesHtml = rulesToRender.map(rule => this.createRuleHtml(rule)).join('');
        this.rulesContainer.innerHTML = rulesHtml;
        
        // 绑定规则操作事件
        this.bindRuleEvents();
    }
    
    createRuleHtml(rule) {
        const typeLabels = {
            'ip': 'IP地址',
            'domain': '域名',
            'port': '端口',
            'protocol': '协议'
        };
        
        // 根据权限生成操作按钮
        const actionButtons = rule.isOwnRule ? `
            <button class="rule-action-btn edit" data-action="edit" data-rule-id="${rule.id}">
                <i class="fa fa-edit"></i> 编辑
            </button>
            <button class="rule-action-btn toggle ${rule.enabled ? '' : 'enable'}" data-action="toggle" data-rule-id="${rule.id}">
                <i class="fa fa-${rule.enabled ? 'pause' : 'play'}"></i> ${rule.enabled ? '停用' : '启用'}
            </button>
            <button class="rule-action-btn delete" data-action="delete" data-rule-id="${rule.id}">
                <i class="fa fa-trash"></i> 删除
            </button>
        ` : `
            <span class="rule-no-permission">
                <i class="fa fa-lock"></i> 无权限操作
            </span>
        `;
        
        return `
            <div class="rule-item ${rule.isOwnRule ? '' : 'readonly'}" data-rule-id="${rule.id}">
                <div class="rule-header">
                    <div class="rule-info">
                        <div class="rule-title">
                            <h4 class="rule-name">${this.escapeHtml(rule.name)}</h4>
                            <span class="rule-tag ${rule.enabled ? 'enabled' : 'disabled'}">
                                ${rule.enabled ? '启用中' : '已停用'}
                            </span>
                            <span class="rule-tag type">${typeLabels[rule.type] || rule.type}</span>
                            <span class="rule-tag creator">创建者: ${this.escapeHtml(rule.creatorName)}</span>
                        </div>
                        <p class="rule-condition">匹配条件: ${this.escapeHtml(rule.condition)}</p>
                        <p class="rule-time">创建时间: ${rule.createTime}</p>
                    </div>
                    <div class="rule-actions">
                        ${actionButtons}
                    </div>
                </div>
            </div>
        `;
    }
    
    bindRuleEvents() {
        const actionBtns = this.rulesContainer.querySelectorAll('.rule-action-btn');
        actionBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const action = btn.dataset.action;
                const ruleId = parseInt(btn.dataset.ruleId);
                
                switch (action) {
                    case 'edit':
                        this.editRule(ruleId);
                        break;
                    case 'toggle':
                        this.toggleRule(ruleId);
                        break;
                    case 'delete':
                        this.deleteRule(ruleId);
                        break;
                }
            });
        });
    }
    
    showEmptyState() {
        if (this.emptyState) {
            this.emptyState.classList.remove('hidden');
            this.rulesContainer.innerHTML = '';
            this.rulesContainer.appendChild(this.emptyState);
        }
    }
    
    hideEmptyState() {
        if (this.emptyState) {
            this.emptyState.classList.add('hidden');
        }
    }
    
    filterRules() {
        const searchTerm = this.searchInput?.value.toLowerCase() || '';
        const statusFilter = this.filterSelect?.value || '';
        
        let filtered = this.rules;
        
        if (searchTerm) {
            filtered = filtered.filter(rule => 
                rule.name.toLowerCase().includes(searchTerm) ||
                rule.condition.toLowerCase().includes(searchTerm)
            );
        }
        
        if (statusFilter) {
            filtered = filtered.filter(rule => 
                statusFilter === 'enabled' ? rule.enabled : !rule.enabled
            );
        }
        
        this.filteredRules = filtered;
        this.renderRules(filtered);
    }
    
    openModal(isEdit = false, ruleId = null) {
        if (!this.modal) return;
        
        this.modal.classList.remove('hidden');
        setTimeout(() => {
            if (this.modalContent) {
                this.modalContent.classList.remove('scale-95', 'opacity-0');
                this.modalContent.classList.add('scale-100', 'opacity-100');
            }
        }, 50);
        
        if (isEdit && ruleId) {
            this.currentEditId = ruleId;
            const rule = this.rules.find(r => r.id === ruleId);
            if (rule) {
                if (this.modalTitle) this.modalTitle.textContent = '编辑规则';
                if (this.ruleNameInput) this.ruleNameInput.value = rule.name;
                if (this.ruleTypeSelect) this.ruleTypeSelect.value = rule.type;
                if (this.ruleConditionInput) this.ruleConditionInput.value = rule.condition;
                if (this.ruleEnableCheckbox) this.ruleEnableCheckbox.checked = rule.enabled;
                
                // 更新条件按钮状态
                this.updateConditionButtons(rule.type);
            }
        } else {
            this.currentEditId = null;
            if (this.modalTitle) this.modalTitle.textContent = '新增白流量规则';
            if (this.ruleForm) this.ruleForm.reset();
            if (this.ruleEnableCheckbox) this.ruleEnableCheckbox.checked = true;
            
            // 默认选择IP类型
            this.updateConditionButtons('ip');
        }
        
        // 聚焦到名称输入框
        setTimeout(() => {
            if (this.ruleNameInput) this.ruleNameInput.focus();
        }, 100);
    }
    
    closeModal() {
        if (!this.modal || !this.modalContent) return;
        
        this.modalContent.classList.remove('scale-100', 'opacity-100');
        this.modalContent.classList.add('scale-95', 'opacity-0');
        
        setTimeout(() => {
            this.modal.classList.add('hidden');
            this.currentEditId = null;
        }, 200);
    }
    
    handleConditionBtnClick(btn) {
        const type = btn.dataset.type;
        this.updateConditionButtons(type);
        
        if (this.ruleTypeSelect) {
            this.ruleTypeSelect.value = type;
        }
        
        if (this.ruleConditionInput) {
            const placeholders = {
                'ip': '例如: 192.168.1.0/24 或 10.0.0.1',
                'domain': '例如: *.example.com 或 api.example.com',
                'port': '例如: 80 或 443-8080',
                'protocol': '例如: TCP 或 UDP'
            };
            this.ruleConditionInput.placeholder = placeholders[type] || '';
        }
    }
    
    updateConditionButtons(activeType) {
        this.conditionBtns.forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.type === activeType) {
                btn.classList.add('active');
            }
        });
    }
    
    async handleFormSubmit(e) {
        e.preventDefault();
        
        if (!this.ruleForm) return;
        
        const formData = new FormData();
        formData.append('name', this.ruleNameInput?.value || '');
        formData.append('rule_type', this.ruleTypeSelect?.value || '');
        formData.append('rule_value', this.ruleConditionInput?.value || '');
        formData.append('description', '');
        
        const url = this.currentEditId ? 
            `/white-rules/edit/${this.currentEditId}` : 
            '/white-rules/add';
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast(data.message);
                this.closeModal();
                // 重新加载页面以获取最新数据
                window.location.reload();
            } else {
                this.showToast(data.message, 'error');
            }
        } catch (error) {
            console.error('提交表单失败:', error);
            this.showToast('操作失败，请重试', 'error');
        }
    }
    
    editRule(ruleId) {
        this.openModal(true, ruleId);
    }
    
    async toggleRule(ruleId) {
        try {
            const response = await fetch(`/white-rules/toggle/${ruleId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 更新本地数据
                const rule = this.rules.find(r => r.id === ruleId);
                if (rule) {
                    rule.enabled = data.is_active;
                    this.updateStats();
                    this.renderRules(this.filteredRules.length > 0 ? this.filteredRules : this.rules);
                    this.showToast(`规则已${rule.enabled ? '启用' : '停用'}`);
                }
            } else {
                this.showToast(data.message, 'error');
            }
        } catch (error) {
            console.error('切换规则状态失败:', error);
            this.showToast('操作失败，请重试', 'error');
        }
    }
    
    async deleteRule(ruleId) {
        const rule = this.rules.find(r => r.id === ruleId);
        if (!rule) return;
        
        if (!confirm(`确定要删除规则"${rule.name}"吗？`)) {
            return;
        }
        
        try {
            const response = await fetch(`/white-rules/delete/${ruleId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 从本地数据中移除
                this.rules = this.rules.filter(r => r.id !== ruleId);
                this.updateStats();
                this.filterRules(); // 重新筛选和渲染
                this.showToast('规则删除成功');
            } else {
                this.showToast(data.message, 'error');
            }
        } catch (error) {
            console.error('删除规则失败:', error);
            this.showToast('删除失败，请重试', 'error');
        }
    }
    
    showToast(message, type = 'success') {
        // 移除现有的toast
        const existingToasts = document.querySelectorAll('.toast');
        existingToasts.forEach(toast => toast.remove());
        
        // 创建新的toast
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // 显示动画
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // 3秒后自动移除
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    new WhiteRulesManager();
});