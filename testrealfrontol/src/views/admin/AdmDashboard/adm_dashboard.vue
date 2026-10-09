<template>
  <div class="admin-dashboard" v-loading="loading">
    <template v-if="loading">
      <div class="skeleton-hero">
        <div class="sk-line long motion-shimmer"></div>
        <div class="sk-line medium motion-shimmer"></div>
      </div>
      <div class="stats-grid">
        <div v-for="n in 4" :key="n" class="stat-card"><div class="sk-line short motion-shimmer"></div><div class="sk-line medium motion-shimmer"></div></div>
      </div>
    </template>
    <template v-else>
    <!-- Hero区域 -->
    <section class="hero-section">
      <div class="hero-content">
        <h1>{{ greeting }}，{{ adminRoleLabel }}</h1>
        <p>{{ $t('adminDashboard.heroSubtitle') }}<span v-if="lastUpdate && lastUpdate !== '-'"> · {{ lastUpdate }}</span></p>
      </div>
      <div class="hero-actions">
        <el-button type="primary" @click="refreshNow" :icon="RefreshRight">{{ $t('adminDashboard.refreshData') }}</el-button>
        <el-button @click="exportSnapshot" :icon="Download">{{ $t('adminDashboard.exportReport') }}</el-button>
      </div>
    </section>

    <!-- 数据分发流向 3D 地球 -->
    <DataFlowGlobe />

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

    <!-- KPI卡片（§3.8 入场 stagger 40ms） -->
    <section class="kpi-grid motion-stagger">
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
          <EmptyState compact variant="never" :title="$t('adminDashboard.noDownloadData')" />
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
          <EmptyState compact variant="never" :title="$t('adminDashboard.noDownloadData')" />
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
          <EmptyState compact variant="never" :title="$t('adminDashboard.noActivityData')" />
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
          <EmptyState compact variant="never" :title="$t('adminDashboard.noData')" />
        </div>
      </el-card>
    </section>

    <!-- 下载统计（7/30/90 天切换）：逐日下载量 + 独立下载人数、两个 Top 小表 + 导出 CSV -->
    <section class="download-stats-section">
      <el-card shadow="hover" v-loading="dlStatsLoading">
        <template #header>
          <div class="dl-stats-header">
            <span>{{ $t('adminDashboard.dlStatsTitle') }}</span>
            <div class="dl-stats-actions">
              <el-radio-group v-model="dlStatsDays" size="small" @change="fetchDownloadStats">
                <el-radio-button :value="7">{{ $t('adminDashboard.day7') }}</el-radio-button>
                <el-radio-button :value="30">{{ $t('adminDashboard.day30') }}</el-radio-button>
                <el-radio-button :value="90">{{ $t('adminDashboard.day90') }}</el-radio-button>
              </el-radio-group>
              <el-button plain size="small" :icon="Download" :loading="dlStatsExporting" @click="exportDlStats">
                {{ $t('adminDashboard.dlStatsExport') }}
              </el-button>
            </div>
          </div>
        </template>

        <div class="dl-stats-summary">
          <div class="dl-summary-item">
            <span class="dl-summary-label">{{ $t('adminDashboard.dlStatsWeekDownloads') }}</span>
            <span class="dl-summary-value">{{ dlComparison.this_week_downloads ?? 0 }}</span>
            <el-tag size="small" :type="(dlComparison.downloads_growth ?? 0) >= 0 ? 'success' : 'danger'">
              {{ (dlComparison.downloads_growth ?? 0) >= 0 ? '+' : '' }}{{ dlComparison.downloads_growth ?? 0 }}%
            </el-tag>
          </div>
          <div class="dl-summary-item">
            <span class="dl-summary-label">{{ $t('adminDashboard.dlStatsWeekUsers') }}</span>
            <span class="dl-summary-value">{{ dlComparison.this_week_users ?? 0 }}</span>
            <el-tag size="small" :type="(dlComparison.users_growth ?? 0) >= 0 ? 'success' : 'danger'">
              {{ (dlComparison.users_growth ?? 0) >= 0 ? '+' : '' }}{{ dlComparison.users_growth ?? 0 }}%
            </el-tag>
          </div>
        </div>

        <v-chart
          v-if="dlStats.daily.length > 0"
          class="dl-stats-chart"
          :option="dlStatsOption"
          autoresize
        />
        <div v-else class="chart-empty dl-stats-chart">
          <EmptyState compact variant="never" :title="$t('adminDashboard.noDownloadData')" />
        </div>

        <div class="dl-stats-tables">
          <div class="dl-stats-table">
            <h4 class="dl-table-title">{{ $t('adminDashboard.dlStatsTopUsers') }}</h4>
            <el-table :data="dlStats.top_users" size="small" max-height="280" :empty-text="$t('adminDashboard.noDownloadData')">
              <el-table-column :label="$t('adminDashboard.colRank')" width="56" align="center">
                <template #default="{ $index }">
                  <span class="dl-rank" :class="{ top: $index < 3 }">{{ $index + 1 }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('adminDashboard.colUser')" min-width="150" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="dl-user">{{ row.name || row.user_number || '—' }}</span>
                  <span v-if="row.name && row.user_number" class="dl-user-number">{{ row.user_number }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('adminDashboard.colCount')" width="90" align="right">
                <template #default="{ row }"><span class="dl-num">{{ row.downloads ?? 0 }}</span></template>
              </el-table-column>
            </el-table>
          </div>
          <div class="dl-stats-table">
            <h4 class="dl-table-title">{{ $t('adminDashboard.dlStatsTopData') }}</h4>
            <el-table :data="dlStats.top_data" size="small" max-height="280" :empty-text="$t('adminDashboard.noDownloadData')">
              <el-table-column :label="$t('adminDashboard.colRank')" width="56" align="center">
                <template #default="{ $index }">
                  <span class="dl-rank" :class="{ top: $index < 3 }">{{ $index + 1 }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('adminDashboard.colDataName')" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="dl-user">{{ row.data_name || $t('adminDashboard.untitled') }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="$t('adminDashboard.colDataType')" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.data_type === 'vector' ? 'primary' : (row.data_type === 'raster' ? 'success' : 'info')">
                    {{ dlTypeLabel(row.data_type) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="$t('adminDashboard.colCount')" width="90" align="right">
                <template #default="{ row }"><span class="dl-num">{{ row.downloads ?? 0 }}</span></template>
              </el-table-column>
            </el-table>
          </div>
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
          <EmptyState compact variant="never" :title="$t('adminDashboard.noReviewData')" />
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
import { ElMessage } from 'element-plus';
import { getDashboard, getDownloadStats, exportDownloadStats } from '@/api/admin';
import {
  User, Clock, FolderOpened, TrendCharts, Download, RefreshRight,
  Document, UserFilled, List, ChatDotRound, Upload
} from '@element-plus/icons-vue';
import { useTheme } from '@/composables/useTheme.js';
import { use, graphic } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart, BarChart, PieChart } from 'echarts/charts';
import {
  TooltipComponent, LegendComponent, GridComponent, DataZoomComponent,
  MarkPointComponent, MarkLineComponent, GraphicComponent
} from 'echarts/components';
import VChart from 'vue-echarts';
import DataFlowGlobe from '@/components/admin/home/DataFlowGlobe.vue';
import EmptyState from '@/components/common/EmptyState.vue';

// ── ECharts 按需注册：仅本页用到的渲染器 / 图表 / 组件 ──
use([
  CanvasRenderer, LineChart, BarChart, PieChart,
  TooltipComponent, LegendComponent, GridComponent, DataZoomComponent,
  MarkPointComponent, MarkLineComponent, GraphicComponent
]);

const { t } = useI18n();
const { isDark } = useTheme();
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

// ── 下载统计区块（7/30/90 天切换，独立于主仪表盘按需拉取） ──
const dlStatsDays = ref(7);
const dlStatsLoading = ref(false);
const dlStatsExporting = ref(false);
const dlStats = ref({ daily: [], top_users: [], top_data: [] });
const dlComparison = ref({
  this_week_downloads: 0,
  last_week_downloads: 0,
  downloads_growth: 0,
  this_week_users: 0,
  last_week_users: 0,
  users_growth: 0
});

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

// ── 颜色常量：随浅/深主题切换，对齐 A/B 设计体系（blue = 品牌强调色） ──
const C = computed(() => (isDark.value
  ? {
      blue: ['#6e79de', '#5e6ad2'],
      cyan: ['#5aa9c9', '#3e7fa6'],
      green: ['#5cc08f', '#3e8f6a'],
      orange: ['#d6a75c', '#b4894a'],
      red: ['#e06a6a', '#b45454'],
      teal: ['#52b8a8', '#3a8f83'],
      pink: ['#c97fad', '#a05c86'],
      indigo: ['#8e97dc', '#6e79de'],
    }
  : {
      blue: ['#0070f3', '#0052b3'],
      cyan: ['#0e8fa8', '#0b6e84'],
      green: ['#0e7a4e', '#0b6842'],
      orange: ['#d08a2e', '#9a6b15'],
      red: ['#b42318', '#97190f'],
      teal: ['#0f766e', '#115e59'],
      pink: ['#b0528a', '#8a3f6c'],
      indigo: ['#5966b8', '#424c8f'],
    }));

// 十六进制 → rgba（面积/渐变填充用）
const hexA = (hex, a) => {
  const n = parseInt(hex.replace('#', ''), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

// 图表主题色：随浅/深主题切换（对齐 A/B 设计体系：A 近黑面板 / B 白底细线）
const chartColors = computed(() => (isDark.value
  ? {
      tooltipBg: 'rgba(17,17,20,0.96)',
      tooltipBorder: 'rgba(94,106,210,0.35)',
      tooltipText: '#ededf0',
      divider: '1px solid rgba(255,255,255,0.08)',
      legendText: '#a0a0ab',
      axisLine: 'rgba(255,255,255,0.10)',
      axisLabelMuted: '#8d8d98',
      axisLabelStrong: '#a0a0ab',
      splitLine: 'rgba(255,255,255,0.06)',
      centerLabel: '#ededf0',
      centerSubLabel: '#8d8d98',
    }
  : {
      tooltipBg: 'rgba(255,255,255,0.98)',
      tooltipBorder: '#eaeaea',
      tooltipText: '#0a0a0a',
      divider: '1px solid #f0f0f0',
      legendText: '#666666',
      axisLine: '#eaeaea',
      axisLabelMuted: '#8f8f8f',
      axisLabelStrong: '#333333',
      splitLine: '#f0f0f0',
      centerLabel: '#0a0a0a',
      centerSubLabel: '#8f8f8f',
    }));

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
      backgroundColor: chartColors.value.tooltipBg,
      borderColor: chartColors.value.tooltipBorder,
      borderWidth: 1,
      textStyle: { color: chartColors.value.tooltipText, fontSize: 13 },
      formatter: params => {
        let html = `<div style="font-weight:600;font-size:14px;margin-bottom:6px;border-bottom:${chartColors.value.divider};padding-bottom:4px">${params[0].axisValue}</div>`;
        params.forEach(p => {
          const dot = p.seriesName === t('adminDashboard.chartApplications') ? C.value.blue[0]
                   : p.seriesName === t('adminDashboard.chartLogins') ? C.value.cyan[0] : C.value.green[0];
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
      textStyle: { color: chartColors.value.legendText, fontSize: 12 }
    },
    grid: { top: 24, bottom: 52, left: 48, right: 24 },
    xAxis: {
      type: 'category', data: dates,
      axisLine: { lineStyle: { color: chartColors.value.axisLine } },
      axisLabel: { color: chartColors.value.axisLabelMuted, fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value', splitLine: { lineStyle: { color: chartColors.value.splitLine, type: 'dashed' } },
      axisLabel: { color: chartColors.value.axisLabelMuted, fontSize: 11 }
    },
    dataZoom: [{
      type: 'inside', start: 0, end: 100, height: 8,
    }],
    series: [
      {
        name: t('adminDashboard.chartApplications'), type: 'line', smooth: true,
        data: appData, symbol: 'circle', symbolSize: 6,
        lineStyle: { width: 2.5, color: C.value.blue[0] },
        itemStyle: { color: C.value.blue[0] },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexA(C.value.blue[0], 0.32) },
            { offset: 1, color: hexA(C.value.blue[0], 0.02) }
          ])
        },
        markPoint: {
          data: appData.map((v, i) => v === Math.max(...appData) ? { coord: [dates[i], v], symbol: 'pin', symbolSize: 40, label: { formatter: v, fontSize: 10 } } : null).filter(Boolean).slice(0, 1),
          symbol: 'pin', symbolSize: 40,
          itemStyle: { color: C.value.blue[0] },
          label: { color: '#fff', fontSize: 10 }
        }
      },
      {
        name: t('adminDashboard.chartLogins'), type: 'line', smooth: true,
        data: loginData, symbol: 'diamond', symbolSize: 6,
        lineStyle: { width: 2, color: C.value.cyan[0], type: 'dotted' },
        itemStyle: { color: C.value.cyan[0] },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexA(C.value.cyan[0], 0.18) },
            { offset: 1, color: hexA(C.value.cyan[0], 0.01) }
          ])
        }
      },
      {
        name: t('adminDashboard.chartDownloads'), type: 'bar', barMaxWidth: 56,
        data: dlData,
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexA(C.value.green[0], 0.9) },
            { offset: 1, color: hexA(C.value.green[0], 0.3) }
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
      backgroundColor: chartColors.value.tooltipBg,
      borderColor: chartColors.value.tooltipBorder,
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
        text: `${total}`, fill: chartColors.value.centerLabel,
        font: 'bold 32px system-ui, sans-serif',
        textAlign: 'center'
      },
      z: 100
    }, {
      type: 'text', left: 'center', top: '56%',
      style: {
        text: '总计', fill: chartColors.value.centerSubLabel,
        font: '13px system-ui, sans-serif',
        textAlign: 'center'
      },
      z: 100
    }] : [],
    series: [{
      type: 'pie', radius: ['42%', '68%'], center: ['50%', '48%'],
      avoidLabelOverlap: true,
      label: {
        show: true, formatter: '{b}\n{d}%',
        color: chartColors.value.legendText, fontSize: 12, lineHeight: 18
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
              { offset: 0, color: C.value.orange[0] }, { offset: 1, color: C.value.orange[1] }
            ])
          }
        },
        {
          value: statusDistribution.value.approved, name: t('adminDashboard.approved'),
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: C.value.green[0] }, { offset: 1, color: C.value.green[1] }
            ])
          }
        },
        {
          value: statusDistribution.value.rejected, name: t('adminDashboard.rejected'),
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: C.value.red[0] }, { offset: 1, color: C.value.red[1] }
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
      backgroundColor: chartColors.value.tooltipBg,
      borderColor: chartColors.value.tooltipBorder,
      borderWidth: 1,
      formatter: params => {
        const p = params[0];
        const isPeak = p.dataIndex === peakIdx;
        return `
          <div style="font-weight:600;font-size:14px;margin-bottom:4px">${p.name}</div>
          <div style="display:flex;align-items:center;gap:6px">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${p.color}"></span>
            <span>${t('adminDashboard.activityCount')}: <b>${p.value}</b></span>
            ${isPeak ? `<span style="background:${C.value.orange[1]};color:#fff;font-size:11px;padding:0 6px;border-radius:4px">峰值</span>` : ''}
          </div>
        `;
      }
    },
    grid: { top: 20, bottom: 28, left: 44, right: 20 },
    xAxis: {
      type: 'category', data: hourlyActivity.value.map(i => i.hour),
      axisLine: { lineStyle: { color: chartColors.value.axisLine } },
      axisLabel: { color: chartColors.value.axisLabelMuted, fontSize: 11, interval: 2 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value', max: maxVal * 1.25,
      splitLine: { lineStyle: { color: chartColors.value.splitLine, type: 'dashed' } },
      axisLabel: { color: chartColors.value.axisLabelMuted, fontSize: 11 }
    },
    series: [{
      type: 'bar', barMaxWidth: 56,
      data: hourlyActivity.value.map((i, idx) => ({
        value: i.count,
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: idx === peakIdx ? C.value.orange[1] : C.value.blue[0] },
            { offset: 1, color: idx === peakIdx ? hexA(C.value.orange[0], 0.6) : hexA(C.value.blue[0], 0.35) }
          ]),
          borderRadius: [4, 4, 0, 0]
        }
      })),
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color: C.value.orange[1], type: 'dashed', width: 1.5 },
        label: { formatter: `峰值 ${maxVal}`, color: C.value.orange[1], fontSize: 11 },
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
      backgroundColor: chartColors.value.tooltipBg,
      borderColor: chartColors.value.tooltipBorder,
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
        text: `${dtTotal}`, fill: chartColors.value.centerLabel,
        font: 'bold 30px system-ui, sans-serif',
        textAlign: 'center'
      },
      z: 100
    }, {
      type: 'text', left: 'center', top: '54%',
      style: {
        text: '数据总量', fill: chartColors.value.centerSubLabel,
        font: '13px system-ui, sans-serif',
        textAlign: 'center'
      },
      z: 100
    }] : [],
    series: [{
      type: 'pie', radius: ['44%', '70%'], center: ['50%', '48%'],
      label: {
        show: true, formatter: '{b}\n{d}%',
        color: chartColors.value.legendText, fontSize: 12, lineHeight: 18
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
              { offset: 0, color: C.value.blue[0] }, { offset: 1, color: C.value.blue[1] }
            ])
          }
        },
        {
          value: dataTypeStats.value.raster || 0, name: t('adminDashboard.raster'),
          itemStyle: {
            color: new graphic.LinearGradient(0, 0, 1, 1, [
              { offset: 0, color: C.value.green[0] }, { offset: 1, color: C.value.green[1] }
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
      backgroundColor: chartColors.value.tooltipBg,
      borderColor: chartColors.value.tooltipBorder,
      borderWidth: 1,
      formatter: params => {
        const name = params[0].name;
        const total = params.reduce((s, p) => s + p.value, 0);
        let html = `<div style="font-weight:600;font-size:14px;margin-bottom:6px;border-bottom:${chartColors.value.divider};padding-bottom:4px">${name}</div>`;
        params.forEach(p => {
          html += `<div style="display:flex;align-items:center;gap:8px;padding:2px 0">
            <span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${p.color}"></span>
            <span style="flex:1">${p.seriesName}</span>
            <span style="font-weight:600">${p.value}</span>
          </div>`;
        });
        html += `<div style="border-top:${chartColors.value.divider};margin-top:4px;padding-top:4px;font-weight:600">合计: ${total}</div>`;
        return html;
      }
    },
    legend: {
      bottom: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 4,
      textStyle: { color: chartColors.value.legendText, fontSize: 12 }
    },
    grid: { top: 16, bottom: 40, left: 80, right: 60 },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: chartColors.value.splitLine, type: 'dashed' } },
      axisLabel: { color: chartColors.value.axisLabelMuted, fontSize: 11 }
    },
    yAxis: {
      type: 'category', data: names, axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: chartColors.value.axisLabelStrong, fontSize: 12, fontWeight: 500 }
    },
    series: [
      {
        name: t('adminDashboard.approved'), type: 'bar', stack: 'total',
        barMaxWidth: 56, data: approvedData,
        label: {
          show: true, position: 'right',
          formatter: params => params.value || '',
          color: C.value.green[1], fontSize: 12, fontWeight: 600
        },
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: C.value.green[0] }, { offset: 1, color: C.value.green[1] }
          ]),
          borderRadius: [0, 4, 4, 0]
        }
      },
      {
        name: t('adminDashboard.rejected'), type: 'bar', stack: 'total',
        barMaxWidth: 56, data: rejectedData,
        label: {
          show: true, position: 'right',
          formatter: params => params.value || '',
          color: C.value.red[1], fontSize: 12, fontWeight: 600
        },
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: C.value.red[0] }, { offset: 1, color: C.value.red[1] }
          ]),
          borderRadius: [0, 4, 4, 0]
        }
      }
    ]
  };
});

const goTo = (path) => router.push(path);
const refreshNow = () => {
  fetchDashboard();
  fetchDownloadStats();
};

// ── 下载统计：数据拉取 / 图表 option（沿用本页 ECharts + 深浅色 palette 惯例） ──
const dlTypeLabel = (dataType) => {
  if (dataType === 'vector') return t('adminDashboard.vector');
  if (dataType === 'raster') return t('adminDashboard.raster');
  return t('adminDashboard.dlStatsUnknownType');
};

const fetchDownloadStats = async () => {
  dlStatsLoading.value = true;
  try {
    const res = await getDownloadStats({ days: dlStatsDays.value });
    const data = res.data?.data || {};
    dlStats.value = {
      daily: Array.isArray(data.daily) ? data.daily : [],
      top_users: Array.isArray(data.top_users) ? data.top_users : [],
      top_data: Array.isArray(data.top_data) ? data.top_data : []
    };
    if (data.comparison) dlComparison.value = data.comparison;
  } catch (err) {
    console.error('获取下载统计失败:', err);
  } finally {
    dlStatsLoading.value = false;
  }
};

const dlStatsOption = computed(() => {
  const dates = dlStats.value.daily.map(i => i.date);
  const dlData = dlStats.value.daily.map(i => i.downloads || 0);
  const userData = dlStats.value.daily.map(i => i.users || 0);

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: chartColors.value.tooltipBg,
      borderColor: chartColors.value.tooltipBorder,
      borderWidth: 1,
      textStyle: { color: chartColors.value.tooltipText, fontSize: 13 }
    },
    legend: {
      bottom: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 4,
      textStyle: { color: chartColors.value.legendText, fontSize: 12 }
    },
    grid: { top: 24, bottom: 52, left: 48, right: 48 },
    xAxis: {
      type: 'category', data: dates,
      axisLine: { lineStyle: { color: chartColors.value.axisLine } },
      axisLabel: { color: chartColors.value.axisLabelMuted, fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: [
      {
        type: 'value',
        splitLine: { lineStyle: { color: chartColors.value.splitLine, type: 'dashed' } },
        axisLabel: { color: chartColors.value.axisLabelMuted, fontSize: 11 }
      },
      {
        type: 'value', minInterval: 1,
        splitLine: { show: false },
        axisLabel: { color: chartColors.value.axisLabelMuted, fontSize: 11 }
      }
    ],
    series: [
      {
        name: t('adminDashboard.dlStatsDownloads'), type: 'line', smooth: true,
        data: dlData, symbol: 'circle', symbolSize: 6,
        lineStyle: { width: 2.5, color: C.value.green[0] },
        itemStyle: { color: C.value.green[0] },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexA(C.value.green[0], 0.28) },
            { offset: 1, color: hexA(C.value.green[0], 0.02) }
          ])
        }
      },
      {
        name: t('adminDashboard.dlStatsUniqueUsers'), type: 'bar', yAxisIndex: 1,
        data: userData, barMaxWidth: 22,
        itemStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexA(C.value.cyan[0], 0.75) },
            { offset: 1, color: hexA(C.value.cyan[0], 0.25) }
          ]),
          borderRadius: [3, 3, 0, 0]
        }
      }
    ]
  };
});

// 导出 CSV：文件名优先取服务端 Content-Disposition（同 AnchorCenter 惯例）
const exportDlStats = async () => {
  dlStatsExporting.value = true;
  try {
    const res = await exportDownloadStats({ days: dlStatsDays.value });
    const cd = res?.headers?.['content-disposition'] || '';
    const match = /filename="?([^";]+)"?/i.exec(cd);
    const filename = match ? decodeURIComponent(match[1]) : `download_stats_${Date.now()}.csv`;
    const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv;charset=utf-8;' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    ElMessage.success(t('adminDashboard.dlStatsExportSuccess'));
  } catch (err) {
    console.error('导出下载统计失败:', err);
    ElMessage.error(t('adminDashboard.dlStatsExportFailed'));
  } finally {
    dlStatsExporting.value = false;
  }
};

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
  await Promise.all([fetchDashboard(), fetchDownloadStats()]);
  autoRefreshTimer = setInterval(() => {
    fetchDashboard();
    fetchDownloadStats();
  }, 60000);
});
onActivated(async () => {
  await Promise.all([fetchDashboard(), fetchDownloadStats()]);
  autoRefreshTimer = setInterval(() => {
    fetchDashboard();
    fetchDownloadStats();
  }, 60000);
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
  padding: 24px;
  background: var(--bg-secondary, #f5f7fa);
  min-height: calc(100vh - 60px);
}

/* Hero */
.hero-section {
  background: var(--bg-primary, #ffffff);
  border: 1px solid var(--border-color, #eaeaea);
  border-radius: var(--radius-lg, 12px);
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  color: var(--text-primary, #0a0a0a);
}
.hero-content h1 { margin: 0 0 8px; font-size: 24px; font-weight: 600; }
.hero-content p { margin: 0; color: var(--text-secondary, #666666); font-size: 14px; }
.hero-actions { display: flex; gap: 12px; }

/* 告警 */
.alert-section { margin-bottom: 16px; display: flex; flex-direction: column; gap: 8px; }

/* KPI卡片 */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.kpi-card { border-radius: var(--radius-lg, 8px); }
.kpi-body { display: flex; align-items: center; gap: 16px; padding: 8px; }
.kpi-icon { width: 48px; height: 48px; border-radius: var(--radius-md, 8px); display: flex; align-items: center; justify-content: center; font-size: 22px; }
.kpi-icon.blue { background: var(--tint-info-bg, rgba(0, 112, 243, 0.08)); color: var(--tint-info-text, #0070f3); }
.kpi-icon.orange { background: var(--tint-warning-bg, rgba(154, 107, 21, 0.08)); color: var(--tint-warning-text, #9a6b15); }
.kpi-icon.green { background: var(--tint-success-bg, rgba(14, 122, 78, 0.08)); color: var(--tint-success-text, #0e7a4e); }
.kpi-icon.cyan { background: var(--tint-info-bg, rgba(0, 112, 243, 0.08)); color: var(--tint-info-text, #0070f3); }
.kpi-info span.kpi-label { color: var(--text-tertiary, #909399); font-size: 13px; }
.kpi-info h2.kpi-value { margin: 4px 0; font-size: 28px; color: var(--text-primary, #303133); font-variant-numeric: tabular-nums; }
.kpi-info small { color: var(--text-tertiary, #909399); font-size: 12px; }

/* 快捷入口 */
.quick-actions { margin-bottom: 24px; }
.action-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; }
.action-item { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 16px; border-radius: var(--radius-md, 8px); cursor: pointer; transition: background-color var(--transition-fast); }
.action-item:hover { background: var(--bg-hover, #fafafa); }
.action-item span { font-size: 13px; color: var(--text-secondary, #606266); }
.action-item .el-icon { color: var(--primary-500, #409EFF); }

/* 图表 */
.charts-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 24px; }
.chart-container { height: 320px; }
.chart-container-wide { height: 360px; }
.chart-empty { height: 320px; display: flex; align-items: center; justify-content: center; }
.full-chart-section { margin-bottom: 24px; }

/* 底部统计 */
.bottom-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.stats-row { display: flex; gap: 40px; padding: 12px 0; }
.stat-item { display: flex; flex-direction: column; gap: 8px; }
.stat-label { font-size: 13px; color: var(--text-tertiary, #909399); }
.stat-value { font-size: 32px; font-weight: 600; color: var(--text-primary, #303133); font-variant-numeric: tabular-nums; }

/* 热门列表 */
.hot-list { max-height: 200px; overflow-y: auto; }
.hot-item { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border-color, #f0f0f0); }
.hot-item:last-child { border-bottom: none; }
.rank { width: 24px; height: 24px; border-radius: 4px; background: var(--bg-tertiary, #e4e7ed); display: flex; align-items: center; justify-content: center; font-size: 12px; color: var(--text-tertiary, #909399); }
.rank.top { background: var(--primary-500, #409EFF); color: #fff; }
.hot-item .name { flex: 1; font-size: 13px; color: var(--text-primary, #303133); }
.hot-item .count { font-size: 12px; color: var(--text-tertiary, #909399); }

/* 日志列表 */
.log-list { max-height: 200px; overflow-y: auto; }
.log-item { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px dashed var(--border-color, #ebeef5); }
.log-item:last-child { border-bottom: none; }
.log-user { flex: 1; font-size: 13px; color: var(--text-secondary, #606266); }
.log-time { font-size: 12px; color: var(--text-tertiary, #909399); }

.empty-tip { text-align: center; padding: 20px; color: var(--text-tertiary, #909399); font-size: 13px; }

/* 下载统计区块 */
.download-stats-section { margin-bottom: 24px; }
.dl-stats-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.dl-stats-actions { display: flex; align-items: center; gap: 12px; }
.dl-stats-summary { display: flex; gap: 48px; padding: 4px 0 12px; flex-wrap: wrap; }
.dl-summary-item { display: flex; align-items: center; gap: 10px; }
.dl-summary-label { font-size: 13px; color: var(--text-tertiary, #909399); }
.dl-summary-value { font-size: 26px; font-weight: 600; color: var(--text-primary, #303133); font-variant-numeric: tabular-nums; }
.dl-stats-chart { height: 280px; }
.dl-stats-tables { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 12px; }
.dl-table-title { margin: 0 0 8px; font-size: 13px; font-weight: 600; color: var(--text-secondary, #666666); }
.dl-rank { width: 22px; height: 22px; border-radius: 4px; background: var(--bg-tertiary, #e4e7ed); display: inline-flex; align-items: center; justify-content: center; font-size: 12px; color: var(--text-tertiary, #909399); }
.dl-rank.top { background: var(--primary-500, #409EFF); color: #fff; }
.dl-user { font-size: 13px; color: var(--text-primary, #303133); }
.dl-user-number { margin-left: 8px; font-size: 12px; color: var(--text-tertiary, #909399); }
.dl-num { font-variant-numeric: tabular-nums; font-weight: 600; }

/* 响应式 */
@media (max-width: 1200px) {
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .charts-grid { grid-template-columns: 1fr; }
  .bottom-grid { grid-template-columns: 1fr; }
  .action-grid { grid-template-columns: repeat(3, 1fr); }
  .dl-stats-tables { grid-template-columns: 1fr; }
}

/* 移动端（<768px）：hero 纵向堆叠，避免标题被按钮挤成逐字换行 */
@media (max-width: 767px) {
  .hero-section {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
    padding: 18px;
  }
  .hero-content,
  .hero-actions {
    width: 100%;
  }
  .kpi-body { gap: 10px; }
  .kpi-icon { width: 40px; height: 40px; font-size: 19px; flex-shrink: 0; }
  .kpi-info h2.kpi-value { white-space: nowrap; }
  .action-grid { gap: 8px; }
  .action-item { padding: 10px 6px; }
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
