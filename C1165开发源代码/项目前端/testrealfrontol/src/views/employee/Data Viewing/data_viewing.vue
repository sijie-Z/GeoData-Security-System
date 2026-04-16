
<template>
  <div class="data-viewing-page">

    <div class="page-header">
      <h1 class="page-title">数据目录检索</h1>
    </div>


    <div class="content-panel-pro">

      <div class="filter-area">
        <el-input
          v-model="keyword"
          placeholder="搜索数据名称、标识或来源..."
          :prefix-icon="Search"
          size="large"
          clearable
          @keydown.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" size="large" :icon="Search" @click="handleSearch">搜索</el-button>
      </div>

      <div class="table-container">
        <el-table :data="data.list" style="width: 100%" class="custom-table" v-loading="loading">
          <el-table-column prop="data_id" label="ID" width="125" align="center" />
          <el-table-column prop="data_alias" label="数据名称" width="120" align="center" />
          
          <el-table-column 
            prop="uuid" 
            label="数据标识" 
            width="370" 
            align="center"
            show-overflow-tooltip>
          </el-table-column>

          <el-table-column prop="coordinate_system" label="坐标系" width="150" align="center" show-overflow-tooltip>
            <template #default="scope">{{ scope.row.coordinate_system || 'N/A' }}</template>
          </el-table-column>
          <el-table-column prop="data_source" label="数据来源" min-width="120" align="center" show-overflow-tooltip>
            <template #default="scope">{{ scope.row.data_source || 'N/A' }}</template>
          </el-table-column>
          <el-table-column prop="geomtype" label="类型" width="150" align="center" />
          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="openMapDialog(scope.row)">查看详情</el-button>
              <el-divider direction="vertical" />
              <el-button link type="success" @click="openRequestDialog(scope.row)">申请数据</el-button>
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
    custom-class="preview-dialog"
    :show-close="false"
    top="13vh"
    draggable 
    :overflow="true"
    @closed="destroyMapView"
  >
    <template #header="{ close }">
      <div class="dialog-header-custom">
        <h4 class="header-main-title">数据查看</h4>
        <el-button text circle :icon="Close" @click="close" class="header-close-btn" title="关闭"></el-button>
      </div>
    </template>
    <div class="dialog-layout">
      <div class="map-view" ref="mapContainer">
        <el-button
          circle
          :icon="ArrowLeftBold"
          class="map-back-btn"
          @click="viewDataVisible = false"
          title="返回"
        />
        <div class="map-search-bar">
          <el-input
            v-model="mapSearchKeyword"
            placeholder="搜索地图上的地点..."
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
        </div>
      </div>
      <div class="info-view">
        <div class="info-header-flex">
          <h3 class="info-title">{{ selectedData.data_alias }}</h3>
        </div>
        <div class="info-content-scroll">
          <p class="info-description">{{ selectedData.data_introduction }}</p>
          <el-divider style="margin: 24px 0;" />
          <h4 class="details-subtitle">详细信息</h4>
          <ul class="meta-list">
            <li><span>坐标系</span><strong>{{ selectedData.coordinate_system || 'N/A' }}</strong></li>
            <li><span>数据来源</span><strong>{{ selectedData.data_source || 'N/A' }}</strong></li>
            <li><span>数据类型</span><strong>{{ selectedData.geomtype }}</strong></li>
            <li class="meta-uuid"><span>唯一标识</span><strong>{{ selectedData.uuid }}</strong></li>
          </ul>
        </div>
        <div class="info-footer-flex">
          <el-button type="primary" size="large" class="apply-btn" @click="openRequestDialog(selectedData)">
            申请使用此数据
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>
  

  <el-dialog
    v-model="requestDataVisible"
    title="申请使用数据"
    width="600px"
    :before-close="(done) => handleClose('request', done)"
  >
    <el-form 
      ref="requestFormRef" 
      :model="requestInformation" 
      :rules="rules" 
      label-width="100px"
      style="padding-right: 30px;"
    >
      <el-form-item label="数据编号" required>
        <el-input v-model="requestInformation.data_id" disabled />
      </el-form-item>
      <el-form-item label="数据名称" required>
        <el-input v-model="requestInformation.data_alias" disabled />
      </el-form-item>
      <el-form-item label="申请人姓名" prop="applicant">
        <el-input v-model="requestInformation.applicant" placeholder="请输入申请人姓名" />
      </el-form-item>
      <el-form-item label="员工编号" prop="user_number">
        <el-input v-model="requestInformation.user_number" placeholder="请输入员工编号" />
      </el-form-item>
      <el-form-item label="申请理由" prop="reason">
        <el-input 
          v-model="requestInformation.reason" 
          type="textarea" 
          :rows="4" 
          placeholder="请填写理由" 
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer-left">
        <el-button type="primary" @click="submitForm">提交申请</el-button>
        <el-button @click="resetForm">重置</el-button>
      </div>
    </template>
  </el-dialog>

</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed } from 'vue';
import { Search, Close, ArrowLeftBold } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox, ElDivider } from 'element-plus';
import axios from 'axios';
import { useUserStore } from '@/stores/userStore';

import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import { TileWMS, XYZ } from 'ol/source';
import { ScaleLine, Rotate, defaults as defaultControls } from 'ol/control';

const basic_url = import.meta.env.VITE_API_URL;
const tiandituKey = '11ac7f190ef74ee4bd64081fe7ae419c';

const loading = ref(true);
const data = reactive({ list: [] });
const keyword = ref('');
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const viewDataVisible = ref(false);
const requestDataVisible = ref(false);
const mapContainer = ref(null);
const mapView = ref(null);
const requestFormRef = ref(null);
const mapSearchKeyword = ref('');
const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);

const selectedData = reactive({ data_id: '', uuid: '', data_alias: '', data_introduction: '', geomtype: '', coordinate_system: '', data_source: '', data_url: '', layer: '' });

// 【关键修复 1】: 确保 initialRequestInformation 包含后端需要的所有字段
// 从您提供的“最初版本”代码学习，我们添加了 data_name, uuid, data_url, layer
const initialRequestInformation = {
  data_id: '',
  data_alias: '',
  applicant: '',
  user_number: '',
  reason: '',
  data_name: '', // 新增
  uuid: '',      // 新增
  data_url: '',  // 新增
  layer: '',     // 新增
};
const requestInformation = reactive({ ...initialRequestInformation });

const rules = {
  applicant: [{ required: true, message: '请填写申请人姓名', trigger: 'blur' }],
  user_number: [{ required: true, message: '请填写员工编号', trigger: 'blur' }],
  reason: [{ required: true, message: '请填写申请理由', trigger: 'blur' }],
};

const fetchData = async () => {
  loading.value = true;
  try {
    // 【代码优化】: 使用 /api/data_viewing 接口，因为它与表格列匹配度更高
    const response = await axios.get(`${basic_url}/api/data_viewing`, { params: { page: page.value, pageSize: pageSize.value, keyword: keyword.value || undefined } });
    const result = response.data;
    if (result && result.data && Array.isArray(result.data.list)) {
      data.list = result.data.list.sort((a, b) => a.data_id - b.data_id);
      total.value = result.data.pages.total;
    } else {
      data.list = []; total.value = 0;
      ElMessage.error('数据获取失败或响应格式错误');
    }
  } catch (error) {
    console.error('Error fetching data:', error);
    data.list = []; total.value = 0;
    ElMessage.error('数据获取异常');
  } finally {
    loading.value = false;
  }
};
const pageChanged = (newPage) => { page.value = newPage; fetchData(); };
const handleSearch = () => { page.value = 1; fetchData(); };

const openMapDialog = (row) => {
  Object.assign(selectedData, row);
  mapSearchKeyword.value = '';
  viewDataVisible.value = true;
  nextTick(() => { initializeMapView(row.data_url, row.layer); });
};

// 【关键修复 2】: 在打开申请对话框时，填充所有需要的字段到 requestInformation 对象中
const openRequestDialog = (dataToApply) => {
  // 清空之前的理由
  requestInformation.reason = ''; 
  // 填充所有字段
  Object.assign(requestInformation, {
    data_id: dataToApply.data_id,
    data_alias: dataToApply.data_alias,
    applicant: userName.value,
    user_number: userNumber.value,
    data_name: dataToApply.data_name || dataToApply.data_alias, // 确保 data_name 有值
    uuid: dataToApply.uuid,
    data_url: dataToApply.data_url,
    layer: dataToApply.layer,
    reason: '', // 每次打开时清空理由
  });
  requestDataVisible.value = true;
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('您填写的内容将不会被保存，确认关闭吗？').then(() => {
    done();
    if (dialogType === 'request') resetForm();
  }).catch(() => {});
};

const submitForm = () => {
  requestFormRef.value.validate((valid) => {
    if (valid) {
      // 发送包含了所有后端所需字段的 requestInformation 对象
      axios.post(`${basic_url}/api/submit_application`, requestInformation)
        .then(() => { 
            ElMessage.success('申请提交成功');
            requestDataVisible.value = false;
        })
        .catch(error => {
            // 这里的 console.error 会捕获并打印详细的 400 错误信息
            console.error('Error submitting application:', error);
            const errorMsg = error.response?.data?.message || '申请提交失败，请检查网络或联系管理员';
            ElMessage.error(errorMsg);
        });
    }
  });
};
const resetForm = () => {
    // 只重置用户可编辑的字段，保留预填信息
    if (requestFormRef.value) {
        requestFormRef.value.resetFields();
    }
};

const handleMapSearch = async () => {
  if (!mapSearchKeyword.value.trim() || !mapView.value) { if (!mapSearchKeyword.value.trim()) ElMessage.warning('请输入搜索关键词。'); return; }
  try {
    const response = await axios.get(`${basic_url}/api/map/search`, { params: { keyword: mapSearchKeyword.value.trim() } });
    if (response.data && response.data.pois && response.data.pois.length > 0) {
      const lonlat = response.data.pois[0].lonlat.split(',').map(Number);
      mapView.value.getView().animate({ center: lonlat, zoom: 14, duration: 1000 });
    } else { ElMessage.warning(`在地图上未能找到“${mapSearchKeyword.value}”`); }
  } catch (error) {
    console.error('地图搜索失败 (通过后端代理):', error);
    const errorMsg = error.response?.data?.message || '地图搜索服务异常，请稍后重试。';
    ElMessage.error(errorMsg);
  }
};
const initializeMapView = async (url, fullLayerName) => {
  if (!mapContainer.value) return;
  destroyMapView();
  const baseLayers = [
    new TileLayer({ source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }) }),
    new TileLayer({ source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }) }),
  ];
  const map = new Map({ target: mapContainer.value, layers: baseLayers, view: new View({ projection: 'EPSG:4326', center: [104.0, 35.0], zoom: 4 }), controls: defaultControls().extend([ new ScaleLine({ units: 'metric' }), new Rotate({ autoHide: false, className: 'ol-rotate ol-control-custom-rotate' }) ]) });
  mapView.value = map;
  if (url && fullLayerName) {
    try {
      map.addLayer(new TileLayer({ source: new TileWMS({ url: url, params: { 'LAYERS': fullLayerName, 'TILED': true }, serverType: 'geoserver' }) }));
      const response = await axios.get(`${url}?service=WMS&version=1.3.0&request=GetCapabilities`);
      const xmlDoc = new DOMParser().parseFromString(response.data, "text/xml");
      const layerNameToMatch = fullLayerName.includes(':') ? fullLayerName.split(':')[1] : fullLayerName;
      const layersNodes = xmlDoc.querySelectorAll('Layer > Name');
      let targetLayerNode = Array.from(layersNodes).find(node => node.textContent === layerNameToMatch)?.parentNode;
      if (targetLayerNode) {
        const bboxNode = targetLayerNode.querySelector('BoundingBox[CRS="CRS:84"]');
        if (bboxNode) {
          const bbox = [parseFloat(bboxNode.getAttribute('minx')), parseFloat(bboxNode.getAttribute('miny')), parseFloat(bboxNode.getAttribute('maxx')), parseFloat(bboxNode.getAttribute('maxy'))];
          map.getView().fit(bbox, { size: map.getSize(), duration: 1000, padding: [50, 50, 50, 50] });
        } else { console.warn(`Layer found, but BoundingBox not found.`); ElMessage.warning('无法获取该数据的精确范围。'); }
      } else { console.warn(`Layer not found.`); ElMessage.warning('无法在地图服务中找到指定图层。'); }
    } catch (error) { console.error('Failed to load WMS layer or capabilities:', error); ElMessage.error('加载矢量数据失败，请检查地图服务。'); }
  }
};
const destroyMapView = () => { if (mapView.value) { mapView.value.setTarget(null); mapView.value = null; } };
onMounted(fetchData);
</script>

<style scoped>
/* 所有UI样式保持不变 */
.data-viewing-page{background:#f7f8fa;padding:24px 32px;min-height:calc(100vh - 50px)}.page-header{margin-bottom:24px}.page-title{font-size:28px;font-weight:700;color:#1d2129;margin:0}.content-panel-pro{background:#fff;border-radius:12px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,.04);border:1px solid #e5e7eb}.filter-area{display:flex;gap:16px;margin-bottom:20px}.filter-area .el-input{--el-input-border-radius:8px}.filter-area .el-button{--el-button-border-radius:8px}.table-container{border-radius:8px;border:1px solid #e5e7eb;overflow:hidden}:deep(.custom-table .el-table__header-wrapper){background-color:#f9fafb}:deep(.custom-table th){font-weight:600;color:#4b5563;background-color:#f9fafb!important}:deep(.custom-table .el-table__row){transition:background-color .2s}:deep(.custom-table .el-table__row:hover>td){background-color:#f3f4f6!important}.el-divider--vertical{height:1em;border-left:1px solid #dcdfe6;margin:0 8px}.pagination-wrapper{display:flex;justify-content:flex-end;margin-top:24px}:deep(.preview-dialog){--el-dialog-border-radius:16px;background-color:#fff;box-shadow:0 25px 50px -12px rgba(0,0,0,.25);display:flex;flex-direction:column}:deep(.preview-dialog .el-dialog__body){padding:0!important}:deep(.preview-dialog .el-dialog__header){padding:12px 24px;border-bottom:1px solid #e5e7eb;margin-right:0;cursor:move}.dialog-header-custom{display:flex;justify-content:space-between;align-items:center}.header-main-title{font-size:18px;font-weight:600;color:#1d2129;margin:0}.header-close-btn{font-size:20px}.dialog-layout{display:flex;width:100%;height:70vh;max-height:660px}.map-view{flex:4;background-color:#e0e0e0;position:relative}.info-view{flex:3;display:flex;flex-direction:column;background-color:#fff;border-left:1px solid #e5e7eb}.info-header-flex{padding:20px 24px;border-bottom:1px solid #e5e7eb;flex-shrink:0;text-align:left}.info-title{font-size:22px;font-weight:700;color:#111827;margin:0}.info-content-scroll{flex-grow:1;overflow-y:auto;padding:20px 24px}.info-description{font-size:15px;line-height:1.8;color:#4b5563;margin:0}.details-subtitle{font-size:16px;font-weight:600;color:#111827;margin:16px 0 12px}.meta-list{list-style:none;padding:0;margin:0;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden}.meta-list li{display:grid;grid-template-columns:110px 1fr;align-items:stretch;font-size:14px;border-bottom:1px solid #e5e7eb}.meta-list li:last-child{border-bottom:none}.meta-list li span{background-color:#f9fafb;padding:16px;color:#374151;font-weight:500;display:flex;align-items:center}.meta-list li strong{padding:16px;color:#111827;font-weight:500;text-align:left;display:flex;align-items:center}.meta-list .meta-uuid strong{word-break:break-all;font-family:monospace}.info-footer-flex{padding:20px 24px;border-top:1px solid #e5e7eb;flex-shrink:0}.apply-btn{width:100%;--el-button-border-radius:8px}.map-search-bar{position:absolute;top:15px;left:50%;transform:translateX(-50%);width:400px;max-width:50%;z-index:10;display:flex;align-items:center;gap:8px}.map-search-bar .search-input-custom{flex-grow:1;box-shadow:0 2px 8px rgba(0,0,0,0.15)}.map-search-bar .search-btn-custom{flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,0.15)}.map-back-btn{position:absolute;top:15px;left:15px;z-index:10;width:40px;height:40px;background-color:rgba(255,255,255,.9);box-shadow:0 2px 8px rgba(0,0,0,.1);border:none}.map-view :deep(.ol-zoom){top:65px;left:15px;background-color:transparent}.map-view :deep(.ol-zoom-in),.map-view :deep(.ol-zoom-out){width:40px;height:40px;font-size:24px;background-color:rgba(255,255,255,.9);box-shadow:0 2px 6px rgba(0,0,0,.15);transition:all .2s;color:#333}.map-view :deep(.ol-zoom-in){border-radius:8px 8px 0 0}.map-view :deep(.ol-zoom-out){border-radius:0 0 8px 8px;margin-top:2px}.map-view :deep(.ol-zoom-in:hover),.map-view :deep(.ol-zoom-out:hover){background-color:#fff}.map-view :deep(.ol-control-custom-rotate){top:15px;right:15px;background-color:rgba(255,255,255,.9);border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,.15);transition:background-color .2s;width:40px;height:40px}.map-view :deep(.ol-control-custom-rotate button::before){font-size:20px}.map-view :deep(.ol-control-custom-rotate button){display:flex;justify-content:center;align-items:center;width:100%;height:100%}.map-view :deep(.ol-control-custom-rotate:hover){background-color:#fff}.map-view :deep(.ol-scale-line){bottom:15px;left:15px;background:rgba(255,255,255,.8);padding:3px 8px;border-radius:4px}

.dialog-footer-left {
  width: 100%;
  text-align: left;
}
</style>





 <!-- <template>
  <div class="data-viewing-page">
    <div class="page-header">
      <h1 class="page-title">数据目录检索</h1>
    </div>

    <div class="content-panel-pro">
      <div class="filter-area">
        <el-input
          v-model="keyword"
          placeholder="搜索数据名称、标识或来源..."
          :prefix-icon="Search"
          size="large"
          clearable
          @keydown.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" size="large" :icon="Search" @click="handleSearch">搜索</el-button>
      </div>

      <div class="data-type-toggle">
        <el-button-group>
          <el-button 
            :class="{ active: activeDataType === 'vector' }" 
            @click="activeDataType = 'vector'"
          >
            矢量数据
          </el-button>
          <el-button 
            :class="{ active: activeDataType === 'raster' }" 
            @click="activeDataType = 'raster'"
          >
            栅格数据
          </el-button>
        </el-button-group>
      </div>
      
      <div class="table-container">
        <el-table :data="data.list" style="width: 100%" class="custom-table" v-loading="loading">
          <el-table-column prop="data_id" label="ID" width="100" align="center" />
          <el-table-column prop="data_alias" label="数据名称" min-width="120" align="center" show-overflow-tooltip />
          <el-table-column prop="uuid" label="数据标识" min-width="250" align="center" show-overflow-tooltip />
          <el-table-column prop="data_source" label="数据来源" min-width="120" align="center" show-overflow-tooltip>
            <template #default="scope">{{ scope.row.data_source || 'N/A' }}</template>
          </el-table-column>
          
          <el-table-column v-if="activeDataType === 'vector'" prop="geomtype" label="几何类型" width="100" align="center" />
          <el-table-column v-if="activeDataType === 'vector'" prop="coordinate_system" label="坐标系" width="150" align="center" show-overflow-tooltip>
            <template #default="scope">{{ scope.row.coordinate_system || 'N/A' }}</template>
          </el-table-column>

          <el-table-column v-if="activeDataType === 'raster'" prop="band_count" label="波段数" width="100" align="center" />
          <el-table-column v-if="activeDataType === 'raster'" prop="pixel_type" label="像元类型" width="120" align="center" />
          <el-table-column prop="geomtype" label="数据类型" width="150" align="center" />

          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="openMapDialog(scope.row)">查看详情</el-button>
              <el-divider direction="vertical" />
              <el-button link type="success" @click="openRequestDialog(scope.row)">申请数据</el-button>
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
    custom-class="preview-dialog"
    :show-close="false"
    top="13vh"
    draggable 
    :overflow="true"
    @closed="destroyMapView"
  >
    <template #header="{ close }">
      <div class="dialog-header-custom">
        <h4 class="header-main-title">数据查看</h4>
        <el-button text circle :icon="Close" @click="close" class="header-close-btn" title="关闭"></el-button>
      </div>
    </template>
    
    <div class="dialog-layout">
      <div class="map-view" ref="mapContainer">
        <el-button
          circle
          :icon="ArrowLeftBold"
          class="map-back-btn"
          @click="viewDataVisible = false"
          title="返回"
        />
        <div class="map-search-bar">
          <el-input
            v-model="mapSearchKeyword"
            placeholder="搜索地图上的地点..."
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
        </div>
      </div>
      
      <div class="info-view">
        <div class="info-header-flex">
          <h3 class="info-title">{{ selectedData.data_alias }}</h3>
        </div>
        <div class="info-content-scroll">
          <p class="info-description">{{ selectedData.data_introduction || '无描述' }}</p>
          <el-divider style="margin: 24px 0;" />
          <h4 class="details-subtitle">详细信息</h4>
          <ul class="meta-list">
            <li v-if="activeDataType === 'vector'"><span>坐标系</span><strong>{{ selectedData.coordinate_system || 'N/A' }}</strong></li>
            <li v-if="activeDataType === 'vector'"><span>几何类型</span><strong>{{ selectedData.geomtype || 'N/A' }}</strong></li>
            <li v-if="activeDataType === 'raster'"><span>波段数</span><strong>{{ selectedData.band_count || 'N/A' }}</strong></li>
            <li v-if="activeDataType === 'raster'"><span>像元类型</span><strong>{{ selectedData.pixel_type || 'N/A' }}</strong></li>
            <li><span>数据来源</span><strong>{{ selectedData.data_source || 'N/A' }}</strong></li>
            <li class="meta-uuid"><span>唯一标识</span><strong>{{ selectedData.uuid }}</strong></li>
          </ul>
        </div>
        <div class="info-footer-flex">
          <el-button type="primary" size="large" class="apply-btn" @click="openRequestDialog(selectedData)">
            申请使用此数据
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>
  
  <el-dialog
    v-model="requestDataVisible"
    title="申请使用数据"
    width="600px"
    :before-close="(done) => handleClose('request', done)"
  >
    <el-form 
      ref="requestFormRef" 
      :model="requestInformation" 
      :rules="rules" 
      label-width="100px"
      style="padding-right: 30px;"
    >
      <el-form-item label="数据编号" required>
        <el-input v-model="requestInformation.data_id" disabled />
      </el-form-item>
      <el-form-item label="数据名称" required>
        <el-input v-model="requestInformation.data_alias" disabled />
      </el-form-item>
      <el-form-item label="申请人姓名" prop="applicant">
        <el-input v-model="requestInformation.applicant" placeholder="请输入申请人姓名" />
      </el-form-item>
      <el-form-item label="员工编号" prop="user_number">
        <el-input v-model="requestInformation.user_number" placeholder="请输入员工编号" />
      </el-form-item>
      <el-form-item label="申请理由" prop="reason">
        <el-input 
          v-model="requestInformation.reason" 
          type="textarea" 
          :rows="4" 
          placeholder="请填写理由" 
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer-left">
        <el-button type="primary" @click="submitForm">提交申请</el-button>
        <el-button @click="resetForm">重置</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue';
import { Search, Close, ArrowLeftBold } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox, ElDivider } from 'element-plus';
import axios from 'axios';
import { useUserStore } from '@/stores/userStore';

// OpenLayers 库导入
import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import { TileWMS, XYZ } from 'ol/source';
import { ScaleLine, Rotate, defaults as defaultControls } from 'ol/control';

const basic_url = import.meta.env.VITE_API_URL;
const tiandituKey = '11ac7f190ef74ee4bd64081fe7ae419c';

const loading = ref(true);
const data = reactive({ list: [] });
const keyword = ref('');
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const viewDataVisible = ref(false);
const requestDataVisible = ref(false);
const mapContainer = ref(null);
const mapView = ref(null);
const requestFormRef = ref(null);
const mapSearchKeyword = ref('');
const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);

// 新增 activeDataType，并默认设置为 'vector'
const activeDataType = ref('vector');

const selectedData = reactive({ data_id: '', uuid: '', data_alias: '', data_introduction: '', geomtype: '', coordinate_system: '', data_source: '', data_url: '', layer: '', band_count: null, pixel_type: null });

const initialRequestInformation = {
  data_id: '',
  data_alias: '',
  applicant: '',
  user_number: '',
  reason: '',
  uuid: '', 
  data_url: '', 
  layer: '', 
};
const requestInformation = reactive({ ...initialRequestInformation });

const rules = {
  applicant: [{ required: true, message: '请填写申请人姓名', trigger: 'blur' }],
  user_number: [{ required: true, message: '请填写员工编号', trigger: 'blur' }],
  reason: [{ required: true, message: '请填写申请理由', trigger: 'blur' }],
};

// 【重要】根据 activeDataType 和 keyword 获取数据
const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`${basic_url}/api/data_viewing`, { 
      params: { 
        page: page.value, 
        pageSize: pageSize.value, 
        keyword: keyword.value || undefined,
        dataType: activeDataType.value, // 根据数据类型切换
      } 
    });

    const result = response.data;
    
    if (result && result.data && Array.isArray(result.data.list)) {
      data.list = result.data.list.sort((a, b) => a.data_id - b.data_id);
      total.value = result.data.pages.total;
    } else {
      data.list = []; 
      total.value = 0;
      console.error('API响应格式错误，无法获取数据列表。');
      ElMessage.error('数据获取失败或响应格式错误');
    }
  } catch (error) {
    console.error('Error fetching data:', error);
    data.list = []; 
    total.value = 0;
    ElMessage.error('数据获取异常');
  } finally {
    loading.value = false;
  }
};

// 监听数据类型切换，重置页码并重新获取数据
watch(activeDataType, () => {
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
  nextTick(() => { 
    initializeMapView(row.data_url, row.layer, row.geomtype); 
  });
};

const openRequestDialog = (dataToApply) => {
  requestInformation.reason = ''; 
  Object.assign(requestInformation, {
    data_id: dataToApply.data_id,
    data_alias: dataToApply.data_alias,
    applicant: userName.value,
    user_number: userNumber.value,
    uuid: dataToApply.uuid,
    data_url: dataToApply.data_url,
    layer: dataToApply.layer,
  });
  requestDataVisible.value = true;
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('您填写的内容将不会被保存，确认关闭吗？').then(() => {
    done();
    if (dialogType === 'request') resetForm();
  }).catch(() => {});
};

const submitForm = () => {
  requestFormRef.value.validate((valid) => {
    if (valid) {
      axios.post(`${basic_url}/api/submit_application`, requestInformation)
        .then(() => { 
            ElMessage.success('申请提交成功');
            requestDataVisible.value = false;
        })
        .catch(error => {
            console.error('Error submitting application:', error);
            const errorMsg = error.response?.data?.message || '申请提交失败，请检查网络或联系管理员';
            ElMessage.error(errorMsg);
        });
    }
  });
};

const resetForm = () => {
    if (requestFormRef.value) {
        requestFormRef.value.resetFields();
        Object.assign(requestInformation, {
          ...initialRequestInformation,
          applicant: userName.value,
          user_number: userNumber.value,
          data_id: selectedData.data_id,
          data_alias: selectedData.data_alias,
          uuid: selectedData.uuid,
          data_url: selectedData.data_url,
          layer: selectedData.layer,
        });
    }
};

const handleMapSearch = async () => {
  if (!mapSearchKeyword.value.trim() || !mapView.value) { 
    if (!mapSearchKeyword.value.trim()) ElMessage.warning('请输入搜索关键词。'); 
    return; 
  }
  try {
    const response = await axios.get(`${basic_url}/api/map/search`, { params: { keyword: mapSearchKeyword.value.trim() } });
    if (response.data && response.data.pois && response.data.pois.length > 0) {
      const lonlat = response.data.pois[0].lonlat.split(',').map(Number);
      mapView.value.getView().animate({ center: lonlat, zoom: 14, duration: 1000 });
    } else { 
      ElMessage.warning(`在地图上未能找到“${mapSearchKeyword.value}”`); 
    }
  } catch (error) {
    console.error('地图搜索失败 (通过后端代理):', error);
    const errorMsg = error.response?.data?.message || '地图搜索服务异常，请稍后重试。';
    ElMessage.error(errorMsg);
  }
};

// 【核心修复】: 根据 geomtype 动态加载 WMS 图层或显示提示
const initializeMapView = async (url, fullLayerName, geomtype) => {
  if (!mapContainer.value) return;
  destroyMapView();

  // 天地图矢量底图和标注层
  const baseLayers = [
    new TileLayer({ source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }) }),
    new TileLayer({ source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }) }),
  ];

  const map = new Map({ 
    target: mapContainer.value, 
    layers: baseLayers, 
    view: new View({ 
      projection: 'EPSG:4326', 
      center: [104.0, 35.0], 
      zoom: 4 
    }), 
    controls: defaultControls().extend([ 
      new ScaleLine({ units: 'metric' }), 
      new Rotate({ autoHide: false, className: 'ol-rotate ol-control-custom-rotate' }) 
    ]) 
  });
  mapView.value = map;
  
  // 根据数据类型加载 WMS 图层
  if (url && fullLayerName && geomtype === '矢量数据') {
    try {
      const wmsLayer = new TileLayer({ 
        source: new TileWMS({ 
          url: url, 
          params: { 'LAYERS': fullLayerName, 'TILED': true }, 
          serverType: 'geoserver' 
        }) 
      });
      map.addLayer(wmsLayer);

      // 获取图层边界并缩放到合适范围
      const response = await axios.get(`${url}?service=WMS&version=1.3.0&request=GetCapabilities`);
      const xmlDoc = new DOMParser().parseFromString(response.data, "text/xml");
      const layerNameToMatch = fullLayerName.includes(':') ? fullLayerName.split(':')[1] : fullLayerName;
      const layersNodes = xmlDoc.querySelectorAll('Layer > Name');
      let targetLayerNode = Array.from(layersNodes).find(node => node.textContent === layerNameToMatch)?.parentNode;
      
      if (targetLayerNode) {
        const bboxNode = targetLayerNode.querySelector('BoundingBox[CRS="CRS:84"]');
        if (bboxNode) {
          const bbox = [
            parseFloat(bboxNode.getAttribute('minx')), 
            parseFloat(bboxNode.getAttribute('miny')), 
            parseFloat(bboxNode.getAttribute('maxx')), 
            parseFloat(bboxNode.getAttribute('maxy'))
          ];
          map.getView().fit(bbox, { size: map.getSize(), duration: 1000, padding: [50, 50, 50, 50] });
        } else { 
          console.warn(`Layer found, but BoundingBox not found.`); 
          ElMessage.warning('无法获取该数据的精确范围。'); 
        }
      } else { 
        console.warn(`Layer not found.`); 
        ElMessage.warning('无法在地图服务中找到指定图层。'); 
      }
    } catch (error) { 
      console.error('Failed to load WMS layer or capabilities:', error); 
      ElMessage.error('加载矢量数据失败，请检查地图服务。'); 
    }
  } else if (geomtype === '栅格数据') {
    // 栅格数据预览提示
    ElMessage.info('栅格数据无法直接在地图上预览，您可以申请下载。');
  }
};

const destroyMapView = () => { 
  if (mapView.value) { 
    mapView.value.setTarget(null); 
    mapView.value = null; 
  } 
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
/* 保持原始样式，只修改切换按钮的样式 */
.data-viewing-page{background:#f7f8fa;padding:24px 32px;min-height:calc(100vh - 50px)}.page-header{margin-bottom:24px}.page-title{font-size:28px;font-weight:700;color:#1d2129;margin:0}.content-panel-pro{background:#fff;border-radius:12px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,.04);border:1px solid #e5e7eb}.filter-area{display:flex;gap:16px;margin-bottom:20px}.filter-area .el-input{--el-input-border-radius:8px}.filter-area .el-button{--el-button-border-radius:8px}.table-container{border-radius:8px;border:1px solid #e5e7eb;overflow:hidden}:deep(.custom-table .el-table__header-wrapper){background-color:#f9fafb}:deep(.custom-table th){font-weight:600;color:#4b5563;background-color:#f9fafb!important}:deep(.custom-table .el-table__row){transition:background-color .2s}:deep(.custom-table .el-table__row:hover>td){background-color:#f3f4f6!important}.el-divider--vertical{height:1em;border-left:1px solid #dcdfe6;margin:0 8px}.pagination-wrapper{display:flex;justify-content:flex-end;margin-top:24px}:deep(.preview-dialog){--el-dialog-border-radius:16px;background-color:#fff;box-shadow:0 25px 50px -12px rgba(0,0,0,.25);display:flex;flex-direction:column}:deep(.preview-dialog .el-dialog__body){padding:0!important}:deep(.preview-dialog .el-dialog__header){padding:12px 24px;border-bottom:1px solid #e5e7eb;margin-right:0;cursor:move}.dialog-header-custom{display:flex;justify-content:space-between;align-items:center}.header-main-title{font-size:18px;font-weight:600;color:#1d2129;margin:0}.header-close-btn{font-size:20px}.dialog-layout{display:flex;width:100%;height:70vh;max-height:660px}.map-view{flex:4;background-color:#e0e0e0;position:relative}.info-view{flex:3;display:flex;flex-direction:column;background-color:#fff;border-left:1px solid #e5e7eb}.info-header-flex{padding:20px 24px;border-bottom:1px solid #e5e7eb;flex-shrink:0;text-align:left}.info-title{font-size:22px;font-weight:700;color:#111827;margin:0}.info-content-scroll{flex-grow:1;overflow-y:auto;padding:20px 24px}.info-description{font-size:15px;line-height:1.8;color:#4b5563;margin:0}.details-subtitle{font-size:16px;font-weight:600;color:#111827;margin:16px 0 12px}.meta-list{list-style:none;padding:0;margin:0;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden}.meta-list li{display:grid;grid-template-columns:110px 1fr;align-items:stretch;font-size:14px;border-bottom:1px solid #e5e7eb}.meta-list li:last-child{border-bottom:none}.meta-list li span{background-color:#f9fafb;padding:16px;color:#374151;font-weight:500;display:flex;align-items:center}.meta-list li strong{padding:16px;color:#111827;font-weight:500;text-align:left;display:flex;align-items:center}.meta-list .meta-uuid strong{word-break:break-all;font-family:monospace}.info-footer-flex{padding:20px 24px;border-top:1px solid #e5e7eb;flex-shrink:0}.apply-btn{width:100%;--el-button-border-radius:8px}.map-search-bar{position:absolute;top:15px;left:50%;transform:translateX(-50%);width:400px;max-width:50%;z-index:10;display:flex;align-items:center;gap:8px}.map-search-bar .search-input-custom{flex-grow:1;box-shadow:0 2px 8px rgba(0,0,0,0.15)}.map-search-bar .search-btn-custom{flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,0.15)}.map-back-btn{position:absolute;top:15px;left:15px;z-index:10;width:40px;height:40px;background-color:rgba(255,255,255,.9);box-shadow:0 2px 8px rgba(0,0,0,.1);border:none}.map-view :deep(.ol-zoom){top:65px;left:15px;background-color:transparent}.map-view :deep(.ol-zoom-in),.map-view :deep(.ol-zoom-out){width:40px;height:40px;font-size:24px;background-color:rgba(255,255,255,.9);box-shadow:0 2px 6px rgba(0,0,0,.15);transition:all .2s;color:#333}.map-view :deep(.ol-zoom-in){border-radius:8px 8px 0 0}.map-view :deep(.ol-zoom-out){border-radius:0 0 8px 8px;margin-top:2px}.map-view :deep(.ol-zoom-in:hover),.map-view :deep(.ol-zoom-out:hover){background-color:#fff}.map-view :deep(.ol-control-custom-rotate){top:15px;right:15px;background-color:rgba(255,255,255,.9);border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,.15);transition:background-color .2s;width:40px;height:40px}.map-view :deep(.ol-control-custom-rotate button::before){font-size:20px}.map-view :deep(.ol-control-custom-rotate button){display:flex;justify-content:center;align-items:center;width:100%;height:100%}.map-view :deep(.ol-control-custom-rotate:hover){background-color:#fff}.map-view :deep(.ol-scale-line){bottom:15px;left:15px;background:rgba(255,255,255,.8);padding:3px 8px;border-radius:4px}
.dialog-footer-left {
  width: 100%;
  text-align: left;
}

/* 新增的切换按钮样式 */
.data-type-toggle {
  margin-bottom: 20px;
}

.data-type-toggle .el-button-group {
  border-radius: 8px;
  overflow: hidden;
}

.data-type-toggle .el-button {
  background-color: #fff;
  border: 1px solid #dcdfe6;
  color: #606266;
  font-weight: 500;
  transition: all 0.2s ease-in-out;
  padding: 12px 24px;
}

.data-type-toggle .el-button:hover {
  color: #409eff;
  border-color: #c6e2ff;
  background-color: #ecf5ff;
}

.data-type-toggle .el-button.active {
  background-color: #409eff;
  color: #fff;
  border-color: #409eff;
}

.data-type-toggle .el-button.active:hover {
  background-color: #337ecc;
  color: #fff;
  border-color: #337ecc;
}
</style> -->




<!-- <template>
  <div class="data-viewing-page">
    <div class="page-header">
      <h1 class="page-title">数据目录检索</h1>
    </div>

    <div class="content-panel-pro">
      <div class="filter-area">
        <el-input
          v-model="keyword"
          placeholder="搜索数据名称、标识或来源..."
          :prefix-icon="Search"
          size="large"
          clearable
          @keydown.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-button type="primary" size="large" :icon="Search" @click="handleSearch">搜索</el-button>
      </div>

      <div class="data-type-toggle">
        <el-button-group>
          <el-button 
            :class="{ active: activeDataType === 'vector' }" 
            @click="activeDataType = 'vector'"
          >
            矢量数据
          </el-button>
          <el-button 
            :class="{ active: activeDataType === 'raster' }" 
            @click="activeDataType = 'raster'"
          >
            栅格数据
          </el-button>
        </el-button-group>
      </div>
      
      <div class="table-container">
        <el-table :data="data.list" style="width: 100%" class="custom-table" v-loading="loading">
          <el-table-column prop="data_id" label="ID" width="100" align="center" />
          <el-table-column prop="data_alias" label="数据名称" min-width="120" align="center" show-overflow-tooltip />
          <el-table-column prop="uuid" label="数据标识" min-width="250" align="center" show-overflow-tooltip />
          <el-table-column prop="data_source" label="数据来源" min-width="120" align="center" show-overflow-tooltip>
            <template #default="scope">{{ scope.row.data_source || 'N/A' }}</template>
          </el-table-column>
          
          <el-table-column v-if="activeDataType === 'vector'" prop="geomtype" label="几何类型" width="100" align="center" />
          <el-table-column v-if="activeDataType === 'vector'" prop="coordinate_system" label="坐标系" width="150" align="center" show-overflow-tooltip>
            <template #default="scope">{{ scope.row.coordinate_system || 'N/A' }}</template>
          </el-table-column>

          <el-table-column v-if="activeDataType === 'raster'" prop="bands" label="波段数" width="100" align="center" />
          <el-table-column v-if="activeDataType === 'raster'" prop="resolution" label="分辨率" width="120" align="center" />

          <el-table-column label="操作" width="180" align="center" fixed="right">
            <template #default="scope">
              <el-button link type="primary" @click="openMapDialog(scope.row)">查看详情</el-button>
              <el-divider direction="vertical" />
              <el-button link type="success" @click="openRequestDialog(scope.row)">申请数据</el-button>
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
    custom-class="preview-dialog"
    :show-close="false"
    top="13vh"
    draggable 
    :overflow="true"
    @closed="destroyMapView"
  >
    <template #header="{ close }">
      <div class="dialog-header-custom">
        <h4 class="header-main-title">数据查看</h4>
        <el-button text circle :icon="Close" @click="close" class="header-close-btn" title="关闭"></el-button>
      </div>
    </template>
    
    <div class="dialog-layout">
      <div class="map-view" ref="mapContainer">
        <el-button
          circle
          :icon="ArrowLeftBold"
          class="map-back-btn"
          @click="viewDataVisible = false"
          title="返回"
        />
        <div class="map-search-bar" v-if="isVectorData">
          <el-input
            v-model="mapSearchKeyword"
            placeholder="搜索地图上的地点..."
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
        </div>
        <div class="raster-overlay" v-if="!isVectorData">
          <el-alert title="栅格数据无法直接在地图上预览，您可以申请下载。" type="warning" show-icon :closable="false" />
        </div>
      </div>
      
      <div class="info-view">
        <div class="info-header-flex">
          <h3 class="info-title">{{ selectedData.data_alias }}</h3>
        </div>
        <div class="info-content-scroll">
          <p class="info-description">{{ selectedData.data_introduction || '无描述' }}</p>
          <el-divider style="margin: 24px 0;" />
          <h4 class="details-subtitle">详细信息</h4>
          <ul class="meta-list">
            <li v-if="isVectorData"><span>坐标系</span><strong>{{ selectedData.coordinate_system || 'N/A' }}</strong></li>
            <li v-if="isVectorData"><span>几何类型</span><strong>{{ selectedData.geomtype || 'N/A' }}</strong></li>
            <li v-if="!isVectorData"><span>波段数</span><strong>{{ selectedData.bands || 'N/A' }}</strong></li>
            <li v-if="!isVectorData"><span>分辨率</span><strong>{{ selectedData.resolution || 'N/A' }}</strong></li>
            <li><span>数据来源</span><strong>{{ selectedData.data_source || 'N/A' }}</strong></li>
            <li class="meta-uuid"><span>唯一标识</span><strong>{{ selectedData.uuid }}</strong></li>
          </ul>
        </div>
        <div class="info-footer-flex">
          <el-button type="primary" size="large" class="apply-btn" @click="openRequestDialog(selectedData)">
            申请使用此数据
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>
  
  <el-dialog
    v-model="requestDataVisible"
    title="申请使用数据"
    width="600px"
    :before-close="(done) => handleClose('request', done)"
  >
    <el-form 
      ref="requestFormRef" 
      :model="requestInformation" 
      :rules="rules" 
      label-width="100px"
      style="padding-right: 30px;"
    >
      <el-form-item label="数据编号" required>
        <el-input v-model="requestInformation.data_id" disabled />
      </el-form-item>
      <el-form-item label="数据名称" required>
        <el-input v-model="requestInformation.data_alias" disabled />
      </el-form-item>
      <el-form-item label="申请人姓名" prop="applicant">
        <el-input v-model="requestInformation.applicant" placeholder="请输入申请人姓名" />
      </el-form-item>
      <el-form-item label="员工编号" prop="user_number">
        <el-input v-model="requestInformation.user_number" placeholder="请输入员工编号" />
      </el-form-item>
      <el-form-item label="申请理由" prop="reason">
        <el-input 
          v-model="requestInformation.reason" 
          type="textarea" 
          :rows="4" 
          placeholder="请填写理由" 
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer-left">
        <el-button type="primary" @click="submitForm">提交申请</el-button>
        <el-button @click="resetForm">重置</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed, watch } from 'vue';
import { Search, Close, ArrowLeftBold } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox, ElDivider } from 'element-plus';
import axios from 'axios';
import { useUserStore } from '@/stores/userStore';

// OpenLayers 库导入
import 'ol/ol.css';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import { TileWMS, XYZ } from 'ol/source';
import { ScaleLine, Rotate, defaults as defaultControls } from 'ol/control';

const basic_url = import.meta.env.VITE_API_URL;
const tiandituKey = '11ac7f190ef74ee4bd64081fe7ae419c';

const loading = ref(true);
const data = reactive({ list: [] });
const keyword = ref('');
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const viewDataVisible = ref(false);
const requestDataVisible = ref(false);
const mapContainer = ref(null);
const mapView = ref(null);
const requestFormRef = ref(null);
const mapSearchKeyword = ref('');
const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);

// 使用 activeDataType 区分数据类型
const activeDataType = ref('vector');

// 计算属性判断当前是否为矢量数据
const isVectorData = computed(() => activeDataType.value === 'vector');

const selectedData = reactive({ 
  data_id: '', 
  uuid: '', 
  data_alias: '', 
  data_introduction: '', 
  geomtype: '', 
  coordinate_system: '', 
  data_source: '', 
  data_url: '', 
  layer: '', 
  bands: null, 
  resolution: null 
});

const initialRequestInformation = {
  data_id: '',
  data_alias: '',
  applicant: '',
  user_number: '',
  reason: '',
  uuid: '', 
  data_url: '', 
  layer: '', 
};
const requestInformation = reactive({ ...initialRequestInformation });

const rules = {
  applicant: [{ required: true, message: '请填写申请人姓名', trigger: 'blur' }],
  user_number: [{ required: true, message: '请填写员工编号', trigger: 'blur' }],
  reason: [{ required: true, message: '请填写申请理由', trigger: 'blur' }],
};

// 根据 activeDataType 获取数据
const fetchData = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`${basic_url}/api/data_viewing`, { 
      params: { 
        page: page.value, 
        pageSize: pageSize.value, 
        keyword: keyword.value || undefined,
        dataType: activeDataType.value // 根据数据类型切换
      } 
    });

    const result = response.data;
    
    if (result && result.data && Array.isArray(result.data.list)) {
      data.list = result.data.list.sort((a, b) => a.data_id - b.data_id);
      total.value = result.data.pages.total;
    } else {
      data.list = []; 
      total.value = 0;
      console.error('API响应格式错误，无法获取数据列表。');
      ElMessage.error('数据获取失败或响应格式错误');
    }
  } catch (error) {
    console.error('Error fetching data:', error);
    data.list = []; 
    total.value = 0;
    ElMessage.error('数据获取异常');
  } finally {
    loading.value = false;
  }
};

// 监听数据类型切换，重置页码并重新获取数据
watch(activeDataType, () => {
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
  nextTick(() => { 
    // 根据数据类型初始化地图
    if (isVectorData.value) {
      initializeMapView(row.data_url, row.layer); 
    }
  });
};

const openRequestDialog = (dataToApply) => {
  requestInformation.reason = ''; 
  Object.assign(requestInformation, {
    data_id: dataToApply.data_id,
    data_alias: dataToApply.data_alias,
    applicant: userName.value,
    user_number: userNumber.value,
    uuid: dataToApply.uuid,
    data_url: dataToApply.data_url,
    layer: dataToApply.layer,
  });
  requestDataVisible.value = true;
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('您填写的内容将不会被保存，确认关闭吗？').then(() => {
    done();
    if (dialogType === 'request') resetForm();
  }).catch(() => {});
};

const submitForm = () => {
  requestFormRef.value.validate((valid) => {
    if (valid) {
      axios.post(`${basic_url}/api/submit_application`, requestInformation)
        .then(() => { 
            ElMessage.success('申请提交成功');
            requestDataVisible.value = false;
        })
        .catch(error => {
            console.error('Error submitting application:', error);
            const errorMsg = error.response?.data?.message || '申请提交失败，请检查网络或联系管理员';
            ElMessage.error(errorMsg);
        });
    }
  });
};

const resetForm = () => {
    if (requestFormRef.value) {
        requestFormRef.value.resetFields();
        Object.assign(requestInformation, {
          ...initialRequestInformation,
          applicant: userName.value,
          user_number: userNumber.value,
          data_id: selectedData.data_id,
          data_alias: selectedData.data_alias,
          uuid: selectedData.uuid,
          data_url: selectedData.data_url,
          layer: selectedData.layer,
        });
    }
};

const handleMapSearch = async () => {
  if (!mapSearchKeyword.value.trim() || !mapView.value) { 
    if (!mapSearchKeyword.value.trim()) ElMessage.warning('请输入搜索关键词。'); 
    return; 
  }
  try {
    const response = await axios.get(`${basic_url}/api/map/search`, { params: { keyword: mapSearchKeyword.value.trim() } });
    if (response.data && response.data.pois && response.data.pois.length > 0) {
      const lonlat = response.data.pois[0].lonlat.split(',').map(Number);
      mapView.value.getView().animate({ center: lonlat, zoom: 14, duration: 1000 });
    } else { 
      ElMessage.warning(`在地图上未能找到“${mapSearchKeyword.value}”`); 
    }
  } catch (error) {
    console.error('地图搜索失败 (通过后端代理):', error);
    const errorMsg = error.response?.data?.message || '地图搜索服务异常，请稍后重试。';
    ElMessage.error(errorMsg);
  }
};

// 初始化地图视图（仅用于矢量数据）
const initializeMapView = async (url, fullLayerName) => {
  if (!mapContainer.value) return;
  destroyMapView();

  // 天地图矢量底图和标注层
  const baseLayers = [
    new TileLayer({ source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }) }),
    new TileLayer({ source: new XYZ({ url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=${tiandituKey}` }) }),
  ];

  const map = new Map({ 
    target: mapContainer.value, 
    layers: baseLayers, 
    view: new View({ 
      projection: 'EPSG:4326', 
      center: [104.0, 35.0], 
      zoom: 4 
    }), 
    controls: defaultControls().extend([ 
      new ScaleLine({ units: 'metric' }), 
      new Rotate({ autoHide: false, className: 'ol-rotate ol-control-custom-rotate' }) 
    ]) 
  });
  mapView.value = map;
  
  if (url && fullLayerName) {
    try {
      const wmsLayer = new TileLayer({ 
        source: new TileWMS({ 
          url: url, 
          params: { 'LAYERS': fullLayerName, 'TILED': true }, 
          serverType: 'geoserver' 
        }) 
      });
      map.addLayer(wmsLayer);

      // 获取图层边界并缩放到合适范围
      const response = await axios.get(`${url}?service=WMS&version=1.3.0&request=GetCapabilities`);
      const xmlDoc = new DOMParser().parseFromString(response.data, "text/xml");
      const layerNameToMatch = fullLayerName.includes(':') ? fullLayerName.split(':')[1] : fullLayerName;
      const layersNodes = xmlDoc.querySelectorAll('Layer > Name');
      let targetLayerNode = Array.from(layersNodes).find(node => node.textContent === layerNameToMatch)?.parentNode;
      
      if (targetLayerNode) {
        const bboxNode = targetLayerNode.querySelector('BoundingBox[CRS="CRS:84"]');
        if (bboxNode) {
          const bbox = [
            parseFloat(bboxNode.getAttribute('minx')), 
            parseFloat(bboxNode.getAttribute('miny')), 
            parseFloat(bboxNode.getAttribute('maxx')), 
            parseFloat(bboxNode.getAttribute('maxy'))
          ];
          map.getView().fit(bbox, { size: map.getSize(), duration: 1000, padding: [50, 50, 50, 50] });
        } else { 
          console.warn(`Layer found, but BoundingBox not found.`); 
          ElMessage.warning('无法获取该数据的精确范围。'); 
        }
      } else { 
        console.warn(`Layer not found.`); 
        ElMessage.warning('无法在地图服务中找到指定图层。'); 
      }
    } catch (error) { 
      console.error('Failed to load WMS layer or capabilities:', error); 
      ElMessage.error('加载矢量数据失败，请检查地图服务。'); 
    }
  }
};

const destroyMapView = () => { 
  if (mapView.value) { 
    mapView.value.setTarget(null); 
    mapView.value = null; 
  } 
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.data-viewing-page {
  background: #f7f8fa;
  padding: 24px 32px;
  min-height: calc(100vh - 50px);
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #1d2129;
  margin: 0;
}

.content-panel-pro {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, .04);
  border: 1px solid #e5e7eb;
}

.filter-area {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
}

.filter-area .el-input {
  --el-input-border-radius: 8px;
}

.filter-area .el-button {
  --el-button-border-radius: 8px;
}

.table-container {
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  overflow: hidden;
}

:deep(.custom-table .el-table__header-wrapper) {
  background-color: #f9fafb;
}

:deep(.custom-table th) {
  font-weight: 600;
  color: #4b5563;
  background-color: #f9fafb !important;
}

:deep(.custom-table .el-table__row) {
  transition: background-color .2s;
}

:deep(.custom-table .el-table__row:hover>td) {
  background-color: #f3f4f6 !important;
}

.el-divider--vertical {
  height: 1em;
  border-left: 1px solid #dcdfe6;
  margin: 0 8px;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
}

:deep(.preview-dialog) {
  --el-dialog-border-radius: 16px;
  background-color: #fff;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, .25);
  display: flex;
  flex-direction: column;
}

:deep(.preview-dialog .el-dialog__body) {
  padding: 0 !important;
}

:deep(.preview-dialog .el-dialog__header) {
  padding: 12px 24px;
  border-bottom: 1px solid #e5e7eb;
  margin-right: 0;
  cursor: move;
}

.dialog-header-custom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-main-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d2129;
  margin: 0;
}

.header-close-btn {
  font-size: 20px;
}

.dialog-layout {
  display: flex;
  width: 100%;
  height: 70vh;
  max-height: 660px;
}

.map-view {
  flex: 4;
  background-color: #e0e0e0;
  position: relative;
}

.info-view {
  flex: 3;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  border-left: 1px solid #e5e7eb;
}

.info-header-flex {
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
  text-align: left;
}

.info-title {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.info-content-scroll {
  flex-grow: 1;
  overflow-y: auto;
  padding: 20px 24px;
}

.info-description {
  font-size: 15px;
  line-height: 1.8;
  color: #4b5563;
  margin: 0;
}

.details-subtitle {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 16px 0 12px;
}

.meta-list {
  list-style: none;
  padding: 0;
  margin: 0;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
}

.meta-list li {
  display: grid;
  grid-template-columns: 110px 1fr;
  align-items: stretch;
  font-size: 14px;
  border-bottom: 1px solid #e5e7eb;
}

.meta-list li:last-child {
  border-bottom: none;
}

.meta-list li span {
  background-color: #f9fafb;
  padding: 16px;
  color: #374151;
  font-weight: 500;
  display: flex;
  align-items: center;
}

.meta-list li strong {
  padding: 16px;
  color: #111827;
  font-weight: 500;
  text-align: left;
  display: flex;
  align-items: center;
}

.meta-list .meta-uuid strong {
  word-break: break-all;
  font-family: monospace;
}

.info-footer-flex {
  padding: 20px 24px;
  border-top: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.apply-btn {
  width: 100%;
  --el-button-border-radius: 8px;
}

.map-search-bar {
  position: absolute;
  top: 15px;
  left: 50%;
  transform: translateX(-50%);
  width: 400px;
  max-width: 50%;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 8px;
}

.map-search-bar .search-input-custom {
  flex-grow: 1;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.map-search-bar .search-btn-custom {
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.map-back-btn {
  position: absolute;
  top: 15px;
  left: 15px;
  z-index: 10;
  width: 40px;
  height: 40px;
  background-color: rgba(255, 255, 255, .9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, .1);
  border: none;
}

.map-view :deep(.ol-zoom) {
  top: 65px;
  left: 15px;
  background-color: transparent;
}

.map-view :deep(.ol-zoom-in),
.map-view :deep(.ol-zoom-out) {
  width: 40px;
  height: 40px;
  font-size: 24px;
  background-color: rgba(255, 255, 255, .9);
  box-shadow: 0 2px 6px rgba(0, 0, 0, .15);
  transition: all .2s;
  color: #333;
}

.map-view :deep(.ol-zoom-in) {
  border-radius: 8px 8px 0 0;
}

.map-view :deep(.ol-zoom-out) {
  border-radius: 0 0 8px 8px;
  margin-top: 2px;
}

.map-view :deep(.ol-zoom-in:hover),
.map-view :deep(.ol-zoom-out:hover) {
  background-color: #fff;
}

.map-view :deep(.ol-control-custom-rotate) {
  top: 15px;
  right: 15px;
  background-color: rgba(255, 255, 255, .9);
  border-radius: 50%;
  box-shadow: 0 2px 6px rgba(0, 0, 0, .15);
  transition: background-color .2s;
  width: 40px;
  height: 40px;
}

.map-view :deep(.ol-control-custom-rotate button::before) {
  font-size: 20px;
}

.map-view :deep(.ol-control-custom-rotate button) {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  height: 100%;
}

.map-view :deep(.ol-control-custom-rotate:hover) {
  background-color: #fff;
}

.map-view :deep(.ol-scale-line) {
  bottom: 15px;
  left: 15px;
  background: rgba(255, 255, 255, .8);
  padding: 3px 8px;
  border-radius: 4px;
}

.dialog-footer-left {
  width: 100%;
  text-align: left;
}

.raster-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.8);
  z-index: 100;
}

.raster-overlay .el-alert {
  width: 80%;
  max-width: 400px;
}

/* 新增的切换按钮样式 */
.data-type-toggle {
  margin-bottom: 20px;
}

.data-type-toggle .el-button-group {
  border-radius: 8px;
  overflow: hidden;
}

.data-type-toggle .el-button {
  background-color: #fff;
  border: 1px solid #dcdfe6;
  color: #606266;
  font-weight: 500;
  transition: all 0.2s ease-in-out;
  padding: 12px 24px;
}

.data-type-toggle .el-button:hover {
  color: #409eff;
  border-color: #c6e2ff;
  background-color: #ecf5ff;
}

.data-type-toggle .el-button.active {
  background-color: #409eff;
  color: #fff;
  border-color: #409eff;
}

.data-type-toggle .el-button.active:hover {
  background-color: #337ecc;
  color: #fff;
  border-color: #337ecc;
}
</style> -->