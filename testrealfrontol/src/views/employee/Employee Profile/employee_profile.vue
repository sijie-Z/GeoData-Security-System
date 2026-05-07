<template>
  <div class="employee-profile-page page-container">
    <!-- 顶部装饰区域 -->
    <div class="profile-header-bg">
      <div class="header-content">
        <h1 class="profile-title">个人中心</h1>
        <p class="profile-subtitle">管理您的个人信息和账户设置</p>
      </div>
    </div>

    <div class="profile-main-content">
      <!-- 个人信息卡片 -->
      <el-card class="box-card profile-info-card" v-loading="loading">
        <template #header>
          <div class="card-header">
            <el-icon size="20" color="#409eff"><User /></el-icon>
            <span>基本信息</span>
          </div>
        </template>
        <div class="profile-content">
          <div class="avatar-section">
            <el-avatar :size="120" class="profile-avatar">
              <img v-if="profileData.avatarUrl" :src="profileData.avatarUrl" alt="员工头像" />
              <el-icon v-else :size="60" class="default-avatar-icon"><User /></el-icon>
            </el-avatar>
            <div class="avatar-info">
              <h3 class="user-name">{{ profileData.userName || '未设置姓名' }}</h3>
              <p class="user-number">员工编号: {{ profileData.userNumber || 'N/A' }}</p>
              <p class="user-status">
                <el-tag type="success" size="small">在职</el-tag>
              </p>
            </div>
          </div>

          <el-descriptions :column="1" border class="profile-descriptions">
            <el-descriptions-item label="邮箱">
              <strong>{{ profileData.email || profileData.userName + '@company.com' }}</strong>
            </el-descriptions-item>
            <el-descriptions-item label="联系电话">
              <strong>{{ profileData.phoneNumber || 'N/A' }}</strong>
            </el-descriptions-item>
            <el-descriptions-item label="入职日期">
              <strong>{{ profileData.hireDate || '新员工' }}</strong>
            </el-descriptions-item>
            <el-descriptions-item label="住址">
              <strong>{{ profileData.address || 'N/A' }}</strong>
            </el-descriptions-item>
          </el-descriptions>

          <div class="action-buttons">
            <el-button type="primary" @click="editProfile" size="large">
              <el-icon><Edit /></el-icon>
              编辑资料
            </el-button>
            <el-button @click="changePassword" size="large">
              <el-icon><Key /></el-icon>
              修改密码
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 统计信息卡片 -->
      <el-card class="stats-card">
        <template #header>
          <div class="card-header">
            <el-icon size="20" color="#67c23a"><DataAnalysis /></el-icon>
            <span>账户统计</span>
          </div>
        </template>
        <div class="stats-content">
          <div class="stat-item">
            <div class="stat-icon">
              <el-icon size="24" color="#409eff"><Calendar /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ profileData.hireDate ? calculateDaysSinceHire() : '0' }}</div>
              <div class="stat-label">入职天数</div>
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-icon">
              <el-icon size="24" color="#67c23a"><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ lastLoginTime || '首次登录' }}</div>
              <div class="stat-label">最近登录</div>
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-icon">
              <el-icon size="24" color="#e6a23c"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ dataCount || '0' }}</div>
              <div class="stat-label">处理数据</div>
            </div>
          </div>
        </div>
        <div class="quick-links">
          <router-link to="/employee/operation_history" class="quick-link">操作历史</router-link>
          <span class="quick-divider">|</span>
          <router-link to="/employee/notifications" class="quick-link">我的通知</router-link>
        </div>
      </el-card>
    </div>
    
    <!-- 编辑资料对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑个人资料"
      width="500px"
      :before-close="handleEditClose"
    >
      <el-form :model="editForm" label-width="80px">
        <!-- 头像上传区域 -->
        <el-form-item label="头像">
          <div class="avatar-upload-section">
            <div class="avatar-preview" @click="triggerFileInput">
              <img v-if="editForm.avatarUrl" :src="editForm.avatarUrl" alt="头像预览" class="avatar-image" />
              <div v-else class="avatar-placeholder">
                <el-icon size="32" color="#909399"><User /></el-icon>
                <span class="avatar-text">点击上传头像</span>
              </div>
              <div class="avatar-overlay">
                <el-icon color="white" size="20"><Camera /></el-icon>
                <span>更换头像</span>
              </div>
            </div>
            <input
              ref="fileInput"
              type="file"
              accept="image/*"
              style="display: none"
              @change="handleAvatarChange"
            />
            <div class="avatar-tips">
              <el-text type="info" size="small">
                支持 JPG、PNG 格式，大小不超过 2MB
              </el-text>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="姓名">
          <el-input v-model="editForm.userName" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="editForm.phoneNumber" placeholder="请输入电话号码" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="editForm.address" placeholder="请输入地址" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveProfile">保存</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="500px"
      :before-close="handlePasswordClose"
    >
      <el-form :model="passwordForm" label-width="100px">
        <el-form-item label="原密码">
          <el-input 
            v-model="passwordForm.oldPassword" 
            type="password" 
            placeholder="请输入原密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input 
            v-model="passwordForm.newPassword" 
            type="password" 
            placeholder="请输入新密码"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input 
            v-model="passwordForm.confirmPassword" 
            type="password" 
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="passwordDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="updatePassword">确认修改</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { ElMessage, ElLoading, ElMessageBox } from 'element-plus';
import { User, Camera, Edit, Key, DataAnalysis, Calendar, Clock, Document } from '@element-plus/icons-vue';
import axios from '@/utils/Axios';
import { useUserStore } from '@/stores/userStore';

const userStore = useUserStore();

// 获取当前用户编号
const userNumber = computed(() => userStore.userNumber);
const loading = ref(false);

// 存放从后端获取的员工资料数据
const profileData = ref({
  userName: '',
  userNumber: '',
  department: '',
  email: '',
  phoneNumber: '',
  hireDate: '',
  address: '',
  avatarUrl: ''
});

// 统计信息
const lastLoginTime = ref('');
const dataCount = ref(0);

// 编辑表单数据
const editForm = ref({
  userName: '',
  email: '',
  phoneNumber: '',
  address: '',
  avatar: null,
  avatarUrl: ''
});

// 对话框显示状态
const editDialogVisible = ref(false);
const passwordDialogVisible = ref(false);
const fileInput = ref(null);

// 密码表单
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

// 从后端获取用户资料
const fetchUserProfile = async () => {
  loading.value = true;
  try {
    const response = await axios.get('/api/employee/profile');
    if (response.data && response.data.code === 200) {
      profileData.value = response.data.data;
      // 调用获取头像函数 - 使用用户编号
      if (userNumber.value) {
        await fetchUserAvatar(userNumber.value);
      }
      // 同步最近登录时间到统计卡片
      lastLoginTime.value = profileData.value.lastLoginTime || '今天';
      ElMessage.success('用户资料加载成功！');
    } else {
      ElMessage.error(response.data.message || '获取用户资料失败');
    }
  } catch (error) {
    console.error('获取用户资料时出错:', error);
    ElMessage.error('获取用户资料失败，请检查网络或后端服务');
  } finally {
    loading.value = false;
  }
};

// 新增：从后端获取用户头像
const fetchUserAvatar = async (employeeNumber) => {
  if (!employeeNumber) return;
  try {
    // 假设后端API是 GET /api/employee/photo/{employeeNumber}
    const response = await axios.get(`/api/employee/photo/${employeeNumber}`, {
      responseType: 'blob' // 重要：将响应类型设置为blob
    });
    // 将Blob对象转换为URL
    profileData.value.avatarUrl = URL.createObjectURL(response.data);
  } catch (error) {
    console.error(`获取员工 ${employeeNumber} 头像失败:`, error);
    // 如果获取失败，不设置avatarUrl，让它显示默认图标
    profileData.value.avatarUrl = null;
    ElMessage.warning('未能加载用户头像');
  }
};

// 计算入职天数
const calculateDaysSinceHire = () => {
  if (!profileData.value.hireDate) return '0';
  const hireDate = new Date(profileData.value.hireDate);
  const today = new Date();
  const diffTime = Math.abs(today - hireDate);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays.toString();
};

onMounted(async () => {
  await fetchUserProfile();
  lastLoginTime.value = profileData.value.lastLoginTime || '今天';
  // 从仪表盘API获取真实统计数据
  try {
    const resp = await axios.get('/api/employee/dashboard', {
      params: { userNumber: userStore.userNumber }
    });
    if (resp.data?.status) {
      dataCount.value = resp.data.data.my_downloads || 0;
    }
  } catch {
    dataCount.value = 0;
  }
});

const editProfile = () => {
  // 打开编辑对话框，填充当前数据
  editForm.value = {
    userName: profileData.value.userName,
    email: profileData.value.email,
    phoneNumber: profileData.value.phoneNumber,
    address: profileData.value.address,
    avatar: null,
    avatarUrl: profileData.value.avatarUrl || ''
  };
  editDialogVisible.value = true;
};

// 头像上传处理
const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleAvatarChange = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('请上传 JPG、JPEG 或 PNG 格式的图片');
    return;
  }

  // 验证文件大小
  const maxSize = 2 * 1024 * 1024; // 2MB
  if (file.size > maxSize) {
    ElMessage.error('头像大小不能超过 2MB');
    return;
  }

  // 读取文件并显示预览
  const reader = new FileReader();
  reader.onload = (e) => {
    editForm.value.avatarUrl = e.target.result;
    editForm.value.avatar = file;
    ElMessage.success('头像上传成功！');
  };
  reader.readAsDataURL(file);
};

const changePassword = () => {
  // 重置密码表单
  passwordForm.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  };
  passwordDialogVisible.value = true;
};

// 保存编辑的个人资料
const saveProfile = async () => {
  try {
    // 创建 FormData 对象，支持文件上传
    const formData = new FormData();
    formData.append('userName', editForm.value.userName);
    formData.append('email', editForm.value.email);
    formData.append('phoneNumber', editForm.value.phoneNumber);
    formData.append('address', editForm.value.address);
    
    // 如果有头像文件，添加到 FormData
    if (editForm.value.avatar) {
      formData.append('avatar', editForm.value.avatar);
    }

    const response = await axios.put('/api/employee/profile', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    
    if (response.data && response.data.code === 200) {
      ElMessage.success('个人资料更新成功！');
      editDialogVisible.value = false;
      // 重新获取用户资料
      await fetchUserProfile();
    } else {
      ElMessage.error(response.data.message || '更新个人资料失败');
    }
  } catch (error) {
    console.error('更新个人资料失败:', error);
    ElMessage.error('更新个人资料失败，请检查网络连接');
  }
};

// 修改密码
const updatePassword = async () => {
  // 验证密码
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.error('新密码和确认密码不一致');
    return;
  }
  
  if (passwordForm.value.newPassword.length < 6) {
    ElMessage.error('新密码长度至少为6位');
    return;
  }
  
  try {
    const response = await axios.put('/api/employee/password', {
      old_password: passwordForm.value.oldPassword,
      new_password: passwordForm.value.newPassword
    });
    
    if (response.data && response.data.code === 200) {
      ElMessage.success('密码修改成功！');
      passwordDialogVisible.value = false;
    } else {
      ElMessage.error(response.data.message || '密码修改失败');
    }
  } catch (error) {
    console.error('修改密码失败:', error);
    ElMessage.error(error.response?.data?.message || '密码修改失败');
  }
};

// 处理编辑对话框关闭
const handleEditClose = (done) => {
  ElMessageBox.confirm('确定要关闭编辑对话框吗？未保存的更改将丢失。')
    .then(() => {
      done();
    })
    .catch(() => {
      // 用户取消关闭
    });
};

// 处理密码对话框关闭
const handlePasswordClose = (done) => {
  ElMessageBox.confirm('确定要关闭密码修改对话框吗？')
    .then(() => {
      done();
    })
    .catch(() => {
      // 用户取消关闭
    });
};
</script>

<style scoped>
.employee-profile-page {
  padding: 0;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: calc(100vh - 60px);
  position: relative;
  overflow: hidden;
}

/* 顶部装饰区域 */
.profile-header-bg {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 60px 24px 40px;
  text-align: center;
  position: relative;
  color: white;
}

.profile-header-bg::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 20"><defs><radialGradient id="a" cx="50%" cy="40%"><stop offset="0%" stop-color="rgba(255,255,255,0.3)"/><stop offset="100%" stop-color="rgba(255,255,255,0)"/></radialGradient></defs><circle cx="20" cy="10" r="8" fill="url(%23a)"/><circle cx="80" cy="10" r="6" fill="url(%23a)"/></svg>') no-repeat center;
  opacity: 0.3;
}

.header-content {
  position: relative;
  z-index: 1;
}

.profile-title {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin: 0 0 8px 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.profile-subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
  font-weight: 400;
}

/* 主要内容区域 */
.profile-main-content {
  padding: 24px;
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  max-width: 800px;
  margin: -20px auto 0;
  position: relative;
  z-index: 2;
}

.box-card {
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
}

.profile-info-card {
  height: fit-content;
}

.card-header {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.profile-content {
  padding: 24px;
}

/* 头像区域 */
.avatar-section {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9ff 0%, #e8f2ff 100%);
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.1);
}

.profile-avatar {
  background: white;
  border: 3px solid #e6f0ff;
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.15);
}

.avatar-info {
  flex: 1;
}

.user-name {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 8px 0;
}

.user-number {
  font-size: 14px;
  color: #7f8c8d;
  margin: 0 0 8px 0;
}

.user-status {
  margin: 0;
}

.default-avatar-icon {
  color: #bdc3c7;
}

.profile-descriptions {
  margin-bottom: 32px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  padding: 20px 0;
}

.action-buttons .el-button {
  min-width: 120px;
  height: 44px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.action-buttons .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 统计卡片 */
.stats-card {
  height: fit-content;
}

.stats-content {
  padding: 24px 0;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
  border-radius: 12px;
  border: 1px solid rgba(64, 158, 255, 0.1);
  transition: all 0.3s ease;
}

.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(64, 158, 255, 0.1);
}

.stat-item:last-child {
  margin-bottom: 0;
}

.quick-links {
  padding: 12px 0 0;
  border-top: 1px solid #eee;
  font-size: 14px;
}
.quick-link {
  color: #409eff;
  text-decoration: none;
}
.quick-link:hover {
  text-decoration: underline;
}
.quick-divider {
  margin: 0 10px;
  color: #ccc;
}

.stat-icon {
  width: 48px;
  height: 48px;
  background: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #7f8c8d;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 头像上传样式 */
.avatar-upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.avatar-preview {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 2px dashed #d9d9d9;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
}

.avatar-preview:hover {
  border-color: #409eff;
  background: #f0f7ff;
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.avatar-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #909399;
}

.avatar-text {
  font-size: 12px;
  color: #909399;
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.3s ease;
  color: white;
  font-size: 12px;
}

.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.avatar-tips {
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .profile-main-content {
    grid-template-columns: 1fr;
    max-width: 800px;
  }
}

@media (max-width: 768px) {
  .profile-header-bg {
    padding: 30px 16px 20px;
  }
  
  .profile-title {
    font-size: 24px;
  }
  
  .profile-subtitle {
    font-size: 14px;
  }
  
  .profile-main-content {
    padding: 16px;
    gap: 16px;
  }
  
  .avatar-section {
    flex-direction: column;
    text-align: center;
    gap: 16px;
  }
  
  .action-buttons {
    flex-direction: column;
    width: 100%;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }
  
  .stat-item {
    flex-direction: column;
    text-align: center;
    gap: 12px;
  }
}
</style>