<template>
  <div class="sidebar" :class="{ collapsed: isCollapse }">
    <el-menu
      router
      :default-active="$route.path"
      :collapse="isCollapse"
      class="sidebar-menu"
    >
      <!-- 仪表盘 -->
      <el-menu-item index="/employee">
        <el-icon><HomeFilled /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>

      <!-- 数据浏览 -->
      <el-menu-item index="/employee/data_viewing">
        <el-icon><View /></el-icon>
        <template #title>数据目录</template>
      </el-menu-item>

      <!-- 数据申请 -->
      <el-menu-item index="/employee/data_application">
        <el-icon><EditPen /></el-icon>
        <template #title>我的申请</template>
      </el-menu-item>

      <!-- 数据下载 -->
      <el-menu-item index="/employee/data_download">
        <el-icon><Download /></el-icon>
        <template #title>我的下载</template>
      </el-menu-item>

      <!-- 操作历史 -->
      <el-menu-item index="/employee/operation_history">
        <el-icon><Clock /></el-icon>
        <template #title>操作历史</template>
      </el-menu-item>

      <!-- 通知 -->
      <el-menu-item index="/employee/notifications">
        <el-icon><Bell /></el-icon>
        <template #title>我的通知</template>
      </el-menu-item>

      <!-- 在线沟通 -->
      <el-menu-item index="/employee/chat">
        <el-icon><ChatDotRound /></el-icon>
        <template #title>在线沟通</template>
      </el-menu-item>

      <!-- 申请成为管理员 -->
      <el-menu-item index="/employee/apply_admin">
        <el-icon><UserFilled /></el-icon>
        <template #title>申请管理员</template>
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
  background: #304156;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.2s ease;
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

/* 菜单项样式 */
:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 46px;
  line-height: 46px;
  color: #bfcbd9 !important;
  font-size: 14px;
  transition: all 0.15s ease !important;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background-color: #263445 !important;
  color: #409EFF !important;
}

:deep(.el-menu-item.is-active) {
  color: #409EFF !important;
  background-color: #1f2d3d !important;
  border-left: 3px solid #409EFF;
}

/* 子菜单背景 */
:deep(.el-menu--inline) {
  background-color: #1f2d3d !important;
}

:deep(.el-sub-menu .el-menu-item) {
  min-width: auto !important;
  padding-left: 50px !important;
  height: 42px;
  line-height: 42px;
}

/* 图标 */
.el-icon {
  font-size: 17px;
  margin-right: 8px;
}

/* 滚动条 */
.sidebar::-webkit-scrollbar {
  width: 4px;
}

.sidebar::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
}
</style>