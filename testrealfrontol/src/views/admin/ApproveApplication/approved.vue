<template>
  <div class="approval-page">
    <PageHeader :title="$t('approval.secondReviewTitle')" :subtitle="$t('approval.secondReviewDescription')" />

    <el-card class="table-card" shadow="hover">
      <ListShell
        :empty="!loading && filteredList.length === 0"
        :empty-variant="filters.keyword ? 'filtered' : 'never'"
        :empty-title="$t('approval.noSecondReview')"
        :empty-description="$t('common.noDataDesc')"
        :pagination="{ page, pageSize, total, layout: 'prev, pager, next, jumper, total' }"
        @page-change="pageChanged"
      >
        <template #filters>
          <el-input v-model="filters.keyword" :placeholder="$t('approval.searchPlaceholder')" clearable style="width: 300px;" />
        </template>

        <el-table :data="filteredList" border stripe v-loading="loading" class="approval-table">
          <el-table-column prop="id" :label="$t('approval.applyId')" width="90" align="center" />
          <el-table-column prop="data_alias" :label="$t('approval.dataName')" min-width="140" show-overflow-tooltip />
          <el-table-column prop="data_id" :label="$t('approval.dataId')" width="100" align="center" />
          <el-table-column prop="applicant_user_number" :label="$t('approval.applicantId')" width="130" align="center" />
          <el-table-column prop="applicant_name" :label="$t('approval.applicantName')" width="110" align="center" />
          <el-table-column prop="reason" :label="$t('approval.applyReason')" min-width="180" show-overflow-tooltip />

          <el-table-column :label="$t('approval.firstReviewStatus')" width="100" align="center">
            <template #default="scope">
              {{ getStatusText(scope.row.first_statu) }}
            </template>
          </el-table-column>

          <el-table-column :label="$t('approval.operation')" width="230" align="center" fixed="right">
            <template #default="scope">
              <el-button size="small" type="primary" @click="review(scope.row, true)">{{ $t('approval.secondReviewApprove') }}</el-button>
              <el-button size="small" @click="review(scope.row, false)">{{ $t('approval.secondReviewReject') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </ListShell>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, onMounted, ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from 'vue-i18n';
import { getApprovedApplications, reReview } from '@/api/admin';
import { useUserStore } from "@/stores/userStore.js";
import ListShell from '@/components/common/ListShell.vue';
import PageHeader from '@/components/common/PageHeader.vue';

const { t } = useI18n();

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
  if (status === true) return t('approval.passed');
  if (status === false) return t('approval.failed');
  if (status === null || status === undefined) return t('approval.pending');
  return '';
};

const admin2_get_approved = async () => {
  loading.value = true;
  try {
    const response = await getApprovedApplications({ page: page.value, pageSize: pageSize.value });
    if (!response.data?.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data?.msg || t('approval.fetchFailed'));
      return;
    }
    data.list = response.data.approved_application_data || [];
    total.value = response.data.pages?.total ?? 0;
  } catch (err) {
    ElMessage.error(t('approval.fetchFailed'));
  } finally {
    loading.value = false;
  }
};

const review = async (row, pass) => {
  if (!isAdm2.value) {
    ElMessage.error(t('approval.notAdmin2'));
    return;
  }
  try {
    await ElMessageBox.confirm(t('approval.secondReviewConfirm', { id: row.id, action: pass ? t('approval.approve') : t('approval.reject') }), t('approval.secondReview'), {
      type: 'warning',
      confirmButtonText: t('approval.confirm'),
      cancelButtonText: t('approval.cancel')
    });
    const resp = await reReview({
      id: row.id,
      stage: 'adm2',
      statu: pass,
      user_name: userName.value,
      user_number: userNumber.value
    });
    if (!resp.data?.status) {
      ElMessage.error(resp.data?.msg || t('approval.secondReviewFailed'));
      return;
    }
    ElMessage.success(t('approval.secondReviewSubmitted'));
    await admin2_get_approved();
  } catch (_e) {
    // cancel ignore
  }
};

onMounted(() => {
  if (!isAdm2.value) {
    data.list = [];
    total.value = 0;
    ElMessage.warning(t('approval.notAdmin2Warning'));
    return;
  }
  admin2_get_approved();
});
</script>

<style scoped>
.approval-page { padding: 20px 24px; max-width: 1200px; margin: 0 auto; }
.table-card { border-radius: 12px; }
.approval-table { width: 100%; }
</style>
