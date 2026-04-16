<!-- <template>
  <div>

    <el-table :data="data.list" border style="width: 702px">
      <el-table-column prop="application_id" label="申请编号" width="85" />
      <el-table-column prop="data_alias" label="数据名称" width="85" />
      <el-table-column prop="data_id" label="矢量数据编号" width="110" />
      <el-table-column prop="applicant_user_number" label="申请人编号" width="100" />
      <el-table-column prop="applicant_name" label="申请人姓名" width="100" />
      <el-table-column prop="send_file_person_user_number" label="数据发送人" width="100"/>

      <el-table-column label="操作" width="122">
        <template v-slot="scope">
          <el-button size="small" type="primary" @click="download(scope.row)">下载数据</el-button>
        </template>
      </el-table-column>
    </el-table>

  </div>
  <div>

    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="prev, pager, next, jumper, total"
      @current-change="pageChanged"
      class="view-pagination"
    />

  </div>

</template>

<script setup>
import { reactive, onMounted, ref, watch, computed } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";
import { useUserStore } from "@/stores/userStore.js";

const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);


const basic_url=import.meta.env.VITE_API_URL



const data = reactive({
  list: [],
});

const page = ref(1);
const pageSize = ref(2);
const total = ref(0);

const pageChanged = (newPage) => {
  page.value = newPage;
};

watch(page, (newValue, oldValue) => {
  if (oldValue !== newValue) {
    get_applications(); // 重新获取列表
  }
});

const get_applications = async () => {
  try {
    const response = await axios.get(`${basic_url}/api/get_approved_applications`, {
      params: { page: page.value, pageSize: pageSize.value, userNumber: userNumber.value },
    });
    // console.log('get_response:', response.data); // 打印数据
    if (response.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }
    if (!response.data.status) {
      ElMessage.error(response.data.msg);
      return;
    }
    data.list = response.data.emp_get_applications;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error("Error", err);
    ElMessage.error("获取记录失败");
  }
};

onMounted(() => {
  get_applications();
});


const download = async (row) => {
  try {
    const response = await axios.post(`${basic_url}/api/emp_download_zip`, {
      application_id: row.application_id,
      data_id: row.data_id,
      applicant_user_number: row.applicant_user_number,
      applicant: row.applicant_name,
      send_file_person_user_number:row.send_file_person_user_number
    }, {
      responseType: 'blob' // 确保接收的是二进制文件流
    });

    // 从响应头中提取文件名
    const contentDisposition = response.headers['content-disposition'];
    let fileName = 'downloaded_file.zip'; // 默认文件名

    if (contentDisposition) {
      console.log('Content-Disposition Header:', contentDisposition); // 打印响应头

      // 使用正则表达式提取文件名
      const fileNameMatch = contentDisposition.match(/filename="([^"]*)"/);
      if (fileNameMatch && fileNameMatch[1]) {
        fileName = fileNameMatch[1];
        console.log('Extracted File Name:', fileName); // 打印提取的文件名

        // 提取文件名中最后一个 '__' 之后的部分
        const lastUnderscoreIndex = fileName.lastIndexOf('__');
        if (lastUnderscoreIndex !== -1) {
          fileName = fileName.substring(lastUnderscoreIndex + 2);
        }
      }
    }

    await axios.post(`${basic_url}/api/record_download_file`,{

      application_id: row.application_id,
      data_id: row.data_id,
      applicant_user_number: row.applicant_user_number,
      applicant: row.applicant_name,
      send_file_person_user_number:row.send_file_person_user_number,
      fileName:fileName

    })

    // 创建一个链接元素
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;

    // 设置下载文件名
    link.setAttribute('download', fileName);

    // 触发下载
    document.body.appendChild(link);
    link.click();

    // 移除链接元素
    document.body.removeChild(link);
  } catch (error) {
    console.error('Download error:', error);
    ElMessage.error('下载失败');
  }
};

</script>

<style scoped>
.view-pagination {
  margin-top: 20px;
}
</style> -->



<template>
  <el-card class="page-container" shadow="never">
    <!-- 顶部标题和操作区 -->
    <template #header>
      <div class="card-header">
        <span>已批准数据下载</span>
        <el-button :icon="Refresh" circle @click="get_applications" :loading="loading" />
      </div>
    </template>

    <!-- 主内容区域：卡片列表或空状态 -->
    <div v-if="!loading && data.list.length > 0" class="data-card-list">
      <el-card v-for="item in data.list" :key="item.application_id" class="data-card" shadow="hover">
        <div class="card-content">
          <!-- 左侧信息区 -->
          <div class="info-section">
            <el-descriptions :column="1" size="small">
              <el-descriptions-item label="申请 ID">#{{ item.application_id }}</el-descriptions-item>
              <el-descriptions-item label="数据名称"><strong>{{ item.data_alias }}</strong></el-descriptions-item>
              <el-descriptions-item label="矢量数据 ID">{{ item.data_id }}</el-descriptions-item>
              <el-descriptions-item label="数据提供方">{{ item.send_file_person_user_number }}</el-descriptions-item>
            </el-descriptions>
          </div>
          <!-- 右侧操作区 -->
          <div class="action-section">
            <el-button 
              type="primary" 
              size="large" 
              :icon="Download"
              @click="download(item)"
              :loading="downloadingStatus[item.application_id]"
            >
              下载数据
            </el-button>
          </div>
        </div>
      </el-card>
    </div>
    
    <!-- 加载状态 -->
    <div v-if="loading" v-loading="loading" class="loading-placeholder"></div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && data.list.length === 0" description="暂无已批准的可下载数据" />

    <!-- 分页器 -->
    <div v-if="total > 0" class="pagination-container">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        background
        @current-change="pageChanged"
      />
    </div>
  </el-card>
</template>

<script setup>
// [新增] 导入 Refresh 和 Download 图标
import { Refresh, Download } from "@element-plus/icons-vue";
import { reactive, onMounted, ref, watch, computed } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";
import { useUserStore } from "@/stores/userStore.js";

const userStore = useUserStore();
const userNumber = computed(() => userStore.userNumber);
const basic_url = import.meta.env.VITE_API_URL;

// [新增] 页面加载状态和下载按钮的独立加载状态
const loading = ref(true);
const downloadingStatus = reactive({});

const data = reactive({
  list: [],
});

const page = ref(1);
const pageSize = ref(5); // 每页显示5个卡片
const total = ref(0);

const pageChanged = (newPage) => {
  page.value = newPage;
};

watch(page, () => {
  get_applications();
});

const get_applications = async () => {
  loading.value = true;
  try {
    const response = await axios.get(`${basic_url}/api/get_approved_applications`, {
      params: { page: page.value, pageSize: pageSize.value, userNumber: userNumber.value },
    });
    
    if (response.data == null) {
      data.list = [];
      total.value = 0;
      return;
    }
    if (response.data.status === false) {
      ElMessage.error(response.data.msg);
      data.list = [];
      total.value = 0;
      return;
    }
    data.list = response.data.emp_get_applications;
    total.value = response.data.pages.total;
  } catch (err) {
    console.error("Error", err);
    ElMessage.error("获取记录失败");
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  get_applications();
});

// 下载逻辑保持不变，但增加了按钮加载状态的控制
const download = async (row) => {
  downloadingStatus[row.application_id] = true; // 开始下载，设置对应按钮为加载状态
  try {
    const response = await axios.post(`${basic_url}/api/emp_download_zip`, {
      application_id: row.application_id,
      data_id: row.data_id,
      applicant_user_number: row.applicant_user_number,
      applicant: row.applicant_name,
      send_file_person_user_number: row.send_file_person_user_number
    }, {
      responseType: 'blob'
    });

    const contentDisposition = response.headers['content-disposition'];
    let fileName = 'downloaded_file.zip';

    if (contentDisposition) {
      const fileNameMatch = contentDisposition.match(/filename="([^"]*)"/);
      if (fileNameMatch && fileNameMatch[1]) {
        fileName = decodeURIComponent(fileNameMatch[1]); // [优化] 解码文件名以支持中文
        const lastUnderscoreIndex = fileName.lastIndexOf('__');
        if (lastUnderscoreIndex !== -1) {
          fileName = fileName.substring(lastUnderscoreIndex + 2);
        }
      }
    }

    await axios.post(`${basic_url}/api/record_download_file`, {
      application_id: row.application_id,
      data_id: row.data_id,
      applicant_user_number: row.applicant_user_number,
      applicant: row.applicant_name,
      send_file_person_user_number: row.send_file_person_user_number,
      fileName: fileName
    });

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url); // [优化] 释放内存
  } catch (error) {
    console.error('Download error:', error);
    ElMessage.error('下载失败，请稍后重试');
  } finally {
    downloadingStatus[row.application_id] = false; // 结束下载，恢复按钮状态
  }
};
</script>

<style scoped>
.page-container {
  border-radius: 8px;
  min-height: calc(100vh - 110px);
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header span {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

.loading-placeholder {
  min-height: 300px;
}

.data-card-list {
  display: flex;
  flex-direction: column;
  gap: 16px; /* 卡片之间的垂直间距 */
}

.data-card {
  border-radius: 8px;
  transition: box-shadow 0.3s;
}

.card-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.info-section {
  flex-grow: 1;
}

.action-section {
  flex-shrink: 0;
  margin-left: 24px;
}

/* 覆盖 el-descriptions 的样式 */
:deep(.el-descriptions__label) {
  color: #909399;
}
:deep(.el-descriptions__content) {
  color: #303133;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: auto; /* 将分页器推到底部 */
  padding-top: 24px; /* 与上方内容保持间距 */
  padding-bottom: 10px;
}
</style>