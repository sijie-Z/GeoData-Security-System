<template>
  <el-card class="page-container" shadow="never">
    <!-- 顶部标题和操作区 -->
    <template #header>
      <div class="card-header">
        <h1>{{ $t('empDataDownload.title') }}</h1>
        <el-button :icon="Refresh" circle @click="get_applications" :loading="loading" />
      </div>
    </template>

    <!-- 主内容区域：卡片列表或空状态 -->
    <div v-if="!loading && data.list.length > 0" class="data-card-list">
      <el-card v-for="item in data.list" :key="item.application_id" class="data-card" shadow="hover">
        <div class="card-content">
          <!-- 左侧信息区 -->
          <div class="info-section">
            <el-descriptions :column="1" size="small">
              <el-descriptions-item :label="$t('empDataDownload.applicationId')">#{{ item.application_id }}</el-descriptions-item>
              <el-descriptions-item :label="$t('empDataDownload.dataName')"><strong>{{ item.data_alias }}</strong></el-descriptions-item>
              <el-descriptions-item :label="$t('empDataDownload.vectorDataId')">{{ item.data_id }}</el-descriptions-item>
              <el-descriptions-item :label="$t('empDataDownload.dataProvider')">{{ item.send_file_person_user_number }}</el-descriptions-item>
            </el-descriptions>
          </div>
          <!-- 右侧操作区 -->
          <div class="action-section">
            <el-button
              type="primary"
              size="large"
              :icon="Download"
              @click="download(item)"
              :loading="downloadingStatus[item.application_id]"
            >
              {{ downloadingStatus[item.application_id] ? $t('empDataDownload.preparingDelivery') : $t('empDataDownload.downloadData') }}
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" v-loading="loading" class="loading-placeholder"></div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && data.list.length === 0" :description="$t('empDataDownload.emptyDescription')" />

    <!-- 分页器 -->
    <div v-if="total > 0" class="pagination-container">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        background
        @current-change="pageChanged"
      />
    </div>
  </el-card>
</template>

<script setup>
// [新增] 导入 Refresh 和 Download 图标
import { Refresh, Download } from "@element-plus/icons-vue";
import { reactive, onMounted, ref, watch, computed } from "vue";
import { useI18n } from 'vue-i18n';
import { ElMessage } from "element-plus";
import { getApprovedApplications, requestDownloadToken } from '@/api/employee';
import axios from '@/utils/Axios';
import { useUserStore } from "@/stores/userStore.js";

const { t } = useI18n();

const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);

// [新增] 页面加载状态和下载按钮的独立加载状态
const loading = ref(true);
const downloadingStatus = reactive({});

const data = reactive({
  list: [],
});

const page = ref(1);
const pageSize = ref(5); // 每页显示5个卡片
const total = ref(0);

const pageChanged = (newPage) => {
  page.value = newPage;
};

watch(page, () => {
  get_applications();
});

const get_applications = async () => {
  loading.value = true;
  try {
    const params = { page: page.value, pageSize: pageSize.value, userNumber: userNumber.value };
    const response = await getApprovedApplications(params);

    if (response?.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }
    if (response?.data?.status === false) {
      ElMessage.error(response?.data?.msg || t('empDataDownload.fetchFailed'));
      data.list = [];
      total.value = 0;
      return;
    }
    data.list = response?.data?.emp_get_applications || [];
    total.value = response?.data?.pages?.total ?? 0;
  } catch (err) {
    console.error("Error", err);
    ElMessage.error(t('empDataDownload.fetchRecordsFailed'));
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  get_applications();
});

// 个性化交付下载：申请下载 token → 拉取个性化副本 → 服务端自动落下载记录
const download = async (row) => {
  downloadingStatus[row.application_id] = true; // 开始下载，设置对应按钮为加载状态
  try {
    // 1. 申请本次个性化交付副本的下载 token（服务端现场生成，耗时长，单独放宽超时）
    const tokenResponse = await requestDownloadToken(
      { application_id: row.application_id },
      { timeout: 180000 }
    );
    const tokenBody = tokenResponse?.data;
    if (!tokenBody?.status || !tokenBody?.token) {
      ElMessage.error(tokenBody?.msg || t('empDataDownload.deliveryGenerateFailed'));
      return;
    }
    const delivery = tokenBody.delivery || {};
    const deliveryUuid = delivery.uuid || '';

    // 2. 凭 token 下载个性化副本（token 即凭证）
    const fileResponse = await axios.get('/api/download/' + tokenBody.token, {
      responseType: 'blob',
      timeout: 120000
    });

    // 3. 解析文件名：优先 RFC5987 filename*=UTF-8''，回退 filename=
    const disposition = fileResponse.headers['content-disposition'];
    let fileName = 'delivery.zip';
    if (disposition) {
      const matchesRFC = /filename\*=UTF-8''([^;\n]*)/.exec(disposition);
      if (matchesRFC && matchesRFC[1]) {
        fileName = decodeURIComponent(matchesRFC[1]);
      } else {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
        if (matches && matches[1]) {
          fileName = matches[1].replace(/['"]/g, '');
        }
      }
    }

    // 4. 存盘（服务端已自动记账，前端不再调用 recordDownloadFile）
    const url = window.URL.createObjectURL(new Blob([fileResponse.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url); // [优化] 释放内存

    ElMessage.success(t('empDataDownload.downloadSuccess', {
      uuid: deliveryUuid ? deliveryUuid.slice(0, 8) : '—'
    }));
  } catch (error) {
    console.error('Download error:', error);
    const status = error?.response?.status;
    let msg = error?.response?.data?.msg;
    // blob 响应下错误体是 Blob，尝试读出其中的 msg
    if (!msg && error?.response?.data instanceof Blob) {
      try {
        const text = await error.response.data.text();
        try {
          msg = JSON.parse(text)?.msg;
        } catch (parseErr) {
          console.error('Parse error body failed:', parseErr);
          msg = text ? text.slice(0, 200) : undefined;
        }
      } catch (readErr) {
        console.error('Read error body failed:', readErr);
      }
    }
    if (status === 403) {
      ElMessage.error(msg || t('empDataDownload.unauthorizedOrRevoked'));
    } else if (status === 500) {
      ElMessage.error(msg || t('empDataDownload.deliveryGenerateFailed'));
    } else if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
      ElMessage.error(t('empDataDownload.timeoutRetry'));
    } else {
      ElMessage.error(t('empDataDownload.downloadFailed'));
    }
  } finally {
    downloadingStatus[row.application_id] = false; // 结束下载，恢复按钮状态
  }
};
</script>

<style scoped>
.page-container {
  border-radius: 8px;
  min-height: calc(100vh - 110px);
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h1 {
  font-size: 18px;
  font-weight: 400;
  color: var(--text-primary, #303133);
}

.loading-placeholder {
  min-height: 300px;
}

.data-card-list {
  display: flex;
  flex-direction: column;
  gap: 16px; /* 卡片之间的垂直间距 */
}

.data-card {
  border-radius: 8px;
  transition: box-shadow 0.3s;
}

.card-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.info-section {
  flex-grow: 1;
}

.action-section {
  flex-shrink: 0;
  margin-left: 24px;
}

/* 覆盖 el-descriptions 的样式 */
:deep(.el-descriptions__label) {
  color: var(--text-tertiary, #909399);
}
:deep(.el-descriptions__content) {
  color: var(--text-primary, #303133);
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: auto; /* 将分页器推到底部 */
  padding-top: 24px; /* 与上方内容保持间距 */
  padding-bottom: 10px;
}
</style>
