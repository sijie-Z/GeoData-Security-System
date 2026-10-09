<template>
  <div class="log-viewer-page">
    <PageHeader :title="$t('adminLogViewer.title')" :subtitle="$t('adminLogViewer.description')" />

    <el-card class="log-card density-compact" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ $t('adminLogViewer.logList') }}</span>
          <div class="card-header-actions">
            <el-button :icon="Download" :loading="exporting" @click="exportLogs">
              {{ $t('adminLogViewer.exportCsv') }}
            </el-button>
            <el-button :icon="RefreshRight" circle @click="fetchLogs" :loading="loading" :title="$t('adminLogViewer.refresh')" />
          </div>
        </div>
      </template>

      <ListShell
        :empty="!loading && logList.length === 0"
        :empty-variant="hasActiveFilters ? 'filtered' : 'never'"
        :empty-title="$t('adminLogViewer.noLogs')"
        :empty-description="$t('common.noDataDesc')"
        :pagination="{ page: currentPage, pageSize, total, layout: 'total, sizes, prev, pager, next, jumper', pageSizes: [10, 20, 50, 100], background: true }"
        @page-change="handlePageChange"
        @size-change="handleSizeChange"
      >
        <template #filters>
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
            <el-option :label="$t('adminLogViewer.userLogin')" value="登录" />
            <el-option :label="$t('adminLogViewer.submitDataRequest')" value="申请提交" />
            <el-option :label="$t('adminLogViewer.approveDataRequest')" value="一审通过" />
            <el-option :label="$t('adminLogViewer.generateWatermark')" value="生成水印" />
            <el-option :label="$t('adminLogViewer.embedWatermark')" value="嵌入水印" />
            <el-option :label="$t('adminLogViewer.extractWatermark')" value="提取水印" />
            <el-option :label="$t('adminLogViewer.downloadData')" value="下载数据" />
            <el-option :label="$t('adminLogViewer.withdrawApplication')" value="撤回申请" />
            <el-option :label="$t('adminLogViewer.recallProposal')" value="回收提议创建" />
            <el-option :label="$t('adminLogViewer.recallVote')" value="回收投票" />
          </el-select>
          <el-button type="primary" :icon="Search" @click="handleFilterSearch">{{ $t('adminLogViewer.search') }}</el-button>
          <el-button :icon="RefreshLeft" @click="resetFilters">{{ $t('adminLogViewer.reset') }}</el-button>
        </template>

        <el-table
          :data="logList"
          border
          stripe
          v-loading="loading"
          class="log-table"
          style="width: 100%"
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
      </ListShell>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search, RefreshRight, RefreshLeft, Download, User, UserFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getSystemLogs, exportSystemLogs } from '@/api/admin'
import PageHeader from '@/components/common/PageHeader.vue'
import ListShell from '@/components/common/ListShell.vue'

const { t } = useI18n()

const loading = ref(false)
const exporting = ref(false)
const logList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

const filters = reactive({
  username: '',
  user_number: '',
  action: ''
})

// 空态语义：有筛选条件且无结果 -> filtered；否则 never（与 EmptyState 约定一致）
const hasActiveFilters = computed(() => !!(filters.username || filters.user_number || filters.action))

const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await getSystemLogs({
      page: currentPage.value,
      pageSize: pageSize.value,
      username: filters.username || undefined,
      user_number: filters.user_number || undefined,
      action: filters.action || undefined
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

// 分页状态回写与取数流程与旧版一致（旧 v-model 先行回写，现由事件参数回写）
const handlePageChange = (page) => {
  currentPage.value = page;
  fetchLogs();
};
const handleSizeChange = (size) => {
  pageSize.value = size;
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

// 导出 CSV：携带当前筛选参数（与列表同一套过滤），文件名优先取服务端 Content-Disposition
const exportLogs = async () => {
  exporting.value = true;
  try {
    const response = await exportSystemLogs({
      username: filters.username || undefined,
      user_number: filters.user_number || undefined,
      action: filters.action || undefined
    });
    const cd = response?.headers?.['content-disposition'] || '';
    const match = /filename="?([^";]+)"?/i.exec(cd);
    const filename = match ? decodeURIComponent(match[1]) : `audit_logs_${Date.now()}.csv`;
    const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv;charset=utf-8;' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    ElMessage.success(t('adminLogViewer.exportSuccess'));
  } catch (err) {
    console.error('exportLogs error', err);
    ElMessage.error(err.response?.data?.msg || t('adminLogViewer.exportFailed'));
  } finally {
    exporting.value = false;
  }
};

onMounted(() => fetchLogs());
</script>

<style scoped>
.log-viewer-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
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
.card-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-1);
}
.log-table {
  font-size: 13px;
}
.details-cell {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
  padding: 8px 10px;
  background: var(--bg-inset);
  border-radius: 6px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: var(--text-2);
  max-height: 160px;
  overflow-y: auto;
}
</style>
