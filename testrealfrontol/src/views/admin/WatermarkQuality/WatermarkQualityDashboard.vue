<template>
  <div class="watermark-quality-dashboard">
    <div class="page-header">
      <div class="page-header-left" :ref="setTourEl('header')">
        <h2>{{ $t('watermarkQuality.title') }}</h2>
        <p class="subtitle">{{ $t('watermarkQuality.subtitle') }}</p>
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

    <!-- ═══════════ 区一 · Hero 统计带（8 KPI · 数字滚动） ═══════════ -->
    <el-row :gutter="16" class="hero-band" :ref="setTourEl('hero')">
      <el-col v-for="card in kpiCards" :key="card.key" :xs="24" :sm="12" :md="8" :lg="6">
        <div class="kpi-card hover-lift">
          <div class="kpi-icon">
            <el-icon size="18"><component :is="card.icon" /></el-icon>
          </div>
          <div class="kpi-body">
            <span class="kpi-value">{{ kpiText(card) }}</span>
            <span class="kpi-label-row">
              <span class="kpi-label">{{ card.label }}</span>
              <GlossaryHelp v-bind="glossary[card.help]" />
            </span>
            <span v-if="card.meta" class="kpi-meta" :title="card.meta">{{ card.meta }}</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ═══════════ 区二 · 图表画廊（ECharts · 全部真数据） ═══════════ -->
    <el-card class="section-card" shadow="never" v-loading="verifLoading" :ref="setTourEl('gallery')">
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
        </el-col>
        <el-col :xs="24" :lg="12">
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
        </el-col>
      </el-row>

      <!-- Row 2 · 算法对比双轴柱线图 -->
      <div class="chart-box">
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

      <!-- Row 3 · 验证数据构成 + 交付健康度 -->
      <el-row :gutter="16">
        <el-col :xs="24" :lg="12">
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
        </el-col>
        <el-col :xs="24" :lg="12">
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
        </el-col>
      </el-row>
    </el-card>

    <!-- ═══════════ 区三 · 算法能力矩阵（基准真数据） ═══════════ -->
    <el-card class="section-card" shadow="never" v-loading="benchLoading" :ref="setTourEl('matrix')">
      <template #header>
        <div class="card-header">
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
              <el-tag
                :type="row.baseline_nc >= 0.95 ? 'success' : row.baseline_nc >= 0.8 ? 'warning' : 'danger'"
                effect="dark"
                size="small"
              >
                {{ row.baseline_nc != null ? row.baseline_nc.toFixed(4) : '—' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.baselineBer')" width="110" align="right">
            <template #default="{ row }">
              {{ row.baseline_ber != null ? row.baseline_ber.toFixed(4) : '—' }}
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.recovery')" width="100">
            <template #default="{ row }">
              <el-tag :type="row.recovery_perfect ? 'success' : 'danger'" size="small">
                {{ row.recovery_perfect ? $t('watermarkQuality.perfect') : $t('watermarkQuality.broken') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="$t('watermarkQuality.colStatus')" min-width="120">
            <template #default="{ row }">
              <el-tag v-if="row.embed_error" type="danger" size="small">{{ $t('watermarkQuality.embedFailed') }}</el-tag>
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
      <div class="dqim-card hover-lift">
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
            <el-tag :type="statusTagType(row.status)" size="small" effect="dark">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.colTime')" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- ═══════════ 验证记录（分页表格 · data_type + 时间范围筛选） ═══════════ -->
    <el-card class="records-card" shadow="never" :ref="setTourEl('records')">
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

    <!-- ═══════════ 区五 · 质量指标说明（阈值可视化小卡） ═══════════ -->
    <el-card class="section-card" shadow="never" :ref="setTourEl('metrics')">
      <template #header><span class="section-title">{{ $t('watermarkQuality.metricsExplained') }}</span></template>
      <el-row :gutter="16">
        <el-col v-for="m in metricCards" :key="m.tag" :xs="24" :sm="12" :lg="6">
          <div class="metric-item">
            <div class="metric-header">
              <el-tag effect="dark" :type="m.type" round>{{ m.tag }}</el-tag>
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
      <el-tour-step :target="() => tourEls.header" :title="$t('watermarkQuality.tourStep1Title')" :description="$t('watermarkQuality.tourStep1Desc')" />
      <el-tour-step :target="() => tourEls.hero" :title="$t('watermarkQuality.tourStep2Title')" :description="$t('watermarkQuality.tourStep2Desc')" />
      <el-tour-step :target="() => tourEls.gallery" :title="$t('watermarkQuality.tourStep3Title')" :description="$t('watermarkQuality.tourStep3Desc')" />
      <el-tour-step :target="() => tourEls.matrix" :title="$t('watermarkQuality.tourStep4Title')" :description="$t('watermarkQuality.tourStep4Desc')" />
      <el-tour-step :target="() => tourEls.metrics" :title="$t('watermarkQuality.tourStep5Title')" :description="$t('watermarkQuality.tourStep5Desc')" />
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
import { use, graphic } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { useTheme } from '@/composables/useTheme.js'
import GlossaryHelp from './GlossaryHelp.vue'
import EmptyState from '@/components/common/EmptyState.vue'

// ── ECharts 按需注册：本页用到的渲染器 / 图表 / 组件 ──
use([CanvasRenderer, BarChart, LineChart, PieChart, TooltipComponent, LegendComponent, GridComponent])

const { t } = useI18n()
const router = useRouter()
const { isDark } = useTheme()

// ══════════════════ 首入引导（ElTour · localStorage key 'tour:v1:quality' 只自动弹一次） ══════════════════
const TOUR_KEY = 'tour:v1:quality'
const tourVisible = ref(false)
const tourEls = reactive({ header: null, hero: null, gallery: null, matrix: null, metrics: null, records: null })
// 同时兼容 DOM 元素与组件（el-row / el-card）实例
const setTourEl = (key) => (el) => { tourEls[key] = el?.$el ?? el }
// 遮罩色随模式：深色 A 用 rgba(10,10,12,.65)，浅色 B 用中性黑 50%
const tourMask = computed(() => (isDark.value
  ? { color: 'rgba(10,10,12,0.65)' }
  : { color: 'rgba(10,10,10,0.5)' }))
let tourAutoTimer = null
const startTour = () => { tourVisible.value = true }
const onTourClose = () => {
  try { localStorage.setItem(TOUR_KEY, '1') } catch { /* 隐私模式等场景忽略 */ }
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
  return [
    {
      key: 'verify', icon: DataLine, help: 'verify',
      label: t('watermarkQuality.totalVerifications'), value: numOrNull(v.total), fmt: 'int',
      meta: verificationWindow(v) || (v.min_nc != null && v.max_nc != null
        ? t('watermarkQuality.kpiNcMinMax', { min: v.min_nc.toFixed(3), max: v.max_nc.toFixed(3) })
        : t('watermarkQuality.kpiTotalNote')),
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
    },
    {
      key: 'deliveries', icon: Box, help: 'deliveries',
      label: t('watermarkQuality.kpiDeliveries'), value: numOrNull(d.total), fmt: 'int',
      meta: d.total != null
        ? t('watermarkQuality.kpiDeliveryDetail', { downloaded: d.downloaded_count ?? 0, total: d.total })
        : '',
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
    },
    {
      key: 'anchor', icon: Aim, help: 'anchor',
      label: t('watermarkQuality.kpiAnchoredBatches'),
      value: anchor.submitted != null && anchor.pending != null ? anchor.submitted + anchor.pending : null,
      fmt: 'int',
      meta: anchor.submitted != null || anchor.pending != null
        ? t('watermarkQuality.kpiAnchorDetail', { submitted: anchor.submitted ?? '—', pending: anchor.pending ?? '—' })
        : '',
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
// 图表配色（canvas 内无法用 CSS 变量，随 isDark 切换；对齐 A/B 设计体系）
const chartInk = computed(() => (isDark.value
  ? {
      axisLabel: '#a0a0ab',
      axisLabelMinor: '#6e6e7a',
      pieBorder: '#111114',
      chartLabel: '#a0a0ab',
      tooltipBg: 'rgba(17,17,20,0.96)',
      tooltipBorder: 'rgba(94,106,210,0.35)',
      tooltipText: '#ededf0',
      chainTrack: 'rgba(255,255,255,0.08)',
      accent: '#5e6ad2',
      accentHi: '#6e79de',
      accentSoft: 'rgba(94,106,210,0.16)',
      green: '#5cc08f',
      greenHi: '#6fce9f',
      red: '#e06a6a',
      amber: '#d6a75c',
      amberHi: '#e0b97a',
      neutral: '#6e6e7a',
    }
  : {
      axisLabel: '#666666',
      axisLabelMinor: '#8f8f8f',
      pieBorder: '#ffffff',
      chartLabel: '#666666',
      tooltipBg: 'rgba(255,255,255,0.98)',
      tooltipBorder: '#eaeaea',
      tooltipText: '#0a0a0a',
      chainTrack: '#eaeaea',
      accent: '#0070f3',
      accentHi: '#4d9bf7',
      accentSoft: 'rgba(0,112,243,0.12)',
      green: '#0e7a4e',
      greenHi: '#3e9c74',
      red: '#b42318',
      amber: '#9a6b15',
      amberHi: '#d6a75c',
      neutral: '#8f8f8f',
    }))
// ── NC 直方图（服务端 10 桶，低于 0.8 冷暖双色渐变） ──
const hasHistogram = computed(() => (vStats.value?.total || 0) > 0)
const ncHistogramOption = computed(() => {
  const hist = vStats.value?.nc_histogram || []
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, backgroundColor: chartInk.value.tooltipBg, borderColor: chartInk.value.tooltipBorder, textStyle: { color: chartInk.value.tooltipText } },
    grid: { left: '4%', right: '4%', bottom: '6%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: hist.map((h) => h.bucket),
      axisLabel: { fontSize: 10, color: chartInk.value.axisLabel },
    },
    yAxis: { type: 'value', minInterval: 1, axisLabel: { color: chartInk.value.axisLabel } },
    series: [{
      name: t('watermarkQuality.seriesCount'),
      type: 'bar',
      barWidth: '56%',
      barMaxWidth: 56,
      data: hist.map((h) => {
        const low = parseFloat(h.bucket) || 0
        return {
          value: h.count,
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: low < 0.8
              ? new graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: chartInk.value.amberHi }, { offset: 1, color: chartInk.value.red },
              ])
              : new graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: chartInk.value.greenHi }, { offset: 1, color: chartInk.value.green },
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
    tooltip: { trigger: 'axis', backgroundColor: chartInk.value.tooltipBg, borderColor: chartInk.value.tooltipBorder, textStyle: { color: chartInk.value.tooltipText } },
    legend: { data: [ncLabel, countLabel], bottom: 0, textStyle: { fontSize: 11, color: chartInk.value.chartLabel } },
    grid: { left: '4%', right: '4%', bottom: '18%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: daily.map((d) => String(d.date).slice(5)),
      axisLabel: { fontSize: 10, color: chartInk.value.axisLabel },
    },
    yAxis: [
      { type: 'value', name: 'NC', min: 0, max: 1, axisLabel: { color: chartInk.value.axisLabel } },
      {
        type: 'value', name: countLabel, minInterval: 1,
        axisLabel: { color: chartInk.value.axisLabelMinor }, splitLine: { show: false },
      },
    ],
    series: [
      {
        name: countLabel, type: 'bar', yAxisIndex: 1, barWidth: '52%', barMaxWidth: 56,
        data: daily.map((d) => d.count),
        itemStyle: { color: chartInk.value.accentSoft, borderRadius: [3, 3, 0, 0] },
      },
      {
        name: ncLabel, type: 'line', yAxisIndex: 0, smooth: true, connectNulls: false,
        data: daily.map((d) => d.avg_nc),
        symbolSize: 6,
        lineStyle: { width: 2.5, color: chartInk.value.accent },
        itemStyle: { color: chartInk.value.accent },
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
      backgroundColor: chartInk.value.tooltipBg,
      borderColor: chartInk.value.tooltipBorder,
      textStyle: { color: chartInk.value.tooltipText },
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
    legend: { data: [countLabel, ncLabel], bottom: 0, textStyle: { fontSize: 11, color: chartInk.value.chartLabel } },
    grid: { left: '4%', right: '4%', bottom: '18%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: rows.map((r) => r.algorithm),
      axisLabel: { color: chartInk.value.axisLabel },
    },
    yAxis: [
      { type: 'value', name: countLabel, minInterval: 1, axisLabel: { color: chartInk.value.axisLabel } },
      { type: 'value', name: 'NC', min: 0, max: 1, axisLabel: { color: chartInk.value.axisLabelMinor }, splitLine: { show: false } },
    ],
    series: [
      {
        name: countLabel, type: 'bar', barWidth: '32%', barMaxWidth: 56,
        data: rows.map((r) => r.count),
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: chartInk.value.accentHi }, { offset: 1, color: chartInk.value.accent },
          ]),
        },
      },
      {
        name: ncLabel, type: 'line', yAxisIndex: 1, symbolSize: 9,
        data: rows.map((r) => r.avg_nc),
        lineStyle: { width: 2.5, color: chartInk.value.green },
        itemStyle: { color: chartInk.value.green },
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
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', backgroundColor: chartInk.value.tooltipBg, borderColor: chartInk.value.tooltipBorder, textStyle: { color: chartInk.value.tooltipText } },
  legend: { bottom: 0, textStyle: { fontSize: 11, color: chartInk.value.chartLabel } },
  series: [{
    type: 'pie',
    radius: ['50%', '72%'],
    center: ['50%', '44%'],
    itemStyle: { borderRadius: 6, borderColor: chartInk.value.pieBorder, borderWidth: 2 },
    label: { formatter: '{b}\n{d}%', fontSize: 11, color: chartInk.value.chartLabel },
    data: (vStats.value?.by_data_type || []).map((d) => ({
      name: dataTypeLabel(d.data_type),
      value: d.count,
      itemStyle: {
        color: d.data_type === 'vector' ? chartInk.value.accent : d.data_type === 'raster' ? chartInk.value.green : chartInk.value.neutral,
      },
    })),
  }],
}))

// ── 交付健康度（内环 = 交付状态，外环 = 锚定状态，中心叠加汇总） ──
const STATUS_INK_KEY = { READY: 'green', FAILED: 'red', PENDING: 'amber' }
const hasDelivery = computed(() => (dStats.value?.total || 0) > 0)
const deliveryHealthOption = computed(() => {
  const d = dStats.value || {}
  const anchor = d.anchor || {}
  const ink = chartInk.value
  return {
    tooltip: { trigger: 'item', formatter: '{a} · {b}: {c} ({d}%)', backgroundColor: chartInk.value.tooltipBg, borderColor: chartInk.value.tooltipBorder, textStyle: { color: chartInk.value.tooltipText } },
    legend: { bottom: 0, textStyle: { fontSize: 11, color: chartInk.value.chartLabel } },
    series: [
      {
        name: t('watermarkQuality.ringInner'), type: 'pie',
        radius: ['38%', '58%'], center: ['50%', '44%'],
        itemStyle: { borderColor: chartInk.value.pieBorder, borderWidth: 2 },
        label: { show: false }, labelLine: { show: false },
        data: (d.by_status || []).map((s) => ({
          name: s.status, value: s.count,
          itemStyle: { color: ink[STATUS_INK_KEY[s.status]] || ink.neutral },
        })),
      },
      {
        name: t('watermarkQuality.ringOuter'), type: 'pie',
        radius: ['64%', '84%'], center: ['50%', '44%'],
        itemStyle: { borderColor: chartInk.value.pieBorder, borderWidth: 2 },
        label: { show: false }, labelLine: { show: false },
        data: [
          { name: t('watermarkQuality.anchorSubmitted'), value: anchor.submitted || 0, itemStyle: { color: ink.accent } },
          { name: t('watermarkQuality.anchorPending'), value: anchor.pending || 0, itemStyle: { color: ink.amber } },
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
  background: `conic-gradient(${chainPct.value >= 100 ? chartInk.value.green : chartInk.value.amber} ${chainPct.value}%, ${chartInk.value.chainTrack} 0)`,
}))
const shortUuid = (u) => (u ? String(u).slice(0, 8) : '—')
const statusTagType = (s) => ({ READY: 'success', FAILED: 'danger', PENDING: 'warning' }[s] || 'info')
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
  font-weight: 600;
  color: var(--text-primary, #0a0a0a);
  margin-bottom: 4px;
}

.subtitle {
  color: var(--text-secondary, #666666);
  font-size: 14px;
}

.page-header-left { min-width: 0; }

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* ── 区一 · Hero 统计带（A：近黑卡+灰阶层次 / B：白卡+1px 边框 · 安静排版） ── */
.hero-band { margin-bottom: 8px; }

.hero-band .el-col { margin-bottom: 16px; }

.kpi-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  height: 100%;
  padding: 20px;
  background: var(--bg-primary, #ffffff);
  /* §4.11 ring 描边（1px 前景 alpha 10%，替代 border，避免双线） */
  border: none;
  box-shadow: var(--card-ring);
  border-radius: var(--radius-lg, 8px);
}

.hover-lift {
  transition: box-shadow var(--duration-200) var(--ease-out-soft);
}

.hover-lift:hover {
  transform: none;
  box-shadow: var(--card-ring-hover);
}

.kpi-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md, 8px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary, #666666);
  background: var(--bg-tertiary, #fafafa);
  border: 1px solid var(--border-color, #eaeaea);
  flex-shrink: 0;
}

.kpi-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.kpi-value {
  font-size: 24px;
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.01em;
  color: var(--text-primary, #0a0a0a);
  font-variant-numeric: tabular-nums;
}

.kpi-label-row {
  display: inline-flex;
  align-items: center;
  margin-top: 2px;
}

.kpi-label {
  font-size: 13px;
  color: var(--text-secondary, #666666);
}

.kpi-meta {
  font-size: 12px;
  color: var(--text-tertiary, #8f8f8f);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── 区二 · 图表画廊 ── */
.section-card {
  border-radius: var(--radius-lg, 8px);
  margin-bottom: 24px;
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
  color: var(--text-primary, #0a0a0a);
}

.chart-box {
  background: var(--bg-tertiary, #fafafa);
  border: 1px solid var(--border-color-light, #f0f0f0);
  border-radius: var(--radius-md, 8px);
  padding: 16px;
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

.chart-title-row {
  display: inline-flex;
  align-items: center;
}

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #0a0a0a);
}

.chart-sub {
  font-size: 12px;
  color: var(--text-tertiary, #8f8f8f);
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
  font-weight: 600;
  line-height: 1.1;
  color: var(--text-primary, #0a0a0a);
  font-variant-numeric: tabular-nums;
}

.donut-center-label {
  font-size: 12px;
  color: var(--text-secondary, #666666);
}

.donut-center-sub {
  font-size: 12px;
  color: var(--text-tertiary, #8f8f8f);
}

/* ── 验证记录表 ── */
.records-card {
  border-radius: var(--radius-lg, 8px);
  margin-bottom: 24px;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

/* ── 区五 · 指标说明（阈值可视化） ── */
.metric-item {
  height: 100%;
  margin-bottom: 16px;
  padding: 16px;
  background: var(--bg-tertiary, #fafafa);
  border-radius: var(--radius-lg, 8px);
  border: 1px solid var(--border-color, #eaeaea);
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
  background: var(--bg-primary, #ffffff);
  box-shadow: 0 0 0 1px var(--border-color-hover, #d4d4d4);
  border-radius: 2px;
}

.metric-marker-label {
  position: absolute;
  top: -16px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: var(--text-secondary, #666666);
  white-space: nowrap;
}

.metric-scale {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--text-tertiary, #8f8f8f);
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.metric-range { font-size: 12px; color: var(--text-secondary, #666666); }

.metric-desc {
  font-size: 13px;
  color: var(--text-secondary, #666666);
  margin: 0;
  line-height: 1.6;
}

/* ── 区三 · 算法能力矩阵 ── */
.matrix-legend {
  font-size: 12px;
  color: var(--text-secondary, #666666);
  margin: 0 0 12px;
}

.attack-name {
  font-weight: 600;
  color: var(--text-primary, #0a0a0a);
}

.nc-cell {
  display: inline-block;
  min-width: 64px;
  padding: 2px 8px;
  border-radius: var(--radius-sm, 6px);
  font-weight: 600;
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.nc-good { background: var(--tint-success-bg, rgba(16, 185, 129, 0.12)); color: var(--tint-success-text, #047857); }
.nc-mid { background: var(--tint-warning-bg, rgba(245, 158, 11, 0.14)); color: var(--tint-warning-text, #b45309); }
.nc-bad { background: var(--tint-danger-bg, rgba(239, 68, 68, 0.12)); color: var(--tint-danger-text, #b91c1c); }

.decode-ok { color: var(--tint-success-text, #0e7a4e); font-weight: 700; }
.decode-bad { color: var(--tint-danger-text, #b42318); font-weight: 700; }

.sub-section { margin-top: 20px; }

.sub-title {
  margin: 0 0 10px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #0a0a0a);
}

.bench-howto-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-tertiary, #8f8f8f);
}

.dqim-card {
  margin-top: 20px;
  padding: 18px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--tint-info-border, rgba(0, 112, 243, 0.2));
  background: var(--tint-info-bg, #f0f7ff);
}

.dqim-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.dqim-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #0a0a0a);
  margin-right: 8px;
}

.dqim-subtitle { font-size: 12px; color: var(--text-secondary, #666666); }

.dqim-desc {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary, #666666);
  margin: 10px 0 14px;
}

.dqim-stats { display: flex; gap: 12px; flex-wrap: wrap; }

.dqim-stat {
  display: flex;
  flex-direction: column;
  min-width: 150px;
  padding: 10px 16px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #eaeaea);
  border-radius: var(--radius-md, 8px);
}

.dqim-stat-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary-500, #0070f3);
  font-variant-numeric: tabular-nums;
}

.dqim-stat-label { font-size: 12px; color: var(--text-secondary, #666666); }

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
  background: var(--bg-primary, #fff);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 0 1px var(--border-color-light, #f1f5f9);
}

.chain-ring-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--text-primary, #0a0a0a);
  font-variant-numeric: tabular-nums;
}

.chain-ring-label { font-size: 12px; color: var(--text-secondary, #666666); }

.chain-ring-meta { font-size: 12px; color: var(--text-tertiary, #8f8f8f); }

.chain-anchor-box {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 10px;
  padding: 10px 4px;
}

.chain-anchor-title { font-size: 13px; font-weight: 600; color: var(--text-secondary, #666666); }

.anchor-chips { display: flex; gap: 12px; flex-wrap: wrap; }

.anchor-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 110px;
  padding: 12px 20px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #eaeaea);
  border-radius: var(--radius-md, 8px);
}

.anchor-chip-value {
  font-size: 20px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.anchor-chip-label { font-size: 12px; color: var(--text-secondary, #666666); }

.chip-submitted .anchor-chip-value { color: var(--primary-500, #0070f3); }
.chip-pending .anchor-chip-value { color: var(--tint-warning-text, #9a6b15); }
.chip-none .anchor-chip-value { color: var(--text-tertiary, #8f8f8f); }

.clickable-table :deep(.el-table__row) { cursor: pointer; }

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
  font-size: 12px;
}
</style>
