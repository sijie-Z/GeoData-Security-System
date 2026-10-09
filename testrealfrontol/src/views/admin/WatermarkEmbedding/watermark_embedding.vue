<template>
  <div>
    <PageHeader :title="$t('wmEmbed.pageTitle')" />
    <div class="data-type-tabs" style="margin-bottom: 12px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
      <span class="data-type-label">{{ $t('wmEmbed.dataTypeLabel') }}</span>
      <div v-if="hasRasterData" class="algo-block">
        <div class="algo-row">
          <span class="algo-label">{{ $t('wmEmbed.algorithm') || 'Algorithm' }}:</span>
          <el-select v-model="selectedAlgorithm" size="small" style="width: 180px;">
            <el-option label="LSB (Reversible)" value="lsb" />
            <el-option label="DWT (Frequency)" value="dwt" />
            <el-option label="Histogram Shift" value="histogram" />
            <el-option :label="$t('wmEmbed.algorithmBlind') || 'Blind (crop-resistant, needs large image)'" value="blind" />
            <el-option :label="$t('wmEmbed.algorithmIwDct') || 'IW-DCT (needs large image)'" value="iw_dct" />
          </el-select>
          <el-tooltip :content="$t('wmEmbed.algorithmTip') || 'LSB: reversible, fragile. DWT: robust to attacks. Histogram: high capacity for concentrated images.'" placement="top">
            <el-icon style="color: var(--text-3); cursor: help;"><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
        <p class="algo-host-hint">{{ $t('wmEmbed.algorithmHostHint') }}</p>
      </div>
      <el-button type="primary" class="batch-open-btn" @click="openBatchDialog">
        {{ $t('wmEmbed.batchEmbed') }}
      </el-button>
    </div>
    <el-table :data="data.list" border style="width: 100%" v-loading="loading">
      <el-table-column prop="id" :label="$t('wmEmbed.colApplicationId')" width="82.5" />
      <el-table-column prop="data_alias" :label="$t('wmEmbed.colDataName')" width="85"/>
      <el-table-column prop="data_id" :label="$t('wmEmbed.colVectorDataId')" width="110"/>
      <el-table-column prop="applicant_user_number" :label="$t('wmEmbed.colApplicantNo')" width="100"/>
      <el-table-column prop="applicant_name" :label="$t('wmEmbed.colApplicantName')" width="95"/>
      <el-table-column prop="adm1_name" :label="$t('wmEmbed.colAdm1Name')" width="110"/>
      <el-table-column prop="adm2_name" :label="$t('wmEmbed.colAdm2Name')" width="110"/>

      <el-table-column :label="$t('wmEmbed.colFirstStatus')" width="85">
        <template v-slot="scope">
          {{ getStatusText(scope.row.first_statu) }}
        </template>
      </el-table-column>

      <el-table-column :label="$t('wmEmbed.colSecondStatus')" width="85">
        <template v-slot="scope">
          <div v-if="!scope.row.first_statu">
            {{ getStatusText(null) }}
          </div>
          <div v-else>
            {{ getStatusText(scope.row.second_statu) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('wmEmbed.colWatermark')">
        <template #default="scope">
          <div class="qr-image-wrapper">
            <WatermarkImage class="qr-code-image"
              :src="scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : ''"
              fit="cover"
              style="width: 72px; height: 72px;"
            />
            <span v-if="!scope.row.qrcode" class="qr-empty-text">{{ $t('wmEmbed.noQRCode') || '—' }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column :label="$t('wmEmbed.colAction')" width="380">
        <template v-slot="scope">
          <el-button size="small" type="primary" @click="openMapDialog(scope.row)">{{ $t('wmEmbed.viewOriginalData') }}</el-button>
          <el-button size="small" type="info" @click="previewWatermark(scope.row)" :loading="previewingId === scope.row.id">{{ $t('wmEmbed.preview') || 'Preview' }}</el-button>
          <el-button size="small" type="primary" @click="embedding_watermark(scope.row)" :loading="embeddingId === scope.row.id">{{ $t('wmEmbed.embedWatermark') }}</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>

  <div>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="prev, pager, next, jumper, total"
      @current-change="pageChanged"
      class="view-pagination"
    />
  </div>

  <el-dialog
    :title="$t('wmEmbed.vectorMapDialogTitle')"
    v-model="viewDataVisible"
    width="72%"
    class="vector-map-dialog"
    :before-close="(done)=>handleClose('map',done)"
    destroy-on-close
  >
    <div class="dialog-container vector-preview-layout">
      <div class="map-wrapper">
        <div class="map-container" ref="mapContainer"></div>
        <div v-if="!selectedData.data_url" class="map-placeholder">
          <el-empty :description="$t('wmEmbed.mapEmptyDesc')" />
        </div>
      </div>
      <div class="info-container">
        <h4 class="info-title">{{ $t('wmEmbed.applicationDataInfo') }}</h4>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item :label="$t('wmEmbed.descDataName')">{{ selectedData.data_alias }}</el-descriptions-item>
          <el-descriptions-item :label="$t('wmEmbed.descDataId')">{{ selectedData.data_id }}</el-descriptions-item>
          <el-descriptions-item :label="$t('wmEmbed.descApplicant')">{{ selectedData.applicant_name }} ({{ selectedData.applicant_user_number }})</el-descriptions-item>
          <el-descriptions-item :label="$t('wmEmbed.descMapServiceUrl')">
            <span class="url-text" :title="selectedData.data_url">{{ selectedData.data_url || '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <p class="info-tip">{{ $t('wmEmbed.closeDialogTip') }}</p>
      </div>
    </div>
  </el-dialog>

  <!-- Watermark Preview Dialog -->
  <el-dialog
    v-model="previewVisible"
    :title="$t('wmEmbed.previewTitle') || 'Watermark Embedding Preview'"
    width="500px"
    class="preview-dialog"
  >
    <el-descriptions :column="1" border size="small">
      <el-descriptions-item :label="$t('wmEmbed.previewDataType') || 'Data Type'">
        <el-tag :type="previewData.data_type === 'raster' ? 'warning' : 'primary'" effect="plain">
          {{ previewData.data_type }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item v-if="previewData.data_type === 'vector'" :label="$t('wmEmbed.previewVertices') || 'Total Vertices'">
        {{ previewData.total_vertices.toLocaleString() }}
      </el-descriptions-item>
      <el-descriptions-item v-if="previewData.data_type === 'raster'" :label="$t('wmEmbed.previewHostSize') || 'Host Image Size'">
        {{ previewData.host_size ? `${previewData.host_size.width} x ${previewData.host_size.height}` : '-' }}
      </el-descriptions-item>
      <el-descriptions-item v-if="previewData.data_type === 'raster'" :label="$t('wmEmbed.previewTotalPixels') || 'Total Pixels'">
        {{ previewData.total_pixels.toLocaleString() }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('wmEmbed.previewWmBits') || 'Watermark Bits'">
        {{ previewData.watermark_bits.toLocaleString() }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('wmEmbed.previewUtilization') || 'Capacity Utilization'">
        <el-progress
          :percentage="Math.min(100, previewData.estimated_utilization)"
          :color="previewData.estimated_utilization > 80 ? 'var(--tint-danger-text)' : previewData.estimated_utilization > 50 ? 'var(--tint-warning-text)' : 'var(--tint-success-text)'"
          :stroke-width="18"
          :text-inside="true"
        />
      </el-descriptions-item>
      <el-descriptions-item :label="$t('wmEmbed.previewStatus') || 'Capacity Status'">
        <el-tag :type="previewData.sufficient ? 'success' : 'danger'" effect="dark">
          {{ previewData.sufficient ? ($t('wmEmbed.sufficient') || 'Sufficient') : ($t('wmEmbed.insufficient') || 'Insufficient') }}
        </el-tag>
      </el-descriptions-item>
    </el-descriptions>
  </el-dialog>

  <!-- Batch Embed Job Dialog：选申请 → 真实进度 → 逐项结果 → 重试失败项 / 历史作业 -->
  <el-dialog
    v-model="batchVisible"
    :title="$t('wmEmbed.batchDialogTitle')"
    width="880px"
    class="batch-dialog"
  >
    <!-- ① 发起视图：可选申请（已审批·已生成水印·未嵌入）+ 历史作业 -->
    <div v-if="!batchJob" class="batch-create">
      <div class="batch-toolbar">
        <span class="batch-select-title">{{ $t('wmEmbed.batchSelectTitle') }}</span>
        <span class="batch-selected-hint">{{ $t('wmEmbed.batchSelected', { n: batchSelected.length }) }}</span>
        <div class="batch-algo-row">
          <span class="algo-label">{{ $t('wmEmbed.batchAlgorithmLabel') }}</span>
          <el-select v-model="batchAlgorithm" size="small" style="width: 200px;">
            <el-option label="LSB (Reversible)" value="lsb" />
            <el-option label="DWT (Frequency)" value="dwt" />
            <el-option label="Histogram Shift" value="histogram" />
            <el-option :label="$t('wmEmbed.algorithmBlind')" value="blind" />
            <el-option :label="$t('wmEmbed.algorithmIwDct')" value="iw_dct" />
          </el-select>
        </div>
      </div>
      <el-table
        :data="batchEligible"
        border
        size="small"
        v-loading="batchEligibleLoading"
        max-height="260"
        @selection-change="onBatchSelectionChange"
      >
        <el-table-column type="selection" width="42" />
        <el-table-column prop="id" :label="$t('wmEmbed.colApplicationId')" width="88" />
        <el-table-column prop="data_alias" :label="$t('wmEmbed.colDataName')" min-width="130" show-overflow-tooltip />
        <el-table-column prop="data_id" :label="$t('wmEmbed.colVectorDataId')" width="105" />
        <el-table-column :label="$t('wmEmbed.previewDataType')" width="88">
          <template #default="scope">
            <el-tag size="small" effect="plain" :type="(scope.row.data_type || '').toLowerCase() === 'raster' ? 'warning' : 'primary'">
              {{ scope.row.data_type || 'vector' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="applicant_name" :label="$t('wmEmbed.colApplicantName')" width="105" />
        <template #empty>
          <el-empty :description="$t('wmEmbed.batchNoEligible')" :image-size="60" />
        </template>
      </el-table>
      <div class="batch-actions">
        <span class="batch-limit-hint">{{ $t('wmEmbed.batchLimit') }}</span>
        <el-button
          type="primary"
          :loading="batchSubmitting"
          :disabled="!batchSelected.length"
          @click="submitBatchSelected"
        >
          {{ $t('wmEmbed.batchSubmit') }}
        </el-button>
      </div>

      <div class="batch-history">
        <div class="batch-section-title">{{ $t('wmEmbed.batchHistoryTitle') }}</div>
        <el-table :data="batchHistory" size="small" border v-loading="batchHistoryLoading" max-height="200">
          <el-table-column prop="created_at" :label="$t('wmEmbed.batchCreatedAt')" width="165" />
          <el-table-column :label="$t('wmEmbed.batchColStatus')" width="88">
            <template #default="scope">
              <el-tag size="small" :type="batchJobStatusType(scope.row.status)">{{ batchJobStatusText(scope.row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('wmEmbed.batchJobCount')" width="90">
            <template #default="scope">{{ scope.row.done }} / {{ scope.row.total }}</template>
          </el-table-column>
          <el-table-column prop="ok" :label="$t('wmEmbed.batchOkCount')" width="72" />
          <el-table-column prop="fail" :label="$t('wmEmbed.batchFailCount')" width="72" />
          <el-table-column prop="algorithm" :label="$t('wmEmbed.algorithm')" width="92" />
          <el-table-column prop="uuid" label="UUID" min-width="130" show-overflow-tooltip />
          <el-table-column :label="$t('wmEmbed.colAction')" width="96">
            <template #default="scope">
              <el-button size="small" link type="primary" @click="loadBatchJob(scope.row.uuid)">
                {{ $t('wmEmbed.batchViewDetail') }}
              </el-button>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :description="$t('wmEmbed.batchHistoryEmpty')" :image-size="48" />
          </template>
        </el-table>
      </div>
    </div>

    <!-- ② 作业详情视图：真实进度条 + 逐项结果 + 重试失败项 -->
    <div v-else class="batch-detail" v-loading="batchDetailLoading">
      <div class="batch-detail-head">
        <el-button size="small" @click="backToBatchSelect">{{ $t('wmEmbed.batchBack') }}</el-button>
        <el-tag size="small" :type="batchJobStatusType(batchJob.status)">{{ batchJobStatusText(batchJob.status) }}</el-tag>
        <span class="batch-detail-uuid">{{ batchJob.uuid }}</span>
        <span class="batch-detail-counts">
          {{ $t('wmEmbed.batchOkCount') }} {{ batchJob.ok }} ·
          {{ $t('wmEmbed.batchFailCount') }} {{ batchJob.fail }} ·
          {{ batchJob.done }}/{{ batchJob.total }}
        </span>
      </div>
      <div class="batch-progress-block">
        <div class="batch-section-title">{{ $t('wmEmbed.batchProgress') }}</div>
        <el-progress
          :percentage="batchProgressPercent"
          :status="batchProgressStatus"
          :stroke-width="18"
          :text-inside="true"
          :duration="2"
          :striped="batchJob.status === 'running'"
          :striped-flow="batchJob.status === 'running'"
        />
      </div>
      <div class="batch-section-title">{{ $t('wmEmbed.batchResultTitle') }}</div>
      <el-table :data="batchJob.items" size="small" border max-height="280">
        <el-table-column prop="application_id" :label="$t('wmEmbed.colApplicationId')" width="88" />
        <el-table-column prop="data_alias" :label="$t('wmEmbed.colDataName')" min-width="120" show-overflow-tooltip />
        <el-table-column prop="data_type" :label="$t('wmEmbed.previewDataType')" width="90" />
        <el-table-column :label="$t('wmEmbed.batchColStatus')" width="92">
          <template #default="scope">
            <el-tag size="small" :type="batchItemStatusType(scope.row.status)">{{ batchItemStatusText(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('wmEmbed.batchColError')" min-width="230">
          <template #default="scope">
            <span v-if="scope.row.error" class="batch-item-error" :title="scope.row.error">{{ scope.row.error }}</span>
            <span v-else class="batch-item-empty">—</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="batch-actions">
        <el-button
          v-if="batchJob.status === 'done' && batchJob.fail > 0"
          type="warning"
          :loading="batchSubmitting"
          @click="retryFailedBatch"
        >
          {{ $t('wmEmbed.batchRetryFailed') }}
        </el-button>
      </div>
    </div>
  </el-dialog>

</template>

<script setup>
import {useUserStore} from "@/stores/userStore.js";
import PageHeader from '@/components/common/PageHeader.vue';
import {reactive, ref, onMounted, onBeforeUnmount, watch, nextTick, computed} from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElMessageBox } from 'element-plus';
import { QuestionFilled } from '@element-plus/icons-vue';
import {
  getEmbeddingApplications,
  embedWatermark as embedWatermarkApi,
  embedDispatch,
  previewWatermark as previewWatermarkApi,
  startBatchEmbedJob,
  getBatchEmbedJobs,
  getBatchEmbedJob
} from '@/api/watermark';
import WatermarkImage from '@/components/common/WatermarkImage.vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// 修正 Leaflet 默认图标路径（webpack/vite 下 marker 图标会丢失）
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl, iconRetinaUrl, shadowUrl });

const { t } = useI18n();

const loading = ref(false);
const embeddingId = ref(null);
const previewingId = ref(null);
const selectedAlgorithm = ref('lsb');
const hasRasterData = computed(() => data.list.some(r => (r.data_type || '').toLowerCase() === 'raster'));
const previewVisible = ref(false);
const previewData = reactive({
  data_type: '',
  total_vertices: 0,
  watermark_bits: 0,
  estimated_utilization: 0,
  sufficient: true,
  host_size: null,
  watermark_size: null,
  total_pixels: 0
});
const data = reactive({ list: [] });
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const dataTypeTab = ref('');

const requestFormRef = ref(null);
const viewDataVisible = ref(false);
const mapContainer = ref(null);




watch(page, (newValue, oldValue) => {
  if (oldValue !== newValue) {
    get_applications();
  }
});

const pageChanged = (newPage) => {
  page.value = newPage;
};

const onDataTypeChange = () => {
  page.value = 1;
  get_applications();
};

const getStatusText = (status) => {
  if (status === true) return t('wmEmbed.statusPassed');
  if (status === false) return t('wmEmbed.statusRejected');
  if (status === null) return t('wmEmbed.statusPending');
  return ''; // 默认返回空字符串
};



const initialRequestInformation = {
  application_id: '',
  data_name:'',
  data_id: '',
  data_url:'',
  data_alias: '',
  applicant_name: '',
  applicant_user_number: '',
  adm1_name: '',
  adm2_name: '',
  now: ''
};

const requestInformation = reactive({ ...initialRequestInformation });

const get_applications = async () => {
  loading.value = true;
  try {
    const response = await getEmbeddingApplications({
      page: page.value, pageSize: pageSize.value
    });

    if (!response.data || !response.data.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data.msg || t('wmEmbed.fetchFailed'));
      return;
    }

    data.list = response.data.application_data;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error('Error fetching records:', err);
    ElMessage.error(t('wmEmbed.fetchFailed'));
  } finally {
    loading.value = false;
  }
};


onMounted(() => {
  get_applications();
});


const resetForm = async () => {
  Object.assign(requestInformation, { ...initialRequestInformation });
  await nextTick();
  requestFormRef.value?.clearValidate();
};


const embedding_watermark = async (row) => {
  const ApplicationId = row.id;
  const DataId = row.data_id;
  const applicant_user_number = row.applicant_user_number;
  const isRaster = (row.data_type || '').toLowerCase() === 'raster';

  embeddingId.value = ApplicationId;
  ElMessage.info(t('wmEmbed.embeddingInProgress'));

  try {
    if (isRaster) {
      const res = await embedDispatch({ application_id: ApplicationId, algorithm: selectedAlgorithm.value });
      if (res.data && res.data.status) {
        ElMessage.success(res.data.msg || t('wmEmbed.rasterEmbedSuccess'));
        get_applications();
      } else {
        ElMessage.error(res.data?.msg || t('wmEmbed.rasterEmbedFailed'));
      }
      return;
    }

    const response = await embedWatermarkApi({
      application_id: ApplicationId,
      data_id: DataId,
      applicant_user_number: applicant_user_number,
      embed_person: row.adm2_name,
      applicant: row.applicant_name
    });

    const disposition = response.headers['content-disposition'];
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    let fileName = 'default.zip';
    if (disposition) {
      // 优先取 filename*=UTF-8''...（支持中文），再取 filename=...（仅 ASCII）
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
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    // 显示下载成功提示，包含文件名和对应申请信息
    ElMessage.success(
      t('wmEmbed.embedSuccess') + ` (${t('wmEmbed.colApplicationId')}: ${ApplicationId}, ${t('wmEmbed.colDataName')}: ${row.data_alias})`,
      { duration: 6000 }
    );
    ElMessage.info(t('wmEmbed.downloadFileHint') + `: ${fileName}`);
    get_applications();
  } catch (error) {
    ElMessage.error(t('wmEmbed.embedFailed'));
    // 如果是矢量嵌入失败，尝试重新获取列表
    if (!isRaster) get_applications();
  } finally {
    embeddingId.value = null;
  }
};


const previewWatermark = async (row) => {
  previewingId.value = row.id;
  try {
    const resp = await previewWatermarkApi({ application_id: row.id });
    if (resp.data.status) {
      const p = resp.data.preview;
      Object.assign(previewData, {
        data_type: resp.data.data_type,
        total_vertices: p.total_vertices || 0,
        watermark_bits: p.watermark_bits || 0,
        estimated_utilization: p.estimated_utilization || 0,
        sufficient: p.capacity?.sufficient ?? true,
        host_size: p.host_size || null,
        watermark_size: p.watermark_size || null,
        total_pixels: p.total_pixels || 0
      });
      previewVisible.value = true;
    } else {
      ElMessage.error(resp.data.msg || 'Preview failed');
    }
  } catch (e) {
    ElMessage.error('Preview failed');
  } finally {
    previewingId.value = null;
  }
};

const selectedData = reactive({
  data_alias: '',
  data_id: '',
  data_url: '',
  applicant_name: '',
  applicant_user_number: ''
});

// ──────────────────────────────────────
//  批量嵌入作业（feat_batch_embed）
//  真实进度：1.5s 轮询作业详情（done/total），无任何假进度
// ──────────────────────────────────────
const BATCH_POLL_MS = 1500;
const MAX_BATCH_ITEMS = 50;

const batchVisible = ref(false);
const batchEligible = ref([]);
const batchEligibleLoading = ref(false);
const batchSelected = ref([]);
const batchAlgorithm = ref('lsb');
const batchSubmitting = ref(false);
const batchJob = ref(null); // 作业详情（null = 发起视图）
const batchDetailLoading = ref(false);
const batchHistory = ref([]);
const batchHistoryLoading = ref(false);
let batchPollTimer = null;

const openBatchDialog = () => {
  batchVisible.value = true;
  batchJob.value = null;
  batchSelected.value = [];
  fetchBatchEligible();
  fetchBatchHistory();
};

const fetchBatchEligible = async () => {
  batchEligibleLoading.value = true;
  try {
    // data_type='' 关闭既有 data_type 过滤（同时列出矢量与栅格）；
    // embedded=false 只列未嵌入的申请（页面既有接口的轻量扩展参数）
    const res = await getEmbeddingApplications({ page: 1, pageSize: 100, data_type: '', embedded: 'false' });
    if (res.data?.status) {
      batchEligible.value = res.data.application_data || [];
    } else {
      batchEligible.value = [];
      ElMessage.error(res.data?.msg || t('wmEmbed.fetchFailed'));
    }
  } catch (err) {
    console.error('Error fetching batch-eligible applications:', err);
    batchEligible.value = [];
    ElMessage.error(t('wmEmbed.fetchFailed'));
  } finally {
    batchEligibleLoading.value = false;
  }
};

const fetchBatchHistory = async () => {
  batchHistoryLoading.value = true;
  try {
    const res = await getBatchEmbedJobs({ page: 1, per_page: 20 });
    if (res.data?.status) {
      batchHistory.value = res.data.jobs || [];
    }
  } catch (err) {
    console.error('Error fetching batch jobs:', err);
    ElMessage.error(t('wmEmbed.batchLoadFailed'));
  } finally {
    batchHistoryLoading.value = false;
  }
};

const onBatchSelectionChange = (rows) => {
  batchSelected.value = rows;
};

const stopBatchPolling = () => {
  if (batchPollTimer) {
    clearInterval(batchPollTimer);
    batchPollTimer = null;
  }
};

const startBatchPolling = () => {
  stopBatchPolling();
  batchPollTimer = setInterval(batchPollTick, BATCH_POLL_MS);
};

const batchPollTick = async () => {
  const jobUuid = batchJob.value?.uuid;
  if (!jobUuid) {
    stopBatchPolling();
    return;
  }
  try {
    const res = await getBatchEmbedJob(jobUuid);
    const job = res.data?.job;
    if (!job) return;
    batchJob.value = job;
    if (job.status === 'done') {
      stopBatchPolling();
      fetchBatchHistory();
    }
  } catch {
    // 单次轮询失败静默，下一周期重试
  }
};

const loadBatchJob = async (jobUuid) => {
  if (!jobUuid) return;
  batchDetailLoading.value = true;
  try {
    const res = await getBatchEmbedJob(jobUuid);
    if (res.data?.status && res.data.job) {
      batchJob.value = res.data.job;
      if (res.data.job.status === 'done') {
        stopBatchPolling();
      } else {
        startBatchPolling();
      }
    } else {
      ElMessage.error(res.data?.msg || t('wmEmbed.batchLoadFailed'));
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.msg || t('wmEmbed.batchLoadFailed'));
  } finally {
    batchDetailLoading.value = false;
  }
};

const submitBatch = async (ids) => {
  if (!ids || !ids.length) {
    ElMessage.warning(t('wmEmbed.batchNoSelection'));
    return;
  }
  if (ids.length > MAX_BATCH_ITEMS) {
    ElMessage.warning(t('wmEmbed.batchLimit'));
    return;
  }
  batchSubmitting.value = true;
  try {
    const res = await startBatchEmbedJob({ application_ids: ids, algorithm: batchAlgorithm.value });
    if (res.data?.status) {
      ElMessage.success(t('wmEmbed.batchStarted'));
      await loadBatchJob(res.data.data.uuid);
      fetchBatchHistory();
    } else {
      ElMessage.error(res.data?.msg || t('wmEmbed.batchStartFailed'));
    }
  } catch (error) {
    const body = error.response?.data;
    if (error.response?.status === 409 && body?.data?.uuid) {
      // 单活动作业锁：提示并直接跳转当前作业详情
      ElMessage.warning(body.msg || t('wmEmbed.batchActiveExists'));
      await loadBatchJob(body.data.uuid);
    } else {
      ElMessage.error(body?.msg || t('wmEmbed.batchStartFailed'));
    }
  } finally {
    batchSubmitting.value = false;
  }
};

const submitBatchSelected = () => submitBatch(batchSelected.value.map((row) => row.id));

const retryFailedBatch = () =>
  submitBatch((batchJob.value?.items || []).filter((item) => item.status === 'fail').map((item) => item.application_id));

const backToBatchSelect = () => {
  stopBatchPolling();
  batchJob.value = null;
  fetchBatchEligible();
  fetchBatchHistory();
};

const batchProgressPercent = computed(() => {
  const job = batchJob.value;
  if (!job || !job.total) return 0;
  return Math.min(100, Math.round((job.done / job.total) * 100));
});

const batchProgressStatus = computed(() => {
  const job = batchJob.value;
  if (!job || job.status !== 'done') return undefined;
  return job.fail > 0 ? 'exception' : 'success';
});

const batchJobStatusText = (status) => {
  if (status === 'done') return t('wmEmbed.batchStatusDone');
  if (status === 'running') return t('wmEmbed.batchStatusRunning');
  return t('wmEmbed.batchStatusQueued');
};

const batchJobStatusType = (status) => {
  if (status === 'done') return 'success';
  if (status === 'running') return 'primary';
  return 'info';
};

const batchItemStatusText = (status) => {
  if (status === 'ok') return t('wmEmbed.batchItemOk');
  if (status === 'fail') return t('wmEmbed.batchItemFail');
  return t('wmEmbed.batchItemPending');
};

const batchItemStatusType = (status) => {
  if (status === 'ok') return 'success';
  if (status === 'fail') return 'danger';
  return 'info';
};

watch(batchVisible, (visible) => {
  if (!visible) stopBatchPolling();
});

const openMapDialog = async (row) => {
  destroyMapView();
  selectedData.data_alias = row.data_alias ?? '';
  selectedData.data_id = row.data_id ?? '';
  selectedData.data_url = row.data_url ?? '';
  selectedData.applicant_name = row.applicant_name ?? '';
  selectedData.applicant_user_number = row.applicant_user_number ?? '';
  viewDataVisible.value = true;
  await nextTick();
  if (selectedData.data_url && viewDataVisible.value) {
    initializeMapView(selectedData.data_url);
  }
};

let mapInstance = null;
const initializeMapView = (data_url) => {
  destroyMapView();
  if (!mapContainer.value) return;

  // 创建 OSM 底图
  mapInstance = L.map(mapContainer.value, {
    center: [0, 0],
    zoom: 2,
    zoomControl: true,
    attributionControl: true,
  });

  // OpenStreetMap 高清瓦片
  // #24 深色适配（方案 A）：仅瓦片层挂 dark-tile-layer class，由全局
  // design-system.css 在 html.dark 下施加 invert+hue-rotate filter；默认 PNG
  // 标记、GeoJSON 矢量与控件位于独立 pane，不含该 class，不受影响。
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    className: 'dark-tile-layer', // #24
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(mapInstance);

  // 尝试加载 ArcGIS 服务上的要素图层
  if (data_url) {
    // 用 fetch 获取 ArcGIS 服务的 GeoJSON（支持 ArcGIS Server / MapServer / FeatureServer）
    const queryUrl = data_url.replace(/\/MapServer\/\d+$/, '/MapServer')
      + '/query?where=1%3D1&outFields=*&returnGeometry=true&f=geojson';

    fetch(queryUrl)
      .then(res => {
        if (!res.ok) throw new Error('Service unavailable');
        return res.json();
      })
      .then(geojson => {
        if (!geojson.features || geojson.features.length === 0) {
          ElMessage.warning(t('wmEmbed.noFeaturesFound') || 'No features found on map service');
          return;
        }
        const geoLayer = L.geoJSON(geojson, {
          style: { color: '#FF6F00', weight: 2, opacity: 0.8, fillColor: '#FFB74D', fillOpacity: 0.2 },
          pointToLayer: (feature, latlng) => L.marker(latlng),
        }).addTo(mapInstance);
        mapInstance.fitBounds(geoLayer.getBounds().pad(0.1));
      })
      .catch(() => {
        // 如果 ArcGIS 服务不可用，至少展示 OSM 底图 + 服务地址标记
        ElMessage.info(t('wmEmbed.mapServiceHint') || 'Map service layer unavailable, showing base map only');
        mapInstance.setView([35, 105], 4); // 中国区域
      });
  }
};

const destroyMapView = () => {
  if (mapInstance) {
    try { mapInstance.remove() } catch (_) {}
    mapInstance = null;
  }
};

// Clean up ArcGIS resources when leaving the page
onBeforeUnmount(() => {
  destroyMapView();
  stopBatchPolling();
});

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm(t('wmEmbed.confirmClose')).then(() => {
    done();
    if (dialogType === 'map') {
      destroyMapView();
    }
  }).catch(() => {});
};



</script>

<style scoped>

/* 栅格算法选择块：行内选择器 + 宿主约束提示行 */
.algo-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.algo-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.algo-label {
  font-size: 13px;
  color: var(--text-2, #64748b);
}

.algo-host-hint {
  margin: 0;
  font-size: 12px;
  color: var(--text-3, #94a3b8);
  line-height: 1.5;
}

.qr-code-image {
  width: 72px;
  height: 72px;
}

.qr-image-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.qr-error-slot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  background: var(--bg-inset, #f5f7fa);
  border-radius: 4px;
  color: var(--text-4, #c0c4cc);
  font-size: 24px;
}

.qr-empty-text {
  font-size: 12px;
  color: var(--text-4, #c0c4cc);
}

.view-pagination{
  margin-top: 20px;
}

.dialog-container {
  display: flex;
  gap: 20px;
}

.vector-preview-layout .map-wrapper {
  flex: 3;
  min-width: 0;
  position: relative;
  height: 520px;
  border-radius: 12px;
  overflow: hidden;
  background: var(--bg-inset, #e8ecf1);
  border: 1px solid var(--border-default, #d0d5dd);
}

.vector-preview-layout .map-container {
  width: 100%;
  height: 100%;
  z-index: 1;
}

.map-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-inset, #f8fafc);
}

.vector-preview-layout .info-container {
  flex: 1;
  min-width: 260px;
  padding: 0;
}

.info-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-1, #1e293b);
  margin: 0 0 12px 0;
}

.url-text {
  font-size: 12px;
  color: var(--text-2, #64748b);
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.info-tip {
  font-size: 12px;
  color: var(--text-3, #94a3b8);
  margin: 16px 0 0 0;
}

.preview-dialog .el-descriptions {
  margin-top: 8px;
}

/* ── 批量嵌入（feat_batch_embed）：入口按钮贴右 + 作业对话框 ── */
.batch-open-btn {
  margin-left: auto;
}

.batch-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.batch-select-title {
  font-size: 13px;
  color: var(--text-1, #1e293b);
}

.batch-selected-hint {
  font-size: 12px;
  color: var(--text-3, #94a3b8);
}

.batch-algo-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.batch-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 10px;
}

.batch-limit-hint {
  font-size: 12px;
  color: var(--text-3, #94a3b8);
}

.batch-history {
  margin-top: 18px;
}

.batch-section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-2, #475569);
  margin: 0 0 8px 0;
}

.batch-detail-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.batch-detail-uuid {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  color: var(--text-3, #94a3b8);
  word-break: break-all;
}

.batch-detail-counts {
  margin-left: auto;
  font-size: 13px;
  color: var(--text-1, #1e293b);
}

.batch-progress-block {
  margin-bottom: 16px;
}

.batch-item-error {
  display: inline-block;
  font-size: 12px;
  color: var(--el-color-danger, #d93025);
  word-break: break-all;
  line-height: 1.4;
}

.batch-item-empty {
  color: var(--text-4, #c0c4cc);
}

</style>
