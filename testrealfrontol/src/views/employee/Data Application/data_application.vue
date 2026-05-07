<template>
  <el-card class="page-container" shadow="never">
    <!-- 顶部标题和操作区 -->
    <template #header>
      <div class="card-header">
        <span>我的申请记录</span>
        <el-button :icon="Refresh" circle @click="get_applications" />
      </div>
    </template>

    <!-- 表格区域 -->
    <el-table :data="data.list" style="width: 100%" stripe v-loading="loading">
      <el-table-column prop="id" label="申请ID" width="100" align="center">
         <template #default="{ row }">
          <strong>#{{ row.id }}</strong>
        </template>
      </el-table-column>
      <el-table-column prop="data_alias" label="申请数据名称" show-overflow-tooltip />
      <el-table-column prop="data_id" label="矢量数据ID" width="120" align="center"/>
      <el-table-column prop="reason" label="申请理由" show-overflow-tooltip />

      <el-table-column label="一审状态" width="120" align="center">
        <template #default="{ row }">
          <el-tag :type="getStatusTagType(row.first_statu)">
            {{ getStatusText(row.first_statu) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="二审状态" width="120" align="center">
        <template #default="{ row }">
          <div v-if="row.first_statu === false">
            <el-tag type="info">未开始</el-tag>
          </div>
          <div v-else>
            <el-tag :type="getStatusTagType(row.second_statu)">
              {{ getStatusText(row.second_statu) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="120" align="center">
        <template #default>
          <el-button type="primary" link size="small">查看详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页器 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        background
        @current-change="pageChanged"
      />
    </div>
  </el-card>
</template>

<script setup>
// [新增] 导入 Refresh 图标
import { Refresh } from "@element-plus/icons-vue";
import { reactive, onMounted, ref, watch, computed } from "vue";
import { ElMessage } from "element-plus";
import axios from '@/utils/Axios';
import { useUserStore } from "@/stores/userStore.js";

// [新增] 加载状态，提升用户体验
const loading = ref(true);

const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);

const data = reactive({
  list: [],
});

const page = ref(1);
const pageSize = ref(10); // 默认每页显示10条，更常用
const total = ref(0);

const pageChanged = (newPage) => {
  page.value = newPage;
};

watch(page, (newValue, oldValue) => {
  if (oldValue !== newValue) {
    get_applications(); //重新获取列表
  }
});

// [新增] 根据状态返回 Tag 类型的函数
const getStatusTagType = (status) => {
  if (status === true) return 'success';
  if (status === false) return 'danger';
  if (status === null) return 'warning';
  return 'info';
};

const getStatusText = (status) => {
  if (status === true) return '已通过';
  if (status === false) return '未通过';
  if (status === null) return '待审核';
  return 'N/A';
};

const get_applications = async () => {
  loading.value = true; // 开始加载
  try {
    const response = await axios.get(`/api/get_applications`, {
      params: { page: page.value, pageSize: pageSize.value, userNumber: userNumber.value },
    });

    if (response.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }
    if (response.data.status === false) { // 严格等于 false
      ElMessage.error(response.data.msg);
      data.list = [];
      total.value = 0;
      return;
    }
    data.list = response.data.emp_get_applications;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error("Error", err);
    ElMessage.error("获取申请记录失败，请稍后重试");
  } finally {
    loading.value = false; // 结束加载
  }
};

onMounted(() => {
  get_applications();
});
</script>

<style scoped>
/* 主容器卡片样式 */
.page-container {
  border-radius: 8px;
  min-height: calc(100vh - 110px); /* 视口高度减去大致的header和margin */
  display: flex;
  flex-direction: column;
}

/* 卡片头部样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header span {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

/* el-table 样式覆盖 */
:deep(.el-table th.el-table__cell) {
  background-color: #f5f7fa;
  color: #606266;
}

:deep(.el-table td.el-table__cell) {
    padding: 12px 0;
}

/* 分页器容器样式 */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 24px;
  padding-bottom: 10px;
}
</style>