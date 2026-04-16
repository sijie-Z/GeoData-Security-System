<!-- <script setup>
import { reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import NaviApi from "@/api/NaviApi.js";

const data = reactive({
  list: []
});

onMounted(() => {
  NaviApi.getEmpAll().then(navData => {
    data.list = navData;
    console.log("Processed data:", data.list);
  }).catch(err => {
    console.error("API Error:", err);
    ElMessage.error(err.message || "获取导航数据失败");
  });
});
</script>


<template>
  <div class="side">
    <el-menu router background-color="#545c64" text-color="#fff" active-text-color="#ffd04b">
      <template v-for="item in data.list">  

        
        <el-menu-item v-if="!item.children" :index="item.path || ''">
          {{ item.name }}
        </el-menu-item>


        <el-sub-menu v-else :index="item.path || ''">
          <template #title>
            {{ item.name }}
          </template>

          <el-menu-item-group>
            <template v-for="childrenItem in item.children">
              <el-menu-item :index="childrenItem.path || ''">{{ childrenItem.name }}</el-menu-item>
            </template>
          </el-menu-item-group>
        </el-sub-menu>
      </template>
    </el-menu>
  </div>
</template>


<style scoped>

.el-menu{
  border-right: none;
}

</style>

  -->




  <template>
    <div :class="['employee-sidebar', { 'is-collapsed': isCollapse }]">
      <el-menu
        router
        :collapse="isCollapse"
        :default-active="$route.path"
        class="el-menu-vertical-demo"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <div class="sidebar-header" :class="{ 'is-collapsed-header': isCollapse }">
          <!-- ======================================================================= -->
          <!--            【【【 这 是 唯 一 的、最 关 键 的 修 正 点 】】】            -->
          <!-- 将图片路径从 "@/assets/logo.png" 修改为正确的 "@/components/icons/logo.png" -->
          <!-- ======================================================================= -->
          <img src="@/components/icons/logo.png" alt="Logo" class="sidebar-logo" />
          <h1 v-if="!isCollapse" class="sidebar-title">数据平台</h1>
        </div>
  
        <template v-for="item in data.list" :key="item.id">
          <el-menu-item :index="item.path || ''">
            <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
            <template #title>
              <span>{{ item.name }}</span>
            </template>
          </el-menu-item>
        </template>
      </el-menu>
    </div>
  </template>
  
  <script setup>
  import { reactive, onMounted, shallowRef } from "vue";
  import { useRoute } from 'vue-router';
  import { HomeFilled, View, Download, EditPen } from '@element-plus/icons-vue';
  
  const route = useRoute();
  
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
    const mockEmpNavData = [
      {
        id: "dashboard",
        name: "仪表盘",
        icon: shallowRef(HomeFilled),
        path: "/employee"
      },
      {
        id: "data-viewing",
        name: "数据目录",
        icon: shallowRef(View),
        path: "/employee/data_viewing"
      },
      {
        id: "data-application",
        name: "我的申请",
        icon: shallowRef(EditPen),
        path: "/employee/data_application"
      },
      {
        id: "data-download",
        name: "我的下载",
        icon: shallowRef(Download),
        path: "/employee/data_download"
      },
    ];
    data.list = mockEmpNavData;
  });
  </script>
  
  <style scoped>
  .employee-sidebar {
    width: 210px;
    flex-shrink: 0;
    background-color: #304156;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
    transition: width 0.3s ease;
    height: 100vh;
    position: sticky;
    top: 0;
    left: 0;
    z-index: 99;
  }
  
  .employee-sidebar.is-collapsed {
    width: 64px;
  }
  
  .el-menu-vertical-demo:not(.el-menu--collapse) {
    width: 210px;
    min-height: 400px;
  }
  
  .el-menu-vertical-demo {
    border-right: none;
    height: 100%;
  }
  
  .sidebar-header {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 10px;
    background-color: #263445;
    gap: 8px;
    overflow: hidden;
  }
  
  .sidebar-header.is-collapsed-header {
    justify-content: center;
  }
  
  .sidebar-logo {
    height: 32px;
    width: auto;
    min-width: 32px;
  }
  
  .sidebar-title {
    font-size: 18px;
    color: #fff;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    opacity: 1;
    transition: opacity 0.3s ease;
  }
  
  .employee-sidebar.is-collapsed .sidebar-title {
    opacity: 0;
    width: 0;
  }
  
  .el-menu-item, :deep(.el-sub-menu__title) {
    height: 50px;
    line-height: 50px;
    font-size: 15px;
    padding-left: 20px !important;
    position: relative;
  }
  
  .el-menu-item:hover, :deep(.el-sub-menu__title:hover) {
    background-color: #3a4b60 !important;
    color: #409EFF !important;
  }
  
  .el-menu-item.is-active {
    color: #409EFF !important;
    background-color: #2d3e52 !important;
    border-left: 4px solid #409EFF;
    box-sizing: border-box;
  }
  
  .el-menu-item.is-active .el-icon {
    color: #409EFF !important;
  }
  
  .el-icon {
    margin-right: 12px;
    font-size: 18px;
    color: #bfcbd9;
  }
  </style>