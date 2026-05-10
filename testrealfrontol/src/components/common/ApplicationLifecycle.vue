<template>
  <div class="lifecycle-container" v-loading="loading">
    <el-empty v-if="!loading && !detail" :description="$t('lifecycle.noData')" />

    <template v-if="detail">
      <!-- Header summary -->
      <div class="lifecycle-header">
        <div class="header-left">
          <h3>{{ $t('lifecycle.appId') }}: #{{ detail.id }}</h3>
          <el-tag :type="statusTagType" effect="dark" size="large">{{ statusText }}</el-tag>
        </div>
        <div class="header-right">
          <span class="data-type-tag">
            <el-tag :type="detail.data_type === 'vector' ? 'primary' : 'success'" size="small">
              {{ detail.data_type === 'vector' ? $t('lifecycle.vector') : $t('lifecycle.raster') }}
            </el-tag>
          </span>
          <span class="data-name">{{ detail.data_alias || detail.data_name }}</span>
        </div>
      </div>

      <!-- Timeline -->
      <el-timeline>
        <!-- 1. Submitted -->
        <el-timeline-item
          :timestamp="formatTime(detail.application_submission_time)"
          placement="top"
          :color="'#409eff'"
          :icon="Document"
          :size="'large'"
        >
          <el-card shadow="never" class="timeline-card">
            <h4>{{ $t('lifecycle.submitted') }}</h4>
            <p class="timeline-desc">{{ $t('lifecycle.applicant') }}: <strong>{{ detail.applicant_name }}</strong> ({{ detail.applicant_user_number }})</p>
            <p class="timeline-desc" v-if="detail.reason">{{ $t('lifecycle.reason') }}: {{ detail.reason }}</p>
          </el-card>
        </el-timeline-item>

        <!-- 2. First Review -->
        <el-timeline-item
          v-if="detail.first_statu !== null"
          :timestamp="formatTime(detail.adm1_approval_time)"
          placement="top"
          :color="detail.first_statu ? '#67c23a' : '#f56c6c'"
          :icon="detail.first_statu ? CircleCheck : CircleClose"
          :size="'large'"
        >
          <el-card shadow="never" class="timeline-card">
            <h4>{{ $t('lifecycle.firstReview') }}
              <el-tag :type="detail.first_statu ? 'success' : 'danger'" size="small">
                {{ detail.first_statu ? $t('lifecycle.passed') : $t('lifecycle.rejected') }}
              </el-tag>
            </h4>
            <p class="timeline-desc">{{ $t('lifecycle.reviewer') }}: {{ detail.adm1_name || '-' }} ({{ detail.adm1_user_number || '-' }})</p>
          </el-card>
        </el-timeline-item>

        <!-- Pending first review -->
        <el-timeline-item
          v-if="detail.first_statu === null && status !== 'recalled'"
          placement="top"
          color="#e4e7ed"
          :size="'normal'"
        >
          <el-card shadow="never" class="timeline-card pending-card">
            <h4>{{ $t('lifecycle.firstReview') }}
              <el-tag type="warning" size="small">{{ $t('lifecycle.pending') }}</el-tag>
            </h4>
            <p class="timeline-desc">{{ $t('lifecycle.awaitingFirstReview') }}</p>
          </el-card>
        </el-timeline-item>

        <!-- 3. Second Review -->
        <el-timeline-item
          v-if="detail.second_statu !== null"
          :timestamp="formatTime(detail.adm2_approval_time)"
          placement="top"
          :color="detail.second_statu ? '#67c23a' : '#f56c6c'"
          :icon="detail.second_statu ? CircleCheck : CircleClose"
          :size="'large'"
        >
          <el-card shadow="never" class="timeline-card">
            <h4>{{ $t('lifecycle.secondReview') }}
              <el-tag :type="detail.second_statu ? 'success' : 'danger'" size="small">
                {{ detail.second_statu ? $t('lifecycle.passed') : $t('lifecycle.rejected') }}
              </el-tag>
            </h4>
            <p class="timeline-desc">{{ $t('lifecycle.reviewer') }}: {{ detail.adm2_name || '-' }} ({{ detail.adm2_user_number || '-' }})</p>
          </el-card>
        </el-timeline-item>

        <!-- Pending second review -->
        <el-timeline-item
          v-if="detail.first_statu === true && detail.second_statu === null && status !== 'recalled'"
          placement="top"
          color="#e4e7ed"
          :size="'normal'"
        >
          <el-card shadow="never" class="timeline-card pending-card">
            <h4>{{ $t('lifecycle.secondReview') }}
              <el-tag type="warning" size="small">{{ $t('lifecycle.pending') }}</el-tag>
            </h4>
            <p class="timeline-desc">{{ $t('lifecycle.awaitingSecondReview') }}</p>
          </el-card>
        </el-timeline-item>

        <!-- 4. Watermark Generated -->
        <el-timeline-item
          v-if="detail.watermark_generated"
          :timestamp="formatTime(detail.generation_timestamp)"
          placement="top"
          color="#909399"
          :icon="Picture"
          :size="'normal'"
        >
          <el-card shadow="never" class="timeline-card">
            <h4>{{ $t('lifecycle.watermarkGenerated') }}</h4>
            <p class="timeline-desc" v-if="detail.purpose">{{ $t('lifecycle.purpose') }}: {{ detail.purpose }}</p>
            <p class="timeline-desc" v-if="detail.security_level">{{ $t('lifecycle.securityLevel') }}: {{ detail.security_level }}</p>
            <p class="timeline-desc" v-if="detail.qr_version">{{ $t('lifecycle.qrVersion') }}: V{{ detail.qr_version }}</p>
          </el-card>
        </el-timeline-item>

        <!-- 5. Watermark Embedded -->
        <el-timeline-item
          v-if="detail.watermark_embedded"
          placement="top"
          color="#909399"
          :icon="Stamp"
          :size="'normal'"
        >
          <el-card shadow="never" class="timeline-card">
            <h4>{{ $t('lifecycle.watermarkEmbedded') }}</h4>
            <p class="timeline-desc">{{ $t('lifecycle.dataProtected') }}</p>
          </el-card>
        </el-timeline-item>

        <!-- 6. Downloads -->
        <el-timeline-item
          v-for="(dl, idx) in (detail.download_records || [])"
          :key="'dl-' + idx"
          :timestamp="formatTime(dl.download_time)"
          placement="top"
          color="#67c23a"
          :icon="Download"
          :size="'normal'"
        >
          <el-card shadow="never" class="timeline-card">
            <h4>{{ $t('lifecycle.downloaded') }}</h4>
            <p class="timeline-desc">{{ $t('lifecycle.downloadedBy') }}: {{ dl.download_user_number }}</p>
            <p class="timeline-desc" v-if="dl.filename">{{ $t('lifecycle.filename') }}: {{ dl.filename }}</p>
          </el-card>
        </el-timeline-item>

        <!-- 7. Recalled -->
        <el-timeline-item
          v-if="detail.is_recalled"
          :timestamp="formatTime(detail.recalled_at)"
          placement="top"
          color="#e6a23c"
          :icon="WarningFilled"
          :size="'large'"
        >
          <el-card shadow="never" class="timeline-card recall-card">
            <h4>{{ $t('lifecycle.recalled') }}
              <el-tag type="warning" size="small">{{ $t('lifecycle.dataRevoked') }}</el-tag>
            </h4>
            <p class="timeline-desc" v-if="detail.recall_reason">{{ $t('lifecycle.recallReason') }}: {{ detail.recall_reason }}</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>

      <!-- Watermark signature info (if available) -->
      <div v-if="detail.qr_signature" class="signature-section">
        <el-divider />
        <div class="sig-row">
          <el-icon><Lock /></el-icon>
          <span>{{ $t('lifecycle.hmacSignature') }}: <code>{{ detail.qr_signature }}</code></span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Document, CircleCheck, CircleClose, Picture,
  Stamp, Download, WarningFilled, Lock
} from '@element-plus/icons-vue'

const { t } = useI18n()

const props = defineProps({
  applicationId: { type: [Number, String], required: true },
  detailData: { type: Object, default: null }
})

const loading = ref(false)
const detail = ref(null)

const status = computed(() => {
  if (!detail.value) return 'pending'
  const d = detail.value
  if (d.is_recalled) return 'recalled'
  if (d.second_statu === true) return 'approved'
  if (d.second_statu === false) return 'rejected'
  if (d.first_statu === true) return 'adm1_approved'
  if (d.first_statu === false) return 'adm1_rejected'
  return 'pending'
})

const statusText = computed(() => {
  const map = {
    pending: t('lifecycle.statusPending'),
    adm1_approved: t('lifecycle.statusAdm1Approved'),
    adm1_rejected: t('lifecycle.statusAdm1Rejected'),
    approved: t('lifecycle.statusApproved'),
    rejected: t('lifecycle.statusRejected'),
    recalled: t('lifecycle.statusRecalled')
  }
  return map[status.value] || status.value
})

const statusTagType = computed(() => {
  const map = { pending: 'warning', adm1_approved: 'info', adm1_rejected: 'danger', approved: 'success', rejected: 'danger', recalled: 'warning' }
  return map[status.value] || 'info'
})

const formatTime = (isoStr) => {
  if (!isoStr) return ''
  return new Date(isoStr).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const loadDetail = async () => {
  if (props.detailData) {
    detail.value = props.detailData
    return
  }
  if (!props.applicationId) return
  loading.value = true
  try {
    const { getApplicationDetail } = await import('@/api/employee')
    const res = await getApplicationDetail(props.applicationId)
    detail.value = res.data?.data || null
  } catch (e) {
    console.error('Failed to load application detail:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.applicationId, () => { if (props.applicationId) loadDetail() }, { immediate: true })
watch(() => props.detailData, (val) => { if (val) detail.value = val }, { immediate: true })
</script>

<style scoped>
.lifecycle-container {
  padding: 8px 0;
}

.lifecycle-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.data-name {
  font-size: 14px;
  color: #606266;
}

.timeline-card {
  border: none;
  background: #f8fafc;
}

.timeline-card :deep(.el-card__body) {
  padding: 12px 16px;
}

.timeline-card h4 {
  margin: 0 0 6px;
  font-size: 14px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeline-desc {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}

.pending-card {
  background: #fdf6ec;
  border: 1px dashed #e6a23c;
}

.recall-card {
  background: #fef0f0;
  border-left: 3px solid #e6a23c;
}

.signature-section {
  color: #909399;
  font-size: 13px;
}

.sig-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sig-row code {
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
}
</style>
