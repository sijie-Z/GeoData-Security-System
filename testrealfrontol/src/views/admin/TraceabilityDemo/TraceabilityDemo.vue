<template>
  <div class="decode-platform">
    <div class="page-header">
      <h2>{{ $t('decodePlatform.title') }}</h2>
      <p class="subtitle">{{ $t('decodePlatform.subtitle') }}</p>
    </div>

    <el-tabs v-model="activeTab" type="border-card" class="platform-tabs">
      <!-- Tab 1: 直接解码 QR 码（主要） -->
      <el-tab-pane :label="$t('decodePlatform.qrDecodeTab')" name="qr">
        <div class="tab-content">
          <el-alert type="info" :closable="false" style="margin-bottom: 20px;">
            {{ $t('decodePlatform.qrDecodeHint') }}
          </el-alert>

          <el-row :gutter="24">
            <!-- 粘贴 QR 码文本 -->
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>
                  <span class="card-label">{{ $t('decodePlatform.pasteQRText') }}</span>
                </template>
                <el-input
                  v-model="qrText"
                  type="textarea"
                  :rows="10"
                  :placeholder="$t('decodePlatform.qrTextPlaceholder')"
                />
              </el-card>
            </el-col>

            <!-- 上传 QR 码图片 -->
            <el-col :span="12">
              <el-card shadow="hover">
                <template #header>
                  <span class="card-label">{{ $t('decodePlatform.uploadQRImage') }}</span>
                </template>
                <el-upload
                  ref="qrUploadRef"
                  class="qr-uploader"
                  drag
                  :limit="1"
                  accept=".png,.jpg,.jpeg,.bmp"
                  :auto-upload="false"
                  :on-change="onQRFileChange"
                  :on-remove="onQRFileRemove"
                >
                  <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                  <div class="el-upload__text">
                    {{ $t('decodePlatform.dragQRHere') }} <em>{{ $t('decodePlatform.clickToUpload') }}</em>
                  </div>
                  <template #tip>
                    <div class="el-upload__tip">{{ $t('decodePlatform.qrFormatTip') }}</div>
                  </template>
                </el-upload>
              </el-card>
            </el-col>
          </el-row>

          <div class="action-bar">
            <el-button type="primary" size="large" :loading="qrDecoding" :disabled="!qrText && !qrFile" @click="decodeQR">
              <el-icon style="margin-right: 4px;"><Search /></el-icon>
              {{ $t('decodePlatform.decodeQRBtn') }}
            </el-button>
            <el-button size="large" @click="resetQR">
              {{ $t('decodePlatform.reset') }}
            </el-button>
          </div>

          <!-- QR 解码结果 -->
          <div v-if="qrResult" class="qr-result-section">
            <QRProvenanceCard :decoded-info="qrDecodedInfo" :verify-passed="qrVerifyPassed" :signature-ok="qrSignatureOk" />
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 文件溯源（保留现有流程） -->
      <el-tab-pane :label="$t('decodePlatform.fileTraceTab')" name="file">
        <div class="tab-content">
          <el-alert type="warning" :closable="false" style="margin-bottom: 20px;">
            {{ $t('decodePlatform.fileTraceHint') }}
          </el-alert>

          <el-steps :active="currentStep" finish-status="success" align-center class="steps-bar">
            <el-step :title="$t('decodePlatform.step1Title')" :description="$t('decodePlatform.step1Desc')" />
            <el-step :title="$t('decodePlatform.step2Title')" :description="$t('decodePlatform.step2Desc')" />
            <el-step :title="$t('decodePlatform.step3Title')" :description="$t('decodePlatform.step3Desc')" />
          </el-steps>

          <!-- Step 1: 输入申请编号 -->
          <el-card v-show="currentStep === 0" class="step-card" shadow="hover">
            <div class="step-content">
              <el-icon class="step-icon"><Search /></el-icon>
              <h3>{{ $t('decodePlatform.enterAppId') }}</h3>
              <el-input
                v-model="applicationId"
                :placeholder="$t('decodePlatform.appIdPlaceholder')"
                size="large"
                clearable
                style="max-width: 400px;"
                @keyup.enter="goToStep2"
              />
              <div class="step-actions">
                <el-button type="primary" size="large" :disabled="!applicationId" @click="goToStep2">
                  {{ $t('decodePlatform.next') }}
                </el-button>
              </div>
            </div>
          </el-card>

          <!-- Step 2: 上传文件 -->
          <el-card v-show="currentStep === 1" class="step-card" shadow="hover">
            <div class="step-content">
              <el-icon class="step-icon"><UploadFilled /></el-icon>
              <h3>{{ $t('decodePlatform.uploadTitle') }}</h3>
              <p class="upload-hint">{{ $t('decodePlatform.uploadHint') }}</p>
              <el-upload
                class="trace-uploader"
                drag
                :limit="1"
                accept=".zip,.png,.jpg,.jpeg,.tif,.tiff"
                :auto-upload="false"
                :on-change="onFileChange"
              >
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  {{ $t('decodePlatform.dragOrClick') }} <em>{{ $t('decodePlatform.clickToUpload') }}</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">{{ $t('decodePlatform.formatTip') }}</div>
                </template>
              </el-upload>
              <div class="step-actions">
                <el-button size="large" @click="currentStep = 0">{{ $t('decodePlatform.prev') }}</el-button>
                <el-button type="primary" size="large" :loading="extracting" :disabled="!selectedFile" @click="doExtract">
                  {{ $t('decodePlatform.extractBtn') }}
                </el-button>
              </div>
            </div>
          </el-card>

          <!-- Step 3: 溯源结果 -->
          <el-card v-show="currentStep === 2" class="step-card" shadow="hover">
            <div class="step-content results-content">
              <div v-if="extracting" class="extracting-overlay">
                <el-icon class="spin-icon" :size="48"><Loading /></el-icon>
                <p>{{ $t('decodePlatform.extracting') }}</p>
              </div>

              <el-alert
                v-if="errorMsg"
                :title="errorMsg"
                type="error"
                show-icon
                :closable="false"
                style="margin-bottom: 20px;"
              />

              <template v-if="resultData">
                <div class="verify-banner" :class="verifyPassed ? 'verify-pass' : 'verify-fail'">
                  <el-icon :size="32"><CircleCheckFilled v-if="verifyPassed" /><CircleCloseFilled v-else /></el-icon>
                  <div>
                    <h3>{{ verifyPassed ? $t('decodePlatform.verifyPass') : $t('decodePlatform.verifyFail') }}</h3>
                    <p v-if="verifyPassed">{{ $t('decodePlatform.verifyPassDesc') }}</p>
                    <p v-else>{{ $t('decodePlatform.verifyFailDesc') }}</p>
                  </div>
                </div>

                <div class="result-columns">
                  <div class="watermark-panel">
                    <h4>{{ $t('decodePlatform.extractedWatermark') }}</h4>
                    <div class="watermark-img-box">
                      <img
                        v-if="watermarkBase64"
                        :src="`data:image/png;base64,${watermarkBase64}`"
                        alt="Extracted Watermark"
                      />
                      <el-empty v-else :description="$t('decodePlatform.noWatermark')" />
                    </div>
                    <template v-if="recoveredBase64">
                      <h4 style="margin-top: 16px;">{{ $t('decodePlatform.recoveredImage') }}</h4>
                      <div class="watermark-img-box">
                        <img :src="`data:image/png;base64,${recoveredBase64}`" alt="Recovered" />
                      </div>
                    </template>
                  </div>

                  <div class="provenance-panel">
                    <QRProvenanceCard :decoded-info="decodedInfo" :verify-passed="verifyPassed" :signature-ok="signatureOk" :nc-value="ncValue" />
                  </div>
                </div>
              </template>

              <div class="step-actions" style="margin-top: 24px;">
                <el-button size="large" @click="resetAll">{{ $t('decodePlatform.resetAll') }}</el-button>
                <el-button type="primary" size="large" @click="currentStep = 1">{{ $t('decodePlatform.reUpload') }}</el-button>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  Search, UploadFilled, Loading,
  CircleCheckFilled, CircleCloseFilled
} from '@element-plus/icons-vue'
import QRProvenanceCard from './QRProvenanceCard.vue'

const { t } = useI18n()

const activeTab = ref('qr')

// ── QR Code Decode state ──
const qrText = ref('')
const qrFile = ref(null)
const qrDecoding = ref(false)
const qrResult = ref(null)

const qrDecodedInfo = computed(() => qrResult.value?.data?.decoded_info || null)
const qrVerifyPassed = computed(() => qrDecodedInfo.value?.verify?.signature_ok !== false)
const qrSignatureOk = computed(() => qrDecodedInfo.value?.verify?.signature_ok !== false)

const onQRFileChange = (file) => {
  qrFile.value = file.raw
}

const onQRFileRemove = () => {
  qrFile.value = null
}

const decodeQR = async () => {
  if (!qrText.value && !qrFile.value) {
    ElMessage.warning(t('decodePlatform.qrRequired'))
    return
  }
  qrDecoding.value = true
  try {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token') || ''
    let response
    if (qrFile.value) {
      const formData = new FormData()
      formData.append('file', qrFile.value)
      const res = await fetch('/api/qrcode/decode', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      })
      response = await res.json()
      if (!res.ok) throw new Error(response.message || t('decodePlatform.qrDecodeFailed'))
    } else {
      const res = await fetch('/api/qrcode/decode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ qr_text: qrText.value })
      })
      response = await res.json()
      if (!res.ok) throw new Error(response.message || t('decodePlatform.qrDecodeFailed'))
    }
    qrResult.value = response
    ElMessage.success(t('decodePlatform.qrDecodeSuccess'))
  } catch (e) {
    ElMessage.error(e.message || t('decodePlatform.qrDecodeFailed'))
  } finally {
    qrDecoding.value = false
  }
}

const resetQR = () => {
  qrText.value = ''
  qrFile.value = null
  qrResult.value = null
}

// ── File Traceability state (existing flow) ──
const currentStep = ref(0)
const applicationId = ref('')
const selectedFile = ref(null)
const extracting = ref(false)
const errorMsg = ref('')
const resultData = ref(null)

const uploadUrl = '/api/vector/extract'

const watermarkBase64 = computed(() => resultData.value?.watermark_base64 || '')
const recoveredBase64 = computed(() => resultData.value?.recovered_base64 || '')
const decodedInfo = computed(() => resultData.value?.data?.decoded_info || null)
const normalized = computed(() => decodedInfo.value?.normalized || {})
const parsed = computed(() => decodedInfo.value?.parsed || {})
const verify = computed(() => decodedInfo.value?.verify || {})
const verifyPassed = computed(() => verify.value?.digest_ok !== false && verify.value?.signature_ok !== false)
const signatureOk = computed(() => verify.value?.signature_ok !== false)
const ncValue = computed(() => decodedInfo.value?.verify?.nc_value || null)

const goToStep2 = () => {
  if (!applicationId.value) {
    ElMessage.warning(t('decodePlatform.appIdRequired'))
    return
  }
  currentStep.value = 1
}

const onFileChange = (file) => {
  selectedFile.value = file.raw
}

const doExtract = () => {
  if (!selectedFile.value) {
    ElMessage.warning(t('decodePlatform.selectFileFirst'))
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
      'Authorization': `Bearer ${localStorage.getItem('token') || sessionStorage.getItem('token') || ''}`
    },
    body: formData
  })
    .then(async (res) => {
      const json = await res.json()
      if (!res.ok || json.status === false) {
        throw new Error(json.error || json.message || t('decodePlatform.extractFailed'))
      }
      resultData.value = json
      ElMessage.success(t('decodePlatform.extractSuccess'))
    })
    .catch((err) => {
      errorMsg.value = err.message || t('decodePlatform.extractFailed')
      ElMessage.error(errorMsg.value)
    })
    .finally(() => {
      extracting.value = false
    })
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
.decode-platform {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 24px;
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

.platform-tabs {
  border-radius: 12px;
  overflow: hidden;
}

.tab-content {
  padding: 8px 0;
}

.card-label {
  font-weight: 600;
}

/* ── QR Decode Tab ── */
.qr-uploader {
  width: 100%;
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}

.qr-result-section {
  margin-top: 24px;
}

/* ── File Traceability Tab ── */
.steps-bar {
  margin-bottom: 24px;
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

@media (max-width: 768px) {
  .result-columns {
    flex-direction: column;
  }

  .watermark-panel {
    flex: none;
  }
}
</style>
