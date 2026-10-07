<template>
  <div class="anchor-center">
    <div class="page-header">
      <div class="page-header-text">
        <h2>{{ $t('anchorCenter.title') }}</h2>
        <p class="subtitle">{{ $t('anchorCenter.subtitle') }}</p>
      </div>
      <div class="page-header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="fetchAnchors">{{ $t('anchorCenter.refreshBtn') }}</el-button>
        <el-button type="primary" :icon="Plus" @click="buildVisible = true">{{ $t('anchorCenter.buildBtn') }}</el-button>
      </div>
    </div>

    <!-- Hero 统计带：整表聚合（summary），不是当前页聚合 -->
    <div class="hero-band">
      <div class="hero-card">
        <span class="hero-value">{{ stats.total }}</span>
        <span class="hero-label">{{ $t('anchorCenter.statTotal') }}</span>
      </div>
      <div class="hero-card">
        <span class="hero-value">{{ stats.ots }}</span>
        <span class="hero-label">{{ $t('anchorCenter.statOts') }}</span>
      </div>
      <div class="hero-card">
        <span class="hero-value">{{ stats.evm }}</span>
        <span class="hero-label">{{ $t('anchorCenter.statEvm') }}</span>
      </div>
      <div class="hero-card" :class="{ 'is-alert': stats.pending > 0 }">
        <span class="hero-value">{{ stats.pending }}</span>
        <span class="hero-label">{{ $t('anchorCenter.statPending') }}</span>
      </div>
    </div>

    <!-- 双链说明卡：讲清架构 + 状态含义 + 诚实边界 -->
    <div class="chain-grid">
      <section class="chain-card">
        <div class="chain-card-head">
          <span class="anchor-badge is-ots">{{ $t('anchorCenter.chainOtsName') }}</span>
        </div>
        <p class="chain-desc">{{ $t('anchorCenter.chainOtsDesc') }}</p>
        <div class="state-legend">
          <el-tag size="small" type="warning">{{ $t('anchorCenter.statePending') }}</el-tag>
          <el-tag size="small" type="success">{{ $t('anchorCenter.stateSubmitted') }}</el-tag>
          <el-tag size="small" type="success">{{ $t('anchorCenter.stateReady') }}</el-tag>
          <el-tag size="small" type="success">{{ $t('anchorCenter.stateConfirmed') }}</el-tag>
        </div>
        <p class="chain-honest">{{ $t('anchorCenter.chainOtsHonest') }}</p>
      </section>
      <section class="chain-card">
        <div class="chain-card-head">
          <span class="anchor-badge is-evm">{{ $t('anchorCenter.chainEvmName') }}</span>
        </div>
        <p class="chain-desc">{{ $t('anchorCenter.chainEvmDesc') }}</p>
        <div class="state-legend">
          <el-tag size="small" type="warning">{{ $t('anchorCenter.statePending') }}</el-tag>
          <el-tag size="small" type="success">{{ $t('anchorCenter.stateSubmitted') }}</el-tag>
          <el-tag size="small" type="success">{{ $t('anchorCenter.stateReady') }}</el-tag>
          <el-tag size="small" type="success">{{ $t('anchorCenter.stateConfirmed') }}</el-tag>
        </div>
        <p class="chain-honest">{{ $t('anchorCenter.chainEvmHonest') }}</p>
      </section>
    </div>

    <!-- 批次台账 -->
    <el-card shadow="never" class="ledger-card">
      <h4 class="ledger-title">{{ $t('anchorCenter.ledgerTitle') }}</h4>
      <el-table
        v-loading="loading"
        :data="anchors"
        stripe
        class="ledger-table"
        :row-class-name="ledgerRowClass"
        @row-click="openDetail"
      >
        <el-table-column :label="$t('anchorCenter.colBatchId')" width="150">
          <template #default="{ row }">
            <HashText :value="row.batch_id" />
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="$t('anchorCenter.colCreatedAt')" width="180" />
        <el-table-column :label="$t('anchorCenter.colProvider')" width="120">
          <template #default="{ row }">
            <span class="anchor-badge" :class="providerBadgeClass(row.provider)">{{ providerLabel(row.provider) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('anchorCenter.colStatus')" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.status" size="small" :type="statusTagType(row.status)">{{ row.status }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('anchorCenter.colRootHex')" min-width="150">
          <template #default="{ row }">
            <HashText :value="row.root_hex" />
          </template>
        </el-table-column>
        <el-table-column :label="$t('anchorCenter.colEventCount')" width="90" align="right">
          <template #default="{ row }">
            <span class="mono">{{ row.event_count != null ? row.event_count : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('anchorCenter.colProof')" width="100" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.proof_available"
              size="small"
              link
              type="primary"
              :icon="Download"
              @click.stop="downloadProof(row)"
            >
              {{ $t('anchorCenter.downloadProofBtn') }}
            </el-button>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('anchorCenter.colExplorer')" width="110" align="center">
          <template #default="{ row }">
            <a
              v-if="row.explorer_url"
              :href="row.explorer_url"
              target="_blank"
              rel="noopener noreferrer"
              class="explorer-link"
              @click.stop
            >
              <el-icon><Link /></el-icon>
              {{ $t('anchorCenter.explorerLink') }}
            </a>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <template #empty>
          <EmptyState
            variant="never"
            :title="$t('anchorCenter.empty')"
            :description="$t('common.noDataDesc')"
            :cta-text="$t('anchorCenter.buildBtn')"
            @cta="buildVisible = true"
          />
        </template>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          background
          layout="total, sizes, prev, pager, next"
          @current-change="fetchAnchors"
          @size-change="onSizeChange"
        />
      </div>
    </el-card>

    <!-- 构建锚定批次 -->
    <el-dialog v-model="buildVisible" :title="$t('anchorCenter.buildTitle')" width="480px">
      <el-radio-group v-model="buildProvider" class="provider-group">
        <el-radio value="ots" border class="provider-radio">
          <div class="provider-radio-title">{{ $t('anchorCenter.buildProviderOts') }}</div>
          <div class="provider-radio-hint">{{ $t('anchorCenter.buildProviderOtsHint') }}</div>
        </el-radio>
        <el-radio value="evm" border class="provider-radio">
          <div class="provider-radio-title">{{ $t('anchorCenter.buildProviderEvm') }}</div>
          <div class="provider-radio-hint">{{ $t('anchorCenter.buildProviderEvmHint') }}</div>
        </el-radio>
      </el-radio-group>
      <p class="build-hint">{{ $t('anchorCenter.buildHint') }}</p>
      <template #footer>
        <el-button @click="buildVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="building" @click="submitBuild">
          {{ $t('anchorCenter.buildConfirm') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 批次详情 -->
    <el-dialog v-model="detailVisible" :title="$t('anchorCenter.detailTitle')" width="720px">
      <div v-loading="detailLoading" class="detail-body">
        <template v-if="detail">
          <section class="summary-card">
            <div class="summary-head">
              <div class="summary-id">
                <span class="summary-label">{{ $t('anchorCenter.fieldBatchId') }}</span>
                <HashText :value="detail.batch_id" :head="18" :tail="17" />
              </div>
              <el-tag v-if="detail.status" size="large" effect="dark" :type="statusTagType(detail.status)">
                {{ detail.status }}
              </el-tag>
            </div>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="summary-label">{{ $t('anchorCenter.fieldProvider') }}</span>
                <span class="anchor-badge" :class="providerBadgeClass(detail.provider)">{{ providerLabel(detail.provider) }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">{{ $t('anchorCenter.fieldEventCount') }}</span>
                <span class="mono">{{ detail.event_count != null ? detail.event_count : '—' }}</span>
              </div>
              <div class="summary-item summary-item--wide">
                <span class="summary-label">{{ $t('anchorCenter.fieldRootHex') }}</span>
                <HashText :value="detail.root_hex" />
              </div>
              <div class="summary-item summary-item--wide">
                <span class="summary-label">{{ $t('anchorCenter.fieldHeadHash') }}</span>
                <HashText :value="detail.head_hash" />
              </div>
            </div>
          </section>

          <h4 class="detail-section-title">{{ $t('anchorCenter.timelineTitle') }}</h4>
          <div class="time-axis">
            <span class="time-chip">
              <span class="time-chip-label">{{ $t('anchorCenter.fieldCreatedAt') }}</span>
              <span class="mono">{{ detail.created_at || '—' }}</span>
            </span>
            <span class="time-arrow">→</span>
            <span class="time-chip">
              <span class="time-chip-label">{{ $t('anchorCenter.fieldUpdatedAt') }}</span>
              <span class="mono">{{ detail.updated_at || '—' }}</span>
            </span>
          </div>

          <h4 class="detail-section-title">{{ $t('anchorCenter.digestTitle') }}</h4>
          <p class="digest-note">{{ $t('anchorCenter.digestSemantics') }}</p>
          <div class="summary-item">
            <span class="summary-label">{{ $t('anchorCenter.digestIncluded') }}</span>
            <span class="mono">{{ digestCount }}</span>
          </div>

          <template v-if="detail.proof_sha256">
            <h4 class="detail-section-title">{{ $t('anchorCenter.fieldProofSha') }}</h4>
            <HashText :value="detail.proof_sha256" />
          </template>

          <p v-if="detail.error" class="anchor-error">{{ $t('anchorCenter.fieldError') }}: {{ detail.error }}</p>

          <div class="dialog-actions">
            <el-button
              v-if="detail.proof_available"
              type="primary"
              :icon="Download"
              @click="downloadProof(detail)"
            >
              {{ $t('anchorCenter.downloadProofBtn') }}
            </el-button>
            <el-button
              v-if="detail.explorer_url"
              tag="a"
              :href="detail.explorer_url"
              target="_blank"
              rel="noopener noreferrer"
              :icon="Link"
            >
              {{ $t('anchorCenter.explorerLink') }}
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
import { ElMessage } from 'element-plus'
import { Plus, Download, Refresh, Link } from '@element-plus/icons-vue'
import HashText from '@/components/common/HashText.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { getAnchors, getAnchorDetail, buildAnchorBatch, downloadAnchorProof } from '@/api/forensics'

const { t } = useI18n()

// ── 台账列表 ──
const anchors = ref([])
const summary = ref(null)
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// ── Hero 统计：来自整表聚合的 summary（不随分页变化）──
const stats = computed(() => {
  const s = summary.value || {}
  const byProvider = s.by_provider || {}
  const byStatus = s.by_status || {}
  return {
    total: s.total || 0,
    ots: byProvider['opentimestamps'] || 0,
    evm: byProvider['evm-sepolia'] || byProvider['evm_sepolia'] || 0,
    pending: byStatus['PENDING'] || byStatus['pending'] || 0
  }
})

// ── 构建对话框 ──
const buildVisible = ref(false)
const buildProvider = ref('ots')
const building = ref(false)

// ── 详情弹窗 ──
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

const digestCount = computed(() => {
  const d = detail.value?.events_digest
  if (d && d.included_event_count != null) return d.included_event_count
  return detail.value?.event_count != null ? detail.value.event_count : '—'
})

// 提供方徽章：provider 是技术标识，不翻译（与 Forensics 页一致）
const providerLabel = (provider) => {
  const p = String(provider || '').toLowerCase()
  if (!p) return '—'
  if (p.includes('evm')) return p.includes('sepolia') ? 'EVM · Sepolia' : 'EVM'
  if (p === 'ots' || p.includes('opentimestamp')) return 'OTS'
  if (p.includes('bitcoin')) return 'Bitcoin'
  return provider
}

const providerBadgeClass = (provider) => {
  const p = String(provider || '').toLowerCase()
  if (p.includes('evm')) return 'is-evm'
  if (p) return 'is-ots'
  return 'is-plain'
}

const statusTagType = (value) => {
  const s = String(value || '').toUpperCase()
  if (!s) return 'info'
  if (s === 'CONFIRMED' || s === 'PROOF_READY' || s === 'SUBMITTED') return 'success'
  if (s === 'PENDING') return 'warning'
  if (s.includes('FAIL') || s.includes('ERROR')) return 'danger'
  return 'info'
}

// §4.13 状态色带：行左 4px（仅状态类表格）
const ledgerRowClass = ({ row }) => {
  const t = statusTagType(row.status)
  return t && t !== 'info' ? `row-band-${t}` : ''
}

const fetchAnchors = async () => {
  loading.value = true
  try {
    const res = await getAnchors({ page: page.value, page_size: pageSize.value })
    const body = res?.data
    if (!body?.status) {
      ElMessage.error(body?.msg || t('anchorCenter.fetchFailed'))
      return
    }
    anchors.value = body.anchors || []
    summary.value = body.summary || null
    total.value = body.pages?.total || 0
  } catch (err) {
    console.error('Anchor ledger fetch failed:', err)
    ElMessage.error(t('anchorCenter.fetchFailed'))
  } finally {
    loading.value = false
  }
}

const onSizeChange = () => {
  page.value = 1
  fetchAnchors()
}

const submitBuild = async () => {
  building.value = true
  try {
    const res = await buildAnchorBatch({ provider: buildProvider.value })
    const body = res?.data
    const batch = body?.batch
    if (body?.status && batch) {
      if (String(batch.status || '').toUpperCase() === 'SUBMITTED') {
        ElMessage.success(t('anchorCenter.buildSuccess'))
      } else {
        // 诚实提示：批次已记录，但提供方尚未返回证明（如 EVM 未配置/网络失败）
        ElMessage.warning(t('anchorCenter.buildPending', { error: batch.error || '—' }))
      }
      buildVisible.value = false
      page.value = 1
      await fetchAnchors()
    } else {
      ElMessage.error(body?.msg || t('anchorCenter.buildFailed'))
    }
  } catch (err) {
    console.error('Anchor batch build failed:', err)
    ElMessage.error(err?.response?.data?.msg || t('anchorCenter.buildFailed'))
  } finally {
    building.value = false
  }
}

const openDetail = async (row) => {
  if (!row?.batch_id) return
  detailVisible.value = true
  detail.value = row
  detailLoading.value = true
  try {
    const res = await getAnchorDetail(row.batch_id)
    const body = res?.data
    if (body?.status && body.anchor) {
      detail.value = { ...body.anchor, events_digest: body.events_digest || null }
    } else {
      ElMessage.error(body?.msg || t('anchorCenter.detailFailed'))
    }
  } catch (err) {
    console.error('Anchor detail fetch failed:', err)
    ElMessage.error(t('anchorCenter.detailFailed'))
  } finally {
    detailLoading.value = false
  }
}

const downloadProof = async (row) => {
  try {
    const res = await downloadAnchorProof(row.batch_id)
    // 文件名优先取服务端 Content-Disposition（同源代理下可读），回退按 provider 推断
    const cd = res?.headers?.['content-disposition'] || ''
    const match = /filename="?([^";]+)"?/i.exec(cd)
    let filename = match ? decodeURIComponent(match[1]) : ''
    if (!filename) {
      const isJson = String(row.provider || '').toLowerCase().includes('evm')
      filename = isJson ? `${row.batch_id}.proof.json` : `${row.batch_id}.ots`
    }
    const url = URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Anchor proof download failed:', err)
    ElMessage.error(t('anchorCenter.downloadFailed'))
  }
}

onMounted(fetchAnchors)
</script>

<style scoped>
.anchor-center {
  padding: 4px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 24px;
  color: var(--text-primary);
  margin: 0 0 8px;
}

.subtitle {
  color: var(--text-tertiary);
  font-size: 14px;
  margin: 0;
}

.page-header-actions {
  display: flex;
  gap: 10px;
}

/* ── Hero 统计带 ── */
.hero-band {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.hero-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  background: linear-gradient(135deg, var(--bg-secondary), var(--bg-tertiary));
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 14px 18px;
}

.hero-card.is-alert {
  border-color: var(--warning-500);
}

.hero-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.hero-label {
  font-size: 13px;
  color: var(--text-secondary);
}

/* ── 双链说明卡 ── */
.chain-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

@media (max-width: 900px) {
  .chain-grid {
    grid-template-columns: 1fr;
  }
}

.chain-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
}

.chain-card-head {
  margin-bottom: 10px;
}

.chain-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 10px;
}

.state-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}

.chain-honest {
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.6;
  margin: 0;
  border-top: 1px dashed var(--border-color);
  padding-top: 10px;
}

/* ── 台账 ── */
.ledger-card {
  border-radius: var(--radius-lg);
}

.ledger-title {
  margin: 0 0 12px;
  font-size: 15px;
  color: var(--text-primary);
}

.ledger-table {
  width: 100%;
}

:deep(.ledger-table .el-table__row) {
  cursor: pointer;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
  font-size: 13px;
  color: var(--text-primary);
}

.muted {
  color: var(--text-tertiary);
}

.explorer-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--primary-600);
  font-size: 13px;
  text-decoration: none;
}

.explorer-link:hover {
  text-decoration: underline;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

/* ── 构建对话框 ── */
.provider-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.provider-radio {
  width: 100%;
  height: auto;
  margin-right: 0;
  padding: 10px 14px;
  align-items: flex-start;
}

.provider-radio-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.5;
}

.provider-radio-hint {
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.5;
  white-space: normal;
}

.build-hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.6;
}

/* ── 详情弹窗 ── */
.detail-body {
  min-height: 120px;
}

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

.detail-section-title {
  margin: 20px 0 10px;
  font-size: 14px;
  color: var(--text-primary);
}

.time-axis {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.time-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 6px 12px;
}

.time-chip-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.time-arrow {
  color: var(--text-tertiary);
}

.digest-note {
  font-size: 12px;
  color: var(--text-tertiary);
  line-height: 1.6;
  margin: 0 0 8px;
}

.anchor-error {
  color: var(--danger-500);
  font-size: 13px;
  margin: 16px 0 0;
  word-break: break-all;
}

.dialog-actions {
  margin-top: 16px;
  text-align: right;
}

/* 徽章样式与 Forensics 页保持一致 */
.anchor-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.3px;
  white-space: nowrap;
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
</style>
