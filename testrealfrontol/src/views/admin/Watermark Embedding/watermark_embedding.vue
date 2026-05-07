<template>
  <div>
    <div class="data-type-tabs" style="margin-bottom: 12px;">
      <span class="data-type-label">数据类型：矢量</span>
    </div>
    <el-table :data="data.list" border style="width: 1175px">
      <el-table-column prop="id" label="申请编号" width="82.5" />
      <el-table-column prop="data_alias" label="数据名称" width="85"/>
      <el-table-column prop="data_id" label="矢量数据编号" width="110"/>
      <el-table-column prop="applicant_user_number" label="申请人编号" width="100"/>
      <el-table-column prop="applicant_name" label="申请人姓名" width="95"/>
      <el-table-column prop="adm1_name" label="一审人员姓名" width="110"/>
      <el-table-column prop="adm2_name" label="二审人员姓名" width="110"/>

      <el-table-column label="一审状态" width="85">
        <template v-slot="scope">
          {{ getStatusText(scope.row.first_statu) }}
        </template>
      </el-table-column>

      <el-table-column label="二审状态" width="85">
        <template v-slot="scope">
          <div v-if="!scope.row.first_statu">
            {{ getStatusText('空') }}
          </div>
          <div v-else>
            {{ getStatusText(scope.row.second_statu) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="水印">
        <template #default="scope">
          <el-image class="qr-code-image"
            :src="scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : ''"
            :preview-src-list="[scope.row.qrcode ? `data:image/png;base64,${scope.row.qrcode}` : '']"
            fit="cover"
            style="width: 50px; height: 50px;"
          />
        </template>
      </el-table-column>

      <el-table-column label="操作" width="300">
        <template v-slot="scope">
          <el-button size="small" type="primary" @click="openMapDialog(scope.row)">查看原始数据</el-button>
          <el-button size="small" type="primary" @click="embedding_watermark(scope.row)">嵌入水印</el-button>
<!--          <el-button size="small" type="primary" @click="OpenSendZip(scope.row)">发送数据</el-button>-->
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
    title="矢量地图服务预览" 
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
          <el-empty description="暂无地图服务地址，无法加载预览" />
        </div>
      </div>
      <div class="info-container">
        <h4 class="info-title">申请与数据信息</h4>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="数据名称">{{ selectedData.data_alias }}</el-descriptions-item>
          <el-descriptions-item label="数据编号">{{ selectedData.data_id }}</el-descriptions-item>
          <el-descriptions-item label="申请人">{{ selectedData.applicant_name }} ({{ selectedData.applicant_user_number }})</el-descriptions-item>
          <el-descriptions-item label="地图服务地址">
            <span class="url-text" :title="selectedData.data_url">{{ selectedData.data_url || '—' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        <p class="info-tip">关闭后可对该条记录执行「嵌入水印」。</p>
      </div>
    </div>
  </el-dialog>


  <el-dialog title="发送数据" v-model="SendDataVisible" width="50%" :before-close="(done)=>handleClose('send',done)">
    <div class="send-dialog-container" >
      <el-upload

        class="send_file"
        drag
        action=""
        multiple
        accept=".zip"


      >
        <el-icon class="el-icon--upload"><upload-filled/></el-icon>
        <div class="el-upload__text">
          拖放要发送的zip文件到这或者<em>点击这里</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            仅限发送zip文件
          </div>
        </template>
      </el-upload>
    </div>
  </el-dialog>



</template>

<script setup>
import {useUserStore} from "@/stores/userStore.js";
import {reactive, ref, onMounted, watch, nextTick, computed} from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import {UploadFilled} from "@element-plus/icons-vue";
import axios from '@/utils/Axios';
import '@arcgis/core/assets/esri/themes/light/main.css';
import MapView from '@arcgis/core/views/MapView';
import Map from '@arcgis/core/Map';
import MapImageLayer from '@arcgis/core/layers/MapImageLayer';
import FeatureLayer from '@arcgis/core/layers/FeatureLayer';



const data = reactive({ list: [] });
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const dataTypeTab = ref('');

const requestFormRef = ref(null);

const SendDataVisible=ref(false);
const viewDataVisible = ref(false);
const mapContainer = ref(null);
let mapView = null;




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
  if (status === true) return '通过';
  if (status === false) return '不通过';
  if (status === null) return '待审核';
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
  try {
    const response = await axios.get(`/api/adm2_embedding_watermark_applications`, {
      params: { page: page.value, pageSize: pageSize.value, data_type: 'vector' },
      responseType: 'json'
    });

    if (!response.data || !response.data.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data.msg || '获取记录失败');
      return;
    }

    data.list = response.data.application_data;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error('Error fetching records:', err);
    ElMessage.error('获取记录失败');
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


const embedding_watermark =async (row) => {
  const ApplicationId = row.id;
  const DataId = row.data_id;
  const applicant_user_number = row.applicant_user_number;
  const isRaster = (row.data_type || '').toLowerCase() === 'raster';

  ElMessage.info('正在嵌入水印，请稍候...');

  if (isRaster) {
    axios.post(`/api/admin/embed_dispatch`, { application_id: ApplicationId }, { responseType: 'json' })
      .then(res => {
        if (res.data && res.data.status) {
          ElMessage.success(res.data.msg || '栅格水印嵌入成功');
          get_applications();
        } else {
          ElMessage.error(res.data?.msg || '栅格水印嵌入失败');
        }
      })
      .catch(err => {
        ElMessage.error('栅格水印嵌入失败');
        console.error(err);
      });
    return;
  }

  axios.post(`/api/embedding_watermark`, {
    application_id: ApplicationId,
    data_id: DataId,
    applicant_user_number: applicant_user_number,
    embed_person:row.adm2_name,
    applicant:row.applicant_name
  }, {
    responseType: 'blob'  // 设置响应类型为 blob
  })
  .then(response => {
    // 打印完整的响应头
    console.log('Response Headers:', response.headers);
    // 打印Content-Disposition内容
    const disposition = response.headers['content-disposition'];
    console.log('Content-Disposition:', disposition);
    // 创建一个 URL 对象来处理 Blob 数据
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    // 从响应头中提取文件名（如果后端有设置下载文件名）
    let fileName = 'default.zip';
    if (disposition) {
      const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
      console.log('Filename matches:', matches);
      if (matches && matches[1]) {
        fileName = matches[1].replace(/['"]/g, ''); // 去除引号
      }
    }
    console.log('Final filename:', fileName);
    link.setAttribute('download', fileName);  // 设置下载的文件名
    document.body.appendChild(link);
    link.click();  // 触发下载
    document.body.removeChild(link);  // 清理 DOM
    window.URL.revokeObjectURL(url);  // 释放 URL 对象
    ElMessage.success('嵌入成功，已打包成zip文件');
  })
  .catch(error => {
    ElMessage.error('嵌入水印失败');
    console.error('Error embedding watermark:', error);
  });
};


const OpenSendZip=(row)=>{
  SendDataVisible.value=true
}


const selectedData = reactive({
  data_alias: '',
  data_id: '',
  data_url: '',
  applicant_name: '',
  applicant_user_number: ''
});

const openMapDialog = (row) => {
  selectedData.data_alias = row.data_alias ?? '';
  selectedData.data_id = row.data_id ?? '';
  selectedData.data_url = row.data_url ?? '';
  selectedData.applicant_name = row.applicant_name ?? '';
  selectedData.applicant_user_number = row.applicant_user_number ?? '';
  viewDataVisible.value = true;
  nextTick(() => {
    if (selectedData.data_url) {
      initializeMapView(selectedData.data_url);
    }
  });
};


const initializeMapView = (data_url) => {
  // Create layers with the correct URL
  const mapImageLayer = new MapImageLayer({ url: data_url });
  const featureLayer = new FeatureLayer({ url: data_url });

  // Create a Map instance with the layers
  const map = new Map({
    basemap: 'topo-vector',
    layers: [mapImageLayer, featureLayer],
  });

  // Create and configure the MapView
  mapView = new MapView({
    container: mapContainer.value,
    map,
  });

  // When the map view is ready
  mapView.when(() => {
    // Wait for the feature layer to be ready
    featureLayer.when(() => {
      featureLayer.queryExtent().then((response) => {
        mapView.goTo(response.extent);
      }).catch((error) => console.error('Error navigating to extent:', error));
    }).catch((error) => console.error('Error loading feature layer:', error));

    mapView.ui.remove('attribution');
  }).catch((error) => console.error('Error loading map view:', error));
};


const destroyMapView = () => {
  if (mapView) {
    mapView.destroy();
    mapView = null;
  }
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('确认关闭？').then(() => {
    done();
    if (dialogType === 'map') {
      destroyMapView(); // 仅在处理地图视图的对话框时销毁地图视图
    } else if (dialogType === 'send') {
      resetForm(); // 在关闭申请使用数据对话框时重置表单
    }
  }).catch(() => {});
};



</script>

<style>

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

.vector-preview-layout .map-wrapper {
  flex: 3;
  min-width: 0;
  position: relative;
  height: 480px;
  border-radius: 12px;
  overflow: hidden;
  background: #f1f5f9;
}

.vector-preview-layout .map-container {
  width: 100%;
  height: 100%;
}

.map-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
}

.vector-preview-layout .info-container {
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

.url-text {
  font-size: 12px;
  color: #64748b;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.info-tip {
  font-size: 12px;
  color: #94a3b8;
  margin: 16px 0 0 0;
}

.send-dialog-container{
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;

}

.send_file{
  width: 100%;
}

</style>
