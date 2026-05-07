<template>
  <div class="admin-dashboard" v-loading="loading">
    <!-- Hero区域 -->
    <section class="hero-section">
      <div class="hero-content">
        <h1>{{ greeting }}，{{ adminRoleLabel }}</h1>
        <p>实时掌握审批、数据资产与系统运行状态 | 更新时间：{{ lastUpdate }}</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="refreshNow" :icon="RefreshRight">刷新数据</el-button>
        <el-button @click="exportSnapshot" :icon="Download">导出报告</el-button>
      </div>
    </section>

    <!-- 告警提示 -->
    <section class="alert-section" v-if="alerts.length > 0">
      <el-alert
        v-for="(alert, idx) in alerts.slice(0, 3)"
        :key="idx"
        :title="alert.message"
        :type="alert.level === 'warning' ? 'warning' : 'info'"
        show-icon
        closable
      />
    </section>

    <!-- KPI卡片 -->
    <section class="kpi-grid">
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-body">
          <div class="kpi-icon blue"><el-icon><User /></el-icon></div>
          <div class="kpi-info">
            <span class="kpi-label">注册用户</span>
            <h2 class="kpi-value">{{ metrics.totalUsers }}</h2>
            <small>管理员 {{ metrics.totalAdmins }} 人</small>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-body">
          <div class="kpi-icon orange"><el-icon><Clock /></el-icon></div>
          <div class="kpi-info">
            <span class="kpi-label">待审批申请</span>
            <h2 class="kpi-value">{{ metrics.pendingApprovals }}</h2>
            <small>累计 {{ metrics.totalApplications }} 条</small>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-body">
          <div class="kpi-icon green"><el-icon><FolderOpened /></el-icon></div>
          <div class="kpi-info">
            <span class="kpi-label">数据资产</span>
            <h2 class="kpi-value">{{ dataTypeStats.vector + dataTypeStats.raster }}</h2>
            <small>矢量 {{ dataTypeStats.vector }} · 栅格 {{ dataTypeStats.raster }}</small>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-body">
          <div class="kpi-icon cyan"><el-icon><TrendCharts /></el-icon></div>
          <div class="kpi-info">
            <span class="kpi-label">今日活跃 / 总下载</span>
            <h2 class="kpi-value">{{ todayStats.activeUsers }} / {{ metrics.totalDownloads }}</h2>
            <small>登录 {{ todayStats.logins }} 次</small>
          </div>
        </div>
      </el-card>
    </section>

    <!-- 快捷入口 -->
    <section class="quick-actions">
      <el-card shadow="hover">
        <template #header><span>快捷待办</span></template>
        <div class="action-grid">
          <div class="action-item" @click="goTo('/admin/approve_application/not_approved')">
            <el-badge :value="metrics.pendingApprovals" :hidden="metrics.pendingApprovals === 0">
              <el-icon :size="24"><Document /></el-icon>
            </el-badge>
            <span>待审批</span>
          </div>
          <div class="action-item" @click="goTo('/admin/recall')">
            <el-badge :value="recallStats.voting" :hidden="recallStats.voting === 0">
              <el-icon :size="24"><RefreshRight /></el-icon>
            </el-badge>
            <span>回收审议</span>
          </div>
          <div class="action-item" @click="goTo('/admin/admin-application')">
            <el-badge :value="adminAppStats.pending + adminAppStats.voting" :hidden="adminAppStats.pending + adminAppStats.voting === 0">
              <el-icon :size="24"><UserFilled /></el-icon>
            </el-badge>
            <span>管理员申请</span>
          </div>
          <div class="action-item" @click="goTo('/admin/data/upload')">
            <el-icon :size="24"><Upload /></el-icon>
            <span>数据上传</span>
          </div>
          <div class="action-item" @click="goTo('/admin/logs')">
            <el-icon :size="24"><List /></el-icon>
            <span>系统日志</span>
          </div>
          <div class="action-item" @click="goTo('/admin/system/chat')">
            <el-icon :size="24"><ChatDotRound /></el-icon>
            <span>在线沟通</span>
          </div>
        </div>
      </el-card>
    </section>

    <!-- 图表区域 -->
    <section class="charts-grid">
      <el-card shadow="hover">
        <template #header><span>14天申请与下载趋势</span></template>
        <div ref="trendChartRef" class="chart-container"></div>
      </el-card>
      <el-card shadow="hover">
        <template #header><span>申请状态分布</span></template>
        <div ref="statusChartRef" class="chart-container"></div>
      </el-card>
    </section>

    <!-- 底部统计 -->
    <section class="bottom-grid">
      <el-card shadow="hover">
        <template #header><span>本周统计对比</span></template>
        <div class="stats-row">
          <div class="stat-item">
            <span class="stat-label">本周申请</span>
            <span class="stat-value">{{ weeklyComparison.thisWeekApplications }}</span>
            <el-tag size="small" :type="weeklyComparison.applicationGrowth >= 0 ? 'success' : 'danger'">
              {{ weeklyComparison.applicationGrowth >= 0 ? '+' : '' }}{{ weeklyComparison.applicationGrowth }}%
            </el-tag>
          </div>
          <div class="stat-item">
            <span class="stat-label">本周下载</span>
            <span class="stat-value">{{ weeklyComparison.thisWeekDownloads }}</span>
            <el-tag size="small" :type="weeklyComparison.downloadGrowth >= 0 ? 'success' : 'danger'">
              {{ weeklyComparison.downloadGrowth >= 0 ? '+' : '' }}{{ weeklyComparison.downloadGrowth }}%
            </el-tag>
          </div>
        </div>
      </el-card>

      <el-card shadow="hover">
        <template #header><span>热门数据 TOP 5</span></template>
        <div class="hot-list">
          <div v-for="(item, idx) in hotData.slice(0, 5)" :key="idx" class="hot-item">
            <span class="rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
            <span class="name">{{ item.name }}</span>
            <el-tag size="small" :type="item.type === 'vector' ? 'primary' : 'success'">
              {{ item.type === 'vector' ? '矢量' : '栅格' }}
            </el-tag>
            <span class="count">{{ item.downloads }} 次</span>
          </div>
          <div v-if="hotData.length === 0" class="empty-tip">暂无下载数据</div>
        </div>
      </el-card>

      <el-card shadow="hover">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>最近操作日志</span>
            <el-button text type="primary" size="small" @click="goTo('/admin/logs')">查看全部</el-button>
          </div>
        </template>
        <div class="log-list">
          <div v-for="(log, idx) in recentLogs" :key="idx" class="log-item">
            <el-tag size="small" :type="getLogType(log.action)">{{ log.action }}</el-tag>
            <span class="log-user">{{ log.username }}</span>
            <span class="log-time">{{ log.timestamp }}</span>
          </div>
          <div v-if="recentLogs.length === 0" class="empty-tip">暂无日志</div>
        </div>
      </el-card>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useUserStore } from '@/stores/userStore';
import { useRouter } from 'vue-router';
import * as echarts from 'echarts';
import axios from '@/utils/Axios';
import {
  User, Clock, FolderOpened, TrendCharts, Download, RefreshRight,
  Document, UserFilled, List, ChatDotRound, Upload
} from '@element-plus/icons-vue';

const router = useRouter();
const userStore = useUserStore();
const loading = ref(false);
const lastUpdate = ref('-');

const trendChartRef = ref(null);
const statusChartRef = ref(null);
let trendIns = null, statusIns = null;

const metrics = ref({ totalUsers: 0, totalAdmins: 0, pendingApprovals: 0, totalApplications: 0, totalDownloads: 0 });
const todayStats = ref({ activeUsers: 0, logins: 0, applications: 0, downloads: 0 });
const weeklyComparison = ref({ thisWeekApplications: 0, lastWeekApplications: 0, applicationGrowth: 0, thisWeekDownloads: 0, lastWeekDownloads: 0, downloadGrowth: 0 });
const recallStats = ref({ voting: 0, approved: 0, rejected: 0, recalledData: 0 });
const adminAppStats = ref({ pending: 0, voting: 0, approved: 0, rejected: 0 });
const chartData = ref([]);
const statusDistribution = ref({ pending: 0, approved: 0, rejected: 0 });
const dataTypeStats = ref({ vector: 0, raster: 0 });
const recentLogs = ref([]);
const hotData = ref([]);
const alerts = ref([]);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return '早上好';
  if (h < 18) return '下午好';
  return '晚上好';
});

const adminRoleLabel = computed(() => {
  const num = (userStore.userNumber || '').toString().toLowerCase();
  if (num.includes('admin1') || num.includes('adm1')) return '管理员1';
  if (num.includes('admin2') || num.includes('adm2')) return '管理员2';
  if (num.includes('admin3') || num.includes('adm3')) return '管理员3';
  return '管理员';
});

const getLogType = (action) => {
  const map = { login: 'success', download: 'primary', apply: 'warning', logout: 'info' };
  return map[action] || 'info';
};

const fetchDashboard = async () => {
  loading.value = true;
  try {
    const res = await axios.get('/api/admin/dashboard');
    const data = res.data?.data || {};

    metrics.value = {
      totalUsers: data.total_users || 0,
      totalAdmins: data.total_admins || 0,
      pendingApprovals: data.pending_applications || 0,
      totalApplications: data.total_applications || 0,
      totalDownloads: data.total_downloads || 0
    };

    todayStats.value = data.today || { activeUsers: 0, logins: 0, applications: 0, downloads: 0 };
    weeklyComparison.value = data.weekly_comparison || {};
    recallStats.value = data.recall_stats || {};
    adminAppStats.value = data.admin_application_stats || {};
    chartData.value = Array.isArray(data.daily_trend) ? data.daily_trend : [];
    statusDistribution.value = data.status_distribution || { pending: 0, approved: 0, rejected: 0 };
    dataTypeStats.value = data.data_type_stats || { vector: 0, raster: 0 };
    hotData.value = data.hot_data || [];
    alerts.value = data.alerts || [];

    recentLogs.value = (data.recent_logs || []).map(i => ({
      action: i.action || '-',
      username: i.username || '-',
      timestamp: i.timestamp ? i.timestamp.replace('T', ' ').slice(0, 16) : '-'
    }));

    lastUpdate.value = new Date().toLocaleTimeString('zh-CN');

    await nextTick();
    renderCharts();
  } finally {
    loading.value = false;
  }
};

const renderCharts = () => {
  // 趋势图
  if (trendChartRef.value) {
    trendIns?.dispose();
    trendIns = echarts.init(trendChartRef.value);
    trendIns.setOption({
      tooltip: { trigger: 'axis' },
      legend: { bottom: 0 },
      grid: { top: 20, bottom: 50, left: 50, right: 20 },
      xAxis: { type: 'category', data: chartData.value.map(i => i.date), axisLine: { lineStyle: { color: '#e0e0e0' } } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f0f0f0' } } },
      series: [
        { name: '申请数', type: 'line', smooth: true, data: chartData.value.map(i => i.applications || 0), itemStyle: { color: '#409EFF' }, areaStyle: { opacity: 0.1 } },
        { name: '下载数', type: 'bar', barMaxWidth: 20, data: chartData.value.map(i => i.downloads || 0), itemStyle: { color: '#67C23A' } }
      ]
    });
  }

  // 状态分布饼图
  if (statusChartRef.value) {
    statusIns?.dispose();
    statusIns = echarts.init(statusChartRef.value);
    statusIns.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '65%'], center: ['50%', '45%'],
        data: [
          { value: statusDistribution.value.pending, name: '待审批', itemStyle: { color: '#E6A23C' } },
          { value: statusDistribution.value.approved, name: '已通过', itemStyle: { color: '#67C23A' } },
          { value: statusDistribution.value.rejected, name: '已拒绝', itemStyle: { color: '#F56C6C' } }
        ]
      }]
    });
  }
};

const goTo = (path) => router.push(path);
const refreshNow = () => fetchDashboard();

const exportSnapshot = () => {
  const payload = {
    exported_at: new Date().toISOString(),
    metrics: metrics.value,
    today: todayStats.value,
    weekly_comparison: weeklyComparison.value,
    status_distribution: statusDistribution.value,
    data_type_stats: dataTypeStats.value
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `dashboard_${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
};

const onResize = () => {
  trendIns?.resize();
  statusIns?.resize();
};

onMounted(async () => {
  await fetchDashboard();
  window.addEventListener('resize', onResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
  trendIns?.dispose();
  statusIns?.dispose();
});
</script>

<style scoped>
.admin-dashboard {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

/* Hero */
.hero-section {
  background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
  border-radius: 12px;
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  color: #fff;
}
.hero-content h1 { margin: 0 0 8px; font-size: 22px; }
.hero-content p { margin: 0; opacity: 0.85; font-size: 14px; }
.hero-actions { display: flex; gap: 12px; }

/* 告警 */
.alert-section { margin-bottom: 16px; display: flex; flex-direction: column; gap: 8px; }

/* KPI卡片 */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.kpi-card { border-radius: 10px; }
.kpi-body { display: flex; align-items: center; gap: 16px; padding: 8px; }
.kpi-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 24px; color: #fff; }
.kpi-icon.blue { background: linear-gradient(135deg, #409EFF, #3a8ee6); }
.kpi-icon.orange { background: linear-gradient(135deg, #E6A23C, #d9a028); }
.kpi-icon.green { background: linear-gradient(135deg, #67C23A, #5cb530); }
.kpi-icon.cyan { background: linear-gradient(135deg, #00d2d3, #01b8b8); }
.kpi-info span.kpi-label { color: #909399; font-size: 13px; }
.kpi-info h2.kpi-value { margin: 4px 0; font-size: 28px; color: #303133; }
.kpi-info small { color: #909399; font-size: 12px; }

/* 快捷入口 */
.quick-actions { margin-bottom: 20px; }
.action-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; }
.action-item { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 16px; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
.action-item:hover { background: #f0f2f5; }
.action-item span { font-size: 13px; color: #606266; }
.action-item .el-icon { color: #409EFF; }

/* 图表 */
.charts-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 20px; }
.chart-container { height: 280px; }

/* 底部统计 */
.bottom-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.stats-row { display: flex; gap: 40px; padding: 12px 0; }
.stat-item { display: flex; flex-direction: column; gap: 8px; }
.stat-label { font-size: 13px; color: #909399; }
.stat-value { font-size: 32px; font-weight: 600; color: #303133; }

/* 热门列表 */
.hot-list { max-height: 200px; overflow-y: auto; }
.hot-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
.hot-item:last-child { border-bottom: none; }
.rank { width: 24px; height: 24px; border-radius: 4px; background: #e4e7ed; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #909399; }
.rank.top { background: #409EFF; color: #fff; }
.hot-item .name { flex: 1; font-size: 13px; color: #303133; }
.hot-item .count { font-size: 12px; color: #909399; }

/* 日志列表 */
.log-list { max-height: 200px; overflow-y: auto; }
.log-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px dashed #ebeef5; }
.log-item:last-child { border-bottom: none; }
.log-user { flex: 1; font-size: 13px; color: #606266; }
.log-time { font-size: 12px; color: #909399; }

.empty-tip { text-align: center; padding: 20px; color: #909399; font-size: 13px; }

/* 响应式 */
@media (max-width: 1200px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .bottom-grid { grid-template-columns: 1fr; }
  .action-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
