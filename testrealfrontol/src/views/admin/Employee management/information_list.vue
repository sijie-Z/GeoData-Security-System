<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh, Plus, User as UserIcon } from '@element-plus/icons-vue';
import Axios from '@/utils/Axios.js';

const router = useRouter();
const loading = ref(true);
const state = reactive({ employeeList: [] });
const objectUrls = ref(new Set());

const fetchEmployeePhoto = async (employeeNumber) => {
  if (!employeeNumber) return null;
  try {
    const response = await Axios.get(`/api/employee/photo/${employeeNumber}`, { responseType: 'blob' });
    const url = URL.createObjectURL(response.data);
    objectUrls.value.add(url);
    return url;
  } catch (error) {
    console.error(`Failed to fetch photo for employee ${employeeNumber}:`, error);
    return null;
  }
};

const revokeObjectUrls = () => {
  objectUrls.value.forEach(url => {
    URL.revokeObjectURL(url);
  });
  objectUrls.value.clear();
};

const fetchData = async () => {
  loading.value = true;
  state.employeeList = [];
  try {
    const response = await Axios.get('/api/adm/get_emp_info_list');
    if (response.data && response.data.status) {
      const rawList = response.data.data.list;
      state.employeeList = await Promise.all(rawList.map(async (item) => {
        const photoSrc = await fetchEmployeePhoto(item.employee_number);
        return { ...item, photo: photoSrc };
      }));
    } else {
      ElMessage.error(response.data.msg || '获取员工信息失败');
    }
  } catch (err) {
    console.error('Failed to fetch employee data:', err);
    ElMessage.error('获取员工信息失败，请检查网络连接');
  } finally {
    loading.value = false;
  }
};

const handleAdd = () => {
  router.push('/admin/employee_management/information_add'); 
};

// 【新增】处理编辑按钮点击事件
const handleEdit = (row) => {
  router.push(`/admin/employee_management/edit/${row.employee_number}`);
};

const handleRefresh = () => {
  ElMessage.info('正在刷新数据...');
  fetchData();
};

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除员工 "${row.name}" (编号：${row.employee_number}) 吗？删除后无法恢复，请确认是否继续？`,
    '删除员工',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      center: true,
      customStyle: 'width:360px;border-radius:12px;'
    }
  ).then(async () => {
    try {
      const response = await Axios.delete(`/api/admin/employee/${row.employee_number}`);
      ElMessage.success(response.data.message || '删除成功');
      fetchData();
    } catch (error) {
      console.error('Delete failed:', error);
      ElMessage.error(error.response?.data?.message || '删除失败，请稍后重试');
    }
  }).catch(() => {
    ElMessage.info('已取消删除');
  });
};

onMounted(fetchData);

onBeforeUnmount(() => {
  revokeObjectUrls();
});
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h2 class="page-title">员工信息列表</h2>
      <div class="action-bar">
        <el-button :icon="Plus" type="primary" @click="handleAdd">添加新员工</el-button>
        <el-button :icon="Refresh" circle @click="handleRefresh" />
      </div>
    </div>
    <el-divider />
    <el-table :data="state.employeeList" v-loading="loading" style="width: 100%" stripe table-layout="auto">
      <template #empty><el-empty description="暂无员工信息" /></template>
      <el-table-column label="照片" width="80" align="center" fixed>
        <template #default="scope">
          <el-avatar :size="40" :src="scope.row.photo"><el-icon><UserIcon /></el-icon></el-avatar>
        </template>
      </el-table-column>
      <el-table-column prop="employee_number" label="员工编号" width="180" sortable />
      <el-table-column prop="name" label="姓名" width="120" />
      <el-table-column prop="job_number" label="工号" width="150" sortable />
      <el-table-column prop="phone_number" label="手机号码" width="180" />
      <el-table-column prop="address" label="住址" min-width="250" show-overflow-tooltip />
      <el-table-column label="操作" width="150" align="center" fixed="right">
        <template #default="scope">
          <!-- 【新增】为编辑按钮绑定点击事件 -->
          <el-button link type="primary" size="small" @click="handleEdit(scope.row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.page-container { padding: 24px; background-color: #fff; height: 100%; display: flex; flex-direction: column; }
.page-header { display: flex; justify-content: space-between; align-items: center; }
.page-title { font-size: 22px; font-weight: 600; color: #303133; margin: 0; }
.action-bar { display: flex; gap: 10px; }
.el-table { flex-grow: 1; }
</style>