<template>
  <div class="sidebar" :class="{ collapsed: isCollapse }">
    <el-menu
      router
      :default-active="$route.path"
      :collapse="isCollapse"
      class="sidebar-menu"
    >
      <!-- 仪表板 -->
      <el-menu-item index="/admin">
        <el-icon><HomeFilled /></el-icon>
        <template #title>仪表板</template>
      </el-menu-item>

      <!-- 审批管理 -->
      <el-sub-menu index="approval">
        <template #title>
          <el-icon><DocumentChecked /></el-icon>
          <span>审批管理</span>
        </template>
        <el-menu-item index="/admin/approve_application/not_approved">待一审</el-menu-item>
        <el-menu-item index="/admin/approve_application/approved">待二审</el-menu-item>
        <el-menu-item index="/admin/approve_application/dual_channel">双通道审批</el-menu-item>
        <el-menu-item index="/admin/recall">数据回收审议</el-menu-item>
        <el-menu-item index="/admin/admin-application">管理员申请审批</el-menu-item>
      </el-sub-menu>

      <!-- 水印流程 -->
      <el-sub-menu index="watermark">
        <template #title>
          <el-icon><Picture /></el-icon>
          <span>水印流程</span>
        </template>
        <el-sub-menu index="vector-wm">
          <template #title>矢量数据</template>
          <el-menu-item index="/admin/watermark_generation">生成</el-menu-item>
          <el-menu-item index="/admin/watermark_embedding">嵌入</el-menu-item>
          <el-menu-item index="/admin/watermark_extraction">提取</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="raster-wm">
          <template #title>栅格数据</template>
          <el-menu-item index="/admin/raster_watermark_generation">生成</el-menu-item>
          <el-menu-item index="/admin/raster_watermark_embedding">嵌入</el-menu-item>
          <el-menu-item index="/admin/raster_watermark_extraction">提取</el-menu-item>
        </el-sub-menu>
      </el-sub-menu>

      <!-- 数据管理 -->
      <el-sub-menu index="data">
        <template #title>
          <el-icon><Folder /></el-icon>
          <span>数据管理</span>
        </template>
        <el-menu-item index="/admin/data/upload">数据上传</el-menu-item>
      </el-sub-menu>

      <!-- 员工管理 -->
      <el-sub-menu index="employee">
        <template #title>
          <el-icon><User /></el-icon>
          <span>员工管理</span>
        </template>
        <el-menu-item index="/admin/employee_management/information_list">员工列表</el-menu-item>
        <el-menu-item index="/admin/employee_management/information_add">添加员工</el-menu-item>
        <el-menu-item index="/admin/system/chat">在线沟通</el-menu-item>
      </el-sub-menu>

      <!-- 系统设置 -->
      <el-sub-menu index="system">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </template>
        <el-menu-item index="/admin/logs">操作日志</el-menu-item>
        <el-menu-item index="/admin/system/announcements">系统公告</el-menu-item>
        <el-menu-item index="/admin/system/notifications">消息发送</el-menu-item>
        <el-menu-item index="/admin/guide">上手指南</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </div>
</template>

<script setup>
import { defineProps } from 'vue'
import {
  HomeFilled, User, DocumentChecked, Setting,
  Picture, Folder
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
