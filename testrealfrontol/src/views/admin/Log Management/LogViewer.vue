<template>
  <div class="log-viewer-page">
    <div class="page-header">
      <h1 class="page-title">{{ $t('adminLogViewer.title') }}</h1>
      <p class="page-desc">{{ $t('adminLogViewer.description') }}</p>
    </div>

    <el-card class="log-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ $t('adminLogViewer.logList') }}</span>
          <el-button type="primary" :icon="RefreshRight" circle @click="fetchLogs" :loading="loading" :title="$t('adminLogViewer.refresh')" />
        </div>
      </template>

      <div class="filter-bar">
        <el-input
          v-model="filters.user_number"
          :placeholder="$t('adminLogViewer.filterByNumber')"
          clearable
          class="filter-input"
          style="width: 180px;"
          @clear="handleFilterSearch"
          @keyup.enter="handleFilterSearch"
        >
          <template #prefix>
            <el-icon><User /></el-icon>
          </template>
        </el-input>
        <el-input
          v-model="filters.username"
          :placeholder="$t('adminLogViewer.filterByName')"
          clearable
          class="filter-input"
          style="width: 180px;"
          @clear="handleFilterSearch"
          @keyup.enter="handleFilterSearch"
        >
          <template #prefix>
            <el-icon><UserFilled /></el-icon>
          </template>
        </el-input>
        <el-select
          v-model="filters.action"
          :placeholder="$t('adminLogViewer.actionType')"
          clearable
          class="filter-select"
          style="width: 200px;"
          @change="handleFilterSearch"
        >
          <el-option :label="$t('adminLogViewer.allTypes')" value="" />
          <el-option :label="$t('adminLogViewer.userLogin')" value="用户登录" />
          <el-option :label="$t('adminLogViewer.submitDataRequest')" value="提交数据申请" />
          <el-option :label="$t('adminLogViewer.approveDataRequest')" value="审批数据申请" />
          <el-option :label="$t('adminLogViewer.generateWatermark')" value="生成水印" />
          <el-option :label="$t('adminLogViewer.embedWatermark')" value="嵌入水印" />
          <el-option :label="$t('adminLogViewer.dataUpload')" value="数据上传" />
          <el-option :label="$t('adminLogViewer.userPermissionChange')" value="用户权限修改" />
          <el-option :label="$t('adminLogViewer.dataBackup')" value="数据备份" />
          <el-option :label="$t('adminLogViewer.extractWatermark')" value="提取水印" />
          <el-option :label="$t('adminLogViewer.userLogout')" value="用户登出" />
          <el-option :label="$t('adminLogViewer.securityPolicyUpdate')" value="安全策略更新" />
          <el-option :label="$t('adminLogViewer.downloadData')" value="下载数据" />
          <el-option :label="$t('adminLogViewer.generateReport')" value="生成报告" />
          <el-option :label="$t('adminLogViewer.deleteUser')" value="删除用户" />
          <el-option :label="$t('adminLogViewer.systemParamConfig')" value="系统参数配置" />
        </el-select>
        <el-button type="primary" :icon="Search" @click="handleFilterSearch">{{ $t('adminLogViewer.search') }}</el-button>
        <el-button :icon="RefreshLeft" @click="resetFilters">{{ $t('adminLogViewer.reset') }}</el-button>
      </div>

      <el-table
        :data="logList"
        border
        stripe
        v-loading="loading"
        class="log-table"
        style="width: 100%"
        :header-cell-style="{ background: '#f5f7fa' }"
      >
        <el-table-column type="index" label="#" width="56" align="center" />
        <el-table-column prop="timestamp" :label="$t('adminLogViewer.timestamp')" width="172" sortable />
        <el-table-column prop="user_number" :label="$t('adminLogViewer.userNumber')" width="120" show-overflow-tooltip />
        <el-table-column prop="username" :label="$t('adminLogViewer.operator')" width="110" show-overflow-tooltip />
        <el-table-column prop="ip_address" :label="$t('adminLogViewer.ipAddress')" width="130" show-overflow-tooltip />
        <el-table-column prop="action" :label="$t('adminLogViewer.actionType')" width="130" show-overflow-tooltip />
        <el-table-column prop="status" :label="$t('adminLogViewer.status')" width="88" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === '成功' ? 'success' : 'danger'" size="small" effect="plain" round>
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('adminLogViewer.details')" min-width="240">
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
          :page-sizes="[10, 20, 50, 100]"
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
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search, RefreshRight, RefreshLeft, User, UserFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from '@/utils/Axios'

const { t } = useI18n()

const loading = ref(false)
const logList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const filters = reactive({
  username: '',
  user_number: '',
  action: ''
})

const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await axios.get(`/api/admin/logs`, {
      params: {
        page: currentPage.value,
        pageSize: pageSize.value,
        username: filters.username || undefined,
        user_number: filters.user_number || undefined,
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
      ElMessage.error(result?.msg || t('adminLogViewer.fetchFailed'));
    }
  } catch (err) {
    console.error('fetchLogs error', err);
    logList.value = [];
    total.value = 0;
    ElMessage.error(err.response?.data?.msg || err.message || t('adminLogViewer.networkError'));
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
  filters.username = '';
  filters.user_number = '';
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
.log-viewer-page {
  padding: 24px;
  max-width: 1400px;
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
.log-card {
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
.log-table {
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
