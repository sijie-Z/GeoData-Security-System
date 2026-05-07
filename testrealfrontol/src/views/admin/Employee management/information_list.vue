<script setup>
import { reactive, ref, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Refresh, Plus, User as UserIcon } from '@element-plus/icons-vue';
import { useI18n } from 'vue-i18n';
import Axios from '@/utils/Axios.js';

const { t } = useI18n();
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
      ElMessage.error(response.data.msg || t('employeeMgmt.fetchEmployeeFailed'));
    }
  } catch (err) {
    console.error('Failed to fetch employee data:', err);
    ElMessage.error(t('employeeMgmt.fetchEmployeeFailedNetwork'));
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
  ElMessage.info(t('employeeMgmt.refreshingData'));
  fetchData();
};

const handleDelete = (row) => {
  ElMessageBox.confirm(
    t('employeeMgmt.deleteConfirmMessage', { name: row.name, number: row.employee_number }),
    t('employeeMgmt.deleteEmployeeTitle'),
    {
      confirmButtonText: t('employeeMgmt.confirmDelete'),
      cancelButtonText: t('employeeMgmt.cancel'),
      type: 'warning',
      center: true,
      customStyle: 'width:360px;border-radius:12px;'
    }
  ).then(async () => {
    try {
      const response = await Axios.delete(`/api/admin/employee/${row.employee_number}`);
      ElMessage.success(response.data.message || t('employeeMgmt.deleteSuccess'));
      fetchData();
    } catch (error) {
      console.error('Delete failed:', error);
      ElMessage.error(error.response?.data?.message || t('employeeMgmt.deleteFailed'));
    }
  }).catch(() => {
    ElMessage.info(t('employeeMgmt.deleteCancelled'));
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
      <h2 class="page-title">{{ $t('employeeMgmt.employeeInfoList') }}</h2>
      <div class="action-bar">
        <el-button :icon="Plus" type="primary" @click="handleAdd">{{ $t('employeeMgmt.addNewEmployee') }}</el-button>
        <el-button :icon="Refresh" circle @click="handleRefresh" />
      </div>
    </div>
    <el-divider />
    <el-table :data="state.employeeList" v-loading="loading" style="width: 100%" stripe table-layout="auto">
      <template #empty><el-empty :description="$t('employeeMgmt.noEmployeeInfo')" /></template>
      <el-table-column :label="$t('employeeMgmt.photo')" width="80" align="center" fixed>
        <template #default="scope">
          <el-avatar :size="40" :src="scope.row.photo"><el-icon><UserIcon /></el-icon></el-avatar>
        </template>
      </el-table-column>
      <el-table-column prop="employee_number" :label="$t('employeeMgmt.employeeNumber')" width="180" sortable />
      <el-table-column prop="name" :label="$t('employeeMgmt.name')" width="120" />
      <el-table-column prop="job_number" :label="$t('employeeMgmt.jobNumber')" width="150" sortable />
      <el-table-column prop="phone_number" :label="$t('employeeMgmt.phoneNumber')" width="180" />
      <el-table-column prop="address" :label="$t('employeeMgmt.address')" min-width="250" show-overflow-tooltip />
      <el-table-column :label="$t('employeeMgmt.actions')" width="150" align="center" fixed="right">
        <template #default="scope">
          <!-- 【新增】为编辑按钮绑定点击事件 -->
          <el-button link type="primary" size="small" @click="handleEdit(scope.row)">{{ $t('employeeMgmt.edit') }}</el-button>
          <el-button link type="danger" size="small" @click="handleDelete(scope.row)">{{ $t('employeeMgmt.delete') }}</el-button>
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