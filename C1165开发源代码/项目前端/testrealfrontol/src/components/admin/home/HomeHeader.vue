<!-- <script setup>
import { computed, onMounted } from 'vue';
import { useUserStore } from "@/stores/userStore";
import { useRouter } from "vue-router";
import { MostlyCloudy } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import axiosInstance from "@/utils/Axios";

const userStore = useUserStore();
const router = useRouter();

const userNumber = computed(() => userStore.userNumber);

const fetchUserInfo = async () => {
  try {
    const response = await axiosInstance.get('/api/protected');
    userStore.setUserInfo({
      ...userStore.currentUser,
      user_number: response.data.user_number,
      role: response.data.role
    });
  } catch (err) {
    console.error('获取管理员信息失败', err);
    ElMessage.error('获取管理员信息失败');
  }
};

onMounted(() => {
  if (!userNumber.value) {
    fetchUserInfo();
  }
});

const logout = async () => {
  try {
    await axiosInstance.post('/api/logout');
    ElMessage.success('管理员已登出');
  } catch (err) {
    console.error('管理员登出失败', err);
    ElMessage.warning('登出请求失败，但会继续清除本地管理员信息');
  } finally {
    userStore.clearUserInfo();
    await router.push('/login');
  }
};
</script>

<template>
  <div class="header">
    <div class="title">
      <div class="logo">
        <el-icon><MostlyCloudy /></el-icon>
      </div>
      <div class="text">
        <a href="/admin">返回管理员首页</a>
      </div>
    </div>

    <div class="info" v-if="userNumber">
      <div class="user-info">
        <span>管理员: {{ userNumber }}</span>
      </div>
      <div class="logout" @click="logout">
        退出
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 添加您的样式 */
</style> -->





<script setup>
import { computed, onMounted } from 'vue';
import { useUserStore } from "@/stores/userStore";
import { useRouter } from "vue-router";
import { MostlyCloudy, UserFilled, SwitchButton, Expand, Fold } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import axiosInstance from "@/utils/Axios";

const userStore = useUserStore();
const router = useRouter();

const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);

const props = defineProps({
  isSideCollapse: Boolean
});
const emit = defineEmits(['toggle-sidebar']);

const toggleSidebar = () => {
  emit('toggle-sidebar');
};

// ... (其他逻辑保持不变)
const fetchUserInfo = async () => {
  try {
    const response = await axiosInstance.get('/api/protected');
    userStore.setUserInfo({
      ...userStore.currentUser,
      user_number: response.data.user_number,
      role: response.data.role,
      user_name: response.data.user_name || '管理员'
    });
  } catch (err) {
    console.error('获取管理员信息失败', err);
  }
};

onMounted(() => {
  if (!userNumber.value || !userName.value) {
    fetchUserInfo();
  }
});

const logout = async () => {
  try {
    await axiosInstance.post('/api/logout');
    ElMessage.success('管理员已登出');
  } catch (err) {
    console.error('管理员登出失败', err);
    ElMessage.warning('登出请求失败，但会继续清除本地管理员信息');
  } finally {
    userStore.clearUserInfo();
    await router.push('/login');
  }
};
</script>

<template>
  <header class="admin-header">
    <div class="header-left">
      <el-button
          :icon="isSideCollapse ? Expand : Fold"
          class="toggle-sidebar-button"
          text
          @click="toggleSidebar"
      />
      <div class="logo-container">
        <el-icon class="logo-icon"><MostlyCloudy /></el-icon>
        <span class="logo-text" v-if="!isSideCollapse">矢量地理数据安全分发与定责溯源系统</span>
      </div>
      <div class="return-home">
        <router-link :to="{ name: 'AdminDashboard' }" class="return-link">返回管理员首页</router-link>
      </div>
    </div>

    <div class="header-right" v-if="userNumber">
      <div class="user-info-display">
        <el-icon><UserFilled /></el-icon>
        <span>管理员: {{ userName || userNumber }}</span>
      </div>
      <el-button type="danger" :icon="SwitchButton" circle @click="logout" title="退出登录"></el-button>
    </div>
  </header>
</template>

<style scoped>
.admin-header {
  height: 60px;
  background-color: #2c3e50;
  color: #ffffff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
  font-family: 'Inter', sans-serif;
}

.header-left {
  display: flex;
  align-items: center;
}

.toggle-sidebar-button {
  font-size: 20px;
  color: #ffffff;
  margin-right: 10px;
  transition: all 0.3s ease;
}

.toggle-sidebar-button:hover {
  transform: rotate(90deg);
}

.logo-container {
  display: flex;
  align-items: center;
  margin-right: 30px;
  transition: margin-right 0.3s ease;
}

.logo-icon {
  font-size: 28px;
  margin-right: 10px;
  color: #409eff;
}

.logo-text {
  font-size: 20px;
  font-weight: bold;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity 0.3s ease;
}

.return-home .return-link {
  color: #a0a0a0;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.3s ease;
}

.return-home .return-link:hover {
  color: #ffffff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-info-display {
  display: flex;
  align-items: center;
  font-size: 15px;
}

.user-info-display .el-icon {
  margin-right: 8px;
  font-size: 18px;
}

.el-button.el-button--danger.is-circle {
  background-color: #f56c6c;
  border-color: #f56c6c;
  color: white;
  transition: all 0.3s ease;
}

.el-button.el-button--danger.is-circle:hover {
  background-color: #f78989;
  border-color: #f78989;
  transform: translateY(-2px);
}
</style>