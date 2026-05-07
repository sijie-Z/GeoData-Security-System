<template>
  <div class="admin-application-page">
    <div class="page-header">
      <h1 class="page-title">申请成为管理员</h1>
      <p class="page-desc">申请获得管理员权限，参与系统管理和数据审批</p>
    </div>

    <el-card class="eligibility-card" shadow="hover" v-loading="checkingEligibility">
      <div class="eligibility-content" v-if="eligibility">
        <div v-if="eligibility.eligible" class="eligible">
          <el-icon class="success-icon"><CircleCheckFilled /></el-icon>
          <div class="eligibility-text">
            <h3>您符合申请条件</h3>
            <p>已注册 {{ eligibility.days_registered }} 天，可以提交管理员申请</p>
          </div>
        </div>
        <div v-else class="not-eligible">
          <el-icon class="warning-icon"><WarningFilled /></el-icon>
          <div class="eligibility-text">
            <h3>暂不符合申请条件</h3>
            <p>{{ eligibility.reason }}</p>
            <p v-if="eligibility.days_needed">还需等待 {{ eligibility.days_needed }} 天</p>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Application Form -->
    <el-card class="form-card" shadow="hover" v-if="eligibility?.eligible">
      <template #header>
        <span>填写申请信息</span>
      </template>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="申请原因" prop="reason">
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="6"
            placeholder="请详细说明您申请成为管理员的原因（至少50字）"
            show-word-limit
            maxlength="1000"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="submitApplication" :loading="submitting">
            提交申请
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- My Applications History -->
    <el-card class="history-card" shadow="hover">
      <template #header>
        <span>我的申请记录</span>
      </template>
      <el-table :data="myApplications" v-loading="loadingHistory" empty-text="暂无申请记录">
        <el-table-column prop="id" label="申请编号" width="100" />
        <el-table-column prop="status_text" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="approval_ratio" label="支持率" width="100">
          <template #default="scope">
            <span>{{ scope.row.approval_ratio }}%</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_votes" label="投票数" width="100" />
        <el-table-column prop="created_at" label="申请时间" width="160" />
        <el-table-column prop="reason" label="申请原因" min-width="200" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { CircleCheckFilled, WarningFilled } from '@element-plus/icons-vue';
import axios from '@/utils/Axios';

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
  reason: [{ required: true, min: 50, message: '申请原因至少需要50个字符', trigger: 'blur' }]
};

const getStatusType = (status) => {
  const map = { pending: 'info', voting: 'warning', approved: 'success', rejected: 'danger' };
  return map[status] || 'info';
};

const checkEligibility = async () => {
  checkingEligibility.value = true;
  try {
    const resp = await axios.get('/api/admin-application/eligibility');
    if (resp.data?.status) {
      eligibility.value = resp.data.data;
    }
  } catch (err) {
    ElMessage.error('检查资格失败');
  } finally {
    checkingEligibility.value = false;
  }
};

const getMyApplications = async () => {
  loadingHistory.value = true;
  try {
    const resp = await axios.get('/api/admin-application/my');
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
    const resp = await axios.post('/api/admin-application/submit', form);
    if (resp.data?.status) {
      ElMessage.success('申请已提交，请等待管理员审核');
      form.reason = '';
      getMyApplications();
    } else {
      ElMessage.error(resp.data?.msg || '提交失败');
    }
  } catch (err) {
    ElMessage.error('提交失败');
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
