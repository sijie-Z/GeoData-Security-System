<template>
  <div class="my-history-page">
    <div class="page-header">
      <h1 class="page-title">我的操作历史</h1>
      <p class="page-desc">查看您在本系统中的操作记录，支持按操作类型筛选</p>
    </div>

    <el-card class="history-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">操作记录</span>
          <el-button type="primary" :icon="RefreshRight" circle @click="fetchLogs" :loading="loading" title="刷新" />
        </div>
      </template>

      <div class="filter-bar">
        <el-select
          v-model="filters.action"
          placeholder="操作类型"
          clearable
          style="width: 200px;"
          @change="handleFilterSearch"
        >
          <el-option label="全部类型" value="" />
          <el-option label="用户登录" value="用户登录" />
          <el-option label="提交数据申请" value="提交数据申请" />
          <el-option label="下载数据" value="下载数据" />
          <el-option label="修改密码" value="修改密码" />
          <el-option label="修改个人信息" value="修改个人信息" />
          <el-option label="用户登出" value="用户登出" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="handleFilterSearch">查询</el-button>
        <el-button :icon="RefreshLeft" @click="resetFilters">重置</el-button>
      </div>

      <el-table
        :data="logList"
        border
        stripe
        v-loading="loading"
        class="history-table"
        style="width: 100%"
        :header-cell-style="{ background: '#f5f7fa' }"
      >
        <el-table-column type="index" label="#" width="56" align="center" />
        <el-table-column prop="timestamp" label="操作时间" width="172" />
        <el-table-column prop="ip_address" label="IP 地址" width="140" show-overflow-tooltip />
        <el-table-column prop="action" label="操作类型" width="140" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="88" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === '成功' ? 'success' : 'danger'" size="small" effect="plain" round>
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="260">
          <template #default="scope">
            <pre class="details-cell">{{ formatDetails(scope.row.details) }}</pre>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :page-sizes="[10, 20, 50]"
          v-model:page-size="pageSize"
          v-model:current-page="currentPage"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { Search, RefreshRight, RefreshLeft } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import axios from '@/utils/Axios';

const loading = ref(false);
const logList = ref([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);
const filters = reactive({ action: '' });

const fetchLogs = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`/api/employee/my_logs`, {
      params: {
        page: currentPage.value,
        pageSize: pageSize.value,
        action: filters.action || undefined
      }
    });
    const result = response.data;
    if (result?.status === true && result?.data) {
      logList.value = result.data.list || [];
      total.value = result.data.total ?? 0;
    } else {
      logList.value = [];
      total.value = 0;
      ElMessage.error(result?.msg || '获取记录失败');
    }
  } catch (err) {
    console.error('fetchLogs error', err);
    logList.value = [];
    total.value = 0;
    ElMessage.error(err.response?.data?.msg || err.message || '网络错误');
  } finally {
    loading.value = false;
  }
};

const handlePageChange = () => fetchLogs();
const handleSizeChange = () => {
  currentPage.value = 1;
  fetchLogs();
};
const handleFilterSearch = () => {
  currentPage.value = 1;
  fetchLogs();
};
const resetFilters = () => {
  filters.action = '';
  currentPage.value = 1;
  fetchLogs();
};

const formatDetails = (details) => {
  if (details == null) return '—';
  if (typeof details === 'object') {
    try {
      return JSON.stringify(details, null, 2);
    } catch {
      return String(details);
    }
  }
  return String(details);
};

onMounted(() => fetchLogs());
</script>

<style scoped>
.my-history-page {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 8px 0;
}
.page-desc {
  font-size: 14px;
  color: #6b7280;
  margin: 0;
}
.history-card {
  border-radius: 12px;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}
.history-table {
  font-size: 13px;
}
.details-cell {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #475569;
  max-height: 160px;
  overflow-y: auto;
}
.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
