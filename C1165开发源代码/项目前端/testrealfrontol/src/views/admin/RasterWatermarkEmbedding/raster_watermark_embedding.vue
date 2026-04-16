<!-- src/views/admin/Watermark Embedding/raster_watermark_embedding.vue -->
<!-- 栅格数据水印嵌入界面 -->

<template>
    <div>
      <!-- 水印嵌入申请表格 -->
      <el-table :data="data.list" border style="width: 1175px">
        <el-table-column prop="id" label="申请编号" width="82.5" />
        <el-table-column prop="data_alias" label="数据名称" width="85"/>
        <el-table-column prop="data_id" label="栅格数据编号" width="110"/>
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
            <el-button size="small" type="primary" @click="openDataPreviewDialog(scope.row)">查看原始数据</el-button>
            <el-button size="small" type="primary" @click="embedding_watermark(scope.row)">嵌入水印</el-button>
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
    <el-dialog title="数据预览" v-model="viewDataVisible" width="50%" :before-close="handleClose">
      <div class="dialog-container">
        <!-- 这里是栅格数据预览区域，例如一个图片或一个画布 -->
        <!-- 由于您提到前端数据为空，这里先使用一个占位符 -->
        <div class="raster-preview-container">
          <p>栅格数据预览区域</p>
          <p>（此处应显示栅格数据，待前端数据和API调用逻辑完成后实现）</p>
        </div>
        <div class="info-container">
          <el-descriptions title="原始栅格数据" :column='1'>
            <el-descriptions-item label="数据名称:">{{ selectedData.data_alias }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </template>
  
  <script setup>
  import { reactive, ref, onMounted, watch, nextTick } from 'vue';
  import { ElMessage, ElMessageBox } from 'element-plus';
  import axios from 'axios';
  
  // 使用环境变量获取API基础URL，确保端口正确
  const basic_url = import.meta.env.VITE_API_URL;
  
  const data = reactive({ list: [] });
  const page = ref(1);
  const pageSize = ref(2);
  const total = ref(0);
  const viewDataVisible = ref(false);
  
  const selectedData = reactive({
    data_alias: '',
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
    if (status === true) return '通过';
    if (status === false) return '不通过';
    if (status === null) return '待审核';
    return '';
  };
  
  const get_applications = async () => {
    try {
      // 调用栅格数据专用的API端点
      const response = await axios.get(`${basic_url}/api/adm2_embedding_raster_watermark_applications`, {
        params: { page: page.value, pageSize: pageSize.value },
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
  
  const openDataPreviewDialog = (row) => {
    selectedData.data_alias = row.data_alias;
    viewDataVisible.value = true;
    // TODO: 这里需要根据后端API返回的栅格数据URL来加载图像或在canvas上绘制
    // 目前先使用占位符
  };
  
  const handleClose = (done) => {
    ElMessageBox.confirm('确认关闭？').then(() => {
      done();
    }).catch(() => {});
  };
  
  const embedding_watermark = async (row) => {
    const ApplicationId = row.id;
    const DataId = row.data_id;
    const applicant_user_number = row.applicant_user_number;
  
    ElMessage.info('正在嵌入水印，请稍候...');
  
    // 调用栅格数据嵌入水印的API端点
    axios.post(`${basic_url}/api/embedding_raster_watermark`, {
      application_id: ApplicationId,
      data_id: DataId,
      applicant_user_number: applicant_user_number,
      embed_person:row.adm2_name,
      applicant:row.applicant_name
    }, {
      responseType: 'blob'
    })
    .then(response => {
      console.log('Response Headers:', response.headers);
      const disposition = response.headers['content-disposition'];
      console.log('Content-Disposition:', disposition);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      let fileName = 'default.zip';
      if (disposition) {
        const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
        console.log('Filename matches:', matches);
        if (matches && matches[1]) {
          fileName = matches[1].replace(/['"]/g, '');
        }
      }
      console.log('Final filename:', fileName);
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      ElMessage.success('嵌入成功，已打包成zip文件');
      get_applications(); // 嵌入成功后刷新列表
    })
    .catch(error => {
      ElMessage.error('嵌入水印失败');
      console.error('Error embedding watermark:', error);
    });
  };
  
  </script>
  
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
  