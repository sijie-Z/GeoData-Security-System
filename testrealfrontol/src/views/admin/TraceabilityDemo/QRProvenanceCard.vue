<!--
  QR 溯源信息卡（Blockscout 三段式视觉）
  小白解释：解码 QR 后展示这张卡——只重排视觉，数据字段与绑定逻辑一律不变：
  ① 结论卡：验证状态 banner + 签名 tag + 核心字段（申请编号/状态/数据类型/申请人）+ NC 进度；
  ② 完整字段：按 申请信息 / 审批信息 / 其他信息 分区的 descriptions（原字段原顺序）；
  ③ 原始数据：HMAC 签名（HashText 等宽显示）+ QR 原文折叠（保留原 textarea 展示）。
-->
<template>
  <div class="qr-provenance-card">
    <h4 class="card-title">{{ $t('decodePlatform.provenanceTitle') }}</h4>

    <!-- ① 结论卡：状态 banner + 核心字段 -->
    <section class="conclusion-card" :class="verifyPassed ? 'is-pass' : 'is-fail'">
      <div class="conclusion-head">
        <el-icon :size="20" class="conclusion-icon">
          <CircleCheckFilled v-if="verifyPassed" />
          <CircleCloseFilled v-else />
        </el-icon>
        <span class="conclusion-title">
          {{ verifyPassed ? $t('decodePlatform.verifyPass') : $t('decodePlatform.verifyFail') }}
        </span>
        <el-tag
          class="conclusion-sig"
          :type="signatureOk ? 'success' : 'danger'"
          effect="dark"
          size="small"
        >
          <el-icon style="margin-right: 4px;"><Lock /></el-icon>
          {{ signatureOk ? $t('decodePlatform.sigValid') : $t('decodePlatform.sigInvalid') }}
        </el-tag>
      </div>

      <div class="conclusion-grid">
        <div class="conclusion-item">
          <span class="conclusion-label">{{ $t('decodePlatform.appId') }}</span>
          <span class="conclusion-value">{{ normalized.id || parsed.id || '-' }}</span>
        </div>
        <div class="conclusion-item">
          <span class="conclusion-label">{{ $t('decodePlatform.appStatus') }}</span>
          <el-tag size="small" :type="statusTagType">{{ normalized.application_status || parsed.application_status || '-' }}</el-tag>
        </div>
        <div class="conclusion-item">
          <span class="conclusion-label">{{ $t('decodePlatform.dataType') }}</span>
          <span class="conclusion-value">{{ normalized.data_type || parsed.data_type || '-' }}</span>
        </div>
        <div class="conclusion-item">
          <span class="conclusion-label">{{ $t('decodePlatform.applicant') }}</span>
          <span class="conclusion-value">
            <strong>{{ normalized.applicant || parsed.applicant || '-' }}</strong>
            <span v-if="normalized.applicant_id || parsed.applicant_id"> ({{ normalized.applicant_id || parsed.applicant_id }})</span>
          </span>
        </div>
      </div>

      <div v-if="ncValue != null" class="nc-badge">
        <span class="nc-label">{{ $t('decodePlatform.ncValue') }}</span>
        <el-progress
          :percentage="Math.round((ncValue || 0) * 100)"
          :color="ncColor"
          :stroke-width="16"
          :text-inside="true"
        />
      </div>
    </section>

    <!-- ② 完整字段：分区 descriptions -->
    <section class="fields-section">
      <h5 class="section-title">{{ $t('decodePlatform.fullFieldsTitle') }}</h5>

      <div class="fields-group-label">{{ $t('decodePlatform.sectionApplication') }}</div>
      <el-descriptions :column="1" border size="small" class="provenance-desc">
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
      </el-descriptions>

      <div class="fields-group-label">{{ $t('decodePlatform.sectionApproval') }}</div>
      <el-descriptions :column="1" border size="small" class="provenance-desc">
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
      </el-descriptions>

      <div class="fields-group-label">{{ $t('decodePlatform.sectionOther') }}</div>
      <el-descriptions :column="1" border size="small" class="provenance-desc">
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
    </section>

    <!-- ③ 原始数据：签名（HashText）+ QR 原文折叠 -->
    <section class="raw-section">
      <h5 class="section-title">{{ $t('decodePlatform.rawDataTitle') }}</h5>
      <div v-if="signature" class="signature-row">
        <span class="signature-label">{{ $t('decodePlatform.signature') }}</span>
        <HashText :value="signature" />
      </div>
      <el-collapse v-if="qrRaw">
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
    </section>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Lock, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import HashText from '@/components/common/HashText.vue'

const props = defineProps({
  decodedInfo: { type: Object, default: null },
  verifyPassed: { type: Boolean, default: false },
  signatureOk: { type: Boolean, default: false },
  ncValue: { type: Number, default: null }
})

const normalized = computed(() => props.decodedInfo?.normalized || {})
const parsed = computed(() => props.decodedInfo?.parsed || {})
const qrRaw = computed(() => normalized.value?._qr_raw || parsed.value?._raw || '')
// HMAC 签名：仅文件溯源路径保留（解码接口按设计 pop 掉），有则展示
const signature = computed(() => parsed.value?.Signature || '')

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
.qr-provenance-card {
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 14px;
}

/* ── ① 结论卡 ── */
.conclusion-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  padding: 14px 16px;
  margin-bottom: 18px;
}

.conclusion-card.is-pass {
  background: linear-gradient(135deg, #f0f9eb, #e1f3d8);
  border-color: #b3e19d;
}

.conclusion-card.is-fail {
  background: linear-gradient(135deg, #fef0f0, #fde2e2);
  border-color: #fbc4c4;
}

.conclusion-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.conclusion-icon {
  color: var(--text-secondary);
}

.conclusion-card.is-pass .conclusion-icon,
.conclusion-card.is-pass .conclusion-title {
  color: #67c23a;
}

.conclusion-card.is-fail .conclusion-icon,
.conclusion-card.is-fail .conclusion-title {
  color: #f56c6c;
}

.conclusion-title {
  font-size: 15px;
  font-weight: 600;
}

.conclusion-sig {
  margin-left: auto;
  flex: none;
}

.conclusion-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
  margin-top: 12px;
}

.conclusion-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 13px;
}

.conclusion-label {
  flex: none;
  color: var(--text-secondary);
  font-size: 12px;
}

.conclusion-value {
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nc-badge {
  margin-top: 12px;
}

.nc-label {
  font-size: 12px;
  color: var(--text-secondary);
  display: block;
  margin-bottom: 4px;
}

/* ── ② 完整字段 ── */
.fields-section {
  margin-bottom: 18px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.4px;
  margin: 0 0 8px;
}

.fields-group-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin: 10px 0 6px;
}

.provenance-desc {
  margin-bottom: 6px;
}

/* ── ③ 原始数据 ── */
.signature-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 13px;
}

.signature-label {
  color: var(--text-secondary);
  font-size: 12px;
}

.qr-raw-text :deep(textarea) {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
  font-size: 12px;
}
</style>
