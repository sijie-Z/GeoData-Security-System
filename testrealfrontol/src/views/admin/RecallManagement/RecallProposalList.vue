<template>
  <div class="recall-list-page">
    <div class="page-header">
      <h1 class="page-title">数据回收审议</h1>
      <p class="page-desc">管理已批准数据的回收提议，投票决定是否收回数据</p>
    </div>

    <el-card class="filter-card" shadow="hover">
      <div class="filter-row">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 150px" @change="getProposals">
          <el-option label="投票中" value="voting" />
          <el-option label="已通过" value="approved" />
          <el-option label="已否决" value="rejected" />
        </el-select>
        <el-button type="primary" @click="openCreateDialog" v-if="canCreate">
          <el-icon><Plus /></el-icon>
          发起回收提议
        </el-button>
      </div>
    </el-card>

    <el-card class="table-card" shadow="hover">
      <el-table :data="proposals" v-loading="loading" stripe empty-text="暂无回收提议">
        <el-table-column prop="id" label="提议编号" width="90" />
        <el-table-column label="关联申请" width="100">
          <template #default="scope">
            <el-link type="primary" @click="viewApplication(scope.row.application_id)">
              #{{ scope.row.application_id }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="application_info.data_alias" label="数据名称" min-width="140" />
        <el-table-column prop="proposer_name" label="提议人" width="100" />
        <el-table-column label="投票进度" width="180">
          <template #default="scope">
            <div class="vote-progress">
              <el-tag type="success" size="small">支持: {{ scope.row.votes_for }}</el-tag>
              <el-tag type="danger" size="small">反对: {{ scope.row.votes_against }}</el-tag>
              <el-tag type="info" size="small">弃权: {{ scope.row.votes_abstain }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="180" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
            <el-button
              v-if="scope.row.status === 'voting' && scope.row.can_vote"
              size="small"
              type="primary"
              @click="openVoteDialog(scope.row)"
            >
              投票
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="prev, pager, next, total"
        @current-change="getProposals"
      />
    </div>

    <!-- Create Recall Dialog -->
    <el-dialog v-model="createDialogVisible" title="发起数据回收提议" width="550px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="100px">
        <el-form-item label="选择申请" prop="application_id">
          <el-select v-model="createForm.application_id" placeholder="选择已批准的申请" filterable style="width: 100%">
            <el-option
              v-for="app in approvedApps"
              :key="app.id"
              :label="`#${app.id} - ${app.data_alias} (${app.applicant_name})`"
              :value="app.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="回收原因" prop="reason">
          <el-input
            v-model="createForm.reason"
            type="textarea"
            :rows="4"
            placeholder="请详细说明回收原因（至少20字）"
            show-word-limit
            maxlength="500"
          />
        </el-form-item>
        <el-alert type="warning" :closable="false" show-icon>
          <template #title>
            提示：回收提议发起后，其他管理员将进行投票。若超过50%的管理员反对，数据将被收回，用户将无法继续下载。
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreate" :loading="createLoading">确认发起</el-button>
      </template>
    </el-dialog>

    <!-- Vote Dialog -->
    <el-dialog v-model="voteDialogVisible" title="投票" width="500px">
      <div class="vote-content">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="提议编号">#{{ currentProposal?.id }}</el-descriptions-item>
          <el-descriptions-item label="提议人">{{ currentProposal?.proposer_name }}</el-descriptions-item>
          <el-descriptions-item label="回收原因">{{ currentProposal?.reason }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <p class="vote-question">您是否支持回收该数据？</p>
        <div class="vote-buttons">
          <el-button type="success" size="large" @click="submitVote('for')">支持回收</el-button>
          <el-button type="danger" size="large" @click="submitVote('against')">反对回收</el-button>
          <el-button type="info" size="large" @click="submitVote('abstain')">弃权</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailDialogVisible" title="提议详情" width="650px">
      <div v-if="currentProposal">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="提议编号">#{{ currentProposal.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentProposal.status)">{{ currentProposal.status_text }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="提议人">{{ currentProposal.proposer_name }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ currentProposal.created_at }}</el-descriptions-item>
          <el-descriptions-item label="关联申请">#{{ currentProposal.application_id }}</el-descriptions-item>
          <el-descriptions-item label="数据名称">{{ currentProposal.application_info?.data_alias }}</el-descriptions-item>
          <el-descriptions-item label="回收原因" :span="2">{{ currentProposal.reason }}</el-descriptions-item>
        </el-descriptions>
        <el-divider content-position="left">投票情况</el-divider>
        <div class="vote-summary">
          <div class="vote-item">
            <span class="vote-label">支持回收:</span>
            <span class="vote-count success">{{ currentProposal.votes_for }}</span>
          </div>
          <div class="vote-item">
            <span class="vote-label">反对回收:</span>
            <span class="vote-count danger">{{ currentProposal.votes_against }}</span>
          </div>
          <div class="vote-item">
            <span class="vote-label">弃权:</span>
            <span class="vote-count info">{{ currentProposal.votes_abstain }}</span>
          </div>
        </div>
        <div v-if="Object.keys(currentProposal.votes_json || {}).length > 0" class="vote-details">
          <el-divider content-position="left">投票详情</el-divider>
          <el-table :data="formatVotes(currentProposal.votes_json)" size="small">
            <el-table-column prop="name" label="投票人" />
            <el-table-column label="投票结果">
              <template #default="scope">
                <el-tag :type="scope.row.voteType" size="small">{{ scope.row.voteText }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
import axios from '@/utils/Axios';
import { useUserStore } from '@/stores/userStore';

const userStore = useUserStore();

const proposals = ref([]);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const loading = ref(false);
const statusFilter = ref('');

const createDialogVisible = ref(false);
const voteDialogVisible = ref(false);
const detailDialogVisible = ref(false);
const createLoading = ref(false);
const createFormRef = ref(null);
const currentProposal = ref(null);

const approvedApps = ref([]);
const createForm = reactive({
  application_id: null,
  reason: ''
});

const createRules = {
  application_id: [{ required: true, message: '请选择申请', trigger: 'change' }],
  reason: [{ required: true, min: 20, message: '回收原因至少需要20个字符', trigger: 'blur' }]
};

const canCreate = computed(() => userStore.currentUser?.role === 'admin');

const getStatusType = (status) => {
  const map = { voting: 'warning', approved: 'success', rejected: 'info', cancelled: 'danger' };
  return map[status] || 'info';
};

const getProposals = async () => {
  loading.value = true;
  try {
    const params = { page: page.value, pageSize: pageSize.value };
    if (statusFilter.value) params.status = statusFilter.value;
    const resp = await axios.get('/api/recall/list', { params });
    if (resp.data?.status) {
      proposals.value = resp.data.data.list || [];
      total.value = resp.data.data.total || 0;
    }
  } catch (err) {
    ElMessage.error('获取列表失败');
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = async () => {
  createForm.application_id = null;
  createForm.reason = '';
  // Get approved applications
  try {
    const resp = await axios.get('/api/adm2_get_approved', { params: { pageSize: 100 } });
    if (resp.data?.status) {
      approvedApps.value = resp.data.approved_application_data || [];
    }
  } catch (err) {
    ElMessage.error('获取申请列表失败');
  }
  createDialogVisible.value = true;
};

const submitCreate = async () => {
  await createFormRef.value?.validate();
  createLoading.value = true;
  try {
    const resp = await axios.post('/api/recall/create', createForm);
    if (resp.data?.status) {
      ElMessage.success('回收提议已发起');
      createDialogVisible.value = false;
      getProposals();
    } else {
      ElMessage.error(resp.data?.msg || '发起失败');
    }
  } catch (err) {
    ElMessage.error('发起失败');
  } finally {
    createLoading.value = false;
  }
};

const openVoteDialog = (row) => {
  currentProposal.value = row;
  voteDialogVisible.value = true;
};

const submitVote = async (voteType) => {
  try {
    const resp = await axios.post(`/api/recall/${currentProposal.value.id}/vote`, { vote: voteType });
    if (resp.data?.status) {
      ElMessage.success(resp.data.msg);
      voteDialogVisible.value = false;
      getProposals();
    } else {
      ElMessage.error(resp.data?.msg || '投票失败');
    }
  } catch (err) {
    ElMessage.error('投票失败');
  }
};

const viewDetail = async (row) => {
  try {
    const resp = await axios.get(`/api/recall/${row.id}`);
    if (resp.data?.status) {
      currentProposal.value = resp.data.data;
      detailDialogVisible.value = true;
    }
  } catch (err) {
    ElMessage.error('获取详情失败');
  }
};

const viewApplication = (appId) => {
  // Navigate to application detail or show modal
  ElMessage.info(`查看申请 #${appId}`);
};

const formatVotes = (votesJson) => {
  return Object.entries(votesJson || {}).map(([number, data]) => ({
    number,
    name: data.name || number,
    vote: data.vote,
    voteText: { for: '支持', against: '反对', abstain: '弃权' }[data.vote] || data.vote,
    voteType: { for: 'success', against: 'danger', abstain: 'info' }[data.vote] || 'info'
  }));
};

onMounted(() => {
  getProposals();
});
</script>

<style scoped>
.recall-list-page { padding: 20px 24px; }
.page-header { margin-bottom: 16px; }
.page-title { margin: 0 0 8px; font-size: 22px; color: #1f2937; }
.page-desc { margin: 0; color: #6b7280; }
.filter-card { margin-bottom: 16px; border-radius: 12px; }
.filter-row { display: flex; justify-content: space-between; align-items: center; }
.table-card { border-radius: 12px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
.vote-progress { display: flex; gap: 6px; flex-wrap: wrap; }
.vote-content { padding: 16px 0; }
.vote-question { font-size: 16px; font-weight: 500; text-align: center; margin: 20px 0; }
.vote-buttons { display: flex; justify-content: center; gap: 16px; }
.vote-summary { display: flex; justify-content: center; gap: 32px; margin: 16px 0; }
.vote-item { text-align: center; }
.vote-label { font-size: 14px; color: #6b7280; }
.vote-count { font-size: 24px; font-weight: 600; display: block; }
.vote-count.success { color: #10b981; }
.vote-count.danger { color: #ef4444; }
.vote-count.info { color: #6b7280; }
</style>
