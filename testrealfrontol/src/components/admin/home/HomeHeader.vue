<script setup>
import { computed, onMounted } from 'vue';
import { useUserStore } from "@/stores/userStore";
import { useRouter } from "vue-router";
import { useI18n } from 'vue-i18n';
import { UserFilled, SwitchButton, Expand, Fold } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import axiosInstance from "@/utils/Axios";
import NotificationCenter from "@/components/common/NotificationCenter.vue";
import LanguageSwitcher from "@/components/common/LanguageSwitcher.vue";

const { t } = useI18n();

const userStore = useUserStore();
const router = useRouter();

const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);

const displayLabel = computed(() => {
  const name = userName.value || userNumber.value || '';
  const subRole = userStore.adminSubRole || '';
  let roleText = t('header.admin');
  if (subRole === 'admin1') roleText += '1';
  else if (subRole === 'admin2') roleText += '2';
  else if (subRole === 'admin3') roleText += '3';
  return `${name} (${roleText})`;
});

const props = defineProps({
  isSideCollapse: Boolean
});
const emit = defineEmits(['toggle-sidebar']);

const toggleSidebar = () => {
  emit('toggle-sidebar');
};

const fetchUserInfo = async () => {
  try {
    const response = await axiosInstance.get('/api/protected');
    const respData = response.data?.data || response.data || {};
    userStore.setUserInfo({
      ...userStore.currentUser,
      user_number: respData.user_number,
      role: respData.role,
      user_name: respData.user_name || t('header.admin')
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
    ElMessage.success(t('header.logoutSuccess'));
  } catch (err) {
    console.error('Admin logout failed', err);
    ElMessage.warning(t('header.logoutFailed'));
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
        <img src="@/components/icons/geo-wiki-logo.svg" alt="Logo" class="wiki-logo" />
        <span class="logo-text" v-if="!isSideCollapse">{{ $t('header.systemTitle') }}</span>
      </div>
      <div class="return-home">
        <router-link :to="{ name: 'AdminDashboard' }" class="return-link">{{ $t('header.dashboard') }}</router-link>
      </div>
    </div>

    <div class="header-right" v-if="userNumber">
      <LanguageSwitcher />
      <NotificationCenter />
      <div class="user-info-display">
        <el-icon><UserFilled /></el-icon>
        <span>{{ displayLabel }}</span>
      </div>
      <el-button type="danger" :icon="SwitchButton" circle @click="logout" :title="$t('header.logout')"></el-button>
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

.wiki-logo {
  height: 20px;
  width: 20px;
  margin-right: 8px;
  vertical-align: middle;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
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
  gap: 16px;
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
