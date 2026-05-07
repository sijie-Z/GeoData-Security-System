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

    <el-card v-if="decodedInfo" class="decode-card" shadow="never" style="margin-top: 16px;">
      <template #header>
        <div class="card-header"><span>在线解码信息</span></div>
      </template>
      <el-alert
        :title="decodedInfo.verify?.message || '二维码校验信息不可用'"
        :type="decodedInfo.verify?.digest_ok === false || decodedInfo.verify?.signature_ok === false ? 'error' : 'success'"
        :closable="false"
        style="margin-bottom: 10px;"
      />
      <el-descriptions :column="2" border>
        <el-descriptions-item label="申请编号">{{ decodedInfo.normalized?.id || decodedInfo.parsed?.id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请流水号">{{ decodedInfo.normalized?.application_number || decodedInfo.parsed?.application_number || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请状态">{{ decodedInfo.normalized?.application_status || decodedInfo.parsed?.application_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="数据类型">{{ decodedInfo.normalized?.data_type || decodedInfo.parsed?.data_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请人">{{ decodedInfo.normalized?.applicant || decodedInfo.parsed?.applicant || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请人编号">{{ decodedInfo.normalized?.applicant_id || decodedInfo.parsed?.applicant_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="一审管理员">{{ decodedInfo.normalized?.approver_1 || decodedInfo.parsed?.approver_1 || '-' }}</el-descriptions-item>
        <el-descriptions-item label="二审管理员">{{ decodedInfo.normalized?.approver_2 || decodedInfo.parsed?.approver_2 || '-' }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ decodedInfo.normalized?.submitted_at || decodedInfo.parsed?.submitted_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="二维码生成时间">{{ decodedInfo.normalized?.generated_at || decodedInfo.parsed?.generated_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请原因" :span="2">{{ decodedInfo.normalized?.reason || decodedInfo.parsed?.reason || '-' }}</el-descriptions-item>
      </el-descriptions>
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
              支持 .zip（矢量）与 .png/.jpg/.tif（栅格）格式文件。
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
import axios from "@/utils/Axios";
import { ElMessage, ElMessageBox } from "element-plus";

// State and refs
const ExtractVisible = ref(false);
const GetIdInput = ref('');
const extractedWatermarkBase64 = ref('');
const decodedInfo = ref(null);

// API URL from environment variables
const uploadUrl = `/api/vector/extract`;

// Data for file upload
const uploadData = ref({
  application_id: GetIdInput.value
});

// Watch for changes in the input field to update the upload data
watch(GetIdInput, (newValue) => {
  uploadData.value = {
    application_id: newValue
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

  const extracted = response?.watermark_base64 || response?.extracted_watermark_base64 || response?.base64;
  if (extracted) {
    extractedWatermarkBase64.value = extracted;
    decodedInfo.value = response?.data?.decoded_info || null;
    if (decodedInfo.value) {
      ElMessage.success('二维码已在线解码');
    }
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

  const allowedExtensions = ['.zip', '.png', '.jpg', '.jpeg', '.tif', '.tiff'];
  const fileName = file.name.toLowerCase();
  const isAllowed = allowedExtensions.some(ext => fileName.endsWith(ext));

  if (!isAllowed) {
    ElMessage.error('仅支持 .zip, .png, .jpg, .tif 等格式文件');
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
  decodedInfo.value = null;
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