<template>
  <div class="qr-provenance-card">
    <h4>{{ $t('decodePlatform.provenanceTitle') }}</h4>

    <div v-if="ncValue != null" class="nc-badge">
      <span class="nc-label">{{ $t('decodePlatform.ncValue') }}</span>
      <el-progress
        :percentage="Math.round((ncValue || 0) * 100)"
        :color="ncColor"
        :stroke-width="20"
        :text-inside="true"
      />
    </div>

    <el-descriptions :column="1" border class="provenance-desc">
      <el-descriptions-item :label="$t('decodePlatform.appId')">
        {{ normalized.id || parsed.id || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.appNumber')">
        {{ normalized.application_number || parsed.application_number || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.appStatus')">
        <el-tag :type="statusTagType">{{ normalized.application_status || parsed.application_status || '-' }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.dataType')">
        {{ normalized.data_type || parsed.data_type || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.applicant')">
        <strong>{{ normalized.applicant || parsed.applicant || '-' }}</strong>
        <span v-if="normalized.applicant_id || parsed.applicant_id"> ({{ normalized.applicant_id || parsed.applicant_id }})</span>
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.approver1')">
        {{ normalized.approver_1 || parsed.approver_1 || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.approver1Id')">
        {{ normalized.approver_1_id || parsed.approver_1_id || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.approver1Time')">
        {{ normalized.approver_1_time || parsed.approver_1_time || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.approver2')">
        {{ normalized.approver_2 || parsed.approver_2 || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.approver2Id')">
        {{ normalized.approver_2_id || parsed.approver_2_id || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.approver2Time')">
        {{ normalized.approver_2_time || parsed.approver_2_time || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.submittedAt')">
        {{ normalized.submitted_at || parsed.submitted_at || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.generatedAt')">
        {{ normalized.generated_at || parsed.generated_at || '-' }}
      </el-descriptions-item>
      <el-descriptions-item :label="$t('decodePlatform.reason')">
        {{ normalized.reason || parsed.reason || '-' }}
      </el-descriptions-item>
    </el-descriptions>

    <div class="sig-verify">
      <el-tag :type="signatureOk ? 'success' : 'danger'" effect="dark" size="large">
        <el-icon style="margin-right: 4px;"><Lock /></el-icon>
        {{ signatureOk ? $t('decodePlatform.sigValid') : $t('decodePlatform.sigInvalid') }}
      </el-tag>
    </div>

    <el-collapse v-if="qrRaw" style="margin-top: 16px;">
      <el-collapse-item :title="$t('decodePlatform.qrRawContent')" name="qrraw">
        <el-input
          :model-value="qrRaw"
          type="textarea"
          :rows="10"
          readonly
          class="qr-raw-text"
        />
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Lock } from '@element-plus/icons-vue'

const props = defineProps({
  decodedInfo: { type: Object, default: null },
  verifyPassed: { type: Boolean, default: false },
  signatureOk: { type: Boolean, default: false },
  ncValue: { type: Number, default: null }
})

const normalized = computed(() => props.decodedInfo?.normalized || {})
const parsed = computed(() => props.decodedInfo?.parsed || {})
const qrRaw = computed(() => normalized.value?._qr_raw || parsed.value?._raw || '')

const ncColor = computed(() => {
  const nc = props.ncValue || 0
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
</script>

<style scoped>
.qr-provenance-card h4 {
  font-size: 15px;
  color: #303133;
  margin: 0 0 12px;
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

.qr-raw-text :deep(textarea) {
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 12px;
}
</style>
