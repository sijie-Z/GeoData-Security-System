<template>
  <!-- 侧栏即站点导航：<nav> 提供 navigation 地标（axe region / landmark-one-main 根因之一） -->
  <nav
    ref="navRef"
    class="sidebar"
    :class="{ collapsed: isCollapse }"
  >
    <el-menu
      router
      unique-opened
      :default-active="$route.path"
      :collapse="isCollapse"
      class="sidebar-menu"
    >
      <el-menu-item index="/employee">
        <el-icon><HomeFilled /></el-icon>
        <template #title>{{ $t('sidebar.employee.dashboard') }}</template>
      </el-menu-item>

      <el-menu-item index="/employee/data_viewing">
        <el-icon><View /></el-icon>
        <template #title>{{ $t('sidebar.employee.dataCatalog') }}</template>
      </el-menu-item>

      <el-menu-item index="/employee/data_application">
        <el-icon><EditPen /></el-icon>
        <template #title>{{ $t('sidebar.employee.myApplications') }}</template>
      </el-menu-item>

      <el-menu-item index="/employee/data_download">
        <el-icon><Download /></el-icon>
        <template #title>{{ $t('sidebar.employee.myDownloads') }}</template>
      </el-menu-item>

      <el-menu-item index="/employee/operation_history">
        <el-icon><Clock /></el-icon>
        <template #title>{{ $t('sidebar.employee.operationHistory') }}</template>
      </el-menu-item>

      <el-menu-item index="/employee/notifications">
        <el-icon><Bell /></el-icon>
        <template #title>{{ $t('sidebar.employee.myNotifications') }}</template>
      </el-menu-item>

      <el-menu-item index="/employee/chat">
        <el-icon><ChatDotRound /></el-icon>
        <template #title>{{ $t('sidebar.employee.onlineChat') }}</template>
      </el-menu-item>

      <el-menu-item index="/employee/apply_admin">
        <el-icon><UserFilled /></el-icon>
        <template #title>{{ $t('sidebar.employee.applyAdmin') }}</template>
      </el-menu-item>
    </el-menu>
  </nav>
</template>

<script setup>
import { defineProps, ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import {
  HomeFilled, View, EditPen, Download, Clock, Bell, ChatDotRound, UserFilled
} from '@element-plus/icons-vue'

defineProps({
  isCollapse: {
    type: Boolean,
    default: false
  }
})

const route = useRoute()
const navRef = ref(null)
let scrollTimers = []

// 激活项滚入侧栏可视区（block: 'nearest' 语义；只调整侧栏自身滚动容器，绝不滚动外层壳）
const scrollActiveIntoView = () => {
  const nav = navRef.value
  if (!nav) return
  const active =
    nav.querySelector('.el-menu-item.is-active') ||
    nav.querySelector('.el-sub-menu.is-active > .el-sub-menu__title')
  if (!active) return
  const nr = nav.getBoundingClientRect()
  const ar = active.getBoundingClientRect()
  if (ar.width === 0 && ar.height === 0) return // 激活项在未展开的子菜单里（display:none）
  if (ar.top < nr.top) nav.scrollTop = Math.max(0, nav.scrollTop - (nr.top - ar.top))
  else if (ar.bottom > nr.bottom) nav.scrollTop += ar.bottom - nr.bottom
}

const scheduleScrollActive = () => {
  scrollTimers.forEach(clearTimeout)
  scrollTimers = []
  nextTick(() => {
    requestAnimationFrame(scrollActiveIntoView)
    // 子菜单开合带过渡：过渡中/后再校正两次
    scrollTimers.push(setTimeout(scrollActiveIntoView, 180))
    scrollTimers.push(setTimeout(scrollActiveIntoView, 380))
  })
}

// 路由变化与首挂载都要把激活项滚入可视区（keep-alive 返回页面同样触发 path 变化）
watch(() => route.path, scheduleScrollActive)
onMounted(scheduleScrollActive)
onBeforeUnmount(() => {
  scrollTimers.forEach(clearTimeout)
  scrollTimers = []
})
</script>

<style scoped>
.sidebar {
  width: 200px;
  background: var(--sidebar-solid-bg, #ffffff);
  border-right: 1px solid var(--border-color);
  /* 高度不写死：flex stretch 精确填满顶栏（60px）下的可用高度，自身即滚动容器 */
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain; /* 滚轮在侧栏尽头不链式带动外层壳 */
  transition: width 220ms var(--ease-drawer), background-color var(--duration-200) var(--ease-out-soft), border-color var(--duration-200) var(--ease-out-soft);
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-menu {
  border-right: none !important;
  background: transparent !important;
  height: 100%;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 200px;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 46px;
  line-height: 46px;
  color: var(--sidebar-text) !important;
  font-size: 14px;
  /* 显式属性过渡（原 transition: all 会在容器变宽时全量比对/重算）*/
  transition: background-color var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast) !important;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background-color: var(--sidebar-item-hover) !important;
  color: var(--sidebar-text-active) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--sidebar-text-active) !important;
  background-color: var(--sidebar-item-active) !important;
  border-left: 3px solid var(--primary-500);
}

:deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--sidebar-text-active) !important;
}

:deep(.el-menu--inline) {
  background-color: transparent !important;
}

:deep(.el-sub-menu .el-menu-item) {
  min-width: auto !important;
  padding-left: 50px !important;
  height: 42px;
  line-height: 42px;
}

.el-icon {
  font-size: 17px;
  margin-right: 8px;
}

.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar::-webkit-scrollbar-thumb {
  background: var(--border-color-hover);
  border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: var(--text-3);
}
</style>
