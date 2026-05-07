<template>
    <div class="data-upload-container">
      <!-- 1. 页面标题和引导区 -->
      <div class="page-header">
        <h1 class="page-title">{{ $t('adminDataUpload.title') }}</h1>
        <p class="page-description">
          {{ $t('adminDataUpload.description') }}
        </p>
      </div>

      <!-- 2. 主操作区：表单和上传控件 -->
      <el-card class="upload-main-card">
        <el-form
          ref="uploadFormRef"
          :model="form"
          :rules="rules"
          label-width="120px"
          label-position="top"
          class="upload-form"
          size="large"
        >
          <el-row :gutter="40">
            <el-col :span="12">
              <el-form-item :label="$t('adminDataUpload.dataName')" prop="data_alias">
                <el-input
                  v-model="form.data_alias"
                  :placeholder="$t('adminDataUpload.dataNameExample')"
                  clearable
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
               <el-form-item :label="$t('adminDataUpload.category')" prop="category">
                  <el-select v-model="form.category" :placeholder="$t('adminDataUpload.selectCategory')" filterable allow-create>
                    <el-option :label="$t('adminDataUpload.categoryAdmin')" value="行政区划"></el-option>
                    <el-option :label="$t('adminDataUpload.categoryWater')" value="水系"></el-option>
                    <el-option :label="$t('adminDataUpload.categoryTraffic')" value="交通网络"></el-option>
                    <el-option :label="$t('adminDataUpload.categoryPOI')" value="兴趣点 (POI)"></el-option>
                  </el-select>
                </el-form-item>
            </el-col>
          </el-row>

          <el-form-item :label="$t('adminDataUpload.dataIntro')" prop="data_introduction">
            <el-input
              v-model="form.data_introduction"
              type="textarea"
              :rows="4"
              :placeholder="$t('adminDataUpload.dataIntroPlaceholder')"
              show-word-limit
              maxlength="500"
            />
          </el-form-item>

          <el-form-item :label="$t('adminDataUpload.uploadSHP')" prop="file">
            <!-- el-upload 组件现在只用于选择文件，不进行实际上传 -->
            <el-upload
              ref="uploadRef"
              class="upload-dragger-wrapper"
              drag
              action="#"
              :limit="1"
              :auto-upload="false"
              :http-request="() => {}"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :on-exceed="handleExceed"
              accept=".zip"
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                {{ $t('adminDataUpload.dragHere') }}<em>{{ $t('adminDataUpload.clickUpload') }}</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  {{ $t('adminDataUpload.zipOnly') }}
                </div>
              </template>
            </el-upload>
          </el-form-item>

          <!-- 上传进度条 -->
          <el-progress
              v-if="uploadPercentage > 0"
              :percentage="uploadPercentage"
              :stroke-width="10"
              :text-inside="true"
              status="success"
              class="upload-progress"
            />

          <!-- 3. 操作按钮区 -->
          <el-form-item class="form-actions">
            <el-button
              type="primary"
              size="large"
              :icon="Upload"
              @click="submitUpload"
              :loading="isUploading"
              :disabled="!form.file"
            >
              {{ isUploading ? $t('adminDataUpload.uploading') : $t('adminDataUpload.uploadNow') }}
            </el-button>
            <el-button size="large" @click="resetForm">{{ $t('adminDataUpload.resetAll') }}</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </template>

<script setup>
import { ref, reactive, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { Upload, UploadFilled } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import axios from '@/utils/Axios';

const { t } = useI18n()

const uploadFormRef = ref(null);
const uploadRef = ref(null);

// --- 状态管理 ---
const isUploading = ref(false);
const uploadPercentage = ref(0);

// --- 表单数据与规则 ---
const initialForm = {
  data_alias: '',
  category: '',
  data_introduction: '',
  file: null,
};
const form = reactive({ ...initialForm });

const rules = reactive({
  data_alias: [{ required: true, message: () => t('adminDataUpload.enterDataName'), trigger: 'blur' }],
  data_introduction: [{ required: true, message: () => t('adminDataUpload.introRequired'), trigger: 'blur' }],
  file: [{ required: true, message: () => t('adminDataUpload.selectZip'), trigger: 'change' }],
});

// --- 事件处理函数 ---
const handleFileChange = (uploadFile) => {
  const isZip = uploadFile.name.endsWith('.zip');
  const isLt500M = uploadFile.size / 1024 / 1024 < 500;

  if (!isZip) {
    ElMessage.error(t('adminDataUpload.zipOnlyError'));
    uploadRef.value?.clearFiles();
    form.file = null;
    return;
  }
  if (!isLt500M) {
    ElMessage.error(t('adminDataUpload.fileSizeError'));
    uploadRef.value?.clearFiles();
    form.file = null;
    return;
  }

  uploadPercentage.value = 0;
  form.file = uploadFile;
  uploadFormRef.value?.validateField('file');
};

const handleFileRemove = () => {
  form.file = null;
  uploadPercentage.value = 0;
  uploadFormRef.value?.validateField('file');
};

const handleExceed = () => {
  ElMessage.warning(t('adminDataUpload.singleFileOnly'));
};

const submitUpload = async () => {
  if (!uploadFormRef.value) return;

  await uploadFormRef.value.validate(async (valid) => {
    if (!valid) {
      ElMessage.error(t('adminDataUpload.formIncomplete'));
      return;
    }

    isUploading.value = true;
    uploadPercentage.value = 0;

    const formData = new FormData();
    formData.append('file', form.file.raw);
    formData.append('data_alias', form.data_alias);
    formData.append('category', form.category);
    formData.append('data_introduction', form.data_introduction);

    try {
      await axios.post('/api/upload_shp_data', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            uploadPercentage.value = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          }
        }
      });

      uploadPercentage.value = 100;
      ElMessage.success(t('adminDataUpload.uploadSuccess'));
      setTimeout(resetForm, 1000);
    } catch (error) {
      const msg = error.response?.data?.msg || t('adminDataUpload.uploadFailed');
      ElMessage.error(msg);
    } finally {
      isUploading.value = false;
    }
  });
};

const resetForm = () => {
  isUploading.value = false;
  uploadPercentage.value = 0;
  Object.assign(form, initialForm);
  uploadRef.value?.clearFiles();
  nextTick(() => {
    uploadFormRef.value?.resetFields();
  });
};
</script>

<style scoped>
.data-upload-container {
  padding: 24px 40px;
  background-color: #f7f8fa;
  min-height: calc(100vh - 50px);
}
.page-header {
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1d2129;
  margin: 0 0 8px 0;
}
.page-description {
  font-size: 14px;
  color: #86909c;
  margin: 0;
}
.upload-main-card {
  border-radius: 8px;
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}
.upload-form {
  padding: 20px;
}
.upload-form .el-form-item {
  margin-bottom: 24px;
}
.upload-form .el-form-item__label {
  font-size: 14px;
  font-weight: 500;
  color: #4e5969;
}
.upload-dragger-wrapper :deep(.el-upload-dragger) {
  padding: 40px;
  border-radius: 8px;
  border: 2px dashed #dcdfe6;
  transition: border-color 0.3s;
}
.upload-dragger-wrapper :deep(.el-upload-dragger:hover) {
  border-color: var(--el-color-primary);
}
.el-icon--upload {
  font-size: 50px;
  color: #c0c4cc;
  margin-bottom: 16px;
}
.el-upload__text {
  color: #606266;
  font-size: 14px;
}
.el-upload__text em {
  color: var(--el-color-primary);
  font-style: normal;
}
.el-upload__tip {
  color: #909399;
  font-size: 13px;
  margin-top: 10px;
  text-align: center;
}
.upload-progress {
  margin-top: -10px;
  margin-bottom: 20px;
}
.form-actions {
  margin-top: 32px;
  margin-bottom: 0 !important;
  display: flex;
  justify-content: flex-start;
}
.el-select{
    width: 100%;
}
</style>
