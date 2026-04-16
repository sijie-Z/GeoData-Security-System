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
 import { ref } from 'vue';
 
 const isSideCollapse = ref(false); // 用于控制侧边栏折叠状态
 
 const toggleSideCollapse = () => {
   isSideCollapse.value = !isSideCollapse.value;
 };
 </script>
 
 <template>
   <div class="employee-home-layout">
     <HomeHeader :is-side-collapse="isSideCollapse" @toggle-sidebar="toggleSideCollapse" />
 
     <div class="main-content-area">
       <HomeSide :is-collapse="isSideCollapse" />
 
       <div :class="['content-panel', { 'content-panel-expanded': isSideCollapse }]">
         <router-view />
       </div>
     </div>
   </div>
 </template>
 
 <style scoped>
 .employee-home-layout {
   display: flex;
   flex-direction: column;
   min-height: 100vh; /* 确保整个页面至少占据视口高度 */
   background-color: #f0f2f5; /* 柔和的背景色 */
   font-family: 'Inter', sans-serif, "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
   color: #333;
 }
 
 .main-content-area {
   display: flex;
   flex-grow: 1; /* 让主内容区域占据剩余空间 */
 }
 
 .content-panel {
   flex-grow: 1; /* 让内容面板占据侧边栏之外的所有空间 */
   padding: 24px; /* 内部填充 */
   background-color: #ffffff; /* 白色背景 */
   border-radius: 8px; /* 圆角 */
   margin: 20px; /* 外部留白 */
   box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05); /* 柔和阴影 */
   overflow: auto; /* 确保内容溢出时可滚动 */
   transition: margin-left 0.3s ease; /* 添加过渡效果 */
   margin-left: 20px; /* 默认与侧边栏有间距 */
 }
 
 /* 侧边栏折叠时内容区域的样式 */
 .content-panel-expanded {
   margin-left: calc(64px + 20px); /* 侧边栏折叠后的宽度 (64px) + 外部留白 (20px) */
 }
 </style>