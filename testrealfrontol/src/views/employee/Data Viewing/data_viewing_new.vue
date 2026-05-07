<template>
  <div class="data-catalog-page">
    <!-- 页面头部 - 地理空间数据云风格 -->
    <div class="page-hero">
      <div class="hero-content">
        <h1 class="hero-title">地理空间数据目录</h1>
        <p class="hero-subtitle">专业的遥感影像与矢量数据管理与服务平台</p>
        <div class="hero-stats">
          <div class="stat-item">
            <span class="stat-number">{{ totalVector }}</span>
            <span class="stat-label">矢量数据集</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-number">{{ totalRaster }}</span>
            <span class="stat-label">栅格数据集</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item">
            <span class="stat-number">{{ total }}</span>
            <span class="stat-label">总数据量</span>
          </div>
        </div>
      </div>
      <div class="hero-visual">
        <div class="globe-container">
          <svg class="globe-icon" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="#4A90E2" opacity="0.1"/>
            <circle cx="50" cy="50" r="40" fill="none" stroke="#4A90E2" stroke-width="2"/>
            <path d="M 10 50 Q 50 30 90 50" stroke="#4A90E2" stroke-width="1" fill="none"/>
            <path d="M 10 50 Q 50 70 90 50" stroke="#4A90E2" stroke-width="1" fill="none"/>
            <path d="M 50 10 Q 30 50 50 90" stroke="#4A90E2" stroke-width="1" fill="none"/>
            <path d="M 50 10 Q 70 50 50 90" stroke="#4A90E2" stroke-width="1" fill="none"/>
            <circle cx="30" cy="35" r="8" fill="#4A90E2" opacity="0.6"/>
            <circle cx="65" cy="45" r="6" fill="#4A90E2" opacity="0.6"/>
            <circle cx="25" cy="65" r="5" fill="#4A90E2" opacity="0.6"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- 搜索区域 - 地理空间数据云风格 -->
    <div class="search-section">
      <div class="search-container">
        <div class="search-main">
          <div class="search-icon">
            <el-icon><Search /></el-icon>
          </div>
          <el-input
            v-model="keyword"
            placeholder="输入数据名称、标识符或关键词搜索..."
            size="large"
            clearable
            @keydown.enter="handleSearch"
            @clear="handleSearch"
            class="search-input"
          />
          <el-button type="primary" size="large" @click="handleSearch" class="search-btn">
            <el-icon><Search /></el-icon>
            搜索数据
          </el-button>
        </div>
        
        <div class="search-filters">
          <div class="filter-group">
            <label class="filter-label">数据类型</label>
            <el-radio-group v-model="activeDataType" size="large" class="data-type-radio">
              <el-radio-button value="vector">
                <el-icon><Location /></el-icon>
                矢量数据
              </el-radio-button>
              <el-radio-button value="raster">
                <el-icon><Picture /></el-icon>
                栅格数据
              </el-radio-button>
              <el-radio-button value="all">
                <el-icon><DataAnalysis /></el-icon>
                全部类型
              </el-radio-button>
            </el-radio-group>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">数据来源</label>
            <el-select v-model="dataSourceFilter" placeholder="选择数据来源" clearable size="large" class="filter-select">
              <el-option label="自然资源部" value="自然资源部" />
              <el-option label="中科院地理所" value="中科院" />
              <el-option label="国家测绘局" value="测绘局" />
              <el-option label="商业数据" value="商业" />
            </el-select>
          </div>
          
          <div class="filter-group">
            <label class="filter-label">时间范围</label>
            <el-select v-model="timeFilter" placeholder="选择时间范围" clearable size="large" class="filter-select">
              <el-option label="最近一周" value="week" />
              <el-option label="最近一月" value="month" />
              <el-option label="最近一年" value="year" />
              <el-option label="全部时间" value="" />
            </el-select>
          </div>
        </div>
      </div>
    </div>

    <!-- 数据展示区域 -->
    <div class="data-section">
      <div class="section-header">
        <h2 class="section-title">
          <el-icon><Grid /></el-icon>
          {{ getDataTypeTitle }}
        </h2>
        <div class="section-actions">
          <el-button :icon="Refresh" @click="fetchData" circle size="default" />
          <el-button :icon="Download" @click="exportData" circle size="default" />
        </div>
      </div>

      <!-- 数据卡片网格 -->
      <div class="data-grid" v-loading="loading">
        <div 
          v-for="item in data.list" 
          :key="item.data_id"
          class="data-card"
          @click="openMapDialog(item)"
        >
          <div class="card-header">
            <div class="data-type-badge" :class="getDataTypeClass(item)">
              <el-icon><Location v-if="item.data_type === 'vector'" /><Picture v-else /></el-icon>
              <span>{{ item.data_type === 'vector' ? '矢量' : '栅格' }}</span>
            </div>
            <div class="data-id">#{{ item.data_id }}</div>
          </div>
          
          <div class="card-body">
            <h3 class="data-title">{{ item.data_alias }}</h3>
            <p class="data-description">{{ item.data_introduction || '暂无描述信息' }}</p>
            
            <div class="data-meta">
              <div class="meta-item">
                <el-icon><Collection /></el-icon>
                <span>{{ item.data_source || '未知来源' }}</span>
              </div>
              <div class="meta-item" v-if="item.data_type === 'vector'">
                <el-icon><Compass /></el-icon>
                <span>{{ item.geomtype || '未知类型' }}</span>
              </div>
              <div class="meta-item" v-if="item.data_type === 'raster'">
                <el-icon><Picture /></el-icon>
                <span>{{ item.band_count }}波段</span>
              </div>
              <div class="meta-item">
                <el-icon><Coordinate /></el-icon>
                <span>{{ item.coordinate_system || '未知坐标系' }}</span>
              </div>
            </div>
          </div>
          
          <div class="card-footer">
            <div class="data-uuid">
              <span class="uuid-label">UUID:</span>
              <span class="uuid-value">{{ item.uuid }}</span>
            </div>
            <div class="card-actions">
              <el-button type="primary" size="small" @click.stop="openRequestDialog(item)">
                <el-icon><Download /></el-icon>
                申请数据
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="!loading && data.list.length === 0" class="empty-state">
        <el-empty description="暂无数据">
          <template #image>
            <div class="empty-icon">
              <el-icon><DataAnalysis /></el-icon>
            </div>
          </template>
          <template #description>
            <p>没有找到符合条件的数据</p>
            <p class="empty-tips">请尝试调整搜索条件或筛选器</p>
          </template>
        </el-empty>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-section" v-if="total > 0">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        :current-page="page"
        :page-size="pageSize"
        :page-sizes="[12, 24, 48, 96]"
        @current-change="pageChanged"
        @size-change="sizeChanged"
      />
    </div>
  </div>

  <!-- 数据详情对话框 -->
  <el-dialog
    v-model="viewDataVisible"
    width="75%"
    custom-class="data-detail-dialog rounded-dialog"
    :show-close="false"
    top="8vh"
    draggable
    @closed="destroyMapView"
  >
    <template #header="{ close }">
      <div class="dialog-header-custom">
        <div class="dialog-title-info">
          <h3 class="dialog-main-title">{{ selectedData.data_alias }}</h3>
          <span class="dialog-subtitle">{{ selectedData.data_type === 'vector' ? '矢量数据' : '栅格数据' }}</span>
        </div>
        <el-button text circle :icon="Close" @click="close" class="header-close-btn" title="关闭"></el-button>
      </div>
    </template>
    
    <div class="data-detail-layout">
      <div class="map-preview-section">
        <div class="map-container" ref="mapContainer">
          <div class="map-controls">
            <el-button 
              circle 
              :icon="ArrowLeftBold" 
              @click="viewDataVisible = false"
              class="map-back-btn"
              title="返回列表"
            />
            <div class="map-search-controls" v-if="isVectorData">
              <el-input
                v-model="mapSearchKeyword"
                placeholder="搜索地图位置..."
                :prefix-icon="Search"
                clearable
                @keydown.enter="handleMapSearch"
                class="map-search-input"
              />
              <el-button 
                :icon="Search" 
                @click="handleMapSearch" 
                class="map-search-btn" 
                circle 
              />
            </div>
          </div>
          <div class="raster-placeholder" v-if="!isVectorData">
            <div class="placeholder-content">
              <el-icon><Picture /></el-icon>
              <h4>栅格数据预览</h4>
              <p>栅格数据无法直接在地图上预览，您可以申请下载后查看</p>
            </div>
          </div>
        </div>
      </div>
      
      <div class="data-info-section">
        <div class="info-header">
          <h4 class="info-section-title">数据详情</h4>
        </div>
        
        <div class="info-content">
          <div class="info-description">
            <h5>数据描述</h5>
            <p>{{ selectedData.data_introduction || '暂无描述信息' }}</p>
          </div>
          
          <el-divider />
          
          <div class="info-metadata">
            <h5>技术参数</h5>
            <div class="metadata-grid">
              <div class="metadata-item">
                <span class="metadata-label">数据标识</span>
                <span class="metadata-value">{{ selectedData.uuid }}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">数据来源</span>
                <span class="metadata-value">{{ selectedData.data_source || '未知' }}</span>
              </div>
              <div class="metadata-item" v-if="selectedData.data_type === 'vector'">
                <span class="metadata-label">几何类型</span>
                <span class="metadata-value">{{ selectedData.geomtype || '未知' }}</span>
              </div>
              <div class="metadata-item" v-if="selectedData.data_type === 'raster'">
                <span class="metadata-label">波段数量</span>
                <span class="metadata-value">{{ selectedData.band_count }}波段</span>
              </div>
              <div class="metadata-item" v-if="selectedData.data_type === 'raster'">
                <span class="metadata-label">像元类型</span>
                <span class="metadata-value">{{ selectedData.pixel_type || '未知' }}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">坐标系统</span>
                <span class="metadata-value">{{ selectedData.coordinate_system || '未知' }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="info-actions">
          <el-button 
            type="primary" 
            size="large" 
            class="apply-data-btn"
            @click="openRequestDialog(selectedData)"
          >
            <el-icon><Download /></el-icon>
            申请使用此数据
          </el-button>
        </div>
      </div>
    </div>
  </el-dialog>

  <!-- 申请数据对话框 -->
  <el-dialog
    v-model="requestDataVisible"
    title="数据使用申请"
    width="600px"
    custom-class="request-dialog rounded-dialog"
    :before-close="handleClose"
    draggable
  >
    <el-form 
      ref="requestFormRef" 
      :model="requestInformation" 
      :rules="rules" 
      label-width="120px"
      class="request-form"
    >
      <el-form-item label="申请数据">
        <div class="data-info-display">
          <el-icon><Location v-if="requestInformation.data_type === 'vector'" /><Picture v-else /></el-icon>
          <span>{{ requestInformation.data_alias }}</span>
          <el-tag size="small">{{ requestInformation.data_type === 'vector' ? '矢量' : '栅格' }}</el-tag>
        </div>
      </el-form-item>
      
      <el-form-item label="数据标识" required>
        <el-input v-model="requestInformation.uuid" disabled />
      </el-form-item>
      
      <el-form-item label="申请人姓名" prop="applicant">
        <el-input 
          v-model="requestInformation.applicant" 
          placeholder="请输入您的姓名"
          size="large"
        />
      </el-form-item>
      
      <el-form-item label="员工编号" prop="user_number">
        <el-input 
          v-model="requestInformation.user_number" 
          placeholder="请输入员工编号"
          size="large"
        />
      </el-form-item>
      
      <el-form-item label="申请用途" prop="reason">
        <el-input 
          v-model="requestInformation.reason" 
          type="textarea" 
          :rows="4" 
          placeholder="请详细描述数据使用目的和用途"
          size="large"
        />
      </el-form-item>
    </el-form>
    
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="requestDataVisible = false" size="large">取消</el-button>
        <el-button type="primary" @click="submitForm" size="large">
          <el-icon><Check /></el-icon>
          提交申请
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>





<script setup>
import { ref, reactive, onMounted, computed, nextTick, watch } from 'vue';
import { 
  Search, Close, ArrowLeftBold, Location, Picture, DataAnalysis, 
  View, Download, Refresh, Grid, Collection, Compass, Coordinate, Check 
} from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox, ElDivider } from 'element-plus';
import axios from '@/utils/Axios';
import { useUserStore } from '@/stores/userStore';

import 'ol/ol.css';
import Map from 'ol/Map';
import OlView from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import { TileWMS, XYZ } from 'ol/source';
import { ScaleLine, Rotate, defaults as defaultControls } from 'ol/control';

const tiandituKey = import.meta.env.VITE_TIANDITU_KEY || '11ac7f190ef74ee4bd64081fe7ae419c';

// 状态管理
const loading = ref(true);
const data = reactive({ list: [] });
const keyword = ref('');
const page = ref(1);
const pageSize = ref(12);
const total = ref(0);
const totalVector = ref(0);
const totalRaster = ref(0);

// 筛选条件
const activeDataType = ref('all');
const dataSourceFilter = ref('');
const timeFilter = ref('');

// 对话框状态
const viewDataVisible = ref(false);
const requestDataVisible = ref(false);
const mapContainer = ref(null);
const mapView = ref(null);
const mapSearchKeyword = ref('');
const requestFormRef = ref(null);

// 用户状态
const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const userName = computed(() => userStore.userName);

// 选中的数据
const selectedData = reactive({
  data_id: '',
  uuid: '',
  data_name: '',
  data_alias: '',
  data_introduction: '',
  data_type: '',
  data_source: '',
  data_url: '',
  layer: '',
  geomtype: '',
  coordinate_system: '',
  band_count: null,
  pixel_type: null
});

// 【关键修复】: 初始申请信息对象，包含所有必填字段
const initialRequestInformation = {
  data_id: '',
  data_name: '', // 必填
  data_alias: '',
  applicant: '',
  user_number: '',
  reason: '',
  uuid: '',
  data_type: 'vector',
  data_url: '',
  layer: ''
};
const requestInformation = reactive({ ...initialRequestInformation });

// 表单验证规则
const rules = {
  applicant: [{ required: true, message: '请输入申请人姓名', trigger: 'blur' }],
  user_number: [{ required: true, message: '请输入员工编号', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入申请用途', trigger: 'blur' }]
};

// 计算属性
const isVectorData = computed(() => selectedData.data_type === 'vector');
const getDataTypeTitle = computed(() => {
  switch (activeDataType.value) {
    case 'vector': return '矢量数据';
    case 'raster': return '栅格数据';
    default: return '全部数据';
  }
});

// 方法定义
const getDataTypeClass = (item) => {
  return item.data_type === 'vector' ? 'vector-badge' : 'raster-badge';
};

const fetchData = async () => {
  loading.value = true;
  try {
    const params = {
      page: page.value,
      pageSize: pageSize.value,
      keyword: keyword.value || undefined,
      data_source: dataSourceFilter.value || undefined,
      time_filter: timeFilter.value || undefined
    };

    const [vectorResp, rasterResp] = await Promise.all([
      axios.get(`/api/vector_data_viewing`, { params }),
      axios.get(`/api/raster_data_viewing`, { params })
    ]);

    const vectorResult = vectorResp.data;
    const rasterResult = rasterResp.data;

    totalVector.value = (vectorResult?.data?.pages?.total) || 0;
    totalRaster.value = (rasterResult?.data?.pages?.total) || 0;

    let mergedList = [];

    if (activeDataType.value === 'vector' || activeDataType.value === 'all') {
      const vList = (vectorResult?.data?.list) || [];
      // 标记数据类型
      vList.forEach(item => item.data_type = 'vector');
      mergedList = [...mergedList, ...vList];
    }
    if (activeDataType.value === 'raster' || activeDataType.value === 'all') {
      const rList = (rasterResult?.data?.list) || [];
      // 标记数据类型
      rList.forEach(item => item.data_type = 'raster');
      mergedList = [...mergedList, ...rList];
    }

    // 简单排序
    data.list = mergedList.sort((a, b) => (a.data_id || 0) - (b.data_id || 0));
    
    // 如果是 all，总数简单相加
    if (activeDataType.value === 'all') {
      total.value = totalVector.value + totalRaster.value;
    } else if (activeDataType.value === 'vector') {
      total.value = totalVector.value;
    } else {
      total.value = totalRaster.value;
    }

  } catch (error) {
    console.error('获取数据失败:', error);
    ElMessage.error('数据获取异常');
    data.list = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  page.value = 1;
  fetchData();
};

const pageChanged = (newPage) => {
  page.value = newPage;
  fetchData();
};

const sizeChanged = (newSize) => {
  pageSize.value = newSize;
  page.value = 1;
  fetchData();
};

const openMapDialog = (row) => {
  Object.assign(selectedData, row);
  // 确保 data_name 有值
  selectedData.data_name = row.data_name || row.data_alias;
  
  mapSearchKeyword.value = '';
  viewDataVisible.value = true;
  nextTick(() => {
    if (isVectorData.value) {
      initializeMapView(row.data_url, row.layer);
    }
  });
};

// 【关键修复】: 正确填充申请信息
// 修复：确保打开弹窗时，所有字段都有值
const openRequestDialog = (dataToApply) => {
  requestInformation.reason = ''; // 清空理由
  
  // 打印日志，方便你在浏览器控制台看点的数据对不对
  console.log("点击申请的数据:", dataToApply);

  Object.assign(requestInformation, {
    data_id: dataToApply.data_id,
    // 关键点：后端通常需要 data_name，如果原数据里没有，就用别名代替，防止为空
    data_name: dataToApply.data_name || dataToApply.data_alias || '未命名数据',
    data_alias: dataToApply.data_alias,
    
    // 预填用户信息
    applicant: userName.value, 
    user_number: userNumber.value,
    
    // 关键点：确保 UUID 和 类型 存在
    uuid: dataToApply.uuid,
    data_type: dataToApply.data_type || 'vector', // 如果没类型，默认给 vector
    data_url: dataToApply.data_url,
    layer: dataToApply.layer
  });
  
  requestDataVisible.value = true;
};

const handleClose = (done) => {
  ElMessageBox.confirm('确定要关闭申请窗口吗？未保存的内容将丢失。')
    .then(() => {
      done();
      resetForm();
    })
    .catch(() => {});
};

// 【关键修复】: 提交表单逻辑
const submitForm = () => {
  requestFormRef.value.validate((valid) => {
    if (valid) {
      // 构造干净的 payload，不做多余的嵌套
      const payload = {
        // 确保是数字
        data_id: Number(requestInformation.data_id),
        
        // 确保有值
        data_name: requestInformation.data_name || requestInformation.data_alias || '未命名数据',
        data_alias: requestInformation.data_alias || '',
        
        // 确保 data_type 格式正确 (转小写，后端再处理)
        data_type: String(requestInformation.data_type || 'vector').toLowerCase(),
        
        data_url: requestInformation.data_url || '',
        uuid: requestInformation.uuid || '',
        layer: requestInformation.layer || '',
        
        // ★★★ 关键修改：字段名必须匹配后端接收的参数名 ★★★
        applicant_name: requestInformation.applicant,          // 前端叫 applicant, 后端要 applicant_name
        applicant_user_number: String(requestInformation.user_number), // 前端叫 user_number, 后端要 applicant_user_number
        
        reason: requestInformation.reason || ''
      };

      console.log("🚀 [前端调试] 准备发送的数据:", payload);

      axios.post(`/api/submit_application`, payload)
        .then((res) => {
          // 兼容后端返回格式 (有的返回 status 在外层，有的在 data 里)
          const isSuccess = res.data && (res.data.status === true || res.status === 200);
          
          if (isSuccess) {
            ElMessage.success('申请提交成功');
            requestDataVisible.value = false;
          } else {
            ElMessage.error(res.data?.msg || '提交失败');
          }
        })
        .catch(error => {
          console.error('❌ 申请提交失败:', error);
          // 获取后端返回的具体错误信息
          const errorMsg = error.response?.data?.msg || error.response?.data?.message || '申请提交失败';
          ElMessage.error(errorMsg);
        });
    } else {
      ElMessage.warning('请填写完整信息');
    }
  });
};

const resetForm = () => {
  if (requestFormRef.value) {
    requestFormRef.value.resetFields();
  }
  Object.assign(requestInformation, initialRequestInformation);
};

const handleMapSearch = async () => {
  if (!mapSearchKeyword.value.trim() || !mapView.value) {
    if (!mapSearchKeyword.value.trim()) {
      ElMessage.warning('请输入搜索关键词');
    }
    return;
  }
  
  try {
    const response = await axios.get(`/api/map/search`, {
      params: { keyword: mapSearchKeyword.value.trim() }
    });
    
    if (response.data && response.data.pois && response.data.pois.length > 0) {
      const lonlat = response.data.pois[0].lonlat.split(',').map(Number);
      mapView.value.getView().animate({
        center: lonlat,
        zoom: 14,
        duration: 1000
      });
    } else {
      ElMessage.warning(`未找到"${mapSearchKeyword.value}"`);
    }
  } catch (error) {
    console.error('地图搜索失败:', error);
    ElMessage.error('地图搜索服务异常');
  }
};

const initializeMapView = async (url, fullLayerName) => {
  if (!mapContainer.value) return;
  
  destroyMapView();
  
  const baseLayers = [
    new TileLayer({
      source: new XYZ({
        url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=${tiandituKey}`
      })
    }),
    new TileLayer({
      source: new XYZ({
        url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=${tiandituKey}`
      })
    })
  ];
  
  const map = new Map({
    target: mapContainer.value,
    layers: baseLayers,
    view: new OlView({
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
      map.addLayer(new TileLayer({
        source: new TileWMS({
          url: url,
          params: { 'LAYERS': fullLayerName, 'TILED': true },
          serverType: 'geoserver'
        })
      }));
      
      const response = await axios.get(`${url}?service=WMS&version=1.3.0&request=GetCapabilities`);
      const xmlDoc = new DOMParser().parseFromString(response.data, "text/xml");
      const layerNameToMatch = fullLayerName.includes(':') ? fullLayerName.split(':')[1] : fullLayerName;
      const layersNodes = xmlDoc.querySelectorAll('Layer > Name');
      const targetLayerNode = Array.from(layersNodes).find(node => node.textContent === layerNameToMatch)?.parentNode;
      
      if (targetLayerNode) {
        const bboxNode = targetLayerNode.querySelector('BoundingBox[CRS="CRS:84"]');
        if (bboxNode) {
          const bbox = [
            parseFloat(bboxNode.getAttribute('minx')),
            parseFloat(bboxNode.getAttribute('miny')),
            parseFloat(bboxNode.getAttribute('maxx')),
            parseFloat(bboxNode.getAttribute('maxy'))
          ];
          map.getView().fit(bbox, {
            size: map.getSize(),
            duration: 1000,
            padding: [50, 50, 50, 50]
          });
        }
      }
    } catch (error) {
      console.error('地图加载失败:', error);
      ElMessage.error('地图加载失败');
    }
  }
};

const destroyMapView = () => {
  if (mapView.value) {
    mapView.value.setTarget(null);
    mapView.value = null;
  }
};

const exportData = () => {
  ElMessage.success('数据导出功能开发中...');
};

// 监听筛选条件变化
watch([activeDataType, dataSourceFilter, timeFilter], () => {
  page.value = 1;
  fetchData();
});

// 生命周期
onMounted(() => {
  fetchData();
});
</script>




<style scoped>
/* 地理空间数据云风格设计 */
.data-catalog-page {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  min-height: calc(100vh - 60px);
  padding: 0;
}

/* 页面头部 - 英雄区域 */
.page-hero {
  background: linear-gradient(135deg, #1e40af 0%, #3b82f6 50%, #60a5fa 100%);
  color: white;
  padding: 60px 40px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.page-hero::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grid" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M 10 0 L 0 0 0 10" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="0.5"/></pattern></defs><rect width="100" height="100" fill="url(%23grid)"/></svg>');
  opacity: 0.3;
}

.hero-content {
  flex: 1;
  position: relative;
  z-index: 1;
}

.hero-title {
  font-size: 48px;
  font-weight: 700;
  margin: 0 0 16px 0;
  text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.hero-subtitle {
  font-size: 20px;
  opacity: 0.9;
  margin: 0 0 32px 0;
  font-weight: 400;
}

.hero-stats {
  display: flex;
  align-items: center;
  gap: 32px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 4px;
  text-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-label {
  font-size: 14px;
  opacity: 0.8;
  font-weight: 500;
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: rgba(255,255,255,0.3);
}

.hero-visual {
  width: 200px;
  height: 200px;
  position: relative;
  z-index: 1;
}

.globe-container {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.globe-icon {
  width: 160px;
  height: 160px;
  filter: drop-shadow(0 4px 8px rgba(0,0,0,0.2));
  animation: rotate 20s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 搜索区域 */
.search-section {
  background: white;
  padding: 40px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}

.search-container {
  max-width: 1200px;
  margin: 0 auto;
}

.search-main {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
}

.search-icon {
  font-size: 24px;
  color: #64748b;
}

.search-input {
  flex: 1;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  border: 2px solid #e2e8f0;
  padding: 16px 20px;
  font-size: 16px;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.search-input :deep(.el-input__wrapper):hover {
  border-color: #3b82f6;
  box-shadow: 0 6px 20px rgba(59, 130, 246, 0.15);
}

.search-input :deep(.el-input__wrapper).is-focus {
  border-color: #1e40af;
  box-shadow: 0 6px 20px rgba(30, 64, 175, 0.2);
}

.search-btn {
  border-radius: 12px;
  padding: 16px 32px;
  font-size: 16px;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  transition: all 0.3s ease;
}

.search-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
}

.search-filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.data-type-radio {
  width: 100%;
}

.data-type-radio :deep(.el-radio-button__inner) {
  padding: 12px 16px;
  font-size: 14px;
  border-radius: 8px;
  margin: 0 4px;
  transition: all 0.3s ease;
}

.filter-select {
  width: 100%;
}

.filter-select :deep(.el-select__wrapper) {
  border-radius: 8px;
  border: 2px solid #e2e8f0;
  transition: all 0.3s ease;
}

.filter-select :deep(.el-select__wrapper):hover {
  border-color: #3b82f6;
}

/* 数据展示区域 */
.data-section {
  padding: 40px;
  max-width: 1400px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.section-title {
  font-size: 28px;
  font-weight: 700;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
}

.section-title .el-icon {
  font-size: 32px;
  color: #3b82f6;
}

.section-actions {
  display: flex;
  gap: 12px;
}

.section-actions .el-button {
  border-radius: 8px;
  transition: all 0.3s ease;
}

.section-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

/* 数据卡片网格 */
.data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  margin-bottom: 40px;
}

.data-card {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  border: 1px solid #e5e7eb;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.data-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3b82f6, #1e40af);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.data-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(0,0,0,0.12);
}

.data-card:hover::before {
  opacity: 1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.data-type-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.vector-badge {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
}

.raster-badge {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
  color: #166534;
}

.data-id {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.data-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 12px 0;
  line-height: 1.4;
}

.data-description {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 20px 0;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.data-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #6b7280;
}

.meta-item .el-icon {
  font-size: 14px;
  color: #9ca3af;
}

.card-footer {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-uuid {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.uuid-label {
  font-size: 10px;
  color: #9ca3af;
  font-weight: 600;
}

.uuid-value {
  font-size: 11px;
  color: #6b7280;
  font-family: 'Courier New', monospace;
  word-break: break-all;
}

.card-actions .el-button {
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.empty-icon {
  font-size: 64px;
  color: #d1d5db;
  margin-bottom: 16px;
}

.empty-tips {
  font-size: 14px;
  color: #9ca3af;
  margin-top: 8px;
}

/* 分页 */
.pagination-section {
  display: flex;
  justify-content: center;
  padding: 40px;
}

/* 数据详情对话框 */
.data-detail-dialog {
  border-radius: 20px;
  overflow: hidden;
}

.dialog-header-custom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-bottom: 1px solid #e5e7eb;
}

.dialog-title-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dialog-main-title {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.dialog-subtitle {
  font-size: 14px;
  color: #6b7280;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  padding: 4px 12px;
  border-radius: 12px;
  font-weight: 600;
}

.header-close-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  transition: all 0.3s ease;
}

.header-close-btn:hover {
  background: #f3f4f6;
  transform: rotate(90deg);
}

.data-detail-layout {
  display: flex;
  height: 70vh;
  max-height: 600px;
}

.map-preview-section {
  flex: 3;
  position: relative;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

.map-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.map-controls {
  position: absolute;
  top: 20px;
  left: 20px;
  right: 20px;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.map-back-btn {
  border-radius: 50%;
  width: 44px;
  height: 44px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
}

.map-back-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.map-search-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.map-search-input {
  width: 300px;
}

.map-search-input :deep(.el-input__wrapper) {
  border-radius: 12px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.map-search-btn {
  border-radius: 50%;
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
  border: none;
  color: white;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  transition: all 0.3s ease;
}

.map-search-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
}

.raster-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(248, 250, 252, 0.95) 0%, rgba(226, 232, 240, 0.95) 100%);
  backdrop-filter: blur(5px);
}

.placeholder-content {
  text-align: center;
  color: #6b7280;
}

.placeholder-content .el-icon {
  font-size: 48px;
  margin-bottom: 16px;
  color: #9ca3af;
}

.placeholder-content h4 {
  font-size: 18px;
  margin: 0 0 8px 0;
  color: #374151;
}

.placeholder-content p {
  font-size: 14px;
  margin: 0;
}

.data-info-section {
  flex: 2;
  display: flex;
  flex-direction: column;
  background: white;
  border-left: 1px solid #e5e7eb;
}

.info-header {
  padding: 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-bottom: 1px solid #e5e7eb;
}

.info-section-title {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}

.info-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.info-description h5,
.info-metadata h5 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 12px 0;
}

.info-description p {
  font-size: 14px;
  line-height: 1.6;
  color: #6b7280;
  margin: 0;
}

.metadata-grid {
  display: grid;
  gap: 16px;
}

.metadata-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metadata-label {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metadata-value {
  font-size: 14px;
  color: #374151;
  font-weight: 500;
  word-break: break-word;
}

.info-actions {
  padding: 24px;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  border-top: 1px solid #e5e7eb;
}

.apply-data-btn {
  width: 100%;
  border-radius: 12px;
  padding: 16px 24px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
  border: none;
  transition: all 0.3s ease;
}

.apply-data-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}

/* 申请对话框 */
.request-dialog {
  border-radius: 20px;
}

.data-info-display {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 12px;
  border: 1px solid #bae6fd;
}

.data-info-display .el-icon {
  font-size: 20px;
  color: #0284c7;
}

.data-info-display span {
  font-weight: 600;
  color: #0c4a6e;
}

.request-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: #374151;
}

.request-form :deep(.el-input__wrapper),
.request-form :deep(.el-textarea__inner) {
  border-radius: 8px;
  border: 2px solid #e2e8f0;
  transition: all 0.3s ease;
}

.request-form :deep(.el-input__wrapper):hover,
.request-form :deep(.el-textarea__inner):hover {
  border-color: #3b82f6;
}

.request-form :deep(.el-input__wrapper).is-focus,
.request-form :deep(.el-textarea__inner):focus {
  border-color: #1e40af;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 24px 0 0 0;
}

.dialog-footer .el-button {
  border-radius: 8px;
  padding: 12px 24px;
  font-weight: 600;
  transition: all 0.3s ease;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .page-hero {
    flex-direction: column;
    text-align: center;
    gap: 32px;
  }
  
  .hero-stats {
    justify-content: center;
  }
  
  .data-detail-layout {
    flex-direction: column;
    height: 80vh;
  }
  
  .map-preview-section {
    flex: 1;
    min-height: 300px;
  }
}

@media (max-width: 768px) {
  .page-hero {
    padding: 40px 20px;
  }
  
  .hero-title {
    font-size: 32px;
  }
  
  .hero-stats {
    flex-direction: column;
    gap: 16px;
  }
  
  .stat-divider {
    width: 60px;
    height: 1px;
  }
  
  .search-section {
    padding: 20px;
  }
  
  .search-main {
    flex-direction: column;
  }
  
  .search-filters {
    grid-template-columns: 1fr;
  }
  
  .data-section {
    padding: 20px;
  }
  
  .data-grid {
    grid-template-columns: 1fr;
  }
  
  .map-controls {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .map-search-controls {
    width: 100%;
  }
  
  .map-search-input {
    width: 100%;
  }
}

/* 地图控件样式覆盖 */
:deep(.ol-zoom) {
  top: 20px;
  left: 20px;
  background: transparent;
}

:deep(.ol-zoom-in),
:deep(.ol-zoom-out) {
  width: 44px;
  height: 44px;
  font-size: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  color: #374151;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 8px;
}

:deep(.ol-zoom-in) {
  border-radius: 8px 8px 0 0;
  margin-bottom: 4px;
}

:deep(.ol-zoom-out) {
  border-radius: 0 0 8px 8px;
}

:deep(.ol-zoom-in:hover),
:deep(.ol-zoom-out:hover) {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

:deep(.ol-control-custom-rotate) {
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
  width: 44px;
  height: 44px;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

:deep(.ol-control-custom-rotate:hover) {
  background: white;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

:deep(.ol-scale-line) {
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 8px 12px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #374151;
}
</style>
:deep(.rounded-dialog) { border-radius: 12px; overflow: hidden; }
:deep(.rounded-dialog .el-dialog__header) { margin-right: 0; padding-top: 20px; }
