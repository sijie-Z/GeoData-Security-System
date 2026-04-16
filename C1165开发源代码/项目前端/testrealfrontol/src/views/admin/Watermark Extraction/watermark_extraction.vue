<!-- <template>
  <div class="upload_data_container">
    <el-input v-model="GetIdInput" style="width: 250px" placeholder="请输入疑似泄露数据对应的数据编号"/>
    <el-button size="small" type="primary" @click="click_extract">选择文件上传</el-button>
  </div>

  <div v-if="extractedWatermarkBase64" class="watermark-container with-margin-top">
    <div class="watermark-header">
      从数据中提取出的水印
    </div>
    <div class="watermark-image-container">
      <img :src="`data:image/png;base64,${extractedWatermarkBase64}`" alt="Extracted Watermark" class="watermark-image"/>
    </div>
  </div>
  <div v-else class="with-margin-top">
    加载提取的水印失败，请稍后再试。
  </div>

  <el-dialog title="发送数据" v-model="ExtractVisible" width="50%" :before-close="(done) => handleClose('send', done)">
    <div class="send-dialog-container">
      <el-upload
        class="send_file"
        drag
        :action="uploadUrl"
        multiple
        accept=".zip"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
        :data="uploadData"
      >
        <el-icon class="el-icon--upload"><UploadFilled/></el-icon>
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
import { UploadFilled,Plus } from "@element-plus/icons-vue";
import {reactive, ref, watch} from "vue";
import axios from "axios";
import { ElMessage, ElMessageBox } from "element-plus";


// const data = reactive({
//   list:[]
// })

const ExtractVisible = ref(false);

const GetIdInput = ref('');
const extractedWatermarkBase64 = ref('');
const originalWatermarkBase64 = ref('');
const numberInput = ref('');

const basic_url=import.meta.env.VITE_API_URL

const uploadUrl = `${basic_url}/api/upload_zip`;

const upload_original_watermark_action=`${basic_url}/api/upload_original_watermark`
const upload_extracted_watermark_action=`${basic_url}/api/upload_extracted_watermark`

const originalUploadComplete = ref(false);
const extractedUploadComplete = ref(false);


// 上传控件的引用
const uploadOriginal = ref(null)
const uploadExtracted = ref(null)


const originalFile = ref(null);
const extractedFile = ref(null);
const originalThumbnail = ref('');
const extractedThumbnail = ref('');
const isUploading = ref(false);



const handleOriginalFileChange = (file) => {
  console.log('Original file selected:', file);
  originalFile.value = file.raw; // 存储文件对象
  originalThumbnail.value = URL.createObjectURL(file.raw); // 显示缩略图
};

// 处理提取后的文件选择
const handleExtractedFileChange = (file) => {
  console.log('Extracted file selected:', file);
  extractedFile.value = file.raw; // 存储文件对象
  extractedThumbnail.value = URL.createObjectURL(file.raw); // 显示缩略图
};


const uploadFiles = async () => {
  if (!originalFile.value) {
    ElMessage.error('请上传原始水印文件');
    return;
  }

  if (!extractedFile.value) {
    ElMessage.error('请上传提取后的水印文件');
    return;
  }

  isUploading.value = true;

  const formData = new FormData();
  formData.append('originalFile', originalFile.value);
  formData.append('extractedFile', extractedFile.value);

  try {
    const response = await axios.post(`${basic_url}/api/upload/ori&ext_watermark`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });

    if (response.data.status) {
      ElMessage.success('文件上传成功');
      UploadWatermarkSuccess(response.data); // 上传成功后处理
    } else {
      ElMessage.error('文件上传失败');
    }
  } catch (error) {
    ElMessage.error('上传出错');
  } finally {
    isUploading.value = false;
  }
};

const UploadWatermarkSuccess = (data) => {
  if (data.nc_value) {
    ElMessage.success(`NC值: ${data.nc_value}`);
    originalWatermarkBase64.value = data.original_watermark; // 显示原始水印
    extractedWatermarkBase64.value = data.extracted_watermark; // 显示提取的水印
  } else {
    ElMessage.error('NC值获取失败');
  }
};


const uploadData = ref({
  dataNumber: GetIdInput.value
});

watch(GetIdInput, (newValue) => {
  uploadData.value = {
    dataNumber: newValue
  };
});

const click_extract = () => {
  if (!GetIdInput.value) {
    ElMessage.error('请先填写数据编号');
    return;
  }
  ExtractVisible.value = true;
};

const handleUploadSuccess = (response, file) => {
  ElMessage.success(`文件 ${file.name} 上传成功！`);
  ExtractVisible.value = false;

  if (response.watermark_base64) {
    extractedWatermarkBase64.value = response.watermark_base64;
  } else {
    ElMessage.error('文件上传成功但未提取出水印');
  }
};

const handleUploadError = (err, file) => {
  let errorMessage = `文件 ${file.name} 上传失败！`;
  if (err.response && err.response.data && err.response.data.error) {
    errorMessage += ` 错误信息: ${err.response.data.error}`;
  }
  ElMessage.error(errorMessage);
  console.error("Error during file upload:", err);
};

const beforeUpload = (file) => {
  if (!GetIdInput.value) {
    ElMessage.error('请先填写数据编号');
    return false;
  }

  const isZipByType = file.type === 'application/zip' || file.type === 'application/x-zip-compressed';
  const isZipByExtension = file.name.endsWith('.zip');

  if (!(isZipByType || isZipByExtension)) {
    ElMessage.error('上传的文件必须是ZIP格式');
    return false;
  }

  uploadData.value = {
    dataNumber: GetIdInput.value
  };

  return true;
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('确认关闭？').then(() => {
    done();
    if (dialogType === 'send') {
      resetForm();
    }
  }).catch(() => {});
};

const resetForm = () => {
  GetIdInput.value = '';
  extractedWatermarkBase64.value = '';
  originalWatermarkBase64.value = '';
};

const handleNumberInput = async () => {
  if (numberInput.value) {
    try {
      const response = await axios.post(`${basic_url}/api/get_original_watermark`, {
        number: numberInput.value
      });

      if (response.data.status) {
        ElMessage.success('水印已成功获取');
        originalWatermarkBase64.value = response.data.original_watermark;
      } else {
        ElMessage.error('未能找到对应的水印');
        originalWatermarkBase64.value = '';
      }

    } catch (error) {
      ElMessage.error('获取水印失败，请稍后再试');
      console.error('Error while fetching watermark:', error);
      originalWatermarkBase64.value = '';
    }
  } else {
    ElMessage.warning('请输入编号');
  }
};


</script>


<style scoped>

.upload_data_container {
  display: flex;
  align-items: center;
  gap: 15px;
}

.with-margin-top {
  margin-top: 20px;
}

.watermark-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  background-color: #f9f9f9;
}

.watermark-header {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 10px;
  color: #333;
}

.watermark-image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: white;
  padding: 10px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.watermark-image {
  max-width: 100%;
  height: auto;
}

/* 针对第二个水印容器的样式 */
.original-watermark-container {
  max-width: 400px; /* 设置容器的最大宽度 */
  padding: 15px; /* 调整填充 */
}

.original-watermark-image {
  max-width: 80%; /* 调整图片的最大宽度 */
}

</style>


<style>

.thumbnail-uploader .thumbnail {
  width: 180px;
  height: 180px;
  display: block;
}

.thumbnail-uploader .el-upload {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: var(--el-transition-duration-fast);
}

.thumbnail-uploader .el-upload:hover {
  border-color: var(--el-color-primary);
}

.el-icon.thumbnail-uploader-icon {
  font-size: 28px;
  color: #8c939d;
  width: 180px;
  height: 180px;
  text-align: center;
}

</style>
 -->

 <!-- <template>
  <div class="watermark-extraction-view">
    <el-card class="action-card">
      <template #header>
        <div class="card-header">
          <span>水印提取操作</span>
          <el-tooltip
            effect="dark"
            content="输入数据编号，上传疑似泄露的zip文件，系统将自动提取隐藏的水印信息。"
            placement="top"
          >
            <el-icon><InfoFilled /></el-icon>
          </el-tooltip>
        </div>
      </template>
      <div class="action-content">
        <div class="input-group">
          <label>疑似泄露数据编号：</label>
          <el-input
            v-model="GetIdInput"
            placeholder="请输入数据编号"
            clearable
            style="width: 250px"
          />
        </div>
        <el-button
          type="primary"
          @click="click_extract"
          :disabled="!GetIdInput"
          >上传并提取水印</el-button
        >
      </div>
    </el-card>

    <div v-if="extractedWatermarkBase64" class="result-display-container">
      <el-card class="result-card">
        <template #header>
          <div class="card-header">
            <span>提取结果</span>
          </div>
        </template>
        <div class="watermark-comparison">
          <div class="watermark-item">
            <div class="watermark-title">提取出的水印</div>
            <div class="watermark-image-container">
              <img
                :src="`data:image/png;base64,${extractedWatermarkBase64}`"
                alt="Extracted Watermark"
                class="watermark-image"
              />
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <el-alert
      v-else-if="!GetIdInput && !extractedWatermarkBase64"
      title="请先输入数据编号并上传文件以提取水印"
      type="info"
      show-icon
      class="info-alert"
    />
    <el-alert
      v-else-if="!extractedWatermarkBase64"
      title="未提取到水印或文件无效，请检查后重试。"
      type="warning"
      show-icon
      class="info-alert"
    />

    <el-dialog
      title="上传疑似泄露文件"
      v-model="ExtractVisible"
      width="500px"
      center
      :before-close="(done) => handleClose('send', done)"
    >
      <div class="dialog-content">
        <el-upload
          class="send_file_uploader"
          drag
          :action="uploadUrl"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :data="uploadData"
          :limit="1"
          accept=".zip"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持文件格式：.zip（大小不超过50MB）
            </div>
          </template>
        </el-upload>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { UploadFilled, Plus, InfoFilled } from "@element-plus/icons-vue";
import { reactive, ref, watch } from "vue";
import axios from "axios";
import { ElMessage, ElMessageBox } from "element-plus";

const ExtractVisible = ref(false);
const GetIdInput = ref('');
const extractedWatermarkBase64 = ref('');
const basic_url = import.meta.env.VITE_API_URL;
const uploadUrl = `${basic_url}/api/upload_zip`;

const uploadData = ref({
  dataNumber: GetIdInput.value,
});

watch(GetIdInput, (newValue) => {
  uploadData.value = {
    dataNumber: newValue,
  };
});

const click_extract = () => {
  if (!GetIdInput.value) {
    ElMessage.error('请先填写数据编号');
    return;
  }
  ExtractVisible.value = true;
};

const handleUploadSuccess = (response, file) => {
  ElMessage.success(`文件 ${file.name} 上传成功！`);
  ExtractVisible.value = false;

  if (response.watermark_base64) {
    extractedWatermarkBase64.value = response.watermark_base64;
  } else {
    ElMessage.error('文件上传成功但未提取出水印');
    extractedWatermarkBase64.value = null; // 清空旧的水印，显示未提取到水印的提示
  }
};

const handleUploadError = (err, file) => {
  let errorMessage = `文件 ${file.name} 上传失败！`;
  if (err.response && err.response.data && err.response.data.error) {
    errorMessage += ` 错误信息: ${err.response.data.error}`;
  }
  ElMessage.error(errorMessage);
  console.error("Error during file upload:", err);
  extractedWatermarkBase64.value = null; // 上传失败，清空旧的水印
};

const beforeUpload = (file) => {
  if (!GetIdInput.value) {
    ElMessage.error('请先填写数据编号');
    return false;
  }

  const isZipByType = file.type === 'application/zip' || file.type === 'application/x-zip-compressed';
  const isZipByExtension = file.name.endsWith('.zip');

  if (!(isZipByType || isZipByExtension)) {
    ElMessage.error('上传的文件必须是ZIP格式');
    return false;
  }

  uploadData.value = {
    dataNumber: GetIdInput.value,
  };

  return true;
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('确认关闭？').then(() => {
    done();
    if (dialogType === 'send') {
      // 可以在这里重置表单，但由于已经用v-if控制，一般不需要
    }
  }).catch(() => {});
};
</script>

<style scoped>
.watermark-extraction-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.action-card {
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.action-content {
  display: flex;
  align-items: center;
  gap: 15px;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.result-display-container {
  max-width: 600px;
  margin: 0 auto;
}

.result-card {
  border: 1px solid #e4e7ed;
}

.watermark-comparison {
  display: flex;
  justify-content: center;
  gap: 40px;
  padding: 20px;
}

.watermark-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.watermark-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 10px;
  font-weight: bold;
}

.watermark-image-container {
  border: 1px solid #dcdfe6;
  padding: 10px;
  border-radius: 4px;
  background-color: #ffffff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.watermark-image {
  max-width: 200px;
  max-height: 200px;
  display: block;
}

.info-alert {
  max-width: 600px;
  margin: 0 auto;
}

.dialog-content {
  text-align: center;
}

.send_file_uploader .el-upload-dragger {
  padding: 30px;
}
</style> -->

<template>
  <div class="watermark-extraction-container">
    <div class="input-section">
      <el-input v-model="GetIdInput" style="width: 250px" placeholder="请输入疑似泄露数据对应的数据编号" clearable/>
      <el-button size="default" type="primary" @click="click_extract">选择文件并提取水印</el-button>
    </div>

    <el-card class="watermark-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>从数据中提取出的水印</span>
        </div>
      </template>
      <div v-if="extractedWatermarkBase64" class="watermark-image-wrapper">
        <img :src="`data:image/png;base64,${extractedWatermarkBase64}`" alt="Extracted Watermark" class="watermark-image"/>
      </div>
      <div v-else class="watermark-placeholder">
        <el-empty description="提取出的水印将在此处显示"></el-empty>
      </div>
    </el-card>

    <el-dialog title="上传数据" v-model="ExtractVisible" width="50%" :before-close="(done) => handleClose('send', done)">
      <div class="upload-dialog-content">
        <el-upload
          class="send_file_uploader"
          drag
          :action="uploadUrl"
          :data="uploadData"
          :limit="1"
          accept=".zip"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :file-list="[]"
        >
          <el-icon class="el-icon--upload"><UploadFilled/></el-icon>
          <div class="el-upload__text">
            将文件拖放到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              只能上传 .zip 格式文件，且文件内必须包含一个 .shp 文件。
            </div>
          </template>
        </el-upload>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { UploadFilled } from "@element-plus/icons-vue";
import { ref, watch } from "vue";
import axios from "axios";
import { ElMessage, ElMessageBox } from "element-plus";

// State and refs
const ExtractVisible = ref(false);
const GetIdInput = ref('');
const extractedWatermarkBase64 = ref('');

// API URL from environment variables
const basic_url = import.meta.env.VITE_API_URL;
const uploadUrl = `${basic_url}/api/upload_zip`;

// Data for file upload
const uploadData = ref({
  dataNumber: GetIdInput.value
});

// Watch for changes in the input field to update the upload data
watch(GetIdInput, (newValue) => {
  uploadData.value = {
    dataNumber: newValue
  };
});

// Handlers
const click_extract = () => {
  if (!GetIdInput.value) {
    ElMessage.error('请先填写数据编号');
    return;
  }
  ExtractVisible.value = true;
};

const handleUploadSuccess = (response, file) => {
  ElMessage.success(`文件 ${file.name} 上传成功！`);
  ExtractVisible.value = false;

  if (response.watermark_base64) {
    extractedWatermarkBase64.value = response.watermark_base64;
  } else {
    ElMessage.error('文件上传成功但未提取出水印');
  }
};

const handleUploadError = (err, file) => {
  let errorMessage = `文件 ${file.name} 上传失败！`;
  if (err.response && err.response.data && err.response.data.error) {
    errorMessage += ` 错误信息: ${err.response.data.error}`;
  }
  ElMessage.error(errorMessage);
  console.error("Error during file upload:", err);
};

const beforeUpload = (file) => {
  if (!GetIdInput.value) {
    ElMessage.error('请先填写数据编号');
    return false;
  }
  const isZipByType = file.type === 'application/zip' || file.type === 'application/x-zip-compressed';
  const isZipByExtension = file.name.endsWith('.zip');
  if (!(isZipByType || isZipByExtension)) {
    ElMessage.error('上传的文件必须是ZIP格式');
    return false;
  }
  return true;
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm('确认关闭？').then(() => {
    done();
    if (dialogType === 'send') {
      resetForm();
    }
  }).catch(() => {});
};

const resetForm = () => {
  GetIdInput.value = '';
  extractedWatermarkBase64.value = '';
};

</script>

<style scoped>
/* Main layout container with padding and flexbox for alignment */
.watermark-extraction-container {
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 8px;
}

/* Flex container for the input and button */
.input-section {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
}

/* Card for the watermark display */
.watermark-card {
  border-radius: 8px;
  background-color: #fff;
}

/* Custom header style for the cards */
.card-header {
  display: flex;
  justify-content: center;
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

/* Styles for the watermark image and its container */
.watermark-image-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 10px;
  min-height: 200px;
}

.watermark-image {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}

/* Placeholder for when no image is loaded */
.watermark-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  color: #909399;
  text-align: center;
}

/* Styles for the upload dialog */
.upload-dialog-content {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.send_file_uploader {
  width: 100%;
}

.send_file_uploader .el-upload-dragger {
  width: 100%;
  padding: 30px;
}
</style>