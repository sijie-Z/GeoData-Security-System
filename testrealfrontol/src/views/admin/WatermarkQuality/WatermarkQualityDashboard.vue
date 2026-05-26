<template>
  <div class="watermark-quality-dashboard">
    <div class="page-header">
      <h2>{{ $t('watermarkQuality.title') }}</h2>
      <p class="subtitle">{{ $t('watermarkQuality.subtitle') }}</p>
    </div>

    <!-- Stats Cards -->
    <div class="stats-row">
      <el-card class="stat-card hover-lift" shadow="hover">
        <div class="stat-content">
          <div class="stat-icon" style="background: linear-gradient(135deg, #667eea, #764ba2)">
            <el-icon size="24"><Check /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.totalVerifications }}</span>
            <span class="stat-label">{{ $t('watermarkQuality.totalVerifications') }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card hover-lift" shadow="hover">
        <div class="stat-content">
          <div class="stat-icon" style="background: linear-gradient(135deg, #3b82f6, #1d4ed8)">
            <el-icon size="24"><MapLocation /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.vectorVerifications }}</span>
            <span class="stat-label">{{ $t('watermarkQuality.totalVectorVerifications') }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card hover-lift" shadow="hover">
        <div class="stat-content">
          <div class="stat-icon" style="background: linear-gradient(135deg, #10b981, #059669)">
            <el-icon size="24"><Picture /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.rasterVerifications }}</span>
            <span class="stat-label">{{ $t('watermarkQuality.totalRasterVerifications') }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card hover-lift" shadow="hover">
        <div class="stat-content">
          <div class="stat-icon" style="background: linear-gradient(135deg, #6366f1, #4f46e5)">
            <el-icon size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.avgVectorNc }}</span>
            <span class="stat-label">{{ $t('watermarkQuality.avgVectorNc') }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card hover-lift" shadow="hover">
        <div class="stat-content">
          <div class="stat-icon" style="background: linear-gradient(135deg, #22c55e, #16a34a)">
            <el-icon size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.avgRasterNc }}</span>
            <span class="stat-label">{{ $t('watermarkQuality.avgRasterNc') }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card hover-lift" shadow="hover">
        <div class="stat-content">
          <div class="stat-icon" style="background: linear-gradient(135deg, #f59e0b, #d97706)">
            <el-icon size="24"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.lowNcCount }}</span>
            <span class="stat-label">{{ $t('watermarkQuality.lowNc') }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Data Type Filter Tabs -->
    <el-card class="records-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="card-header-left">
            <span>{{ $t('watermarkQuality.records') }}</span>
            <el-radio-group v-model="dataTypeFilter" size="small" style="margin-left: 16px;">
              <el-radio-button value="">{{ $t('watermarkQuality.allTypes') }}</el-radio-button>
              <el-radio-button value="vector">{{ $t('watermarkQuality.vectorLabel') }}</el-radio-button>
              <el-radio-button value="raster">{{ $t('watermarkQuality.rasterLabel') }}</el-radio-button>
            </el-radio-group>
          </div>
          <el-button type="primary" :icon="Refresh" @click="fetchRecords" :loading="loading">
            {{ $t('common.refresh') }}
          </el-button>
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

    <!-- NC Value Distribution Chart (by data type) -->
    <el-card class="chart-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('watermarkQuality.ncDistribution') }}</span>
          <el-tag size="small" type="info">矢量 vs 栅格</el-tag>
        </div>
      </template>
      <div ref="chartRef" class="chart-container"></div>
      <div v-if="records.length === 0 && !loading" class="empty-hint">
        暂无验证记录。执行水印提取/验证操作后，数据将实时更新。
      </div>
    </el-card>

    <!-- ====== 矢量水印算法 ====== -->
    <el-card class="algo-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ $t('watermarkQuality.vectorAlgoSection') }}</span>
          <el-tag type="primary" size="small">{{ $t('watermarkQuality.vectorLabel') }}</el-tag>
        </div>
      </template>
      <p class="algo-description">{{ $t('watermarkQuality.vectorAlgoDesc') }}</p>

      <el-row :gutter="16" style="margin-bottom: 16px;">
        <el-col :span="6">
          <div class="vector-stat-box">
            <span class="vector-stat-value">{{ vectorStats.totalRecords }}</span>
            <span class="vector-stat-label">{{ $t('watermarkQuality.totalVerifications') }}</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="vector-stat-box">
            <span class="vector-stat-value" :style="{ color: vectorStats.avgNc !== '-' ? '#6366f1' : '#94a3b8' }">
              {{ vectorStats.avgNc }}
            </span>
            <span class="vector-stat-label">AVG NC</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="vector-stat-box">
            <span class="vector-stat-value" :style="{ color: vectorStats.avgBer !== '-' ? '#f59e0b' : '#94a3b8' }">
              {{ vectorStats.avgBer }}
            </span>
            <span class="vector-stat-label">AVG BER</span>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="vector-stat-box">
            <span class="vector-stat-value">{{ vectorStats.ncRange }}</span>
            <span class="vector-stat-label">NC 范围</span>
          </div>
        </el-col>
      </el-row>

      <!-- 矢量水印算法对比表 -->
      <el-table :data="vectorAlgoSummary" stripe style="width: 100%">
        <el-table-column prop="name" :label="$t('watermarkQuality.algoName')" width="150" />
        <el-table-column prop="domain" :label="$t('watermarkQuality.algoDomain')" width="130" />
        <el-table-column :label="$t('watermarkQuality.baselineNc')" width="110">
          <template #default="{ row }">
            <el-tag :type="row.baselineNc >= 0.99 ? 'success' : 'warning'" effect="dark" size="small">
              {{ row.baselineNc?.toFixed(4) || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.baselineBer')" width="90">
          <template #default="{ row }">{{ row.baselineBer?.toFixed(4) || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.vertexCount')" width="100">
          <template #default="{ row }">{{ row.avgVertices }}</template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.embeddingCapacity')" width="120">
          <template #default="{ row }">{{ row.capacity }}</template>
        </el-table-column>
        <el-table-column prop="robustnessNote" :label="$t('watermarkQuality.robustness')" min-width="200" />
      </el-table>
    </el-card>

    <!-- ====== 算法鲁棒性基准测试（栅格） ====== -->
    <el-card class="algo-card" shadow="never" v-loading="benchLoading">
      <template #header>
        <div class="card-header">
          <span>{{ $t('watermarkQuality.benchmarkTitle') }}</span>
          <el-tag type="success" size="small" style="margin-left: 8px;">{{ $t('watermarkQuality.rasterLabel') }}</el-tag>
          <el-tag v-if="benchMeta" type="info" size="small">{{ benchMeta.timestamp?.split('T')[0] }}</el-tag>
        </div>
      </template>

      <!-- 算法对比表 -->
      <el-table :data="algorithmComparison" stripe style="width: 100%; margin-bottom: 24px">
        <el-table-column prop="name" :label="$t('watermarkQuality.algoName')" width="120" />
        <el-table-column prop="domain" :label="$t('watermarkQuality.algoDomain')" width="100" />
        <el-table-column :label="$t('watermarkQuality.algoReversible')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.reversible === '是' ? 'success' : 'danger'" size="small">{{ row.reversible }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.stegoPsnr')" width="120">
          <template #default="{ row }">
            <span :style="{ color: row.stegoPsnr >= 50 ? '#10b981' : row.stegoPsnr >= 40 ? '#f59e0b' : '#ef4444', fontWeight: 700 }">
              {{ row.stegoPsnr }} dB
            </span>
          </template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.baselineNc')" width="110">
          <template #default="{ row }">
            <el-tag :type="row.baselineNc >= 0.99 ? 'success' : 'danger'" effect="dark" size="small">
              {{ row.baselineNc?.toFixed(4) || '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.baselineBer')" width="90">
          <template #default="{ row }">{{ row.baselineBer?.toFixed(4) || '-' }}</template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.recovery')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.recoveryPerfect ? 'success' : 'danger'" size="small">
              {{ row.recoveryPerfect ? ($t('watermarkQuality.perfect') || '完美') : ($t('watermarkQuality.broken') || '失败') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('watermarkQuality.robustness')" min-width="200">
          <template #default="{ row }">
            <el-tag :type="row.robustnessLevel === ($t('watermarkQuality.robustnessFragile') || '脆弱') ? 'danger' : row.robustnessLevel === ($t('watermarkQuality.robustnessNone') || '无效') ? 'info' : 'warning'" size="small">
              {{ row.robustnessLevel }}
            </el-tag>
            <span style="margin-left: 8px; font-size: 12px; color: #64748b;">{{ row.robustnessNote }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 攻击下鲁棒性对比：四合一图表 -->
      <div class="charts-grid">
        <div class="chart-box">
          <h5 class="chart-title">NC 对比（越高越好，> 0.95 为优秀）</h5>
          <div ref="chartNcRef" class="chart-inner"></div>
        </div>
        <div class="chart-box">
          <h5 class="chart-title">BER 对比（越低越好，&lt; 0.01 为优秀）</h5>
          <div ref="chartBerRef" class="chart-inner"></div>
        </div>
        <div class="chart-box">
          <h5 class="chart-title">恢复 PSNR 对比（攻击后能否还原原图）</h5>
          <div ref="chartRecRef" class="chart-inner"></div>
        </div>
        <div class="chart-box">
          <h5 class="chart-title">隐写质量对比（PSNR / SSIM）</h5>
          <div ref="chartStegoRef" class="chart-inner"></div>
        </div>
      </div>

      <!-- 关键发现 -->
      <div class="findings-section">
        <h4>{{ $t('watermarkQuality.keyFindings') }}</h4>
        <el-alert
          v-for="(finding, idx) in keyFindings"
          :key="idx"
          :title="finding.title"
          :description="finding.description"
          :type="finding.type"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        />
        <!-- Vector finding -->
        <el-alert
          :title="$t('watermarkQuality.findingVectorTitle')"
          :description="vectorFindingDesc"
          type="primary"
          :closable="false"
          show-icon
        />
      </div>
    </el-card>

    <!-- Quality Metrics Explained -->
    <el-card class="metrics-card" shadow="never">
      <template #header><span>{{ $t('watermarkQuality.metricsExplained') }}</span></template>
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
import { ref, onMounted, computed, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, TrendCharts, Warning, Timer, Refresh, MapLocation, Picture } from '@element-plus/icons-vue'
import { getVerificationRecords, getBenchmarkResults } from '@/api/watermark'

const { t } = useI18n()
const loading = ref(false)
const records = ref([])
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const dataTypeFilter = ref('')  // ''=all, 'vector', 'raster'
const chartRef = ref(null)
const chartNcRef = ref(null)
const chartBerRef = ref(null)
const chartRecRef = ref(null)
const chartStegoRef = ref(null)

// ── Benchmark state ──
const benchLoading = ref(false)
const benchMeta = ref(null)
const benchResults = ref([])

// ── Stats computed from records ──
const stats = computed(() => {
  const total_ = records.value.length
  const vectorRecs = records.value.filter(r => r.data_type === 'vector')
  const rasterRecs = records.value.filter(r => r.data_type === 'raster')
  const ncAll = records.value.filter(r => r.nc_value != null).map(r => r.nc_value)
  const ncVec = vectorRecs.filter(r => r.nc_value != null).map(r => r.nc_value)
  const ncRas = rasterRecs.filter(r => r.nc_value != null).map(r => r.nc_value)

  const avg = (arr) => arr.length > 0 ? (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(4) : '-'
  const lowNcCount = ncAll.filter(v => v < 0.8).length

  return {
    totalVerifications: total_,
    vectorVerifications: vectorRecs.length,
    rasterVerifications: rasterRecs.length,
    avgVectorNc: avg(ncVec),
    avgRasterNc: avg(ncRas),
    lowNcCount,
  }
})

// ── Vector algorithm stats from real records ──
const vectorStats = computed(() => {
  const vecRecs = records.value.filter(r => r.data_type === 'vector' && r.nc_value != null)
  const ncVals = vecRecs.map(r => r.nc_value)
  const totalRecords = vecRecs.length
  const avgNc = totalRecords > 0 ? (ncVals.reduce((a, b) => a + b, 0) / totalRecords).toFixed(4) : '-'
  const ncRange = totalRecords > 0
    ? `${Math.min(...ncVals).toFixed(2)} ~ ${Math.max(...ncVals).toFixed(2)}`
    : '-'
  // BER — approximate from the relationship BER ≈ (1 - NC) / 2 for random errors
  const avgBer = totalRecords > 0 ? (1 - ncVals.reduce((a, b) => a + b, 0) / totalRecords).toFixed(4) : '-'
  return { totalRecords, avgNc, avgBer, ncRange }
})

// ── Vector algorithm summary table ──
const vectorAlgoSummary = computed(() => {
  const vecRecs = records.value.filter(r => r.data_type === 'vector' && r.nc_value != null)
  if (vecRecs.length === 0) return []

  const avgNc = vecRecs.reduce((s, r) => s + r.nc_value, 0) / vecRecs.length
  const avgBer = 1 - avgNc
  const avgVertices = '~5000'
  const capacity = 'n=4 / 顶点'

  return [{
    name: t('watermarkQuality.vectorAlgoName') || 'Vector Geo Embedding',
    domain: '空间域 (坐标)',
    baselineNc: avgNc,
    baselineBer: avgBer,
    avgVertices,
    capacity,
    robustnessNote: '十进制坐标精度损失导致BER偏高；QR纠错码可容忍此错误率',
  }]
})

// ── Vector finding description ──
const vectorFindingDesc = computed(() => {
  const s = vectorStats.value
  return `NC=${s.avgNc}，BER=${s.avgBer}。水印通过修改坐标值的低位二进制位嵌入，坐标四舍五入到小数点后固定位数时会产生量子化误差，破坏部分水印比特。适合：数据溯源、版权证明（即使有比特错误，QR码仍可通过错误校正识别）。共 ${s.totalRecords} 条矢量验证记录。`
})

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

// ── Fetch records with data_type filter ──
const fetchRecords = async () => {
  loading.value = true
  try {
    const params = { page: currentPage.value, pageSize }
    if (dataTypeFilter.value) {
      params.data_type = dataTypeFilter.value
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
    nextTick(renderChart)
  }
}

// ── Fetch benchmark results ──
const fetchBenchmark = async () => {
  benchLoading.value = true
  try {
    const resp = await getBenchmarkResults()
    if (resp.data.status) {
      benchMeta.value = resp.data.data.benchmark_metadata
      benchResults.value = resp.data.data.results || []
    }
  } catch (e) {
    console.error('Failed to fetch benchmark results:', e)
  } finally {
    benchLoading.value = false
    nextTick(renderAllBenchmarkCharts)
  }
}

// ── NC distribution chart (dual series) ──
const renderChart = async () => {
  if (!chartRef.value || records.value.length === 0) return
  const echarts = await import('echarts')
  const chart = echarts.init(chartRef.value)

  const vecNc = records.value.filter(r => r.data_type === 'vector' && r.nc_value != null).map(r => r.nc_value)
  const rasNc = records.value.filter(r => r.data_type === 'raster' && r.nc_value != null).map(r => r.nc_value)

  const buckets = ['0.0-0.5', '0.5-0.7', '0.7-0.8', '0.8-0.9', '0.9-0.95', '0.95-1.0']
  const toBucket = (v) => {
    if (v < 0.5) return 0
    if (v < 0.7) return 1
    if (v < 0.8) return 2
    if (v < 0.9) return 3
    if (v < 0.95) return 4
    return 5
  }
  const bucketCounts = (arr) => {
    const cnt = [0, 0, 0, 0, 0, 0]
    arr.forEach(v => cnt[toBucket(v)]++)
    return cnt
  }

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: {
      data: [t('watermarkQuality.vectorLabel') || 'Vector', t('watermarkQuality.rasterLabel') || 'Raster'],
      bottom: 0, textStyle: { fontSize: 11 },
    },
    xAxis: { type: 'category', data: buckets, axisLabel: { color: '#64748b' } },
    yAxis: { type: 'value', axisLabel: { color: '#64748b' } },
    series: [
      {
        name: t('watermarkQuality.vectorLabel') || 'Vector',
        data: bucketCounts(vecNc), type: 'bar',
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#3b82f6' }, { offset: 1, color: '#1d4ed8' }
          ])
        }
      },
      {
        name: t('watermarkQuality.rasterLabel') || 'Raster',
        data: bucketCounts(rasNc), type: 'bar',
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#10b981' }, { offset: 1, color: '#059669' }
          ])
        }
      }
    ],
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true }
  })
}

// ── All benchmark charts ──
function _getAttackData() {
  return benchResults.value.filter(r => r.attack && !r.attack?.includes('[conc]'))
}

const renderAllBenchmarkCharts = async () => {
  const atkResults = _getAttackData()
  if (atkResults.length === 0) return

  const echarts = await import('echarts')
  window._echartsInstance = echarts

  const attackNames = [...new Set(atkResults.map(r => r.attack))]
  const algos = ['LSB', 'DWT']
  const colors = ['#667eea', '#f59e0b']

  const xOpts = { type: 'category', data: attackNames, axisLabel: { rotate: 30, fontSize: 10, color: '#64748b' } }
  const legendOpts = { data: algos, bottom: 0, textStyle: { fontSize: 11 } }

  const ncChart = chartNcRef.value ? echarts.init(chartNcRef.value) : null
  if (ncChart) {
    ncChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: legendOpts,
      xAxis: xOpts,
      yAxis: { type: 'value', name: 'NC', min: 0, max: 1, axisLabel: { color: '#64748b' } },
      series: algos.map((alg, i) => ({
        name: alg, type: 'bar',
        data: attackNames.map(a => atkResults.find(r => r.attack === a && r.algorithm === alg)?.nc ?? null),
        itemStyle: { borderRadius: [4, 4, 0, 0], color: colors[i] },
      })),
      grid: { left: '8%', right: '4%', bottom: '15%', top: '8%', containLabel: true },
    })
  }

  const berChart = chartBerRef.value ? echarts.init(chartBerRef.value) : null
  if (berChart) {
    berChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: legendOpts,
      xAxis: xOpts,
      yAxis: { type: 'value', name: 'BER', min: 0, max: 1, axisLabel: { color: '#64748b' } },
      series: algos.map((alg, i) => ({
        name: alg, type: 'bar',
        data: attackNames.map(a => atkResults.find(r => r.attack === a && r.algorithm === alg)?.ber ?? null),
        itemStyle: { borderRadius: [4, 4, 0, 0], color: colors[i] },
      })),
      grid: { left: '8%', right: '4%', bottom: '15%', top: '8%', containLabel: true },
    })
  }

  const recChart = chartRecRef.value ? echarts.init(chartRecRef.value) : null
  if (recChart) {
    recChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: legendOpts,
      xAxis: xOpts,
      yAxis: { type: 'value', name: 'dB', axisLabel: { color: '#64748b' } },
      series: algos.map((alg, i) => ({
        name: alg, type: 'bar',
        data: attackNames.map(a => atkResults.find(r => r.attack === a && r.algorithm === alg)?.recovery_psnr ?? null),
        itemStyle: { borderRadius: [4, 4, 0, 0], color: colors[i] },
      })),
      grid: { left: '8%', right: '4%', bottom: '15%', top: '8%', containLabel: true },
    })
  }

  const stegoChart = chartStegoRef.value ? echarts.init(chartStegoRef.value) : null
  if (stegoChart) {
    const summaries = benchResults.value.filter(r => 'stego_psnr' in r && !r.embed_error)
    const algoNames = summaries.map(s => s.algorithm)
    stegoChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['PSNR (dB)', 'SSIM×100'], bottom: 0, textStyle: { fontSize: 10 } },
      xAxis: { type: 'category', data: algoNames, axisLabel: { color: '#64748b', fontSize: 12 } },
      yAxis: [
        { type: 'value', name: 'PSNR (dB)', axisLabel: { color: '#64748b' } },
        { type: 'value', name: 'SSIM×100', axisLabel: { color: '#64748b' } },
      ],
      series: [
        {
          name: 'PSNR (dB)', type: 'bar',
          data: summaries.map(s => s.stego_psnr),
          itemStyle: { borderRadius: [4, 4, 0, 0], color: '#10b981' },
        },
        {
          name: 'SSIM×100', type: 'bar', yAxisIndex: 1,
          data: summaries.map(s => Math.round((s.stego_ssim || 0) * 10000) / 100),
          itemStyle: { borderRadius: [4, 4, 0, 0], color: '#f59e0b' },
        },
      ],
      grid: { left: '8%', right: '8%', bottom: '15%', top: '8%', containLabel: true },
    })
  }
}

// ── Watch filter change to re-fetch ──
watch(dataTypeFilter, () => {
  currentPage.value = 1
  fetchRecords()
})

// ── Algorithm comparison (from real benchmark, raster only) ──
const algorithmComparison = computed(() => {
  const summaries = benchResults.value.filter(r => 'stego_psnr' in r && !r.embed_error)
  return summaries.map(s => {
    const alg = s.algorithm
    const isDWT = alg === 'DWT'
    const isLSB = alg === 'LSB'
    const isHist = alg === 'Histogram'

    const atkResults = benchResults.value.filter(r => r.algorithm === alg && r.attack && !r.attack?.includes('[conc]'))
    const avgNcUnderAttack = atkResults.length > 0
      ? atkResults.reduce((sum, r) => sum + (r.nc || 0), 0) / atkResults.length
      : 0

    let robustnessLevel, robustnessNote
    if (isHist) {
      robustnessLevel = t('watermarkQuality.robustnessNA') || '不适用'
      robustnessNote = '所有非纯色图像上均嵌入失败'
    } else if (isDWT) {
      robustnessLevel = t('watermarkQuality.robustnessNone') || '无效'
      robustnessNote = `提取已损坏 — NC=${s.baseline_nc?.toFixed(3) || 'N/A'}（≈随机），QIM奇偶性Bug`
    } else {
      robustnessLevel = t('watermarkQuality.robustnessFragile') || '脆弱'
      robustnessNote = `受攻击后NC降至~${avgNcUnderAttack.toFixed(2)} — 仅适用于篡改检测`
    }

    return {
      name: alg,
      domain: isDWT ? '频域 (DWT)' : '空间域',
      reversible: (isLSB && s.recovery_perfect) ? '是' : (isDWT ? '否（已损坏）' : '否'),
      robustnessScore: isLSB ? 1 : isDWT ? 0 : 0,
      capacity: isLSB ? '全像素级' : isDWT ? 'LL子带' : '峰值限制',
      useCase: isLSB ? '篡改检测、可逆恢复' : isDWT ? '提取损坏，需修复' : '需要近均匀图像',
      stegoPsnr: s.stego_psnr || 'N/A',
      stegoSsim: s.stego_ssim || 'N/A',
      baselineNc: s.baseline_nc,
      baselineBer: s.baseline_ber,
      recoveryPerfect: s.recovery_perfect,
      robustnessLevel,
      robustnessNote,
    }
  })
})

// ── Key findings from benchmark (raster only) ──
const keyFindings = computed(() => {
  const findings = []
  const lsb = benchResults.value.find(r => r.algorithm === 'LSB' && 'stego_psnr' in r)
  const dwt = benchResults.value.find(r => r.algorithm === 'DWT' && 'stego_psnr' in r)
  const hist = benchResults.value.find(r => r.algorithm === 'Histogram' && r.embed_error)

  if (lsb) {
    findings.push({
      title: t('watermarkQuality.findingLsbTitle') || 'LSB：隐写质量优秀，但水印极其脆弱',
      description: t('watermarkQuality.findingLsbDesc') || `PSNR=${lsb.stego_psnr}dB（肉眼不可见），SSIM=${lsb.stego_ssim}。无攻击时可完美提取（NC=1.0，BER=0），可完美恢复原图。但任何攻击都会彻底摧毁水印——LSB位平面被破坏导致随机噪声。最适合：篡改检测、需要完全可逆恢复的场景。`,
      type: 'success',
    })
  }
  if (dwt) {
    findings.push({
      title: t('watermarkQuality.findingDwtTitle') || 'DWT：QIM提取存在Bug — 返回的是系数奇偶性，而非水印比特',
      description: t('watermarkQuality.findingDwtDesc') || `PSNR=${dwt.stego_psnr}dB（肉眼可见退化）。基准NC=${dwt.baseline_nc?.toFixed(4)}（≈随机，期望值应为1.0）。提取代码 \`round(value/step) % 2\` 返回的是量化后DWT系数的奇偶性。NC在所有攻击下稳定在~0.23，是因为它始终读取的是系数奇偶性，而非水印真的"鲁棒"。`,
      type: 'warning',
    })
  }
  if (hist) {
    findings.push({
      title: t('watermarkQuality.findingHistTitle') || '直方图平移：在自然图像上数学上不可行',
      description: t('watermarkQuality.findingHistDesc') || `需要峰值像素数 ≥ 图像总像素数（${hist.embed_error?.match(/need (\d+) bits but peak bin has only (\d+)/)?.[0] || '容量不足'}）。代码将水印缩放到了全图尺寸，除非图像是纯色，否则永远无法满足。这是实现层面的设计缺陷。`,
      type: 'danger',
    })
  }
  findings.push({
    title: t('watermarkQuality.findingRecommendTitle') || '建议：保留LSB，移除DWT和直方图平移',
    description: t('watermarkQuality.findingRecommendDesc') || 'LSB是目前唯一可正确工作的可逆水印算法。DWT存在已确认的提取bug（QIM奇偶性错误）。直方图平移因容量限制对自然图像不可用。如果未来需要抗攻击的鲁棒水印，可以考虑实现修正后的DWT+QIM或扩频水印方案。',
    type: 'info',
  })
  return findings
})

onMounted(() => {
  fetchRecords()
  fetchBenchmark()
})
</script>

<style scoped>
.watermark-quality-dashboard {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
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

.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card { border-radius: 14px; }

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
}

.stat-info { display: flex; flex-direction: column; }

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #1e293b);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary, #64748b);
}

.records-card { margin-bottom: 24px; border-radius: 14px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  flex-wrap: wrap;
  gap: 8px;
}

.card-header-left {
  display: flex;
  align-items: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.chart-card { border-radius: 14px; margin-bottom: 24px; }

.chart-container {
  width: 100%;
  height: 300px;
}

.empty-hint {
  text-align: center;
  color: #94a3b8;
  padding: 40px 0;
  font-size: 14px;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.chart-box {
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 12px;
}

.chart-title {
  margin: 0 0 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.chart-inner {
  width: 100%;
  height: 280px;
}

.algo-card { border-radius: 14px; margin-top: 24px; }

.algo-description {
  color: #64748b;
  font-size: 14px;
  margin: 0 0 16px 0;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.vector-stat-box {
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 16px;
  text-align: center;
}

.vector-stat-value {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 4px;
}

.vector-stat-label {
  font-size: 12px;
  color: #64748b;
  text-transform: uppercase;
}

.findings-section {
  margin-top: 24px;
  padding: 20px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.findings-section h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.metrics-card { border-radius: 14px; margin-top: 24px; }

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
