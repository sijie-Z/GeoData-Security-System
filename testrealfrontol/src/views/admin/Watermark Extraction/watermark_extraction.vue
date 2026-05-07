<template>
  <div class="watermark-extraction-container">
    <div class="input-section">
      <el-input v-model="GetIdInput" style="width: 250px" :placeholder="$t('wmExtract.inputPlaceholder')" clearable/>
      <el-button size="default" type="primary" @click="click_extract">{{ $t('wmExtract.selectAndExtract') }}</el-button>
    </div>

    <el-card class="watermark-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>{{ $t('wmExtract.extractedWatermarkTitle') }}</span>
        </div>
      </template>
      <div v-if="extractedWatermarkBase64" class="watermark-image-wrapper">
        <img :src="`data:image/png;base64,${extractedWatermarkBase64}`" alt="Extracted Watermark" class="watermark-image"/>
      </div>
      <div v-else class="watermark-placeholder">
        <el-empty :description="$t('wmExtract.watermarkPlaceholder')"></el-empty>
      </div>
    </el-card>

    <el-card v-if="decodedInfo" class="decode-card" shadow="never" style="margin-top: 16px;">
      <template #header>
        <div class="card-header"><span>{{ $t('wmExtract.decodeInfoTitle') }}</span></div>
      </template>
      <el-alert
        :title="decodedInfo.verify?.message || $t('wmExtract.verifyUnavailable')"
        :type="decodedInfo.verify?.digest_ok === false || decodedInfo.verify?.signature_ok === false ? 'error' : 'success'"
        :closable="false"
        style="margin-bottom: 10px;"
      />
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="$t('wmExtract.descApplicationId')">{{ decodedInfo.normalized?.id || decodedInfo.parsed?.id || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descApplicationNumber')">{{ decodedInfo.normalized?.application_number || decodedInfo.parsed?.application_number || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descApplicationStatus')">{{ decodedInfo.normalized?.application_status || decodedInfo.parsed?.application_status || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descDataType')">{{ decodedInfo.normalized?.data_type || decodedInfo.parsed?.data_type || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descApplicant')">{{ decodedInfo.normalized?.applicant || decodedInfo.parsed?.applicant || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descApplicantId')">{{ decodedInfo.normalized?.applicant_id || decodedInfo.parsed?.applicant_id || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descApprover1')">{{ decodedInfo.normalized?.approver_1 || decodedInfo.parsed?.approver_1 || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descApprover2')">{{ decodedInfo.normalized?.approver_2 || decodedInfo.parsed?.approver_2 || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descSubmittedAt')">{{ decodedInfo.normalized?.submitted_at || decodedInfo.parsed?.submitted_at || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descGeneratedAt')">{{ decodedInfo.normalized?.generated_at || decodedInfo.parsed?.generated_at || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('wmExtract.descReason')" :span="2">{{ decodedInfo.normalized?.reason || decodedInfo.parsed?.reason || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-dialog :title="$t('wmExtract.uploadDialogTitle')" v-model="ExtractVisible" width="50%" :before-close="(done) => handleClose('send', done)">
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
            {{ $t('wmExtract.uploadText') }} <em>{{ $t('wmExtract.uploadClick') }}</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              {{ $t('wmExtract.uploadTip') }}
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
import { useI18n } from 'vue-i18n';
import axios from "@/utils/Axios";
import { ElMessage, ElMessageBox } from "element-plus";

const { t } = useI18n();

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
    ElMessage.error(t('wmExtract.fillDataIdFirst'));
    return;
  }
  ExtractVisible.value = true;
};

const handleUploadSuccess = (response, file) => {
  ElMessage.success(t('wmExtract.uploadSuccess', { name: file.name }));
  ExtractVisible.value = false;

  const extracted = response?.watermark_base64 || response?.extracted_watermark_base64 || response?.base64;
  if (extracted) {
    extractedWatermarkBase64.value = extracted;
    decodedInfo.value = response?.data?.decoded_info || null;
    if (decodedInfo.value) {
      ElMessage.success(t('wmExtract.qrDecoded'));
    }
  } else {
    ElMessage.error(t('wmExtract.noWatermarkExtracted'));
  }
};

const handleUploadError = (err, file) => {
  let errorMessage = t('wmExtract.uploadFailed', { name: file.name });
  if (err.response && err.response.data && err.response.data.error) {
    errorMessage += ` ${t('wmExtract.errorInfo')}: ${err.response.data.error}`;
  }
  ElMessage.error(errorMessage);
  console.error("Error during file upload:", err);
};

const beforeUpload = (file) => {
  if (!GetIdInput.value) {
    ElMessage.error(t('wmExtract.fillDataIdFirst'));
    return false;
  }

  const allowedExtensions = ['.zip', '.png', '.jpg', '.jpeg', '.tif', '.tiff'];
  const fileName = file.name.toLowerCase();
  const isAllowed = allowedExtensions.some(ext => fileName.endsWith(ext));

  if (!isAllowed) {
    ElMessage.error(t('wmExtract.unsupportedFormat'));
    return false;
  }

  return true;
};

const handleClose = (dialogType, done) => {
  ElMessageBox.confirm(t('wmExtract.confirmClose')).then(() => {
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
