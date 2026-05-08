<template>
  <div class="watermark-quality-dashboard">
    <div class="page-header">
      <h2>{{ t('watermarkQuality.title') || 'Watermark Quality Dashboard' }}</h2>
      <p class="subtitle">{{ t('watermarkQuality.subtitle') || 'Monitor watermark verification records and quality metrics' }}</p>
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
            <span class="stat-label">{{ t('watermarkQuality.totalVerifications') || 'Total Verifications' }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card hover-lift" shadow="hover">
        <div class="stat-content">
          <div class="stat-icon" style="background: linear-gradient(135deg, #10b981, #059669)">
            <el-icon size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.avgNc }}</span>
            <span class="stat-label">{{ t('watermarkQuality.avgNc') || 'Average NC Value' }}</span>
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
            <span class="stat-label">{{ t('watermarkQuality.lowNc') || 'Low NC (< 0.8)' }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="stat-card hover-lift" shadow="hover">
        <div class="stat-content">
          <div class="stat-icon" style="background: linear-gradient(135deg, #3b82f6, #2563eb)">
            <el-icon size="24"><Timer /></el-icon>
          </div>
          <div class="stat-info">
            <span class="stat-value">{{ stats.todayVerifications }}</span>
            <span class="stat-label">{{ t('watermarkQuality.today') || "Today's Verifications" }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- Verification Records Table -->
    <el-card class="records-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>{{ t('watermarkQuality.records') || 'Verification Records' }}</span>
          <el-button type="primary" :icon="Refresh" @click="fetchRecords" :loading="loading">
            {{ t('common.refresh') || 'Refresh' }}
          </el-button>
        </div>
      </template>

      <el-table
        :data="records"
        v-loading="loading"
        stripe
        style="width: 100%"
        :empty-text="t('common.noData') || 'No data'"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="nc_value" :label="t('watermarkQuality.ncValue') || 'NC Value'" width="120">
          <template #default="{ row }">
            <el-tag
              :type="getNcTagType(row.nc_value)"
              effect="dark"
              round
            >
              {{ row.nc_value?.toFixed(4) || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="verified_by" :label="t('watermarkQuality.verifiedBy') || 'Verified By'" width="140" />
        <el-table-column prop="verified_at" :label="t('watermarkQuality.verifiedAt') || 'Verified At'" width="180">
          <template #default="{ row }">
            {{ formatDate(row.verified_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" :label="t('watermarkQuality.ipAddress') || 'IP Address'" width="140" />
        <el-table-column prop="original_hash" :label="t('watermarkQuality.originalHash') || 'Original Hash'" min-width="200" show-overflow-tooltip />
        <el-table-column prop="extracted_hash" :label="t('watermarkQuality.extractedHash') || 'Extracted Hash'" min-width="200" show-overflow-tooltip />
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

    <!-- NC Value Distribution Chart -->
    <el-card class="chart-card" shadow="never">
      <template #header>
        <span>{{ t('watermarkQuality.ncDistribution') || 'NC Value Distribution' }}</span>
      </template>
      <div ref="chartRef" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Check, TrendCharts, Warning, Timer, Refresh } from '@element-plus/icons-vue'
import { getVerificationRecords } from '@/api/watermark'
import * as echarts from 'echarts'

const { t } = useI18n()
const loading = ref(false)
const records = ref([])
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const chartRef = ref(null)

const stats = computed(() => {
  const totalVerifications = records.value.length
  const ncValues = records.value.filter(r => r.nc_value != null).map(r => r.nc_value)
  const avgNc = ncValues.length > 0 ? (ncValues.reduce((a, b) => a + b, 0) / ncValues.length).toFixed(4) : '-'
  const lowNcCount = ncValues.filter(v => v < 0.8).length
  const today = new Date().toISOString().split('T')[0]
  const todayVerifications = records.value.filter(r => r.verified_at?.startsWith(today)).length
  return { totalVerifications, avgNc, lowNcCount, todayVerifications }
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

const fetchRecords = async () => {
  loading.value = true
  try {
    const resp = await getVerificationRecords({ page: currentPage.value, pageSize })
    if (resp.data.status) {
      records.value = resp.data.data || []
      total.value = resp.data.pages?.total || 0
    }
  } catch (e) {
    console.error('Failed to fetch verification records:', e)
  } finally {
    loading.value = false
    nextTick(renderChart)
  }
}

const renderChart = () => {
  if (!chartRef.value || records.value.length === 0) return
  const chart = echarts.init(chartRef.value)
  const ncValues = records.value.filter(r => r.nc_value != null).map(r => r.nc_value)

  const buckets = { '0.0-0.5': 0, '0.5-0.7': 0, '0.7-0.8': 0, '0.8-0.9': 0, '0.9-0.95': 0, '0.95-1.0': 0 }
  ncValues.forEach(v => {
    if (v < 0.5) buckets['0.0-0.5']++
    else if (v < 0.7) buckets['0.5-0.7']++
    else if (v < 0.8) buckets['0.7-0.8']++
    else if (v < 0.9) buckets['0.8-0.9']++
    else if (v < 0.95) buckets['0.9-0.95']++
    else buckets['0.95-1.0']++
  })

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Object.keys(buckets), axisLabel: { color: '#64748b' } },
    yAxis: { type: 'value', axisLabel: { color: '#64748b' } },
    series: [{
      data: Object.values(buckets),
      type: 'bar',
      itemStyle: {
        borderRadius: [6, 6, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#667eea' },
          { offset: 1, color: '#764ba2' }
        ])
      }
    }],
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }
  })
}

onMounted(fetchRecords)
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
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 14px;
}

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

.stat-info {
  display: flex;
  flex-direction: column;
}

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

.records-card {
  margin-bottom: 24px;
  border-radius: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.chart-card {
  border-radius: 14px;
}

.chart-container {
  width: 100%;
  height: 300px;
}
</style>
