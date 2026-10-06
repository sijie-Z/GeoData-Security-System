<!--
  RobustnessLab — 鲁棒性实验室（管理员）
  把已落库的鲁棒性实验矩阵做成可见产品面：
    区一 说明卡：攻击矩阵方法论（WAVES 式单失真攻击 + 判定指标）与文档化边界
    区二 运行控制 + 历史：发起新实验（矢量数据 × 方案 × 攻击），历史 run 列表
    区三 结果矩阵：行 = 方案，列 = 攻击；NC 色阶 / ✗ 解码失败；对比结论卡
    区四 对比图：分组柱状图（两方案 NC 按攻击对比）
  数据源：GET /api/robustness/runs（列表）、GET /api/robustness/runs/<id>（详情 + 进度轮询）
-->
<template>
  <div class="robustness-lab fade-in">
    <!-- 页头 -->
    <div class="page-header">
      <div class="page-header-text">
        <h2>{{ $t('robustnessLab.title') }}</h2>
        <p class="subtitle">{{ $t('robustnessLab.subtitle') }}</p>
      </div>
      <div class="page-header-actions">
        <el-button :icon="Refresh" :loading="runsLoading && detailLoading" @click="refreshAll">
          {{ $t('robustnessLab.refreshBtn') }}
        </el-button>
      </div>
    </div>

    <!-- 区一 · 说明卡（方法论，诚实边界） -->
    <el-card shadow="never" class="method-card">
      <h4 class="card-title">{{ $t('robustnessLab.methodTitle') }}</h4>
      <p class="method-desc">{{ $t('robustnessLab.methodDesc') }}</p>
      <div class="method-grid">
        <div class="method-item">
          <span class="method-label">{{ $t('robustnessLab.methodSchemesLabel') }}</span>
          <span class="method-text">{{ $t('robustnessLab.methodSchemes') }}</span>
        </div>
        <div class="method-item">
          <span class="method-label">{{ $t('robustnessLab.methodAttacksLabel') }}</span>
          <span class="method-text">{{ $t('robustnessLab.methodAttacks') }}</span>
        </div>
        <div class="method-item">
          <span class="method-label">{{ $t('robustnessLab.methodMetricsLabel') }}</span>
          <span class="method-text">{{ $t('robustnessLab.methodMetrics') }}</span>
        </div>
      </div>
      <div class="boundary-note">
        <el-icon class="boundary-icon"><InfoFilled /></el-icon>
        <span>{{ $t('robustnessLab.methodBoundary') }}</span>
      </div>
    </el-card>

    <!-- 区二 · 运行控制 + 历史 -->
    <div class="control-grid">
      <el-card shadow="never" class="run-card">
        <h4 class="card-title">{{ $t('robustnessLab.runTitle') }}</h4>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.dataLabel') }}</label>
          <el-select
            v-model="selectedDataId"
            class="data-select"
            filterable
            clearable
            :loading="dataLoading"
            :placeholder="$t('robustnessLab.dataPlaceholder')"
          >
            <el-option
              v-for="d in vectorDataList"
              :key="d.data_id"
              :label="dataOptionLabel(d)"
              :value="d.data_id"
            />
          </el-select>
        </div>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.dataIdLabel') }}</label>
          <el-input-number
            v-model="manualDataId"
            class="data-id-input"
            :min="1"
            :step="1"
            :controls="false"
            placeholder="data_id"
          />
        </div>
        <p class="form-hint">{{ $t('robustnessLab.dataIdHint') }}</p>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.schemesLabel') }}</label>
          <el-checkbox-group v-model="selectedSchemes" class="check-group">
            <el-checkbox v-for="s in SCHEMES" :key="s" :value="s" class="check-item">
              {{ $t(`robustnessLab.scheme.${s}`) }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.attacksLabel') }}</label>
          <el-checkbox-group v-model="selectedAttacks" class="check-group">
            <el-checkbox v-for="a in ATTACKS" :key="a" :value="a" class="check-item">
              {{ $t(`robustnessLab.attack.${a}`) }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <el-button
          type="primary"
          class="start-btn"
          :icon="VideoPlay"
          :loading="startLoading"
          @click="startRun"
        >
          {{ $t('robustnessLab.startBtn') }}
        </el-button>
      </el-card>

      <el-card shadow="never" class="history-card">
        <h4 class="card-title">{{ $t('robustnessLab.historyTitle') }}</h4>
        <el-table
          v-loading="runsLoading"
          :data="runs"
          size="small"
          class="history-table"
          :empty-text="$t('robustnessLab.historyEmpty')"
          highlight-current-row
          :row-class-name="historyRowClass"
          @row-click="onRunRowClick"
        >
          <el-table-column :label="$t('robustnessLab.colRunId')" min-width="130">
            <template #default="{ row }">
              <HashText :value="row.run_id" :head="8" :tail="4" />
            </template>
          </el-table-column>
          <el-table-column :label="$t('robustnessLab.colDataRef')" min-width="100">
            <template #default="{ row }">
              <span class="mono-text">{{ row.data_ref }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('robustnessLab.colCreatedAt')" min-width="150">
            <template #default="{ row }">
              <span class="mono-text">{{ formatTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('robustnessLab.colProgress')" width="90" align="center">
            <template #default="{ row }">
              <span class="mono-text">{{ row.done }}/{{ row.total }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('robustnessLab.colStatus')" width="96" align="center">
            <template #default="{ row }">
              <span class="status-badge" :class="runStatusClass(row)">{{ runStatusText(row) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 区三 · 结果矩阵 -->
    <el-card v-loading="detailLoading" shadow="never" class="matrix-card">
      <template v-if="runMeta">
        <div class="matrix-head">
          <div class="matrix-meta">
            <h4 class="card-title inline-title">{{ $t('robustnessLab.matrixTitle') }}</h4>
            <HashText :value="runMeta.run_id" :head="8" :tail="4" />
            <span class="meta-sep">·</span>
            <span class="mono-text">{{ runMeta.data_ref }}</span>
            <span class="meta-sep">·</span>
            <span class="mono-text">{{ formatTime(runMeta.created_at) }}</span>
          </div>
          <div class="matrix-actions">
            <div v-if="!matrixDone" class="progress-inline">
              <el-progress :percentage="progressPct" :stroke-width="8" :show-text="false" class="progress-bar" />
              <span class="mono-text progress-text">{{ runMeta.done }}/{{ runMeta.total }}</span>
            </div>
            <el-button size="small" :icon="Download" @click="exportJson">
              {{ $t('robustnessLab.exportBtn') }}
            </el-button>
            <el-button size="small" :icon="Refresh" @click="loadRun(runMeta.run_id)">
              {{ $t('robustnessLab.refreshBtn') }}
            </el-button>
          </div>
        </div>

        <p class="matrix-subtitle">{{ $t('robustnessLab.matrixSubtitle') }}</p>

        <el-table :data="matrixRows" border class="matrix-table">
          <el-table-column :label="$t('robustnessLab.colScheme')" width="190" fixed>
            <template #default="{ row }">
              <span class="scheme-name" :class="`is-${row.scheme}`">
                {{ $t(`robustnessLab.scheme.${row.scheme}`) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            v-for="(attack, idx) in matrixAttacks"
            :key="attack"
            :label="$t(`robustnessLab.attack.${attack}`)"
            align="center"
            min-width="110"
          >
            <template #default="{ row }">
              <el-tooltip
                v-if="row.cells[idx] && row.cells[idx].decode_success !== null"
                placement="top"
                effect="dark"
                :show-after="120"
              >
                <template #content>
                  <div class="cell-tip">
                    <div>{{ $t('robustnessLab.tipParams') }}: {{ formatParams(row.cells[idx].attack_params) }}</div>
                    <div>BER: {{ formatBer(row.cells[idx].ber) }}</div>
                    <div>{{ $t('robustnessLab.tipDuration') }}: {{ formatDuration(row.cells[idx].duration_ms) }}</div>
                  </div>
                </template>
                <span class="cell-value" :class="cellClass(row.cells[idx])">{{ cellText(row.cells[idx]) }}</span>
              </el-tooltip>
              <span v-else class="cell-value is-pending">{{ $t('robustnessLab.cellPending') }}</span>
            </template>
          </el-table-column>
        </el-table>

        <!-- 对比结论卡（自动生成，数字来自数据） -->
        <div class="verdict-card" :class="{ 'is-ready': verdictReady }">
          <div class="verdict-head">
            <h4 class="verdict-title">{{ $t('robustnessLab.verdictTitle') }}</h4>
            <span v-if="!verdictReady" class="mono-text verdict-progress">{{ runMeta.done }}/{{ runMeta.total }}</span>
          </div>
          <template v-if="verdictReady">
            <p v-for="(sentence, i) in verdictSentences" :key="i" class="verdict-line">{{ sentence }}</p>
          </template>
          <p v-else class="verdict-line is-muted">
            {{ $t('robustnessLab.verdictPending', { done: runMeta.done, total: runMeta.total }) }}
          </p>
          <div class="verdict-tags">
            <span
              v-for="item in verdictItems"
              :key="item.attack"
              class="verdict-tag"
              :class="`is-${item.kind}`"
            >
              {{ $t(`robustnessLab.attack.${item.attack}`) }} · {{ tagText(item.kind) }}
            </span>
          </div>
        </div>
      </template>
      <el-empty
        v-else
        :description="$t('robustnessLab.noRun')"
        :image-size="90"
      />
    </el-card>

    <!-- 区四 · 对比图 -->
    <el-card v-if="runMeta" shadow="never" class="chart-card">
      <h4 class="card-title">{{ $t('robustnessLab.chartTitle') }}</h4>
      <v-chart class="chart-holder" :option="comparisonChartOption" autoresize />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Download, InfoFilled, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

import HashText from '@/components/common/HashText.vue'
import { getDataList } from '@/api/upload'
import { getRobustnessRun, getRobustnessRuns, startRobustnessRun } from '@/api/robustness'

// ── ECharts 按需注册：本页只用到柱状图 ──
use([CanvasRenderer, BarChart, TooltipComponent, LegendComponent, GridComponent])

const { t } = useI18n()

// 与后端白名单同名同序（schemes 决定矩阵行、attacks 决定矩阵列）
const SCHEMES = ['legacy', 'dqim1']
const ATTACKS = ['none', 'translate', 'scale', 'vertex_drop', 'noise', 'simplify']

const POLL_INTERVAL_MS = 5000

// ── 运行控制状态 ──
const vectorDataList = ref([])
const dataLoading = ref(false)
const selectedDataId = ref(null)
const manualDataId = ref(null)
const selectedSchemes = ref([...SCHEMES])
const selectedAttacks = ref([...ATTACKS])
const startLoading = ref(false)

// ── 历史列表状态 ──
const runs = ref([])
const runsLoading = ref(false)

// ── 当前 run（矩阵 + 结论 + 图表）状态 ──
const runMeta = ref(null)
const runRows = ref([])
const detailLoading = ref(false)
let pollTimer = null

// ──────────────────────────────────────
//  数据获取
// ──────────────────────────────────────

const fetchVectorData = async () => {
  dataLoading.value = true
  try {
    const res = await getDataList('vector', { page: 1, pageSize: 100 })
    const body = res.data
    if (body?.status) vectorDataList.value = body.data?.list || []
  } catch {
    // 矢量列表拉取失败不阻断：仍可手填 data_id
  } finally {
    dataLoading.value = false
  }
}

const fetchRuns = async () => {
  runsLoading.value = true
  try {
    const res = await getRobustnessRuns({ page: 1, per_page: 20 })
    const body = res.data
    if (body?.status) {
      runs.value = body.runs || []
    } else {
      ElMessage.error(body?.msg || t('robustnessLab.historyLoadFailed'))
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || t('robustnessLab.historyLoadFailed'))
  } finally {
    runsLoading.value = false
  }
}

const applyRunPayload = (run) => {
  runMeta.value = {
    run_id: run.run_id,
    data_ref: run.data_ref,
    created_at: run.created_at,
    done: run.done,
    total: run.total,
  }
  runRows.value = Array.isArray(run.rows) ? run.rows : []
}

const loadRun = async (runId) => {
  if (!runId) return
  detailLoading.value = true
  try {
    const res = await getRobustnessRun(runId)
    const body = res.data
    if (body?.status && body.run) {
      applyRunPayload(body.run)
      if (body.run.done < body.run.total) startPolling()
      else stopPolling()
    } else {
      ElMessage.error(body?.msg || t('robustnessLab.matrixLoadFailed'))
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || t('robustnessLab.matrixLoadFailed'))
  } finally {
    detailLoading.value = false
  }
}

// ── 轮询：实验进行中每 5s 刷新进度，完成后自动停止并刷新历史 ──
const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(pollTick, POLL_INTERVAL_MS)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const pollTick = async () => {
  const runId = runMeta.value?.run_id
  if (!runId) {
    stopPolling()
    return
  }
  try {
    const res = await getRobustnessRun(runId)
    const run = res.data?.run
    if (!run) return
    applyRunPayload(run)
    if (run.done >= run.total) {
      stopPolling()
      fetchRuns()
    }
  } catch {
    // 单次轮询失败静默，下一个周期重试
  }
}

onBeforeUnmount(stopPolling)

// ──────────────────────────────────────
//  发起实验
// ──────────────────────────────────────

const resolvedDataId = computed(() => {
  const raw = manualDataId.value ?? selectedDataId.value
  return raw === null || raw === undefined || raw === '' ? null : Number(raw)
})

const startRun = async () => {
  const dataId = resolvedDataId.value
  if (dataId === null) {
    ElMessage.warning(t('robustnessLab.dataRequired'))
    return
  }
  if (!Number.isInteger(dataId) || dataId <= 0) {
    ElMessage.warning(t('robustnessLab.dataIdInvalid'))
    return
  }
  if (!selectedSchemes.value.length || !selectedAttacks.value.length) {
    ElMessage.warning(t('robustnessLab.comboRequired'))
    return
  }

  startLoading.value = true
  try {
    const res = await startRobustnessRun({
      data_id: dataId,
      schemes: [...selectedSchemes.value],
      attacks: [...selectedAttacks.value],
    })
    const body = res.data
    if (body?.status && body.data?.run_id) {
      ElMessage.success(t('robustnessLab.startOk', { total: body.data.total }))
      await fetchRuns()
      await loadRun(body.data.run_id)
    } else {
      ElMessage.error(body?.msg || t('robustnessLab.startFailed'))
    }
  } catch (e) {
    if (e.response?.status === 409) {
      ElMessage.warning(e.response?.data?.msg || t('robustnessLab.startBusy'))
    } else {
      ElMessage.error(e.response?.data?.msg || t('robustnessLab.startFailed'))
    }
  } finally {
    startLoading.value = false
  }
}

// ──────────────────────────────────────
//  历史列表
// ──────────────────────────────────────

const onRunRowClick = (row) => {
  loadRun(row.run_id)
}

const runStatusText = (row) => {
  if (row.error && row.done < row.total) return t('robustnessLab.statusError')
  if (row.total > 0 && row.done >= row.total) return t('robustnessLab.statusDone')
  return t('robustnessLab.statusRunning')
}

const runStatusClass = (row) => {
  if (row.error && row.done < row.total) return 'is-error'
  if (row.total > 0 && row.done >= row.total) return 'is-done'
  return 'is-running'
}

const historyRowClass = ({ row }) =>
  runMeta.value && row.run_id === runMeta.value.run_id ? 'is-active-row' : ''

const refreshAll = async () => {
  await fetchRuns()
  if (runMeta.value) await loadRun(runMeta.value.run_id)
}

// ──────────────────────────────────────
//  结果矩阵
// ──────────────────────────────────────

// 该 run 实际包含的列（按白名单顺序）；行固定按 scheme 顺序
const matrixAttacks = computed(() => {
  const present = new Set(runRows.value.map((r) => r.attack))
  return ATTACKS.filter((a) => present.has(a))
})

const matrixRows = computed(() => {
  const byScheme = {}
  for (const r of runRows.value) {
    if (!byScheme[r.scheme]) byScheme[r.scheme] = {}
    byScheme[r.scheme][r.attack] = r
  }
  const presentSchemes = SCHEMES.filter((s) => byScheme[s])
  return presentSchemes.map((scheme) => ({
    scheme,
    cells: matrixAttacks.value.map((a) => byScheme[scheme][a] || null),
  }))
})

// `null` 单元格 = rows 里还没有该组合的行（理论不出现）；null 指标 = 等待中
const cellClass = (cell) => {
  if (!cell || cell.decode_success === null) return 'is-pending'
  if (!cell.decode_success) return 'is-fail'
  if (Number(cell.nc) >= 0.95) return 'is-high'
  if (Number(cell.nc) >= 0.75) return 'is-mid'
  return 'is-low'
}

const cellText = (cell) => {
  if (!cell || cell.decode_success === null) return t('robustnessLab.cellPending')
  if (!cell.decode_success) return t('robustnessLab.cellFailed')
  return Number(cell.nc).toFixed(4)
}

const matrixDone = computed(() => !!runMeta.value && runMeta.value.done >= runMeta.value.total)

const progressPct = computed(() => {
  if (!runMeta.value || !runMeta.value.total) return 0
  return Math.min(100, Math.round((runMeta.value.done / runMeta.value.total) * 100))
})

// ── 对比结论（全部来自数据） ──

const verdictItems = computed(() => {
  const byScheme = {}
  for (const r of runRows.value) {
    if (!byScheme[r.scheme]) byScheme[r.scheme] = {}
    byScheme[r.scheme][r.attack] = r
  }
  return matrixAttacks.value.map((attack) => {
    const legacy = byScheme.legacy?.[attack]
    const dqim = byScheme.dqim1?.[attack]
    if (!legacy || !dqim || legacy.decode_success === null || dqim.decode_success === null) {
      return { attack, kind: 'pending' }
    }
    if (!legacy.decode_success && dqim.decode_success) return { attack, kind: 'improved' }
    if (legacy.decode_success && !dqim.decode_success) return { attack, kind: 'regressed' }
    if (legacy.decode_success && dqim.decode_success) return { attack, kind: 'same-pass' }
    return { attack, kind: 'same-fail' }
  })
})

const verdictReady = computed(
  () => matrixDone.value && verdictItems.value.length > 0 && verdictItems.value.every((i) => i.kind !== 'pending')
)

const verdictSentences = computed(() => {
  const items = verdictItems.value
  const improved = items.filter((i) => i.kind === 'improved')
  const regressed = items.filter((i) => i.kind === 'regressed')
  const samePass = items.filter((i) => i.kind === 'same-pass')
  const sameFail = items.filter((i) => i.kind === 'same-fail')
  const sentences = []
  if (improved.length) sentences.push(t('robustnessLab.verdictImproved', { n: improved.length }))
  if (regressed.length) sentences.push(t('robustnessLab.verdictRegressed', { n: regressed.length }))
  if (!improved.length && !regressed.length) {
    sentences.push(t('robustnessLab.verdictTie', { pass: samePass.length, fail: sameFail.length }))
  }
  return sentences
})

const tagText = (kind) => t(`robustnessLab.tag.${kind}`)

// ──────────────────────────────────────
//  对比图（分组柱状图：失败为 0 且柱顶标 ✗）
// ──────────────────────────────────────

const comparisonChartOption = computed(() => {
  const attacks = matrixAttacks.value
  const byScheme = {}
  for (const r of runRows.value) {
    if (!byScheme[r.scheme]) byScheme[r.scheme] = {}
    byScheme[r.scheme][r.attack] = r
  }
  const buildSeries = (scheme, color) => {
    const failFlags = []
    const values = attacks.map((a) => {
      const cell = byScheme[scheme]?.[a]
      const success = !!cell && cell.decode_success === true
      failFlags.push(!!cell && cell.decode_success === false)
      return success ? Number(cell.nc) : 0
    })
    return {
      name: t(`robustnessLab.scheme.${scheme}`),
      type: 'bar',
      barMaxWidth: 34,
      data: values,
      itemStyle: { color, borderRadius: [4, 4, 0, 0] },
      label: {
        show: true,
        position: 'top',
        fontSize: 11,
        color: '#64748b',
        rich: { fail: { fontSize: 14, fontWeight: 'bold', color: '#ef4444' } },
        formatter: (p) => (failFlags[p.dataIndex] ? '{fail|✗}' : p.value > 0 ? Number(p.value).toFixed(3) : ''),
      },
    }
  }
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { bottom: 0, icon: 'roundRect', itemWidth: 14, itemHeight: 8 },
    grid: { left: 12, right: 16, top: 28, bottom: 44, containLabel: true },
    xAxis: {
      type: 'category',
      data: attacks.map((a) => t(`robustnessLab.attack.${a}`)),
      axisLabel: { interval: 0, color: '#64748b' },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      name: 'NC',
      nameTextStyle: { color: '#94a3b8' },
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: '#f1f5f9' } },
    },
    series: [buildSeries('legacy', '#1e40af'), buildSeries('dqim1', '#60a5fa')],
  }
})

// ──────────────────────────────────────
//  格式化 / 导出
// ──────────────────────────────────────

const formatTime = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

const dataOptionLabel = (d) => `${d.data_alias || d.name || 'dataset'} · #${d.data_id}`

const formatParams = (params) => {
  if (!params || typeof params !== 'object') return '—'
  const entries = Object.entries(params)
  if (!entries.length) return '—'
  return entries.map(([k, v]) => `${k}=${v}`).join(', ')
}

const formatBer = (ber) => (ber === null || ber === undefined ? '—' : Number(ber).toExponential(3))

const formatDuration = (ms) => (ms === null || ms === undefined ? '—' : `${(Number(ms) / 1000).toFixed(1)} s`)

const exportJson = () => {
  if (!runMeta.value) return
  const payload = {
    run_id: runMeta.value.run_id,
    data_ref: runMeta.value.data_ref,
    created_at: runMeta.value.created_at,
    done: runMeta.value.done,
    total: runMeta.value.total,
    rows: runRows.value,
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `robustness_${runMeta.value.run_id.slice(0, 8)}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success(t('robustnessLab.exportOk'))
}

onMounted(() => {
  fetchRuns()
  fetchVectorData()
})
</script>

<style scoped>
.robustness-lab {
  width: 100%;
}

/* ── 页头 ── */
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

/* ── 通用卡片 ── */
.method-card,
.run-card,
.history-card,
.matrix-card,
.chart-card {
  border-radius: var(--radius-lg);
  margin-bottom: 16px;
}

.card-title {
  margin: 0 0 12px;
  font-size: 15px;
  color: var(--text-primary);
}

.inline-title {
  margin: 0;
  display: inline-block;
}

/* ── 区一 · 说明卡 ── */
.method-desc {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
}

.method-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.method-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
}

.method-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-700);
}

.method-text {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.boundary-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--warning-600);
  background: var(--warning-50);
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: var(--radius-md);
}

.boundary-icon {
  margin-top: 2px;
  flex: 0 0 auto;
}

/* ── 区二 · 控制 + 历史 ── */
.control-grid {
  display: grid;
  grid-template-columns: minmax(320px, 430px) 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

@media (max-width: 1100px) {
  .control-grid {
    grid-template-columns: 1fr;
  }
}

.form-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}

.form-label {
  flex: 0 0 92px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 32px;
}

.data-select {
  flex: 1;
}

.data-id-input {
  width: 140px;
}

.form-hint {
  margin: -4px 0 12px 102px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.check-group {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 10px;
  padding-top: 5px;
}

.check-item {
  margin-right: 0;
}

.start-btn {
  width: 100%;
  margin-top: 4px;
}

.history-table {
  width: 100%;
}

.history-table :deep(.el-table__row) {
  cursor: pointer;
}

.history-table :deep(.is-active-row) {
  background: var(--primary-50);
}

.mono-text {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12.5px;
  color: var(--text-secondary);
}

.status-badge {
  display: inline-block;
  padding: 1px 10px;
  font-size: 12px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.status-badge.is-done {
  color: var(--success-600);
  background: var(--success-50);
}

.status-badge.is-running {
  color: var(--warning-600);
  background: var(--warning-50);
}

.status-badge.is-error {
  color: var(--danger-600);
  background: var(--danger-50);
}

/* ── 区三 · 结果矩阵 ── */
.matrix-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.matrix-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-sep {
  color: var(--text-tertiary);
}

.matrix-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  width: 160px;
}

.progress-text {
  white-space: nowrap;
}

.matrix-subtitle {
  margin: 0 0 12px;
  font-size: 12.5px;
  color: var(--text-tertiary);
}

.matrix-table {
  width: 100%;
}

.scheme-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
}

.scheme-name.is-dqim1 {
  color: var(--primary-700);
}

.cell-value {
  display: inline-block;
  min-width: 78px;
  padding: 3px 8px;
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  border-radius: var(--radius-sm);
}

.cell-value.is-high {
  color: var(--success-600);
  background: var(--success-50);
}

.cell-value.is-mid {
  color: var(--warning-600);
  background: var(--warning-50);
}

.cell-value.is-low {
  color: var(--danger-600);
  background: var(--danger-50);
}

.cell-value.is-fail {
  color: var(--danger-500);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  font-weight: 500;
}

.cell-value.is-pending {
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  font-weight: 400;
  font-style: italic;
}

.cell-tip {
  font-size: 12px;
  line-height: 1.7;
}

/* ── 对比结论卡 ── */
.verdict-card {
  margin-top: 16px;
  padding: 14px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.verdict-card.is-ready {
  border-color: rgba(37, 99, 235, 0.25);
  background: linear-gradient(135deg, var(--bg-secondary), var(--primary-50));
}

.verdict-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.verdict-title {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
}

.verdict-progress {
  font-size: 12px;
}

.verdict-line {
  margin: 8px 0 0;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--text-primary);
}

.verdict-line.is-muted {
  color: var(--text-tertiary);
}

.verdict-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.verdict-tag {
  padding: 2px 10px;
  font-size: 12px;
  border-radius: var(--radius-full);
}

.verdict-tag.is-improved {
  color: var(--success-600);
  background: var(--success-50);
}

.verdict-tag.is-regressed {
  color: var(--danger-600);
  background: var(--danger-50);
}

.verdict-tag.is-same-pass {
  color: var(--primary-700);
  background: var(--primary-50);
}

.verdict-tag.is-same-fail {
  color: var(--text-secondary);
  background: var(--bg-tertiary);
}

.verdict-tag.is-pending {
  color: var(--text-tertiary);
  background: var(--bg-tertiary);
  font-style: italic;
}

/* ── 区四 · 对比图 ── */
.chart-holder {
  width: 100%;
  height: 330px;
}
</style>
