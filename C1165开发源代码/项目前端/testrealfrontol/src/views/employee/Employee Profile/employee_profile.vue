<!-- <template>
  <div class="employee-profile-page page-container">
    <el-card class="box-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>个人中心</span>
        </div>
      </template>
      <div class="profile-content">
        <el-avatar :size="100" class="profile-avatar">
          <img v-if="profileData.avatarUrl" :src="profileData.avatarUrl" alt="员工头像" />
          <el-icon v-else :size="50" class="default-avatar-icon"><User /></el-icon>
        </el-avatar>

        <el-descriptions :column="1" border class="profile-descriptions">
          <el-descriptions-item label="姓名">
            <strong>{{ profileData.userName || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="员工编号">
            <strong>{{ profileData.userNumber || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="部门">
            <strong>{{ profileData.department || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">
            <strong>{{ profileData.email || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="联系电话">
            <strong>{{ profileData.phoneNumber || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="入职日期">
            <strong>{{ profileData.hireDate || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="住址">
            <strong>{{ profileData.address || 'N/A' }}</strong>
          </el-descriptions-item>
        </el-descriptions>

        <div class="action-buttons">
          <el-button type="primary" @click="editProfile">编辑资料</el-button>
          <el-button @click="changePassword">修改密码</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage, ElLoading } from 'element-plus';
import { User } from '@element-plus/icons-vue'; // 导入 User 图标
import axios from '@/utils/Axios'; // 引入你的 axios 实例
import { useUserStore } from '@/stores/userStore'; // 引入用户状态管理

const userStore = useUserStore();
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

// 从后端获取用户资料
const fetchUserProfile = async () => {
  loading.value = true;
  try {
    const response = await axios.get('/api/employee/profile');
    if (response.data && response.data.code === 200) {
      profileData.value = response.data.data;
      // 调用获取头像函数
      await fetchUserAvatar(profileData.value.userNumber);
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

onMounted(() => {
  fetchUserProfile();
});

const editProfile = () => {
  ElMessage.info('编辑资料功能待实现');
};

const changePassword = () => {
  ElMessage.info('修改密码功能待实现');
};
</script>

<style scoped>
.employee-profile-page {
  padding: 24px;
  background-color: #f7f8fa;
  min-height: calc(100vh - 60px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.box-card {
  width: 100%;
  max-width: 700px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  margin-top: 40px;
}

.card-header {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  text-align: center;
  padding: 10px 0;
}

.profile-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 25px;
  padding: 20px;
}

.profile-avatar {
  border: 4px solid #409eff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.profile-avatar:hover {
  transform: translateY(-5px);
}

:deep(.profile-avatar img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.default-avatar-icon {
    color: #c0c4cc; /* 默认图标颜色 */
}

.profile-descriptions {
  width: 100%;
  max-width: 500px;
}

:deep(.profile-descriptions .el-descriptions__label) {
  background-color: #f9fafb;
  font-weight: 500;
  color: #606266;
  padding: 12px 18px;
  width: 120px;
  vertical-align: middle;
}
:deep(.profile-descriptions .el-descriptions__content) {
  padding: 12px 18px;
  color: #333;
  font-weight: 500;
  vertical-align: middle;
}

.action-buttons {
  display: flex;
  gap: 15px;
  margin-top: 15px;
}

@media (max-width: 768px) {
  .box-card {
    margin: 20px;
  }
  .profile-descriptions {
    max-width: 100%;
  }
}
</style> -->



<!-- <template>
  <div class="employee-profile-page page-container">
    <el-card class="box-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>个人中心</span>
        </div>
      </template>
      <div class="profile-content">
        <el-avatar :size="100" class="profile-avatar">
          <img v-if="profileData.avatarUrl" :src="profileData.avatarUrl" alt="员工头像" @error="handleAvatarError" />
          <el-icon v-else :size="50" class="default-avatar-icon"><User /></el-icon>
        </el-avatar>

        <el-descriptions :column="1" border class="profile-descriptions">
          <el-descriptions-item label="姓名">
            <strong>{{ profileData.userName || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="员工编号">
            <strong>{{ profileData.userNumber || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="部门">
            <strong>{{ profileData.department || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="邮箱">
            <strong>{{ profileData.email || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="联系电话">
            <strong>{{ profileData.phoneNumber || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="入职日期">
            <strong>{{ profileData.hireDate || 'N/A' }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="住址">
            <strong>{{ profileData.address || 'N/A' }}</strong>
          </el-descriptions-item>
        </el-descriptions>

        <div class="action-buttons">
          <el-button type="primary" @click="editProfile">编辑资料</el-button>
          <el-button @click="changePassword">修改密码</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { User } from '@element-plus/icons-vue';
import axios from '@/utils/Axios';
import { useUserStore } from '@/stores/userStore';

const userStore = useUserStore();
const loading = ref(false);
const defaultAvatar = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg';

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

// 从后端获取用户资料
const fetchUserProfile = async () => {
  loading.value = true;
  try {
    // 添加withCredentials以携带凭证
    const response = await axios.get('/api/employee/profile', {
      withCredentials: true
    });
    
    if (response.data && response.data.code === 200) {
      profileData.value = response.data.data;
      // 调用获取头像函数
      await fetchUserAvatar(profileData.value.userNumber);
      ElMessage.success('用户资料加载成功！');
    } else {
      ElMessage.error(response.data.message || '获取用户资料失败');
      // 如果API返回错误，尝试从用户存储中获取基本信息
      loadBasicInfoFromStore();
    }
  } catch (error) {
    console.error('获取用户资料时出错:', error);
    
    // 更详细的错误处理
    if (error.response) {
      // 服务器返回了响应但状态码不在2xx范围内
      console.error('错误状态码:', error.response.status);
      console.error('错误数据:', error.response.data);
      ElMessage.error(`服务器错误: ${error.response.status} - ${error.response.data.message || '未知错误'}`);
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('请求对象:', error.request);
      ElMessage.error('网络错误: 无法连接到服务器');
    } else {
      // 其他错误
      console.error('错误信息:', error.message);
      ElMessage.error('未知错误: ' + error.message);
    }
    
    // 从用户存储中获取基本信息
    loadBasicInfoFromStore();
  } finally {
    loading.value = false;
  }
};

// 从用户存储中获取基本信息
const loadBasicInfoFromStore = () => {
  if (userStore.currentUser) {
    profileData.value.userName = userStore.currentUser.userName || '';
    profileData.value.userNumber = userStore.currentUser.user_number || '';
    profileData.value.department = userStore.currentUser.department || '';
    profileData.value.email = userStore.currentUser.email || '';
    // 其他字段可以根据需要从存储中获取
  }
};

// 从后端获取用户头像
const fetchUserAvatar = async (employeeNumber) => {
  if (!employeeNumber) return;
  try {
    const response = await axios.get(`/api/employee/photo/${employeeNumber}`, {
      responseType: 'blob',
      withCredentials: true // 添加凭证
    });
    
    // 检查响应数据是否有效
    if (response.data && response.data.size > 0) {
      profileData.value.avatarUrl = URL.createObjectURL(response.data);
    } else {
      // 如果响应数据为空，使用默认头像
      profileData.value.avatarUrl = defaultAvatar;
      ElMessage.warning("未能加载用户头像，使用默认头像。");
    }
  } catch (error) {
    console.error(`获取员工 ${employeeNumber} 头像失败:`, error);
    // 如果获取失败，使用默认头像
    profileData.value.avatarUrl = defaultAvatar;
    ElMessage.warning("获取用户头像时发生错误，使用默认头像。");
  }
};

// 处理头像加载错误
const handleAvatarError = () => {
  profileData.value.avatarUrl = defaultAvatar;
};

// 组件卸载时释放Blob URL
onUnmounted(() => {
  if (profileData.value.avatarUrl && profileData.value.avatarUrl.startsWith('blob:')) {
    URL.revokeObjectURL(profileData.value.avatarUrl);
  }
});

onMounted(() => {
  fetchUserProfile();
});

const editProfile = () => {
  ElMessage.info('编辑资料功能待实现');
};

const changePassword = () => {
  ElMessage.info('修改密码功能待实现');
};
</script>

<style scoped>
.employee-profile-page {
  padding: 24px;
  background-color: #f7f8fa;
  min-height: calc(100vh - 60px);
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.box-card {
  width: 100%;
  max-width: 700px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  margin-top: 40px;
}

.card-header {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  text-align: center;
  padding: 10px 0;
}

.profile-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 25px;
  padding: 20px;
}

.profile-avatar {
  border: 4px solid #409eff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.profile-avatar:hover {
  transform: translateY(-5px);
}

:deep(.profile-avatar img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.default-avatar-icon {
    color: #c0c4cc; /* 默认图标颜色 */
}

.profile-descriptions {
  width: 100%;
  max-width: 500px;
}

:deep(.profile-descriptions .el-descriptions__label) {
  background-color: #f9fafb;
  font-weight: 500;
  color: #606266;
  padding: 12px 18px;
  width: 120px;
  vertical-align: middle;
}
:deep(.profile-descriptions .el-descriptions__content) {
  padding: 12px 18px;
  color: #333;
  font-weight: 500;
  vertical-align: middle;
}

.action-buttons {
  display: flex;
  gap: 15px;
  margin-top: 15px;
}

@media (max-width: 768px) {
  .box-card {
    margin: 20px;
  }
  .profile-descriptions {
    max-width: 100%;
  }
}
</style> -->

<template>
  <div class="employee-profile-page page-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>个人中心</span>
        </div>
      </template>
      <div class="profile-content">
        <el-avatar :size="100" class="profile-avatar">
          <img src="@/assets/参考.png" alt="员工头像" />
        </el-avatar>

        <el-descriptions :column="1" border class="profile-descriptions">
          <el-descriptions-item label="姓名">
            <strong>zengsijie</strong>
          </el-descriptions-item>
          <el-descriptions-item label="员工编号">
            <strong>23200214126</strong>
          </el-descriptions-item>
          <el-descriptions-item label="住址">
            <strong>sz</strong>
          </el-descriptions-item>
          <el-descriptions-item label="手机号码">
            <strong>19150649985</strong>
          </el-descriptions-item>
        </el-descriptions>

        <div class="action-buttons">
          <el-button type="primary">编辑资料</el-button>
          <el-button>修改密码</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 根据你的要求，这里不添加任何动态数据或逻辑
</script>

<style scoped>
.employee-profile-page {
  padding: 24px;
  background-color: #f7f8fa;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.box-card {
  width: 100%;
  max-width: 700px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  margin-top: 40px;
}

.card-header {
  font-size: 20px;
  font-weight: 600;
  color: #333;
  text-align: center;
  padding: 10px 0;
}

.profile-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 25px;
  padding: 20px;
}

.profile-avatar {
  border: 4px solid #409eff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.profile-avatar:hover {
  transform: translateY(-5px);
}

:deep(.profile-avatar img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.profile-descriptions {
  width: 100%;
  max-width: 500px;
}

:deep(.profile-descriptions .el-descriptions__label) {
  background-color: #f9fafb;
  font-weight: 500;
  color: #606266;
  padding: 12px 18px;
  width: 120px;
  vertical-align: middle;
}

:deep(.profile-descriptions .el-descriptions__content) {
  padding: 12px 18px;
  color: #333;
  font-weight: 500;
  vertical-align: middle;
}

.action-buttons {
  display: flex;
  gap: 15px;
  margin-top: 15px;
}

@media (max-width: 768px) {
  .box-card {
    margin: 20px;
  }
  .profile-descriptions {
    max-width: 100%;
  }
}
</style>