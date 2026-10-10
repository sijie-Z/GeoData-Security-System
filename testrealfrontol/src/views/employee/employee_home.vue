<!-- <script setup>

import '@/assets/employee/css/employeehome.css'
import HomeHeader from "@/components/employee/home/HomeHeader.vue";
import HomeSide from "@/components/employee/home/HomeSide.vue";

</script>

<template>

<div class="employee-home">
  <HomeHeader />

  <div class="main">
    <HomeSide/>

    <div class="content">
      <router-view />

    </div>

  </div>

</div>

  <div class="employee-echarts">

  </div>

</template>

<style scoped>

</style>
 -->



 <script setup>
 import HomeHeader from "@/components/employee/home/HomeHeader.vue";
 import HomeSide from "@/components/employee/home/HomeSide.vue";
 import { ref, watch, onMounted, onUnmounted } from 'vue';
 import { useMediaQuery } from '@vueuse/core';
 import { useRoute } from 'vue-router';

 const route = useRoute();
 // 折叠状态持久化：桌面端记忆到 localStorage；移动端抽屉开合不写入（见下方 watch 守卫）
 const SIDEBAR_COLLAPSE_KEY = 'ui:sidebar-collapsed:employee';
 const readStoredCollapse = () => {
   try {
     return localStorage.getItem(SIDEBAR_COLLAPSE_KEY) === '1';
   } catch (e) {
     return false;
   }
 };
 const isSideCollapse = ref(readStoredCollapse()); // 用于控制侧边栏折叠状态（≥768px 的图标栏）

 // 移动端（<768px）：侧栏改为覆盖层抽屉，由汉堡按钮唤出，遮罩点击/路由切换/Esc 关闭
 const isMobile = useMediaQuery('(max-width: 767px)');
 const isDrawerOpen = ref(false);

 const toggleSideCollapse = () => {
   if (isMobile.value) {
     isDrawerOpen.value = !isDrawerOpen.value;
     return;
   }
   isSideCollapse.value = !isSideCollapse.value;
 };

 const closeDrawer = () => {
   isDrawerOpen.value = false;
 };

 const onKeydown = (e) => {
   if (e.key === 'Escape' && isDrawerOpen.value) closeDrawer();
 };

 onMounted(() => window.addEventListener('keydown', onKeydown));
 onUnmounted(() => window.removeEventListener('keydown', onKeydown));
 watch(() => route.path, closeDrawer);
 watch(isMobile, closeDrawer);
 // 持久化折叠状态（移动端不入此逻辑：抽屉开合不影响该值，也不写存储）
 watch(isSideCollapse, (v) => {
   if (isMobile.value) return;
   try {
     localStorage.setItem(SIDEBAR_COLLAPSE_KEY, v ? '1' : '0');
   } catch (e) {
     /* localStorage 不可用时静默降级 */
   }
 });
 </script>

 <template>
   <div class="employee-home-layout">
     <HomeHeader
       :is-side-collapse="isSideCollapse"
       :is-mobile="isMobile"
       :drawer-open="isDrawerOpen"
       @toggle-sidebar="toggleSideCollapse"
     />

     <div class="main-content-area">
       <div
         v-if="isMobile && isDrawerOpen"
         class="sidebar-mask"
         aria-hidden="true"
         @click="closeDrawer"
       ></div>

       <HomeSide
         :is-collapse="isMobile ? false : isSideCollapse"
         :class="{ 'drawer-open': isMobile && isDrawerOpen }"
       />

       <!-- 主内容地标（<main>）：axe landmark-one-main；tabindex=0 让纵向溢出时可键盘聚焦滚动 -->
       <main
         :class="['content-panel', { 'content-panel-expanded': isSideCollapse }]"
         tabindex="0"
       >
         <router-view v-slot="{ Component }">
           <transition name="page-fade" mode="out-in">
             <keep-alive :include="['EmployeeDashboard', 'EmployeeDataViewing', 'EmployeeNotifications']">
               <div :key="$route.path" style="height: 100%;">
                 <component :is="Component" />
               </div>
             </keep-alive>
           </transition>
         </router-view>
       </main>
     </div>
   </div>
 </template>

 <style scoped>
 .employee-home-layout {
   display: flex;
   flex-direction: column;
   height: 100vh;
   overflow: hidden;
   background-color: var(--bg-secondary, #f0f2f5);
   font-family: var(--font-family);
   color: var(--text-primary, #333);
 }

 .main-content-area {
   display: flex;
   flex-grow: 1;
   min-height: 0;
 }

 .content-panel {
   flex-grow: 1;
   min-width: 0;
   min-height: 0;
   padding: 16px;
   background-color: var(--bg-primary, #ffffff);
   border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
   margin: 12px;
   box-shadow: none;
   overflow-y: auto;
   overflow-x: hidden;
 }

 .page-fade-enter-active,
 .page-fade-leave-active {
   transition: opacity 0.2s ease, transform 0.2s ease;
 }

 .page-fade-enter-from {
   opacity: 0;
   transform: translateY(8px);
 }

 .page-fade-leave-to {
   opacity: 0;
   transform: translateY(-4px);
 }

 /* ===== 移动端壳层（<768px）：侧栏离屏抽屉 + 内容区全宽 =====
    ≥768px 保持桌面现状（媒体查询不生效）。 */
 @media (max-width: 767px) {
   .sidebar-mask {
     position: fixed;
     top: 60px; /* 顶栏保持可点（汉堡可再次开合） */
     left: 0;
     right: 0;
     bottom: 0;
     background: rgba(15, 23, 42, 0.45);
     z-index: 1100;
   }

   .main-content-area > .sidebar {
     position: fixed;
     top: 60px;
     left: 0;
     bottom: 0;
     height: auto;
     width: min(240px, 82vw);
     z-index: 1200;
     transform: translateX(-105%);
     visibility: hidden;
     transition: transform 220ms var(--ease-drawer), visibility 0s linear 260ms;
     box-shadow: var(--shadow-lg);
   }

   .main-content-area > .sidebar.drawer-open {
     transform: translateX(0);
     visibility: visible;
     transition: transform 220ms var(--ease-drawer), visibility 0s;
   }

   .main-content-area > .sidebar :deep(.sidebar-menu:not(.el-menu--collapse)) {
     width: 100%;
   }

   .content-panel {
     margin: 8px;
     padding: 10px;
     overflow-x: auto; /* 原 overflow-x:hidden 会静默裁切；改为可操作横滚 */
   }
 }
 </style>
