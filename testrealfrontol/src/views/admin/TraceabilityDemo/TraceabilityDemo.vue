<template>
  <div class="trace-container">
    <!-- Page header -->
    <div class="page-header">
      <h2>{{ $t('trace.title') }}</h2>
      <p class="subtitle">{{ $t('trace.subtitle') }}</p>
    </div>

    <!-- Steps -->
    <el-steps :active="currentStep" finish-status="success" align-center class="steps-bar">
      <el-step :title="$t('trace.step1Title')" :description="$t('trace.step1Desc')" />
      <el-step :title="$t('trace.step2Title')" :description="$t('trace.step2Desc')" />
      <el-step :title="$t('trace.step3Title')" :description="$t('trace.step3Desc')" />
    </el-steps>

    <!-- Step 1: Enter application ID -->
    <el-card v-show="currentStep === 0" class="step-card" shadow="hover">
      <div class="step-content">
        <el-icon class="step-icon"><Search /></el-icon>
        <h3>{{ $t('trace.enterAppId') }}</h3>
        <el-input
          v-model="applicationId"
          :placeholder="$t('trace.appIdPlaceholder')"
          size="large"
          clearable
          style="max-width: 400px;"
          @keyup.enter="goToStep2"
        />
        <div class="step-actions">
          <el-button type="primary" size="large" :disabled="!applicationId" @click="goToStep2">
            {{ $t('trace.next') }}
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- Step 2: Upload file -->
    <el-card v-show="currentStep === 1" class="step-card" shadow="hover">
      <div class="step-content">
        <el-icon class="step-icon"><UploadFilled /></el-icon>
        <h3>{{ $t('trace.uploadTitle') }}</h3>
        <p class="upload-hint">{{ $t('trace.uploadHint') }}</p>
        <el-upload
          ref="uploadRef"
          class="trace-uploader"
          drag
          :action="uploadUrl"
          :data="uploadData"
          :limit="1"
          accept=".zip,.png,.jpg,.jpeg,.tif,.tiff"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :auto-upload="false"
          :on-change="onFileChange"
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            {{ $t('trace.dragOrClick') }} <em>{{ $t('trace.clickToUpload') }}</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">{{ $t('trace.formatTip') }}</div>
          </template>
        </el-upload>
        <div class="step-actions">
          <el-button size="large" @click="currentStep = 0">{{ $t('trace.prev') }}</el-button>
          <el-button type="primary" size="large" :loading="extracting" :disabled="!selectedFile" @click="doExtract">
            {{ $t('trace.extractBtn') }}
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- Step 3: Results -->
    <el-card v-show="currentStep === 2" class="step-card" shadow="hover">
      <div class="step-content results-content">
        <!-- Loading overlay -->
        <div v-if="extracting" class="extracting-overlay">
          <el-icon class="spin-icon" :size="48"><Loading /></el-icon>
          <p>{{ $t('trace.extracting') }}</p>
        </div>

        <!-- Error state -->
        <el-alert
          v-if="errorMsg"
          :title="errorMsg"
          type="error"
          show-icon
          :closable="false"
          style="margin-bottom: 20px;"
        />

        <!-- Success: Provenance card -->
        <template v-if="resultData">
          <!-- Verification status banner -->
          <div class="verify-banner" :class="verifyPassed ? 'verify-pass' : 'verify-fail'">
            <el-icon :size="32"><CircleCheckFilled v-if="verifyPassed" /><CircleCloseFilled v-else /></el-icon>
            <div>
              <h3>{{ verifyPassed ? $t('trace.verifyPass') : $t('trace.verifyFail') }}</h3>
              <p v-if="verifyPassed">{{ $t('trace.verifyPassDesc') }}</p>
              <p v-else>{{ $t('trace.verifyFailDesc') }}</p>
            </div>
          </div>

          <!-- Two-column layout: watermark image + provenance info -->
          <div class="result-columns">
            <!-- Left: Extracted watermark -->
            <div class="watermark-panel">
              <h4>{{ $t('trace.extractedWatermark') }}</h4>
              <div class="watermark-img-box">
                <img
                  v-if="watermarkBase64"
                  :src="`data:image/png;base64,${watermarkBase64}`"
                  alt="Extracted Watermark"
                />
                <el-empty v-else :description="$t('trace.noWatermark')" />
              </div>
              <!-- Recovered image (raster only) -->
              <template v-if="recoveredBase64">
                <h4 style="margin-top: 16px;">{{ $t('trace.recoveredImage') }}</h4>
                <div class="watermark-img-box">
                  <img :src="`data:image/png;base64,${recoveredBase64}`" alt="Recovered" />
                </div>
              </template>
            </div>

            <!-- Right: Provenance card -->
            <div class="provenance-panel">
              <h4>{{ $t('trace.provenanceTitle') }}</h4>

              <!-- NC value -->
              <div v-if="decodedInfo?.verify?.nc_value != null" class="nc-badge">
                <span class="nc-label">{{ $t('trace.ncValue') }}</span>
                <el-progress
                  :percentage="Math.round((decodedInfo.verify.nc_value || 0) * 100)"
                  :color="ncColor"
                  :stroke-width="20"
                  :text-inside="true"
                />
              </div>

              <el-descriptions :column="1" border class="provenance-desc">
                <el-descriptions-item :label="$t('trace.appId')">
                  {{ normalized.id || parsed.id || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.appNumber')">
                  {{ normalized.application_number || parsed.application_number || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.appStatus')">
                  <el-tag :type="statusTagType">{{ normalized.application_status || parsed.application_status || '-' }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.dataType')">
                  {{ normalized.data_type || parsed.data_type || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.applicant')">
                  <strong>{{ normalized.applicant || parsed.applicant || '-' }}</strong>
                  <span v-if="normalized.applicant_id || parsed.applicant_id"> ({{ normalized.applicant_id || parsed.applicant_id }})</span>
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.approver1')">
                  {{ normalized.approver_1 || parsed.approver_1 || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.approver2')">
                  {{ normalized.approver_2 || parsed.approver_2 || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.submittedAt')">
                  {{ normalized.submitted_at || parsed.submitted_at || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.generatedAt')">
                  {{ normalized.generated_at || parsed.generated_at || '-' }}
                </el-descriptions-item>
                <el-descriptions-item :label="$t('trace.reason')">
                  {{ normalized.reason || parsed.reason || '-' }}
                </el-descriptions-item>
              </el-descriptions>

              <!-- Signature verification -->
              <div class="sig-verify">
                <el-tag :type="signatureOk ? 'success' : 'danger'" effect="dark" size="large">
                  <el-icon style="margin-right: 4px;"><Lock /></el-icon>
                  {{ signatureOk ? $t('trace.sigValid') : $t('trace.sigInvalid') }}
                </el-tag>
                <el-tag :type="digestOk ? 'success' : 'danger'" effect="dark" size="large" style="margin-left: 8px;">
                  <el-icon style="margin-right: 4px;"><Key /></el-icon>
                  {{ digestOk ? $t('trace.digestValid') : $t('trace.digestInvalid') }}
                </el-tag>
              </div>
            </div>
          </div>
        </template>

        <!-- Actions -->
        <div class="step-actions" style="margin-top: 24px;">
          <el-button size="large" @click="resetAll">{{ $t('trace.reset') }}</el-button>
          <el-button type="primary" size="large" @click="currentStep = 1">{{ $t('trace.reUpload') }}</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  Search, UploadFilled, Loading,
  CircleCheckFilled, CircleCloseFilled, Lock, Key
} from '@element-plus/icons-vue'

const { t } = useI18n()

const currentStep = ref(0)
const applicationId = ref('')
const selectedFile = ref(null)
const extracting = ref(false)
const errorMsg = ref('')
const resultData = ref(null)
const uploadRef = ref(null)

const uploadUrl = '/api/vector/extract'
const uploadData = computed(() => ({ application_id: applicationId.value }))

// Parsed result fields
const watermarkBase64 = computed(() => resultData.value?.watermark_base64 || '')
const recoveredBase64 = computed(() => resultData.value?.recovered_base64 || '')
const decodedInfo = computed(() => resultData.value?.data?.decoded_info || null)
const normalized = computed(() => decodedInfo.value?.normalized || {})
const parsed = computed(() => decodedInfo.value?.parsed || {})
const verify = computed(() => decodedInfo.value?.verify || {})
const verifyPassed = computed(() => verify.value?.digest_ok !== false && verify.value?.signature_ok !== false)
const signatureOk = computed(() => verify.value?.signature_ok !== false)
const digestOk = computed(() => verify.value?.digest_ok !== false)

const ncColor = computed(() => {
  const nc = verify.value?.nc_value || 0
  if (nc >= 0.9) return '#67c23a'
  if (nc >= 0.7) return '#e6a23c'
  return '#f56c6c'
})

const statusTagType = computed(() => {
  const s = (normalized.value?.application_status || '').toLowerCase()
  if (s.includes('approved') || s.includes('通过')) return 'success'
  if (s.includes('rejected') || s.includes('驳回')) return 'danger'
  if (s.includes('recalled') || s.includes('回收')) return 'warning'
  return 'info'
})

const goToStep2 = () => {
  if (!applicationId.value) {
    ElMessage.warning(t('trace.appIdRequired'))
    return
  }
  currentStep.value = 1
}

const onFileChange = (file) => {
  selectedFile.value = file.raw
}

const beforeUpload = (file) => {
  const allowed = ['.zip', '.png', '.jpg', '.jpeg', '.tif', '.tiff']
  const name = file.name.toLowerCase()
  if (!allowed.some(ext => name.endsWith(ext))) {
    ElMessage.error(t('trace.unsupportedFormat'))
    return false
  }
  return true
}

const doExtract = () => {
  if (!selectedFile.value) {
    ElMessage.warning(t('trace.selectFileFirst'))
    return
  }
  extracting.value = true
  errorMsg.value = ''
  currentStep.value = 2

  const formData = new FormData()
  formData.append('application_id', applicationId.value)
  formData.append('file', selectedFile.value)

  fetch(uploadUrl, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
    },
    body: formData
  })
    .then(async (res) => {
      const json = await res.json()
      if (!res.ok || json.status === false) {
        throw new Error(json.error || json.message || t('trace.extractFailed'))
      }
      resultData.value = json
      ElMessage.success(t('trace.extractSuccess'))
    })
    .catch((err) => {
      errorMsg.value = err.message || t('trace.extractFailed')
      ElMessage.error(errorMsg.value)
    })
    .finally(() => {
      extracting.value = false
    })
}

const handleUploadSuccess = (response) => {
  extracting.value = false
  resultData.value = response
  ElMessage.success(t('trace.extractSuccess'))
}

const handleUploadError = (err) => {
  extracting.value = false
  errorMsg.value = err?.response?.data?.error || t('trace.extractFailed')
  ElMessage.error(errorMsg.value)
}

const resetAll = () => {
  currentStep.value = 0
  applicationId.value = ''
  selectedFile.value = null
  resultData.value = null
  errorMsg.value = ''
}
</script>

<style scoped>
.trace-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-header h2 {
  font-size: 24px;
  color: #303133;
  margin: 0 0 8px;
}

.subtitle {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.steps-bar {
  margin-bottom: 32px;
}

.step-card {
  border-radius: 12px;
}

.step-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 24px;
  text-align: center;
}

.step-icon {
  font-size: 48px;
  color: #409eff;
  margin-bottom: 16px;
}

.step-content h3 {
  font-size: 18px;
  color: #303133;
  margin: 0 0 16px;
}

.upload-hint {
  color: #909399;
  font-size: 13px;
  margin: 0 0 20px;
}

.trace-uploader {
  width: 100%;
  max-width: 500px;
}

.trace-uploader :deep(.el-upload-dragger) {
  padding: 40px;
}

.step-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

/* Results */
.results-content {
  align-items: stretch;
  text-align: left;
}

.extracting-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  gap: 16px;
}

.spin-icon {
  animation: spin 1.2s linear infinite;
  color: #409eff;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.verify-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-radius: 10px;
  margin-bottom: 24px;
}

.verify-banner h3 {
  margin: 0 0 4px;
  font-size: 18px;
}

.verify-banner p {
  margin: 0;
  font-size: 13px;
  opacity: 0.8;
}

.verify-pass {
  background: linear-gradient(135deg, #f0f9eb, #e1f3d8);
  border: 1px solid #b3e19d;
  color: #67c23a;
}

.verify-fail {
  background: linear-gradient(135deg, #fef0f0, #fde2e2);
  border: 1px solid #fbc4c4;
  color: #f56c6c;
}

.result-columns {
  display: flex;
  gap: 24px;
}

.watermark-panel {
  flex: 0 0 320px;
}

.watermark-panel h4,
.provenance-panel h4 {
  font-size: 15px;
  color: #303133;
  margin: 0 0 12px;
}

.watermark-img-box {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.watermark-img-box img {
  max-width: 100%;
  max-height: 280px;
  border-radius: 4px;
}

.provenance-panel {
  flex: 1;
  min-width: 0;
}

.nc-badge {
  margin-bottom: 16px;
}

.nc-label {
  font-size: 13px;
  color: #606266;
  display: block;
  margin-bottom: 4px;
}

.provenance-desc {
  margin-bottom: 16px;
}

.sig-verify {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

/* Responsive */
@media (max-width: 768px) {
  .result-columns {
    flex-direction: column;
  }

  .watermark-panel {
    flex: none;
  }
}
</style>
