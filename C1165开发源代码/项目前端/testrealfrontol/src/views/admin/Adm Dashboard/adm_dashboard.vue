<!-- <template>
  <div class="p-5 dashboard-container">

    <el-card class="welcome-card rounded-lg shadow-md mb-5">
      <div class="welcome-content">
        <h1 class="text-3xl font-bold welcome-title">管理员工作台</h1>
        <p class="text-lg welcome-text">欢迎您，{{ userStore.userName || '管理员' }}！这是您的数据管理概览。</p>
      </div>
      <div class="welcome-image">
        <img src="https://placehold.co/150x150/d7e9f7/2a668e?text=Hello" alt="Welcome Image">
      </div>
    </el-card>


    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-5">
      <el-card shadow="hover" class="overview-card total-emp rounded-lg">
        <div class="flex items-center p-4">
          <el-icon :size="40" class="mr-4"><UserFilled /></el-icon>
          <div>
            <div class="text-sm text-gray-500">员工总数</div>
            <div class="text-2xl font-bold mt-1">{{ metrics.totalEmployees }} 人</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="overview-card pending-app rounded-lg">
        <div class="flex items-center p-4">
          <el-icon :size="40" class="mr-4"><Tickets /></el-icon>
          <div>
            <div class="text-sm text-gray-500">待审批申请</div>
            <div class="text-2xl font-bold mt-1">{{ metrics.pendingApplications }} 条</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="overview-card pending-upload rounded-lg">
        <div class="flex items-center p-4">
          <el-icon :size="40" class="mr-4"><UploadFilled /></el-icon>
          <div>
            <div class="text-sm text-gray-500">近期上传数据</div>
            <div class="text-2xl font-bold mt-1">{{ metrics.recentUploads }} 个</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="overview-card logs rounded-lg">
        <div class="flex items-center p-4">
          <el-icon :size="40" class="mr-4"><WarningFilled /></el-icon>
          <div>
            <div class="text-sm text-gray-500">近期操作日志</div>
            <div class="text-2xl font-bold mt-1">{{ metrics.recentLogs }} 条</div>
          </div>
        </div>
      </el-card>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="hover" class="chart-card rounded-lg">
          <template #header>
            <div class="card-header font-bold text-lg">近期数据上传趋势</div>
          </template>
          <div id="admin-upload-chart" style="width: 100%; height: 350px;"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="quick-links-card rounded-lg">
          <template #header>
            <div class="card-header font-bold text-lg">快捷功能</div>
          </template>
          <div class="flex flex-col space-y-3">
            <el-button type="primary" class="w-full quick-button" @click="goTo('/admin/employee_management/information_add')">
              <el-icon class="mr-2"><UserFilled /></el-icon>录入员工信息
            </el-button>
            <el-button type="success" class="w-full quick-button" @click="goTo('/admin/approve_application/not_approved')">
              <el-icon class="mr-2"><Tickets /></el-icon>审批待办申请
            </el-button>
            <el-button type="warning" class="w-full quick-button" @click="goTo('/admin/data/upload')">
              <el-icon class="mr-2"><UploadFilled /></el-icon>上传矢量数据
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useUserStore } from '@/stores/userStore';
import { ElMessage } from 'element-plus';
import { UserFilled, Tickets, UploadFilled, WarningFilled } from '@element-plus/icons-vue';
import axios from '@/utils/Axios';
import * as echarts from 'echarts';
import { useRouter } from 'vue-router';

const router = useRouter();
const userStore = useUserStore();
const metrics = ref({
  totalEmployees: 0,
  pendingApplications: 0,
  recentUploads: 0,
  recentLogs: 0,
});

const fetchAdminMetrics = async () => {
  try {
    // 模拟数据加载
    await new Promise(resolve => setTimeout(resolve, 800));
    metrics.value = {
      totalEmployees: 45,
      pendingApplications: 3,
      recentUploads: 12,
      recentLogs: 55,
    };
  } catch (error) {
    ElMessage.error('获取仪表盘数据失败');
    console.error('Failed to fetch admin dashboard metrics:', error);
  }
};

const initChart = () => {
  const chartData = [
    { date: '2025-07-01', uploads: 2 },
    { date: '2025-07-02', uploads: 3 },
    { date: '2025-07-03', uploads: 1 },
    { date: '2025-07-04', uploads: 4 },
    { date: '2025-07-05', uploads: 2 },
    { date: '2025-07-06', uploads: 3 },
    { date: '2025-07-07', uploads: 5 }
  ];

  const chartDom = document.getElementById('admin-upload-chart');
  const myChart = echarts.init(chartDom);
  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: '日期: {b0}<br/>上传次数: {c0}'
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.map(item => item.date),
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '上传次数',
        type: 'line',
        smooth: true,
        data: chartData.map(item => item.uploads),
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
            offset: 0,
            color: 'rgba(64, 158, 255, 0.5)'
          }, {
            offset: 1,
            color: 'rgba(64, 158, 255, 0)'
          }])
        },
        itemStyle: {
          color: '#409EFF'
        }
      }
    ]
  };
  myChart.setOption(option);
};

const goTo = (path) => {
  router.push(path);
};

onMounted(() => {
  fetchAdminMetrics();
  initChart();
});
</script>

<style scoped>
.dashboard-container {
  background-color: #f0f2f5;
}
.welcome-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #e6f7ff 0%, #d5e6f3 100%);
  color: #1890ff;
  padding: 2rem;
  border: none;
}
.welcome-title {
  color: #1890ff;
}
.welcome-text {
  color: #409EFF;
}
.welcome-image {
  flex-shrink: 0;
  margin-left: 20px;
}
.overview-card {
  border: none;
  transition: all 0.3s ease;
  background-color: #fff;
  color: #666;
}
.overview-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.overview-card .el-icon {
  color: #409EFF;
}
.overview-card.total-emp .el-icon {
  color: #67c23a;
}
.overview-card.pending-app .el-icon {
  color: #e6a23c;
}
.overview-card.pending-upload .el-icon {
  color: #409eff;
}
.overview-card.logs .el-icon {
  color: #f56c6c;
}
.chart-card {
  border: none;
  height: 100%;
}
.quick-links-card {
  border: none;
  height: 100%;
}
.quick-button {
  padding: 1.25rem 1rem;
  font-size: 1rem;
  font-weight: bold;
}
</style> -->



<template>
  <div class="dashboard-page">
    <!-- 欢迎卡片 -->
    <el-card class="welcome-card mb-6" shadow="never">
      <div class="welcome-section">
        <h1 class="welcome-title">欢迎您，{{ userStore.userName || '管理员' }}!</h1>
        <p class="welcome-subtitle">这是系统运营概览，您可以高效管理和监控系统。</p>
      </div>
      <div class="welcome-image-placeholder"></div>
    </el-card>

    <!-- 核心数据概览 -->
    <div class="metrics-grid mb-6">
      <el-card shadow="hover" class="metric-card">
        <div class="metric-inner-content">
          <el-icon class="metric-icon users-icon"><UserFilled /></el-icon>
          <div class="text-content">
            <div class="metric-value">{{ adminMetrics.totalUsers }}</div>
            <div class="metric-label">注册用户总数</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="metric-card">
        <div class="metric-inner-content">
          <el-icon class="metric-icon pending-app-icon"><List /></el-icon>
          <div class="text-content">
            <div class="metric-value">{{ adminMetrics.pendingApprovals }}</div>
            <div class="metric-label">待审批申请</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="metric-card">
        <div class="metric-inner-content">
          <el-icon class="metric-icon dataset-icon"><Files /></el-icon>
          <div class="text-content">
            <div class="metric-value">{{ adminMetrics.totalDatasets }}</div>
            <div class="metric-label">总数据集数量</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="metric-card">
        <div class="metric-inner-content">
          <el-icon class="metric-icon active-users-icon"><ChatLineSquare /></el-icon>
          <div class="text-content">
            <div class="metric-value">{{ adminMetrics.activeUsers }}</div>
            <div class="metric-label">本月活跃用户</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 图表和快捷功能 -->
    <el-row :gutter="24">
      <el-col :span="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <h3 class="card-title">系统下载与申请趋势</h3>
            </div>
          </template>
          <div ref="adminChart" class="echart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="quick-links-card">
          <template #header>
            <div class="card-header">
              <h3 class="card-title">快捷功能</h3>
            </div>
          </template>
          <!-- 核心改动：更精致的快捷按钮布局 -->
          <div class="quick-links-group">
            <el-button class="quick-link-btn" @click="goTo('/admin/approve_application/not_approved')">
              <div class="btn-icon"><el-icon><Tickets /></el-icon></div>
              <span class="btn-text">数据申请审批</span>
            </el-button>
            <el-button class="quick-link-btn" @click="goTo('/admin/data/upload')">
              <div class="btn-icon"><el-icon><Upload /></el-icon></div>
              <span class="btn-text">数据上传与管理</span>
            </el-button>
            <el-button class="quick-link-btn" @click="goTo('/admin/employee_management/account_list')">
              <div class="btn-icon"><el-icon><User /></el-icon></div>
              <span class="btn-text">用户账户管理</span>
            </el-button>
            <el-button class="quick-link-btn" @click="goTo('/admin/logs')">
              <div class="btn-icon"><el-icon><Monitor /></el-icon></div>
              <span class="btn-text">系统日志</span>
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useUserStore } from '@/stores/userStore';
import { ElMessage } from 'element-plus';
import { UserFilled, List, Files, ChatLineSquare, Tickets, Upload, User, Monitor } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { useRouter } from 'vue-router';

const router = useRouter();
const userStore = useUserStore();
const adminChart = ref(null);

const adminMetrics = ref({
  totalUsers: 7,
  pendingApprovals: 5,
  totalDatasets: 10,
  activeUsers: 3
});

const chartData = ref([]);

const fetchAdminDashboardData = async () => {
  try {
    // 模拟API数据
    await new Promise(resolve => setTimeout(resolve, 500));
    adminMetrics.value = {
      totalUsers: 7,
      pendingApprovals: 2,
      totalDatasets: 5,
      activeUsers: 3
    };
    chartData.value = [
      { date: '2025-07-01', downloads: 10, applications: 8 },
      { date: '2025-07-02', downloads: 15, applications: 12 },
      { date: '2025-07-03', downloads: 8, applications: 6 },
      { date: '2025-07-04', downloads: 20, applications: 15 },
      { date: '2025-07-05', downloads: 12, applications: 10 },
      { date: '2025-07-06', downloads: 18, applications: 14 },
      { date: '2025-07-07', downloads: 25, applications: 20 },
    ];

    initChart();
  } catch (error) {
    ElMessage.error('获取管理员仪表盘数据失败');
    console.error('Failed to fetch admin dashboard data:', error);
  }
};

const initChart = () => {
  if (!adminChart.value) return;
  const myChart = echarts.init(adminChart.value);
  const option = {
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['下载次数', '申请次数']
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.value.map(item => item.date),
      axisLabel: { color: '#999' },
      axisLine: { lineStyle: { color: '#e0e0e0' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#999' },
      splitLine: { lineStyle: { type: 'dashed', color: '#e0e0e0' } }
    },
    series: [
      {
        name: '下载次数',
        type: 'line',
        smooth: true,
        data: chartData.value.map(item => item.downloads),
        itemStyle: { color: '#409EFF' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
            offset: 0, color: 'rgba(64, 158, 255, 0.5)'
          }, {
            offset: 1, color: 'rgba(64, 158, 255, 0)'
          }])
        },
        lineStyle: { width: 2 }
      },
      {
        name: '申请次数',
        type: 'line',
        smooth: true,
        data: chartData.value.map(item => item.applications),
        itemStyle: { color: '#67C23A' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
            offset: 0, color: 'rgba(103, 194, 58, 0.5)'
          }, {
            offset: 1, color: 'rgba(103, 194, 58, 0)'
          }])
        },
        lineStyle: { width: 2 }
      }
    ]
  };
  myChart.setOption(option);
  window.addEventListener('resize', () => myChart.resize());
};

const goTo = (path) => {
  router.push(path);
};

onMounted(() => {
  fetchAdminDashboardData();
});
</script>

<style scoped>
.dashboard-page {
  padding: 24px;
  background-color: #f0f2f5;
  min-height: calc(100vh - 84px);
}

/* 移除所有 el-card 的边框，并使用 box-shadow 提升视觉效果 */
.el-card {
  border: none;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

/* 移除卡片头部的边框线 */
:deep(.el-card__header) {
  border-bottom: none;
  padding: 20px 20px 0;
}

.mb-6 {
  margin-bottom: 24px;
}

.welcome-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px;
  background: linear-gradient(135deg, #f0f8ff 0%, #dbefff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}
.welcome-title {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}
.welcome-subtitle {
  font-size: 16px;
  color: #666;
  margin-top: 8px;
}
.welcome-image-placeholder {
  width: 150px;
  height: 150px;
  background-image: url('https://placehold.co/150x150/d7e9f7/2a668e?text=Hello');
  background-size: cover;
  border-radius: 8px;
  flex-shrink: 0;
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
}
.metric-card {
  padding: 24px;
  border-radius: 12px;
  background-color: #ffffff;
  transition: all 0.3s ease;
}
.metric-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}
.metric-inner-content {
  display: flex;
  align-items: center;
  gap: 20px;
}
.metric-icon {
  font-size: 48px;
}
.metric-icon.users-icon { color: #606266; }
.metric-icon.pending-app-icon { color: #E6A23C; }
.metric-icon.dataset-icon { color: #409EFF; }
.metric-icon.active-users-icon { color: #67C23A; }
.text-content {
  display: flex;
  flex-direction: column;
}
.metric-value {
  font-size: 36px;
  font-weight: bold;
  color: #333;
}
.metric-label {
  font-size: 14px;
  color: #999;
}
.chart-card, .quick-links-card {
  border-radius: 12px;
  background-color: #ffffff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
  height: 100%;
}
.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
}
.echart-container {
  width: 100%;
  height: 350px;
}
.quick-links-group {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  padding: 12px 20px 20px;
}
.quick-link-btn {
  width: 100%;
  height: 50px; /* 减小按钮高度 */
  font-size: 16px;
  font-weight: bold;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  color: #fff;
  border: none;
}
.quick-link-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.1);
}

.quick-link-btn .el-icon {
  font-size: 24px;
}

.quick-link-btn:nth-child(1) { background: linear-gradient(135deg, #409EFF, #79bbff); }
.quick-link-btn:nth-child(2) { background: linear-gradient(135deg, #67C23A, #95d475); }
.quick-link-btn:nth-child(3) { background: linear-gradient(135deg, #E6A23C, #eebe77); }
.quick-link-btn:nth-child(4) { background: linear-gradient(135deg, #909399, #c8c9cc); }

@media (max-width: 992px) {
  .metric-inner-content {
    flex-direction: column;
    text-align: center;
  }
  .quick-links-group {
    grid-template-columns: repeat(2, 1fr);
  }
  .quick-link-btn {
    height: 80px;
    font-size: 14px;
    flex-direction: column;
    gap: 4px;
  }
  .quick-link-btn .el-icon {
    font-size: 20px;
  }
}
</style>


