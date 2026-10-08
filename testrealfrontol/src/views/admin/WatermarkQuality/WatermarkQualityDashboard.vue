<template>
  <div class="watermark-quality-dashboard">
    <div class="page-header">
      <div class="page-header-left" :ref="setTourEl('header')">
        <h2>{{ $t('watermarkQuality.title') }}</h2>
        <p class="subtitle">
          {{ $t('watermarkQuality.subtitle') }}
          <span v-if="verificationWindowText" class="subtitle-meta">{{
            $t('watermarkQuality.dataWindow', { range: verificationWindowText })
          }}</span>
        </p>
      </div>
      <div class="page-header-actions">
        <el-button :icon="Guide" @click="startTour">
          {{ $t('watermarkQuality.replayTour') }}
        </el-button>
        <el-button type="primary" :icon="Refresh" :loading="globalLoading" @click="refreshAll">
          {{ $t('common.refresh') }}
        </el-button>
      </div>
    </div>

    <!-- ═══════════ 区一 · Hero 统计带（8 KPI · 联排细线网格 · 数字滚动） ═══════════ -->
    <div class="hero-band" :ref="setTourEl('hero')">
      <div class="kpi-grid">
        <div v-for="card in kpiCards" :key="card.key" class="kpi-card">
          <!-- 状态点：纯视觉增强，语义已在 meta 文案中（aria 隐藏） -->
          <span v-if="card.status" class="kpi-dot" :class="`kpi-dot--${card.status}`" aria-hidden="true" />
          <div class="kpi-label-row">
            <el-icon class="kpi-icon" :size="13"><component :is="card.icon" /></el-icon>
            <span class="kpi-label">{{ card.label }}</span>
            <GlossaryHelp v-bind="glossary[card.help]" />
          </div>
          <div class="kpi-value">{{ kpiText(card) }}</div>
          <div v-if="card.meta" class="kpi-meta" :title="card.meta">{{ card.meta }}</div>
        </div>
      </div>
    </div>

    <!-- ═══════════ 区二 · 图表画廊（ECharts · 全部真数据） ═══════════ -->
    <el-card class="section-card" shadow="never" v-loading="verifLoading">
      <template #header>
        <div class="card-header" :ref="setTourEl('gallery')">
          <span class="section-title">{{ $t('watermarkQuality.analyticsGallery') }}</span>
        </div>
      </template>

      <!-- 图表联排细线网格：直方图 + 趋势 / 算法（跨列）/ 构成 + 交付 -->
      <div class="chart-grid">
        <div class="chart-box">
          <div class="chart-head">
            <div class="chart-head-left">
              <span class="chart-title-row">
                <span class="chart-title">{{ $t('watermarkQuality.ncHistogram') }}</span>
                <GlossaryHelp v-bind="glossary.histogram" />
              </span>
              <span class="chart-sub">{{ $t('watermarkQuality.ncHistogramSub') }}</span>
            </div>
          </div>
          <v-chart v-if="hasHistogram" class="chart-holder" :option="ncHistogramOption" autoresize />
          <EmptyState v-else compact variant="never" :title="$t('common.noData')" :description="$t('common.noDataDesc')" />
        </div>

        <div class="chart-box" v-loading="trendLoading">
          <div class="chart-head">
            <div class="chart-head-left">
              <span class="chart-title-row">
                <span class="chart-title">{{ $t('watermarkQuality.ncTrend') }}</span>
                <GlossaryHelp v-bind="glossary.trend" />
              </span>
              <span class="chart-sub">{{ $t('watermarkQuality.ncTrendSub', { days: 30 }) }}</span>
            </div>
            <el-radio-group v-model="trendDataType" size="small">
              <el-radio-button value="">{{ $t('watermarkQuality.allTypes') }}</el-radio-button>
              <el-radio-button value="vector">{{ $t('watermarkQuality.vectorLabel') }}</el-radio-button>
              <el-radio-button value="raster">{{ $t('watermarkQuality.rasterLabel') }}</el-radio-button>
            </el-radio-group>
          </div>
          <v-chart v-if="hasTrend" class="chart-holder" :option="ncTrendOption" autoresize />
          <EmptyState v-else compact :variant="trendDataType ? 'filtered' : 'never'" :title="$t('common.noData')" :description="$t('common.noDataDesc')" />
        </div>

        <div class="chart-box chart-box--wide">
          <div class="chart-head">
            <div class="chart-head-left">
              <span class="chart-title-row">
                <span class="chart-title">{{ $t('watermarkQuality.algoBreakdown') }}</span>
                <GlossaryHelp v-bind="glossary.algo" />
              </span>
              <span class="chart-sub">{{ $t('watermarkQuality.algoBreakdownSub') }}</span>
            </div>
          </div>
          <v-chart v-if="hasAlgo" class="chart-holder" :option="algoBreakdownOption" autoresize />
          <EmptyState v-else compact variant="never" :title="$t('common.noData')" :description="$t('common.noDataDesc')" />
        </div>

        <div class="chart-box">
          <div class="chart-head">
            <div class="chart-head-left">
              <span class="chart-title-row">
                <span class="chart-title">{{ $t('watermarkQuality.verificationShare') }}</span>
                <GlossaryHelp v-bind="glossary.share" />
              </span>
              <span class="chart-sub">{{ $t('watermarkQuality.verificationShareSub') }}</span>
            </div>
          </div>
          <v-chart v-if="hasShare" class="chart-holder" :option="verificationShareOption" autoresize />
          <EmptyState v-else compact variant="never" :title="$t('common.noData')" :description="$t('common.noDataDesc')" />
        </div>

        <div class="chart-box" v-loading="dLoading">
          <div class="chart-head">
            <div class="chart-head-left">
              <span class="chart-title-row">
                <span class="chart-title">{{ $t('watermarkQuality.deliveryHealth') }}</span>
                <GlossaryHelp v-bind="glossary.deliveryChart" />
              </span>
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
            <EmptyState v-if="!hasDelivery && !dLoading" compact variant="never" :title="$t('common.noData')" :description="$t('common.noDataDesc')" />
          </div>
        </div>
      </div>
    </el-card>

    <!-- ═══════════ 区三 · 算法能力矩阵（基准真数据） ═══════════ -->
    <el-card class="section-card" shadow="never" v-loading="benchLoading">
      <template #header>
        <div class="card-header" :ref="setTourEl('matrix')">
          <div class="card-header-left">
            <span class="section-title">{{ $t('watermarkQuality.capabilityMatrix') }}</span>
            <GlossaryHelp v-bind="glossary.matrix" />
            <el-tag v-if="benchSnapshotTime" type="info" size="small">
              {{ $t('watermarkQuality.benchSnapshot') }} · {{ benchSnapshotTime }}
            </el-tag>
          </div>
        </div>
      </template>
      <p class="matrix-legend">{{ $t('watermarkQuality.matrixSub') }}</p>

      <el-table :data="matrixAttacks" stripe style="width: 100%" :empty-text="$t('common.noData')">
        <el-table-column :label="$t('watermarkQuality.attackCol')" min-width="140" fixed>
          <template #default="{ row }">
            <span class="attack-name">{{ row }}</span>
          </template>
        </el-table-column>
        <el-table-column v-for="alg in matrixAlgos" :key="alg" :label="alg" align="center">
          <el-table-column :label="$t('watermarkQuality.ncValue')" width="96" align="right">
            <template #default="{ row }">
              <span class="nc-cell" :class="ncCellClass(cellOf(row, alg)?.nc)">
                {{ cellOf(row, alg)?.nc != null ? cellOf(row, alg).nc.toFixed(4) : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.decodeCol')" width="78" align="center">
            <template #default="{ row }">
              <span v-if="cellOf(row, alg)?.decode_success === true" class="decode-ok">✓</span>
              <span v-else-if="cellOf(row, alg)" class="decode-bad">✗</span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.recoveryPsnrCol')" width="110" align="right">
            <template #default="{ row }">
              {{ cellOf(row, alg)?.recovery_psnr != null ? cellOf(row, alg).recovery_psnr.toFixed(1) : '—' }}
            </template>
          </el-table-column>
        </el-table-column>
      </el-table>

      <!-- 嵌入质量总览（无攻击基线） -->
      <div class="sub-section">
        <h4 class="sub-title">{{ $t('watermarkQuality.stegoOverview') }}</h4>
        <el-table :data="benchSummaries" stripe size="small" style="width: 100%" :empty-text="$t('common.noData')" :row-class-name="benchRowClass">
          <el-table-column prop="algorithm" :label="$t('watermarkQuality.algoName')" width="110" />
          <el-table-column :label="$t('watermarkQuality.wmBitCount')" width="110" align="right">
            <template #default="{ row }">{{ row.wm_bit_count ?? '—' }}</template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.stegoPsnr')" width="120" align="right">
            <template #default="{ row }">
              <span :style="{ color: psnrColor(row.stego_psnr), fontWeight: 700 }">
                {{ row.stego_psnr != null ? row.stego_psnr + ' dB' : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="SSIM" width="110" align="right">
            <template #default="{ row }">
              {{ row.stego_ssim != null ? row.stego_ssim.toFixed(5) : '—' }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.baselineNc')" width="110" align="right">
            <template #default="{ row }">
              <span v-if="row.baseline_nc != null" class="state-chip" :class="ncChipClass(row.baseline_nc)">
                {{ row.baseline_nc.toFixed(4) }}
              </span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.baselineBer')" width="110" align="right">
            <template #default="{ row }">
              {{ row.baseline_ber != null ? row.baseline_ber.toFixed(4) : '—' }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.recovery')" width="100">
            <template #default="{ row }">
              <span class="state-chip" :class="row.recovery_perfect ? 'state-chip--success' : 'state-chip--danger'">
                {{ row.recovery_perfect ? $t('watermarkQuality.perfect') : $t('watermarkQuality.broken') }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.colStatus')" min-width="120">
            <template #default="{ row }">
              <span v-if="row.embed_error" class="state-chip state-chip--danger">{{ $t('watermarkQuality.embedFailed') }}</span>
              <span v-else class="decode-ok">✓</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="bench-howto-row">
        <el-icon><InfoFilled /></el-icon>
        <span><b>{{ $t('watermarkQuality.benchHowTo') }}</b> · {{ $t('watermarkQuality.benchHowToDesc') }}</span>
      </div>

      <!-- 矢量 D-QIM（v3 新方案） -->
      <div class="dqim-card">
        <div class="dqim-head">
          <div>
            <span class="dqim-title">{{ $t('watermarkQuality.dqimTitle') }}</span>
            <span class="dqim-subtitle">{{ $t('watermarkQuality.dqimSubtitle') }}</span>
          </div>
          <el-tag type="warning" effect="plain" size="small">{{ $t('watermarkQuality.dqimBadge') }}</el-tag>
        </div>
        <p class="dqim-desc">{{ $t('watermarkQuality.dqimDesc') }}</p>
        <div class="dqim-stats">
          <div class="dqim-stat">
            <span class="dqim-stat-value">{{ $t('watermarkQuality.dqimStatTranslationValue') }}</span>
            <span class="dqim-stat-label">{{ $t('watermarkQuality.dqimStatTranslation') }}</span>
          </div>
          <div class="dqim-stat">
            <span class="dqim-stat-value">{{ $t('watermarkQuality.dqimStatDeletionValue') }}</span>
            <span class="dqim-stat-label">{{ $t('watermarkQuality.dqimStatDeletion') }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- ═══════════ 区四 · 证据链健康度 ═══════════ -->
    <el-card class="section-card" shadow="never" v-loading="dLoading">
      <template #header>
        <div class="card-header">
          <div class="card-header-left">
            <span class="section-title">{{ $t('watermarkQuality.chainHealth') }}</span>
            <el-tag type="info" size="small" effect="plain">{{ $t('watermarkQuality.chainClickHint') }}</el-tag>
          </div>
        </div>
      </template>

      <el-row :gutter="16" class="chain-top">
        <el-col :xs="24" :sm="8" :md="7">
          <div class="chain-ring-box">
            <div class="chain-ring" :style="chainRingStyle">
              <div class="chain-ring-inner">
                <span class="chain-ring-value">{{ chainPct }}%</span>
                <span class="chain-ring-label">{{ $t('watermarkQuality.chainValid') }}</span>
              </div>
            </div>
            <div class="chain-ring-meta">
              {{ $t('watermarkQuality.kpiChainDetail', { valid: dStats?.chain_valid_count ?? 0, checked: dStats?.chain_checked ?? 0 }) }}
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="16" :md="17">
          <div class="chain-anchor-box">
            <span class="chain-anchor-title">{{ $t('watermarkQuality.chainAnchorState') }}</span>
            <div class="anchor-chips">
              <div class="anchor-chip chip-submitted">
                <span class="anchor-chip-value">{{ dStats?.anchor?.submitted ?? '—' }}</span>
                <span class="anchor-chip-label">{{ $t('watermarkQuality.anchorSubmitted') }}</span>
              </div>
              <div class="anchor-chip chip-pending">
                <span class="anchor-chip-value">{{ dStats?.anchor?.pending ?? '—' }}</span>
                <span class="anchor-chip-label">{{ $t('watermarkQuality.anchorPending') }}</span>
              </div>
              <div class="anchor-chip chip-none">
                <span class="anchor-chip-value">{{ dStats?.anchor?.none ?? '—' }}</span>
                <span class="anchor-chip-label">{{ $t('watermarkQuality.anchorNone') }}</span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <h4 class="sub-title">{{ $t('watermarkQuality.chainRecentTitle') }}</h4>
      <el-table
        :data="recentDeliveries"
        stripe
        size="small"
        style="width: 100%"
        class="clickable-table"
        :empty-text="$t('common.noData')"
        :row-class-name="deliveryRowClass"
        @row-click="goForensics"
      >
        <el-table-column :label="$t('watermarkQuality.colDeliveryUuid')" min-width="140">
          <template #default="{ row }"><span class="mono">{{ shortUuid(row.uuid) }}</span></template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.colFid')" min-width="150">
          <template #default="{ row }"><span class="mono">{{ row.fid_short || '—' }}</span></template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.colUser')" width="120">
          <template #default="{ row }">{{ row.user_number || '—' }}</template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.colStatus')" width="110">
          <template #default="{ row }">
            <span class="state-chip" :class="statusChipClass(row.status)">{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.colTime')" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ═══════════ 验证记录（分页表格 · data_type + 时间范围筛选） ═══════════ -->
    <el-card class="records-card" shadow="never">
      <template #header>
        <div class="card-header" :ref="setTourEl('records')">
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
        <el-table-column prop="id" label="ID" width="70" align="right" class-name="tnum-id" />
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
        <el-table-column prop="nc_value" :label="$t('watermarkQuality.ncValue')" width="110" align="right">
          <template #default="{ row }">
            <span v-if="row.nc_value != null" class="state-chip" :class="ncChipClass(row.nc_value)">
              {{ row.nc_value.toFixed(4) }}
            </span>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="verified_by" :label="$t('watermarkQuality.verifiedBy')" width="150" />
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

    <!-- ═══════════ 区五 · 质量指标说明（阈值可视化小卡） ═══════════ -->
    <el-card class="section-card" shadow="never">
      <template #header><span class="section-title" :ref="setTourEl('metrics')">{{ $t('watermarkQuality.metricsExplained') }}</span></template>
      <el-row :gutter="16">
        <el-col v-for="m in metricCards" :key="m.tag" :xs="24" :sm="12" :lg="6">
          <div class="metric-item">
            <div class="metric-header">
              <span class="state-chip" :class="metricChipClass(m.type)">{{ m.tag }}</span>
              <span class="metric-range">{{ m.range }}</span>
            </div>
            <div class="metric-bar">
              <div class="metric-bar-track" :style="{ background: m.gradient }"></div>
              <div
                v-for="mk in m.markers"
                :key="mk.value"
                class="metric-marker"
                :style="{ left: markerPct(mk, m.scale) + '%' }"
              >
                <span class="metric-marker-label">{{ mk.label }}</span>
              </div>
            </div>
            <div class="metric-scale">
              <span>{{ m.scaleLabels[0] }}</span>
              <span>{{ m.scaleLabels[1] }}</span>
              <span>{{ m.scaleLabels[2] }}</span>
            </div>
            <p class="metric-desc">{{ m.desc }}</p>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- ═══════════ 首入引导（ElTour · localStorage 'tour:v1:quality' 只自动弹一次） ═══════════ -->
    <el-tour
      v-model="tourVisible"
      :mask="tourMask"
      :z-index="3000"
      @close="onTourClose"
      @finish="onTourClose"
    >
      <template #indicators="{ current, total }">
        <span
          v-for="i in total"
          :key="i"
          class="el-tour-indicator"
          :class="{ 'is-active': i - 1 === current }"
        />
        <button type="button" class="el-tour-skip" @click="closeTour">
          {{ $t('watermarkQuality.tourSkip') }}
        </button>
      </template>
      <el-tour-step :target="() => tourEls.header" placement="bottom-start" :title="$t('watermarkQuality.tourStep1Title')" :description="$t('watermarkQuality.tourStep1Desc')" />
      <el-tour-step :target="() => tourEls.hero" :title="$t('watermarkQuality.tourStep2Title')" :description="$t('watermarkQuality.tourStep2Desc')" />
      <el-tour-step :target="() => tourEls.gallery" :title="$t('watermarkQuality.tourStep3Title')" :description="$t('watermarkQuality.tourStep3Desc')" />
      <el-tour-step :target="() => tourEls.matrix" :title="$t('watermarkQuality.tourStep4Title')" :description="$t('watermarkQuality.tourStep4Desc')" />
      <el-tour-step :target="() => tourEls.metrics" placement="bottom-start" :title="$t('watermarkQuality.tourStep5Title')" :description="$t('watermarkQuality.tourStep5Desc')" />
      <el-tour-step :target="() => tourEls.records" :title="$t('watermarkQuality.tourStep6Title')" :description="$t('watermarkQuality.tourStep6Desc')" />
    </el-tour>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import {
  Refresh, MapLocation, Picture, Guide,
  DataLine, TrendCharts, Warning, Box, Download, Link, Aim, Odometer, InfoFilled
} from '@element-plus/icons-vue'
import { getVerificationRecords, getBenchmarkResults, getVerificationStats, getBenchmarkStats } from '@/api/watermark'
import { getDeliveryStats } from '@/api/forensics'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent, MarkLineComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { useTheme } from '@/composables/useTheme.js'
import GlossaryHelp from './GlossaryHelp.vue'
import EmptyState from '@/components/common/EmptyState.vue'

// ── ECharts 按需注册：本页用到的渲染器 / 图表 / 组件 ──
use([CanvasRenderer, BarChart, LineChart, PieChart, TooltipComponent, LegendComponent, GridComponent, MarkLineComponent])

const { t } = useI18n()
const router = useRouter()
const { isDark } = useTheme()

// ══════════════════ 首入引导（ElTour · localStorage key 'tour:v1:quality' 只自动弹一次） ══════════════════
const TOUR_KEY = 'tour:v1:quality'
const tourVisible = ref(false)
const tourEls = reactive({ header: null, hero: null, gallery: null, matrix: null, metrics: null, records: null })
// 同时兼容 DOM 元素与组件（el-row / el-card）实例
const setTourEl = (key) => (el) => { tourEls[key] = el?.$el ?? el }
// 遮罩色随模式（纯视觉聚焦层：全局 CSS 已保证不拦截点击、不盖侧栏/顶栏）
const tourMask = computed(() => (isDark.value
  ? { color: 'rgba(10,10,12,0.55)' }
  : { color: 'rgba(10,10,12,0.32)' }))
let tourAutoTimer = null
const startTour = () => { tourVisible.value = true }
const onTourClose = () => {
  try { localStorage.setItem(TOUR_KEY, '1') } catch { /* 隐私模式等场景忽略 */ }
}
// 「跳过」：收起引导并记为已看（同关闭按钮语义）
const closeTour = () => {
  tourVisible.value = false
  onTourClose()
}

// ══════════════════ 数据源：三个统计端点并行 ══════════════════
// 注意：此 ref 绝不能命名为 vLoading —— <script setup> 会把模板里的
// `v-loading` 解析为名为 `vLoading` 的本地绑定（当作自定义指令定义），
// 不再是 ElementPlus 注册的 loading 指令；ref 为 false 时 withDirectives
// 会产出空 dirs 数组，下次补丁直接崩溃（invokeDirectiveHook 读 .value）。
const verifLoading = ref(false)
const vStats = ref(null)        // /api/watermark/verification_stats → stats
const trendLoading = ref(false)
const trendDataType = ref('')   // '' | 'vector' | 'raster' — 仅作用于趋势图
const trendStats = ref(null)    // 带 data_type 的趋势专查
const dLoading = ref(false)
const dStats = ref(null)        // /api/forensics/deliveries/stats → stats
const benchLoading = ref(false)
const benchData = ref(null)     // /api/benchmark/stats（或旧 JSON 回退的等价结构）

const globalLoading = computed(() => verifLoading.value || dLoading.value || benchLoading.value)

// ── 工具 ──
const numOrNull = (x) => (typeof x === 'number' && Number.isFinite(x) ? x : null)
const fmtDateTime = (iso) => {
  if (!iso) return '—'
  const s = String(iso).replace('T', ' ')
  return s.length >= 16 ? s.slice(0, 16) : s
}
// verification_stats.range → 真实验证历史窗口（如 2026-05-15 ~ 2026-10-05）
const verificationWindow = (v) => {
  const a = v?.range?.min_verified_at
  const b = v?.range?.max_verified_at
  if (!a || !b) return ''
  return `${String(a).slice(0, 10)} ~ ${String(b).slice(0, 10)}`
}
// 页头副标题的数据窗口（来自真实 stats，非装饰文案）
const verificationWindowText = computed(() => verificationWindow(vStats.value))

// ══════════════════ 区一 · KPI（count-up rAF，200ms） ══════════════════
const kpiDisplay = reactive({})
const kpiRaf = {}

const animateKpi = (key, target) => {
  if (kpiRaf[key]) cancelAnimationFrame(kpiRaf[key])
  if (target == null || !Number.isFinite(target)) {
    kpiDisplay[key] = null
    return
  }
  // prefers-reduced-motion：直接落值，不做 rAF 补间（§3.10 动效纪律）
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    kpiDisplay[key] = target
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
  if (tourAutoTimer) clearTimeout(tourAutoTimer)
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
  // 状态点（ok/warn/bad）：仅"需要关注/健康"的少数指标亮起，其余保持中性
  const failedDeliveries = (d.by_status || []).find((s) => s.status === 'FAILED')?.count || 0
  return [
    {
      key: 'verify', icon: DataLine, help: 'verify',
      label: t('watermarkQuality.totalVerifications'), value: numOrNull(v.total), fmt: 'int',
      meta: v.min_nc != null && v.max_nc != null
        ? t('watermarkQuality.kpiNcMinMax', { min: v.min_nc.toFixed(3), max: v.max_nc.toFixed(3) })
        : t('watermarkQuality.kpiTotalNote'),
    },
    {
      key: 'avgNc', icon: TrendCharts, help: 'nc',
      label: t('watermarkQuality.avgNc'), value: numOrNull(v.avg_nc), fmt: 'dec4',
      meta: v.p50_nc != null ? t('watermarkQuality.kpiNcMedian', { p50: v.p50_nc.toFixed(4) }) : '',
    },
    {
      key: 'lowNc', icon: Warning, help: 'lowNc',
      label: t('watermarkQuality.lowNc'), value: numOrNull(v.low_nc_count), fmt: 'int',
      meta: v.total ? `${((v.low_nc_count / v.total) * 100).toFixed(1)}% / ${v.total}` : '',
      status: v.total ? (v.low_nc_count > 0 ? 'warn' : 'ok') : null,
    },
    {
      key: 'deliveries', icon: Box, help: 'deliveries',
      label: t('watermarkQuality.kpiDeliveries'), value: numOrNull(d.total), fmt: 'int',
      meta: d.total != null
        ? t('watermarkQuality.kpiDeliveryDetail', { downloaded: d.downloaded_count ?? 0, total: d.total })
        : '',
      status: failedDeliveries > 0 ? 'warn' : null,
    },
    {
      key: 'downloaded', icon: Download, help: 'downloaded',
      label: t('watermarkQuality.kpiDownloaded'), value: numOrNull(d.downloaded_count), fmt: 'int',
      meta: d.total ? `${((d.downloaded_count / d.total) * 100).toFixed(0)}%` : '',
    },
    {
      key: 'chain', icon: Link, help: 'chain',
      label: t('watermarkQuality.kpiChainIntegrity'), value: chainRate, fmt: 'pct1',
      meta: d.chain_checked != null
        ? t('watermarkQuality.kpiChainDetail', { valid: d.chain_valid_count ?? 0, checked: d.chain_checked })
        : '',
      status: d.chain_checked ? (d.chain_valid_count === d.chain_checked ? 'ok' : 'warn') : null,
    },
    {
      key: 'anchor', icon: Aim, help: 'anchor',
      label: t('watermarkQuality.kpiAnchoredBatches'),
      value: anchor.submitted != null && anchor.pending != null ? anchor.submitted + anchor.pending : null,
      fmt: 'int',
      meta: anchor.submitted != null || anchor.pending != null
        ? t('watermarkQuality.kpiAnchorDetail', { submitted: anchor.submitted ?? '—', pending: anchor.pending ?? '—' })
        : '',
      status: anchor.pending > 0 ? 'warn' : null,
    },
    {
      key: 'bench', icon: Odometer, help: 'bench',
      label: t('watermarkQuality.kpiBenchmarkRuns'), value: numOrNull(benchData.value?.runs_count), fmt: 'int',
      meta: snap ? t('watermarkQuality.kpiSnapshot', { time: fmtDateTime(snap) }) : '',
    },
  ]
})

watch(kpiCards, (cards) => {
  cards.forEach((c) => animateKpi(c.key, c.value))
}, { immediate: true })

// ══════════════════ 区二 · 图表 ══════════════════
// 图表墨色：canvas 消费不了 CSS 变量 → 运行时从 design-system 令牌解析（AuthBrandPanel 同源做法，
// 不散落魔法色值）。依赖 isDark 触发重解析：主题类是同步切换的，getComputedStyle 立即可见新值。
const cssVar = (name, fallback) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
const hexToRgba = (color, alpha) => {
  const h = String(color).trim().replace('#', '')
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const n = parseInt(full.slice(0, 6), 16)
  if (!Number.isFinite(n) || full.length !== 6) return color
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`
}
const chartInk = computed(() => {
  void isDark.value // 主题切换即重取
  const accent = cssVar('--accent-9', '#0070f3')
  return {
    axisLabel: cssVar('--text-2', '#333333'),     // 轴刻度：两模式都保持 AA 对比度
    label: cssVar('--text-3', '#666666'),         // 次级说明（图例/轴名）
    grid: cssVar('--border-default', '#eaeaea'),  // 仅横向网格线，低强度
    pieBorder: cssVar('--bg-surface', '#ffffff'), // 环形扇区间隙 = 卡面底色
    tooltipBg: cssVar('--bg-raised', '#ffffff'),
    tooltipBorder: cssVar('--border-default', '#eaeaea'),
    tooltipText: cssVar('--text-1', '#0a0a0a'),
    chainTrack: cssVar('--border-default', '#eaeaea'),
    accent,
    accentSoft: hexToRgba(accent, 0.14),
    success: cssVar('--tint-success-text', '#0e7a4e'),
    danger: cssVar('--tint-danger-text', '#b42318'),
    warning: cssVar('--tint-warning-text', '#9a6b15'),
    neutral: cssVar('--text-4', '#8f8f8f'),
  }
})
// 通用 tooltip（ECharts tooltip 是 HTML 层，可直接吃 CSS 变量：阴影/圆角对齐 el-popper 体系）
const tooltipBase = () => ({
  backgroundColor: chartInk.value.tooltipBg,
  borderColor: chartInk.value.tooltipBorder,
  borderWidth: 1,
  padding: [8, 12],
  textStyle: { color: chartInk.value.tooltipText, fontSize: 12 },
  extraCssText: 'box-shadow: var(--elevation-2); border-radius: var(--radius-md); font-variant-numeric: tabular-nums;',
})
// 通用图例：小圆点 + 次级文字
const legendBase = (data) => ({
  data,
  bottom: 0,
  icon: 'circle',
  itemWidth: 8,
  itemHeight: 8,
  itemGap: 14,
  textStyle: { fontSize: 11, color: chartInk.value.label },
})
// 轴公理：隐藏轴线/刻度，量级以低强度横向网格线承载（Sentry 式克制）
const axisBase = () => ({
  axisLine: { show: false },
  axisTick: { show: false },
  axisLabel: { fontSize: 10, color: chartInk.value.axisLabel },
})
const ySplitBase = () => ({
  ...axisBase(),
  splitLine: { lineStyle: { color: chartInk.value.grid, width: 1 } },
})
// NC 阈值参考线（0.8）：虚线 + 极小标签，不改任何数字口径
const NC_THRESHOLD = 0.8
const thresholdMarkLine = () => ({
  silent: true,
  symbol: 'none',
  label: { show: true, position: 'insideEndTop', formatter: '0.8', fontSize: 10, color: chartInk.value.warning },
  lineStyle: { type: 'dashed', width: 1, color: chartInk.value.warning },
  data: [{ yAxis: NC_THRESHOLD }],
})
// ── NC 直方图（服务端 10 桶；<0.8 危险色 / ≥0.8 成功色，纯色替代渐变） ──
const hasHistogram = computed(() => (vStats.value?.total || 0) > 0)
const ncHistogramOption = computed(() => {
  const hist = vStats.value?.nc_histogram || []
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: hexToRgba(chartInk.value.accent, 0.06) } },
      ...tooltipBase(),
    },
    grid: { left: '2%', right: '2%', bottom: 6, top: 16, containLabel: true },
    xAxis: {
      type: 'category',
      data: hist.map((h) => h.bucket),
      ...axisBase(),
      axisLabel: { fontSize: 10, color: chartInk.value.axisLabel, hideOverlap: true },
    },
    yAxis: { type: 'value', minInterval: 1, ...ySplitBase() },
    series: [{
      name: t('watermarkQuality.seriesCount'),
      type: 'bar',
      barWidth: '52%',
      barMaxWidth: 48,
      data: hist.map((h) => {
        const low = parseFloat(h.bucket) || 0
        return {
          value: h.count,
          itemStyle: {
            borderRadius: [4, 4, 0, 0],
            color: low < NC_THRESHOLD ? chartInk.value.danger : chartInk.value.success,
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
    tooltip: { trigger: 'axis', ...tooltipBase() },
    legend: legendBase([ncLabel, countLabel]),
    grid: { left: '2%', right: '2%', bottom: 34, top: 30, containLabel: true },
    xAxis: {
      type: 'category',
      data: daily.map((d) => String(d.date).slice(5)),
      ...axisBase(),
      axisLabel: { fontSize: 10, color: chartInk.value.axisLabel, hideOverlap: true },
    },
    yAxis: [
      {
        type: 'value', name: 'NC', min: 0, max: 1, nameGap: 10,
        nameTextStyle: { fontSize: 10, color: chartInk.value.label, align: 'right' },
        ...ySplitBase(),
      },
      {
        type: 'value', name: countLabel, minInterval: 1, nameGap: 10,
        nameTextStyle: { fontSize: 10, color: chartInk.value.label },
        ...axisBase(), splitLine: { show: false },
      },
    ],
    series: [
      {
        name: countLabel, type: 'bar', yAxisIndex: 1, barWidth: '52%', barMaxWidth: 40,
        data: daily.map((d) => d.count),
        itemStyle: { color: chartInk.value.accentSoft, borderRadius: [3, 3, 0, 0] },
      },
      {
        name: ncLabel, type: 'line', yAxisIndex: 0, smooth: true, connectNulls: false,
        data: daily.map((d) => d.avg_nc),
        symbolSize: 5,
        lineStyle: { width: 2, color: chartInk.value.accent },
        itemStyle: { color: chartInk.value.accent },
        markLine: thresholdMarkLine(),
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
      ...tooltipBase(),
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
    legend: legendBase([countLabel, ncLabel]),
    grid: { left: '2%', right: '2%', bottom: 34, top: 30, containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map((r) => r.algorithm),
      ...axisBase(),
    },
    yAxis: [
      {
        type: 'value', name: countLabel, minInterval: 1, nameGap: 10,
        nameTextStyle: { fontSize: 10, color: chartInk.value.label },
        ...ySplitBase(),
      },
      {
        type: 'value', name: 'NC', min: 0, max: 1, nameGap: 10,
        nameTextStyle: { fontSize: 10, color: chartInk.value.label, align: 'right' },
        ...axisBase(), splitLine: { show: false },
      },
    ],
    series: [
      {
        name: countLabel, type: 'bar', barWidth: '30%', barMaxWidth: 44,
        data: rows.map((r) => r.count),
        itemStyle: { borderRadius: [4, 4, 0, 0], color: chartInk.value.accentSoft },
      },
      {
        name: ncLabel, type: 'line', yAxisIndex: 1, symbolSize: 7,
        data: rows.map((r) => r.avg_nc),
        lineStyle: { width: 2, color: chartInk.value.accent },
        itemStyle: { color: chartInk.value.accent },
        markLine: thresholdMarkLine(),
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
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', ...tooltipBase() },
  legend: legendBase(),
  series: [{
    type: 'pie',
    radius: ['52%', '72%'],
    center: ['50%', '45%'],
    itemStyle: { borderRadius: 4, borderColor: chartInk.value.pieBorder, borderWidth: 2 },
    label: { formatter: '{b}\n{d}%', fontSize: 11, color: chartInk.value.label, lineHeight: 15 },
    labelLine: { lineStyle: { color: chartInk.value.grid }, length: 8, length2: 8 },
    data: (vStats.value?.by_data_type || []).map((d) => ({
      name: dataTypeLabel(d.data_type),
      value: d.count,
      itemStyle: {
        color: d.data_type === 'vector' ? chartInk.value.accent : d.data_type === 'raster' ? chartInk.value.success : chartInk.value.neutral,
      },
    })),
  }],
}))

// ── 交付健康度（内环 = 交付状态，外环 = 锚定状态，中心叠加汇总） ──
const STATUS_INK_KEY = { READY: 'success', FAILED: 'danger', PENDING: 'warning' }
const hasDelivery = computed(() => (dStats.value?.total || 0) > 0)
const deliveryHealthOption = computed(() => {
  const d = dStats.value || {}
  const anchor = d.anchor || {}
  const ink = chartInk.value
  return {
    tooltip: { trigger: 'item', formatter: '{a} · {b}: {c} ({d}%)', ...tooltipBase() },
    legend: legendBase(),
    series: [
      {
        name: t('watermarkQuality.ringInner'), type: 'pie',
        radius: ['38%', '56%'], center: ['50%', '45%'],
        itemStyle: { borderColor: chartInk.value.pieBorder, borderWidth: 2 },
        label: { show: false }, labelLine: { show: false },
        data: (d.by_status || []).map((s) => ({
          name: s.status, value: s.count,
          itemStyle: { color: ink[STATUS_INK_KEY[s.status]] || ink.neutral },
        })),
      },
      {
        name: t('watermarkQuality.ringOuter'), type: 'pie',
        radius: ['62%', '80%'], center: ['50%', '45%'],
        itemStyle: { borderColor: chartInk.value.pieBorder, borderWidth: 2 },
        label: { show: false }, labelLine: { show: false },
        data: [
          { name: t('watermarkQuality.anchorSubmitted'), value: anchor.submitted || 0, itemStyle: { color: ink.accent } },
          { name: t('watermarkQuality.anchorPending'), value: anchor.pending || 0, itemStyle: { color: ink.warning } },
          { name: t('watermarkQuality.anchorNone'), value: anchor.none || 0, itemStyle: { color: ink.neutral } },
        ].filter((x) => x.value > 0),
      },
    ],
  }
})

// ══════════════════ 区三 · 算法能力矩阵（benchmark/stats 真数据） ══════════════════
const benchResults = computed(() => benchData.value?.results || [])
const benchSnapshotTime = computed(() => {
  const iso = benchData.value?.latest_run?.created_at
  return iso ? fmtDateTime(iso) : ''
})
// [conc] 行为并发压缩变体，与旧页一致地排除在矩阵之外
const benchAttackRows = computed(() =>
  benchResults.value.filter((r) => r.attack && !String(r.attack).includes('[conc]')))
const matrixAlgos = computed(() => [...new Set(benchAttackRows.value.map((r) => r.algorithm))])
const matrixAttacks = computed(() => {
  const seen = []
  for (const r of benchAttackRows.value) {
    if (!seen.includes(r.attack)) seen.push(r.attack)
  }
  return seen
})
const cellOf = (attack, alg) => benchAttackRows.value.find((r) => r.attack === attack && r.algorithm === alg)
const ncCellClass = (nc) => {
  if (nc == null) return ''
  if (nc >= 0.9) return 'nc-good'
  if (nc >= 0.75) return 'nc-mid'
  return 'nc-bad'
}
const benchSummaries = computed(() =>
  benchResults.value.filter((r) => 'stego_psnr' in r || r.embed_error))
const psnrColor = (v) => (v == null ? 'var(--text-tertiary)'
  : v >= 50 ? 'var(--tint-success-text)'
  : v >= 40 ? 'var(--tint-warning-text)'
  : 'var(--tint-danger-text)')

// ══════════════════ 区四 · 证据链健康度 ══════════════════
const chainPct = computed(() => {
  const d = dStats.value
  if (!d?.chain_checked) return 0
  return Math.round((d.chain_valid_count / d.chain_checked) * 100)
})
const chainRingStyle = computed(() => ({
  background: `conic-gradient(${chainPct.value >= 100 ? chartInk.value.success : chartInk.value.warning} ${chainPct.value}%, ${chartInk.value.chainTrack} 0)`,
}))
const shortUuid = (u) => (u ? String(u).slice(0, 8) : '—')
// §4.13 状态色带：行左 4px（仅状态类表格）
const deliveryRowClass = ({ row }) => {
  const t = { READY: 'success', FAILED: 'danger', PENDING: 'warning' }[row.status]
  return t ? `row-band-${t}` : ''
}
const benchRowClass = ({ row }) => (row.embed_error ? 'row-band-danger' : 'row-band-success')
const recentDeliveries = computed(() => dStats.value?.recent || [])
const goForensics = () => router.push('/admin/forensics')

// ══════════════════ 验证记录表（保留 · 新增时间范围筛选） ══════════════════
const loading = ref(false)
const records = ref([])
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const dataTypeFilter = ref('')  // ''=all, 'vector', 'raster'
const dateRange = ref(null)     // [from, to] 'YYYY-MM-DD'

// 状态/数值着色统一为 tint 徽标（state-chip，见样式块）；阈值与旧 el-tag 完全一致
const ncChipClass = (nc) => {
  if (nc == null) return 'state-chip--neutral'
  if (nc >= 0.95) return 'state-chip--success'
  if (nc >= 0.8) return 'state-chip--warning'
  return 'state-chip--danger'
}
const statusChipClass = (s) => ({
  READY: 'state-chip--success',
  FAILED: 'state-chip--danger',
  PENDING: 'state-chip--warning',
  PROCESSING: 'state-chip--info',
}[s] || 'state-chip--neutral')
const metricChipClass = (type) => ({
  primary: 'state-chip--info',
  success: 'state-chip--success',
  warning: 'state-chip--warning',
  danger: 'state-chip--danger',
}[type] || 'state-chip--neutral')

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
  verifLoading.value = true
  try {
    const resp = await getVerificationStats({ days: 30 })
    if (resp?.data?.status) {
      vStats.value = resp.data.stats
    }
  } catch (e) {
    console.error('Failed to fetch verification stats:', e)
  } finally {
    verifLoading.value = false
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

// ══════════════════ 区五 · 质量指标说明（阈值可视化） ══════════════════
const markerPct = (mk, scale) =>
  Math.min(100, Math.max(0, ((mk.value - scale.min) / (scale.max - scale.min)) * 100))

const metricCards = computed(() => {
  const poor = t('watermarkQuality.scalePoor')
  const good = t('watermarkQuality.scaleGood')
  const excellent = t('watermarkQuality.scaleExcellent')
  return [
    {
      tag: 'PSNR', type: 'primary',
      range: t('watermarkQuality.psnrRange'), desc: t('watermarkQuality.psnrDesc'),
      scale: { min: 20, max: 60 }, markers: [{ value: 40, label: '40 dB' }],
      gradient: 'linear-gradient(90deg, var(--tint-danger-text) 0%, var(--tint-warning-text) 42%, var(--tint-success-text) 58%)',
      scaleLabels: [poor, good, excellent],
    },
    {
      tag: 'NC', type: 'success',
      range: t('watermarkQuality.ncRange'), desc: t('watermarkQuality.ncDesc'),
      scale: { min: 0, max: 1 }, markers: [{ value: 0.8, label: '0.8' }, { value: 0.95, label: '0.95' }],
      gradient: 'linear-gradient(90deg, var(--tint-danger-text) 0%, var(--tint-warning-text) 78%, var(--tint-success-text) 96%)',
      scaleLabels: [poor, good, excellent],
    },
    {
      tag: 'SSIM', type: 'warning',
      range: t('watermarkQuality.ssimRange'), desc: t('watermarkQuality.ssimDesc'),
      scale: { min: 0, max: 1 }, markers: [{ value: 0.95, label: '0.95' }],
      gradient: 'linear-gradient(90deg, var(--tint-danger-text) 0%, var(--tint-warning-text) 80%, var(--tint-success-text) 95%)',
      scaleLabels: [poor, good, excellent],
    },
    {
      tag: 'BER', type: 'danger',
      range: t('watermarkQuality.berRange'), desc: t('watermarkQuality.berDesc'),
      scale: { min: 0, max: 0.1 }, markers: [{ value: 0.01, label: '0.01' }],
      gradient: 'linear-gradient(90deg, var(--tint-success-text) 0%, var(--tint-warning-text) 10%, var(--tint-danger-text) 40%)',
      scaleLabels: [excellent, good, poor],
    },
  ]
})

// ══════════════════ v4 · 指标详解数据（ⓘ tooltip + popover 详解卡） ══════════════════
const glossary = computed(() => {
  const m = (k) => t(`watermarkQuality.${k}`)
  const formulaLabel = m('helpFormulaLabel')
  const thresholdLabel = m('thresholdLabel')
  const levels = [m('scalePoor'), m('scaleGood'), m('scaleExcellent')]
  const scaleOf = (gradient, min, max, markers, labels = levels) => ({ gradient, min, max, markers, labels })
  return {
    // ── 五张指标详解卡（文案定稿逐字）──
    nc: {
      tip: m('helpNcTip'), title: m('helpNcTitle'), desc: m('metricNcDesc'),
      formula: m('helpNcFormula'), caveat: m('helpNcCaveat'), formulaLabel, thresholdLabel,
      scale: scaleOf('linear-gradient(90deg, var(--tint-danger-text) 0%, var(--tint-warning-text) 78%, var(--tint-success-text) 96%)',
        0, 1, [{ value: 0.8, label: '0.8' }, { value: 0.95, label: '0.95' }]),
    },
    ber: {
      tip: m('helpBerTip'), title: m('helpBerTitle'), desc: m('metricBerDesc'),
      formula: m('helpBerFormula'), formulaLabel, thresholdLabel,
      scale: scaleOf('linear-gradient(90deg, var(--tint-success-text) 0%, var(--tint-warning-text) 10%, var(--tint-danger-text) 40%)',
        0, 0.1, [{ value: 0.01, label: '0.01' }],
        [m('scaleExcellent'), m('scaleGood'), m('scalePoor')]),
    },
    psnr: {
      tip: m('helpPsnrTip'), title: m('helpPsnrTitle'), desc: m('metricPsnrDesc'),
      formula: m('helpPsnrFormula'), formulaLabel, thresholdLabel,
      scale: scaleOf('linear-gradient(90deg, var(--tint-danger-text) 0%, var(--tint-warning-text) 42%, var(--tint-success-text) 58%)',
        20, 60, [{ value: 40, label: '40 dB' }]),
    },
    ssim: {
      tip: m('helpSsimTip'), title: m('helpSsimTitle'), desc: m('metricSsimDesc'),
      formula: m('helpSsimFormula'), caveat: m('helpSsimCaveat'), formulaLabel, thresholdLabel,
      scale: scaleOf('linear-gradient(90deg, var(--tint-danger-text) 0%, var(--tint-warning-text) 80%, var(--tint-success-text) 95%)',
        0, 1, [{ value: 0.95, label: '0.95' }]),
    },
    recovery: {
      tip: m('helpRecoveryTip'), title: m('helpRecoveryTitle'), desc: m('metricRecoveryDesc'),
      formula: m('helpRecoveryFormula'), caveat: m('helpRecoveryCaveat'), formulaLabel, thresholdLabel,
    },
    // ── KPI / 图表的流程与口径解释 ──
    verify: { tip: m('helpVerifyTip'), title: m('helpVerifyTitle'), desc: m('helpVerifyDesc') },
    lowNc: {
      tip: m('helpLowNcTip'), title: m('helpLowNcTitle'), desc: m('helpLowNcDesc'),
      formulaLabel, thresholdLabel,
      scale: scaleOf('linear-gradient(90deg, var(--tint-danger-text) 0%, var(--tint-warning-text) 78%, var(--tint-success-text) 96%)',
        0, 1, [{ value: 0.8, label: '0.8' }]),
    },
    deliveries: { tip: m('helpDeliveriesTip'), title: m('helpDeliveriesTitle'), desc: m('helpDeliveriesDesc') },
    downloaded: { tip: m('helpDownloadedTip'), title: m('helpDownloadedTitle'), desc: m('helpDownloadedDesc') },
    chain: { tip: m('helpChainTip'), title: m('helpChainTitle'), desc: m('helpChainDesc') },
    anchor: { tip: m('helpAnchorTip'), title: m('helpAnchorTitle'), desc: m('helpAnchorDesc') },
    bench: { tip: m('helpBenchTip'), title: m('helpBenchTitle'), desc: m('helpBenchDesc') },
    histogram: { tip: m('helpHistogramTip'), title: m('helpHistogramTitle'), desc: m('helpHistogramDesc') },
    trend: { tip: m('helpTrendTip'), title: m('helpTrendTitle'), desc: m('helpTrendDesc') },
    algo: { tip: m('helpAlgoTip'), title: m('helpAlgoTitle'), desc: m('helpAlgoDesc') },
    share: { tip: m('helpShareTip'), title: m('helpShareTitle'), desc: m('helpShareDesc') },
    deliveryChart: { tip: m('helpDeliveryChartTip'), title: m('helpDeliveryChartTitle'), desc: m('helpDeliveryChartDesc') },
    matrix: { tip: m('helpMatrixTip'), title: m('helpMatrixTitle'), desc: m('helpMatrixDesc') },
  }
})

onMounted(() => {
  refreshAll()
  // 首入自动讲解：仅当从未看过（localStorage 'tour:v1:quality'）
  let seen = null
  try { seen = localStorage.getItem(TOUR_KEY) } catch { /* 隐私模式等场景忽略 */ }
  if (!seen) {
    tourAutoTimer = setTimeout(() => { tourVisible.value = true }, 800)
  }
})
</script>

<style scoped>
.watermark-quality-dashboard {
  padding: var(--spacing-lg);
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
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-1);
  margin-bottom: 4px;
}

.subtitle {
  color: var(--text-3);
  font-size: var(--font-size-base);
}

.subtitle-meta {
  font-size: var(--font-size-xs);
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
}

.subtitle-meta::before {
  content: '·';
  margin: 0 6px;
}

.page-header-left { min-width: 0; }

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ── 区一 · Hero 统计带（联排细线网格：结构靠 1px 线，不靠 8 层卡片影） ── */
.hero-band { margin-bottom: var(--spacing-lg); }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px; /* 发丝分隔线：容器底色色透出（随模式取 --border-subtle） */
  background: var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--card-ring);
  overflow: hidden;
}

/* 与 el-col 断点对齐：≥1200 四列 / 768–1199 两列 / <768 单列（保证每行填满，不留线洞） */
@media (max-width: 1199px) {
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 767px) {
  .kpi-grid { grid-template-columns: 1fr; }
}

.kpi-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: var(--spacing-md) var(--spacing-md) 14px;
  background: var(--bg-surface);
  transition: background-color var(--duration-150) var(--ease-out-soft);
}

.kpi-card:hover { background: var(--bg-hover); }

.kpi-label-row {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding-right: 14px; /* 给状态点留位 */
}

.kpi-icon {
  color: var(--text-4);
  flex-shrink: 0;
}

.kpi-label {
  font-size: var(--font-size-xs);
  color: var(--text-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  line-height: 1.15;
  letter-spacing: -0.01em;
  color: var(--text-1);
  font-variant-numeric: tabular-nums;
}

.kpi-meta {
  font-size: var(--font-size-xs);
  color: var(--text-3);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 状态点：仅少数"需关注/健康"指标亮起（绿=达阈值，琥珀=有风险） */
.kpi-dot {
  position: absolute;
  top: 15px;
  right: 14px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 0 2px var(--bg-surface);
}

.kpi-dot--ok { background: var(--tint-success-text); }
.kpi-dot--warn { background: var(--tint-warning-text); }
.kpi-dot--bad { background: var(--tint-danger-text); }

/* ── 区二 · 图表画廊（联排细线网格：图表坐在卡面上，去"卡中卡"双层容器） ── */
.section-card {
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-lg);
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
  font-weight: var(--font-weight-semibold);
  color: var(--text-1);
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px; /* 发丝分隔线（容器底色透出） */
  background: var(--border-subtle);
}

/* 与 el-col 断点对齐：<1200 单列 */
@media (max-width: 1199px) {
  .chart-grid { grid-template-columns: 1fr; }
}

.chart-box {
  min-width: 0;
  padding: var(--spacing-md) var(--spacing-md) var(--spacing-sm);
  background: var(--bg-surface);
}

.chart-box--wide { grid-column: 1 / -1; }

.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: var(--spacing-sm);
}

.chart-head-left {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chart-title-row {
  display: inline-flex;
  align-items: center;
}

.chart-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-1);
}

.chart-sub {
  font-size: var(--font-size-xs);
  color: var(--text-3);
}

.chart-holder {
  width: 100%;
  height: 280px;
}

.donut-wrap { position: relative; }

.donut-center {
  position: absolute;
  top: 45%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  pointer-events: none;
}

.donut-center-value {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  line-height: 1.1;
  color: var(--text-1);
  font-variant-numeric: tabular-nums;
}

.donut-center-label {
  font-size: var(--font-size-xs);
  color: var(--text-2);
}

.donut-center-sub {
  font-size: var(--font-size-xs);
  color: var(--text-3);
}

/* ── 验证记录表 ── */
.records-card {
  border-radius: var(--radius-lg);
  margin-bottom: var(--spacing-lg);
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: var(--spacing-md);
}

/* ── 区五 · 指标说明（阈值可视化） ── */
.metric-item {
  height: 100%;
  margin-bottom: 16px;
  padding: 16px;
  background: var(--bg-inset);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.metric-bar {
  position: relative;
  height: 12px;
  margin: 16px 0 6px;
}

.metric-bar-track {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 8px;
  border-radius: 999px;
  opacity: 0.9;
}

.metric-marker {
  position: absolute;
  top: -4px;
  width: 2px;
  height: 16px;
  background: var(--bg-surface);
  box-shadow: 0 0 0 1px var(--border-strong);
  border-radius: 2px;
}

.metric-marker-label {
  position: absolute;
  top: -16px;
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--font-size-xs);
  color: var(--text-2);
  white-space: nowrap;
}

.metric-scale {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: var(--font-size-xs);
  color: var(--text-3);
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.metric-range { font-size: var(--font-size-xs); color: var(--text-2); }

.metric-desc {
  font-size: var(--font-size-sm);
  color: var(--text-2);
  margin: 0;
  line-height: 1.6;
}

/* ── 区三 · 算法能力矩阵 ── */
.matrix-legend {
  font-size: var(--font-size-xs);
  color: var(--text-2);
  margin: 0 0 12px;
}

.attack-name {
  font-weight: var(--font-weight-semibold);
  color: var(--text-1);
}

.nc-cell {
  display: inline-block;
  min-width: 64px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-xs);
  font-variant-numeric: tabular-nums;
}

.nc-good { background: var(--tint-success-bg); color: var(--tint-success-text); }
.nc-mid { background: var(--tint-warning-bg); color: var(--tint-warning-text); }
.nc-bad { background: var(--tint-danger-bg); color: var(--tint-danger-text); }

/* 状态/数值徽标：tint 底 + tint 字（quiet chip 语言，替代 effect=dark 实心 tag） */
.state-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  line-height: 18px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.state-chip--success { background: var(--tint-success-bg); color: var(--tint-success-text); }
.state-chip--warning { background: var(--tint-warning-bg); color: var(--tint-warning-text); }
.state-chip--danger { background: var(--tint-danger-bg); color: var(--tint-danger-text); }
.state-chip--info { background: var(--tint-info-bg); color: var(--tint-info-text); }
.state-chip--neutral { background: var(--tint-neutral-bg); color: var(--text-2); }

.decode-ok { color: var(--tint-success-text); font-weight: var(--font-weight-bold); }
.decode-bad { color: var(--tint-danger-text); font-weight: var(--font-weight-bold); }

.sub-section { margin-top: 20px; }

.sub-title {
  margin: 0 0 10px;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-1);
}

.bench-howto-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 10px;
  font-size: var(--font-size-xs);
  line-height: 1.6;
  color: var(--text-3);
}

.dqim-card {
  margin-top: 20px;
  padding: 18px;
  border-radius: var(--radius-md);
  border: 1px solid var(--tint-info-border);
  background: var(--tint-info-bg);
}

.dqim-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.dqim-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-1);
  margin-right: 8px;
}

.dqim-subtitle { font-size: var(--font-size-xs); color: var(--text-2); }

.dqim-desc {
  font-size: var(--font-size-sm);
  line-height: 1.7;
  color: var(--text-2);
  margin: 10px 0 14px;
}

.dqim-stats { display: flex; gap: 12px; flex-wrap: wrap; }

.dqim-stat {
  display: flex;
  flex-direction: column;
  min-width: 150px;
  padding: 10px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.dqim-stat-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--accent-9);
  font-variant-numeric: tabular-nums;
}

.dqim-stat-label { font-size: var(--font-size-xs); color: var(--text-2); }

/* ── 区四 · 证据链健康度 ── */
.chain-top { margin-bottom: 16px; }

.chain-ring-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
}

.chain-ring {
  width: 132px;
  height: 132px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chain-ring-inner {
  width: 104px;
  height: 104px;
  border-radius: 50%;
  background: var(--bg-surface);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 0 1px var(--border-subtle);
}

.chain-ring-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-1);
  font-variant-numeric: tabular-nums;
}

.chain-ring-label { font-size: var(--font-size-xs); color: var(--text-2); }

.chain-ring-meta { font-size: var(--font-size-xs); color: var(--text-3); }

.chain-anchor-box {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  padding: 10px 4px;
}

.chain-anchor-title { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); color: var(--text-2); }

.anchor-chips { display: flex; gap: 12px; flex-wrap: wrap; }

.anchor-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 110px;
  padding: 12px 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.anchor-chip-value {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  font-variant-numeric: tabular-nums;
}

.anchor-chip-label { font-size: var(--font-size-xs); color: var(--text-2); }

.chip-submitted .anchor-chip-value { color: var(--accent-9); }
.chip-pending .anchor-chip-value { color: var(--tint-warning-text); }
.chip-none .anchor-chip-value { color: var(--text-3); }

.clickable-table :deep(.el-table__row) { cursor: pointer; }

.mono {
  font-family: var(--font-mono);
  font-size: var(--font-size-xs);
}
</style>
