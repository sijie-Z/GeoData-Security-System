<!-- src/views/admin/Watermark Embedding/raster_watermark_embedding.vue -->
<!-- 栅格数据水印嵌入界面 -->

<template>
    <div class="raster-embed-page">
      <el-alert :title="$t('rasterWmEmbed.roleAlert')" type="info" :closable="false" style="margin-bottom: 12px;" />
      <div class="page-header-compact">
        <h2 class="page-title">{{ $t('rasterWmEmbed.pageTitle') }}</h2>
        <p class="page-desc">{{ $t('rasterWmEmbed.pageDesc') }}</p>
      </div>
      <el-alert :title="$t('rasterWmEmbed.workflowTip')" type="warning" :closable="false" style="margin-bottom: 12px;" />
      <!-- 水印嵌入申请表格 -->
      <el-table :data="data.list" border class="embed-table-compact">
        <el-table-column prop="id" :label="$t('rasterWmEmbed.colApplicationId')" width="82.5" />
        <el-table-column prop="data_alias" :label="$t('rasterWmEmbed.colDataName')" width="85"/>
        <el-table-column prop="data_id" :label="$t('rasterWmEmbed.colRasterDataId')" width="110"/>
        <el-table-column prop="applicant_user_number" :label="$t('rasterWmEmbed.colApplicantNo')" width="100"/>
        <el-table-column prop="applicant_name" :label="$t('rasterWmEmbed.colApplicantName')" width="95"/>
        <el-table-column prop="adm1_name" :label="$t('rasterWmEmbed.colAdm1Name')" width="110"/>
        <el-table-column prop="adm2_name" :label="$t('rasterWmEmbed.colAdm2Name')" width="110"/>

        <el-table-column :label="$t('rasterWmEmbed.colFirstStatus')" width="85">
          <template v-slot="scope">
            {{ getStatusText(scope.row.first_statu) }}
          </template>
        </el-table-column>

        <el-table-column :label="$t('rasterWmEmbed.colSecondStatus')" width="85">
          <template v-slot="scope">
            <div v-if="!scope.row.first_statu">
              {{ getStatusText('空') }}
            </div>
            <div v-else>
              {{ getStatusText(scope.row.second_statu) }}
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="$t('rasterWmEmbed.colWatermark')">
          <template #default="scope">
            <el-image class="qr-code-image"
              :src="scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : ''"
              :preview-src-list="[scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : '']"
              fit="cover"
              style="width: 50px; height: 50px;"
            />
          </template>
        </el-table-column>

        <el-table-column :label="$t('rasterWmEmbed.colAction')" width="360">
          <template v-slot="scope">
            <div class="action-wrap">
              <el-button size="small" type="info" plain @click="openDataPreviewDialog(scope.row)">{{ $t('rasterWmEmbed.viewOriginalData') }}</el-button>
              <el-button size="small" type="primary" @click="embedding_watermark(scope.row)">{{ $t('rasterWmEmbed.embedWatermark') }}</el-button>
              <el-button size="small" type="success" plain @click="openCrmarkDialog(scope.row)">{{ $t('rasterWmEmbed.crmarkExperiment') }}</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页组件 -->
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

    <!-- 原始数据预览弹窗 -->
    <el-dialog :title="$t('rasterWmEmbed.rasterPreviewDialogTitle')" v-model="viewDataVisible" width="65%" class="raster-preview-dialog" :before-close="handleClose" destroy-on-close>
      <div class="dialog-container raster-preview-layout">
        <div class="preview-main">
          <div class="raster-preview-container">
            <div v-if="selectedData.preview_base64" class="preview-image-wrapper">
              <el-image
                :src="`data:image/png;base64,${selectedData.preview_base64}`"
                fit="contain"
                style="width: 100%; height: 320px; border-radius: 12px;"
                alt="栅格数据预览"
              />
            </div>
            <div v-else class="preview-placeholder">
              <el-empty :description="$t('rasterWmEmbed.noPreviewImage')" />
            </div>
          </div>
          <div class="raster-actions" v-if="selectedData.data_id">
            <el-button type="primary" plain size="small" @click="openRasterMapDialog">{{ $t('rasterWmEmbed.viewOnMap') }}</el-button>
          </div>
        </div>
        <div class="info-container">
          <h4 class="info-title">{{ $t('rasterWmEmbed.applicationDataInfo') }}</h4>
          <el-descriptions title="" :column="1" border size="small">
            <el-descriptions-item :label="$t('rasterWmEmbed.descDataName')">{{ selectedData.data_alias }}</el-descriptions-item>
            <el-descriptions-item :label="$t('rasterWmEmbed.descRasterDataId')">{{ selectedData.data_id }}</el-descriptions-item>
            <el-descriptions-item :label="$t('rasterWmEmbed.descApplicant')">{{ selectedData.applicant_name }} ({{ selectedData.applicant_user_number }})</el-descriptions-item>
            <el-descriptions-item :label="$t('rasterWmEmbed.descFilePath')">
              <span class="path-text" :title="selectedData.data_file_path">{{ selectedData.data_file_path || '—' }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>

    <!-- 栅格瓦片地图弹窗 -->
    <el-dialog v-model="rasterMapVisible" :title="$t('rasterWmEmbed.rasterMapDialogTitle')" width="75%" class="raster-map-dialog" destroy-on-close @closed="destroyRasterMapView">
      <div class="raster-map-container" ref="rasterMapContainer" style="height: 500px;"></div>
    </el-dialog>

    <!-- CRMark 水印流程弹窗 -->
    <el-dialog v-model="crmarkDialogVisible" :title="$t('rasterWmEmbed.crmarkDialogTitle')" width="600px">
      <el-form label-width="120px">
        <el-form-item :label="$t('rasterWmEmbed.formApplicationId')">
          <el-input v-model="crmarkApplicationId" :placeholder="$t('rasterWmEmbed.placeholderEnterApplicationId')" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="crmarkEmbed">{{ $t('rasterWmEmbed.executeCrmarkEmbed') }}</el-button>
          <el-button @click="crmarkPreviewStego" :disabled="!crmarkResult.stego_path">{{ $t('rasterWmEmbed.previewStegoThumbnail') }}</el-button>
        </el-form-item>
        <el-form-item :label="$t('rasterWmEmbed.returnPaths')">
          <div>
            <div>stego_path：{{ crmarkResult.stego_path || $t('rasterWmEmbed.notReturned') }}</div>
            <div>wm_map_path：{{ crmarkResult.wm_map_path || $t('rasterWmEmbed.notReturned') }}</div>
            <div>wm_meta_path：{{ crmarkResult.wm_meta_path || $t('rasterWmEmbed.notReturned') }}</div>
          </div>
        </el-form-item>
        <el-form-item :label="$t('rasterWmEmbed.embeddedThumbnail')" v-if="crmarkResult.stego_preview_base64">
          <el-image :src="`data:image/png;base64,${crmarkResult.stego_preview_base64}`" fit="contain" style="width: 100%;" />
        </el-form-item>
        <el-form-item>
          <el-button type="success" @click="crmarkRecover" :disabled="!crmarkResult.stego_path || !crmarkResult.wm_map_path">{{ $t('rasterWmEmbed.recoverOriginal') }}</el-button>
          <el-button type="warning" @click="crmarkDecode" :disabled="!crmarkResult.stego_path || !crmarkResult.wm_map_path || !crmarkResult.wm_meta_path">{{ $t('rasterWmEmbed.decodeWatermark') }}</el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </template>

  <script setup>
  import { reactive, ref, onMounted, watch, nextTick } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { ElMessage, ElMessageBox } from 'element-plus';
  import axios from '@/utils/Axios';

  const { t } = useI18n();

  const data = reactive({ list: [] });
  const page = ref(1);
  const pageSize = ref(10);
  const total = ref(0);
  const viewDataVisible = ref(false);

  const selectedData = reactive({
    data_alias: '',
    data_id: '',
    data_file_path: '',
    applicant_name: '',
    applicant_user_number: '',
    preview_base64: ''
  });

  watch(page, (newValue, oldValue) => {
    if (oldValue !== newValue) {
      get_applications();
    }
  });

  const pageChanged = (newPage) => {
    page.value = newPage;
  };

  const getStatusText = (status) => {
    if (status === true) return t('rasterWmEmbed.statusPassed');
    if (status === false) return t('rasterWmEmbed.statusRejected');
    if (status === null) return t('rasterWmEmbed.statusPending');
    return '';
  };

  const get_applications = async () => {
    try {
      // 调用栅格数据专用的API端点
      const response = await axios.get(`/api/adm2_embedding_watermark_applications`, {
        params: { page: page.value, pageSize: pageSize.value, data_type: 'raster' },
        responseType: 'json'
      });

      if (!response.data || !response.data.status) {
        data.list = [];
        total.value = 0;
        ElMessage.error(response.data.msg || t('rasterWmEmbed.fetchFailed'));
        return;
      }

      data.list = response.data.application_data;
      total.value = response.data.pages.total;
    } catch (err) {
      console.error('Error fetching records:', err);
      ElMessage.error(t('rasterWmEmbed.fetchFailed'));
    }
  };

  onMounted(() => {
    get_applications();
  });

  const openDataPreviewDialog = async (row) => {
    selectedData.data_alias = row.data_alias ?? '';
    selectedData.data_id = row.data_id ?? '';
    selectedData.data_file_path = row.data_file_path || '';
    selectedData.applicant_name = row.applicant_name ?? '';
    selectedData.applicant_user_number = row.applicant_user_number ?? '';
    selectedData.preview_base64 = '';
    viewDataVisible.value = true;

    if (selectedData.data_file_path) {
      try {
        const resp = await axios.post(`/api/raster/preview`, {
          file_path: selectedData.data_file_path
        });
        selectedData.preview_base64 = resp.data?.base64 || resp.data?.png_base64 || '';
        if (!selectedData.preview_base64) {
          ElMessage.warning(t('rasterWmEmbed.noPreviewImage'));
        }
      } catch (e) {
        console.error('预览加载失败:', e);
        ElMessage.error(e.response?.data?.message || t('rasterWmEmbed.previewLoadFailed'));
      }
    } else {
      ElMessage.info(t('rasterWmEmbed.noPreviewPath'));
    }
  };

  const rasterMapVisible = ref(false);
  const rasterMapContainer = ref(null);
  let rasterMapInstance = null;

  const openRasterMapDialog = () => {
    if (!selectedData.data_id) {
      ElMessage.warning(t('rasterWmEmbed.cannotGetRasterId'));
      return;
    }
    rasterMapVisible.value = true;
    nextTick(() => {
      import('ol/Map').then(({ default: Map }) => {
      import('ol/View').then(({ default: OlView }) => {
        import('ol/layer/Tile').then(({ default: TileLayer }) => {
          import('ol/source').then(({ XYZ }) => {
            import('ol/proj').then(({ fromLonLat }) => {
              if (!rasterMapContainer.value) return;
              const tileUrl = `/api/raster_tiles/${selectedData.data_id}/{z}/{x}/{y}.png`;
              rasterMapInstance = new Map({
                target: rasterMapContainer.value,
                layers: [
                  new TileLayer({
                    source: new XYZ({
                      url: tileUrl,
                      maxZoom: 18
                    })
                  })
                ],
                view: new OlView({
                  projection: 'EPSG:3857',
                  center: fromLonLat([104.0, 35.0]),
                  zoom: 4
                })
              });
            });
          });
        });
      });
    }).catch(e => {
      console.error('地图加载失败', e);
      ElMessage.error(t('rasterWmEmbed.mapLoadFailed'));
    });
    });
  };

  const destroyRasterMapView = () => {
    if (rasterMapInstance) {
      rasterMapInstance.setTarget(null);
      rasterMapInstance = null;
    }
  };

  const handleClose = (done) => {
    ElMessageBox.confirm(t('rasterWmEmbed.confirmClose')).then(() => {
      done();
    }).catch(() => {});
  };

  /**
   * 栅格水印嵌入（LSB）
   * 小白解释：点"嵌入水印"后把申请编号发到后端，后端会把二维码水印塞进栅格图片里，返回一个可下载的文件。
   */
  const embedding_watermark = async (row) => {
    const ApplicationId = row.id;
    ElMessage.info(t('rasterWmEmbed.embeddingInProgress'));

    axios.post(`/api/admin/embed_dispatch`, {
      application_id: ApplicationId
    })
    .then(response => {
      if (response.data && response.data.status) {
        ElMessage.success(response.data.msg || t('rasterWmEmbed.embedSuccess'));
        get_applications();
      } else {
        ElMessage.error(response.data?.msg || t('rasterWmEmbed.embedFailed'));
      }
    })
    .catch(error => {
      ElMessage.error(t('rasterWmEmbed.embedFailed'));
      console.error('Error embedding watermark:', error);
    });
  };

  // ------------------------ CRMark 嵌入/恢复/解码 ------------------------
  const crmarkDialogVisible = ref(false);
  const crmarkApplicationId = ref('');
  const crmarkResult = reactive({ stego_path: '', wm_map_path: '', wm_meta_path: '', stego_preview_base64: '' });

  /**
   * 打开 CRMark 弹窗
   * 小白解释：选定这一条申请后，弹出窗口可以进行 CRMark 的嵌入、恢复、解码。
   */
  const openCrmarkDialog = (row) => {
    crmarkApplicationId.value = String(row.id || '');
    crmarkResult.stego_path = '';
    crmarkResult.wm_map_path = '';
    crmarkResult.wm_meta_path = '';
    crmarkResult.stego_preview_base64 = '';
    crmarkDialogVisible.value = true;
  };

  /**
   * CRMark 嵌入
   * 小白解释：把申请编号发到后端，后端用更复杂的算法（CRMark）把水印嵌到图片里，返回三个路径。
   */
  const crmarkEmbed = async () => {
    if (!crmarkApplicationId.value) { ElMessage.error(t('rasterWmEmbed.fillApplicationIdFirst')); return; }
    try {
      const resp = await axios.post(`/api/crmark/embed`, { application_id: crmarkApplicationId.value });
      crmarkResult.stego_path = resp.data?.stego_path || '';
      crmarkResult.wm_map_path = resp.data?.wm_map_path || '';
      crmarkResult.wm_meta_path = resp.data?.wm_meta_path || '';
      if (crmarkResult.stego_path) ElMessage.success(t('rasterWmEmbed.crmarkEmbedSuccess')); else ElMessage.error(t('rasterWmEmbed.noEmbedResultPath'));
    } catch (e) {
      console.error('CRMark嵌入失败:', e);
      ElMessage.error(e.response?.data?.message || t('rasterWmEmbed.crmarkEmbedFailed'));
    }
  };

  /**
   * 预览嵌入后的缩略图
   * 小白解释：把返回的 stego_path 发到预览接口，拿到图片的 Base64 内容，直接在前端显示。
   */
  const crmarkPreviewStego = async () => {
    if (!crmarkResult.stego_path) { ElMessage.error(t('rasterWmEmbed.completeEmbedFirst')); return; }
    try {
      const resp = await axios.post(`/api/raster/preview`, { file_path: crmarkResult.stego_path });
      crmarkResult.stego_preview_base64 = resp.data?.base64 || resp.data?.png_base64 || '';
      if (crmarkResult.stego_preview_base64) ElMessage.success(t('rasterWmEmbed.thumbnailLoadSuccess')); else ElMessage.error(t('rasterWmEmbed.thumbnailNotObtained'));
    } catch (e) {
      console.error('CRMark缩略图预览失败:', e);
      ElMessage.error(e.response?.data?.message || t('rasterWmEmbed.thumbnailPreviewFailed'));
    }
  };

  /**
   * CRMark 恢复原图（下载）
   * 小白解释：把 stego_path 和 wm_map_path 发给后端，后端把隐藏前的原图恢复出来，然后让浏览器下载。
   */
  const crmarkRecover = async () => {
    if (!crmarkResult.stego_path || !crmarkResult.wm_map_path) { ElMessage.error(t('rasterWmEmbed.completeEmbedFirst')); return; }
    try {
      const resp = await axios.post(`/api/crmark/recover`, { stego_path: crmarkResult.stego_path, wm_map_path: crmarkResult.wm_map_path }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'recovered_original.png');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      ElMessage.success(t('rasterWmEmbed.recoverSuccess'));
    } catch (e) {
      console.error('CRMark恢复失败:', e);
      ElMessage.error(e.response?.data?.message || t('rasterWmEmbed.recoverFailed'));
    }
  };

  /**
   * CRMark 解码水印（下载）
   * 小白解释：把三条路径发给后端，后端把水印图还原出来，然后让浏览器下载。
   */
  const crmarkDecode = async () => {
    if (!crmarkResult.stego_path || !crmarkResult.wm_map_path || !crmarkResult.wm_meta_path) { ElMessage.error(t('rasterWmEmbed.completeEmbedFirst')); return; }
    try {
      const resp = await axios.post(`/api/crmark/decode`, { stego_path: crmarkResult.stego_path, wm_map_path: crmarkResult.wm_map_path, wm_meta_path: crmarkResult.wm_meta_path }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'decoded_watermark.png');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      ElMessage.success(t('rasterWmEmbed.decodeSuccess'));
    } catch (e) {
      console.error('CRMark解码失败:', e);
      ElMessage.error(e.response?.data?.message || t('rasterWmEmbed.decodeFailed'));
    }
  };

  </script>

  <style scoped>
  .raster-embed-page {
    padding: 16px 20px;
    max-width: 1200px;
    margin: 0 auto;
    background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    border-radius: 12px;
    min-height: 400px;
  }
  .page-header-compact {
    margin-bottom: 16px;
  }
  .page-title {
    font-size: 18px;
    font-weight: 600;
    color: #334155;
    margin: 0 0 4px 0;
  }
  .page-desc {
    font-size: 13px;
    color: #64748b;
    margin: 0;
  }
  .embed-table-compact {
    width: 100%;
    --el-table-border-color: #e2e8f0;
    --el-table-header-bg-color: #f1f5f9;
  }
  .embed-table-compact :deep(.el-table__header th) {
    background: #e8f4f8 !important;
    color: #475569;
    font-weight: 600;
  }
  .embed-table-compact :deep(.el-table__row:hover > td) {
    background: #ecfdf5 !important;
  }

.action-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
  </style>
  <style>
  /* 样式与矢量数据代码保持一致，确保外观统一 */
  .qr-code-image {
    width: 50px;
    height: 50px;
  }

  .view-pagination{
    margin-top: 20px;
  }

  .dialog-container {
    display: flex;
    gap: 20px;
  }

  .raster-preview-layout .preview-main {
    flex: 3;
    min-width: 0;
  }

  .raster-preview-layout .raster-preview-container {
    flex: none;
    width: 100%;
    height: 320px;
    border-radius: 12px;
    overflow: hidden;
    background: #f1f5f9;
  }

  .raster-preview-layout .raster-actions {
    margin-top: 12px;
  }

  .raster-preview-layout .info-container {
    flex: 1;
    min-width: 260px;
    padding: 0;
  }

  .info-title {
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 12px 0;
  }

  .path-text {
    font-size: 12px;
    color: #64748b;
    word-break: break-all;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .raster-map-dialog .raster-map-container {
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
    background: #f1f5f9;
  }

  .dialog-container {
    display: flex;
  }

  .raster-preview-container {
    flex: 3;
    height: 400px;
    width: 70%;
    border: 1px dashed #ccc;
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
    color: #909399;
  }

  .info-container {
    flex: 1;
    padding-left: 20px;
  }
  </style>
