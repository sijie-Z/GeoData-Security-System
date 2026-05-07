<template>
  <div class="admin-app-voting-page">
    <div class="page-header">
      <h1 class="page-title">管理员申请审批</h1>
      <p class="page-desc">审核员工申请成为管理员的请求</p>
    </div>

    <el-card class="table-card" shadow="hover">
      <el-table :data="applications" v-loading="loading" stripe empty-text="暂无待审核申请">
        <el-table-column prop="id" label="申请编号" width="90" />
        <el-table-column prop="employee_name" label="申请人" width="120" />
        <el-table-column prop="employee_number" label="员工编号" width="140" />
        <el-table-column label="投票进度" width="180">
          <template #default="scope">
            <div class="vote-progress">
              <span class="progress-text">
                {{ scope.row.approve_votes }}/{{ scope.row.total_votes }} 票
              </span>
              <el-progress
                :percentage="scope.row.approval_ratio"
                :status="scope.row.approval_ratio >= 66 ? 'success' : ''"
                :stroke-width="8"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="160" />
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="viewDetail(scope.row)">详情</el-button>
            <el-button
              v-if="scope.row.can_vote"
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
        @current-change="getApplications"
      />
    </div>

    <!-- Detail Dialog -->
    <el-dialog v-model="detailDialogVisible" title="申请详情" width="600px">
      <div v-if="currentApp">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="申请编号">#{{ currentApp.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentApp.status)">{{ currentApp.status_text }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="申请人">{{ currentApp.employee_name }}</el-descriptions-item>
          <el-descriptions-item label="员工编号">{{ currentApp.employee_number }}</el-descriptions-item>
          <el-descriptions-item label="申请时间">{{ currentApp.created_at }}</el-descriptions-item>
          <el-descriptions-item label="投票进度">
            {{ currentApp.approve_votes }}/{{ currentApp.total_votes }} ({{ currentApp.approval_ratio }}%)
          </el-descriptions-item>
          <el-descriptions-item label="申请原因" :span="2">{{ currentApp.reason }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="currentApp.employee_info" class="employee-extra">
          <el-divider content-position="left">员工信息</el-divider>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="注册时间">{{ currentApp.employee_info.create_time }}</el-descriptions-item>
            <el-descriptions-item label="联系电话">{{ currentApp.employee_info.phone_number }}</el-descriptions-item>
          </el-descriptions>
        </div>
        <div v-if="Object.keys(currentApp.votes_json || {}).length > 0">
          <el-divider content-position="left">投票详情</el-divider>
          <el-table :data="formatVotes(currentApp.votes_json)" size="small">
            <el-table-column prop="name" label="投票人" />
            <el-table-column label="投票结果">
              <template #default="scope">
                <el-tag :type="scope.row.voteType" size="small">{{ scope.row.voteText }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="comment" label="备注" show-overflow-tooltip />
          </el-table>
        </div>
      </div>
    </el-dialog>

    <!-- Vote Dialog -->
    <el-dialog v-model="voteDialogVisible" title="投票" width="500px">
      <div class="vote-content">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="申请人">{{ currentApp?.employee_name }}</el-descriptions-item>
          <el-descriptions-item label="员工编号">{{ currentApp?.employee_number }}</el-descriptions-item>
          <el-descriptions-item label="申请原因">{{ currentApp?.reason }}</el-descriptions-item>
        </el-descriptions>
        <el-divider />
        <el-form :model="voteForm" label-width="80px">
          <el-form-item label="您的决定">
            <el-radio-group v-model="voteForm.approve">
              <el-radio :label="true">同意</el-radio>
              <el-radio :label="false">拒绝</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="voteForm.comment" type="textarea" :rows="2" placeholder="可选备注" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="voteDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitVote" :loading="voting">确认投票</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import axios from '@/utils/Axios';

const applications = ref([]);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const loading = ref(false);
const voting = ref(false);
const detailDialogVisible = ref(false);
const voteDialogVisible = ref(false);
const currentApp = ref(null);

const voteForm = reactive({
  approve: true,
  comment: ''
});

const getStatusType = (status) => {
  const map = { pending: 'info', voting: 'warning', approved: 'success', rejected: 'danger' };
  return map[status] || 'info';
};

const getApplications = async () => {
  loading.value = true;
  try {
    const resp = await axios.get('/api/admin-application/list', {
      params: { page: page.value, pageSize: pageSize.value }
    });
    if (resp.data?.status) {
      applications.value = resp.data.data.list || [];
      total.value = resp.data.data.total || 0;
    }
  } catch (err) {
    ElMessage.error('获取列表失败');
  } finally {
    loading.value = false;
  }
};

const viewDetail = async (row) => {
  try {
    const resp = await axios.get(`/api/admin-application/${row.id}`);
    if (resp.data?.status) {
      currentApp.value = resp.data.data;
      detailDialogVisible.value = true;
    }
  } catch (err) {
    ElMessage.error('获取详情失败');
  }
};

const openVoteDialog = async (row) => {
  try {
    const resp = await axios.get(`/api/admin-application/${row.id}`);
    if (resp.data?.status) {
      currentApp.value = resp.data.data;
      voteForm.approve = true;
      voteForm.comment = '';
      voteDialogVisible.value = true;
    }
  } catch (err) {
    ElMessage.error('获取详情失败');
  }
};

const submitVote = async () => {
  voting.value = true;
  try {
    const resp = await axios.post(`/api/admin-application/${currentApp.value.id}/vote`, voteForm);
    if (resp.data?.status) {
      ElMessage.success(resp.data.msg);
      voteDialogVisible.value = false;
      getApplications();
    } else {
      ElMessage.error(resp.data?.msg || '投票失败');
    }
  } catch (err) {
    ElMessage.error('投票失败');
  } finally {
    voting.value = false;
  }
};

const formatVotes = (votesJson) => {
  return Object.entries(votesJson || {}).map(([number, data]) => ({
    number,
    name: data.name || number,
    approve: data.approve,
    comment: data.comment || '',
    voteText: data.approve ? '同意' : '拒绝',
    voteType: data.approve ? 'success' : 'danger'
  }));
};

onMounted(() => {
  getApplications();
});
</script>

<style scoped>
.admin-app-voting-page { padding: 20px 24px; }
.page-header { margin-bottom: 16px; }
.page-title { margin: 0 0 8px; font-size: 22px; color: #1f2937; }
.page-desc { margin: 0; color: #6b7280; }
.table-card { border-radius: 12px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
.vote-progress { display: flex; flex-direction: column; gap: 4px; }
.progress-text { font-size: 12px; color: #6b7280; }
.vote-content { padding: 8px 0; }
.employee-extra { margin-top: 16px; }
</style>
