// 主要JavaScript功能
document.addEventListener('DOMContentLoaded', function() {
  // 初始化组件
  initSidebar();
  initToast();
  initCharts();
  initTimeFilters();
  initTrafficTypeDetail();
  
  // 侧边栏控制
  function initSidebar() {
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
      sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('-translate-x-full');
      });
      
      // 点击外部关闭侧边栏（移动端）
      document.addEventListener('click', function(e) {
        if (window.innerWidth < 1024 && 
            !sidebar.contains(e.target) && 
            !sidebarToggle.contains(e.target) &&
            !sidebar.classList.contains('-translate-x-full')) {
          sidebar.classList.add('-translate-x-full');
        }
      });
    }
  }
  
  // 提示消息系统
  function initToast() {
    window.showToast = function(message, type = 'success') {
      const toast = document.getElementById('toast');
      const toastMessage = document.getElementById('toast-message');
      
      if (toast && toastMessage) {
        toastMessage.textContent = message;
        
        // 重置样式
        toast.className = 'toast text-white';
        
        // 设置类型样式
        switch(type) {
          case 'success':
            toast.classList.add('bg-success');
            break;
          case 'error':
          case 'danger':
            toast.classList.add('bg-danger');
            break;
          case 'warning':
            toast.classList.add('bg-warning');
            break;
          case 'info':
            toast.classList.add('bg-primary');
            break;
          default:
            toast.classList.add('bg-success');
        }
        
        // 显示提示
        toast.classList.add('show');
        
        // 3秒后隐藏
        setTimeout(() => {
          toast.classList.remove('show');
        }, 3000);
      }
    };
  }
  
  // 图表初始化
  function initCharts() {
    // 仪表盘流量趋势图
    const trafficTrendCtx = document.getElementById('traffic-trend-chart');
    if (trafficTrendCtx) {
      // 销毁现有图表
      const existingChart = Chart.getChart(trafficTrendCtx);
      if (existingChart) {
        existingChart.destroy();
      }
      
      // 从API获取真实数据
      fetch('/api/traffic-trend')
        .then(response => response.json())
        .then(data => {
          new Chart(trafficTrendCtx, {
            type: 'line',
            data: {
              labels: data.labels,
              datasets: [
                {
                  label: '总流量',
                  data: data.total_traffic,
                  borderColor: '#165DFF',
                  backgroundColor: 'rgba(22, 93, 255, 0.1)',
                  tension: 0.4,
                  fill: true
                },
                {
                  label: '白流量',
                  data: data.white_traffic,
                  borderColor: '#00B42A',
                  backgroundColor: 'rgba(0, 180, 42, 0.1)',
                  tension: 0.4,
                  fill: true
                }
              ]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'top',
                }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  title: {
                    display: true,
                    text: '流量数量'
                  }
                }
              }
            }
          });
        })
        .catch(error => {
          console.error('获取流量趋势数据失败:', error);
          // 销毁现有图表（如果存在）
          const existingErrorChart = Chart.getChart(trafficTrendCtx);
          if (existingErrorChart) {
            existingErrorChart.destroy();
          }
          // 使用默认数据（折线图）
          new Chart(trafficTrendCtx, {
            type: 'line',
            data: {
              labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
              datasets: [
                {
                  label: '总流量',
                  data: [0, 0, 0, 0, 0, 0],
                  borderColor: '#165DFF',
                  backgroundColor: 'rgba(22, 93, 255, 0.1)',
                  tension: 0.4,
                  fill: true
                },
                {
                  label: '白流量',
                  data: [0, 0, 0, 0, 0, 0],
                  borderColor: '#00B42A',
                  backgroundColor: 'rgba(0, 180, 42, 0.1)',
                  tension: 0.4,
                  fill: true
                }
              ]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'top',
                }
              },
              scales: {
                y: {
                  beginAtZero: true,
                  title: {
                    display: true,
                    text: '流量数量'
                  }
                }
              }
            }
          });
        });
    }
    
    // 流量类型分布图
    const trafficTypeCtx = document.getElementById('traffic-type-chart');
    if (trafficTypeCtx) {
      // 销毁现有图表
      const existingTypeChart = Chart.getChart(trafficTypeCtx);
      if (existingTypeChart) {
        existingTypeChart.destroy();
      }
      
      fetch('/api/traffic-types')
        .then(response => response.json())
        .then(data => {
          // 再次确认销毁现有图表
          const existingChart = Chart.getChart(trafficTypeCtx);
          if (existingChart) {
            existingChart.destroy();
          }
          
          new Chart(trafficTypeCtx, {
            type: 'doughnut',
            data: {
              labels: data.labels,
              datasets: [{
                data: data.data,
                backgroundColor: [
                  '#165DFF',
                  '#0FC6C2',
                  '#00B42A',
                  '#4E5969'
                ],
                borderWidth: 0
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'bottom'
                }
              },
              cutout: '70%'
            }
          });
        })
        .catch(error => {
          console.error('获取流量类型数据失败:', error);
          // 销毁现有图表（如果存在）
          const existingErrorChart = Chart.getChart(trafficTypeCtx);
          if (existingErrorChart) {
            existingErrorChart.destroy();
          }
          // 使用默认数据
          new Chart(trafficTypeCtx, {
            type: 'doughnut',
            data: {
              labels: ['HTTP', '视频流', 'DNS', '其他'],
              datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                  '#165DFF',
                  '#0FC6C2',
                  '#00B42A',
                  '#4E5969'
                ],
                borderWidth: 0
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: 'bottom'
                }
              },
              cutout: '70%'
            }
          });
        });
    }
    
    // 实时流量监控图
    const realtimeTrafficCtx = document.getElementById('realtime-traffic-chart');
    if (realtimeTrafficCtx) {
      let realtimeChart;
      
      function initRealtimeChart() {
        fetch('/api/realtime-traffic')
          .then(response => response.json())
          .then(data => {
            realtimeChart = new Chart(realtimeTrafficCtx, {
              type: 'line',
              data: {
                labels: data.labels,
                datasets: [
                  {
                    label: '总流量',
                    data: data.total,
                    borderColor: '#165DFF',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false
                  },
                  {
                    label: '白流量',
                    data: data.white,
                    borderColor: '#00B42A',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false
                  },
                  {
                    label: '可疑流量',
                    data: data.suspicious,
                    borderColor: '#FF7D00',
                    borderWidth: 2,
                    pointRadius: 0,
                    tension: 0.4,
                    fill: false
                  }
                ]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    display: false
                  }
                },
                scales: {
                  y: {
                    beginAtZero: true,
                    title: {
                      display: true,
                      text: '流量数量'
                    }
                  }
                }
              }
            });
          })
          .catch(error => {
            console.error('获取实时流量数据失败:', error);
          });
      }
      
      initRealtimeChart();
      
      // 实时更新数据（每30秒更新一次）
      if (window.location.pathname.includes('traffic-monitor')) {
        setInterval(() => {
          updateRealtimeChart();
        }, 30000);
      }
    }
  }
  
  // 更新实时图表数据
  function updateRealtimeChart() {
    fetch('/api/realtime-traffic')
      .then(response => response.json())
      .then(data => {
        const chart = Chart.getChart('realtime-traffic-chart');
        if (chart) {
          chart.data.labels = data.labels;
          chart.data.datasets[0].data = data.total;
          chart.data.datasets[1].data = data.white;
          chart.data.datasets[2].data = data.suspicious;
          chart.update('none');
        }
      })
      .catch(error => {
        console.error('更新实时流量数据失败:', error);
      });
  }
  
  // 表单验证
  window.validateForm = function(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const inputs = form.querySelectorAll('input[required], select[required]');
    let isValid = true;
    
    inputs.forEach(input => {
      if (!input.value.trim()) {
        input.classList.add('border-danger');
        isValid = false;
      } else {
        input.classList.remove('border-danger');
        input.classList.add('border-success');
      }
    });
    
    return isValid;
  };
  
  // 加载状态管理
  window.setLoading = function(element, loading = true) {
    if (typeof element === 'string') {
      element = document.getElementById(element);
    }
    
    if (element) {
      if (loading) {
        element.classList.add('loading');
        element.disabled = true;
      } else {
        element.classList.remove('loading');
        element.disabled = false;
      }
    }
  };
  
  // 确认对话框
  window.confirmAction = function(message, callback) {
    if (confirm(message)) {
      callback();
    }
  };
  
  // 格式化文件大小
  window.formatFileSize = function(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  // 格式化时间
  window.formatTime = function(date) {
    if (typeof date === 'string') {
      date = new Date(date);
    }
    return date.toLocaleString('zh-CN');
  };
  
  // 防抖函数
  window.debounce = function(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  };
  
  // 搜索表格功能
  window.searchTable = function(inputId, tableId) {
    const searchInput = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    
    if (searchInput && table) {
      searchInput.addEventListener('input', debounce(function() {
        const searchTerm = this.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          if (text.includes(searchTerm)) {
            row.style.display = '';
          } else {
            row.style.display = 'none';
          }
        });
      }, 300));
    }
  };
  
  // 表格排序功能
  window.sortTable = function(tableId, columnIndex, type = 'text') {
    const table = document.getElementById(tableId);
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
      const aText = a.cells[columnIndex].textContent.trim();
      const bText = b.cells[columnIndex].textContent.trim();
      
      if (type === 'date') {
        return new Date(aText) - new Date(bText);
      } else if (type === 'number') {
        return parseFloat(aText) - parseFloat(bText);
      } else {
        return aText.localeCompare(bText);
      }
    });
    
    rows.forEach(row => tbody.appendChild(row));
  };
  
  // 复制到剪贴板
  window.copyToClipboard = function(text) {
    navigator.clipboard.writeText(text).then(() => {
      showToast('已复制到剪贴板');
    }).catch(() => {
      showToast('复制失败', 'error');
    });
  };

  // 时间过滤器初始化
  function initTimeFilters() {
    const timeFilterBtns = document.querySelectorAll('.time-filter-btn');
    
    timeFilterBtns.forEach(btn => {
      btn.addEventListener('click', function() {
        const period = this.dataset.period;
        
        // 更新按钮状态
        timeFilterBtns.forEach(b => {
          b.classList.remove('bg-primary/10', 'text-primary', 'active');
          b.classList.add('hover:bg-light-1');
        });
        
        this.classList.add('bg-primary/10', 'text-primary', 'active');
        this.classList.remove('hover:bg-light-1');
        
        // 更新图表数据
        updateTrafficTrendChart(period);
        
        showToast(`已切换到${this.textContent}视图`);
      });
    });
  }

  // 更新流量趋势图表
  function updateTrafficTrendChart(period) {
    const chart = Chart.getChart('traffic-trend-chart');
    if (!chart) return;
    
    // 根据时间段获取不同的API端点
    let apiUrl = '/api/traffic-trend';
    if (period === 'week') {
      apiUrl = '/api/traffic-trend?period=week';
    } else if (period === 'month') {
      apiUrl = '/api/traffic-trend?period=month';
    }
    
    // 显示加载状态
    chart.data.datasets[0].data = [];
    chart.data.datasets[1].data = [];
    chart.update();
    
    fetch(apiUrl)
      .then(response => response.json())
      .then(data => {
        chart.data.labels = data.labels;
        chart.data.datasets[0].data = data.total_traffic;
        chart.data.datasets[1].data = data.white_traffic;
        chart.update();
      })
      .catch(error => {
        console.error('更新流量趋势数据失败:', error);
        showToast('更新数据失败，请稍后重试', 'error');
      });
  }

  // 流量类型详情初始化
  function initTrafficTypeDetail() {
    const detailBtn = document.getElementById('traffic-type-detail-btn');
    if (detailBtn) {
      detailBtn.addEventListener('click', function() {
        showTrafficTypeModal();
      });
    }
  }

  // 显示流量类型详情模态框
  function showTrafficTypeModal() {
    fetch('/api/traffic-types-detail')
      .then(response => response.json())
      .then(data => {
        const modalHtml = `
          <div id="traffic-type-modal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-bold">流量类型详细分布</h3>
                <button onclick="closeTrafficTypeModal()" class="text-gray-500 hover:text-gray-700">
                  <i class="fa fa-times"></i>
                </button>
              </div>
              <div class="space-y-4">
                ${data.details.map(item => `
                  <div class="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div class="flex items-center">
                      <div class="w-4 h-4 rounded-full mr-3" style="background-color: ${item.color}"></div>
                      <span class="font-medium">${item.type}</span>
                    </div>
                    <div class="text-right">
                      <div class="font-bold">${item.count} 条</div>
                      <div class="text-sm text-gray-500">${item.percentage}%</div>
                    </div>
                  </div>
                `).join('')}
              </div>
              <div class="mt-6 pt-4 border-t">
                <div class="text-sm text-gray-600">
                  <p>总计: ${data.total} 条流量记录</p>
                  <p>更新时间: ${new Date().toLocaleString('zh-CN')}</p>
                </div>
              </div>
            </div>
          </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // 点击背景关闭模态框
        document.getElementById('traffic-type-modal').addEventListener('click', function(e) {
          if (e.target === this) {
            closeTrafficTypeModal();
          }
        });
      })
      .catch(error => {
        console.error('获取流量类型详情失败:', error);
        showToast('获取详情失败，请稍后重试', 'error');
      });
  }

  // 关闭流量类型详情模态框
  window.closeTrafficTypeModal = function() {
    const modal = document.getElementById('traffic-type-modal');
    if (modal) {
      modal.remove();
    }
  };
});
