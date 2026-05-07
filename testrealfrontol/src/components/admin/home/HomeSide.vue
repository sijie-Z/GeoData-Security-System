<template>
  <div class="sidebar" :class="{ collapsed: isCollapse }">
    <el-menu
      router
      :default-active="$route.path"
      :collapse="isCollapse"
      class="sidebar-menu"
    >
      <el-menu-item index="/admin">
        <el-icon><HomeFilled /></el-icon>
        <template #title>{{ $t('sidebar.admin.dashboard') }}</template>
      </el-menu-item>

      <el-sub-menu index="approval">
        <template #title>
          <el-icon><DocumentChecked /></el-icon>
          <span>{{ $t('sidebar.admin.approval') }}</span>
        </template>
        <el-menu-item index="/admin/approve_application/not_approved">{{ $t('sidebar.admin.firstReview') }}</el-menu-item>
        <el-menu-item index="/admin/approve_application/approved">{{ $t('sidebar.admin.secondReview') }}</el-menu-item>
        <el-menu-item index="/admin/approve_application/dual_channel">{{ $t('sidebar.admin.dualChannel') }}</el-menu-item>
        <el-menu-item index="/admin/recall">{{ $t('sidebar.admin.dataRecall') }}</el-menu-item>
        <el-menu-item index="/admin/admin-application">{{ $t('sidebar.admin.adminAppApproval') }}</el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="watermark">
        <template #title>
          <el-icon><Picture /></el-icon>
          <span>{{ $t('sidebar.admin.watermark') }}</span>
        </template>
        <el-sub-menu index="vector-wm">
          <template #title>{{ $t('sidebar.admin.vectorData') }}</template>
          <el-menu-item index="/admin/watermark_generation">{{ $t('sidebar.admin.generate') }}</el-menu-item>
          <el-menu-item index="/admin/watermark_embedding">{{ $t('sidebar.admin.embed') }}</el-menu-item>
          <el-menu-item index="/admin/watermark_extraction">{{ $t('sidebar.admin.extract') }}</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="raster-wm">
          <template #title>{{ $t('sidebar.admin.rasterData') }}</template>
          <el-menu-item index="/admin/raster_watermark_generation">{{ $t('sidebar.admin.generate') }}</el-menu-item>
          <el-menu-item index="/admin/raster_watermark_embedding">{{ $t('sidebar.admin.embed') }}</el-menu-item>
          <el-menu-item index="/admin/raster_watermark_extraction">{{ $t('sidebar.admin.extract') }}</el-menu-item>
        </el-sub-menu>
      </el-sub-menu>

      <el-sub-menu index="data">
        <template #title>
          <el-icon><Folder /></el-icon>
          <span>{{ $t('sidebar.admin.dataMgmt') }}</span>
        </template>
        <el-menu-item index="/admin/data/upload">{{ $t('sidebar.admin.dataUpload') }}</el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="employee">
        <template #title>
          <el-icon><User /></el-icon>
          <span>{{ $t('sidebar.admin.employeeMgmt') }}</span>
        </template>
        <el-menu-item index="/admin/employee_management/information_list">{{ $t('sidebar.admin.employeeList') }}</el-menu-item>
        <el-menu-item index="/admin/employee_management/information_add">{{ $t('sidebar.admin.addEmployee') }}</el-menu-item>
        <el-menu-item index="/admin/system/chat">{{ $t('sidebar.admin.onlineChat') }}</el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="system">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>{{ $t('sidebar.admin.systemSettings') }}</span>
        </template>
        <el-menu-item index="/admin/logs">{{ $t('sidebar.admin.operationLogs') }}</el-menu-item>
        <el-menu-item index="/admin/system/announcements">{{ $t('sidebar.admin.systemAnnouncement') }}</el-menu-item>
        <el-menu-item index="/admin/system/notifications">{{ $t('sidebar.admin.messageSend') }}</el-menu-item>
        <el-menu-item index="/admin/guide">{{ $t('sidebar.admin.guide') }}</el-menu-item>
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

:deep(.el-menu--inline) {
  background-color: #1f2d3d !important;
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
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
}
</style>
