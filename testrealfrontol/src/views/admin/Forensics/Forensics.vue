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
            <el-input
              v-model="queryUser"
              :placeholder="$t('forensics.filterOperator')"
              clearable
              class="query-input"
              @keyup.enter="queryDeliveries"
            />
            <el-input
              v-model="queryFid"
              :placeholder="$t('forensics.filterFingerprint')"
              clearable
              class="query-input"
              @keyup.enter="queryDeliveries"
            />
            <el-input
              v-model="queryUuid"
              :placeholder="$t('forensics.filterUuid')"
              clearable
              class="query-input"
              @keyup.enter="queryDeliveries"
            />
            <el-date-picker
              v-model="queryTimeRange"
              type="datetimerange"
              value-format="YYYY-MM-DDTHH:mm:ss"
              :start-placeholder="$t('forensics.filterTimeStart')"
              :end-placeholder="$t('forensics.filterTimeEnd')"
              class="query-range"
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
            :row-class-name="deliveryRowClass"
            @row-click="openDeliveryDetail"
          >
            <el-table-column :label="$t('forensics.colUuidShort')" width="110">
              <template #default="{ row }"><span class="font-mono">{{ short(row.uuid, 8) }}</span></template>
            </el-table-column>
            <el-table-column prop="user_number" :label="$t('forensics.colUser')" width="140" />
            <el-table-column :label="$t('forensics.colFidShort')" width="150">
              <template #default="{ row }"><span class="font-mono">{{ short(row.fid_short || row.fingerprint_id, 12) }}</span></template>
            </el-table-column>
            <el-table-column :label="$t('forensics.colStatus')" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.status" size="small" :type="statusTagType(row.status)">{{ row.status }}</el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('forensics.colArtifactRoot')" min-width="150">
              <template #default="{ row }"><span class="font-mono">{{ short(row.artifact_root, 12) }}</span></template>
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
                <el-descriptions-item :label="$t('forensics.resultFid')">
                  <HashText :value="result.fid || result.fid_short" />
                </el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultDeliveryUuid')">{{ short(result.delivery_uuid, 8) }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultDataAlias')">{{ result.data_alias || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultDataType')">{{ result.data_type || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultIssuedAt')">{{ result.issued_at || '—' }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.resultArtifactRootMatch')">{{ matchText(result.artifact_root_match) }}</el-descriptions-item>
                <el-descriptions-item :label="$t('forensics.fieldArtifactRoot')">
                  <HashText :value="result.artifact_root" />
                </el-descriptions-item>
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
                <EmptyState v-else compact variant="never" :title="$t('forensics.noRecords')" />

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
                <EmptyState v-else compact variant="never" :title="$t('forensics.noRecords')" />
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

    <!-- 交付详情 dialog：① 摘要卡 → ② 字段明细 → ③ 事件链（时间线卡片）→ ④ 证据与锚定 -->
    <el-dialog v-model="detailVisible" :title="$t('forensics.detailTitle')" width="780px">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <!-- ① 摘要卡：交付号 / 用户 / FID / 状态大 tag / 产物根 -->
          <section class="summary-card">
            <div class="summary-head">
              <div class="summary-id">
                <span class="summary-label">{{ $t('forensics.fieldUuid') }}</span>
                <HashText :value="detail.uuid" />
              </div>
              <el-tag
                v-if="detail.status"
                size="large"
                effect="dark"
                :type="statusTagType(detail.status)"
                class="summary-status"
              >
                {{ detail.status }}
              </el-tag>
              <span v-else class="summary-status-empty">—</span>
            </div>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="summary-label">{{ $t('forensics.fieldUserNumber') }}</span>
                <span class="summary-value">{{ detail.user_number || '—' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">{{ $t('forensics.resultFid') }}</span>
                <HashText :value="detail.fingerprint_id" />
              </div>
              <div class="summary-item summary-item--wide">
                <span class="summary-label">{{ $t('forensics.fieldArtifactRoot') }}</span>
                <HashText :value="detail.artifact_root" />
              </div>
            </div>
          </section>

          <!-- ①.5 分发链水位图（§5.16）：左操作树 + 右时长条；缺失虚线断链；点击节点高亮分享 -->
          <h4 class="detail-section-title">{{ $t('forensics.chainTitle') }}</h4>
          <DeliveryChain :steps="chainSteps" :highlight="highlightKey" @select="onChainSelect" />

          <!-- ② 字段明细 -->
          <h4 class="detail-section-title">{{ $t('forensics.fieldDetailsTitle') }}</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item :label="$t('forensics.fieldApplicationId')">{{ detail.application_id != null ? detail.application_id : '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldDataId')">{{ detail.data_id || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldDataType')">{{ detail.data_type || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldAlgorithm')">{{ detail.algorithm || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldFidShort')">{{ detail.fid_short || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldDownloaded')">
              {{ detail.downloaded ? $t('forensics.yes') : $t('forensics.no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldCreatedAt')">{{ detail.created_at || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldReadyAt')">{{ detail.ready_at || '—' }}</el-descriptions-item>
            <el-descriptions-item :label="$t('forensics.fieldCompletedAt')" :span="2">{{ detail.completed_at || '—' }}</el-descriptions-item>
          </el-descriptions>

          <!-- ③ 事件链：DFIR 风格时间线卡片（左侧类型色标圆点 + 竖连线） -->
          <h4 class="detail-section-title">{{ $t('forensics.eventsTitle') }}</h4>
          <div v-if="(detail.events || []).length > 0" class="event-timeline">
            <div
              v-for="(ev, idx) in detail.events"
              :key="ev.seq != null ? ev.seq : idx"
              class="event-item"
            >
              <div class="event-rail">
                <span class="event-dot" :class="eventTypeClass(ev.event_type)"></span>
                <span v-if="idx < detail.events.length - 1" class="event-rail-line"></span>
              </div>
              <div class="event-card">
                <div class="event-card-head">
                  <span class="event-type-tag" :class="eventTypeClass(ev.event_type)">{{ ev.event_type || '—' }}</span>
                  <span class="event-seq">#{{ ev.seq != null ? ev.seq : idx }}</span>
                  <span v-if="ev.kid" class="event-kid">kid {{ ev.kid }}</span>
                  <span class="event-time">{{ ev.ts || '' }}</span>
                </div>
                <div class="event-card-body">
                  <HashText :value="ev.event_hash" />
                </div>
              </div>
            </div>
          </div>
          <EmptyState v-else compact variant="never" :title="$t('forensics.noEvents')" />

          <!-- ④ 证据与锚定：链校验 + 锚定卡（provider 徽章 + Merkle 根 + 批次） -->
          <h4 class="detail-section-title">{{ $t('forensics.evidenceAnchorTitle') }}</h4>
          <div class="evidence-block">
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

            <div class="anchor-card">
              <div class="anchor-card-head">
                <span v-if="anchorProviderLabel" class="anchor-badge" :class="anchorBadgeClass">{{ anchorProviderLabel }}</span>
                <span v-else class="anchor-badge is-plain">{{ $t('forensics.anchorProvider') }}</span>
                <el-tag v-if="detail.anchor?.status" size="small" :type="statusTagType(detail.anchor.status)">
                  {{ detail.anchor.status }}
                </el-tag>
              </div>
              <div class="anchor-row">
                <span class="summary-label">{{ $t('forensics.anchorBatchId') }}</span>
                <span class="anchor-value">{{ detail.anchor?.batch_id || '—' }}</span>
              </div>
              <div class="anchor-row">
                <span class="summary-label">{{ $t('forensics.anchorRootHex') }}</span>
                <HashText :value="detail.anchor?.root_hex" />
              </div>
              <p v-if="detail.anchor?.error" class="anchor-error">{{ detail.anchor.error }}</p>
            </div>
          </div>

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
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, UploadFilled, Aim, CircleCheck, Link } from '@element-plus/icons-vue'
import HashText from '@/components/common/HashText.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import DeliveryChain from '@/components/common/DeliveryChain.vue'
import {
  verifyForensics,
  traceForensics,
  getDeliveries,
  getDeliveryDetail,
  buildAnchorBatch,
} from '@/api/forensics'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const activeTab = ref('deliveries')

// ── 交付台账（§5.16 四维检索：操作人 / 指纹 / 交付号 / 时间 —— 全部下推后端过滤）──
const queryAppId = ref(null)
const queryUser = ref('')
const queryFid = ref('')
const queryUuid = ref('')
const queryTimeRange = ref(null)
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

// §4.13 状态色带：行左 4px（仅状态类表格）
const deliveryRowClass = ({ row }) => {
  const t = statusTagType(row.status)
  return t && t !== 'info' ? `row-band-${t}` : ''
}

// 事件类型色标映射（DFIR 时间线圆点 + tag 配色；未知类型走中性色）
const EVENT_TYPE_CLASS = {
  DeliveryCreated: 'evt-created',
  FingerprintIssued: 'evt-fingerprint',
  PersonalizationCompleted: 'evt-personalization',
  DownloadCompleted: 'evt-download',
}
const eventTypeClass = (type) => EVENT_TYPE_CLASS[type] || 'evt-default'

// 锚定提供方徽章：evm-sepolia → EVM · Sepolia，opentimestamps → OTS（provider 为技术标识，不翻译）
const anchorProviderLabel = computed(() => {
  const p = String(detail.value?.anchor?.provider || '').toLowerCase()
  if (!p) return ''
  if (p.includes('evm')) return p.includes('sepolia') ? 'EVM · Sepolia' : 'EVM'
  if (p === 'ots' || p.includes('opentimestamp')) return 'OTS'
  if (p.includes('bitcoin')) return 'Bitcoin'
  return detail.value?.anchor?.provider || ''
})

const anchorBadgeClass = computed(() => {
  const p = String(detail.value?.anchor?.provider || '').toLowerCase()
  if (p.includes('evm')) return 'is-evm'
  if (p) return 'is-ots'
  return 'is-plain'
})

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
    // 四维检索全部直连后端：application_id / user_number（精确）/ fingerprint_id（短前缀）/
    // uuid（完整或前缀）/ 时间范围，可任意组合
    const params = {}
    if (queryAppId.value) params.application_id = queryAppId.value
    if (queryUser.value.trim()) params.user_number = queryUser.value.trim()
    if (queryFid.value.trim()) params.fingerprint_id = queryFid.value.trim()
    if (queryUuid.value.trim()) params.uuid = queryUuid.value.trim()
    const range = queryTimeRange.value
    if (range && range.length === 2) {
      // 台账展示的 created_at 是 UTC 墙钟（如 2026-10-06T10:55:16Z），
      // 故选择器值按 UTC 语义加 Z 后缀发送，与项目 utc_iso_z 惯例一致
      params.time_from = `${range[0]}Z`
      params.time_to = `${range[1]}Z`
    }
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
    ElMessage.error(err?.response?.data?.msg || t('forensics.fetchDeliveriesFailed'))
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
  // §5.16 可分享高亮 URL：行点击写入 uuid（保留 hl）
  router.replace({ query: { uuid: row.uuid, ...(route.query.hl ? { hl: route.query.hl } : {}) } })
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

// ── §5.16 分发链水位图（事件 → 步骤；缺失事件以虚线断链呈现；点击节点高亮并写入可分享 URL）──
const highlightKey = ref(String(route.query.hl || ''))

const chainSteps = computed(() => {
  const evs = detail.value?.events || []
  const found = (type) => evs.find((e) => e.event_type === type)
  const mk = (key, label, type, fallback = 'missing') => {
    const ev = found(type)
    return { key, label, ts: ev?.ts || null, status: ev?.ts ? 'done' : fallback }
  }
  return [
    mk('created', t('forensics.chainSteps.created'), 'DeliveryCreated'),
    mk('fingerprint', t('forensics.chainSteps.fingerprint'), 'FingerprintIssued'),
    mk('personalization', t('forensics.chainSteps.personalization'), 'PersonalizationCompleted'),
    mk('download', t('forensics.chainSteps.download'), 'DownloadCompleted', detail.value?.downloaded ? 'missing' : 'pending'),
  ]
})

const onChainSelect = (key) => {
  highlightKey.value = key
  router.replace({ query: { ...route.query, hl: key, uuid: detail.value?.uuid || undefined } })
}

// 首屏：默认查询交付台账；URL 带 uuid 时自动打开详情（可分享链接直达）
onMounted(() => {
  queryDeliveries()
  const uuid = route.query.uuid
  if (uuid) openDeliveryDetail({ uuid: String(uuid) })
})

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
  color: var(--text-primary, #303133);
  margin: 0 0 8px;
}

.subtitle {
  color: var(--text-tertiary, #909399);
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
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.query-range {
  width: 360px;
}

.query-label {
  color: var(--text-secondary, #606266);
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
  color: var(--text-primary, #303133);
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
  background: linear-gradient(135deg, var(--tint-success-bg, #f0f9eb), var(--tint-success-border, #e1f3d8));
  border: 1px solid var(--tint-success-border, #b3e19d);
  color: var(--tint-success-text, #67c23a);
}

.verify-fail {
  background: linear-gradient(135deg, var(--tint-danger-bg, #fef0f0), var(--tint-danger-border, #fde2e2));
  border: 1px solid var(--tint-danger-border, #fbc4c4);
  color: var(--tint-danger-text, #f56c6c);
}

.verify-warn {
  background: linear-gradient(135deg, var(--tint-warning-bg, #fdf6ec), var(--tint-warning-border, #faecd8));
  border: 1px solid var(--tint-warning-border, #f5dab1);
  color: var(--tint-warning-text, #e6a23c);
}

.result-desc {
  margin-bottom: 16px;
}

.locate-card {
  background: linear-gradient(135deg, var(--tint-danger-bg, #fef0f0), var(--tint-danger-border, #fde2e2));
  border: 1px solid var(--tint-danger-border, #fbc4c4);
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 16px;
}

.locate-title {
  margin: 0 0 8px;
  font-size: 16px;
  color: var(--tint-danger-text, #f56c6c);
}

.locate-line {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--tint-danger-text, #f56c6c);
}

.locate-subtitle {
  margin: 16px 0 8px;
  font-size: 14px;
  color: var(--text-primary, #303133);
}

.approval-line {
  font-size: 14px;
  color: var(--text-primary, #303133);
}

.approval-comment {
  color: var(--text-tertiary, #909399);
  font-size: 13px;
}

.result-empty-card {
  margin-bottom: 16px;
}

.disclaimer {
  margin-top: 24px;
  font-size: 12px;
  color: var(--text-tertiary, #909399);
  text-align: center;
  line-height: 1.6;
}

.detail-body {
  min-height: 120px;
}

.detail-section-title {
  margin: 20px 0 10px;
  font-size: 14px;
  color: var(--text-primary);
}

/* ── ① 摘要卡 ── */
.summary-card {
  background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary));
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.summary-id {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex-wrap: wrap;
}

.summary-status {
  flex: none;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.summary-status-empty {
  color: var(--text-tertiary);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 24px;
  margin-top: 14px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 13px;
}

.summary-item--wide {
  grid-column: 1 / -1;
}

.summary-label {
  flex: none;
  color: var(--text-secondary);
  font-size: 12px;
}

.summary-value {
  color: var(--text-primary);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── ③ 事件时间线（DFIR 风格卡片：左侧色标圆点 + 竖连线） ── */
.event-timeline {
  display: flex;
  flex-direction: column;
}

.event-item {
  display: flex;
  gap: 10px;
}

.event-rail {
  position: relative;
  flex: none;
  width: 12px;
  display: flex;
  justify-content: center;
}

.event-dot {
  position: relative;
  z-index: 1;
  width: 10px;
  height: 10px;
  margin-top: 15px;
  border-radius: 50%;
  background: var(--text-tertiary);
  box-shadow: 0 0 0 3px var(--bg-primary);
}

.event-rail-line {
  position: absolute;
  top: 27px;
  bottom: -12px;
  left: calc(50% - 1px);
  width: 2px;
  background: var(--border-color);
}

.event-card {
  flex: 1;
  min-width: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  margin-bottom: 12px;
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.event-item:last-child .event-card {
  margin-bottom: 0;
}

.event-card:hover {
  border-color: var(--primary-200);
  box-shadow: var(--shadow-sm);
}

.event-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.event-type-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.event-type-tag.evt-created { background: var(--primary-50); color: var(--primary-600); }
.event-type-tag.evt-fingerprint { background: var(--neutral-100); color: var(--neutral-700); }
.event-type-tag.evt-personalization { background: var(--success-50); color: var(--success-600); }
.event-type-tag.evt-download { background: var(--warning-50); color: var(--warning-600); }

.event-dot.evt-created { background: var(--primary-500); }
.event-dot.evt-fingerprint { background: var(--neutral-500); }
.event-dot.evt-personalization { background: var(--success-500); }
.event-dot.evt-download { background: var(--warning-500); }

.event-seq {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.event-kid {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* 事件时间等宽显示 */
.event-time {
  margin-left: auto;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
  font-size: 12px;
  color: var(--text-secondary);
}

.event-card-body {
  margin-top: 8px;
}

/* ── ④ 证据与锚定 ── */
.evidence-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chain-line {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--text-secondary);
}

.anchor-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 12px 14px;
}

.anchor-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.anchor-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.3px;
}

.anchor-badge.is-evm {
  background: var(--primary-50);
  color: var(--primary-700);
}

.anchor-badge.is-ots {
  background: var(--warning-50);
  color: var(--warning-600);
}

.anchor-badge.is-plain {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.anchor-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  font-size: 13px;
  margin-top: 6px;
}

.anchor-value {
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.anchor-error {
  color: var(--danger-500);
  font-size: 13px;
  margin: 8px 0 0;
  word-break: break-all;
}

.dialog-actions {
  margin-top: 16px;
  text-align: right;
}
</style>
