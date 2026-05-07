<template>
  <div class="data-viewing-page">

    <div class="page-header">
      <h1 class="page-title">{{ $t('empDataView.pageTitle') }}</h1>
      <p class="page-subtitle">{{ $t('empDataView.pageSubtitle') }}</p>
    </div>

    <!-- 数据统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card vector">
        <div class="stat-icon">
          <el-icon><Location /></el-icon>
        </div>
        <div class="stat-content">
          <h3>{{ totalVector }}</h3>
          <p>{{ $t('empDataView.vectorDatasets') }}</p>
        </div>
      </div>
      <div class="stat-card raster">
        <div class="stat-icon">
          <el-icon><Picture /></el-icon>
        </div>
        <div class="stat-content">
          <h3>{{ totalRaster }}</h3>
          <p>{{ $t('empDataView.rasterDatasets') }}</p>
        </div>
      </div>
      <div class="stat-card total">
        <div class="stat-icon">
          <el-icon><DataAnalysis /></el-icon>
        </div>
        <div class="stat-content">
          <h3>{{ total }}</h3>
          <p>{{ $t('empDataView.totalData') }}</p>
        </div>
      </div>
    </div>

    <div class="content-panel-pro">

      <!-- 高级搜索区域 -->
      <div class="advanced-search-area">
        <div class="search-main">
          <el-input
            v-model="keyword"
            :placeholder="$t('empDataView.searchPlaceholder')"
            :prefix-icon="Search"
            size="large"
            clearable
            @keydown.enter="handleSearch"
            @clear="handleSearch"
            class="search-input"
          />
          <el-button type="primary" size="large" :icon="Search" @click="handleSearch" class="search-btn">
            {{ $t('empDataView.search') }}
          </el-button>
        </div>
        <div class="search-filters">
          <el-select v-model="dataSourceFilter" :placeholder="$t('empDataView.dataSource')" clearable size="large" class="filter-select">
            <el-option :label="$t('empDataView.sourceNaturalResources')" value="自然资源部" />
            <el-option :label="$t('empDataView.sourceCAS')" value="中科院" />
            <el-option :label="$t('empDataView.sourceSurveyBureau')" value="测绘局" />
          </el-select>
          <el-select v-model="timeFilter" :placeholder="$t('empDataView.timeRange')" clearable size="large" class="filter-select">
            <el-option :label="$t('empDataView.recentWeek')" value="week" />
            <el-option :label="$t('empDataView.recentMonth')" value="month" />
            <el-option :label="$t('empDataView.recentYear')" value="year" />
          </el-select>
        </div>
      </div>
      <!-- 数据类型切换 - 专业风格 -->
      <div class="data-type-toggle-pro">
        <div class="toggle-header">
          <h3>{{ $t('empDataView.dataType') }}</h3>
          <div class="toggle-switch">
            <button
              :class="['toggle-btn', { active: activeDataType === 'vector' }]"
              @click="activeDataType = 'vector'"
            >
              <el-icon><Location /></el-icon>
              {{ $t('empDataView.vectorData') }}
            </button>
            <button
              :class="['toggle-btn', { active: activeDataType === 'raster' }]"
              @click="activeDataType = 'raster'"
            >
              <el-icon><Picture /></el-icon>
              {{ $t('empDataView.rasterData') }}
            </button>
          </div>
        </div>
      </div>

      <!-- 数据表格区域 - 专业风格 -->
      <div class="table-container-pro">
        <div class="table-header">
          <h3>{{ activeDataType === 'vector' ? $t('empDataView.vectorData') : $t('empDataView.rasterData') }}{{ $t('empDataView.listSuffix') }}</h3>
          <div class="table-actions">
            <el-button :icon="Refresh" @click="fetchData" circle size="small" />
            <el-button :icon="Download" @click="exportData" circle size="small" />
          </div>
        </div>

        <el-table :data="data.list" style="width: 100%" class="custom-table-pro" v-loading="loading" stripe>
          <el-table-column type="selection" width="55" align="center" />
          <el-table-column prop="data_id" label="ID" width="80" align="center">
            <template #default="scope">
              <span class="data-id">{{ scope.row.data_id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="data_alias" :label="$t('empDataView.dataName')" min-width="160" align="left" show-overflow-tooltip>
            <template #default="scope">
              <div class="data-name-cell">
                <el-icon :class="activeDataType === 'vector' ? 'vector-icon' : 'raster-icon'">
                  <Location v-if="activeDataType === 'vector'" />
                  <Picture v-else />
                </el-icon>
                <span>{{ scope.row.data_alias }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="uuid" :label="$t('empDataView.dataIdentifier')" min-width="200" align="left" show-overflow-tooltip>
            <template #default="scope">
              <span class="uuid-text">{{ scope.row.uuid }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="data_source" :label="$t('empDataView.dataSource')" min-width="120" align="center" show-overflow-tooltip>
            <template #default="scope">
              <el-tag size="small" type="info">{{ scope.row.data_source || 'N/A' }}</el-tag>
            </template>
          </el-table-column>

          <!-- 矢量数据专用列 -->
          <el-table-column v-if="activeDataType === 'vector'" prop="geomtype" :label="$t('empDataView.geomType')" width="120" align="center">
            <template #default="scope">
              <el-tag size="small" :type="getGeomTypeColor(scope.row.geomtype)">
                {{ scope.row.geomtype }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="activeDataType === 'vector'" prop="coordinate_system" :label="$t('empDataView.coordSystem')" width="140" align="center" show-overflow-tooltip>
            <template #default="scope">
              <span class="coord-system">{{ scope.row.coordinate_system || 'N/A' }}</span>
            </template>
          </el-table-column>

          <!-- 栅格数据专用列 -->
          <el-table-column v-if="activeDataType === 'raster'" prop="band_count" :label="$t('empDataView.bandCount')" width="100" align="center">
            <template #default="scope">
              <el-tag size="small" type="warning">{{ scope.row.band_count }}{{ $t('empDataView.bands') }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="activeDataType === 'raster'" prop="pixel_type" :label="$t('empDataView.pixelType')" width="130" align="center">
            <template #default="scope">
              <span class="pixel-type">{{ scope.row.pixel_type }}</span>
            </template>
          </el-table-column>

          <el-table-column :label="$t('empDataView.actions')" width="200" align="center" fixed="right">
            <template #default="scope">
              <div class="action-buttons">
                <el-button
                  link
                  type="primary"
                  @click="openMapDialog(scope.row)"
                  class="action-btn"
                >
                  <el-icon><View /></el-icon>
                  {{ $t('empDataView.view') }}
                </el-button>
                <el-divider direction="vertical" />
                <el-button
                  link
                  type="success"
                  @click="openRequestDialog(scope.row)"
                  class="action-btn"
                >
                  <el-icon><Download /></el-icon>
                  {{ $t('empDataView.apply') }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>


      <div class="pagination-wrapper">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          @current-change="pageChanged"
        />
      </div>
    </div>
  </div>

  <el-dialog
    v-model="viewDataVisible"
    width="65%"
    custom-class="preview-dialog rounded-dialog"
    :show-close="false"
    top="13vh"
    draggable
    :overflow="true"
    @closed="destroyMapView"
  >
    <template #header="{ close }">
      <div class="dialog-header-custom">
        <h4 class="header-main-title">{{ $t('empDataView.dataView') }}</h4>
        <el-button text circle :icon="Close" @click="close" class="header-close-btn" :title="$t('empDataView.close')"></el-button>
      </div>
    </template>
    <div class="dialog-layout">
      <div class="map-view" ref="mapContainer">
        <el-button
          circle
          :icon="ArrowLeftBold"
          class="map-back-btn"
          @click="viewDataVisible = false"
          :title="$t('empDataView.back')"
        />
        <div class="map-search-bar" v-if="isVectorData">
          <el-input
            v-model="mapSearchKeyword"
            :placeholder="$t('empDataView.mapSearchPlaceholder')"
            :prefix-icon="Search"
            clearable
            @keydown.enter="handleMapSearch"
            class="search-input-custom"
          />
          <el-button
            :icon="Search"
            @click="handleMapSearch"
            class="search-btn-custom"
            circle
          />
          <el-button
            :title="$t('empDataView.undoView')"
            @click="undoMapView"
            class="search-btn-custom"
            circle
          >↶</el-button>
          <el-button
            :title="$t('empDataView.redoView')"
            @click="redoMapView"
            class="search-btn-custom"
            circle
          >↷</el-button>
        </div>

        <div class="map-tool-panel">
          <el-segmented
            v-model="currentBaseType"
            :options="[
              { label: $t('empDataView.vectorBaseMap'), value: 'vec' },
              { label: $t('empDataView.imageBaseMap'), value: 'img' }
            ]"
            @change="switchBaseMap"
          />
          <el-button class="map-mini-btn" @click="resetMapView">{{ $t('empDataView.resetView') }}</el-button>
          <div v-if="!isVectorData" class="raster-opacity-wrap">
            <span>{{ $t('empDataView.rasterOpacity') }}</span>
            <el-slider v-model="rasterOpacity" :min="0.2" :max="1" :step="0.05" @input="updateRasterOpacity" />
          </div>
        </div>

      </div>
      <div class="info-view">
        <div class="info-header-flex">
          <h3 class="info-title">{{ selectedData.data_alias }}</h3>
        </div>
        <div class="info-content-scroll">
          <p class="info-description">{{ selectedData.data_introduction }}</p>
          <el-divider style="margin: 24px 0;" />
          <h4 class="details-subtitle">{{ $t('empDataView.details') }}</h4>
          <ul class="meta-list">
            <li v-if="isVectorData"><span>{{ $t('empDataView.coordSystem') }}</span><strong>{{ selectedData.coordinate_system || 'N/A' }}</strong></li>
            <li v-if="isVectorData"><span>{{ $t('empDataView.geomType') }}</span><strong>{{ selectedData.geomtype || 'N/A' }}</strong></li>
            <li v-if="!isVectorData"><span>{{ $t('empDataView.bandCount') }}</span><strong>{{ selectedData.band_count || 'N/A' }}</strong></li>
            <li v-if="!isVectorData"><span>{{ $t('empDataView.pixelType') }}</span><strong>{{ selectedData.pixel_type || 'N/A' }}</strong></li>
            <li><span>{{ $t('empDataView.dataSource') }}</span><strong>{{ selectedData.data_source || 'N/A' }}</strong></li>
            <li class="meta-uuid"><span>{{ $t('empDataView.uniqueIdentifier') }}</span><strong>{{ selectedData.uuid }}</strong></li>
          </ul>
        </div>
        <div class="info-footer-flex">
          <el-button type="primary" size="large" class="apply-btn" @click="openRequestDialog(selectedData)">
            {{ $t('empDataView.applyForData') }}
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>


  <el-dialog
    v-model="requestDataVisible"
    :title="$t('empDataView.applyForData')"
    width="600px"
    draggable
    custom-class="rounded-dialog"
    :before-close="(done) => handleClose('request', done)"
  >
    <el-form
      ref="requestFormRef"
      :model="requestInformation"
      :rules="rules"
      label-width="100px"
      style="padding-right: 30px;"
    >
      <el-form-item :label="$t('empDataView.dataId')" required>
        <el-input v-model="requestInformation.data_id" disabled />
      </el-form-item>
      <el-form-item :label="$t('empDataView.dataName')" required>
        <el-input v-model="requestInformation.data_alias" disabled />
      </el-form-item>
      <el-form-item :label="$t('empDataView.applicantName')" prop="applicant">
        <el-input v-model="requestInformation.applicant" :placeholder="$t('empDataView.enterApplicantName')" />
      </el-form-item>
      <el-form-item :label="$t('empDataView.employeeNumber')" prop="user_number">
        <el-input v-model="requestInformation.user_number" :placeholder="$t('empDataView.enterEmployeeNumber')" />
      </el-form-item>
      <el-form-item :label="$t('empDataView.applyReason')" prop="reason">
        <el-input
          v-model="requestInformation.reason"
          type="textarea"
          :rows="4"
          :placeholder="$t('empDataView.enterReason')"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer-left">
        <el-button type="primary" @click="submitForm">{{ $t('empDataView.submitApplication') }}</el-button>
        <el-button @click="resetForm">{{ $t('empDataView.reset') }}</el-button>
      </div>
    </template>
  </el-dialog>

</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { Search, Close, ArrowLeftBold, Location, Picture, DataAnalysis, View, Download, Refresh } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox, ElDivider } from 'element-plus';
import axios from '@/utils/Axios';
import { useUserStore } from '@/stores/userStore';

import 'ol/ol.css';
import Map from 'ol/Map';
import OlView from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import { TileWMS, XYZ } from 'ol/source';
import { ScaleLine, Rotate, defaults as defaultControls } from 'ol/control';

const { t } = useI18n();

const tiandituKey = import.meta.env.VITE_TIANDITU_KEY || '11ac7f190ef74ee4bd64081fe7ae419c';

const loading = ref(true);
const data = reactive({ list: [] });
const keyword = ref('');
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const totalVector = ref(0);
const totalRaster = ref(0);
const viewDataVisible = ref(false);
const requestDataVisible = ref(false);
const mapContainer = ref(null);
const mapView = ref(null);
const requestFormRef = ref(null);
const mapSearchKeyword = ref('');
const mapViewHistory = ref([]);
const mapViewFuture = ref([]);
const baseVecLayerRef = ref(null);
const baseLabelLayerRef = ref(null);
const baseImgLayerRef = ref(null);
const rasterLayerRef = ref(null);
const currentBaseType = ref('vec');
const rasterOpacity = ref(1);
const defaultMapCenter = [104.0, 35.0];
const defaultMapZoom = 4;
const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);
const activeDataType = ref('vector');
const isVectorData = computed(() => activeDataType.value === 'vector');
const dataSourceFilter = ref('');
const timeFilter = ref('');

const selectedData = reactive({ data_id: '', uuid: '', data_alias: '', data_introduction: '', geomtype: '', coordinate_system: '', data_source: '', data_url: '', layer: '', band_count: null, pixel_type: null });

// 【关键修复 1】: 确保 initialRequestInformation 包含后端需要的所有字段
// 从您提供的"最初版本"代码学习，我们添加了 data_name, uuid, data_url, layer
const initialRequestInformation = { data_id: '', data_alias: '', applicant: '', user_number: '', reason: '', uuid: '', data_url: '', layer: '' };
const requestInformation = reactive({ ...initialRequestInformation });

const rules = computed(() => ({
  applicant: [{ required: true, message: t('empDataView.rulesApplicant'), trigger: 'blur' }],
  user_number: [{ required: true, message: t('empDataView.rulesUserNumber'), trigger: 'blur' }],
  reason: [{ required: true, message: t('empDataView.rulesReason'), trigger: 'blur' }],
}));

// 获取几何类型颜色
const getGeomTypeColor = (type) => {
  const colorMap = {
    '点': 'primary',
    '线': 'success',
    '面': 'warning',
    'Point': 'primary',
    'LineString': 'success',
    'Polygon': 'warning'
  };
  return colorMap[type] || 'info';
};

// 导出数据
const exportData = () => {
  ElMessage.success(t('empDataView.exportInDevelopment'));
};

const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`/api/data_viewing`, {
      params: {
        page: page.value,
        pageSize: pageSize.value,
        keyword: keyword.value || undefined,
        dataType: activeDataType.value,
        dataSource: dataSourceFilter.value || undefined,
        timeRange: timeFilter.value || undefined
      }
    });
    const result = response.data;
    if (result && result.data && Array.isArray(result.data.list)) {
      data.list = result.data.list.sort((a, b) => a.data_id - b.data_id);
      total.value = result.data.pages.total;

      // 更新统计数据
      if (result.data.stats) {
        totalVector.value = result.data.stats.vectorCount || 0;
        totalRaster.value = result.data.stats.rasterCount || 0;
      }
    } else {
      data.list = [];
      total.value = 0;
      ElMessage.error(t('empDataView.fetchDataFailed'));
    }
  } catch (error) {
    console.error('Error fetching data:', error);
    data.list = [];
    total.value = 0;
    ElMessage.error(t('empDataView.fetchDataError'));
  } finally {
    loading.value = false;
  }
};
// 监听筛选条件变化
watch([activeDataType, dataSourceFilter, timeFilter], () => {
  page.value = 1;
  fetchData();
});

const pageChanged = (newPage) => {
  page.value = newPage;
  fetchData();
};

const handleSearch = () => {
  page.value = 1;
  fetchData();
};

const openMapDialog = (row) => {
  Object.assign(selectedData, row);
  mapSearchKeyword.value = '';
  viewDataVisible.value = true;
  nextTick(() => { initializeMapView(row.data_url, row.layer); });
};

// 【关键修复 2】: 在打开申请对话框时，填充所有需要的字段到 requestInformation 对象中
const openRequestDialog = (dataToApply) => {
  requestInformation.reason = '';
  Object.assign(requestInformation, { data_id: dataToApply.data_id, data_alias: dataToApply.data_alias, applicant: userName.value, user_number: userNumber.value, uuid: dataToApply.uuid, data_url: dataToApply.data_url, layer: dataToApply.layer });
  requestDataVisible.value = true;
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm(t('empDataView.confirmClose')).then(() => {
    done();
    if (dialogType === 'request') resetForm();
  }).catch(() => {});
};

const submitForm = () => {
  requestFormRef.value.validate((valid) => {
    if (valid) {
      // 发送包含了所有后端所需字段的 requestInformation 对象
      axios.post(`/api/submit_application`, requestInformation)
        .then(() => {
            ElMessage.success(t('empDataView.submitSuccess'));
            requestDataVisible.value = false;
        })
        .catch(error => {
            // 这里的 console.error 会捕获并打印详细的 400 错误信息
            console.error('Error submitting application:', error);
            const errorMsg = error.response?.data?.message || t('empDataView.submitFailed');
            ElMessage.error(errorMsg);
        });
    }
  });
};

const pushCurrentViewToHistory = () => {
  if (!mapView.value) return;
  const view = mapView.value.getView();
  const center = view.getCenter();
  if (!center) return;
  mapViewHistory.value.push({
    center: [...center],
    zoom: view.getZoom() || 4,
  });
  if (mapViewHistory.value.length > 30) {
    mapViewHistory.value.shift();
  }
};

const undoMapView = () => {
  if (!mapView.value || mapViewHistory.value.length < 2) {
    ElMessage.info(t('empDataView.noUndoView'));
    return;
  }
  const current = mapViewHistory.value.pop();
  if (current) mapViewFuture.value.push(current);
  const prev = mapViewHistory.value[mapViewHistory.value.length - 1];
  if (prev) {
    mapView.value.getView().animate({ center: prev.center, zoom: prev.zoom, duration: 400 });
  }
};

const redoMapView = () => {
  if (!mapView.value || mapViewFuture.value.length === 0) {
    ElMessage.info(t('empDataView.noRedoView'));
    return;
  }
  const next = mapViewFuture.value.pop();
  if (next) {
    mapView.value.getView().animate({ center: next.center, zoom: next.zoom, duration: 400 });
    mapViewHistory.value.push(next);
  }
};

const switchBaseMap = () => {
  if (!baseVecLayerRef.value || !baseLabelLayerRef.value || !baseImgLayerRef.value) return;
  const useVec = currentBaseType.value === 'vec';
  baseVecLayerRef.value.setVisible(useVec);
  baseLabelLayerRef.value.setVisible(useVec);
  baseImgLayerRef.value.setVisible(!useVec);
};

const resetMapView = () => {
  if (!mapView.value) return;
  mapView.value.getView().animate({ center: defaultMapCenter, zoom: defaultMapZoom, duration: 600 });
};

const updateRasterOpacity = () => {
  if (rasterLayerRef.value) {
    rasterLayerRef.value.setOpacity(rasterOpacity.value);
  }
};
const resetForm = () => {
    // 只重置用户可编辑的字段，保留预填信息
    if (requestFormRef.value) {
        requestFormRef.value.resetFields();
    }
};

const handleMapSearch = async () => {
  if (!mapSearchKeyword.value.trim() || !mapView.value) { if (!mapSearchKeyword.value.trim()) ElMessage.warning(t('empDataView.enterSearchKeyword')); return; }
  try {
    const response = await axios.get(`/api/geocoding/search`, { params: { keyword: mapSearchKeyword.value.trim() } });
    const results = response.data?.data?.results || [];
    if (results.length > 0) {
      const first = results[0];
      const lonlat = [Number(first.lng), Number(first.lat)];
      pushCurrentViewToHistory();
      mapViewFuture.value = [];
      mapView.value.getView().animate({ center: lonlat, zoom: 14, duration: 1000 });
      mapViewHistory.value.push({ center: lonlat, zoom: 14 });
    } else { ElMessage.warning(t('empDataView.mapSearchNotFound', { keyword: mapSearchKeyword.value })); }
  } catch (error) {
    console.error('地图搜索失败 (通过后端代理):', error);
    const errorMsg = error.response?.data?.message || t('empDataView.mapSearchError');
    ElMessage.error(errorMsg);
  }
};
const initializeMapView = async (url, fullLayerName) => {
  if (!mapContainer.value) return;
      destroyMapView();

      baseVecLayerRef.value = new TileLayer({
        source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }),
        visible: true,
      });
      baseLabelLayerRef.value = new TileLayer({
        source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }),
        visible: true,
      });
      baseImgLayerRef.value = new TileLayer({
        source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=img_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }),
        visible: false,
      });

      const map = new Map({
        target: mapContainer.value,
        layers: [baseVecLayerRef.value, baseLabelLayerRef.value, baseImgLayerRef.value],
        view: new OlView({
          projection: 'EPSG:4326', // 或者 'EPSG:3857'，根据实际瓦片服务的投影来设置
          center: defaultMapCenter,
          zoom: defaultMapZoom,
        }),
        controls: defaultControls().extend([
          new ScaleLine({ units: 'metric' }),
          new Rotate({ autoHide: false, className: 'ol-rotate ol-control-custom-rotate' })
        ])
      });
      mapView.value = map;
      mapViewHistory.value = [];
      mapViewFuture.value = [];
      switchBaseMap();
      pushCurrentViewToHistory();
      map.on('moveend', () => {
        const view = map.getView();
        const center = view.getCenter();
        if (!center) return;
        const last = mapViewHistory.value[mapViewHistory.value.length - 1];
        const zoom = view.getZoom() || 4;
        if (!last || last.zoom !== zoom || last.center[0] !== center[0] || last.center[1] !== center[1]) {
          mapViewHistory.value.push({ center: [...center], zoom });
          if (mapViewHistory.value.length > 30) mapViewHistory.value.shift();
        }
      });

      if (isVectorData.value && url && fullLayerName) {
        try {
          // 添加WMS图层用于矢量数据
          map.addLayer(new TileLayer({
            source: new TileWMS({
              url: url,
              params: { 'LAYERS': fullLayerName, 'TILED': true },
              serverType: 'geoserver',
            }),
          }));
          // ... (WMS GetCapabilities logic) ...
        } catch (error) {
          console.error('Error loading WMS layer:', error);
          ElMessage.error(t('empDataView.loadWmsFailed'));
        }
      } else if (!isVectorData.value && selectedData.data_id) {
        // 添加XYZ瓦片图层用于栅格数据
        rasterLayerRef.value = new TileLayer({
          source: new XYZ({
            url: `/api/raster_tiles/${selectedData.data_id}/{z}/{x}/{y}.png`, // 指向我们新的瓦片服务API
            maxZoom: 18, // 根据实际情况调整最大缩放级别
          }),
          opacity: rasterOpacity.value,
        });
        map.addLayer(rasterLayerRef.value);
        // 可能需要根据栅格数据的范围调整地图的初始视图
        // 例如：map.getView().fit(extent, map.getSize());
      } else {
        rasterLayerRef.value = null;
      }
    };
const destroyMapView = () => {
  if (mapView.value) {
    mapView.value.setTarget(null);
    mapView.value = null;
  }
  baseVecLayerRef.value = null;
  baseLabelLayerRef.value = null;
  baseImgLayerRef.value = null;
  rasterLayerRef.value = null;
};
onMounted(fetchData);
</script>

<style scoped>
.rounded-dialog { border-radius: 12px; overflow: hidden; }
.rounded-dialog :deep(.el-dialog__header) { margin-right: 0; padding-top: 20px; }
/* 地理空间数据云风格的专业样式 */
.data-viewing-page {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 24px 32px;
  min-height: calc(100vh - 50px);
}

.page-header {
  margin-bottom: 32px;
  text-align: center;
}

.page-title {
  font-size: 36px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0 0 8px 0;
  background: linear-gradient(45deg, #3498db, #2c3e50);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 16px;
  color: #7f8c8d;
  margin: 0;
  font-weight: 400;
}

/* 统计卡片样式 - 参考地理空间数据云 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 28px 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, rgba(255,255,255,0.1), transparent);
  pointer-events: none;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 40px rgba(102, 126, 234, 0.4);
}

.stat-card.vector {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  box-shadow: 0 10px 30px rgba(79, 172, 254, 0.3);
}

.stat-card.raster {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
  box-shadow: 0 10px 30px rgba(67, 233, 123, 0.3);
}

.stat-card.total {
  background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
  box-shadow: 0 10px 30px rgba(250, 112, 154, 0.3);
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: white;
  backdrop-filter: blur(10px);
}

.stat-content h3 {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin: 0 0 4px 0;
  text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-content p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
  margin: 0;
  font-weight: 500;
}

/* 内容面板样式 */
.content-panel-pro {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px;
  padding: 32px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
}

/* 高级搜索区域 */
.advanced-search-area {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  border: 1px solid rgba(233, 236, 239, 0.5);
}

.search-main {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.search-input {
  flex: 1;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  border: 2px solid #e9ecef;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.search-input :deep(.el-input__wrapper):hover {
  border-color: #3498db;
  box-shadow: 0 6px 20px rgba(52, 152, 219, 0.15);
}

.search-input :deep(.el-input__wrapper).is-focus {
  border-color: #2980b9;
  box-shadow: 0 6px 20px rgba(41, 128, 185, 0.2);
}

.search-btn {
  border-radius: 12px;
  padding: 12px 24px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
  transition: all 0.3s ease;
}

.search-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(52, 152, 219, 0.4);
}

.search-filters {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-select {
  min-width: 180px;
}

.filter-select :deep(.el-select__wrapper) {
  border-radius: 10px;
  border: 2px solid #e9ecef;
  transition: all 0.3s ease;
}

.filter-select :deep(.el-select__wrapper):hover {
  border-color: #3498db;
}

/* 数据类型切换 - 现代风格 */
.data-type-toggle-pro {
  margin-bottom: 24px;
}

.toggle-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toggle-header h3 {
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.toggle-switch {
  display: flex;
  background: #f8f9fa;
  border-radius: 12px;
  padding: 4px;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06);
}

.toggle-btn {
  padding: 12px 24px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #6c757d;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-btn:hover {
  color: #495057;
  background: rgba(255, 255, 255, 0.5);
}

.toggle-btn.active {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
}

.toggle-btn.active:hover {
  background: linear-gradient(135deg, #2980b9 0%, #1f4e79 100%);
}

/* 表格容器 */
.table-container-pro {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: 1px solid #e9ecef;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-bottom: 1px solid #dee2e6;
}

.table-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.table-actions .el-button {
  border-radius: 8px;
  transition: all 0.3s ease;
}

.table-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 自定义表格样式 */
:deep(.custom-table-pro) {
  font-size: 14px;
}

:deep(.custom-table-pro .el-table__header-wrapper) {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

:deep(.custom-table-pro th) {
  font-weight: 600;
  color: #2c3e50;
  background: transparent !important;
  padding: 16px 12px;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

:deep(.custom-table-pro .el-table__row) {
  transition: all 0.3s ease;
}

:deep(.custom-table-pro .el-table__row:hover>td) {
  background-color: #f8f9fa !important;
  transform: scale(1.01);
}

:deep(.custom-table-pro td) {
  padding: 16px 12px;
  border-bottom: 1px solid #e9ecef;
}

/* 数据ID样式 */
.data-id {
  font-weight: 600;
  color: #3498db;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

/* 数据名称单元格 */
.data-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.data-name-cell .el-icon {
  font-size: 16px;
  color: #3498db;
}

.data-name-cell .el-icon.vector-icon {
  color: #4facfe;
}

.data-name-cell .el-icon.raster-icon {
  color: #43e97b;
}

/* UUID文本 */
.uuid-text {
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #6c757d;
  background: #f8f9fa;
  padding: 2px 6px;
  border-radius: 4px;
}

/* 坐标系样式 */
.coord-system {
  font-size: 12px;
  color: #495057;
  font-family: 'Courier New', monospace;
}

/* 像元类型 */
.pixel-type {
  font-size: 12px;
  color: #495057;
  font-weight: 500;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 分页样式 */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 32px;
}

:deep(.el-pagination) {
  --el-pagination-bg-color: white;
  --el-pagination-button-bg-color: white;
  --el-pagination-hover-color: #3498db;
}

:deep(.el-pagination.is-background .el-pager li) {
  border-radius: 8px;
  margin: 0 4px;
  transition: all 0.3s ease;
}

:deep(.el-pagination.is-background .el-pager li.active) {
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  border-color: #2980b9;
}

/* 几何类型标签 */
:deep(.el-tag) {
  border-radius: 6px;
  font-weight: 500;
  font-size: 12px;
}

/* 对话框样式 */
:deep(.preview-dialog) {
  --el-dialog-border-radius: 20px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

:deep(.preview-dialog .el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid rgba(233, 236, 239, 0.5);
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 20px 20px 0 0;
}

.header-main-title {
  font-size: 20px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.dialog-layout {
  display: flex;
  width: 100%;
  height: 70vh;
  max-height: 660px;
}

.map-view {
  flex: 4;
  background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
  position: relative;
  border-radius: 0 0 0 16px;
}

.info-view {
  flex: 3;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.95);
  border-left: 1px solid rgba(233, 236, 239, 0.5);
  border-radius: 0 0 16px 0;
}

.info-header-flex {
  padding: 24px;
  border-bottom: 1px solid rgba(233, 236, 239, 0.5);
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
}

.info-title {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
  line-height: 1.4;
}

.info-content-scroll {
  flex-grow: 1;
  overflow-y: auto;
  padding: 24px;
}

.info-description {
  font-size: 15px;
  line-height: 1.8;
  color: #495057;
  margin: 0 0 24px 0;
}

.details-subtitle {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #3498db;
}

.meta-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #e9ecef;
}

.meta-list li {
  display: grid;
  grid-template-columns: 120px 1fr;
  align-items: stretch;
  font-size: 14px;
  border-bottom: 1px solid #e9ecef;
}

.meta-list li:last-child {
  border-bottom: none;
}

.meta-list li span {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 16px 20px;
  color: #495057;
  font-weight: 600;
  display: flex;
  align-items: center;
  border-right: 1px solid #e9ecef;
}

.meta-list li strong {
  padding: 16px 20px;
  color: #2c3e50;
  font-weight: 500;
  text-align: left;
  display: flex;
  align-items: center;
  background: white;
}

.meta-list .meta-uuid strong {
  word-break: break-all;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  color: #6c757d;
}

.info-footer-flex {
  padding: 24px;
  border-top: 1px solid rgba(233, 236, 239, 0.5);
  background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
  border-radius: 0 0 16px 0;
}

.apply-btn {
  width: 100%;
  border-radius: 12px;
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  border: none;
  transition: all 0.3s ease;
}

.apply-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(52, 152, 219, 0.4);
  background: linear-gradient(135deg, #2980b9 0%, #1f4e79 100%);
}

/* 地图搜索栏 */
.map-search-bar {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  width: 400px;
  max-width: 60%;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input-custom {
  flex-grow: 1;
}

.search-input-custom :deep(.el-input__wrapper) {
  border-radius: 12px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.search-btn-custom {
  flex-shrink: 0;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
  border: none;
  color: white;
  box-shadow: 0 4px 12px rgba(52, 152, 219, 0.3);
  transition: all 0.3s ease;
}

.search-btn-custom:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(52, 152, 219, 0.4);
}

.map-back-btn {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 10;
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  transition: all 0.3s ease;
}

.map-back-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
  background: white;
}

/* 地图控件样式 */
.map-view :deep(.ol-zoom) {
  top: 80px;
  left: 20px;
  background: transparent;
}

.map-view :deep(.ol-zoom-in),
.map-view :deep(.ol-zoom-out) {
  width: 44px;
  height: 44px;
  font-size: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  color: #2c3e50;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.map-view :deep(.ol-zoom-in) {
  border-radius: 12px 12px 0 0;
  margin-bottom: 4px;
}

.map-view :deep(.ol-zoom-out) {
  border-radius: 0 0 12px 12px;
}

.map-view :deep(.ol-zoom-in:hover),
.map-view :deep(.ol-zoom-out:hover) {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.map-view :deep(.ol-control-custom-rotate) {
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 50%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.map-view :deep(.ol-control-custom-rotate:hover) {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.map-view :deep(.ol-scale-line) {
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 8px 12px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

/* 对话框页脚 */
.dialog-footer-left {
  width: 100%;
  text-align: left;
  display: flex;
  gap: 12px;
}

.dialog-footer-left .el-button {
  border-radius: 10px;
  padding: 12px 24px;
  font-weight: 500;
  transition: all 0.3s ease;
}

/* 栅格数据覆盖层 */
.raster-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(227, 242, 253, 0.9) 0%, rgba(187, 222, 251, 0.9) 100%);
  backdrop-filter: blur(5px);
  z-index: 100;
}

.raster-overlay .el-alert {
  width: 80%;
  max-width: 400px;
  border-radius: 12px;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .data-viewing-page {
    padding: 16px 20px;
  }

  .stats-cards {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .stat-card {
    padding: 20px 16px;
  }

  .stat-content h3 {
    font-size: 24px;
  }

  .content-panel-pro {
    padding: 20px;
    border-radius: 16px;
  }

  .search-main {
    flex-direction: column;
  }

  .search-filters {
    flex-direction: column;
  }

  .filter-select {
    width: 100%;
  }

  .toggle-header {
    flex-direction: column;
    gap: 16px;
    align-items: flex-start;
  }

  .table-header {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .dialog-layout {
    flex-direction: column;
    height: 80vh;
  }

  .map-view {
    flex: 1;
    border-right: none;
    border-bottom: 1px solid rgba(233, 236, 239, 0.5);
    border-radius: 0 0 0 16px;
  }

  .info-view {
    flex: 1;
    border-radius: 0 0 16px 16px;
  }

  .map-search-bar {
    width: 90%;
    max-width: none;
  }

  .dialog-footer-left {
    flex-direction: column;
  }
}
</style>
