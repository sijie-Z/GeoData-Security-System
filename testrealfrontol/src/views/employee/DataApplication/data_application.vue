<template>
  <el-card class="page-container" shadow="never">
    <!-- 顶部标题和操作区 -->
    <template #header>
      <div class="card-header">
        <span>{{ $t('empDataApp.title') }}</span>
        <el-button :icon="Refresh" circle @click="get_applications" />
      </div>
    </template>

    <!-- 表格区域 -->
    <el-table :data="data.list" style="width: 100%" stripe v-loading="loading">
      <el-table-column prop="id" :label="$t('empDataApp.applicationId')" width="100" align="center">
         <template #default="{ row }">
          <strong>#{{ row.id }}</strong>
        </template>
      </el-table-column>
      <el-table-column prop="data_alias" :label="$t('empDataApp.applicationDataName')" show-overflow-tooltip />
      <el-table-column prop="data_id" :label="$t('empDataApp.vectorDataId')" width="120" align="center"/>
      <el-table-column prop="reason" :label="$t('empDataApp.applicationReason')" show-overflow-tooltip />

      <el-table-column :label="$t('empDataApp.firstReviewStatus')" width="120" align="center">
        <template #default="{ row }">
          <el-tag :type="getStatusTagType(row.first_statu)">
            {{ getStatusText(row.first_statu) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column :label="$t('empDataApp.secondReviewStatus')" width="120" align="center">
        <template #default="{ row }">
          <div v-if="row.first_statu === false">
            <el-tag type="info">{{ $t('empDataApp.notStarted') }}</el-tag>
          </div>
          <div v-else>
            <el-tag :type="getStatusTagType(row.second_statu)">
              {{ getStatusText(row.second_statu) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('empDataApp.actions')" width="180" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="openLifecycle(row)">{{ $t('empDataApp.viewDetails') }}</el-button>
          <el-button
            v-if="row.first_statu === null && !row.is_recalled"
            type="danger" link size="small"
            @click="handleWithdraw(row)"
          >{{ $t('empDataApp.withdraw') || '撤回' }}</el-button>
          <el-tag v-if="row.is_recalled" type="info" size="small" effect="plain">
            {{ $t('empDataApp.recalled') || '已撤回' }}
          </el-tag>
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

    <!-- Lifecycle drawer -->
    <el-drawer
      v-model="drawerVisible"
      :title="$t('lifecycle.appId') + ': #' + selectedAppId"
      size="520px"
      destroy-on-close
    >
      <ApplicationLifecycle v-if="selectedAppId" :application-id="selectedAppId" />
    </el-drawer>
  </el-card>
</template>

<script setup>
// [新增] 导入 Refresh 图标
import { Refresh } from "@element-plus/icons-vue";
import { reactive, onMounted, ref, watch, computed } from "vue";
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from "element-plus";
import { getMyApplications, withdrawApplication } from '@/api/employee';
import { useUserStore } from "@/stores/userStore.js";
import ApplicationLifecycle from '@/components/common/ApplicationLifecycle.vue';

const { t } = useI18n();

// [新增] 加载状态，提升用户体验
const loading = ref(true);
const drawerVisible = ref(false);
const selectedAppId = ref(null);

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
  if (status === true) return t('empDataApp.statusApproved');
  if (status === false) return t('empDataApp.statusRejected');
  if (status === null) return t('empDataApp.statusPending');
  return 'N/A';
};

const get_applications = async () => {
  loading.value = true; // 开始加载
  try {
    const response = await getMyApplications({
      page: page.value, pageSize: pageSize.value, userNumber: userNumber.value
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
    ElMessage.error(t('empDataApp.fetchFailed'));
  } finally {
    loading.value = false; // 结束加载
  }
};

const handleWithdraw = async (row) => {
  try {
    await ElMessageBox.confirm(
      t('empDataApp.withdrawConfirm') || `确定要撤回申请 #${row.id} 吗？`,
      t('empDataApp.withdrawTitle') || '撤回申请',
      { confirmButtonText: t('common.confirm') || '确定', cancelButtonText: t('common.cancel') || '取消', type: 'warning' }
    );
    const resp = await withdrawApplication(row.id);
    if (resp.data.status) {
      ElMessage.success(resp.data.msg || t('empDataApp.withdrawSuccess') || '撤回成功');
      get_applications();
    } else {
      ElMessage.error(resp.data.msg || t('empDataApp.withdrawFailed') || '撤回失败');
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(t('empDataApp.withdrawFailed') || '撤回失败');
    }
  }
};

const openLifecycle = (row) => {
  selectedAppId.value = row.id;
  drawerVisible.value = true;
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
