<template>
  <div class="employee-dashboard" v-loading="loading">
    <section class="hero glass">
      <div>
        <h1>{{ $t('empDashboard.title') }} · {{ greeting }}，{{ userStore.user_name || $t('empDashboard.defaultEmployee') }}</h1>
        <p>{{ $t('empDashboard.subtitle') }}</p>
        <div class="meta">{{ $t('empDashboard.todayVisits') }}：{{ todayVisits }} · {{ $t('empDashboard.lastLogin') }}：{{ lastLoginTime }}</div>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="refreshNow">{{ $t('empDashboard.refreshData') }}</el-button>
        <el-button @click="goTo('/employee/data_viewing')">{{ $t('empDashboard.enterDataCatalog') }}</el-button>
      </div>
    </section>

    <section class="kpi-grid">
      <div class="kpi glass">
        <span>{{ $t('empDashboard.totalApplications') }}</span>
        <h2>{{ metrics.totalApplications }}</h2>
      </div>
      <div class="kpi glass warn">
        <span>{{ $t('empDashboard.pendingApplications') }}</span>
        <h2>{{ metrics.pendingApplications }}</h2>
      </div>
      <div class="kpi glass ok">
        <span>{{ $t('empDashboard.downloadableData') }}</span>
        <h2>{{ metrics.downloadableData }}</h2>
      </div>
      <div class="kpi glass info">
        <span>{{ $t('empDashboard.myDownloads') }}</span>
        <h2>{{ metrics.myDownloads }}</h2>
      </div>
    </section>

    <section class="grid">
      <el-card class="glass" shadow="never">
        <template #header>
          <div class="panel-header">
            <h3>{{ $t('empDashboard.trendTitle') }}</h3>
            <el-tag type="info" effect="light">{{ $t('empDashboard.dbAggregation') }}</el-tag>
          </div>
        </template>
        <div ref="trendChartRef" class="chart"></div>
      </el-card>

      <el-card class="glass" shadow="never">
        <template #header><div class="panel-header"><h3>{{ $t('empDashboard.statusDistribution') }}</h3></div></template>
        <div ref="statusChartRef" class="chart small"></div>
      </el-card>

      <el-card class="glass" shadow="never">
        <template #header><div class="panel-header"><h3>{{ $t('empDashboard.dataTypePreference') }}</h3></div></template>
        <div ref="dataTypeChartRef" class="chart small"></div>
      </el-card>
    </section>

    <section class="grid">
      <el-card class="glass" shadow="never">
        <template #header><div class="panel-header"><h3>{{ $t('empDashboard.quickActions') }}</h3></div></template>
        <div class="action-grid">
          <div class="action-card" @click="goTo('/employee/data_viewing')">
            <b>{{ $t('empDashboard.dataCatalog') }}</b>
            <span>{{ $t('empDashboard.browseResources') }}</span>
          </div>
          <div class="action-card" @click="goTo('/employee/data_application')">
            <b>{{ $t('empDashboard.myApplications') }}</b>
            <span>{{ $t('empDashboard.viewProgress') }}</span>
          </div>
          <div class="action-card" @click="goTo('/employee/data_download')">
            <b>{{ $t('empDashboard.approvedDownloads') }}</b>
            <span>{{ $t('empDashboard.getAuthorizedData') }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="glass" shadow="never">
        <template #header><div class="panel-header"><h3>{{ $t('empDashboard.systemAnnouncements') }}</h3></div></template>
        <div v-if="announcements.length === 0" class="empty">{{ $t('empDashboard.noAnnouncements') }}</div>
        <div v-else class="announcement-list">
          <div v-for="a in announcements" :key="a.id" class="announcement-item">
            <div>
              <b>{{ a.title }}</b>
              <p>{{ a.content }}</p>
            </div>
            <small>{{ a.created_at }}</small>
          </div>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { useUserStore } from '@/stores/userStore';
import { useRouter } from 'vue-router';
import * as echarts from 'echarts';
import axios from '@/utils/Axios';

const { t } = useI18n();
const router = useRouter();
const userStore = useUserStore();
const loading = ref(true);

const trendChartRef = ref(null);
const statusChartRef = ref(null);
const dataTypeChartRef = ref(null);
let trendIns = null;
let statusIns = null;
let dataTypeIns = null;

const announcements = ref([]);
const todayVisits = ref(0);
const lastLoginTime = ref('—');

const metrics = ref({ totalApplications: 0, pendingApplications: 0, downloadableData: 0, myDownloads: 0 });
const chartData = ref([]);
const dataTypePreference = ref({ vector: 0, raster: 0 });
const applicationStatusDist = ref({ pending: 0, approved: 0, rejected: 0 });

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return t('empDashboard.greetingMorning');
  if (h < 18) return t('empDashboard.greetingAfternoon');
  return t('empDashboard.greetingEvening');
});

const fetchDashboard = async () => {
  loading.value = true;
  try {
    const response = await axios.get('/api/employee/dashboard');
    const data = response.data?.data || {};
    metrics.value = {
      totalApplications: data.total_applications || 0,
      pendingApplications: data.pending_applications || 0,
      downloadableData: data.downloadable_data || 0,
      myDownloads: data.my_downloads || 0
    };
    chartData.value = data.daily_trend || [];
    dataTypePreference.value = data.data_type_preference || { vector: 0, raster: 0 };
    applicationStatusDist.value = data.application_status_distribution || { pending: 0, approved: 0, rejected: 0 };
    todayVisits.value = data.today_visits || 0;
    lastLoginTime.value = data.last_login_time || '—';

    const ann = await axios.get('/api/announcements', { params: { page: 1, pageSize: 5 } });
    announcements.value = ann.data?.data?.list || [];

    await nextTick();
    renderCharts();
  } finally {
    loading.value = false;
  }
};

const renderCharts = () => {
  if (trendChartRef.value) {
    trendIns?.dispose();
    trendIns = echarts.init(trendChartRef.value);
    trendIns.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: [t('empDashboard.applicationCount'), t('empDashboard.downloadCount')] },
      xAxis: { type: 'category', data: chartData.value.map(i => i.date) },
      yAxis: { type: 'value' },
      series: [
        { name: t('empDashboard.applicationCount'), type: 'line', smooth: true, data: chartData.value.map(i => i.applications || 0) },
        { name: t('empDashboard.downloadCount'), type: 'bar', barMaxWidth: 16, data: chartData.value.map(i => i.downloads || 0) }
      ]
    });
  }

  if (statusChartRef.value) {
    statusIns?.dispose();
    statusIns = echarts.init(statusChartRef.value);
    statusIns.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { value: applicationStatusDist.value.pending || 0, name: t('empDashboard.pending') },
          { value: applicationStatusDist.value.approved || 0, name: t('empDashboard.approved') },
          { value: applicationStatusDist.value.rejected || 0, name: t('empDashboard.rejected') }
        ]
      }]
    });
  }

  if (dataTypeChartRef.value) {
    dataTypeIns?.dispose();
    dataTypeIns = echarts.init(dataTypeChartRef.value);
    dataTypeIns.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        data: [
          { value: dataTypePreference.value.vector || 0, name: t('empDashboard.vector') },
          { value: dataTypePreference.value.raster || 0, name: t('empDashboard.raster') }
        ]
      }]
    });
  }
};

const goTo = (path) => router.push(path);
const refreshNow = () => fetchDashboard();

const onResize = () => {
  trendIns?.resize();
  statusIns?.resize();
  dataTypeIns?.resize();
};

onMounted(async () => {
  await fetchDashboard();
  window.addEventListener('resize', onResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
  trendIns?.dispose();
  statusIns?.dispose();
  dataTypeIns?.dispose();
});
</script>

<style scoped>
.employee-dashboard {
  padding: 20px;
  background: radial-gradient(1200px 600px at 0% 0%, #0f172a 0%, #f8fafc 45%, #e2e8f0 100%);
  min-height: calc(100vh - 80px);
}
.glass {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 16px;
}
.hero {
  padding: 18px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.hero h1 { margin: 0; font-size: 24px; }
.hero p { margin: 6px 0 0; color: #475569; }
.hero .meta { margin-top: 8px; color: #64748b; }
.hero-actions { display: flex; gap: 10px; align-items: center; }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.kpi { padding: 14px; }
.kpi span { color: #64748b; font-size: 13px; }
.kpi h2 { margin: 6px 0; font-size: 28px; }
.warn { border-left: 4px solid #f59e0b; }
.ok { border-left: 4px solid #22c55e; }
.info { border-left: 4px solid #3b82f6; }

.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 12px;
}
.panel-header { display:flex; justify-content: space-between; align-items: center; }
.panel-header h3 { margin: 0; font-size: 16px; }
.chart { height: 320px; }
.chart.small { height: 260px; }

.action-grid { display: grid; gap: 10px; }
.action-card {
  padding: 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, #f8fafc, #eef2ff);
  border: 1px solid #e2e8f0;
  cursor: pointer;
}
.action-card b { display:block; color:#1e293b; margin-bottom:4px; }
.action-card span { color:#475569; }

.announcement-list { display: grid; gap: 10px; }
.announcement-item { display:flex; justify-content: space-between; align-items:center; padding: 10px; border-radius: 10px; background: #f8fafc; }
.announcement-item p { margin: 6px 0 0; color: #64748b; }
.empty { color:#94a3b8; padding: 10px 0; }

@media (max-width: 1200px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .grid { grid-template-columns: 1fr; }
}
</style>
