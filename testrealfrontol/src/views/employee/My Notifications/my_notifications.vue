<template>
  <div class="notifications-page">
    <div class="page-header">
      <h1 class="page-title">我的个人消息</h1>
      <p class="page-desc">查看管理员发送给您的个人消息，可标记已读</p>
    </div>

    <el-card class="notify-card" shadow="hover">
      <div class="filter-bar">
        <el-radio-group v-model="unreadOnly" @change="fetchList">
          <el-radio-button :value="false">全部</el-radio-button>
          <el-radio-button :value="true">仅未读</el-radio-button>
        </el-radio-group>
        <el-button :icon="RefreshRight" circle @click="fetchList" :loading="loading" title="刷新" />
      </div>

      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column type="index" label="#" width="56" align="center" />
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip />
        <el-table-column prop="content" label="内容" min-width="280" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" width="172" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.read" type="info" size="small">已读</el-tag>
            <el-tag v-else type="warning" size="small">未读</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.read" link type="primary" @click="markRead(row)">标记已读</el-button>
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="total"
          :page-sizes="[10, 20, 50]"
          v-model:page-size="pageSize"
          v-model:current-page="currentPage"
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailVisible" :title="detailRow?.title" width="520px">
      <div class="detail-content">{{ detailRow?.content }}</div>
      <template #footer>
        <el-button v-if="detailRow && !detailRow.read" type="primary" @click="markRead(detailRow); detailVisible = false">标记已读</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { RefreshRight } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import Axios from '@/utils/Axios';

const loading = ref(false);
const list = ref([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);
const unreadOnly = ref(false);
const detailVisible = ref(false);
const detailRow = ref(null);

const fetchList = async () => {
  loading.value = true;
  try {
    const { data } = await Axios.get(`/api/employee/notifications`, {
      params: {
        page: currentPage.value,
        pageSize: pageSize.value,
        unread_only: unreadOnly.value
      }
    });
    if (data?.status && data?.data) {
      list.value = data.data.list || [];
      total.value = data.data.total ?? 0;
    } else {
      list.value = [];
      total.value = 0;
    }
  } catch (e) {
    ElMessage.error('获取通知失败');
    list.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

const markRead = async (row) => {
  try {
    await Axios.post(`/api/employee/notifications/${row.id}/read`);
    row.read = true;
    ElMessage.success('已标记为已读');
  } catch (e) {
    ElMessage.error('操作失败');
  }
};

const openDetail = (row) => {
  detailRow.value = row;
  detailVisible.value = true;
};

onMounted(fetchList);
</script>

<style scoped>
.notifications-page { padding: 24px; max-width: 1000px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 22px; font-weight: 600; color: #1f2937; margin: 0 0 8px 0; }
.page-desc { font-size: 14px; color: #6b7280; margin: 0; }
.notify-card { border-radius: 12px; overflow: hidden; }
.filter-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
.detail-content { white-space: pre-wrap; word-break: break-word; padding: 8px 0; }
</style>
