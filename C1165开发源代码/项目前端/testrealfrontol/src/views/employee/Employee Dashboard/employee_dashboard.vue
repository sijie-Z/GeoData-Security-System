<template>
  <div class="dashboard-container">
    <!-- 欢迎卡片：简洁的欢迎信息 -->
    <el-card class="welcome-card mb-6" shadow="never">
      <div class="welcome-content">
        <h1 class="welcome-title">欢迎您，{{ userStore.userName || '员工' }}!</h1>
        <p class="welcome-subtitle">这是您的数据管理概览，助您高效工作。</p>
      </div>
    </el-card>

    <!-- 概览数据卡片：紧凑的指标展示 -->
    <div class="metrics-grid mb-6">
      <el-card shadow="hover" class="metric-card">
        <div class="metric-inner-content">
          <el-icon class="metric-icon total-icon"><Document /></el-icon>
          <div class="text-content">
            <div class="metric-label">总申请数</div>
            <div class="metric-value">{{ metrics.totalApplications }}</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="metric-card">
        <div class="metric-inner-content">
          <el-icon class="metric-icon pending-icon"><Refresh /></el-icon>
          <div class="text-content">
            <div class="metric-label">待审批申请</div>
            <div class="metric-value">{{ metrics.pendingApplications }}</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="metric-card">
        <div class="metric-inner-content">
          <el-icon class="metric-icon download-icon"><Download /></el-icon>
          <div class="text-content">
            <div class="metric-label">可下载数据</div>
            <div class="metric-value">{{ metrics.downloadableData }}</div>
          </div>
        </div>
      </el-card>
      <el-card shadow="hover" class="metric-card">
        <div class="metric-inner-content">
          <el-icon class="metric-icon my-download-icon"><Tickets /></el-icon>
          <div class="text-content">
            <div class="metric-label">我的下载次数</div>
            <div class="metric-value">{{ metrics.myDownloads }}</div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 图表、公告和快捷功能：更合理的布局 -->
    <el-row :gutter="24" class="mb-6">
      <el-col :span="24" :lg="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <h3 class="card-title">近期数据下载趋势</h3>
            </div>
          </template>
          <div ref="employeeChart" class="echart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="24" :lg="8">
        <el-card shadow="hover" class="quick-links-card">
          <template #header>
            <div class="card-header">
              <h3 class="card-title">快捷功能</h3>
            </div>
          </template>
          <!-- 核心改动：更精致的快捷按钮布局 -->
          <div class="quick-links-group">
            <el-button class="quick-link-btn" @click="goTo('/employee/data_viewing')">
              <div class="btn-icon"><el-icon><View /></el-icon></div>
              <span class="btn-text">数据目录浏览</span>
            </el-button>
            <el-button class="quick-link-btn" @click="goTo('/employee/data_application')">
              <div class="btn-icon"><el-icon><Tickets /></el-icon></div>
              <span class="btn-text">我的申请记录</span>
            </el-button>
            <el-button class="quick-link-btn" @click="goTo('/employee/data_download')">
              <div class="btn-icon"><el-icon><Download /></el-icon></div>
              <span class="btn-text">已批准数据下载</span>
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 最新系统公告模块：与卡片保持一致的风格 -->
    <el-row>
      <el-col :span="24">
        <el-card shadow="hover" class="announcement-card">
          <template #header>
            <div class="card-header">
              <h3 class="card-title">最新系统公告</h3>
            </div>
          </template>
          <div class="announcement-list">
            <el-alert title="系统将于7月15日凌晨进行升级维护，届时将暂停服务约2小时。" type="warning" show-icon :closable="false" />
            <el-alert title="新增一批高精度卫星遥感数据，欢迎查看和申请！" type="success" show-icon :closable="false" />
            <el-alert title="数据审批流程已优化，审批速度得到进一步提升。" type="info" show-icon :closable="false" />
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
import { Document, Refresh, Download, Tickets, View } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import { useRouter } from 'vue-router';

const router = useRouter();
const userStore = useUserStore();
const employeeChart = ref(null);

const metrics = ref({
  totalApplications: 5,
  pendingApplications: 1,
  downloadableData: 3,
  myDownloads: 5
});

const chartData = ref([]);

const fetchDashboardData = async () => {
  try {
    // 模拟API数据
    await new Promise(resolve => setTimeout(resolve, 500));
    metrics.value = {
      totalApplications: 5,
      pendingApplications: 1,
      downloadableData: 3,
      myDownloads: 5
    };
    chartData.value = [
      { date: '2025-07-01', downloads: 1.2 },
      { date: '2025-07-02', downloads: 1.8 },
      { date: '2025-07-03', downloads: 0.8 },
      { date: '2025-07-04', downloads: 2.5 },
      { date: '2025-07-05', downloads: 1.1 },
      { date: '2025-07-06', downloads: 2.2 },
      { date: '2025-07-07', downloads: 1.5 },
    ];

    initChart();
  } catch (error) {
    ElMessage.error('获取仪表盘数据失败');
    console.error('Failed to fetch dashboard data:', error);
  }
};

const initChart = () => {
  if (!employeeChart.value) return;
  const myChart = echarts.init(employeeChart.value);
  const option = {
    tooltip: { trigger: 'axis' },
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
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
            offset: 0, color: 'rgba(64, 158, 255, 0.5)'
          }, {
            offset: 1, color: 'rgba(64, 158, 255, 0)'
          }])
        },
        itemStyle: { color: '#409EFF' },
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
  fetchDashboardData();
});
</script>

<style scoped>
.dashboard-container {
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
  padding: 24px;
  background: linear-gradient(90deg, #f3f9ff 0%, #e8f3ff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

.welcome-title {
  font-size: 24px;
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}

.welcome-subtitle {
  font-size: 16px;
  color: #666;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
}

.metric-card {
  display: flex;
  align-items: center;
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
  gap: 16px;
}

.metric-icon {
  font-size: 36px;
}

.metric-icon.total-icon { color: #409EFF; }
.metric-icon.pending-icon { color: #E6A23C; }
.metric-icon.download-icon { color: #67C23A; }
.metric-icon.my-download-icon { color: #909399; }

.text-content {
  display: flex;
  flex-direction: column;
}

.metric-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #333;
}

.chart-card, .quick-links-card, .announcement-card {
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
  height: 50px; /* 减小按钮高度，更精致 */
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

.announcement-list .el-alert:not(:last-child) {
  margin-bottom: 8px;
}

@media (max-width: 992px) {
  .metric-inner-content {
    flex-direction: row;
    justify-content: center;
  }
  .quick-links-group {
    grid-template-columns: repeat(3, 1fr);
  }
  .quick-link-btn {
    height: 80px;
    font-size: 12px;
    flex-direction: column;
    gap: 4px;
  }
  .quick-link-btn .el-icon {
    font-size: 20px;
  }
}
</style>
