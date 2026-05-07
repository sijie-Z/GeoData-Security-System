<template>
  <div class="watermark-generation-page">
    <div class="page-header">
      <h1 class="page-title">水印生成</h1>
      <p class="page-desc">管理员填写生成信息后，可生成并预览二维码，同时支持地图预览、搜索定位与回退。</p>
    </div>

    <el-card class="table-card" shadow="hover">
      <el-table :data="data.list" border stripe v-loading="loading" empty-text="暂无可生成水印的记录">
        <el-table-column prop="id" label="申请编号" width="90" />
        <el-table-column prop="data_alias" label="数据名称" min-width="140" />
        <el-table-column prop="data_id" label="数据编号" width="120" />
        <el-table-column prop="applicant_user_number" label="申请人编号" width="120" />
        <el-table-column prop="applicant_name" label="申请人姓名" width="120" />
        <el-table-column label="一审状态" width="100" align="center">
          <template #default="scope">{{ getStatusText(scope.row.first_statu) }}</template>
        </el-table-column>
        <el-table-column label="二审状态" width="100" align="center">
          <template #default="scope">{{ getStatusText(scope.row.second_statu) }}</template>
        </el-table-column>
        <el-table-column label="水印" width="100" align="center">
          <template #default="scope">
            <el-image
              v-if="scope.row.qrcode"
              :src="`data:image/png;base64,${scope.row.qrcode}`"
              :preview-src-list="[`data:image/png;base64,${scope.row.qrcode}`]"
              fit="cover"
              style="width: 48px; height: 48px; border-radius: 6px;"
            />
            <span v-else style="color:#909399;">未生成</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" align="center" fixed="right">
          <template #default="scope">
            <el-button size="small" @click="openMapDialog(scope.row)">地图预览</el-button>
            <el-button size="small" type="primary" @click="openRequestDialog(scope.row)">生成水印</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="prev, pager, next, jumper, total"
        @current-change="pageChanged"
      />
    </div>

    <el-dialog
      v-model="requestDataVisible"
      width="560px"
      :close-on-click-modal="false"
      title="生成水印"
    >
      <el-form ref="requestFormRef" :model="requestInformation" :rules="rules" label-width="100px">
        <el-form-item label="申请编号" prop="application_id">
          <el-input v-model="requestInformation.application_id" readonly />
        </el-form-item>
        <el-form-item label="数据编号" prop="data_id">
          <el-input v-model="requestInformation.data_id" readonly />
        </el-form-item>
        <el-form-item label="数据名称" prop="data_alias">
          <el-input v-model="requestInformation.data_alias" readonly />
        </el-form-item>
        <el-form-item label="申请人姓名" prop="applicant_name">
          <el-input v-model="requestInformation.applicant_name" readonly />
        </el-form-item>
        <el-form-item label="申请原因" prop="reason">
          <el-input v-model="requestInformation.reason" type="textarea" :rows="2" placeholder="将写入二维码，可留空" />
        </el-form-item>
        <el-form-item label="使用目的" prop="purpose">
          <el-input v-model="requestInformation.purpose" type="textarea" :rows="2" placeholder="例如：科研分析、项目汇报" />
        </el-form-item>
        <el-form-item label="使用范围" prop="usage_scope">
          <el-input v-model="requestInformation.usage_scope" placeholder="例如：仅限部门内部" />
        </el-form-item>
        <el-form-item label="安全级别" prop="security_level">
          <el-select v-model="requestInformation.security_level" style="width:100%;" placeholder="请选择">
            <el-option label="普通" value="normal" />
            <el-option label="内部" value="internal" />
            <el-option label="敏感" value="sensitive" />
          </el-select>
        </el-form-item>
        <el-form-item label="标记标签" prop="custom_tag">
          <el-input v-model="requestInformation.custom_tag" placeholder="例如：2026Q2-专项" />
        </el-form-item>
        <el-form-item label="二维码预览">
          <div class="qr-preview-area">
            <el-image
              v-if="generatedQrcode"
              :src="`data:image/png;base64,${generatedQrcode}`"
              :preview-src-list="[generatedQrcode ? `data:image/png;base64,${generatedQrcode}` : '']"
              fit="contain"
              style="width: 140px; height: 140px; border: 1px solid #e5e7eb; border-radius: 8px;"
            />
            <span v-else style="color:#909399;">生成后可预览</span>
            <div v-if="generatedQrcode" class="qr-meta">
              <p v-if="generatedQrVersion">版本: V{{ generatedQrVersion }}</p>
              <p v-if="generatedSignature">签名: {{ generatedSignature }}</p>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="requestDataVisible=false">取消</el-button>
        <el-button type="primary" @click="generate">确认生成</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="mapDialogVisible"
      title="地图预览与定位"
      width="74%"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="destroyMapView"
    >
      <div class="map-toolbar">
        <el-input v-model="mapSearchKeyword" clearable placeholder="输入地名进行定位搜索" style="width: 320px" @keyup.enter="searchMap">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="searchMap">搜索定位</el-button>
        <el-button @click="goInitialExtent">回退视图</el-button>
        <el-button @click="clearSearchResult">清空定位</el-button>
      </div>
      <div class="map-dialog-layout">
        <div class="map-pane">
          <div ref="mapContainer" class="map-container"></div>
          <div v-if="!selectedMapRow.data_url" class="map-placeholder">
            <el-empty description="该记录缺少地图服务地址，无法加载" />
          </div>
        </div>
        <div class="info-pane">
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="申请编号">{{ selectedMapRow.id }}</el-descriptions-item>
            <el-descriptions-item label="数据名称">{{ selectedMapRow.data_alias }}</el-descriptions-item>
            <el-descriptions-item label="数据编号">{{ selectedMapRow.data_id }}</el-descriptions-item>
            <el-descriptions-item label="申请人">{{ selectedMapRow.applicant_name }} ({{ selectedMapRow.applicant_user_number }})</el-descriptions-item>
            <el-descriptions-item label="地图服务地址">
              <span class="url-text" :title="selectedMapRow.data_url">{{ selectedMapRow.data_url || '—' }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, watch, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import axios from '@/utils/Axios';
import { Search } from '@element-plus/icons-vue';
import '@arcgis/core/assets/esri/themes/light/main.css';
import MapView from '@arcgis/core/views/MapView';
import Map from '@arcgis/core/Map';
import MapImageLayer from '@arcgis/core/layers/MapImageLayer';
import FeatureLayer from '@arcgis/core/layers/FeatureLayer';
import GraphicsLayer from '@arcgis/core/layers/GraphicsLayer';
import Graphic from '@arcgis/core/Graphic';
import Point from '@arcgis/core/geometry/Point';

const data = reactive({ list: [] });
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const loading = ref(false);

const requestDataVisible = ref(false);
const requestFormRef = ref(null);
const generatedQrcode = ref('');
const generatedQrVersion = ref(null);
const generatedSignature = ref('');

const requestInformation = reactive({
  application_id: '',
  data_id: '',
  data_url: '',
  data_alias: '',
  applicant_name: '',
  applicant_user_number: '',
  adm1_name: '',
  adm2_name: '',
  reason: '',
  purpose: '',
  usage_scope: '',
  security_level: 'internal',
  custom_tag: ''
});

const rules = {
  application_id: [{ required: true, message: '缺少申请编号', trigger: 'blur' }],
  data_id: [{ required: true, message: '缺少数据编号', trigger: 'blur' }],
  data_alias: [{ required: true, message: '缺少数据名称', trigger: 'blur' }],
  applicant_name: [{ required: true, message: '缺少申请人姓名', trigger: 'blur' }]
};

const pageChanged = (newPage) => {
  page.value = newPage;
};

watch(page, (n, o) => {
  if (n !== o) get_applications();
});

const getStatusText = (status) => {
  if (status === true) return '通过';
  if (status === false) return '不通过';
  return '待审核';
};

const get_applications = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`/api/adm1_get_applications_generate_watermark`, {
      params: { page: page.value, pageSize: pageSize.value }
    });
    if (!response.data?.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data?.msg || '获取记录失败');
      return;
    }
    data.list = response.data.application_data || [];
    total.value = response.data.pages?.total ?? 0;
  } catch (_err) {
    ElMessage.error('获取记录失败');
  } finally {
    loading.value = false;
  }
};

const openRequestDialog = async (row) => {
  Object.assign(requestInformation, {
    application_id: row.id,
    data_id: row.data_id,
    data_url: row.data_url || '',
    data_alias: row.data_alias,
    applicant_name: row.applicant_name,
    applicant_user_number: row.applicant_user_number,
    adm1_name: row.adm1_name,
    adm2_name: row.adm2_name,
    reason: row.reason || '',
    purpose: row.purpose || '',
    usage_scope: row.usage_scope || '',
    security_level: row.security_level || 'internal',
    custom_tag: row.custom_tag || ''
  });
  generatedQrcode.value = row.qrcode || '';
  generatedQrVersion.value = row.qr_version || null;
  generatedSignature.value = row.qr_signature || '';
  requestDataVisible.value = true;
  await nextTick();
  requestFormRef.value?.clearValidate();
};

const generate = async () => {
  await requestFormRef.value?.validate();
  const resp = await axios.post(`/api/generate_watermark`, requestInformation);
  if (!resp.data?.status) {
    ElMessage.error(resp.data?.msg || '生成失败');
    return;
  }
  generatedQrcode.value = resp.data?.qrcode || '';
  generatedQrVersion.value = resp.data?.qr_version || null;
  generatedSignature.value = resp.data?.signature || '';
  ElMessage.success(`水印生成成功 (版本: V${generatedQrVersion.value})`);
  requestDataVisible.value = false;
  await get_applications();
};

const mapDialogVisible = ref(false);
const mapContainer = ref(null);
const mapSearchKeyword = ref('');
const selectedMapRow = reactive({
  id: '',
  data_alias: '',
  data_id: '',
  applicant_name: '',
  applicant_user_number: '',
  data_url: ''
});
let mapView = null;
let featureLayer = null;
let markerLayer = null;
let initialExtent = null;

const destroyMapView = () => {
  if (mapView) {
    mapView.destroy();
    mapView = null;
  }
  featureLayer = null;
  markerLayer = null;
  initialExtent = null;
};

const initializeMap = async (row) => {
  destroyMapView();
  if (!row.data_url || !mapContainer.value) return;
  markerLayer = new GraphicsLayer();
  featureLayer = new FeatureLayer({ url: row.data_url });
  const mapImageLayer = new MapImageLayer({ url: row.data_url });
  const map = new Map({
    basemap: 'topo-vector',
    layers: [mapImageLayer, featureLayer, markerLayer]
  });
  mapView = new MapView({
    container: mapContainer.value,
    map
  });
  await mapView.when();
  try {
    await featureLayer.when();
    const response = await featureLayer.queryExtent();
    if (response?.extent) {
      initialExtent = response.extent.clone();
      await mapView.goTo(response.extent);
    }
  } catch (_e) {}
  mapView.ui.remove('attribution');
};

const openMapDialog = async (row) => {
  selectedMapRow.id = row.id || '';
  selectedMapRow.data_alias = row.data_alias || '';
  selectedMapRow.data_id = row.data_id || '';
  selectedMapRow.applicant_name = row.applicant_name || '';
  selectedMapRow.applicant_user_number = row.applicant_user_number || '';
  selectedMapRow.data_url = row.data_url || '';
  mapSearchKeyword.value = '';
  mapDialogVisible.value = true;
  await nextTick();
  await initializeMap(row);
};

const searchMap = async () => {
  const keyword = mapSearchKeyword.value.trim();
  if (!keyword) {
    ElMessage.warning('请输入搜索关键词');
    return;
  }
  if (!mapView) {
    ElMessage.warning('地图尚未加载完成');
    return;
  }
  try {
    const resp = await axios.get(`/api/geocoding/search`, {
      params: { keyword }
    });
    const pois = resp.data?.pois || [];
    if (!pois.length) {
      ElMessage.warning('未找到匹配结果');
      return;
    }
    const [lon, lat] = String(pois[0].lonlat || '').split(',').map(v => Number(v));
    if (Number.isNaN(lon) || Number.isNaN(lat)) {
      ElMessage.warning('定位结果异常');
      return;
    }
    markerLayer?.removeAll();
    const point = new Point({ longitude: lon, latitude: lat });
    const marker = new Graphic({
      geometry: point,
      symbol: {
        type: 'simple-marker',
        color: '#ef4444',
        size: 12,
        outline: { color: '#ffffff', width: 1.5 }
      }
    });
    markerLayer?.add(marker);
    await mapView.goTo({ center: [lon, lat], zoom: 13 });
    ElMessage.success(`已定位：${pois[0].name || keyword}`);
  } catch (_err) {
    ElMessage.error('搜索定位失败');
  }
};

const goInitialExtent = async () => {
  if (!mapView || !initialExtent) {
    ElMessage.warning('暂无可回退视图');
    return;
  }
  await mapView.goTo(initialExtent);
};

const clearSearchResult = () => {
  markerLayer?.removeAll();
};

onMounted(() => {
  get_applications();
});
</script>

<style scoped>
.watermark-generation-page { padding: 20px 24px; }
.page-header { margin-bottom: 16px; }
.page-title { margin: 0 0 8px; font-size: 22px; color: #1f2937; }
.page-desc { margin: 0; color: #6b7280; }
.table-card { border-radius: 12px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
.map-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.map-dialog-layout { display: flex; gap: 16px; }
.map-pane { flex: 3; position: relative; height: 500px; border-radius: 10px; overflow: hidden; background: #f1f5f9; }
.map-container { width: 100%; height: 100%; }
.map-placeholder { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: #f8fafc; }
.info-pane { flex: 1; min-width: 260px; }
.url-text { word-break: break-all; color: #6b7280; font-size: 12px; }
.qr-preview-area { display: flex; flex-direction: column; gap: 8px; }
.qr-meta { font-size: 12px; color: #6b7280; }
.qr-meta p { margin: 4px 0; }
</style>
