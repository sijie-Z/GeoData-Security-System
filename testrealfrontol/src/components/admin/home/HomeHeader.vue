<script setup>
import { computed, onMounted } from 'vue';
import { useUserStore } from "@/stores/userStore";
import { useRouter } from "vue-router";
import { useI18n } from 'vue-i18n';
import { UserFilled, SwitchButton, Expand, Fold, Sunny, Moon, Menu } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import axiosInstance from "@/utils/Axios";
import { useTheme } from "@/composables/useTheme.js";
import NotificationCenter from "@/components/common/NotificationCenter.vue";
import LanguageSwitcher from "@/components/common/LanguageSwitcher.vue";

const { t } = useI18n();
const { isDark, toggleTheme } = useTheme();

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

defineProps({
  isSideCollapse: Boolean,
  isMobile: Boolean,
  drawerOpen: Boolean
});
const emit = defineEmits(['toggle-sidebar']);

const toggleSidebar = () => {
  emit('toggle-sidebar');
};

const fetchUserInfo = async () => {
  try {
    const response = await axiosInstance.get('/api/protected');
    const respData = response.data?.data || response.data || {};
    // Guard: only update if API returned valid data
    if (respData.user_number && respData.role) {
      userStore.setUserInfo({
        ...userStore.currentUser,
        user_number: respData.user_number,
        role: respData.role,
        user_name: respData.user_name || t('header.admin')
      });
    }
  } catch (err) {
    console.error('获取管理员信息失败', err);
    // Don't overwrite store on failure — existing data is still valid
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
        :icon="isMobile ? Menu : (isSideCollapse ? Expand : Fold)"
        class="toggle-sidebar-button"
        text
        :aria-label="isMobile ? (drawerOpen ? $t('header.closeMenu') : $t('header.openMenu')) : $t('header.toggleSidebar')"
        :aria-expanded="isMobile ? drawerOpen : undefined"
        @click="toggleSidebar"
      />
      <div class="logo-container">
        <img
          src="@/components/icons/geo-wiki-logo.svg"
          alt="Logo"
          class="wiki-logo"
        >
        <span
          v-if="!isSideCollapse"
          class="logo-text"
        >{{ $t('header.systemTitle') }}</span>
      </div>
      <div class="return-home">
        <router-link
          :to="{ name: 'AdminDashboard' }"
          class="return-link"
        >
          {{ $t('header.dashboard') }}
        </router-link>
      </div>
    </div>

    <div
      v-if="userNumber"
      class="header-right"
    >
      <LanguageSwitcher />
      <el-button
        class="theme-toggle-button"
        text
        :icon="isDark ? Sunny : Moon"
        :title="isDark ? $t('header.switchToLight') : $t('header.switchToDark')"
        :aria-label="isDark ? $t('header.switchToLight') : $t('header.switchToDark')"
        @click="toggleTheme"
      />
      <NotificationCenter />
      <div class="user-info-display">
        <el-icon><UserFilled /></el-icon>
        <span>{{ displayLabel }}</span>
      </div>
      <el-button
        type="danger"
        :icon="SwitchButton"
        circle
        :title="$t('header.logout')"
        @click="logout"
      />
    </div>
  </header>
</template>

<style scoped>
.admin-header {
  height: 60px;
  background-color: var(--admin-header-bg, #ffffff);
  color: var(--text-primary);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--header-shadow);
  flex-shrink: 0;
  font-family: var(--font-family);
}

.theme-toggle-button {
  font-size: 18px;
  color: var(--text-secondary);
  transition: color var(--transition-fast);
}

.theme-toggle-button:hover {
  color: var(--primary-500);
}

.header-left {
  display: flex;
  align-items: center;
}

.toggle-sidebar-button {
  font-size: 20px;
  color: var(--text-secondary);
  margin-right: 10px;
  transition: color var(--transition-fast), transform 220ms var(--ease-drawer);
}

.toggle-sidebar-button:hover {
  color: var(--text-primary);
  transform: rotate(90deg);
}

.logo-container {
  display: flex;
  align-items: center;
  margin-right: 30px;
  transition: margin-right var(--duration-300) var(--ease-out);
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
  transition: opacity var(--duration-300) var(--ease-out);
}

.return-home .return-link {
  color: var(--text-tertiary);
  text-decoration: none;
  font-size: 14px;
  transition: color var(--transition-fast);
}

.return-home .return-link:hover {
  color: var(--text-primary);
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

/* §4.12 着色式危险按钮（登出）：bg-danger/10 → hover /20，替代实心红 */
.el-button.el-button--danger.is-circle {
  background-color: var(--btn-danger-bg);
  border-color: transparent;
  color: var(--btn-danger-text);
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.el-button.el-button--danger.is-circle:hover {
  background-color: var(--btn-danger-bg-hover);
  color: var(--btn-danger-text);
}

/* ===== 移动端顶栏（<768px）：左收标题、右收用户名，保证主题/通知/登出可达 ===== */
@media (max-width: 767px) {
  .admin-header {
    padding: 0 8px;
  }

  .toggle-sidebar-button {
    margin-right: 2px;
  }

  .logo-container {
    margin-right: 0;
  }

  .logo-text,
  .return-home {
    display: none;
  }

  .header-right {
    gap: 6px;
    flex-shrink: 0;
  }

  .user-info-display {
    font-size: 14px;
  }

  .user-info-display .el-icon {
    margin-right: 0;
  }

  .user-info-display span {
    display: none;
  }
}
</style>
