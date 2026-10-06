<script setup>
import { ref, onErrorCaptured, watch } from 'vue';
import HomeHeader from "@/components/admin/home/HomeHeader.vue";
import HomeSide from "@/components/admin/home/HomeSide.vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from 'element-plus';

const router = useRouter();
const route = useRoute();
const isSideCollapse = ref(false);
const hasError = ref(false);

const toggleSideCollapse = () => {
  isSideCollapse.value = !isSideCollapse.value;
};

// Error boundary — catch child component errors, show fallback instead of white screen
onErrorCaptured((err, instance, info) => {
  console.error('[ErrorBoundary]', err, info);
  hasError.value = true;
  ElMessage.error('页面加载异常，请刷新重试');
  return false; // prevent error from propagating further
});

// Reset error state when route changes (user clicked a different menu item)
watch(() => route.path, () => {
  if (hasError.value) {
    hasError.value = false;
  }
});

const reloadPage = () => {
  hasError.value = false;
  router.replace('/admin').then(() => {
    window.location.reload();
  });
};
</script>

<template>
  <div class="admin-home-layout">
    <HomeHeader :is-side-collapse="isSideCollapse" @toggle-sidebar="toggleSideCollapse" />

    <div class="main-content-area">
      <HomeSide :is-collapse="isSideCollapse" />

      <div :class="['content-panel', { 'content-panel-expanded': isSideCollapse }]">
        <div v-if="hasError" class="error-fallback">
          <h2>⚠️ 页面加载异常</h2>
          <p>子组件渲染出错，请刷新页面或返回首页。</p>
          <el-button type="primary" @click="reloadPage">返回首页</el-button>
        </div>
        <router-view v-else v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <keep-alive :include="['AdminDashboard']">
              <div :key="$route.path" style="height: 100%;">
                <component :is="Component" />
              </div>
            </keep-alive>
          </transition>
        </router-view>
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
  background-color: var(--bg-secondary, #f0f2f5);
  font-family: 'Inter', sans-serif, "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
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
  border-radius: 10px;
  margin: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
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

.error-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #606266;
}
.error-fallback h2 {
  font-size: 20px;
  color: #e6a23c;
  margin-bottom: 12px;
}
.error-fallback p {
  margin-bottom: 20px;
}
</style>
