<template>
  <div class="watermark-quality-dashboard">
    <div class="page-header">
      <div class="page-header-left">
        <h2>{{ $t('watermarkQuality.title') }}</h2>
        <p class="subtitle">{{ $t('watermarkQuality.subtitle') }}</p>
      </div>
      <el-button type="primary" plain :icon="Refresh" :loading="globalLoading" @click="refreshAll">
        {{ $t('common.refresh') }}
      </el-button>
    </div>

    <!-- ═══════════ 区一 · Hero 统计带（8 KPI · 数字滚动） ═══════════ -->
    <el-row :gutter="16" class="hero-band">
      <el-col v-for="card in kpiCards" :key="card.key" :xs="24" :sm="12" :md="8" :lg="6">
        <div class="kpi-card hover-lift">
          <div class="kpi-icon" :style="{ background: card.gradient }">
            <el-icon size="22"><component :is="card.icon" /></el-icon>
          </div>
          <div class="kpi-body">
            <span class="kpi-value">{{ kpiText(card) }}</span>
            <span class="kpi-label">{{ card.label }}</span>
            <span v-if="card.meta" class="kpi-meta" :title="card.meta">{{ card.meta }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ═══════════ 区二 · 图表画廊（ECharts · 全部真数据） ═══════════ -->
    <el-card class="section-card" shadow="never" v-loading="vLoading">
      <template #header>
        <div class="card-header">
          <span class="section-title">{{ $t('watermarkQuality.analyticsGallery') }}</span>
        </div>
      </template>

      <!-- Row 1 · NC 直方图 + NC 日均趋势 -->
      <el-row :gutter="16">
        <el-col :xs="24" :lg="12">
          <div class="chart-box">
            <div class="chart-head">
              <div class="chart-head-left">
                <span class="chart-title">{{ $t('watermarkQuality.ncHistogram') }}</span>
                <span class="chart-sub">{{ $t('watermarkQuality.ncHistogramSub') }}</span>
              </div>
            </div>
            <v-chart v-if="hasHistogram" class="chart-holder" :option="ncHistogramOption" autoresize />
            <el-empty v-else :description="$t('common.noData')" :image-size="72" />
          </div>
        </el-col>
        <el-col :xs="24" :lg="12">
          <div class="chart-box" v-loading="trendLoading">
            <div class="chart-head">
              <div class="chart-head-left">
                <span class="chart-title">{{ $t('watermarkQuality.ncTrend') }}</span>
                <span class="chart-sub">{{ $t('watermarkQuality.ncTrendSub', { days: 30 }) }}</span>
              </div>
              <el-radio-group v-model="trendDataType" size="small">
                <el-radio-button value="">{{ $t('watermarkQuality.allTypes') }}</el-radio-button>
                <el-radio-button value="vector">{{ $t('watermarkQuality.vectorLabel') }}</el-radio-button>
                <el-radio-button value="raster">{{ $t('watermarkQuality.rasterLabel') }}</el-radio-button>
              </el-radio-group>
            </div>
            <v-chart v-if="hasTrend" class="chart-holder" :option="ncTrendOption" autoresize />
            <el-empty v-else :description="$t('common.noData')" :image-size="72" />
          </div>
        </el-col>
      </el-row>

      <!-- Row 2 · 算法对比双轴柱线图 -->
      <div class="chart-box">
        <div class="chart-head">
          <div class="chart-head-left">
            <span class="chart-title">{{ $t('watermarkQuality.algoBreakdown') }}</span>
            <span class="chart-sub">{{ $t('watermarkQuality.algoBreakdownSub') }}</span>
          </div>
        </div>
        <v-chart v-if="hasAlgo" class="chart-holder" :option="algoBreakdownOption" autoresize />
        <el-empty v-else :description="$t('common.noData')" :image-size="72" />
      </div>

      <!-- Row 3 · 验证数据构成 + 交付健康度 -->
      <el-row :gutter="16">
        <el-col :xs="24" :lg="12">
          <div class="chart-box">
            <div class="chart-head">
              <div class="chart-head-left">
                <span class="chart-title">{{ $t('watermarkQuality.verificationShare') }}</span>
                <span class="chart-sub">{{ $t('watermarkQuality.verificationShareSub') }}</span>
              </div>
            </div>
            <v-chart v-if="hasShare" class="chart-holder" :option="verificationShareOption" autoresize />
            <el-empty v-else :description="$t('common.noData')" :image-size="72" />
          </div>
        </el-col>
        <el-col :xs="24" :lg="12">
          <div class="chart-box" v-loading="dLoading">
            <div class="chart-head">
              <div class="chart-head-left">
                <span class="chart-title">{{ $t('watermarkQuality.deliveryHealth') }}</span>
                <span class="chart-sub">
                  {{ $t('watermarkQuality.ringInner') }} / {{ $t('watermarkQuality.ringOuter') }}
                </span>
              </div>
            </div>
            <div class="donut-wrap">
              <v-chart v-if="hasDelivery" class="chart-holder" :option="deliveryHealthOption" autoresize />
              <div v-if="hasDelivery" class="donut-center">
                <span class="donut-center-value">{{ dStats?.total ?? '—' }}</span>
                <span class="donut-center-label">{{ $t('watermarkQuality.centerDeliveries') }}</span>
                <span class="donut-center-sub">
                  {{ $t('watermarkQuality.centerDownloaded') }} {{ dStats?.downloaded_count ?? '—' }}
                </span>
              </div>
              <el-empty v-if="!hasDelivery && !dLoading" :description="$t('common.noData')" :image-size="72" />
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- ═══════════ 验证记录（分页表格 · data_type + 时间范围筛选） ═══════════ -->
    <el-card class="records-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-header-left">
            <span class="section-title">{{ $t('watermarkQuality.records') }}</span>
            <el-radio-group v-model="dataTypeFilter" size="small">
              <el-radio-button value="">{{ $t('watermarkQuality.allTypes') }}</el-radio-button>
              <el-radio-button value="vector">{{ $t('watermarkQuality.vectorLabel') }}</el-radio-button>
              <el-radio-button value="raster">{{ $t('watermarkQuality.rasterLabel') }}</el-radio-button>
            </el-radio-group>
          </div>
          <div class="card-header-right">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              size="small"
              value-format="YYYY-MM-DD"
              :start-placeholder="$t('watermarkQuality.timeRange')"
              range-separator="~"
              unlink-panels
              style="width: 250px"
            />
            <el-button type="primary" :icon="Refresh" @click="fetchRecords" :loading="loading">
              {{ $t('common.refresh') }}
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="records"
        v-loading="loading"
        stripe
        style="width: 100%"
        :empty-text="$t('common.noData')"
      >
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column :label="$t('watermarkQuality.dataType')" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.data_type === 'vector'" type="primary" size="small" effect="plain">
              <el-icon style="margin-right: 4px;"><MapLocation /></el-icon>{{ $t('watermarkQuality.vectorLabel') }}
            </el-tag>
            <el-tag v-else-if="row.data_type === 'raster'" type="success" size="small" effect="plain">
              <el-icon style="margin-right: 4px;"><Picture /></el-icon>{{ $t('watermarkQuality.rasterLabel') }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="nc_value" :label="$t('watermarkQuality.ncValue')" width="110">
          <template #default="{ row }">
            <el-tag :type="getNcTagType(row.nc_value)" effect="dark" round>
              {{ row.nc_value?.toFixed(4) || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="verified_by" :label="$t('watermarkQuality.verifiedBy')" width="130" />
        <el-table-column prop="verified_at" :label="$t('watermarkQuality.verifiedAt')" width="170">
          <template #default="{ row }">{{ formatDate(row.verified_at) }}</template>
        </el-table-column>
        <el-table-column prop="ip_address" :label="$t('watermarkQuality.ipAddress')" width="130" />
      </el-table>

      <div class="pagination-wrapper" v-if="total > pageSize">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          @current-change="fetchRecords"
        />
      </div>
    </el-card>

    <!-- Quality Metrics Explained -->
    <el-card class="metrics-card" shadow="never">
      <template #header><span class="section-title">{{ $t('watermarkQuality.metricsExplained') }}</span></template>
      <div class="metrics-grid">
        <div class="metric-item">
          <div class="metric-header">
            <el-tag effect="dark" round>PSNR</el-tag>
            <span class="metric-range">{{ $t('watermarkQuality.psnrRange') }}</span>
          </div>
          <p class="metric-desc">{{ $t('watermarkQuality.psnrDesc') }}</p>
        </div>
        <div class="metric-item">
          <div class="metric-header">
            <el-tag effect="dark" type="success" round>NC</el-tag>
            <span class="metric-range">{{ $t('watermarkQuality.ncRange') }}</span>
          </div>
          <p class="metric-desc">{{ $t('watermarkQuality.ncDesc') }}</p>
        </div>
        <div class="metric-item">
          <div class="metric-header">
            <el-tag effect="dark" type="warning" round>SSIM</el-tag>
            <span class="metric-range">{{ $t('watermarkQuality.ssimRange') }}</span>
          </div>
          <p class="metric-desc">{{ $t('watermarkQuality.ssimDesc') }}</p>
        </div>
        <div class="metric-item">
          <div class="metric-header">
            <el-tag effect="dark" type="danger" round>BER</el-tag>
            <span class="metric-range">{{ $t('watermarkQuality.berRange') }}</span>
          </div>
          <p class="metric-desc">{{ $t('watermarkQuality.berDesc') }}</p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Refresh, MapLocation, Picture,
  DataLine, TrendCharts, Warning, Box, Download, Link, Aim, Odometer
} from '@element-plus/icons-vue'
import { getVerificationRecords, getBenchmarkResults, getVerificationStats, getBenchmarkStats } from '@/api/watermark'
import { getDeliveryStats } from '@/api/forensics'
import { use, graphic } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

// ── ECharts 按需注册：本页用到的渲染器 / 图表 / 组件 ──
use([CanvasRenderer, BarChart, LineChart, PieChart, TooltipComponent, LegendComponent, GridComponent])

const { t } = useI18n()

// ══════════════════ 数据源：三个统计端点并行 ══════════════════
const vLoading = ref(false)
const vStats = ref(null)        // /api/watermark/verification_stats → stats
const trendLoading = ref(false)
const trendDataType = ref('')   // '' | 'vector' | 'raster' — 仅作用于趋势图
const trendStats = ref(null)    // 带 data_type 的趋势专查
const dLoading = ref(false)
const dStats = ref(null)        // /api/forensics/deliveries/stats → stats
const benchLoading = ref(false)
const benchData = ref(null)     // /api/benchmark/stats（或旧 JSON 回退的等价结构）

const globalLoading = computed(() => vLoading.value || dLoading.value || benchLoading.value)

// ── 工具 ──
const numOrNull = (x) => (typeof x === 'number' && Number.isFinite(x) ? x : null)
const fmtDateTime = (iso) => {
  if (!iso) return '—'
  const s = String(iso).replace('T', ' ')
  return s.length >= 16 ? s.slice(0, 16) : s
}

// ══════════════════ 区一 · KPI（count-up rAF，200ms） ══════════════════
const kpiDisplay = reactive({})
const kpiRaf = {}

const animateKpi = (key, target) => {
  if (kpiRaf[key]) cancelAnimationFrame(kpiRaf[key])
  if (target == null || !Number.isFinite(target)) {
    kpiDisplay[key] = null
    return
  }
  const from = Number.isFinite(kpiDisplay[key]) ? kpiDisplay[key] : 0
  kpiDisplay[key] = from
  const t0 = performance.now()
  const DURATION = 200
  const tick = (now) => {
    const p = Math.min(1, (now - t0) / DURATION)
    const eased = 1 - Math.pow(1 - p, 3)
    kpiDisplay[key] = from + (target - from) * eased
    if (p < 1) {
      kpiRaf[key] = requestAnimationFrame(tick)
    } else {
      kpiDisplay[key] = target
      kpiRaf[key] = null
    }
  }
  kpiRaf[key] = requestAnimationFrame(tick)
}

onBeforeUnmount(() => {
  Object.values(kpiRaf).forEach((id) => id && cancelAnimationFrame(id))
})

const fmtKpiValue = (val, fmt) => {
  if (val == null || !Number.isFinite(val)) return '—'
  switch (fmt) {
    case 'int': return Math.round(val).toLocaleString()
    case 'dec3': return val.toFixed(3)
    case 'dec4': return val.toFixed(4)
    case 'pct1': return `${val.toFixed(1)}%`
    default: return String(val)
  }
}

const kpiText = (card) => {
  if (card.value == null) return '—'
  const shown = kpiDisplay[card.key]
  return fmtKpiValue(shown == null ? card.value : shown, card.fmt)
}

const kpiCards = computed(() => {
  const v = vStats.value || {}
  const d = dStats.value || {}
  const anchor = d.anchor || {}
  const chainRate = d.chain_checked ? (d.chain_valid_count / d.chain_checked) * 100 : null
  const snap = benchData.value?.latest_run?.created_at
  return [
    {
      key: 'verify', icon: DataLine, gradient: 'linear-gradient(135deg, #667eea, #764ba2)',
      label: t('watermarkQuality.totalVerifications'), value: numOrNull(v.total), fmt: 'int',
      meta: v.min_nc != null && v.max_nc != null
        ? t('watermarkQuality.kpiNcMinMax', { min: v.min_nc.toFixed(3), max: v.max_nc.toFixed(3) })
        : t('watermarkQuality.kpiTotalNote'),
    },
    {
      key: 'avgNc', icon: TrendCharts, gradient: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
      label: t('watermarkQuality.avgNc'), value: numOrNull(v.avg_nc), fmt: 'dec4',
      meta: v.p50_nc != null ? t('watermarkQuality.kpiNcMedian', { p50: v.p50_nc.toFixed(4) }) : '',
    },
    {
      key: 'lowNc', icon: Warning, gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
      label: t('watermarkQuality.lowNc'), value: numOrNull(v.low_nc_count), fmt: 'int',
      meta: v.total ? `${((v.low_nc_count / v.total) * 100).toFixed(1)}% / ${v.total}` : '',
    },
    {
      key: 'deliveries', icon: Box, gradient: 'linear-gradient(135deg, #0ea5e9, #0369a1)',
      label: t('watermarkQuality.kpiDeliveries'), value: numOrNull(d.total), fmt: 'int',
      meta: d.total != null
        ? t('watermarkQuality.kpiDeliveryDetail', { downloaded: d.downloaded_count ?? 0, total: d.total })
        : '',
    },
    {
      key: 'downloaded', icon: Download, gradient: 'linear-gradient(135deg, #10b981, #059669)',
      label: t('watermarkQuality.kpiDownloaded'), value: numOrNull(d.downloaded_count), fmt: 'int',
      meta: d.total ? `${((d.downloaded_count / d.total) * 100).toFixed(0)}%` : '',
    },
    {
      key: 'chain', icon: Link, gradient: 'linear-gradient(135deg, #6366f1, #4f46e5)',
      label: t('watermarkQuality.kpiChainIntegrity'), value: chainRate, fmt: 'pct1',
      meta: d.chain_checked != null
        ? t('watermarkQuality.kpiChainDetail', { valid: d.chain_valid_count ?? 0, checked: d.chain_checked })
        : '',
    },
    {
      key: 'anchor', icon: Aim, gradient: 'linear-gradient(135deg, #a855f7, #7c3aed)',
      label: t('watermarkQuality.kpiAnchoredBatches'),
      value: anchor.submitted != null && anchor.pending != null ? anchor.submitted + anchor.pending : null,
      fmt: 'int',
      meta: anchor.submitted != null || anchor.pending != null
        ? t('watermarkQuality.kpiAnchorDetail', { submitted: anchor.submitted ?? '—', pending: anchor.pending ?? '—' })
        : '',
    },
    {
      key: 'bench', icon: Odometer, gradient: 'linear-gradient(135deg, #f43f5e, #be123c)',
      label: t('watermarkQuality.kpiBenchmarkRuns'), value: numOrNull(benchData.value?.runs_count), fmt: 'int',
      meta: snap ? t('watermarkQuality.kpiSnapshot', { time: fmtDateTime(snap) }) : '',
    },
  ]
})

watch(kpiCards, (cards) => {
  cards.forEach((c) => animateKpi(c.key, c.value))
}, { immediate: true })

// ══════════════════ 区二 · 图表 ══════════════════
// ── NC 直方图（服务端 10 桶，低于 0.8 冷暖双色渐变） ──
const hasHistogram = computed(() => (vStats.value?.total || 0) > 0)
const ncHistogramOption = computed(() => {
  const hist = vStats.value?.nc_histogram || []
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '4%', right: '4%', bottom: '6%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: hist.map((h) => h.bucket),
      axisLabel: { fontSize: 10, color: '#64748b' },
    },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { color: '#64748b' } },
    series: [{
      name: t('watermarkQuality.seriesCount'),
      type: 'bar',
      barWidth: '56%',
      data: hist.map((h) => {
        const low = parseFloat(h.bucket) || 0
        return {
          value: h.count,
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: low < 0.8
              ? new graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#fbbf24' }, { offset: 1, color: '#ef4444' },
              ])
              : new graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#34d399' }, { offset: 1, color: '#059669' },
              ]),
          },
        }
      }),
    }],
  }
})

// ── NC 日均趋势（空档日 avg_nc 为 null → 断点；验证数以浅色柱呈现） ──
const trendDaily = computed(() => {
  const src = trendDataType.value ? trendStats.value : vStats.value
  return src?.daily || []
})
const hasTrend = computed(() => trendDaily.value.some((d) => d.count > 0))
const ncTrendOption = computed(() => {
  const daily = trendDaily.value
  const countLabel = t('watermarkQuality.seriesCount')
  const ncLabel = t('watermarkQuality.seriesAvgNc')
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: [ncLabel, countLabel], bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: '4%', right: '4%', bottom: '18%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: daily.map((d) => String(d.date).slice(5)),
      axisLabel: { fontSize: 10, color: '#64748b' },
    },
    yAxis: [
      { type: 'value', name: 'NC', min: 0, max: 1, axisLabel: { color: '#64748b' } },
      {
        type: 'value', name: countLabel, minInterval: 1,
        axisLabel: { color: '#94a3b8' }, splitLine: { show: false },
      },
    ],
    series: [
      {
        name: countLabel, type: 'bar', yAxisIndex: 1, barWidth: '52%',
        data: daily.map((d) => d.count),
        itemStyle: { color: 'rgba(99, 102, 241, 0.16)', borderRadius: [3, 3, 0, 0] },
      },
      {
        name: ncLabel, type: 'line', yAxisIndex: 0, smooth: true, connectNulls: false,
        data: daily.map((d) => d.avg_nc),
        symbolSize: 6,
        lineStyle: { width: 2.5, color: '#6366f1' },
        itemStyle: { color: '#6366f1' },
      },
    ],
  }
})

// ── 算法对比（柱 = 验证数，线 = 平均 NC；tooltip 附真实 avg_ber） ──
const hasAlgo = computed(() => (vStats.value?.by_algorithm || []).length > 0)
const algoBreakdownOption = computed(() => {
  const rows = vStats.value?.by_algorithm || []
  const countLabel = t('watermarkQuality.seriesCount')
  const ncLabel = t('watermarkQuality.seriesAvgNc')
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const alg = params?.[0]?.axisValue
        const row = rows.find((r) => r.algorithm === alg)
        return [
          `<b>${alg}</b>`,
          `${countLabel}: ${row?.count ?? '—'}`,
          `${ncLabel}: ${row?.avg_nc != null ? row.avg_nc.toFixed(4) : '—'}`,
          `${t('watermarkQuality.seriesAvgBer')}: ${row?.avg_ber != null ? row.avg_ber.toFixed(4) : '—'}`,
        ].join('<br/>')
      },
    },
    legend: { data: [countLabel, ncLabel], bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: '4%', right: '4%', bottom: '18%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map((r) => r.algorithm),
      axisLabel: { color: '#64748b' },
    },
    yAxis: [
      { type: 'value', name: countLabel, minInterval: 1, axisLabel: { color: '#64748b' } },
      { type: 'value', name: 'NC', min: 0, max: 1, axisLabel: { color: '#94a3b8' }, splitLine: { show: false } },
    ],
    series: [
      {
        name: countLabel, type: 'bar', barWidth: '32%',
        data: rows.map((r) => r.count),
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#818cf8' }, { offset: 1, color: '#4f46e5' },
          ]),
        },
      },
      {
        name: ncLabel, type: 'line', yAxisIndex: 1, symbolSize: 9,
        data: rows.map((r) => r.avg_nc),
        lineStyle: { width: 2.5, color: '#10b981' },
        itemStyle: { color: '#10b981' },
      },
    ],
  }
})

// ── 验证数据构成（矢量 / 栅格 donut） ──
const dataTypeLabel = (dt) => {
  if (dt === 'vector') return t('watermarkQuality.vectorLabel')
  if (dt === 'raster') return t('watermarkQuality.rasterLabel')
  return dt || '—'
}
const hasShare = computed(() =>
  (vStats.value?.total || 0) > 0 && (vStats.value?.by_data_type || []).length > 0)
const verificationShareOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: { bottom: 0, textStyle: { fontSize: 11 } },
  series: [{
    type: 'pie',
    radius: ['50%', '72%'],
    center: ['50%', '44%'],
    itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
    label: { formatter: '{b}\n{d}%', fontSize: 11, color: '#475569' },
    data: (vStats.value?.by_data_type || []).map((d) => ({
      name: dataTypeLabel(d.data_type),
      value: d.count,
      itemStyle: {
        color: d.data_type === 'vector' ? '#6366f1' : d.data_type === 'raster' ? '#10b981' : '#94a3b8',
      },
    })),
  }],
}))

// ── 交付健康度（内环 = 交付状态，外环 = 锚定状态，中心叠加汇总） ──
const STATUS_COLORS = { READY: '#10b981', FAILED: '#ef4444', PENDING: '#f59e0b' }
const hasDelivery = computed(() => (dStats.value?.total || 0) > 0)
const deliveryHealthOption = computed(() => {
  const d = dStats.value || {}
  const anchor = d.anchor || {}
  return {
    tooltip: { trigger: 'item', formatter: '{a} · {b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [
      {
        name: t('watermarkQuality.ringInner'), type: 'pie',
        radius: ['38%', '58%'], center: ['50%', '44%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { show: false }, labelLine: { show: false },
        data: (d.by_status || []).map((s) => ({
          name: s.status, value: s.count,
          itemStyle: { color: STATUS_COLORS[s.status] || '#94a3b8' },
        })),
      },
      {
        name: t('watermarkQuality.ringOuter'), type: 'pie',
        radius: ['64%', '84%'], center: ['50%', '44%'],
        itemStyle: { borderColor: '#fff', borderWidth: 2 },
        label: { show: false }, labelLine: { show: false },
        data: [
          { name: t('watermarkQuality.anchorSubmitted'), value: anchor.submitted || 0, itemStyle: { color: '#6366f1' } },
          { name: t('watermarkQuality.anchorPending'), value: anchor.pending || 0, itemStyle: { color: '#f59e0b' } },
          { name: t('watermarkQuality.anchorNone'), value: anchor.none || 0, itemStyle: { color: '#cbd5e1' } },
        ].filter((x) => x.value > 0),
      },
    ],
  }
})

// ══════════════════ 验证记录表（保留 · 新增时间范围筛选） ══════════════════
const loading = ref(false)
const records = ref([])
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const dataTypeFilter = ref('')  // ''=all, 'vector', 'raster'
const dateRange = ref(null)     // [from, to] 'YYYY-MM-DD'

const getNcTagType = (nc) => {
  if (nc == null) return 'info'
  if (nc >= 0.95) return 'success'
  if (nc >= 0.8) return 'warning'
  return 'danger'
}

const formatDate = (isoStr) => {
  if (!isoStr) return '-'
  return new Date(isoStr).toLocaleString()
}

const fetchRecords = async () => {
  loading.value = true
  try {
    const params = { page: currentPage.value, pageSize }
    if (dataTypeFilter.value) {
      params.data_type = dataTypeFilter.value
    }
    if (Array.isArray(dateRange.value) && dateRange.value.length === 2) {
      params.from = dateRange.value[0]
      params.to = dateRange.value[1]
    }
    const resp = await getVerificationRecords(params)
    const body = resp?.data
    if (body?.status) {
      records.value = body.data || []
      total.value = body.pages?.total || 0
    }
  } catch (e) {
    console.error('Failed to fetch verification records:', e)
  } finally {
    loading.value = false
  }
}

watch(dataTypeFilter, () => {
  currentPage.value = 1
  fetchRecords()
})

watch(dateRange, () => {
  currentPage.value = 1
  fetchRecords()
})

// ══════════════════ 三个统计端点的取数 ══════════════════
const fetchVerificationStats = async () => {
  vLoading.value = true
  try {
    const resp = await getVerificationStats({ days: 30 })
    if (resp?.data?.status) {
      vStats.value = resp.data.stats
    }
  } catch (e) {
    console.error('Failed to fetch verification stats:', e)
  } finally {
    vLoading.value = false
  }
}

const fetchTrend = async () => {
  if (!trendDataType.value) return
  trendLoading.value = true
  try {
    const resp = await getVerificationStats({ days: 30, data_type: trendDataType.value })
    if (resp?.data?.status) {
      trendStats.value = resp.data.stats
    }
  } catch (e) {
    console.error('Failed to fetch NC trend stats:', e)
  } finally {
    trendLoading.value = false
  }
}

watch(trendDataType, (val) => {
  trendStats.value = null
  if (val) fetchTrend()
})

const fetchDeliveryStats = async () => {
  dLoading.value = true
  try {
    const resp = await getDeliveryStats()
    if (resp?.data?.status) {
      dStats.value = resp.data.stats
    }
  } catch (e) {
    console.error('Failed to fetch delivery stats:', e)
  } finally {
    dLoading.value = false
  }
}

// 优先 /api/benchmark/stats（数据库最新 run）；404 / 空 → 回退旧 JSON 端点
const fetchBenchmark = async () => {
  benchLoading.value = true
  try {
    let body = null
    try {
      const resp = await getBenchmarkStats()
      body = resp?.data
    } catch (e) {
      body = null
    }
    if (body?.status && Array.isArray(body.results) && body.results.length > 0) {
      benchData.value = body
      return
    }
    const legacy = await getBenchmarkResults()
    const d = legacy?.data
    const legacyResults = d?.data?.results
    if (d?.status && Array.isArray(legacyResults) && legacyResults.length > 0) {
      benchData.value = {
        runs_count: null,
        latest_run: { created_at: d.data?.benchmark_metadata?.timestamp || null },
        results: legacyResults,
      }
    }
  } catch (e) {
    console.error('Failed to fetch benchmark stats:', e)
  } finally {
    benchLoading.value = false
  }
}

const refreshAll = () => {
  fetchVerificationStats()
  fetchTrend()
  fetchDeliveryStats()
  fetchBenchmark()
  fetchRecords()
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.watermark-quality-dashboard {
  padding: 24px;
  max-width: 1440px;
  margin: 0 auto;
}

/* ── 页头 ── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  margin-bottom: 4px;
}

.subtitle {
  color: var(--text-secondary, #64748b);
  font-size: 14px;
}

.page-header-left { min-width: 0; }

/* ── 区一 · Hero 统计带 ── */
.hero-band { margin-bottom: 8px; }

.hero-band .el-col { margin-bottom: 16px; }

.kpi-card {
  display: flex;
  align-items: center;
  gap: 14px;
  height: 100%;
  padding: 18px 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid var(--border-color, #e2e8f0);
  border-radius: var(--radius-lg, 14px);
}

.hover-lift {
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.hover-lift:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0, 0, 0, 0.1));
}

.kpi-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.18);
}

.kpi-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.kpi-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--text-primary, #1e293b);
  font-variant-numeric: tabular-nums;
}

.kpi-label {
  font-size: 13px;
  color: var(--text-secondary, #64748b);
  margin-top: 2px;
}

.kpi-meta {
  font-size: 11px;
  color: var(--text-tertiary, #94a3b8);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 区二 · 图表画廊 ── */
.section-card {
  border-radius: var(--radius-lg, 14px);
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.card-header-left,
.card-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.section-title {
  font-weight: 600;
  color: var(--text-primary, #1e293b);
}

.chart-box {
  background: var(--bg-secondary, #f8fafc);
  border: 1px solid var(--border-color-light, #f1f5f9);
  border-radius: var(--radius-md, 10px);
  padding: 14px;
  margin-bottom: 16px;
}

.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.chart-head-left {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1e293b);
}

.chart-sub {
  font-size: 11px;
  color: var(--text-tertiary, #94a3b8);
}

.chart-holder {
  width: 100%;
  height: 280px;
}

.donut-wrap { position: relative; }

.donut-center {
  position: absolute;
  top: 44%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  pointer-events: none;
}

.donut-center-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--text-primary, #1e293b);
  font-variant-numeric: tabular-nums;
}

.donut-center-label {
  font-size: 12px;
  color: var(--text-secondary, #64748b);
}

.donut-center-sub {
  font-size: 11px;
  color: var(--text-tertiary, #94a3b8);
}

/* ── 验证记录表 ── */
.records-card {
  border-radius: var(--radius-lg, 14px);
  margin-bottom: 20px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

/* ── 指标说明 ── */
.metrics-card {
  border-radius: var(--radius-lg, 14px);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
}

.metric-item {
  padding: 16px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.metric-range { font-size: 12px; color: #64748b; }

.metric-desc {
  font-size: 13px;
  color: #475569;
  margin: 0;
  line-height: 1.6;
}
</style>
