<!-- <script setup>
import { computed, onMounted, nextTick } from 'vue';
import { useUserStore } from "@/stores/userStore";
import { useRouter } from "vue-router";
import { MostlyCloudy } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import "@/assets/employee/css/employeehome.css"
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
    console.error('获取员工信息失败', err);
    ElMessage.error('获取员工信息失败');
  }
};

onMounted(async () => {
  if (!userNumber.value) {
    await fetchUserInfo();
  }
  await nextTick();
});

const logout = async () => {
  try {
    await axiosInstance.post('/api/logout');
    ElMessage.success('员工已登出');
  } catch (err) {
    console.error('员工登出失败', err);
    ElMessage.warning('登出请求失败，但会继续清除本地员工信息');
  } finally {
    userStore.clearUserInfo();
    await router.push('/login');
  }
};
</script>

<template>
  <header class="header">
    <div class="title">
      <div class="logo">
        <el-icon><MostlyCloudy /></el-icon>
      </div>
      <div class="text">
        <a href="/employee">返回员工首页</a>
      </div>
    </div>


    <nav class="info" v-if="userNumber">
      <div class="user-info">
        <span>员工: {{ userNumber }}</span>
      </div>
      <div class="logout" @click="logout">
        退出
      </div>
    </nav>
  </header>
</template>

<style scoped>

</style>
 -->





 <script setup>
 import { ref, computed, onMounted, nextTick, watch } from 'vue';
 import { useUserStore } from "@/stores/userStore";
 import { useRouter } from "vue-router";
 import { useI18n } from 'vue-i18n';
 import { ElMessage } from "element-plus";
 import {
   UserFilled, SwitchButton, ArrowDown,
   QuestionFilled, InfoFilled, Expand, Fold, Sunny, Moon, Menu
 } from "@element-plus/icons-vue";
 import Axios from "@/utils/Axios";
import { useTheme } from "@/composables/useTheme.js";
import NotificationCenter from "@/components/common/NotificationCenter.vue";
import LanguageSwitcher from "@/components/common/LanguageSwitcher.vue";

const { t } = useI18n();
const { isDark, toggleTheme } = useTheme();
 
 const userStore = useUserStore();
 const router = useRouter();
 
 const userNumber = computed(() => userStore.userNumber);
 const userName = computed(() => userStore.userName);
 const avatarUrl = ref('');

 defineProps({
   isSideCollapse: Boolean,
   isMobile: Boolean,
   drawerOpen: Boolean
 });
 const emit = defineEmits(['toggle-sidebar']);
 
 const toggleSidebar = () => {
   emit('toggle-sidebar');
 };
 
 const fetchUserAvatar = async () => {
   if (userNumber.value) {
     try {
       const response = await Axios.get(`/api/employee/photo/${userNumber.value}`, {
         responseType: 'blob'
       });
       if (response.data && response.data.size > 0) {
         // 清理之前的blob URL
         if (avatarUrl.value.startsWith('blob:')) {
           URL.revokeObjectURL(avatarUrl.value);
         }
         avatarUrl.value = URL.createObjectURL(response.data);
       } else {
         // 无头像数据，静默使用默认头像
         avatarUrl.value = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg';
       }
     } catch (error) {
       // 头像加载失败属于正常情况（用户可能未上传头像），静默使用默认头像
       avatarUrl.value = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg';
     }
   } else {
     avatarUrl.value = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg';
   }
 };
 
 const fetchUserInfoFromProtected = async () => {
   try {
     const response = await Axios.get('/api/protected');
     if (response.data) {
       // 兼容不同的返回格式
       const userData = response.data.data || response.data;
       userStore.setUserInfo({
         ...userStore.currentUser,
         user_number: userData.user_number,
         role: userData.role,
         user_name: userData.user_name || t('header.employee'),
       });
     } else {
       console.warn('Protected API 未返回预期的用户数据。');
     }
   } catch (err) {
     console.error('获取员工基础信息失败:', err);
   }
 };
 
 onMounted(async () => {
   await nextTick();
   await fetchUserInfoFromProtected();
   if (userNumber.value) {
     await fetchUserAvatar();
   }
 });
 
 watch(userNumber, (newVal, oldVal) => {
   if (newVal && newVal !== oldVal) {
     fetchUserAvatar();
   }
 });
 
 const handleAvatarError = () => {
   avatarUrl.value = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg';
 };
 
 const logout = async () => {
   try {
     await Axios.post('/api/logout');
     ElMessage.success(t('header.logoutSuccess'));
   } catch (err) {
     console.error('Logout failed', err);
     ElMessage.warning(t('header.logoutFailed'));
   } finally {
     userStore.clearUserInfo();
     if (avatarUrl.value.startsWith('blob:')) {
       URL.revokeObjectURL(avatarUrl.value);
     }
     await router.push('/login');
   }
 };
 
 const handleCommand = (command) => {
   if (command === 'profile') {
     router.push('/employee/profile');
   } else if (command === 'help') {
     router.push('/employee/help');
   } else if (command === 'about') {
     router.push('/employee/about');
   } else if (command === 'logout') {
     logout();
   }
 };
 </script>
 
<template>
  <header class="employee-header">
    <div class="header-left">
      <el-button
        :icon="isMobile ? Menu : (isSideCollapse ? Expand : Fold)"
        class="toggle-sidebar-button"
        text
        :aria-label="isMobile ? (drawerOpen ? $t('header.closeMenu') : $t('header.openMenu')) : $t('header.toggleSidebar')"
        :aria-expanded="isMobile ? drawerOpen : undefined"
        @click="toggleSidebar"
      />
      <!-- 使用新的维基风格地理空间logo -->
      <img
        src="@/components/icons/geo-wiki-logo.svg"
        alt="Logo"
        class="wiki-logo"
      >
      <span class="system-title">{{ $t('header.systemTitle') }}</span>
    </div>
 
    <div class="header-right">
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
      <el-menu
        class="header-nav-menu"
        mode="horizontal"
        :ellipsis="false"
        :router="true"
        :default-active="$route.path"
      >
        <el-menu-item index="/employee">
          {{ $t('header.home') }}
        </el-menu-item>
        <el-menu-item index="/employee/data_viewing">
          {{ $t('header.dataCatalog') }}
        </el-menu-item>
        <el-menu-item index="/employee/data_application">
          {{ $t('header.myApplications') }}
        </el-menu-item>
        <el-menu-item index="/employee/data_download">
          {{ $t('header.dataDownload') }}
        </el-menu-item>
      </el-menu>
 
      <el-dropdown
        trigger="click"
        @command="handleCommand"
      >
        <span class="el-dropdown-link user-info-dropdown">
          <el-avatar
            :size="36"
            :src="avatarUrl"
            class="user-avatar"
            :alt="$t('header.defaultAvatar')"
            @error="handleAvatarError"
          >
            <img
              src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg"
              :alt="$t('header.defaultAvatar')"
            >
          </el-avatar>
          <span class="user-name">{{ userName || $t('header.employee') }}</span>
          <el-icon class="el-icon--right"><arrow-down /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              command="profile"
              :icon="UserFilled"
            >
              {{ $t('header.profile') }}
            </el-dropdown-item>
            <el-dropdown-item
              command="help"
              :icon="QuestionFilled"
            >
              {{ $t('header.systemHelp') }}
            </el-dropdown-item>
            <el-dropdown-item
              command="about"
              :icon="InfoFilled"
            >
              {{ $t('header.aboutSystem') }}
            </el-dropdown-item>
            <el-dropdown-item
              divided
              command="logout"
              :icon="SwitchButton"
            >
              {{ $t('header.logout') }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>
 
 <style scoped>
 .employee-header {
   height: 60px;
   background-color: var(--header-bg, #ffffff);
   color: var(--text-primary, #333);
   display: flex;
   justify-content: space-between;
   align-items: center;
   padding: 0 20px;
   border-bottom: 1px solid var(--border-color);
   box-shadow: var(--header-shadow);
   flex-shrink: 0;
   font-family: var(--font-family);
   z-index: 100;
 }

 .header-left {
   display: flex;
   align-items: center;
   gap: 15px;
 }

 .toggle-sidebar-button {
   font-size: 20px;
   color: var(--text-secondary, #606266);
   margin-right: 10px;
 }

 .wiki-logo {
  height: 20px;
  width: 20px;
  margin-right: 8px;
  vertical-align: middle;
}

 .system-title {
   font-size: 20px;
   font-weight: bold;
   color: var(--text-primary, #333);
   letter-spacing: 0.5px;
   margin-left: 5px;
 }

 .header-right {
   display: flex;
   align-items: center;
   gap: 30px;
 }

 .theme-toggle-button {
   font-size: 18px;
   color: var(--text-secondary, #606266);
   transition: color var(--transition-fast);
 }

 .theme-toggle-button:hover {
   color: var(--primary-500, #409EFF);
 }

 .header-nav-menu {
   border-bottom: none !important;
   --el-menu-bg-color: transparent;
   --el-menu-text-color: var(--text-secondary, #555);
   --el-menu-active-color: var(--primary-500, #409EFF);
   --el-menu-hover-bg-color: transparent;
 }

 .header-nav-menu .el-menu-item {
   height: 60px;
   line-height: 60px;
   font-size: 15px;
   font-weight: 400;
   color: var(--text-secondary, #555);
   transition: color var(--transition-fast), background-color var(--transition-fast);
 }

 .header-nav-menu .el-menu-item:hover {
   background-color: var(--bg-tertiary, #f6f6f6) !important;
   color: var(--primary-500, #409EFF) !important;
 }

 .header-nav-menu .el-menu-item.is-active {
   color: var(--primary-500, #409EFF) !important;
   border-bottom: 2px solid var(--primary-500, #409EFF) !important;
   background-color: transparent !important;
 }


 .user-info-dropdown {
   display: flex;
   align-items: center;
   cursor: pointer;
   padding: 5px 10px;
   border-radius: 20px;
   transition: background-color var(--transition-fast);
 }

 .user-info-dropdown:hover {
   background-color: var(--bg-tertiary, #f5f7fa);
 }

 .user-avatar {
   margin-right: 8px;
   border: 1px solid var(--border-color, #eee);
   box-shadow: none;
 }

 .user-name {
   font-size: 15px;
   color: var(--text-secondary, #555);
   margin-right: 5px;
 }
 
 .return-home {
     display: none;
 }

 /* ===== 移动端顶栏（<768px）：隐藏重复导航菜单与用户名，保证主题/通知/用户菜单可达 ===== */
 @media (max-width: 767px) {
   .employee-header {
     padding: 0 8px;
   }

   .toggle-sidebar-button {
     margin-right: 2px;
   }

   .wiki-logo {
     margin-right: 0;
   }

   .system-title {
     display: none;
   }

   .header-right {
     gap: 8px;
     flex-shrink: 0;
   }

   .header-nav-menu {
     display: none; /* 四项导航与抽屉菜单完全重复，移动端由抽屉承担 */
   }

   .user-info-dropdown {
     padding: 4px;
   }

   .user-name {
     display: none;
   }
 }
 </style>