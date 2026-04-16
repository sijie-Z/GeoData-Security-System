<!-- src/views/admin/Log Management/LogViewer.vue
<template>
    <div class="log-viewer-container">
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>系统操作日志</span>
          </div>
        </template>
  

        <div class="filter-container">
          <el-input v-model="filters.username" placeholder="按操作人搜索" style="width: 200px;" clearable @clear="handleFilterSearch" />
          <el-select v-model="filters.action" placeholder="按操作类型筛选" clearable @change="handleFilterSearch" style="width: 180px;">
            <el-option label="用户登录" value="用户登录"></el-option>
            <el-option label="提交数据申请" value="提交数据申请"></el-option>
            <el-option label="审批数据申请" value="审批数据申请"></el-option>
            <el-option label="生成水印" value="生成水印"></el-option>
            <el-option label="嵌入水印" value="嵌入水印"></el-option>
          </el-select>
          <el-button type="primary" :icon="Search" @click="handleFilterSearch">筛选</el-button>
        </div>
  

        <el-table :data="logList" border stripe v-loading="loading" style="width: 100%">
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="timestamp" label="操作时间" width="180" sortable></el-table-column>
          <el-table-column prop="username" label="操作人" width="120" sortable></el-table-column>
          <el-table-column prop="ip_address" label="IP地址" width="150"></el-table-column>
          <el-table-column prop="action" label="操作类型" width="150"></el-table-column>
          <el-table-column prop="status" label="状态" width="90" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.status === '成功' ? 'success' : 'danger'" effect="dark">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="详情">
            <template #default="scope">
              <pre class="details-box">{{ formatDetails(scope.row.details) }}</pre>
            </template>
          </el-table-column>
        </el-table>
  

        <div class="pagination-container">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            :page-size="pageSize"
            :current-page="currentPage"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>
    </div>
  </template>
  
  <script setup>
  import { ref, reactive, onMounted } from 'vue';
  import { Search } from '@element-plus/icons-vue';
  // 暂时不从后端获取，所以注释掉 axios
  // import axios from 'axios';
  
  // const basic_url = import.meta.env.VITE_API_URL;
  
  const loading = ref(false);
  const logList = ref([]);
  const total = ref(0);
  const currentPage = ref(1);
  const pageSize = ref(10);
  
  const filters = reactive({
    username: '',
    action: ''
  });
  
  // ==================== 使用模拟数据 ====================
  const mockLogData = [
  { id: 1, timestamp: '2025-06-15 10:30:05', username: 'adm1', ip_address: '127.0.0.1', action: '审批数据申请', status: '成功', details: { request_id: 101, applicant: '张三丰', decision: '通过', shp_name: '苏州市商业区划' } },
  { id: 2, timestamp: '2025-06-15 09:15:22', username: 'employee_gis', ip_address: '127.0.0.1', action: '提交数据申请', status: '成功', details: { data_id: 205, data_name: '长江流域水系', reason: '年度报告分析' } },
  { id: 3, timestamp: '2025-06-14 17:05:00', username: 'employee_data', ip_address: '127.0.0.1', action: '用户登录', status: '成功', details: null },
  { id: 4, timestamp: '2025-06-14 16:30:15', username: 'adm1', ip_address: '127.0.0.1', action: '嵌入水印', status: '成功', details: { data_id: 203, data_name: '全国高速公路网', applicant: '李四' } },
  { id: 5, timestamp: '2025-06-14 14:20:45', username: 'adm1', ip_address: '127.0.0.1', action: '生成水印', status: '成功', details: { request_id: 98, for_data: '城市绿地分布' } },
  { id: 6, timestamp: '2025-06-13 11:00:30', username: 'guest_user', ip_address: '127.0.0.1', action: '用户登录', status: '失败', details: { reason: '密码连续错误三次，账户已锁定' } },
  { id: 7, timestamp: '2025-06-13 10:50:10', username: 'adm2', ip_address: '127.0.0.1', action: '审批数据申请', status: '驳回', details: { request_id: 95, applicant: '王五', reason: '申请信息不完整', shp_name: '土地利用类型' } },
  { id: 8, timestamp: '2025-06-12 15:00:00', username: 'employee_gis', ip_address: '127.0.0.1', action: '数据上传', status: '成功', details: { filename: 'new_district_plan.zip', size: '5.2MB' } },
  { id: 9, timestamp: '2025-06-12 14:30:00', username: 'adm1', ip_address: '127.0.0.1', action: '用户权限修改', status: '成功', details: { target_user: 'employee_data', new_role: '高级分析员' } },
  { id: 10, timestamp: '2025-06-11 18:00:00', username: 'system_batch', ip_address: '::1', action: '数据备份', status: '成功', details: { target: 'PostGIS_DB', duration: '35min' } },
  { id: 11, timestamp: '2025-05-20 10:00:00', username: 'employee_data', ip_address: '127.0.0.1', action: '提交数据申请', status: '成功', details: { data_id: 199, data_name: '历史气象站点数据', reason: '气候变化研究' } },
  { id: 12, timestamp: '2025-05-19 11:30:00', username: 'adm1', ip_address: '127.0.0.1', action: '系统参数配置', status: '成功', details: { parameter: 'session_timeout', new_value: '60min' } },
  { id: 13, timestamp: '2025-05-18 16:45:00', username: 'test_user_01', ip_address: '127.0.0.1', action: '用户登录', status: '成功', details: null },
  { id: 14, timestamp: '2025-05-18 09:00:00', username: 'employee_gis', ip_address: '127.0.0.1', action: '提取水印', status: '成功', details: { data_id: 180, data_name: '受保护区域影像' } },
  { id: 15, timestamp: '2025-05-17 14:00:00', username: 'adm2', ip_address: '127.0.0.1', action: '审批数据申请', status: '通过', details: { request_id: 88, applicant: '赵六', decision: '部分通过', shp_name: '季度销售数据' } },
  { id: 16, timestamp: '2025-06-16 11:00:00', username: 'adm1', ip_address: '127.0.0.1', action: '用户登出', status: '成功', details: null },
  { id: 17, timestamp: '2025-06-16 10:55:00', username: 'employee_sec', ip_address: '127.0.0.1', action: '安全策略更新', status: '成功', details: { policy_id: 'SEC-003', description: '增强密码复杂度要求' } },
  { id: 18, timestamp: '2025-06-16 09:30:00', username: 'employee_gis', ip_address: '127.0.0.1', action: '下载数据', status: '成功', details: { data_id: 210, data_name: '地形DEM数据', format: 'GeoTIFF' } },
  { id: 19, timestamp: '2025-06-15 18:00:00', username: 'data_analyst', ip_address: '127.0.0.1', action: '生成报告', status: '成功', details: { report_name: '月度空间数据使用分析', period: '2025-05' } },
  { id: 20, timestamp: '2025-06-15 17:30:00', username: 'adm1', ip_address: '127.0.0.1', action: '删除用户', status: '成功', details: { deleted_user: 'temp_user002', reason: '账户过期' } },
  // 你可以继续添加更多数据...
];
  
  const fetchLogs = async () => {
    loading.value = true;
    console.log('Fetching logs with filters:', filters);
    // 模拟API调用延迟
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // 模拟筛选逻辑
    let filteredData = mockLogData.filter(log => {
      const userMatch = filters.username ? log.username.includes(filters.username) : true;
      const actionMatch = filters.action ? log.action === filters.action : true;
      return userMatch && actionMatch;
    });
  
    total.value = filteredData.length;
  
    // 模拟分页逻辑
    const start = (currentPage.value - 1) * pageSize.value;
    const end = start + pageSize.value;
    logList.value = filteredData.slice(start, end);
    
    loading.value = false;
  };
  
  const handlePageChange = (page) => {
    currentPage.value = page;
    fetchLogs();
  };
  
  const handleSizeChange = (size) => {
    pageSize.value = size;
    currentPage.value = 1; // 改变每页数量时回到第一页
    fetchLogs();
  };
  
  const handleFilterSearch = () => {
    currentPage.value = 1;
    fetchLogs();
  };
  
  const formatDetails = (details) => {
    if (details && typeof details === 'object') {
      return JSON.stringify(details, null, 2);
    }
    return details || '无';
  };
  
  onMounted(fetchLogs);
  </script>
  
  <style scoped>
  .log-viewer-container {
    padding: 20px;
  }
  .filter-container {
    margin-bottom: 20px;
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
  .details-box {
    white-space: pre-wrap;
    word-wrap: break-word;
    background-color: #f8f9fa;
    padding: 10px;
    border-radius: 4px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 13px;
    color: #333;
    margin: 0;
  }
  .card-header {
    font-size: 18px;
    font-weight: 600;
  }
  </style> -->


  <template>
    <div class="log-viewer-container">
      <el-card class="box-card">
        <template #header>
          <div class="card-header">
            <span>系统操作日志</span>
          </div>
        </template>
  
        <!-- 筛选区域 -->
        <div class="filter-container">
          <el-input
            v-model="filters.username"
            placeholder="按操作人搜索"
            style="width: 200px;"
            clearable
            @clear="handleFilterSearch"
            @keyup.enter="handleFilterSearch"
          />
          <el-select
            v-model="filters.action"
            placeholder="按操作类型筛选"
            clearable
            @change="handleFilterSearch"
            style="width: 220px;"
          >
            <el-option label="所有类型" value=""></el-option>
            <el-option label="用户登录" value="用户登录"></el-option>
            <el-option label="提交数据申请" value="提交数据申请"></el-option>
            <el-option label="审批数据申请" value="审批数据申请"></el-option>
            <el-option label="生成水印" value="生成水印"></el-option>
            <el-option label="嵌入水印" value="嵌入水印"></el-option>
            <el-option label="数据上传" value="数据上传"></el-option>
            <el-option label="用户权限修改" value="用户权限修改"></el-option>
            <el-option label="数据备份" value="数据备份"></el-option>
            <el-option label="提取水印" value="提取水印"></el-option>
            <el-option label="用户登出" value="用户登出"></el-option>
            <el-option label="安全策略更新" value="安全策略更新"></el-option>
            <el-option label="下载数据" value="下载数据"></el-option>
            <el-option label="生成报告" value="生成报告"></el-option>
            <el-option label="删除用户" value="删除用户"></el-option>
            <el-option label="系统参数配置" value="系统参数配置"></el-option>
          </el-select>
          <el-button type="primary" :icon="Search" @click="handleFilterSearch">筛选</el-button>
        </div>
  
        <!-- 日志表格 -->
        <el-table
          :data="logList"
          border
          stripe
          v-loading="loading"
          style="width: 100%"
          class="log-table"
        >
          <el-table-column type="index" label="#" width="50" fixed />
          <el-table-column prop="timestamp" label="操作时间" width="180" sortable fixed />
          <el-table-column prop="username" label="操作人" width="120" sortable />
          <el-table-column prop="ip_address" label="IP地址" width="150" />
          <el-table-column prop="action" label="操作类型" width="150" />
          <el-table-column prop="status" label="状态" width="90" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.status === '成功' ? 'success' : 'danger'" effect="dark">
                {{ scope.row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="详情" min-width="250">
            <template #default="scope">
              <pre class="details-box">{{ formatDetails(scope.row.details) }}</pre>
            </template>
          </el-table-column>
        </el-table>
  
        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next, jumper"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            v-model:page-size="pageSize"
            v-model:current-page="currentPage"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>
    </div>
  </template>
  
  <script setup>
  import { ref, reactive, onMounted } from 'vue';
  import { Search } from '@element-plus/icons-vue';
  import { ElMessage } from 'element-plus';
  import axios from 'axios';
  
  const basic_url = import.meta.env.VITE_API_URL;
  
  const loading = ref(false);
  const logList = ref([]);
  const total = ref(0);
  const currentPage = ref(1);
  const pageSize = ref(10); // 初始每页显示条数
  
  const filters = reactive({
    username: '',
    action: ''
  });
  
  const fetchLogs = async () => {
    loading.value = true;
    console.log('Fetching logs with filters:', JSON.parse(JSON.stringify(filters)), 'Page:', currentPage.value, 'Size:', pageSize.value);
    try {
      const response = await axios.get(`${basic_url}/api/admin/logs`, {
        params: {
          page: currentPage.value,
          pageSize: pageSize.value,
          username: filters.username || undefined, // 如果为空字符串则不发送该参数
          action: filters.action || undefined    // 如果为空字符串则不发送该参数
        }
      });
      const result = response.data;
      console.log("Full response from backend:", JSON.parse(JSON.stringify(result)));
  
      if (result && result.status === true && result.data) {
        logList.value = result.data.list || [];
        total.value = result.data.total || 0;
      } else {
        logList.value = [];
        total.value = 0;
        ElMessage.error(result.msg || '获取日志数据失败');
        console.error("Failed to fetch logs or unexpected data structure:", result);
      }
    } catch (error) {
      console.error('Error fetching logs:', error);
      logList.value = [];
      total.value = 0;
      if (error.response) {
        ElMessage.error(`获取日志失败: ${(error.response.data && error.response.data.msg) ? error.response.data.msg : error.message} (状态码: ${error.response.status})`);
      } else if (error.request) {
        ElMessage.error('网络错误，无法连接到服务器');
      } else {
        ElMessage.error('请求设置时发生错误');
      }
    } finally {
      loading.value = false;
    }
  };
  
  const handlePageChange = (page) => {
    // currentPage.value 已经通过 v-model:current-page 更新了
    fetchLogs();
  };
  
  const handleSizeChange = (size) => {
    // pageSize.value 已经通过 v-model:page-size 更新了
    currentPage.value = 1; // 改变每页数量时通常回到第一页
    fetchLogs();
  };
  
  const handleFilterSearch = () => {
    currentPage.value = 1; // 筛选时回到第一页
    fetchLogs();
  };
  
  const formatDetails = (details) => {
    if (details === null || details === undefined) {
      return '无';
    }
    if (typeof details === 'object') {
      try {
        return JSON.stringify(details, null, 2); // 格式化JSON并美化输出
      } catch (e) {
        return String(details); // 如果JSON序列化失败，转为字符串
      }
    }
    return String(details); // 其他类型直接转为字符串
  };
  
  onMounted(() => {
    fetchLogs(); // 组件挂载时获取初始数据
  });
  </script>
  
  <style scoped>
  .log-viewer-container {
    padding: 20px;
    /* 这个容器本身不应该限制高度，让父级来控制滚动 */
  }
  
  .box-card {
    /* 卡片可以占据父容器给予的空间 */
  }
  
  .filter-container {
    margin-bottom: 20px;
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap; /* 允许筛选条件在小屏幕上换行 */
  }
  
  .log-table {
    /* 表格宽度100%由父容器（el-card的body）决定 */
    /* 表格高度自适应内容，如果内容超出父组件MainContentArea的视口，则MainContentArea滚动 */
  }
  
  .pagination-container {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end; /* 分页组件靠右显示 */
  }
  
  .details-box {
    white-space: pre-wrap;    /* 保留空格和换行，并在需要时自动换行 */
    word-wrap: break-word;  /* 旧版浏览器兼容 */
    word-break: break-all;  /* 允许在任意字符间换行，防止长字符串撑破布局 */
    background-color: #f8f9fa;
    padding: 10px;
    border-radius: 4px;
    font-family: 'Courier New', Courier, monospace;
    font-size: 13px;
    color: #333;
    margin: 0;
    max-height: 200px; /* 如果详情内容过多，给一个最大高度并允许滚动 */
    overflow-y: auto;
  }
  
  .card-header {
    font-size: 18px;
    font-weight: 600;
  }
  </style>