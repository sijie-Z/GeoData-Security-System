<!-- <template>
  <div class="side">
    <el-menu 
      router 
      background-color="#545c64" 
      text-color="#fff" 
      active-text-color="#ffd04b"
      :default-active="$route.path"
    >
      <template v-for="item in data.list" :key="item.id">


        <el-menu-item v-if="!item.children || item.children.length === 0" :index="item.path || ''">
          <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
          <span>{{ item.name }}</span>
        </el-menu-item>


        <el-sub-menu v-else :index="item.id">
          <template #title>
            <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
            <span>{{ item.name }}</span>
          </template>
          
          <el-menu-item v-for="childItem in item.children" :key="childItem.id" :index="childItem.path || ''">
            {{ childItem.name }}
          </el-menu-item>
        </el-sub-menu>

      </template>
    </el-menu>
  </div>
</template>

<script setup>
import { reactive, onMounted, shallowRef } from "vue";
import { ElMessage } from "element-plus";
// import NaviApi from "@/api/NaviApi.js";
import "@/assets/admin/css/adminhome.css"

import { 
  User, 
  DocumentChecked, 
  Setting, 
  Picture as WatermarkIcon,
  Folder
} from '@element-plus/icons-vue'

const data = reactive({
  list: []
});

onMounted(() => {
  const mockNavData = [
    {
      id: "employee-management",
      name: "员工管理",
      icon: shallowRef(User),
      children: [
        { id: "info-list", name: "信息列表", path: "/admin/employee_management/information_list" },
        { id: "info-add", name: "信息录入", path: "/admin/employee_management/information_add" },
        { id: "account-list", name: "账号列表", path: "/admin/employee_management/account_list" },
        { id: "account-add", name: "账号添加", path: "/admin/employee_management/account_add" },
      ]
    },
    {
      id: "approve-application",
      name: "审批申请",
      icon: shallowRef(DocumentChecked),
      children: [
        { id: "not-approved", name: "待审批", path: "/admin/approve_application/not_approved" },
        { id: "approved", name: "已审批", path: "/admin/approve_application/approved" },
      ]
    },
    {
      id: "data-management",
      name: "数据管理",
      icon: shallowRef(Folder),
      children: [
        {
          id: "data-upload",
          name: "数据上传",
          path: "/admin/data/upload" 
        }
      ]
    },
    {
      id: "watermark-process",
      name: "水印流程",
      icon: shallowRef(WatermarkIcon),
      children: [
          { id: "wm-gen", name: "水印生成", path: "/admin/watermark_generation" },
          { id: "wm-embed", name: "水印嵌入", path: "/admin/watermark_embedding" },
          { id: "wm-extract", name: "水印提取", path: "/admin/watermark_extraction" },
      ]
    },
    {
      id: "system-management",
      name: "系统管理",
      icon: shallowRef(Setting),
      children: [
        { 
          id: "log-viewer", 
          name: "操作日志", 
          path: "/admin/logs"
        }
      ]
    }
  ];

  data.list = mockNavData;
  console.log("Using temporary mock navigation data:", data.list);
});
</script>

<style scoped>
.el-menu {
  border-right: none;
}
</style>  -->



<template>
  <div :class="['admin-sidebar', { 'is-collapsed': isCollapse }]">
    <el-menu
      router
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409EFF"
      :default-active="$route.path"
      :collapse="isCollapse"
      class="el-menu-vertical-demo"
    >
      <template v-for="item in data.list" :key="item.id">
        <el-menu-item v-if="!item.children || item.children.length === 0" :index="item.path || ''">
          <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
          <template #title>
            <span>{{ item.name }}</span>
          </template>
        </el-menu-item>

        <el-sub-menu v-else :index="item.id">
          <template #title>
            <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
            <span>{{ item.name }}</span>
          </template>

          <template v-for="childItem in item.children" :key="childItem.id">
            <el-menu-item-group v-if="childItem.children && childItem.children.length > 0">
              <template #title>{{ childItem.name }}</template>
              <el-menu-item v-for="grandchildItem in childItem.children" :key="grandchildItem.id" :index="grandchildItem.path || ''">
                <el-icon v-if="grandchildItem.icon"><component :is="grandchildItem.icon" /></el-icon>
                <span>{{ grandchildItem.name }}</span>
              </el-menu-item>
            </el-menu-item-group>
            <el-menu-item v-else :index="childItem.path || ''">
              <el-icon v-if="childItem.icon"><component :is="childItem.icon" /></el-icon>
              <span>{{ childItem.name }}</span>
            </el-menu-item>
          </template>
        </el-sub-menu>
      </template>
    </el-menu>
  </div>
</template>

<script setup>
import { reactive, onMounted, shallowRef } from "vue";
import {
  HomeFilled, User, DocumentChecked, Setting,
  Picture as WatermarkIcon, Folder, MagicStick, Crop, Search
} from '@element-plus/icons-vue'

const props = defineProps({
  isCollapse: {
    type: Boolean,
    default: false,
  },
});

const data = reactive({
  list: []
});

onMounted(() => {
  const mockNavData = [
    {
      id: "admin-dashboard",
      name: "仪表板",
      icon: shallowRef(HomeFilled),
      path: "/admin"
    },
    {
      id: "employee-management",
      name: "员工管理",
      icon: shallowRef(User),
      children: [
        { id: "info-list", name: "信息列表", path: "/admin/employee_management/information_list" },
        { id: "info-add", name: "信息录入", path: "/admin/employee_management/information_add" },
        { id: "account-list", name: "账号列表", path: "/admin/employee_management/account_list" },
        { id: "account-add", name: "账号添加", path: "/admin/employee_management/account_add" },
      ]
    },
    {
      id: "approve-application",
      name: "审批申请",
      icon: shallowRef(DocumentChecked),
      children: [
        { id: "not-approved", name: "待审批", path: "/admin/approve_application/not_approved" },
        { id: "approved", name: "已审批", path: "/admin/approve_application/approved" },
      ]
    },
    {
      id: "data-management",
      name: "数据管理",
      icon: shallowRef(Folder),
      children: [
        {
          id: "data-upload",
          name: "数据上传",
          path: "/admin/data/upload"
        }
      ]
    },
    {
      id: "watermark-process",
      name: "水印流程",
      icon: shallowRef(WatermarkIcon),
      children: [
        {
          id: "vector-watermark",
          name: "矢量数据水印",
          children: [
            { id: "wm-gen-vector", name: "生成", path: "/admin/watermark_generation", icon: shallowRef(MagicStick) },
            { id: "wm-embed-vector", name: "嵌入", path: "/admin/watermark_embedding", icon: shallowRef(Crop) },
            { id: "wm-extract-vector", name: "提取", path: "/admin/watermark_extraction", icon: shallowRef(Search) },
          ]
        },
        // --- 新增：栅格数据水印菜单项 ---
        {
          id: "raster-watermark",
          name: "栅格数据水印",
          children: [
            { id: "wm-gen-raster", name: "生成", path: "/admin/raster_watermark_generation", icon: shallowRef(MagicStick) },
            { id: "wm-embed-raster", name: "嵌入", path: "/admin/raster_watermark_embedding", icon: shallowRef(Crop) },
            { id: "wm-extract-raster", name: "提取", path: "/admin/raster_watermark_extraction", icon: shallowRef(Search) },
          ]
        }
        // --- 新增结束 ---
      ]
    },
    {
      id: "system-management",
      name: "系统管理",
      icon: shallowRef(Setting),
      children: [
        {
          id: "log-viewer",
          name: "操作日志",
          path: "/admin/logs"
        }
      ]
    }
  ];

  data.list = mockNavData;
});
</script>

<style scoped>
.admin-sidebar {
  width: 220px;
  flex-shrink: 0;
  background-color: #304156;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  padding-top: 10px;
  font-family: 'Inter', sans-serif;
  height: 100vh;
  transition: width 0.3s ease;
  overflow-y: auto;
  overflow-x: hidden;
}

.admin-sidebar.is-collapsed {
  width: 64px;
}

.el-menu-vertical-demo:not(.el-menu--collapse) {
  width: 220px;
  min-height: 400px;
}

.el-menu-vertical-demo {
  border-right: none;
}

.el-menu-item,
:deep(.el-sub-menu__title) {
  height: 50px;
  line-height: 50px;
  font-size: 15px;
  color: #bfcbd9;
  transition: all 0.3s ease;
}

.el-menu-item:hover,
:deep(.el-sub-menu__title):hover {
  background-color: #263445 !important;
  color: #409EFF !important;
}

.el-menu-item.is-active {
  color: #409EFF !important;
  background-color: #202b38 !important;
  border-left: 4px solid #409EFF;
  box-sizing: border-box;
}

.el-menu--inline {
  background-color: #263445 !important;
}

.el-icon {
  margin-right: 10px;
  font-size: 18px;
}

:deep(.el-menu-item-group__title) {
  padding: 7px 0 7px 20px !important;
  font-size: 13px;
  color: #909399;
  font-weight: bold;
}
</style>
