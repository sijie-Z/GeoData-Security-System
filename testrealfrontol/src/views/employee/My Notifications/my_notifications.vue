<template>
  <div class="notifications-page">
    <div class="page-header">
      <h1 class="page-title">{{ $t('empNotify.title') }}</h1>
      <p class="page-desc">{{ $t('empNotify.description') }}</p>
    </div>

    <el-card class="notify-card" shadow="hover">
      <div class="filter-bar">
        <el-radio-group v-model="unreadOnly" @change="fetchList">
          <el-radio-button :value="false">{{ $t('empNotify.all') }}</el-radio-button>
          <el-radio-button :value="true">{{ $t('empNotify.unreadOnly') }}</el-radio-button>
        </el-radio-group>
        <el-button :icon="RefreshRight" circle @click="fetchList" :loading="loading" title="刷新" />
      </div>

      <el-table :data="list" v-loading="loading" border stripe>
        <el-table-column type="index" label="#" width="56" align="center" />
        <el-table-column prop="title" :label="$t('empNotify.titleColumn')" min-width="180" show-overflow-tooltip />
        <el-table-column prop="content" :label="$t('empNotify.contentColumn')" min-width="280" show-overflow-tooltip />
        <el-table-column prop="created_at" :label="$t('empNotify.timeColumn')" width="172" />
        <el-table-column :label="$t('empNotify.statusColumn')" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.read" type="info" size="small">{{ $t('empNotify.read') }}</el-tag>
            <el-tag v-else type="warning" size="small">{{ $t('empNotify.unread') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('empNotify.actionColumn')" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.read" link type="primary" @click="markRead(row)">{{ $t('empNotify.markRead') }}</el-button>
            <el-button link type="primary" @click="openDetail(row)">{{ $t('empNotify.detail') }}</el-button>
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
        <el-button v-if="detailRow && !detailRow.read" type="primary" @click="markRead(detailRow); detailVisible = false">{{ $t('empNotify.markRead') }}</el-button>
        <el-button @click="detailVisible = false">{{ $t('empNotify.close') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { RefreshRight } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { getNotifications, markNotificationRead as markNotificationReadApi } from '@/api/employee';

const { t } = useI18n();

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
    const { data } = await getNotifications({
      page: currentPage.value,
      pageSize: pageSize.value,
      unread_only: unreadOnly.value
    });
    if (data?.status && data?.data) {
      list.value = data.data.list || [];
      total.value = data.data.total ?? 0;
    } else {
      list.value = [];
      total.value = 0;
    }
  } catch (e) {
    ElMessage.error(t('empNotify.fetchFailed'));
    list.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

const markRead = async (row) => {
  try {
    await markNotificationReadApi(row.id);
    row.read = true;
    ElMessage.success(t('empNotify.markedRead'));
  } catch (e) {
    ElMessage.error(t('empNotify.operationFailed'));
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
