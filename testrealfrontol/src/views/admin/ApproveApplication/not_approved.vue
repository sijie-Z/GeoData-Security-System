<template>
  <div class="approval-page">
    <div class="page-header">
      <h1 class="page-title">{{ $t('approval.firstReviewTitle') }}</h1>
      <p class="page-desc">{{ $t('approval.firstReviewDescription') }}</p>
    </div>

    <el-card class="table-card" shadow="hover">
      <div class="batch-toolbar" v-if="isAdm1">
        <el-button size="small" type="primary" :disabled="selectedIds.length===0" @click="batchReview('pass')">{{ $t('approval.batchApprove') }}</el-button>
        <el-button size="small" :disabled="selectedIds.length===0" @click="batchReview('fail')">{{ $t('approval.batchReject') }}</el-button>
        <span class="batch-tip">{{ $t('approval.selectedCount', { count: selectedIds.length }) }}</span>
      </div>
      <el-table :data="data.list" border stripe v-loading="loading" class="approval-table" :empty-text="$t('approval.noPendingApproval')" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column prop="id" :label="$t('approval.applyId')" width="90" align="center" />
        <el-table-column prop="data_alias" :label="$t('approval.dataName')" min-width="120" show-overflow-tooltip />
        <el-table-column prop="data_id" :label="$t('approval.dataId')" width="100" align="center" />
        <el-table-column prop="applicant_user_number" :label="$t('approval.applicantId')" width="110" align="center" />
        <el-table-column prop="applicant_name" :label="$t('approval.applicantName')" width="100" align="center" />
        <el-table-column prop="reason" :label="$t('approval.applyReason')" min-width="160" show-overflow-tooltip />

        <el-table-column :label="$t('approval.operation')" width="160" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" @click="pass(scope.row)">{{ $t('approval.approve') }}</el-button>
            <el-button size="small" @click="fail(scope.row)">{{ $t('approval.reject') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="prev, pager, next, jumper, total"
        @current-change="pageChanged"
        class="view-pagination"
      />
    </div>
  </div>
</template>

<script setup>
import {reactive, onMounted, ref, computed, watch} from "vue";
import {ElMessage, ElMessageBox, ElLoading} from "element-plus";
import { useI18n } from 'vue-i18n';
import {
  getApplications,
  approveApplication,
  rejectApplication,
  batchReview as batchReviewApi,
  batchReviewFailedExport
} from '@/api/admin';
import {useUserStore} from "@/stores/userStore.js";

const { t } = useI18n();

// const router=useRouter()

const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);
/** 是否为一审管理员（admin1 或旧编号 adm1） */
const isAdm1 = computed(() => {
  const n = (userNumber.value || '').toString().toLowerCase();
  return n === 'adm1' || n === 'admin1' || n === '22200214135';
});


const data=reactive({
  list:[]
})
const keyword = ref('');
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const loading = ref(false);
const selectedIds = ref([]);
const pageChanged = (newPage) => {
  page.value = newPage;
};

const onSelectionChange = (rows) => {
  selectedIds.value = (rows || []).map(r => r.id).filter(Boolean);
};

watch(page, (newValue, oldValue) => {
  if (oldValue !== newValue) {
    admin1_get_applications();
  }
});


// admin1_get_applications
const admin1_get_applications = async () => {
  loading.value = true;
  try {
    const response = await getApplications('adm1', { page: page.value, pageSize: pageSize.value });
    if (response.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }
    if (!response.data.status) {
      ElMessage.error(response.data.msg);
      return;
    }
    data.list = response.data.application_data;
    total.value = response.data.pages.total;  // 使用分页数据中的 total
  } catch (err) {
    console.error('Error:', err);
    ElMessage.error(t('approval.fetchFailed'));
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  if (isAdm1.value) {
    admin1_get_applications();
  } else {
    data.list = [];
    total.value = 0;
    ElMessage.warning(t('approval.notAdmin1'));
  }
});

const pass = async (row) => {
  try {
    await ElMessageBox.confirm(t('approval.confirmApprove'), t('approval.review'), {
      type: 'warning',
      confirmButtonText: t('approval.confirm'),
      cancelButtonText: t('approval.cancel')
    });

    const loadingInstance = ElLoading.service({
      lock: true,
      text: t('approval.processing'),
      background: 'rgba(0, 0, 0, 0.7)',
    });

    try {
      const requestData = {
        id: row.id,
        user_name: userName.value,
        user_number: userNumber.value
      };
      let passResult;
      if (isAdm1.value) {
        passResult = await approveApplication('adm1', requestData);
      } else {
        passResult = await approveApplication('adm2', requestData);
      }

      if (!passResult.data.status) {
        ElMessage.error(passResult.data.msg || t('approval.reviewFailed'));
        return;
      }
      ElMessage.success(t('approval.reviewPassed'));
      if (isAdm1.value) {
        await admin1_get_applications();
      } else {
        await admin2_get_applications();
      }
    } finally {
      loadingInstance.close();
    }
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('approval.operationFailed'));
    }
  }
};

const fail = async (row) => {
  try {
    await ElMessageBox.confirm(t('approval.confirmReject'), t('approval.review'), {
      type: 'warning',
      confirmButtonText: t('approval.confirm'),
      cancelButtonText: t('approval.cancel')
    });

    const requestData = {
      id: row.id,
      user_name: userName.value,
      user_number: userNumber.value
    };

    let failResult;
    if (isAdm1.value) {
      failResult = await rejectApplication('adm1', requestData);
    } else {
      failResult = await rejectApplication('adm2', requestData);
    }

    if (!failResult.data.status) {
      ElMessage.error(failResult.data.msg);
      return;
    }

    ElMessage.success(t('approval.operationSuccess'));
    if (isAdm1.value) {
      await admin1_get_applications();
    } else {
      await admin2_get_applications();
    }

  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error(t('approval.operationFailed'));
    }
  }
};

const exportBatchFailedCsv = async (failed) => {
  try {
    const response = await batchReviewFailedExport({ failed });
    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `batch_review_failed_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (_e) {
    ElMessage.warning(t('approval.exportFailed'));
  }
};

const batchReview = async (action) => {
  if (!selectedIds.value.length) {
    ElMessage.warning(t('approval.selectFirst'));
    return;
  }
  const stage = isAdm1.value ? 'adm1' : 'adm2';
  try {
    await ElMessageBox.confirm(
      t('approval.batchConfirm', { count: selectedIds.value.length, action: action === 'pass' ? t('approval.approve') : t('approval.reject') }),
      t('approval.batchReviewConfirm'),
      { type: 'warning', confirmButtonText: t('approval.confirm'), cancelButtonText: t('approval.cancel') }
    );
    const resp = await batchReviewApi({
      ids: selectedIds.value,
      stage,
      action,
      user_name: userName.value,
      user_number: userNumber.value
    });
    if (!resp.data?.status) {
      ElMessage.error(resp.data?.msg || t('approval.batchReviewFailed'));
      return;
    }
    const failed = resp.data?.data?.failed || [];
    ElMessage.success(resp.data.msg || t('approval.batchReviewComplete'));

    // 增量刷新：仅从当前列表移除成功项
    const successIds = new Set(resp.data?.data?.success_ids || []);
    data.list = (data.list || []).filter(item => !successIds.has(item.id));
    total.value = Math.max(0, total.value - successIds.size);
    selectedIds.value = [];

    if (failed.length > 0) {
      await ElMessageBox.confirm(
        t('approval.partialFail', { count: failed.length }),
        t('approval.partialFailTitle'),
        { type: 'warning', confirmButtonText: t('approval.export'), cancelButtonText: t('approval.later') }
      );
      await exportBatchFailedCsv(failed);
    }
  } catch (_e) {
    // ignore cancel
  }
};


</script>


<style scoped>
.approval-page {
  padding: 20px 24px;
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  margin-bottom: 20px;
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
.table-card {
  border-radius: 12px;
}
.batch-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.batch-tip {
  color: #6b7280;
  font-size: 13px;
}
.approval-table {
  width: 100%;
}
.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.view-pagination {
  margin-top: 0;
}
</style>
