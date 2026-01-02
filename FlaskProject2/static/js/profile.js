document.addEventListener('DOMContentLoaded', function() {
  const profileForm = document.getElementById('profileForm');
  const editBtn = document.getElementById('editProfileBtn');
  const cancelBtn = document.getElementById('cancelBtn');
  const uploadAvatarBtn = document.getElementById('uploadAvatarBtn');
  const avatarInput = document.getElementById('avatarInput');
  
  // 修改密码相关元素
  
  let isEditing = false;
  let originalData = {};
  
  // 保存原始数据
  function saveOriginalData() {
    const inputs = profileForm.querySelectorAll('input[name]');
    inputs.forEach(input => {
      originalData[input.name] = input.value;
    });
  }
  
  // 恢复原始数据
  function restoreOriginalData() {
    const inputs = profileForm.querySelectorAll('input[name]');
    inputs.forEach(input => {
      input.value = originalData[input.name] || '';
    });
  }
  
  // 切换编辑模式
  function toggleEditMode() {
    isEditing = !isEditing;
    const inputs = profileForm.querySelectorAll('input[name]');
    
    inputs.forEach(input => {
      input.disabled = !isEditing;
    });
    
    if (isEditing) {
      saveOriginalData();
      editBtn.innerHTML = '<i class="fa fa-times"></i> 取消编辑';
      editBtn.classList.remove('btn-outline');
      editBtn.classList.add('btn-danger');
    } else {
      restoreOriginalData();
      editBtn.innerHTML = '<i class="fa fa-edit"></i> 编辑信息';
      editBtn.classList.remove('btn-danger');
      editBtn.classList.add('btn-outline');
    }
  }
  
  // 编辑按钮点击
  editBtn.addEventListener('click', toggleEditMode);
  
  // 取消按钮点击
  cancelBtn.addEventListener('click', function() {
    if (isEditing) {
      toggleEditMode();
    }
  });
  
  // 头像上传按钮点击
  uploadAvatarBtn.addEventListener('click', function() {
    avatarInput.click();
  });
  
  // 头像文件选择
  avatarInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        showToast('头像文件大小不能超过5MB', 'error');
        return;
      }
      
      // 检查文件类型
      const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
      if (!allowedTypes.includes(file.type)) {
        showToast('请上传 JPG、PNG 或 GIF 格式的图片', 'error');
        return;
      }
      
      // 显示上传中状态
      const avatarContainer = document.getElementById('avatarContainer');
      const originalContent = avatarContainer.innerHTML;
      avatarContainer.innerHTML = '<i class="fa fa-spinner fa-spin text-2xl text-primary"></i>';
      
      // 创建FormData并上传
      const formData = new FormData();
      formData.append('avatar', file);
      
      fetch('/profile/avatar', {
        method: 'POST',
        body: formData
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          // 更新头像显示
          avatarContainer.innerHTML = '<img src="' + data.avatar_url + '" alt="头像" class="w-full h-full object-cover">';
          showToast(data.message, 'success');
        } else {
          // 恢复原始内容
          avatarContainer.innerHTML = originalContent;
          showToast(data.message, 'error');
        }
      })
      .catch(error => {
        // 恢复原始内容
        avatarContainer.innerHTML = originalContent;
        showToast('头像上传失败，请重试', 'error');
        console.error('Upload error:', error);
      });
    }
  });
  
  // 表单提交
  profileForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    // 如果不在编辑模式，自动进入编辑模式
    if (!isEditing) {
      isEditing = true;
    }
    
    // 显示保存中状态
    const submitBtn = profileForm.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> 保存中...';
    submitBtn.disabled = true;
    
    const formData = new FormData(profileForm);
    
    // 添加调试信息
    console.log('提交的表单数据:');
    for (let [key, value] of formData.entries()) {
      console.log(key, value);
    }
    
    fetch('/profile/update', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      // 检查响应状态
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 检查响应内容类型
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        return response.text().then(text => {
          console.error('非JSON响应:', text);
          throw new Error('服务器返回了非JSON响应');
        });
      }
      
      return response.json();
    })
    .then(data => {
      console.log('服务器响应:', data);
      
      if (data.success) {
        showToast(data.message, 'success');
        toggleEditMode();
        
        // 更新显示的数据
        if (data.data) {
          Object.keys(data.data).forEach(key => {
            const input = profileForm.querySelector(`input[name="${key}"]`);
            if (input && data.data[key] !== null) {
              input.value = data.data[key];
            }
          });
        }
      } else {
        showToast(data.message, 'error');
      }
    })
    .catch(error => {
      showToast('个人信息保存失败', 'error');
      console.error('Save error:', error);
    })
    .finally(() => {
      // 恢复按钮状态
      submitBtn.innerHTML = originalBtnText;
      submitBtn.disabled = false;
    });
  });
  
  // 修改密码按钮点击
  changePasswordBtn.addEventListener('click', function() {
    console.log('修改密码按钮被点击');
    changePasswordModal.classList.remove('hidden');
    changePasswordModal.classList.add('flex');
    // 清空表单
    changePasswordForm.reset();
  });
  
  // 关闭密码修改模态框
  function closePasswordModalFunc() {
    changePasswordModal.classList.add('hidden');
    changePasswordModal.classList.remove('flex');
    changePasswordForm.reset();
  }
  
  closePasswordModal.addEventListener('click', closePasswordModalFunc);
  cancelPasswordBtn.addEventListener('click', closePasswordModalFunc);
  
  // 点击模态框背景关闭
  changePasswordModal.addEventListener('click', function(e) {
    if (e.target === changePasswordModal) {
      closePasswordModalFunc();
    }
  });
  
  // 修改密码表单提交
  changePasswordForm.addEventListener('submit', function(e) {
    e.preventDefault();
    
    const currentPassword = changePasswordForm.querySelector('input[name="current_password"]').value;
    const newPassword = changePasswordForm.querySelector('input[name="new_password"]').value;
    const confirmPassword = changePasswordForm.querySelector('input[name="confirm_password"]').value;
    
    console.log('提交密码修改表单');
    
    // 前端验证
    if (!currentPassword || !newPassword || !confirmPassword) {
      showToast('请填写所有密码字段', 'error');
      return;
    }
    
    if (newPassword.length < 6) {
      showToast('新密码长度不能少于6位', 'error');
      return;
    }
    
    if (newPassword !== confirmPassword) {
      showToast('两次输入的新密码不一致', 'error');
      return;
    }
    
    if (currentPassword === newPassword) {
      showToast('新密码不能与当前密码相同', 'error');
      return;
    }
    
    // 显示提交中状态
    const submitBtn = changePasswordForm.querySelector('button[type="submit"]');
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> 修改中...';
    submitBtn.disabled = true;
    
    const formData = new FormData(changePasswordForm);
    
    fetch('/profile/change-password', {
      method: 'POST',
      body: formData
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        return response.text().then(text => {
          console.error('非JSON响应:', text);
          throw new Error('服务器返回了非JSON响应');
        });
      }
      
      return response.json();
    })
    .then(data => {
      console.log('密码修改响应:', data);
      
      if (data.success) {
        showToast(data.message, 'success');
        closePasswordModalFunc();
      } else {
        showToast(data.message, 'error');
      }
    })
    .catch(error => {
      showToast('密码修改失败，请重试', 'error');
      console.error('Change password error:', error);
    })
    .finally(() => {
      // 恢复按钮状态
      submitBtn.innerHTML = originalBtnText;
      submitBtn.disabled = false;
    });
  });
  
  // Toast 消息显示函数
  function showToast(message, type = 'info') {
    // 创建toast元素
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 px-4 py-2 rounded-lg text-white z-50 ${
      type === 'success' ? 'bg-green-500' : 
      type === 'error' ? 'bg-red-500' : 
      'bg-blue-500'
    }`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // 3秒后自动移除
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 3000);
  }
});