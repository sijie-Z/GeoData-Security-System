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
 import { useRouter, useRoute } from "vue-router";
 import { ElMessage } from "element-plus";
 import {
   UserFilled, SwitchButton, ArrowDown,
   QuestionFilled, InfoFilled, Expand, Fold
 } from "@element-plus/icons-vue";
 import Axios from "@/utils/Axios";
 
 const userStore = useUserStore();
 const router = useRouter();
 const route = useRoute();
 
 const userNumber = computed(() => userStore.userNumber);
 const userName = computed(() => userStore.userName);
 const avatarUrl = ref('');
 const basic_url = import.meta.env.VITE_API_URL;
 
 const props = defineProps({
   isSideCollapse: Boolean
 });
 const emit = defineEmits(['toggle-sidebar']);
 
 const toggleSidebar = () => {
   emit('toggle-sidebar');
 };
 
 const fetchUserAvatar = async () => {
   if (userNumber.value) {
     try {
       const response = await Axios.get(`${basic_url}/api/employee/photo/${userNumber.value}`, {
         responseType: 'blob'
       });
       if (response.data && response.data.size > 0) {
         avatarUrl.value = URL.createObjectURL(response.data);
       } else {
         avatarUrl.value = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg';
         ElMessage.warning("未能加载用户头像，使用默认头像。");
       }
     } catch (error) {
       console.error("获取用户头像失败:", error);
       avatarUrl.value = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg';
       ElMessage.warning("获取用户头像时发生错误。");
     }
   } else {
     avatarUrl.value = 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg';
   }
 };
 
 const fetchUserInfoFromProtected = async () => {
   try {
     const response = await Axios.get('/api/protected');
     if (response.data && response.data.data) {
       const userData = response.data.data;
       userStore.setUserInfo({
         ...userStore.currentUser,
         user_number: userData.user_number,
         role: userData.role,
         userName: userData.user_name || '员工',
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
     ElMessage.success('已退出登录');
   } catch (err) {
     console.error('登出请求失败', err);
     ElMessage.warning('登出请求失败，但会继续清除本地信息');
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
         :icon="isSideCollapse ? Expand : Fold"
         class="toggle-sidebar-button"
         text
         @click="toggleSidebar"
       />
       <!-- ======================================================================= -->
       <!--            【【【 这 是 唯 一 的、最 关 键 的 修 正 点 】】】            -->
       <!-- 将图片路径从 "@/assets/logo.png" 修改为正确的 "@/components/icons/logo.png" -->
       <!-- ======================================================================= -->
       <img src="@/components/icons/logo.png" alt="Logo" class="logo" />
       <span class="system-title">矢量地理数据安全分发与定责溯源系统</span>
     </div>
 
     <div class="header-right">
       <el-menu
         class="header-nav-menu"
         mode="horizontal"
         :ellipsis="false"
         :router="true"
         background-color="#ffffff"
         text-color="#555"
         active-text-color="#409EFF"
         :default-active="$route.path"
       >
         <el-menu-item index="/employee">首页</el-menu-item>
         <el-menu-item index="/employee/data_viewing">数据目录</el-menu-item>
         <el-menu-item index="/employee/data_application">我的申请</el-menu-item>
         <el-menu-item index="/employee/data_download">数据下载</el-menu-item>
       </el-menu>
 
       <el-dropdown trigger="click" @command="handleCommand">
         <span class="el-dropdown-link user-info-dropdown">
           <el-avatar :size="36" :src="avatarUrl" class="user-avatar" @error="handleAvatarError">
             <img src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2646ee683b17fdunop.jpeg" alt="默认头像" />
           </el-avatar>
           <span class="user-name">{{ userName || '员工' }}</span>
           <el-icon class="el-icon--right"><arrow-down /></el-icon>
         </span>
         <template #dropdown>
           <el-dropdown-menu>
             <el-dropdown-item command="profile" :icon="UserFilled">个人中心</el-dropdown-item>
             <el-dropdown-item command="help" :icon="QuestionFilled">系统帮助</el-dropdown-item>
             <el-dropdown-item command="about" :icon="InfoFilled">关于系统</el-dropdown-item>
             <el-dropdown-item divided command="logout" :icon="SwitchButton">退出登录</el-dropdown-item>
           </el-dropdown-menu>
         </template>
       </el-dropdown>
     </div>
   </header>
 </template>
 
 <style scoped>
 .employee-header {
   height: 60px;
   background-color: #ffffff;
   color: #333;
   display: flex;
   justify-content: space-between;
   align-items: center;
   padding: 0 20px;
   box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
   flex-shrink: 0;
   font-family: 'Inter', sans-serif;
   z-index: 100;
 }
 
 .header-left {
   display: flex;
   align-items: center;
   gap: 15px;
 }
 
 .toggle-sidebar-button {
   font-size: 20px;
   color: #606266;
   margin-right: 10px;
 }
 
 .logo {
   height: 36px;
   width: auto;
   vertical-align: middle;
 }
 
 .system-title {
   font-size: 20px;
   font-weight: bold;
   color: #333;
   letter-spacing: 0.5px;
   margin-left: 5px;
 }
 
 .header-right {
   display: flex;
   align-items: center;
   gap: 30px;
 }
 
 .header-nav-menu {
   border-bottom: none !important;
 }
 
 .header-nav-menu .el-menu-item {
   height: 60px;
   line-height: 60px;
   font-size: 15px;
   font-weight: 500;
   color: #555;
   transition: all 0.3s ease;
 }
 
 .header-nav-menu .el-menu-item:hover {
   background-color: #f6f6f6 !important;
   color: #409EFF !important;
 }
 
 .header-nav-menu .el-menu-item.is-active {
   color: #409EFF !important;
   border-bottom: 2px solid #409EFF !important;
   background-color: transparent !important;
 }
 
 
 .user-info-dropdown {
   display: flex;
   align-items: center;
   cursor: pointer;
   padding: 5px 10px;
   border-radius: 20px;
   transition: all 0.3s ease;
 }
 
 .user-info-dropdown:hover {
   background-color: #f5f7fa;
 }
 
 .user-avatar {
   margin-right: 8px;
   border: 1px solid #eee;
   box-shadow: 0 1px 4px rgba(0,0,0,0.08);
 }
 
 .user-name {
   font-size: 15px;
   color: #555;
   margin-right: 5px;
 }
 
 .return-home {
     display: none;
 }
 </style>