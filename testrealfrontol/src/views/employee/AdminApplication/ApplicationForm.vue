<template>
  <div class="admin-application-page">
    <div class="page-header">
      <h1 class="page-title">{{ $t('empAdminApp.title') }}</h1>
      <p class="page-desc">{{ $t('empAdminApp.description') }}</p>
    </div>

    <el-card class="eligibility-card" shadow="hover" v-loading="checkingEligibility">
      <div class="eligibility-content" v-if="eligibility">
        <div v-if="eligibility.eligible" class="eligible">
          <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
          <div class="eligibility-text">
            <h3>{{ $t('empAdminApp.eligible') }}</h3>
            <p>{{ $t('empAdminApp.daysRegistered', { days: eligibility.days_registered }) }}</p>
          </div>
        </div>
        <div v-else class="not-eligible">
          <el-icon class="warning-icon"><WarningFilled /></el-icon>
          <div class="eligibility-text">
            <h3>{{ $t('empAdminApp.notEligible') }}</h3>
            <p>{{ eligibility.reason }}</p>
            <p v-if="eligibility.days_needed">{{ $t('empAdminApp.daysNeeded', { days: eligibility.days_needed }) }}</p>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Application Form -->
    <el-card class="form-card" shadow="hover" v-if="eligibility?.eligible">
      <template #header>
        <span>{{ $t('empAdminApp.fillForm') }}</span>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item :label="$t('empAdminApp.reasonLabel')" prop="reason">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="6"
            :placeholder="$t('empAdminApp.reasonPlaceholder')"
            show-word-limit
            maxlength="1000"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submitApplication" :loading="submitting">
            {{ $t('empAdminApp.submit') }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- My Applications History -->
    <el-card class="history-card" shadow="hover">
      <template #header>
        <span>{{ $t('empAdminApp.myApplications') }}</span>
      </template>
      <el-table :data="myApplications" v-loading="loadingHistory" :empty-text="$t('empAdminApp.noApplications')">
        <el-table-column prop="id" :label="$t('empAdminApp.applicationId')" width="100" />
        <el-table-column prop="status_text" :label="$t('empAdminApp.status')" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="approval_ratio" :label="$t('empAdminApp.approvalRatio')" width="100">
          <template #default="scope">
            <span>{{ scope.row.approval_ratio }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_votes" :label="$t('empAdminApp.totalVotes')" width="100" />
        <el-table-column prop="created_at" :label="$t('empAdminApp.applicationTime')" width="160" />
        <el-table-column prop="reason" :label="$t('empAdminApp.reasonColumn')" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue';
import { checkAdminApplicationEligibility, getMyAdminApplications, submitAdminApplication } from '@/api/admin';

const { t } = useI18n();

const checkingEligibility = ref(true);
const eligibility = ref(null);
const submitting = ref(false);
const loadingHistory = ref(false);
const formRef = ref(null);
const myApplications = ref([]);

const form = reactive({
  reason: ''
});

const rules = {
  reason: [{ required: true, min: 50, message: t('empAdminApp.reasonMinLength'), trigger: 'blur' }]
};

const getStatusType = (status) => {
  const map = { pending: 'info', voting: 'warning', approved: 'success', rejected: 'danger' };
  return map[status] || 'info';
};

const checkEligibility = async () => {
  checkingEligibility.value = true;
  try {
    const resp = await checkAdminApplicationEligibility();
    if (resp.data?.status) {
      eligibility.value = resp.data.data;
    }
  } catch (err) {
    ElMessage.error(t('empAdminApp.checkFailed'));
  } finally {
    checkingEligibility.value = false;
  }
};

const getMyApplications = async () => {
  loadingHistory.value = true;
  try {
    const resp = await getMyAdminApplications();
    if (resp.data?.status) {
      myApplications.value = resp.data.data || [];
    }
  } catch (err) {
    console.error('获取申请记录失败');
  } finally {
    loadingHistory.value = false;
  }
};

const submitApplication = async () => {
  await formRef.value?.validate();
  submitting.value = true;
  try {
    const resp = await submitAdminApplication(form);
    if (resp.data?.status) {
      ElMessage.success(t('empAdminApp.submitSuccess'));
      form.reason = '';
      getMyApplications();
    } else {
      ElMessage.error(resp.data?.msg || t('empAdminApp.submitFailed'));
    }
  } catch (err) {
    ElMessage.error(t('empAdminApp.submitFailed'));
  } finally {
    submitting.value = false;
  }
};

onMounted(() => {
  checkEligibility();
  getMyApplications();
});
</script>

<style scoped>
.admin-application-page { padding: 20px 24px; max-width: 900px; margin: 0 auto; }
.page-header { margin-bottom: 20px; }
.page-title { margin: 0 0 8px; font-size: 22px; color: #1f2937; }
.page-desc { margin: 0; color: #6b7280; }
.eligibility-card, .form-card, .history-card { border-radius: 12px; margin-bottom: 20px; }
.eligibility-content { padding: 12px 0; }
.eligible, .not-eligible { display: flex; align-items: center; gap: 16px; }
.success-icon { font-size: 48px; color: #10b981; }
.warning-icon { font-size: 48px; color: #f59e0b; }
.eligibility-text h3 { margin: 0 0 8px; font-size: 18px; }
.eligibility-text p { margin: 0; color: #6b7280; }
</style>
