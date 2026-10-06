<template>
  <div class="sidebar" :class="{ collapsed: isCollapse }">
    <el-menu
      router
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
  </div>
</template>

<script setup>
import { defineProps } from 'vue'
import {
  HomeFilled, View, EditPen, Download, Clock, Bell, ChatDotRound, UserFilled
} from '@element-plus/icons-vue'

defineProps({
  isCollapse: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.sidebar {
  width: 200px;
  background: var(--sidebar-solid-bg, #ffffff);
  border-right: 1px solid var(--border-color);
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.2s ease, background-color 0.25s ease, border-color 0.25s ease;
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
  transition: all 0.15s ease !important;
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
  width: 4px;
}

.sidebar::-webkit-scrollbar-thumb {
  background: var(--border-color-hover);
  border-radius: 2px;
}
</style>
