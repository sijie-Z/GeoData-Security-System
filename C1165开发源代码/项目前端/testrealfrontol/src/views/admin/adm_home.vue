<!-- <template>

  <div class="admin-home">
    <HomeHeader />
    <div class="main">
      <HomeSide />
      <div class="content">

        <router-view />

      </div>
    </div>
  </div>


</template>

<script setup>

import HomeHeader from "@/components/admin/home/HomeHeader.vue";

import HomeSide from "@/components/admin/home/HomeSide.vue";

import echarts from "/src/views/admin/EChartBar/echarts.vue"


</script>

<style scoped>

</style> -->




<script setup>
import { ref } from 'vue';
import HomeHeader from "@/components/admin/home/HomeHeader.vue";
import HomeSide from "@/components/admin/home/HomeSide.vue";
import { useRouter } from "vue-router";

const router = useRouter();
const isSideCollapse = ref(false); // 用于控制侧边栏折叠状态

// 切换侧边栏折叠状态的函数
const toggleSideCollapse = () => {
  isSideCollapse.value = !isSideCollapse.value;
};
</script>

<template>
  <div class="admin-home-layout">
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
.admin-home-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f0f2f5;
  font-family: 'Inter', sans-serif, "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
  color: #333;
}

.main-content-area {
  display: flex;
  flex-grow: 1;
}

.content-panel {
  flex-grow: 1;
  padding: 24px;
  background-color: #ffffff;
  border-radius: 8px;
  margin: 20px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
  overflow: auto;
  transition: margin-left 0.3s ease;
  margin-left: 20px;
}

/* 侧边栏折叠时内容区域的样式 */
.content-panel-expanded {
  margin-left: calc(64px + 20px); /* 侧边栏折叠后的宽度 (64px) + 外部留白 (20px) */
}
</style>