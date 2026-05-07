<template>
  <div class="watermark-extraction-container">
    <el-alert :title="$t('rasterWmExtract.currentRole')" type="info" :closable="false" style="margin-bottom: 12px;" />
    <!-- 页面标题区域 -->
    <div class="page-header">
      <div class="header-icon">
        <el-icon size="32" color="#409EFF"><Document /></el-icon>
      </div>
      <div class="header-content">
        <h2>{{ $t('rasterWmExtract.pageTitle') }}</h2>
        <p class="description">
          {{ $t('rasterWmExtract.pageDescription') }}
        </p>
      </div>
    </div>

    <!-- 操作步骤指示器 -->
    <div class="step-indicator">
      <div class="step-item" :class="{ active: currentStep >= 1, completed: currentStep > 1 }">
        <div class="step-number">1</div>
        <div class="step-text">{{ $t('rasterWmExtract.step1') }}</div>
      </div>
      <div class="step-line" :class="{ active: currentStep >= 2 }"></div>
      <div class="step-item" :class="{ active: currentStep >= 2, completed: currentStep > 2 }">
        <div class="step-number">2</div>
        <div class="step-text">{{ $t('rasterWmExtract.step2') }}</div>
      </div>
      <div class="step-line" :class="{ active: currentStep >= 3 }"></div>
      <div class="step-item" :class="{ active: currentStep >= 3 }">
        <div class="step-number">3</div>
        <div class="step-text">{{ $t('rasterWmExtract.step3') }}</div>
      </div>
    </div>

    <!-- 输入和操作区域 -->
    <div class="input-and-upload-section">
      <!-- 输入原始数据编号 -->
      <div class="input-section">
        <div class="section-title">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ $t('rasterWmExtract.originalDataId') }}</span>
        </div>
        <el-input
          v-model="dataIdInput"
          :placeholder="$t('rasterWmExtract.dataIdPlaceholder')"
          class="data-id-input"
          size="large"
          clearable
          @input="onDataIdChange"
        >
          <template #prefix>
            <el-icon><Key /></el-icon>
          </template>
        </el-input>
        <div class="input-tip">{{ $t('rasterWmExtract.dataIdTip') }}</div>
      </div>

      <!-- 文件上传区域 -->
      <div class="upload-section">
        <div class="section-title">
          <el-icon><Upload /></el-icon>
          <span>{{ $t('rasterWmExtract.uploadRasterFile') }}</span>
        </div>
        <el-upload
          class="upload-area"
          drag
          :action="uploadUrl"
          :multiple="false"
          accept=".zip,.tif,.tiff"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :data="uploadData"
          :disabled="!dataIdInput"
        >
          <div class="upload-content">
            <el-icon class="upload-icon" size="48"><UploadFilled /></el-icon>
            <div class="upload-text">
              <div class="main-text">{{ $t('rasterWmExtract.dragOrClick') }} <em>{{ $t('rasterWmExtract.clickToUpload') }}</em></div>
              <div class="sub-text">{{ $t('rasterWmExtract.supportedFormats') }}</div>
            </div>
          </div>
        </el-upload>
      </div>
    </div>

    <!-- 水印比对结果展示区 -->
    <el-card v-if="comparisonResult.isReady" class="comparison-card">
      <template #header>
        <div class="card-header">
          <el-icon><Check /></el-icon>
          <span>{{ $t('rasterWmExtract.comparisonResult') }}</span>
          <el-tag :type="comparisonResult.isMatch ? 'success' : 'danger'" size="small">
            {{ comparisonResult.isMatch ? $t('rasterWmExtract.verifyPass') : $t('rasterWmExtract.verifyFail') }}
          </el-tag>
        </div>
      </template>

      <div class="watermark-comparison-area">
        <div class="watermark-item">
          <div class="watermark-header">
            <el-icon><Document /></el-icon>
            <span>{{ $t('rasterWmExtract.originalWatermark') }}</span>
          </div>
          <div class="watermark-content">
            <el-image
              :src="`data:image/png;base64,${originalWatermarkBase64}`"
              fit="contain"
              class="watermark-image"
            >
              <template #error>
                <div class="image-error">
                  <el-icon size="32"><Picture /></el-icon>
                  <span>{{ $t('rasterWmExtract.watermarkLoadFailed') }}</span>
                </div>
              </template>
            </el-image>
          </div>
        </div>

        <div class="comparison-info">
          <div class="nc-value-display">
            <div class="nc-label">{{ $t('rasterWmExtract.ncLabel') }}</div>
            <div class="nc-value" :class="{ high: comparisonResult.ncValue >= 0.95, medium: comparisonResult.ncValue >= 0.8, low: comparisonResult.ncValue < 0.8 }">
              {{ comparisonResult.ncValue?.toFixed(4) || '0.0000' }}
            </div>
          </div>
          <div class="similarity-indicator">
            <el-progress
              :percentage="Math.round((comparisonResult.ncValue || 0) * 100)"
              :status="comparisonResult.isMatch ? 'success' : 'exception'"
              :stroke-width="8"
              :show-text="false"
            />
            <span class="similarity-text">{{ $t('rasterWmExtract.similarity') }}</span>
          </div>
        </div>

        <div class="watermark-item">
          <div class="watermark-header">
            <el-icon><Search /></el-icon>
            <span>{{ $t('rasterWmExtract.extractedWatermark') }}</span>
          </div>
          <div class="watermark-content">
            <el-image
              :src="`data:image/png;base64,${extractedWatermarkBase64}`"
              fit="contain"
              class="watermark-image"
            >
              <template #error>
                <div class="image-error">
                  <el-icon size="32"><Picture /></el-icon>
                  <span>{{ $t('rasterWmExtract.watermarkLoadFailed') }}</span>
                </div>
              </template>
            </el-image>
          </div>
        </div>
      </div>

      <div class="result-message" :class="{ success: comparisonResult.isMatch, danger: !comparisonResult.isMatch }">
        <el-icon size="20">
          <Check v-if="comparisonResult.isMatch" />
          <Warning v-else />
        </el-icon>
        <div class="result-text">
          <div class="result-title">{{ comparisonResult.isMatch ? $t('rasterWmExtract.verifyPass') : $t('rasterWmExtract.verifyFail') }}</div>
          <div class="result-desc">
            {{ comparisonResult.isMatch ? $t('rasterWmExtract.matchSuccess') : $t('rasterWmExtract.matchFail') }}
          </div>
        </div>
      </div>
    </el-card>

    <el-card v-if="decodedInfo" class="comparison-card" style="margin-top: 16px;">
      <template #header>
        <div class="card-header">
          <el-icon><Search /></el-icon>
          <span>{{ $t('rasterWmExtract.onlineDecodeInfo') }}</span>
        </div>
      </template>
      <el-alert
        :title="decodedInfo.verify?.message || $t('rasterWmExtract.qrVerifyUnavailable')"
        :type="decodedInfo.verify?.digest_ok === false || decodedInfo.verify?.signature_ok === false ? 'error' : 'success'"
        :closable="false"
        style="margin-bottom: 10px;"
      />
      <el-descriptions :column="2" border>
        <el-descriptions-item :label="$t('rasterWmExtract.applicationId')">{{ decodedInfo.normalized?.id || decodedInfo.parsed?.id || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.applicationNumber')">{{ decodedInfo.normalized?.application_number || decodedInfo.parsed?.application_number || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.applicationStatus')">{{ decodedInfo.normalized?.application_status || decodedInfo.parsed?.application_status || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.dataType')">{{ decodedInfo.normalized?.data_type || decodedInfo.parsed?.data_type || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.applicant')">{{ decodedInfo.normalized?.applicant || decodedInfo.parsed?.applicant || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.applicantId')">{{ decodedInfo.normalized?.applicant_id || decodedInfo.parsed?.applicant_id || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.approver1')">{{ decodedInfo.normalized?.approver_1 || decodedInfo.parsed?.approver_1 || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.approver2')">{{ decodedInfo.normalized?.approver_2 || decodedInfo.parsed?.approver_2 || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.submittedAt')">{{ decodedInfo.normalized?.submitted_at || decodedInfo.parsed?.submitted_at || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.generatedAt')">{{ decodedInfo.normalized?.generated_at || decodedInfo.parsed?.generated_at || '-' }}</el-descriptions-item>
        <el-descriptions-item :label="$t('rasterWmExtract.reason')" :span="2">{{ decodedInfo.normalized?.reason || decodedInfo.parsed?.reason || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref, watch, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import {
  Document,
  UploadFilled,
  Check,
  Warning,
  InfoFilled,
  Key,
  Upload,
  Search,
  Picture
} from '@element-plus/icons-vue';

const { t } = useI18n();

// 数据状态
const dataIdInput = ref('');
const extractedWatermarkBase64 = ref('');
const originalWatermarkBase64 = ref('');
const decodedInfo = ref(null);
const comparisonResult = reactive({
  isReady: false,
  isMatch: false,
  ncValue: null,
});

// 当前步骤
const currentStep = computed(() => {
  if (comparisonResult.isReady) return 3;
  if (dataIdInput.value) return 2;
  return 1;
});

// 上传URL：统一提取接口（支持矢量/栅格并在线解码）
const uploadUrl = `/api/vector/extract`;

// 上传时附带的数据（后端要求 application_id）
const uploadData = reactive({
  application_id: dataIdInput,
});

// 监听输入框变化，更新上传数据
watch(dataIdInput, (newValue) => {
  uploadData.application_id = newValue;
});

// 数据编号变化处理
const onDataIdChange = () => {
  comparisonResult.isReady = false;
};

// 上传文件前的检查
const beforeUpload = (file) => {
  if (!dataIdInput.value) {
    ElMessage.error(t('rasterWmExtract.errorDataIdRequired'));
    return false;
  }
  const isZipOrTif = file.name.toLowerCase().endsWith('.zip') ||
                     file.name.toLowerCase().endsWith('.tif') ||
                     file.name.toLowerCase().endsWith('.tiff');
  if (!isZipOrTif) {
    ElMessage.error(t('rasterWmExtract.errorFileFormat'));
    return false;
  }
  return true;
};

/**
 * 文件上传成功后的展示
 * 小白解释：后端会返回水印的 Base64 图片，我们直接展示出来。
 */
const handleUploadSuccess = (response, file) => {
  // 统一兼容字段名：watermark_base64 / extracted_watermark_base64 / base64
  const extracted = response?.watermark_base64 || response?.extracted_watermark_base64 || response?.base64;
  if (extracted) {
    ElMessage.success(t('rasterWmExtract.uploadSuccessExtracted', { name: file.name }));
    extractedWatermarkBase64.value = extracted;
    // 若后端暂不返回原始水印与 NC 值，则只展示提取结果
    originalWatermarkBase64.value = response?.original_watermark_base64 || '';
    comparisonResult.ncValue = typeof response?.nc_value === 'number' ? response.nc_value : null;
    comparisonResult.isReady = true;
    comparisonResult.isMatch = comparisonResult.ncValue ? comparisonResult.ncValue > 0.95 : true;

    const decoded = response?.data?.decoded_info;
    decodedInfo.value = decoded || null;
    if (decoded?.content) {
      ElMessage.success(t('rasterWmExtract.qrDecodedOnline'));
    }
  } else {
    ElMessage.error(response?.msg || t('rasterWmExtract.uploadSuccessNoWatermark', { name: file.name }));
    comparisonResult.isReady = false;
  }
};

// 文件上传失败处理
const handleUploadError = (err, file) => {
  ElMessage.error(t('rasterWmExtract.uploadFailed', { name: file.name }));
  console.error("Error during file upload:", err);
  comparisonResult.isReady = false;
};
</script>

<style scoped>
.watermark-extraction-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: calc(100vh - 120px);
  border-radius: 12px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #409EFF 0%, #67C23A 100%);
  border-radius: 12px;
  color: white;
}

.header-content h2 {
  margin: 0 0 8px 0;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.header-content .description {
  margin: 0;
  color: #606266;
  font-size: 14px;
  line-height: 1.5;
}

.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  padding: 24px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 120px;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e4e7ed;
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  transition: all 0.3s ease;
}

.step-item.active .step-number {
  background: #409EFF;
  color: white;
}

.step-item.completed .step-number {
  background: #67C23A;
  color: white;
}

.step-text {
  font-size: 14px;
  color: #909399;
  transition: color 0.3s ease;
}

.step-item.active .step-text {
  color: #409EFF;
  font-weight: 500;
}

.step-item.completed .step-text {
  color: #67C23A;
}

.step-line {
  flex: 1;
  height: 2px;
  background: #e4e7ed;
  margin: 0 16px;
  position: relative;
  top: 16px;
  transition: background 0.3s ease;
}

.step-line.active {
  background: #409EFF;
}

.input-and-upload-section {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 32px;
  margin-bottom: 32px;
}

.input-section,
.upload-section {
  background: white;
  padding: 24px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.data-id-input {
  margin-bottom: 8px;
}

.input-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.upload-area {
  width: 100%;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 32px 16px;
}

.upload-icon {
  color: #409EFF;
  opacity: 0.8;
}

.upload-text {
  text-align: center;
}

.main-text {
  font-size: 16px;
  color: #606266;
  margin-bottom: 8px;
}

.main-text em {
  color: #409EFF;
  font-style: normal;
  font-weight: 500;
}

.sub-text {
  font-size: 12px;
  color: #909399;
}

.comparison-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  border: none;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.watermark-comparison-area {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 32px;
  align-items: center;
  padding: 24px 0;
}

.watermark-item {
  text-align: center;
}

.watermark-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
  font-weight: 500;
  color: #303133;
}

.watermark-content {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.watermark-image {
  max-width: 100%;
  max-height: 200px;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 14px;
}

.comparison-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  padding: 24px;
  background: #f5f7fa;
  border-radius: 8px;
  min-width: 200px;
}

.nc-value-display {
  text-align: center;
}

.nc-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.nc-value {
  font-size: 28px;
  font-weight: bold;
  font-family: 'Courier New', monospace;
}

.nc-value.high {
  color: #67C23A;
}

.nc-value.medium {
  color: #E6A23C;
}

.nc-value.low {
  color: #F56C6C;
}

.similarity-indicator {
  width: 100%;
  text-align: center;
}

.similarity-text {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.result-message {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 8px;
  margin-top: 24px;
}

.result-message.success {
  background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%);
  border: 1px solid #d9f0c8;
}

.result-message.danger {
  background: linear-gradient(135deg, #fef0f0 0%, #fde2e2 100%);
  border: 1px solid #fcd3d3;
}

.result-text {
  flex: 1;
}

.result-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.result-message.success .result-title {
  color: #67C23A;
}

.result-message.danger .result-title {
  color: #F56C6C;
}

.result-desc {
  font-size: 14px;
  color: #606266;
  line-height: 1.5;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .input-and-upload-section {
    grid-template-columns: 1fr;
  }

  .watermark-comparison-area {
    grid-template-columns: 1fr;
    gap: 24px;
  }

  .comparison-info {
    order: -1;
    min-width: auto;
  }

  .step-indicator {
    flex-direction: column;
    gap: 16px;
  }

  .step-line {
    width: 2px;
    height: 20px;
    margin: 0;
    top: 0;
  }
}
</style>