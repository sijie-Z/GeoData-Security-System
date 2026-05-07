<template>
  <div class="approval-page">
    <div class="page-header">
      <h1 class="page-title">待二审申请</h1>
      <p class="page-desc">仅管理员2处理：显示一审已通过、二审待处理记录。</p>
    </div>

    <el-card class="table-card" shadow="hover">
      <div class="toolbar">
        <el-input v-model="filters.keyword" placeholder="按申请编号/数据名/申请人搜索" clearable style="width: 300px;" />
      </div>

      <el-table :data="filteredList" border stripe v-loading="loading" class="approval-table" empty-text="暂无待二审记录">
        <el-table-column prop="id" label="申请编号" width="90" align="center" />
        <el-table-column prop="data_alias" label="数据名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="data_id" label="数据编号" width="100" align="center" />
        <el-table-column prop="applicant_user_number" label="申请人编号" width="130" align="center" />
        <el-table-column prop="applicant_name" label="申请人姓名" width="110" align="center" />
        <el-table-column prop="reason" label="申请理由" min-width="180" show-overflow-tooltip />

        <el-table-column label="一审状态" width="100" align="center">
          <template #default="scope">
            {{ getStatusText(scope.row.first_statu) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="230" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" type="primary" @click="review(scope.row, true)">二审通过</el-button>
            <el-button size="small" @click="review(scope.row, false)">二审不通过</el-button>
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
import { reactive, onMounted, ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import axios from '@/utils/Axios';
import { useUserStore } from "@/stores/userStore.js";

const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);

const isAdm2 = computed(() => {
  const n = (userNumber.value || '').toString().toLowerCase();
  return n === 'adm2' || n === 'admin2' || n === '33300214135';
});

const data = reactive({ list: [] });
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const loading = ref(false);
const filters = reactive({ keyword: '' });

const filteredList = computed(() => {
  const kw = (filters.keyword || '').trim().toLowerCase();
  if (!kw) return data.list || [];
  return (data.list || []).filter((row) => {
    const text = `${row.id ?? ''} ${row.data_alias ?? ''} ${row.applicant_name ?? ''} ${row.applicant_user_number ?? ''}`.toLowerCase();
    return text.includes(kw);
  });
});

const pageChanged = (newPage) => {
  page.value = newPage;
};

watch(page, (newValue, oldValue) => {
  if (oldValue !== newValue) admin2_get_approved();
});

const getStatusText = (status) => {
  if (status === true) return '通过';
  if (status === false) return '不通过';
  if (status === null || status === undefined) return '待审核';
  return '';
};

const admin2_get_approved = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`/api/adm2_get_approved`, {
      params: { page: page.value, pageSize: pageSize.value }
    });
    if (!response.data?.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data?.msg || '获取记录失败');
      return;
    }
    data.list = response.data.approved_application_data || [];
    total.value = response.data.pages?.total ?? 0;
  } catch (err) {
    ElMessage.error('获取记录失败');
  } finally {
    loading.value = false;
  }
};

const review = async (row, pass) => {
  if (!isAdm2.value) {
    ElMessage.error('仅管理员2可执行二审');
    return;
  }
  try {
    await ElMessageBox.confirm(`确认将申请 ${row.id} 二审${pass ? '通过' : '不通过'}？`, '二审确认', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    });
    const resp = await axios.post(`/api/admin/re_review`, {
      id: row.id,
      stage: 'adm2',
      statu: pass,
      user_name: userName.value,
      user_number: userNumber.value
    });
    if (!resp.data?.status) {
      ElMessage.error(resp.data?.msg || '二审失败');
      return;
    }
    ElMessage.success('二审结果已提交');
    await admin2_get_approved();
  } catch (_e) {
    // cancel ignore
  }
};

onMounted(() => {
  if (!isAdm2.value) {
    data.list = [];
    total.value = 0;
    ElMessage.warning('当前账号不是管理员2，待二审页不可操作');
    return;
  }
  admin2_get_approved();
});
</script>

<style scoped>
.approval-page { padding: 20px 24px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 600; color: #1f2937; margin: 0 0 8px 0; }
.page-desc { font-size: 14px; color: #6b7280; margin: 0; }
.table-card { border-radius: 12px; }
.toolbar { display: flex; margin-bottom: 12px; }
.approval-table { width: 100%; }
.pagination-wrap { margin-top: 20px; display: flex; justify-content: flex-end; }
.view-pagination { margin-top: 0; }
</style>
