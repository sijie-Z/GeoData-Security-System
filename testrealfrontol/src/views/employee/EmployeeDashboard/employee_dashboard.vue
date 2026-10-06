<template>
  <div class="employee-dashboard" v-loading="loading">
    <template v-if="loading">
      <div class="skeleton-hero glass">
        <div class="sk-line long"></div>
        <div class="sk-line medium"></div>
        <div class="sk-line short"></div>
      </div>
      <div class="kpi-grid">
        <div v-for="n in 4" :key="n" class="kpi glass"><div class="sk-line short"></div><div class="sk-line medium"></div></div>
      </div>
    </template>
    <template v-else>
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
        <v-chart
          class="chart"
          :option="trendOption"
          autoresize
        />
      </el-card>

      <el-card class="glass" shadow="never">
        <template #header><div class="panel-header"><h3>{{ $t('empDashboard.statusDistribution') }}</h3></div></template>
        <v-chart
          class="chart small"
          :option="statusOption"
          autoresize
        />
      </el-card>

      <el-card class="glass" shadow="never">
        <template #header><div class="panel-header"><h3>{{ $t('empDashboard.dataTypePreference') }}</h3></div></template>
        <v-chart
          class="chart small"
          :option="dataTypeOption"
          autoresize
        />
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
    </template>
  </div>
</template>

<script setup>
defineOptions({ name: 'EmployeeDashboard' });
import { ref, computed, onMounted, onActivated } from 'vue';
import { useI18n } from 'vue-i18n';
import { useUserStore } from '@/stores/userStore';
import { useRouter } from 'vue-router';
import { getDashboard } from '@/api/employee';
import { getAnnouncements } from '@/api/admin';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart, BarChart, PieChart } from 'echarts/charts';
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components';
import VChart from 'vue-echarts';
import { useTheme } from '@/composables/useTheme.js';

// ── ECharts 按需注册：仅本页用到的渲染器 / 图表 / 组件 ──
use([CanvasRenderer, LineChart, BarChart, PieChart, TooltipComponent, LegendComponent, GridComponent]);

const { t } = useI18n();
const { isDark } = useTheme();
const router = useRouter();
const userStore = useUserStore();
const loading = ref(true);

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
    const [response, ann] = await Promise.all([
      getDashboard(),
      getAnnouncements({ page: 1, pageSize: 5 })
    ]);
    const data = response?.data?.data || {};
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
    announcements.value = ann.data?.data?.list || [];

    loading.value = false;
  } catch (err) {
    console.error('获取仪表盘数据失败:', err);
    loading.value = false;
  }
};

// ── 图表主题色（canvas 内无法用 CSS 变量，随 isDark 切换） ──
const ink = computed(() => (isDark.value
  ? {
      tooltipBg: 'rgba(22,32,58,0.96)',
      tooltipBorder: 'rgba(120,170,255,0.25)',
      tooltipText: '#e6eaf2',
      legendText: '#94a3b8',
      axisLine: 'rgba(255,255,255,0.14)',
      axisLabel: '#8fa0b8',
      splitLine: 'rgba(255,255,255,0.08)',
    }
  : {
      tooltipBg: 'rgba(255,255,255,0.95)',
      tooltipBorder: '#e0e0e0',
      tooltipText: '#303133',
      legendText: '#64748b',
      axisLine: '#e2e8f0',
      axisLabel: '#64748b',
      splitLine: '#f1f5f9',
    }));

// ── 图表 option（vue-echarts 响应式渲染，替代手写实例生命周期管理） ──
const trendOption = computed(() => ({
  tooltip: { trigger: 'axis', backgroundColor: ink.value.tooltipBg, borderColor: ink.value.tooltipBorder, textStyle: { color: ink.value.tooltipText } },
  legend: { data: [t('empDashboard.applicationCount'), t('empDashboard.downloadCount')], textStyle: { color: ink.value.legendText } },
  xAxis: { type: 'category', data: chartData.value.map(i => i.date), axisLine: { lineStyle: { color: ink.value.axisLine } }, axisLabel: { color: ink.value.axisLabel } },
  yAxis: { type: 'value', axisLabel: { color: ink.value.axisLabel }, splitLine: { lineStyle: { color: ink.value.splitLine, type: 'dashed' } } },
  series: [
    { name: t('empDashboard.applicationCount'), type: 'line', smooth: true, data: chartData.value.map(i => i.applications || 0) },
    { name: t('empDashboard.downloadCount'), type: 'bar', barMaxWidth: 16, data: chartData.value.map(i => i.downloads || 0) }
  ]
}));

const statusOption = computed(() => ({
  tooltip: { trigger: 'item', backgroundColor: ink.value.tooltipBg, borderColor: ink.value.tooltipBorder, textStyle: { color: ink.value.tooltipText } },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    label: { color: ink.value.axisLabel },
    data: [
      { value: applicationStatusDist.value.pending || 0, name: t('empDashboard.pending') },
      { value: applicationStatusDist.value.approved || 0, name: t('empDashboard.approved') },
      { value: applicationStatusDist.value.rejected || 0, name: t('empDashboard.rejected') }
    ]
  }]
}));

const dataTypeOption = computed(() => ({
  tooltip: { trigger: 'item', backgroundColor: ink.value.tooltipBg, borderColor: ink.value.tooltipBorder, textStyle: { color: ink.value.tooltipText } },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    label: { color: ink.value.axisLabel },
    data: [
      { value: dataTypePreference.value.vector || 0, name: t('empDashboard.vector') },
      { value: dataTypePreference.value.raster || 0, name: t('empDashboard.raster') }
    ]
  }]
}));

const goTo = (path) => router.push(path);
const refreshNow = () => fetchDashboard();

// ── keep-alive 兼容：图表由 v-chart 组件托管（deactivate 保持挂载，unmount 自动销毁，autoresize 处理尺寸） ──
onMounted(async () => {
  // Vue 3.4 keep-alive 下 onActivated 有时不触发，用 onMounted 兜底
  await fetchDashboard();
});
onActivated(async () => {
  await fetchDashboard();
});
</script>

<style scoped>
.employee-dashboard {
  --dash-c1: #0f172a; --dash-c2: #f8fafc; --dash-c3: #e2e8f0;
  padding: 20px;
  background: radial-gradient(1200px 600px at 0% 0%, var(--dash-c1) 0%, var(--dash-c2) 45%, var(--dash-c3) 100%);
  min-height: calc(100vh - 80px);
}
:global(html.dark) .employee-dashboard {
  --dash-c1: #1a2438; --dash-c2: #0b1220; --dash-c3: #0e1626;
}
.glass {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 16px;
}
:global(html.dark) .glass {
  background: rgba(19, 28, 46, 0.75);
  border-color: rgba(148, 163, 184, 0.18);
}
.hero {
  padding: 18px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.hero h1 { margin: 0; font-size: 24px; }
.hero p { margin: 6px 0 0; color: var(--text-secondary, #475569); }
.hero .meta { margin-top: 8px; color: var(--text-secondary, #64748b); }
.hero-actions { display: flex; gap: 10px; align-items: center; }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.kpi { padding: 14px; transition: all var(--transition-base, 250ms cubic-bezier(0.4, 0, 0.2, 1)); }
.kpi:hover { transform: translateY(-2px); box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1)); }
.kpi:first-child { border-left: 4px solid var(--accent-cyan, #0ea5e9); }
.kpi span { color: var(--text-secondary, #64748b); font-size: 13px; }
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
  background: linear-gradient(135deg, var(--bg-secondary, #f8fafc), var(--tint-info-bg, #eef2ff));
  border: 1px solid var(--border-color, #e2e8f0);
  cursor: pointer;
  transition: all var(--transition-base, 250ms cubic-bezier(0.4, 0, 0.2, 1));
}
.action-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
  border-color: var(--accent-blue, #3b82f6);
}
.action-card b { display:block; color: var(--text-primary, #1e293b); margin-bottom:4px; }
.action-card span { color: var(--text-secondary, #475569); }

.announcement-list { display: grid; gap: 10px; max-height: 320px; overflow-y: auto; padding-right: 4px; }
.announcement-item { display:flex; justify-content: space-between; align-items:center; padding: 10px; border-radius: 10px; background: var(--bg-secondary, #f8fafc); }
.announcement-item p { margin: 6px 0 0; color: var(--text-secondary, #64748b); }
.empty { color: var(--text-tertiary, #94a3b8); padding: 10px 0; }

@media (max-width: 1200px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .grid { grid-template-columns: 1fr; }
}

.skeleton-hero {
  padding: 40px;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sk-line {
  height: 16px;
  border-radius: 8px;
  background: linear-gradient(90deg, var(--skeleton-base, #e2e8f0) 25%, var(--skeleton-highlight, #f1f5f9) 50%, var(--skeleton-base, #e2e8f0) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.sk-line.long { width: 60%; }
.sk-line.medium { width: 40%; }
.sk-line.short { width: 25%; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>
