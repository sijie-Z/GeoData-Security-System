<template>
  <div class="employee-dashboard" :aria-busy="loading">
    <template v-if="loading">
      <!-- hero 位：与 .hero 同骨架（3 行 + 右侧 2 按钮块） -->
      <section class="hero glass">
        <div>
          <div class="sk-line sk-hero-title motion-shimmer"></div>
          <div class="sk-line sk-hero-sub motion-shimmer"></div>
          <div class="sk-line sk-hero-meta motion-shimmer"></div>
        </div>
        <div class="hero-actions">
          <div class="sk-btn motion-shimmer"></div>
          <div class="sk-btn motion-shimmer"></div>
        </div>
      </section>

      <!-- KPI 位：真实 .kpi-grid + .kpi.glass（标签线 + 数值线） -->
      <section class="kpi-grid">
        <div v-for="n in 4" :key="n" class="kpi glass sk-pin">
          <div class="sk-line sk-kpi-label motion-shimmer"></div>
          <div class="sk-line sk-kpi-value motion-shimmer"></div>
        </div>
      </section>

      <!-- 图表行位：1 宽图 + 2 小图（与 .chart / .chart.small 同高） -->
      <section class="grid">
        <el-card class="glass" shadow="never">
          <template #header><div class="panel-header"><div class="sk-line sk-h3 sk-h3-with-tag motion-shimmer"></div></div></template>
          <div class="chart sk-block motion-shimmer"></div>
        </el-card>
        <el-card class="glass" shadow="never">
          <template #header><div class="panel-header"><div class="sk-line sk-h3 motion-shimmer"></div></div></template>
          <div class="chart small sk-block motion-shimmer"></div>
        </el-card>
        <el-card class="glass" shadow="never">
          <template #header><div class="panel-header"><div class="sk-line sk-h3 motion-shimmer"></div></div></template>
          <div class="chart small sk-block motion-shimmer"></div>
        </el-card>
      </section>

      <!-- 快捷入口 + 公告行位（3 动作块 + 5 行公告线） -->
      <section class="grid">
        <el-card class="glass" shadow="never">
          <template #header><div class="panel-header"><div class="sk-line sk-h3 motion-shimmer"></div></div></template>
          <div class="action-grid">
            <div v-for="n in 3" :key="n" class="action-card sk-action-card">
              <div class="sk-line sk-action-b motion-shimmer"></div>
              <div class="sk-line sk-action-s motion-shimmer"></div>
            </div>
          </div>
        </el-card>
        <el-card class="glass" shadow="never">
          <template #header><div class="panel-header"><div class="sk-line sk-h3 motion-shimmer"></div></div></template>
          <div class="announcement-list">
            <div v-for="n in 5" :key="n" class="announcement-item sk-ann-row">
              <div class="sk-line sk-ann-line1 motion-shimmer"></div>
              <div class="sk-line sk-ann-line2 motion-shimmer"></div>
            </div>
          </div>
        </el-card>
      </section>
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

    <section class="kpi-grid motion-stagger">
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

// ── 图表主题色（canvas 内无法用 CSS 变量，随 isDark 切换；深色对齐 AdmDashboard 惯例） ──
const ink = computed(() => (isDark.value
  ? {
      tooltipBg: 'rgba(17,17,20,0.96)',
      tooltipBorder: 'rgba(94,106,210,0.35)',
      tooltipText: '#ededf0',
      legendText: '#94a3b8',
      axisLine: 'rgba(255,255,255,0.14)',
      axisLabel: '#8fa0b8',
      splitLine: 'rgba(255,255,255,0.08)',
      series: {
        line: '#6e79de',
        bar: '#5cc08f',
        statusPie: ['#d6a75c', '#5cc08f', '#e06a6a'],
        typePie: ['#6e79de', '#5cc08f'],
      },
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
    {
      name: t('empDashboard.applicationCount'), type: 'line', smooth: true,
      data: chartData.value.map(i => i.applications || 0),
      lineStyle: { color: ink.value.series?.line },
      itemStyle: { color: ink.value.series?.line }
    },
    {
      name: t('empDashboard.downloadCount'), type: 'bar', barMaxWidth: 56,
      data: chartData.value.map(i => i.downloads || 0),
      itemStyle: { color: ink.value.series?.bar }
    }
  ]
}));

const statusOption = computed(() => ({
  tooltip: { trigger: 'item', backgroundColor: ink.value.tooltipBg, borderColor: ink.value.tooltipBorder, textStyle: { color: ink.value.tooltipText } },
  series: [{
    type: 'pie',
    radius: ['40%', '70%'],
    color: ink.value.series?.statusPie,
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
    color: ink.value.series?.typePie,
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
  padding: 20px;
  background: radial-gradient(1200px 600px at 0% 0%, var(--bg-fill) 0%, var(--bg-canvas) 45%, var(--bg-canvas) 100%);
  min-height: calc(100vh - 80px);
}
.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(10px);
  border: 1px solid var(--glass-border);
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
.hero p { margin: 6px 0 0; color: var(--text-secondary, #475569); }
.hero .meta { margin-top: 8px; color: var(--text-secondary, #64748b); font-variant-numeric: tabular-nums; }
.hero-actions { display: flex; gap: 10px; align-items: center; }

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
.kpi { padding: 14px; transition: transform var(--duration-200) var(--ease-out-soft), box-shadow var(--duration-200) var(--ease-out-soft); }
.kpi:hover { transform: translateY(-2px); box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1)); }
.kpi:first-child { border-left: 4px solid var(--accent-9); }
.kpi span { color: var(--text-secondary, #64748b); font-size: 13px; }
.kpi h2 { margin: 6px 0; font-size: 28px; font-variant-numeric: tabular-nums; }
.warn { border-left: 4px solid var(--tint-warning-text); }
.ok { border-left: 4px solid var(--tint-success-text); }
.info { border-left: 4px solid var(--tint-info-text); }

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
  transition: transform var(--duration-200) var(--ease-out-soft), box-shadow var(--duration-200) var(--ease-out-soft), border-color var(--duration-200) var(--ease-out-soft);
}
.action-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1));
  border-color: var(--accent-9);
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

/* 移动端（<768px）：hero 纵向堆叠 + 动作钮换行，避免按钮越过面板右缘 */
@media (max-width: 767px) {
  .hero {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .hero-actions {
    flex-wrap: wrap;
    width: 100%;
  }
}

/* ── 加载骨架（高保真：复用真实布局类，块高对齐 5224 实测值） ── */
.sk-line,
.sk-btn,
.sk-block {
  background: linear-gradient(90deg, var(--skeleton-base, #e2e8f0) 25%, var(--skeleton-highlight, #f1f5f9) 50%, var(--skeleton-base, #e2e8f0) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.sk-line {
  height: 22px;
  border-radius: 8px;
}

/* hero 位（实测 .hero = 118px：padding 18/20 + 内容 80 + 边框 2） */
.sk-hero-title { width: 300px; height: 22px; }
.sk-hero-sub { width: 380px; height: 22px; margin-top: 6px; }
.sk-hero-meta { width: 280px; height: 22px; margin-top: 8px; }
.sk-btn { width: 86px; height: 32px; border-radius: 8px; }
.sk-btn + .sk-btn { width: 116px; margin-left: 12px; }

/* KPI 位（实测 .kpi = 87px：padding 14×2 + 内容 56，补至 87） */
.sk-pin { min-height: 87px; }
.sk-kpi-label { width: 50%; }
.sk-kpi-value { width: 60%; margin: 6px 0; }

/* 图表行位（实测：.chart 320 / .chart.small 260 / 卡片行高 429） */
.sk-h3 { width: 140px; }
.sk-h3.sk-h3-with-tag { height: 24px; }
.sk-block { border-radius: var(--el-card-border-radius, 4px); }

/* 快捷入口 + 公告位（实测 .action-card 74、卡片行高 427、公告区 320） */
.sk-action-card { min-height: 74px; }
.sk-action-b { width: 55%; }
.sk-action-s { width: 75%; margin-top: 4px; }
.sk-ann-row {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
  height: 56px;
}
.sk-ann-line1 { width: 55%; height: 18px; }
.sk-ann-line2 { width: 80%; height: 14px; }

@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

/* 移动端（<=767px）：标题与元信息换行为两行，骨架同步（390 实测值） */
@media (max-width: 767px) {
  .sk-hero-title,
  .sk-hero-sub,
  .sk-hero-meta { width: 100%; }
  .sk-hero-title { height: 44px; }
  .sk-hero-meta { height: 44px; }
}
</style>
