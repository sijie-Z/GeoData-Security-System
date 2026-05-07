<template>
  <div class="approval-page">
    <div class="page-header">
      <h1 class="page-title">待一审申请</h1>
      <p class="page-desc">仅管理员1处理的一审申请列表，通过或不通过后将从本列表移除。</p>
    </div>

    <el-card class="table-card" shadow="hover">
      <div class="batch-toolbar" v-if="isAdm1">
        <el-button size="small" type="primary" :disabled="selectedIds.length===0" @click="batchReview('pass')">批量通过</el-button>
        <el-button size="small" :disabled="selectedIds.length===0" @click="batchReview('fail')">批量不通过</el-button>
        <span class="batch-tip">已选 {{ selectedIds.length }} 条</span>
      </div>
      <el-table :data="data.list" border stripe v-loading="loading" class="approval-table" empty-text="暂无待审批申请" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column prop="id" label="申请编号" width="90" align="center" />
        <el-table-column prop="data_alias" label="数据名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="data_id" label="数据编号" width="100" align="center" />
        <el-table-column prop="applicant_user_number" label="申请人编号" width="110" align="center" />
        <el-table-column prop="applicant_name" label="申请人姓名" width="100" align="center" />
        <el-table-column prop="reason" label="申请理由" min-width="160" show-overflow-tooltip />

        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" @click="pass(scope.row)">通过</el-button>
            <el-button size="small" @click="fail(scope.row)">不通过</el-button>
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
// import {useRouter} from "vue-router";
import axios from '@/utils/Axios';
import {useUserStore} from "@/stores/userStore.js";



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
    const response = await axios.get(`/api/adm1_get_applications`, {
      params: { page: page.value, pageSize: pageSize.value }
    });
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
    ElMessage.error('获取记录失败');
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
    ElMessage.warning('当前账号不是管理员1，待一审页不可操作');
  }
});

const pass = async (row) => {
  try {
    await ElMessageBox.confirm("确定通过?", '审批', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    });
    
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '正在处理，请稍候...',
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
        passResult = await axios.post(`/api/adm1_pass`, requestData);
      } else {
        passResult = await axios.post(`/api/adm2_pass`, requestData);
      }
      
      if (!passResult.data.status) {
        ElMessage.error(passResult.data.msg || '审核失败');
        return;
      }
      ElMessage.success('审核通过并已自动生成嵌入文件');
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
      ElMessage.error('操作失败');
    }
  }
};

const fail = async (row) => {
  try {
    await ElMessageBox.confirm("确定不通过?", '审批', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    });

    const requestData = {
      id: row.id,
      user_name: userName.value,
      user_number: userNumber.value
    };

    let failResult;
    if (isAdm1.value) {
      failResult = await axios.post(`/api/adm1_fail`, requestData);
    } else {
      failResult = await axios.post(`/api/adm2_fail`, requestData);
    }

    if (!failResult.data.status) {
      ElMessage.error(failResult.data.msg);
      return;
    }

    ElMessage.success('操作成功');
    if (isAdm1.value) {
      await admin1_get_applications();
    } else {
      await admin2_get_applications();
    }

  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('操作失败');
    }
  }
};

const exportBatchFailedCsv = async (failed) => {
  try {
    const response = await axios.post(
      `/api/admin/batch_review_failed_export`,
      { failed },
      { responseType: 'blob' }
    );
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
    ElMessage.warning('失败清单导出失败，可稍后重试');
  }
};

const batchReview = async (action) => {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先选择要处理的申请');
    return;
  }
  const stage = isAdm1.value ? 'adm1' : 'adm2';
  try {
    await ElMessageBox.confirm(
      `确认将选中的 ${selectedIds.value.length} 条申请批量${action === 'pass' ? '通过' : '不通过'}？`,
      '批量审批确认',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
    );
    const resp = await axios.post(`/api/admin/batch_review`, {
      ids: selectedIds.value,
      stage,
      action,
      user_name: userName.value,
      user_number: userNumber.value
    });
    if (!resp.data?.status) {
      ElMessage.error(resp.data?.msg || '批量审批失败');
      return;
    }
    const failed = resp.data?.data?.failed || [];
    ElMessage.success(resp.data.msg || '批量审批完成');

    // 增量刷新：仅从当前列表移除成功项
    const successIds = new Set(resp.data?.data?.success_ids || []);
    data.list = (data.list || []).filter(item => !successIds.has(item.id));
    total.value = Math.max(0, total.value - successIds.size);
    selectedIds.value = [];

    if (failed.length > 0) {
      await ElMessageBox.confirm(
        `有 ${failed.length} 条处理失败，是否导出失败清单？`,
        '批量审批部分失败',
        { type: 'warning', confirmButtonText: '导出', cancelButtonText: '稍后' }
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
