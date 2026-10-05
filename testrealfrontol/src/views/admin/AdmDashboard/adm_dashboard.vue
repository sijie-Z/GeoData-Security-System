<template>
  <div class="admin-dashboard" v-loading="loading">
    <template v-if="loading">
      <div class="skeleton-hero">
        <div class="sk-line long"></div>
        <div class="sk-line medium"></div>
      </div>
      <div class="stats-grid">
        <div v-for="n in 4" :key="n" class="stat-card"><div class="sk-line short"></div><div class="sk-line medium"></div></div>
      </div>
    </template>
    <template v-else>
    <!-- Hero区域 -->
    <section class="hero-section">
      <div class="hero-content">
        <h1>{{ greeting }}，{{ adminRoleLabel }}</h1>
        <p>{{ $t('adminDashboard.heroSubtitle') }}{{ lastUpdate }}</p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="refreshNow" :icon="RefreshRight">{{ $t('adminDashboard.refreshData') }}</el-button>
        <el-button @click="exportSnapshot" :icon="Download">{{ $t('adminDashboard.exportReport') }}</el-button>
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
            <span class="kpi-label">{{ $t('adminDashboard.registeredUsers') }}</span>
            <h2 class="kpi-value">{{ metrics.totalUsers }}</h2>
            <small>{{ $t('adminDashboard.adminCount', { count: metrics.totalAdmins }) }}</small>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-body">
          <div class="kpi-icon orange"><el-icon><Clock /></el-icon></div>
          <div class="kpi-info">
            <span class="kpi-label">{{ $t('adminDashboard.pendingApplications') }}</span>
            <h2 class="kpi-value">{{ metrics.pendingApprovals }}</h2>
            <small>{{ $t('adminDashboard.totalCount', { count: metrics.totalApplications }) }}</small>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-body">
          <div class="kpi-icon green"><el-icon><FolderOpened /></el-icon></div>
          <div class="kpi-info">
            <span class="kpi-label">{{ $t('adminDashboard.dataAssets') }}</span>
            <h2 class="kpi-value">{{ dataTypeStats.vector + dataTypeStats.raster }}</h2>
            <small>{{ $t('adminDashboard.vectorRasterBreakdown', { vector: dataTypeStats.vector, raster: dataTypeStats.raster }) }}</small>
          </div>
        </div>
      </el-card>
      <el-card class="kpi-card" shadow="hover">
        <div class="kpi-body">
          <div class="kpi-icon cyan"><el-icon><TrendCharts /></el-icon></div>
          <div class="kpi-info">
            <span class="kpi-label">{{ $t('adminDashboard.todayActiveTotalDownloads') }}</span>
            <h2 class="kpi-value">{{ todayStats.activeUsers }} / {{ metrics.totalDownloads }}</h2>
            <small>{{ $t('adminDashboard.loginTimes', { count: todayStats.logins }) }}</small>
          </div>
        </div>
      </el-card>
    </section>

    <!-- 快捷入口 -->
    <section class="quick-actions">
      <el-card shadow="hover">
        <template #header><span>{{ $t('adminDashboard.quickTodo') }}</span></template>
        <div class="action-grid">
          <div class="action-item" @click="goTo('/admin/approve_application/not_approved')">
            <el-badge :value="metrics.pendingApprovals" :hidden="metrics.pendingApprovals === 0">
              <el-icon :size="24"><Document /></el-icon>
            </el-badge>
            <span>{{ $t('adminDashboard.pendingApproval') }}</span>
          </div>
          <div class="action-item" @click="goTo('/admin/recall')">
            <el-badge :value="recallStats.voting" :hidden="recallStats.voting === 0">
              <el-icon :size="24"><RefreshRight /></el-icon>
            </el-badge>
            <span>{{ $t('adminDashboard.recallReview') }}</span>
          </div>
          <div class="action-item" @click="goTo('/admin/admin-application')">
            <el-badge :value="adminAppStats.pending + adminAppStats.voting" :hidden="adminAppStats.pending + adminAppStats.voting === 0">
              <el-icon :size="24"><UserFilled /></el-icon>
            </el-badge>
            <span>{{ $t('adminDashboard.adminApplication') }}</span>
          </div>
          <div class="action-item" @click="goTo('/admin/data/upload')">
            <el-icon :size="24"><Upload /></el-icon>
            <span>{{ $t('adminDashboard.dataUpload') }}</span>
          </div>
          <div class="action-item" @click="goTo('/admin/logs')">
            <el-icon :size="24"><List /></el-icon>
            <span>{{ $t('adminDashboard.systemLogs') }}</span>
          </div>
          <div class="action-item" @click="goTo('/admin/system/chat')">
            <el-icon :size="24"><ChatDotRound /></el-icon>
            <span>{{ $t('adminDashboard.onlineChat') }}</span>
          </div>
        </div>
      </el-card>
    </section>

    <!-- 图表区域 -->
    <section class="charts-grid">
      <el-card shadow="hover">
        <template #header><span>{{ $t('adminDashboard.trendChart') }}</span></template>
        <v-chart
          v-if="chartData.length > 0"
          class="chart-container"
          :option="trendOption"
          autoresize
        />
        <div v-else class="chart-empty">
          <el-empty :description="$t('adminDashboard.noDownloadData')" :image-size="80" />
        </div>
      </el-card>
      <el-card shadow="hover">
        <template #header><span>{{ $t('adminDashboard.statusDistribution') }}</span></template>
        <v-chart
          v-if="statusDistribution.pending || statusDistribution.approved || statusDistribution.rejected"
          class="chart-container"
          :option="statusOption"
          autoresize
        />
        <div v-else class="chart-empty">
          <el-empty :description="$t('adminDashboard.noDownloadData')" :image-size="80" />
        </div>
      </el-card>
    </section>

    <!-- 图表区域 2：活跃度 + 数据类型分布 -->
    <section class="charts-grid">
      <el-card shadow="hover">
        <template #header><span>{{ $t('adminDashboard.hourlyActivity') }}</span></template>
        <v-chart
          v-if="hourlyActivity.length > 0"
          class="chart-container"
          :option="hourlyOption"
          autoresize
        />
        <div v-else class="chart-empty">
          <el-empty :description="$t('adminDashboard.noActivityData')" :image-size="80" />
        </div>
      </el-card>
      <el-card shadow="hover">
        <template #header><span>{{ $t('adminDashboard.dataTypeDist') }}</span></template>
        <v-chart
          v-if="dataTypeStats.vector || dataTypeStats.raster"
          class="chart-container"
          :option="dataTypeOption"
          autoresize
        />
        <div v-else class="chart-empty">
          <el-empty :description="$t('adminDashboard.noData')" :image-size="80" />
        </div>
      </el-card>
    </section>

    <!-- 管理员审批效率 -->
    <section class="full-chart-section">
      <el-card shadow="hover">
        <template #header><span>{{ $t('adminDashboard.adminEfficiency') }}</span></template>
        <v-chart
          v-if="adminEfficiency.length > 0"
          class="chart-container-wide"
          :option="efficiencyOption"
          autoresize
        />
        <div v-else class="chart-empty">
          <el-empty :description="$t('adminDashboard.noReviewData')" :image-size="80" />
        </div>
      </el-card>
    </section>

    <!-- 底部统计 -->
    <section class="bottom-grid">
      <el-card shadow="hover">
        <template #header><span>{{ $t('adminDashboard.weeklyComparison') }}</span></template>
        <div class="stats-row">
          <div class="stat-item">
            <span class="stat-label">{{ $t('adminDashboard.thisWeekApplications') }}</span>
            <span class="stat-value">{{ weeklyComparison.thisWeekApplications }}</span>
            <el-tag size="small" :type="weeklyComparison.applicationGrowth >= 0 ? 'success' : 'danger'">
              {{ weeklyComparison.applicationGrowth >= 0 ? '+' : '' }}{{ weeklyComparison.applicationGrowth }}%
            </el-tag>
          </div>
          <div class="stat-item">
            <span class="stat-label">{{ $t('adminDashboard.thisWeekDownloads') }}</span>
            <span class="stat-value">{{ weeklyComparison.thisWeekDownloads }}</span>
            <el-tag size="small" :type="weeklyComparison.downloadGrowth >= 0 ? 'success' : 'danger'">
              {{ weeklyComparison.downloadGrowth >= 0 ? '+' : '' }}{{ weeklyComparison.downloadGrowth }}%
            </el-tag>
          </div>
        </div>
      </el-card>

      <el-card shadow="hover">
        <template #header><span>{{ $t('adminDashboard.hotDataTop5') }}</span></template>
        <div class="hot-list">
          <div v-for="(item, idx) in hotData.slice(0, 5)" :key="idx" class="hot-item">
            <span class="rank" :class="{ top: idx < 3 }">{{ idx + 1 }}</span>
            <span class="name">{{ item.name || $t('adminDashboard.untitled') }}</span>
            <el-tag size="small" :type="item.type === 'vector' ? 'primary' : 'success'">
              {{ item.type === 'vector' ? $t('adminDashboard.vector') : $t('adminDashboard.raster') }}
            </el-tag>
            <span class="count">{{ item.downloads ?? 0 }} {{ $t('adminDashboard.timesUnit') }}</span>
          </div>
          <div v-if="hotData.length === 0" class="empty-tip">{{ $t('adminDashboard.noDownloadData') }}</div>
        </div>
      </el-card>

      <el-card shadow="hover">
        <template #header>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <span>{{ $t('adminDashboard.recentLogs') }}</span>
            <el-button text type="primary" size="small" @click="goTo('/admin/logs')">{{ $t('adminDashboard.viewAll') }}</el-button>
          </div>
        </template>
        <div class="log-list">
          <div v-for="(log, idx) in recentLogs" :key="idx" class="log-item">
            <el-tag size="small" :type="getLogType(log.action)">{{ log.action }}</el-tag>
            <span class="log-user">{{ log.username }}</span>
            <span class="log-time">{{ log.timestamp }}</span>
          </div>
          <div v-if="recentLogs.length === 0" class="empty-tip">{{ $t('adminDashboard.noLogs') }}</div>
        </div>
      </el-card>
    </section>
    </template>
  </div>
</template>

<script setup>
defineOptions({ name: 'AdminDashboard' });
import { ref, computed, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useUserStore } from '@/stores/userStore';
import { useRouter } from 'vue-router';
import { getDashboard } from '@/api/admin';
import {
  User, Clock, FolderOpened, TrendCharts, Download, RefreshRight,
  Document, UserFilled, List, ChatDotRound, Upload
} from '@element-plus/icons-vue';
import { use, graphic } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart, BarChart, PieChart } from 'echarts/charts';
import {
  TooltipComponent, LegendComponent, GridComponent, DataZoomComponent,
  MarkPointComponent, MarkLineComponent, GraphicComponent
} from 'echarts/components';
import VChart from 'vue-echarts';

// ── ECharts 按需注册：仅本页用到的渲染器 / 图表 / 组件 ──
use([
  CanvasRenderer, LineChart, BarChart, PieChart,
  TooltipComponent, LegendComponent, GridComponent, DataZoomComponent,
  MarkPointComponent, MarkLineComponent, GraphicComponent
]);

const { t } = useI18n();
const router = useRouter();
const userStore = useUserStore();
const loading = ref(false);
const lastUpdate = ref('-');

let autoRefreshTimer = null;

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
const hourlyActivity = ref([]);
const adminEfficiency = ref([]);
const alerts = ref([]);

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 12) return t('adminDashboard.goodMorning');
  if (h < 18) return t('adminDashboard.goodAfternoon');
  return t('adminDashboard.goodEvening');
});

const adminRoleLabel = computed(() => {
  const subRole = userStore.adminSubRole || '';
  if (subRole === 'adm1') return t('adminDashboard.adminRole1');
  if (subRole === 'adm2') return t('adminDashboard.adminRole2');
  if (subRole === 'adm3') return t('adminDashboard.adminRole3');
  return t('adminDashboard.adminRole');
});

const getLogType = (action) => {
  const map = { login: 'success', download: 'primary', apply: 'warning', logout: 'info' };
  return map[action] || 'info';
};

const fetchDashboard = async () => {
  loading.value = true;
  try {
    const res = await getDashboard();
    const data = res.data?.data || {};

    metrics.value = {
      totalUsers: data.total_users || 0,
      totalAdmins: data.total_admins || 0,
      pendingApprovals: data.pending_applications || 0,
      totalApplications: data.total_applications || 0,
      totalDownloads: data.total_downloads || 0
    };

    todayStats.value = data.today || { activeUsers: 0, logins: 0, applications: 0, downloads: 0 };
    weeklyComparison.value = {
      thisWeekApplications: data.weekly_comparison?.this_week_applications ?? 0,
      lastWeekApplications: data.weekly_comparison?.last_week_applications ?? 0,
      applicationGrowth: data.weekly_comparison?.application_growth ?? 0,
      thisWeekDownloads: data.weekly_comparison?.this_week_downloads ?? 0,
      lastWeekDownloads: data.weekly_comparison?.last_week_downloads ?? 0,
      downloadGrowth: data.weekly_comparison?.download_growth ?? 0
    };
    recallStats.value = data.recall_stats || {};
    adminAppStats.value = data.admin_application_stats || {};
    chartData.value = Array.isArray(data.daily_trend) ? data.daily_trend : [];
    statusDistribution.value = data.status_distribution || { pending: 0, approved: 0, rejected: 0 };
    dataTypeStats.value = data.data_type_stats || { vector: 0, raster: 0 };
    hotData.value = data.hot_data || [];
    hourlyActivity.value = Array.isArray(data.hourly_activity) ? data.hourly_activity : [];
    adminEfficiency.value = Array.isArray(data.admin_efficiency) ? data.admin_efficiency : [];
    alerts.value = data.alerts || [];

    recentLogs.value = (data.recent_logs || []).map(i => ({
      action: i.action || '-',
      username: i.username || '-',
      timestamp: i.timestamp ? i.timestamp.replace('T', ' ').slice(0, 16) : '-'
    }));

    lastUpdate.value = new Date().toLocaleTimeString('zh-CN');

    loading.value = false;
  } catch (err) {
    console.error('获取仪表盘数据失败:', err);
    loading.value = false;
  }
};

// ── 颜色常量 ──
const C = {
  blue: ['#2196F3', '#1565C0'],
  purple: ['#AB47BC', '#6A1B9A'],
  green: ['#66BB6A', '#2E7D32'],
  orange: ['#FFA726', '#E65100'],
  red: ['#EF5350', '#C62828'],
  teal: ['#26A69A', '#00695C'],
  pink: ['#EC407A', '#AD1457'],
  indigo: ['#5C6BC0', '#283593'],
};

// ── 图表 option（vue-echarts 响应式渲染，替代手写实例生命周期管理） ──

// ========== 1. 趋势图：面积渐变 + 数据缩放 + 峰值标记 ==========
const trendOption = computed(() => {
  const dates = chartData.value.map(i => i.date);
  const appData = chartData.value.map(i => i.applications || 0);
  const loginData = chartData.value.map(i => i.logins || 0);
  const dlData = chartData.value.map(i => i.downloads || 0);

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e0e0e0',
      borderWidth: 1,
      textStyle: { color: '#1a1a2e', fontSize: 13 },
      formatter: params => {
        let html = `<div style="font-weight:600;font-size:14px;margin-bottom:6px;border-bottom:1px solid #eee;padding-bottom:4px">${params[0].axisValue}</div>`;
        params.forEach(p => {
          const dot = p.seriesName === t('adminDashboard.chartApplications') ? '#2196F3'
                   : p.seriesName === t('adminDashboard.chartLogins') ? '#AB47BC' : '#66BB6A';
          html += `<div style="display:flex;align-items:center;gap:8px;padding:2px 0">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${dot}"></span>
            <span style="flex:1">${p.seriesName}</span>
            <span style="font-weight:600">${p.value}</span>
          </div>`;
        });
        return html;
      }
    },
    legend: {
      bottom: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 4,
      textStyle: { color: '#666', fontSize: 12 }
    },
    grid: { top: 24, bottom: 52, left: 48, right: 24 },
    xAxis: {
      type: 'category', data: dates,
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#999', fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value', splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } },
      axisLabel: { color: '#999', fontSize: 11 }
    },
    dataZoom: [{
      type: 'inside', start: 0, end: 100, height: 8,
    }],
    series: [
      {
        name: t('adminDashboard.chartApplications'), type: 'line', smooth: true,
        data: appData, symbol: 'circle', symbolSize: 6,
        lineStyle: { width: 2.5, color: C.blue[0] },
        itemStyle: { color: C.blue[0] },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(33,150,243,0.35)' },
            { offset: 1, color: 'rgba(33,150,243,0.02)' }
          ])
        },
        markPoint: {
          data: appData.map((v, i) => v === Math.max(...appData) ? { coord: [dates[i], v], symbol: 'pin', symbolSize: 40, label: { formatter: v, fontSize: 10 } } : null).filter(Boolean).slice(0, 1),
          symbol: 'pin', symbolSize: 40,
          itemStyle: { color: C.blue[0] },
          label: { color: '#fff', fontSize: 10 }
        }
      },
      {
        name: t('adminDashboard.chartLogins'), type: 'line', smooth: true,
        data: loginData, symbol: 'diamond', symbolSize: 6,
        lineStyle: { width: 2, color: C.purple[0], type: 'dotted' },
        itemStyle: { color: C.purple[0] },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(171,71,188,0.2)' },
            { offset: 1, color: 'rgba(171,71,188,0.01)' }
          ])
        }
      },
      {
        name: t('adminDashboard.chartDownloads'), type: 'bar', barMaxWidth: 14,
        data: dlData,
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(102,187,106,0.9)' },
            { offset: 1, color: 'rgba(102,187,106,0.3)' }
          ]),
          borderRadius: [3, 3, 0, 0]
        }
      }
    ]
  };
});

// ========== 2. 状态分布：渐变环形 + 中心总计 + 流光动画 ==========
const statusOption = computed(() => {
  const total = statusDistribution.value.pending + statusDistribution.value.approved + statusDistribution.value.rejected;
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e0e0e0',
      borderWidth: 1,
      formatter: params => `
        <div style="font-weight:600;font-size:15px;margin-bottom:4px">${params.name}</div>
        <div style="display:flex;align-items:center;gap:8px">
          <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${params.color}"></span>
          <span>${params.value} 条 (${params.percent}%)</span>
        </div>
      `
    },
    graphic: total > 0 ? [{
      type: 'text', left: 'center', top: '42%',
      style: {
        text: `${total}`, fill: '#1a1a2e',
        font: 'bold 32px Inter, -apple-system, sans-serif',
        textAlign: 'center'
      },
      z: 100
    }, {
      type: 'text', left: 'center', top: '56%',
      style: {
        text: '总计', fill: '#999',
        font: '13px Inter, -apple-system, sans-serif',
        textAlign: 'center'
      },
      z: 100
    }] : [],
    series: [{
      type: 'pie', radius: ['42%', '68%'], center: ['50%', '48%'],
      avoidLabelOverlap: true,
      label: {
        show: true, formatter: '{b}\n{d}%',
        color: '#666', fontSize: 12, lineHeight: 18
      },
      labelLine: { length: 12, length2: 8, smooth: true },
      emphasis: {
        label: { fontSize: 14, fontWeight: 'bold' },
        itemStyle: { shadowBlur: 20, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' }
      },
      animationType: 'scale',
      animationEasing: 'elasticOut',
      animationDelay: idx => idx * 200,
      data: [
        {
          value: statusDistribution.value.pending, name: t('adminDashboard.pendingApproval'),
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: '#FFD54F' }, { offset: 1, color: '#FF8F00' }
            ])
          }
        },
        {
          value: statusDistribution.value.approved, name: t('adminDashboard.approved'),
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: '#81C784' }, { offset: 1, color: '#2E7D32' }
            ])
          }
        },
        {
          value: statusDistribution.value.rejected, name: t('adminDashboard.rejected'),
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: '#EF9A9A' }, { offset: 1, color: '#C62828' }
            ])
          }
        }
      ]
    }]
  };
});

// ========== 3. 用户活跃时段：渐变柱 + 峰值高亮 + 波峰标记 ==========
const hourlyOption = computed(() => {
  const maxVal = Math.max(...hourlyActivity.value.map(i => i.count), 1);
  const peakIdx = hourlyActivity.value.findIndex(i => i.count === maxVal);

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e0e0e0',
      borderWidth: 1,
      formatter: params => {
        const p = params[0];
        const isPeak = p.dataIndex === peakIdx;
        return `
          <div style="font-weight:600;font-size:14px;margin-bottom:4px">${p.name}</div>
          <div style="display:flex;align-items:center;gap:6px">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${p.color}"></span>
            <span>${t('adminDashboard.activityCount')}: <b>${p.value}</b></span>
            ${isPeak ? '<span style="background:#FF6F00;color:#fff;font-size:11px;padding:0 6px;border-radius:4px">峰值</span>' : ''}
          </div>
        `;
      }
    },
    grid: { top: 20, bottom: 28, left: 44, right: 20 },
    xAxis: {
      type: 'category', data: hourlyActivity.value.map(i => i.hour),
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#999', fontSize: 11, interval: 2 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value', max: maxVal * 1.25,
      splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } },
      axisLabel: { color: '#999', fontSize: 11 }
    },
    series: [{
      type: 'bar', barMaxWidth: 20,
      data: hourlyActivity.value.map((i, idx) => ({
        value: i.count,
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: idx === peakIdx ? '#FF6F00' : '#42A5F5' },
            { offset: 1, color: idx === peakIdx ? '#FFB74D' : '#90CAF9' }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      })),
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color: '#FF6F00', type: 'dashed', width: 1.5 },
        label: { formatter: `峰值 ${maxVal}`, color: '#FF6F00', fontSize: 11 },
        data: [{ yAxis: maxVal }]
      },
      animationDelay: idx => idx * 60
    }],
    animationEasing: 'bounceOut'
  };
});

// ========== 4. 数据类型分布：中心总数环形 ==========
const dataTypeOption = computed(() => {
  const dtTotal = (dataTypeStats.value.vector || 0) + (dataTypeStats.value.raster || 0);
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e0e0e0',
      borderWidth: 1,
      formatter: params => `
        <div style="font-weight:600;font-size:15px;margin-bottom:4px">${params.name}</div>
        <div style="display:flex;align-items:center;gap:8px">
          <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${params.color}"></span>
          <span>${params.value} 个 (${params.percent}%)</span>
        </div>
      `
    },
    graphic: dtTotal > 0 ? [{
      type: 'text', left: 'center', top: '40%',
      style: {
        text: `${dtTotal}`, fill: '#1a1a2e',
        font: 'bold 30px Inter, -apple-system, sans-serif',
        textAlign: 'center'
      },
      z: 100
    }, {
      type: 'text', left: 'center', top: '54%',
      style: {
        text: '数据总量', fill: '#999',
        font: '13px Inter, -apple-system, sans-serif',
        textAlign: 'center'
      },
      z: 100
    }] : [],
    series: [{
      type: 'pie', radius: ['44%', '70%'], center: ['50%', '48%'],
      label: {
        show: true, formatter: '{b}\n{d}%',
        color: '#666', fontSize: 12, lineHeight: 18
      },
      labelLine: { length: 12, length2: 8, smooth: true },
      emphasis: {
        itemStyle: { shadowBlur: 20, shadowOffsetX: 0, shadowColor: 'rgba(0,0,0,0.2)' }
      },
      animationType: 'scale',
      animationEasing: 'elasticOut',
      data: [
        {
          value: dataTypeStats.value.vector || 0, name: t('adminDashboard.vector'),
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: '#42A5F5' }, { offset: 1, color: '#1565C0' }
            ])
          }
        },
        {
          value: dataTypeStats.value.raster || 0, name: t('adminDashboard.raster'),
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: '#66BB6A' }, { offset: 1, color: '#2E7D32' }
            ])
          }
        }
      ]
    }]
  };
});

// ========== 5. 管理员审批效率：堆叠柱 + 数值标签 + 渐变 ==========
const efficiencyOption = computed(() => {
  const names = adminEfficiency.value.map(i => i.name || '-');
  const approvedData = adminEfficiency.value.map(i => i.approved || 0);
  const rejectedData = adminEfficiency.value.map(i => i.rejected || 0);

  return {
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e0e0e0',
      borderWidth: 1,
      formatter: params => {
        const name = params[0].name;
        const total = params.reduce((s, p) => s + p.value, 0);
        let html = `<div style="font-weight:600;font-size:14px;margin-bottom:6px;border-bottom:1px solid #eee;padding-bottom:4px">${name}</div>`;
        params.forEach(p => {
          html += `<div style="display:flex;align-items:center;gap:8px;padding:2px 0">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${p.color}"></span>
            <span style="flex:1">${p.seriesName}</span>
            <span style="font-weight:600">${p.value}</span>
          </div>`;
        });
        html += `<div style="border-top:1px solid #eee;margin-top:4px;padding-top:4px;font-weight:600">合计: ${total}</div>`;
        return html;
      }
    },
    legend: {
      bottom: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 4,
      textStyle: { color: '#666', fontSize: 12 }
    },
    grid: { top: 16, bottom: 40, left: 80, right: 60 },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f5f5f5', type: 'dashed' } },
      axisLabel: { color: '#999', fontSize: 11 }
    },
    yAxis: {
      type: 'category', data: names, axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#444', fontSize: 12, fontWeight: 500 }
    },
    series: [
      {
        name: t('adminDashboard.approved'), type: 'bar', stack: 'total',
        barMaxWidth: 24, data: approvedData,
        label: {
          show: true, position: 'right',
          formatter: params => params.value || '',
          color: '#2E7D32', fontSize: 12, fontWeight: 600
        },
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#81C784' }, { offset: 1, color: '#388E3C' }
          ]),
          borderRadius: [0, 4, 4, 0]
        }
      },
      {
        name: t('adminDashboard.rejected'), type: 'bar', stack: 'total',
        barMaxWidth: 24, data: rejectedData,
        label: {
          show: true, position: 'right',
          formatter: params => params.value || '',
          color: '#C62828', fontSize: 12, fontWeight: 600
        },
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#EF9A9A' }, { offset: 1, color: '#E53935' }
          ]),
          borderRadius: [0, 4, 4, 0]
        }
      }
    ]
  };
});

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

// ── keep-alive 兼容：图表由 v-chart 组件托管（deactivate 保持挂载，unmount 自动销毁，autoresize 处理尺寸） ──
onMounted(async () => {
  // Vue 3.4 keep-alive 下 onActivated 有时不触发，用 onMounted 兜底
  await fetchDashboard();
  autoRefreshTimer = setInterval(fetchDashboard, 60000);
});
onActivated(async () => {
  await fetchDashboard();
  autoRefreshTimer = setInterval(fetchDashboard, 60000);
});

onDeactivated(() => {
  if (autoRefreshTimer) { clearInterval(autoRefreshTimer); autoRefreshTimer = null; }
});

// Permanent unmount — v-chart 自动 dispose，仅需清理定时器
onBeforeUnmount(() => {
  if (autoRefreshTimer) { clearInterval(autoRefreshTimer); autoRefreshTimer = null; }
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
  background: var(--gradient-hero, linear-gradient(135deg, #1e3c72 0%, #2a5298 100%));
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
.action-item { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 16px; border-radius: 8px; cursor: pointer; transition: all var(--transition-base, 250ms cubic-bezier(0.4, 0, 0.2, 1)); }
.action-item:hover { background: #f0f2f5; transform: translateY(-2px); box-shadow: var(--shadow-md, 0 4px 6px -1px rgba(0, 0, 0, 0.1)); }
.action-item span { font-size: 13px; color: #606266; }
.action-item .el-icon { color: #409EFF; }

/* 图表 */
.charts-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 20px; }
.chart-container { height: 320px; }
.chart-container-wide { height: 360px; }
.chart-empty { height: 320px; display: flex; align-items: center; justify-content: center; }
.full-chart-section { margin-bottom: 20px; }

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
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.sk-line.long { width: 60%; }
.sk-line.medium { width: 40%; }
.sk-line.short { width: 25%; }
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>
