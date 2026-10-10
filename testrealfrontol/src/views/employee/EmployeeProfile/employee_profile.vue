<template>
  <div class="employee-profile-page page-container">
    <!-- 顶部装饰区域 -->
    <div class="profile-header-bg">
      <div class="header-content">
        <h1 class="profile-title">{{ $t('empProfile.personalCenter') }}</h1>
        <p class="profile-subtitle">{{ $t('empProfile.manageProfile') }}</p>
      </div>
    </div>

    <div class="profile-main-content">
      <!-- 个人信息卡片 -->
      <el-card class="box-card profile-info-card" v-loading="loading">
        <template #header>
          <div class="card-header">
            <el-icon size="20" color="var(--accent-9)"><User /></el-icon>
            <span>{{ $t('empProfile.basicInfo') }}</span>
          </div>
        </template>
        <div class="profile-content">
          <div class="avatar-section">
            <el-avatar :size="120" class="profile-avatar">
              <img v-if="profileData.avatarUrl" :src="profileData.avatarUrl" :alt="$t('empProfile.employeeAvatar')" @error="handleAvatarError" />
              <el-icon v-else :size="60" class="default-avatar-icon"><User /></el-icon>
            </el-avatar>
            <div class="avatar-info">
              <h2 class="user-name">{{ profileData.userName || $t('empProfile.nameNotSet') }}</h2>
              <p class="user-number">{{ $t('empProfile.employeeNumber') }}: {{ profileData.userNumber || 'N/A' }}</p>
              <p class="user-status">
                <el-tag type="success" size="small">{{ $t('empProfile.active') }}</el-tag>
              </p>
            </div>
          </div>

          <el-descriptions :column="isMobile ? 1 : 2" border class="profile-descriptions">
            <el-descriptions-item :label="$t('empProfile.jobNumber')">
              <strong>{{ profileData.jobNumber || 'N/A' }}</strong>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('empProfile.idNumber')">
              <strong>{{ profileData.idNumber || 'N/A' }}</strong>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('empProfile.department')">
              <strong>{{ profileData.department || 'N/A' }}</strong>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('empProfile.email')">
              <strong>{{ profileData.email || 'N/A' }}</strong>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('empProfile.phone')">
              <strong>{{ profileData.phoneNumber || 'N/A' }}</strong>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('empProfile.hireDate')">
              <strong>{{ profileData.hireDate || 'N/A' }}</strong>
            </el-descriptions-item>
          </el-descriptions>
          <el-descriptions :column="1" border class="profile-descriptions" style="margin-top: 16px;">
            <el-descriptions-item :label="$t('empProfile.address')">
              <strong>{{ profileData.address || 'N/A' }}</strong>
            </el-descriptions-item>
          </el-descriptions>

          <div class="action-buttons">
            <el-button type="primary" @click="editProfile" size="large">
              <el-icon><Edit /></el-icon>
              {{ $t('empProfile.editProfile') }}
            </el-button>
            <el-button @click="openChangePasswordDialog" size="large">
              <el-icon><Key /></el-icon>
              {{ $t('empProfile.changePassword') }}
            </el-button>
          </div>
        </div>
      </el-card>

      <!-- 统计信息卡片 -->
      <el-card class="stats-card">
        <template #header>
          <div class="card-header">
            <el-icon size="20" color="var(--tint-success-text)"><DataAnalysis /></el-icon>
            <span>{{ $t('empProfile.accountStats') }}</span>
          </div>
        </template>
        <div class="stats-content">
          <div class="stat-item">
            <div class="stat-icon">
              <el-icon size="24" color="var(--accent-9)"><Calendar /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ profileData.hireDate ? calculateDaysSinceHire() : '—' }}</div>
              <div class="stat-label">{{ profileData.hireDate ? $t('empProfile.daysSinceHire') : $t('empProfile.noHireDate') || '入职日期未设置' }}</div>
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-icon">
              <el-icon size="24" color="var(--tint-success-text)"><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ lastLoginTime || $t('empProfile.firstLogin') }}</div>
              <div class="stat-label">{{ $t('empProfile.recentLogin') }}</div>
            </div>
          </div>
          <div class="stat-item">
            <div class="stat-icon">
              <el-icon size="24" color="var(--tint-warning-text)"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ dataCount || '0' }}</div>
              <div class="stat-label">{{ $t('empProfile.processedData') }}</div>
            </div>
          </div>
        </div>
        <div class="quick-links">
          <router-link to="/employee/operation_history" class="quick-link">{{ $t('empProfile.operationHistory') }}</router-link>
          <span class="quick-divider">|</span>
          <router-link to="/employee/notifications" class="quick-link">{{ $t('empProfile.myNotifications') }}</router-link>
        </div>
      </el-card>
    </div>

    <!-- 编辑资料对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="$t('empProfile.editProfileTitle')"
      width="500px"
      :before-close="handleEditClose"
    >
      <el-form :model="editForm" label-width="80px">
        <!-- 头像上传区域 -->
        <el-form-item :label="$t('empProfile.avatar')">
          <div class="avatar-upload-section">
            <div class="avatar-preview" @click="triggerFileInput">
              <img v-if="editForm.avatarUrl" :src="editForm.avatarUrl" :alt="$t('empProfile.avatarPreview')" class="avatar-image" />
              <div v-else class="avatar-placeholder">
                <el-icon size="32" color="var(--text-4)"><User /></el-icon>
                <span class="avatar-text">{{ $t('empProfile.clickToUpload') }}</span>
              </div>
              <div class="avatar-overlay">
                <el-icon color="white" size="20"><Camera /></el-icon>
                <span>{{ $t('empProfile.changeAvatar') }}</span>
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
                {{ $t('empProfile.avatarTips') }}
              </el-text>
            </div>
          </div>
        </el-form-item>

        <el-form-item :label="$t('empProfile.name')">
          <el-input v-model="editForm.userName" :placeholder="$t('empProfile.enterName')" />
        </el-form-item>
        <el-form-item :label="$t('empProfile.email')">
          <el-input v-model="editForm.email" :placeholder="$t('empProfile.enterEmail')" />
        </el-form-item>
        <el-form-item :label="$t('empProfile.phoneNumber')">
          <el-input v-model="editForm.phoneNumber" :placeholder="$t('empProfile.enterPhone')" />
        </el-form-item>
        <el-form-item :label="$t('empProfile.address')">
          <el-input v-model="editForm.address" :placeholder="$t('empProfile.enterAddress')" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">{{ $t('empProfile.cancel') }}</el-button>
          <el-button type="primary" @click="saveProfile">{{ $t('empProfile.save') }}</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="passwordDialogVisible"
      :title="$t('empProfile.changePasswordTitle')"
      width="500px"
      :before-close="handlePasswordClose"
    >
      <el-form :model="passwordForm" label-width="100px">
        <el-form-item :label="$t('empProfile.oldPassword')">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            :placeholder="$t('empProfile.enterOldPassword')"
            show-password
          />
        </el-form-item>
        <el-form-item :label="$t('empProfile.newPassword')">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            :placeholder="$t('empProfile.enterNewPassword')"
            show-password
          />
        </el-form-item>
        <el-form-item :label="$t('empProfile.confirmPassword')">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            :placeholder="$t('empProfile.enterConfirmPassword')"
            show-password
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="passwordDialogVisible = false">{{ $t('empProfile.cancel') }}</el-button>
          <el-button type="primary" @click="updatePassword">{{ $t('empProfile.confirmChange') }}</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useMediaQuery } from '@vueuse/core';
import { ElMessage, ElLoading, ElMessageBox } from 'element-plus';
import { User, Camera, Edit, Key, DataAnalysis, Calendar, Clock, Document } from '@element-plus/icons-vue';
import { getProfile, updateProfile, changePassword, getPhoto, getDashboard } from '@/api/employee';
import { useUserStore } from '@/stores/userStore';

const { t } = useI18n();
const userStore = useUserStore();
const isMobile = useMediaQuery('(max-width: 767px)');

// 获取当前用户编号
const userNumber = computed(() => userStore.userNumber);
const loading = ref(false);

// 存放从后端获取的员工资料数据
const profileData = ref({
  userName: '',
  userNumber: '',
  jobNumber: '',
  idNumber: '',
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
    const response = await getProfile();
    const body = response?.data;
    if (body?.status) {
      profileData.value = body.data;
      // 调用获取头像函数 - 使用用户编号
      if (userNumber.value) {
        await fetchUserAvatar(userNumber.value);
      }
      // 同步最近登录时间到统计卡片
      lastLoginTime.value = profileData.value.lastLoginTime || t('empProfile.today');
    } else {
      ElMessage.error(body?.msg || t('empProfile.profileLoadFail'));
    }
  } catch (error) {
    console.error('获取用户资料时出错:', error);
    ElMessage.error(t('empProfile.profileLoadFailNetwork'));
  } finally {
    loading.value = false;
  }
};

// 新增：从后端获取用户头像
const fetchUserAvatar = async (employeeNumber) => {
  if (!employeeNumber) return;
  try {
    const response = await getPhoto(employeeNumber, { responseType: 'blob' });
    // 将Blob对象转换为URL
    profileData.value.avatarUrl = URL.createObjectURL(response.data);
  } catch (error) {
    // 头像加载失败属于正常情况，静默显示默认图标
    profileData.value.avatarUrl = null;
  }
};

// 头像图片加载失败（URL 失效等）：回退默认图标，暗色下不再露出 alt 文字
const handleAvatarError = () => {
  profileData.value.avatarUrl = null;
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
  lastLoginTime.value = profileData.value.lastLoginTime || t('empProfile.today');
  // 从仪表盘API获取真实统计数据
  try {
    const resp = await getDashboard();
    const dashBody = resp?.data;
    if (dashBody?.status) {
      dataCount.value = dashBody.data?.my_downloads || 0;
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
    ElMessage.error(t('empProfile.avatarFormatError'));
    return;
  }

  // 验证文件大小
  const maxSize = 2 * 1024 * 1024; // 2MB
  if (file.size > maxSize) {
    ElMessage.error(t('empProfile.avatarSizeError'));
    return;
  }

  // 读取文件并显示预览
  const reader = new FileReader();
  reader.onload = (e) => {
    editForm.value.avatarUrl = e.target.result;
    editForm.value.avatar = file;
    ElMessage.success(t('empProfile.avatarUploadSuccess'));
  };
  reader.readAsDataURL(file);
};

const openChangePasswordDialog = () => {
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

    const response = await updateProfile(formData);

    if (response.data && response.data.status) {
      ElMessage.success(response.data.msg || t('empProfile.profileUpdateSuccess'));
      editDialogVisible.value = false;
      // 重新获取用户资料
      await fetchUserProfile();
    } else {
      ElMessage.error(response.data?.msg || t('empProfile.profileUpdateFail'));
    }
  } catch (error) {
    console.error('更新个人资料失败:', error);
    ElMessage.error(t('empProfile.profileUpdateFailNetwork'));
  }
};

// 修改密码
const updatePassword = async () => {
  // 验证密码
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.error(t('empProfile.passwordMismatch'));
    return;
  }

  if (passwordForm.value.newPassword.length < 6) {
    ElMessage.error(t('empProfile.passwordTooShort'));
    return;
  }

  try {
    const response = await changePassword({
      old_password: passwordForm.value.oldPassword,
      new_password: passwordForm.value.newPassword
    });

    if (response.data && response.data.status) {
      ElMessage.success(response.data.msg || t('empProfile.passwordChangeSuccess'));
      passwordDialogVisible.value = false;
    } else {
      ElMessage.error(response.data?.msg || t('empProfile.passwordChangeFail'));
    }
  } catch (error) {
    console.error('修改密码失败:', error);
    ElMessage.error(error.response?.data?.message || t('empProfile.passwordChangeFail'));
  }
};

// 处理编辑对话框关闭
const handleEditClose = (done) => {
  ElMessageBox.confirm(t('empProfile.closeEditConfirm'))
    .then(() => {
      done();
    })
    .catch(() => {
      // 用户取消关闭
    });
};

// 处理密码对话框关闭
const handlePasswordClose = (done) => {
  ElMessageBox.confirm(t('empProfile.closePasswordConfirm'))
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
  background: var(--bg-canvas);
  min-height: calc(100vh - 60px);
  position: relative;
  overflow: hidden;
}

/* 顶部装饰区域 */
.profile-header-bg {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
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
  color: var(--text-1);
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--border-subtle);
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
  background: var(--tint-info-bg);
  border-radius: 12px;
  border: 1px solid var(--tint-info-border);
}

.profile-avatar {
  background: var(--bg-raised);
  border: 3px solid var(--border-default);
  box-shadow: var(--shadow-sm);
}

.avatar-info {
  flex: 1;
}

.user-name {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-1);
  margin: 0 0 8px 0;
}

.user-number {
  font-size: 14px;
  color: var(--text-3);
  margin: 0 0 8px 0;
}

.user-status {
  margin: 0;
}

.default-avatar-icon {
  color: var(--text-4);
}

.profile-descriptions {
  margin-bottom: 32px;
  background: var(--bg-surface);
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
  font-weight: 400;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.action-buttons .el-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
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
  background: var(--bg-inset);
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  transition: all 0.3s ease;
}

.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-item:last-child {
  margin-bottom: 0;
}

.quick-links {
  padding: 12px 0 0;
  border-top: 1px solid var(--border-subtle);
  font-size: 14px;
}
.quick-link {
  color: var(--accent-9);
  text-decoration: none;
}
.quick-link:hover {
  text-decoration: underline;
}
.quick-divider {
  margin: 0 10px;
  color: var(--text-4);
}

.stat-icon {
  width: 48px;
  height: 48px;
  background: var(--bg-raised);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-1);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--text-3);
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
  border: 2px dashed var(--border-strong);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-inset);
}

.avatar-preview:hover {
  border-color: var(--accent-9);
  background: var(--tint-info-bg);
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
  color: var(--text-4);
}

.avatar-text {
  font-size: 12px;
  color: var(--text-4);
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
