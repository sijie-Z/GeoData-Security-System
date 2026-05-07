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
