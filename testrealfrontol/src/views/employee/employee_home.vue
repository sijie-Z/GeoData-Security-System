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
   height: 100vh;
   overflow: hidden;
   background-color: #f0f2f5;
   font-family: 'Inter', sans-serif, "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
   color: #333;
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
  background-color: #ffffff;
  border-radius: 10px;
  margin: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
  overflow-y: auto;
  overflow-x: hidden;
}
 </style>
