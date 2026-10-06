<template>
  <div class="forensics-page">
    <div class="page-header">
      <h2>{{ $t('forensics.title') }}</h2>
      <p class="subtitle">{{ $t('forensics.subtitle') }}</p>
    </div>

    <el-tabs v-model="activeTab" type="border-card" class="forensics-tabs">
      <!-- Tab 1: 交付台账 -->
      <el-tab-pane :label="$t('forensics.tabDeliveries')" name="deliveries">
        <div class="tab-content">
          <div class="query-bar">
            <span class="query-label">{{ $t('forensics.applicationIdLabel') }}</span>
            <el-input-number
              v-model="queryAppId"
              :min="1"
              :controls="false"
              :placeholder="$t('forensics.applicationIdPlaceholder')"
              class="query-input"
              @keyup.enter="queryDeliveries"
            />
            <el-button type="primary" :icon="Search" :loading="deliveriesLoading" @click="queryDeliveries">
              {{ $t('forensics.queryBtn') }}
            </el-button>
          </div>

          <el-table
            v-loading="deliveriesLoading"
            :data="deliveries"
            stripe
            class="delivery-table"
            :empty-text="$t('forensics.emptyDeliveries')"
            @row-click="openDeliveryDetail"
          >
            <el-table-column :label="$t('forensics.colUuidShort')" width="110">
              <template #default="{ row }">{{ short(row.uuid, 8) }}</template>
            </el-table-column>
            <el-table-column prop="user_number" :label="$t('forensics.colUser')" width="140" />
            <el-table-column :label="$t('forensics.colFidShort')" width="150">
              <template #default="{ row }">{{ short(row.fid_short || row.fingerprint_id, 12) }}</template>
            </el-table-column>
            <el-table-column :label="$t('forensics.colStatus')" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.status" size="small" :type="statusTagType(row.status)">{{ row.status }}</el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('forensics.colArtifactRoot')" min-width="150">
              <template #default="{ row }">{{ short(row.artifact_root, 12) }}</template>
            </el-table-column>
            <el-table-column :label="$t('forensics.colChain')" width="90" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.chain" size="small" :type="row.chain.valid ? 'success' : 'danger'">
                  {{ row.chain.valid ? '✓' : '✗' }}
                </el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('forensics.colAnchor')" width="110">
              <template #default="{ row }">
                <el-tag v-if="row.anchor?.status" size="small" :type="statusTagType(row.anchor.status)">
                  {{ row.anchor.status }}
                </el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="$t('forensics.colCreatedAt')" width="175" />
            <el-table-column :label="$t('forensics.colDownloaded')" width="100" align="center">
              <template #default="{ row }">{{ row.downloaded ? $t('forensics.yes') : $t('forensics.no') }}</template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 泄漏取证 -->
      <el-tab-pane :label="$t('forensics.tabForensics')" name="forensics">
        <div class="tab-content">
          <h4 class="section-label">{{ $t('forensics.uploadTitle') }}</h4>
          <el-upload
            class="forensics-uploader"
            drag
            accept=".zip,.shp,.shx,.dbf,.prj,.tif,.tiff,.png,.jpg,.jpeg"
            :limit="1"
            :auto-upload="false"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              {{ $t('forensics.dragOrClick') }} <em>{{ $t('forensics.clickToUpload') }}</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">{{ $t('forensics.formatTip') }}</div>
            </template>
          </el-upload>

          <div class="qr-text-block">
            <div class="section-label">{{ $t('forensics.qrTextLabel') }}</div>
            <el-input v-model="qrText" type="textarea" :rows="3" :placeholder="$t('forensics.qrTextPlaceholder')" />
          </div>

          <div class="action-bar">
            <el-button type="primary" :icon="CircleCheck" :loading="verifying" @click="doVerify">
              {{ $t('forensics.verifyBtn') }}
            </el-button>
            <el-button type="danger" :icon="Aim" :loading="tracing" @click="doTrace">
              {{ $t('forensics.traceBtn') }}
            </el-button>
          </div>

          <div v-if="result" class="result-area">
            <!-- found + v2 -->
            <template v-if="result.found && result.watermark_version === 2">
              <div class="verify-banner" :class="verifyPassed ? 'verify-pass' : 'verify-fail'">
                <h3>{{ verifyPassed ? $t('forensics.verifyPassTitle') : $t('forensics.verifyFailTitle') }}</h3>
                <p v-if="result.msg">{{ result.msg }}</p>
              </div>

              <el-descriptions :column="2" border size="small" class="result-desc">
                <el-descriptions-item :label="$t('forensics.resultFid')">{{ result.fid || result.fid_short || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultDeliveryUuid')">{{ short(result.delivery_uuid, 8) }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultDataAlias')">{{ result.data_alias || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultDataType')">{{ result.data_type || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultIssuedAt')">{{ result.issued_at || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultArtifactRootMatch')">{{ matchText(result.artifact_root_match) }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultChainLength')">{{ (result.chain && result.chain.length !== undefined && result.chain.length !== null) ? result.chain.length : '—' }}</el-descriptions-item>
              </el-descriptions>

              <!-- trace 结果：红色高亮定位卡 -->
              <div v-if="isTrace && result.provenance" class="locate-card">
                <h3 class="locate-title">{{ $t('forensics.locateTitle') }}</h3>
                <p class="locate-line">{{ locateText }}</p>

                <h4 class="locate-subtitle">{{ $t('forensics.approvalChainTitle') }}</h4>
                <el-timeline v-if="(result.provenance.approvals || []).length > 0">
                  <el-timeline-item
                    v-for="(item, idx) in result.provenance.approvals"
                    :key="idx"
                    :timestamp="item.time || ''"
                    placement="top"
                  >
                    <div class="approval-line">
                      <strong>{{ item.stage || '—' }}</strong>
                      <span v-if="item.name"> · {{ item.name }}</span>
                      <span v-if="item.comment" class="approval-comment"> · {{ item.comment }}</span>
                    </div>
                  </el-timeline-item>
                </el-timeline>
                <el-empty v-else :description="$t('forensics.noRecords')" :image-size="40" />

                <h4 class="locate-subtitle">{{ $t('forensics.downloadRecordsTitle') }}</h4>
                <el-table
                  v-if="(result.provenance.downloads || []).length > 0"
                  :data="result.provenance.downloads"
                  size="small"
                  stripe
                >
                  <el-table-column prop="user_number" :label="$t('forensics.downloadUser')" />
                  <el-table-column prop="time" :label="$t('forensics.downloadTime')" />
                  <el-table-column prop="ip" :label="$t('forensics.downloadIp')" />
                  <el-table-column :label="$t('forensics.downloadDelivery')">
                    <template #default="{ row }">{{ short(row.delivery_uuid, 8) }}</template>
                  </el-table-column>
                </el-table>
                <el-empty v-else :description="$t('forensics.noRecords')" :image-size="40" />
              </div>
            </template>

            <!-- found + v1（旧版水印） -->
            <template v-else-if="result.found && result.watermark_version === 1">
              <div class="verify-banner verify-warn">
                <h3>{{ $t('forensics.v1Title') }}</h3>
                <p>{{ $t('forensics.v1Hint') }}</p>
                <p v-if="result.msg">{{ result.msg }}</p>
              </div>
              <el-descriptions :column="2" border size="small" class="result-desc">
                <el-descriptions-item :label="$t('forensics.resultDataAlias')">{{ result.data_alias || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultDataType')">{{ result.data_type || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultIssuedAt')">{{ result.issued_at || '—' }}</el-descriptions-item>
                <el-descriptions-item v-if="result.provenance" :label="$t('forensics.applicantName')">
                  {{ result.provenance.applicant_name || '—' }}
                </el-descriptions-item>
                <el-descriptions-item v-if="result.provenance" :label="$t('forensics.applicantNumber')">
                  {{ result.provenance.applicant_number || '—' }}
                </el-descriptions-item>
              </el-descriptions>
            </template>

            <!-- 未检测到证据 / 未知版本（容错） -->
            <el-card v-else shadow="never" class="result-empty-card">
              <el-result
                icon="info"
                :title="result.found ? $t('forensics.verifyFailTitle') : $t('forensics.notFoundTitle')"
                :sub-title="result.msg || ''"
              />
            </el-card>
          </div>

          <p class="disclaimer">{{ $t('forensics.disclaimer') }}</p>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 交付详情 dialog -->
    <el-dialog v-model="detailVisible" :title="$t('forensics.detailTitle')" width="760px">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item :label="$t('forensics.fieldUuid')" :span="2">
              <span class="break-all">{{ detail.uuid || '—' }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldApplicationId')">{{ detail.application_id != null ? detail.application_id : '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldDataId')">{{ detail.data_id || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldDataType')">{{ detail.data_type || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldUserNumber')">{{ detail.user_number || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldFingerprint')" :span="2">
              <span class="break-all">{{ detail.fingerprint_id || '—' }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldFidShort')">{{ detail.fid_short || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldAlgorithm')">{{ detail.algorithm || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldStatus')">
              <el-tag v-if="detail.status" size="small" :type="statusTagType(detail.status)">{{ detail.status }}</el-tag>
              <span v-else>—</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldDownloaded')">
              {{ detail.downloaded ? $t('forensics.yes') : $t('forensics.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldArtifactRoot')" :span="2">
              <span class="break-all">{{ detail.artifact_root || '—' }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldCreatedAt')">{{ detail.created_at || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldReadyAt')">{{ detail.ready_at || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldCompletedAt')">{{ detail.completed_at || '—' }}</el-descriptions-item>
          </el-descriptions>

          <h4 class="detail-section-title">{{ $t('forensics.chainResultTitle') }}</h4>
          <div class="chain-line">
            <el-tag v-if="detail.chain" :type="detail.chain.valid ? 'success' : 'danger'">
              {{ detail.chain.valid ? $t('forensics.chainValid') : $t('forensics.chainInvalid') }}
            </el-tag>
            <span v-else>—</span>
            <span>{{ $t('forensics.chainLengthLabel') }}: {{ (detail.chain && detail.chain.length !== undefined && detail.chain.length !== null) ? detail.chain.length : '—' }}</span>
            <span v-if="detail.chain && detail.chain.broken_at !== undefined && detail.chain.broken_at !== null">
              {{ $t('forensics.chainBrokenAt') }}: {{ detail.chain.broken_at }}
            </span>
          </div>

          <h4 class="detail-section-title">{{ $t('forensics.eventsTitle') }}</h4>
          <el-timeline v-if="(detail.events || []).length > 0">
            <el-timeline-item
              v-for="(ev, idx) in detail.events"
              :key="ev.seq != null ? ev.seq : idx"
              :timestamp="ev.ts || ''"
              placement="top"
            >
              <div class="event-line">
                <el-tag size="small" type="info">#{{ ev.seq != null ? ev.seq : idx }}</el-tag>
                <strong class="event-type">{{ ev.event_type || '—' }}</strong>
                <span class="event-hash">{{ short(ev.event_hash, 16) }}</span>
                <span v-if="ev.kid" class="event-kid">{{ ev.kid }}</span>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else :description="$t('forensics.noEvents')" :image-size="40" />

          <h4 class="detail-section-title">{{ $t('forensics.anchorTitle') }}</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item :label="$t('forensics.anchorBatchId')">{{ detail.anchor?.batch_id || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.anchorStatus')">
              <el-tag v-if="detail.anchor?.status" size="small" :type="statusTagType(detail.anchor.status)">
                {{ detail.anchor.status }}
              </el-tag>
              <span v-else>—</span>
            </el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.anchorProvider')">{{ detail.anchor?.provider || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.anchorRootHex')">
              <span class="break-all">{{ detail.anchor?.root_hex || '—' }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <p v-if="detail.anchor?.error" class="anchor-error">{{ detail.anchor.error }}</p>

          <div class="dialog-actions">
            <el-button type="primary" :icon="Link" :loading="buildingAnchor" @click="buildAnchor">
              {{ $t('forensics.buildAnchorBtn') }}
            </el-button>
          </div>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Search, UploadFilled, Aim, CircleCheck, Link } from '@element-plus/icons-vue'
import {
  verifyForensics,
  traceForensics,
  getDeliveries,
  getDeliveryDetail,
  buildAnchorBatch,
} from '@/api/forensics'

const { t } = useI18n()

const activeTab = ref('deliveries')

// ── 交付台账 ──
const queryAppId = ref(null)
const deliveries = ref([])
const deliveriesLoading = ref(false)

// ── 泄漏取证 ──
const selectedFile = ref(null)
const qrText = ref('')
const verifying = ref(false)
const tracing = ref(false)
const result = ref(null)
const isTrace = ref(false)

// ── 交付详情 dialog ──
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)
const buildingAnchor = ref(false)

// 截断显示，缺失字段回退占位符
const short = (value, len) => {
  if (value === null || value === undefined || value === '') return '—'
  return String(value).slice(0, len)
}

// 状态 tag 色映射（照 QRProvenanceCard 惯例：小写包含匹配 + info 兜底）
const statusTagType = (value) => {
  const s = String(value || '').toLowerCase()
  if (!s) return 'info'
  if (s.includes('ready') || s.includes('complete') || s.includes('approved') || s.includes('anchored') || s.includes('valid')) return 'success'
  if (s.includes('reject') || s.includes('fail') || s.includes('error') || s.includes('missing') || s.includes('invalid') || s.includes('disabled') || s.includes('broken')) return 'danger'
  if (s.includes('revoke') || s.includes('recall') || s.includes('pending') || s.includes('expire') || s.includes('build')) return 'warning'
  return 'info'
}

const verifyPassed = computed(() => !!result.value?.signature_valid && !!result.value?.chain?.valid)

const matchText = (value) => {
  if (value === true) return t('forensics.match')
  if (value === false) return t('forensics.mismatch')
  return '—'
}

const locateText = computed(() => {
  const p = result.value?.provenance
  if (!p) return ''
  return t('forensics.traceLocation', {
    name: p.applicant_name || '—',
    number: p.applicant_number || '—',
    uuid: short(result.value?.delivery_uuid, 8),
  })
})

const queryDeliveries = async () => {
  deliveriesLoading.value = true
  try {
    // application_id 为可选过滤条件：为空时列出全部交付
    const params = {}
    if (queryAppId.value) params.application_id = queryAppId.value
    const res = await getDeliveries(params)
    const body = res?.data
    if (!body?.status) {
      ElMessage.error(body?.msg || t('forensics.fetchDeliveriesFailed'))
      deliveries.value = []
      return
    }
    deliveries.value = body.deliveries || []
  } catch (err) {
    console.error('Forensics deliveries query failed:', err)
    ElMessage.error(t('forensics.fetchDeliveriesFailed'))
  } finally {
    deliveriesLoading.value = false
  }
}

const onFileChange = (uploadFile) => {
  selectedFile.value = uploadFile?.raw || null
}

const onFileRemove = () => {
  selectedFile.value = null
}

// multipart 文件优先；无文件时回退 JSON { qr_text }
const buildPayload = () => {
  if (selectedFile.value) {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    return formData
  }
  const text = qrText.value.trim()
  if (text) return { qr_text: text }
  return null
}

const doVerify = async () => {
  const payload = buildPayload()
  if (!payload) {
    ElMessage.warning(t('forensics.inputRequired'))
    return
  }
  verifying.value = true
  try {
    const res = await verifyForensics(payload)
    const body = res?.data
    if (!body?.status) {
      result.value = null
      ElMessage.error(body?.msg || t('forensics.verifyFailed'))
      return
    }
    result.value = body
    isTrace.value = false
  } catch (err) {
    console.error('Forensics verify failed:', err)
    result.value = null
    ElMessage.error(err?.response?.data?.msg || t('forensics.verifyFailed'))
  } finally {
    verifying.value = false
  }
}

const doTrace = async () => {
  const payload = buildPayload()
  if (!payload) {
    ElMessage.warning(t('forensics.inputRequired'))
    return
  }
  tracing.value = true
  try {
    const res = await traceForensics(payload)
    const body = res?.data
    if (!body?.status) {
      result.value = null
      ElMessage.error(body?.msg || t('forensics.traceFailed'))
      return
    }
    result.value = body
    isTrace.value = true
  } catch (err) {
    console.error('Forensics trace failed:', err)
    result.value = null
    ElMessage.error(err?.response?.data?.msg || t('forensics.traceFailed'))
  } finally {
    tracing.value = false
  }
}

const openDeliveryDetail = async (row) => {
  if (!row?.uuid) return
  detailVisible.value = true
  detail.value = row
  detailLoading.value = true
  try {
    const res = await getDeliveryDetail(row.uuid)
    const body = res?.data
    const delivery = body?.delivery
    if (body?.status && delivery) {
      detail.value = {
        ...delivery,
        events: body.events || [],
        chain: body.chain || null,
        anchor: body.anchor || null
      }
    } else {
      ElMessage.error(body?.msg || t('forensics.detailFailed'))
    }
  } catch (err) {
    console.error('Forensics delivery detail failed:', err)
    ElMessage.error(t('forensics.detailFailed'))
  } finally {
    detailLoading.value = false
  }
}

const buildAnchor = async () => {
  buildingAnchor.value = true
  try {
    const res = await buildAnchorBatch()
    const body = res?.data
    const batch = body?.batch
    if (body?.status && batch) {
      if (detail.value) {
        detail.value = { ...detail.value, anchor: { ...(detail.value.anchor || {}), ...batch } }
      }
      ElMessage.success(t('forensics.buildAnchorSuccess'))
    } else {
      ElMessage.error(body?.msg || t('forensics.buildAnchorFailed'))
    }
  } catch (err) {
    console.error('Forensics build anchor batch failed:', err)
    ElMessage.error(t('forensics.buildAnchorFailed'))
  } finally {
    buildingAnchor.value = false
  }
}
</script>

<style scoped>
.forensics-page {
  padding: 4px;
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

.forensics-tabs {
  border-radius: 12px;
  overflow: hidden;
}

.tab-content {
  padding: 8px 0;
}

.query-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.query-label {
  color: #606266;
  font-size: 14px;
}

.query-input {
  width: 220px;
}

.delivery-table {
  width: 100%;
}

:deep(.delivery-table .el-table__row) {
  cursor: pointer;
}

.section-label {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
  margin: 0 0 8px;
}

.forensics-uploader {
  width: 100%;
}

.qr-text-block {
  margin: 16px 0;
}

.qr-text-block .section-label {
  margin-bottom: 6px;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.result-area {
  margin-top: 4px;
}

.verify-banner {
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 16px;
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

.verify-warn {
  background: linear-gradient(135deg, #fdf6ec, #faecd8);
  border: 1px solid #f5dab1;
  color: #e6a23c;
}

.result-desc {
  margin-bottom: 16px;
}

.locate-card {
  background: linear-gradient(135deg, #fef0f0, #fde2e2);
  border: 1px solid #fbc4c4;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 16px;
}

.locate-title {
  margin: 0 0 8px;
  font-size: 16px;
  color: #f56c6c;
}

.locate-line {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: #f56c6c;
}

.locate-subtitle {
  margin: 16px 0 8px;
  font-size: 14px;
  color: #303133;
}

.approval-line {
  font-size: 14px;
  color: #303133;
}

.approval-comment {
  color: #909399;
  font-size: 13px;
}

.result-empty-card {
  margin-bottom: 16px;
}

.disclaimer {
  margin-top: 24px;
  font-size: 12px;
  color: #909399;
  text-align: center;
  line-height: 1.6;
}

.detail-body {
  min-height: 120px;
}

.detail-section-title {
  margin: 20px 0 10px;
  font-size: 14px;
  color: #303133;
}

.chain-line {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #606266;
}

.event-line {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.event-type {
  color: #303133;
}

.event-hash {
  color: #909399;
  font-family: monospace;
}

.event-kid {
  color: #909399;
  font-size: 12px;
}

.anchor-error {
  color: #f56c6c;
  font-size: 13px;
  margin: 8px 0 0;
  word-break: break-all;
}

.dialog-actions {
  margin-top: 16px;
  text-align: right;
}

.break-all {
  word-break: break-all;
}
</style>
