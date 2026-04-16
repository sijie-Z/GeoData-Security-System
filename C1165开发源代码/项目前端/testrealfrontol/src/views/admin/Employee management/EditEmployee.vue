<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Back, User as UserIcon, Plus as PlusIcon } from '@element-plus/icons-vue';
import Axios from '@/utils/Axios.js';

const router = useRouter();
const route = useRoute();
const formRef = ref(null);
const submitLoading = ref(false);

const formData = reactive({
  id: null,
  employee_number: '',
  name: '',
  job_number: '',
  id_number: '',
  phone_number: '',
  address: '',
  photo: null,
  current_photo_url: '' // 用于显示当前的照片
});
const photoFileList = ref([]);

// 编辑时，密码不是必填项，只有在输入时才校验
const rules = reactive({
  employee_number: [{ required: true, message: '员工编号不能为空', trigger: 'blur' }],
  name: [{ required: true, message: '姓名不能为空', trigger: 'blur' }],
  // ... 其他校验规则可以根据需要调整 ...
});

const handleBack = () => router.back();

const fetchEmployeeData = async (employeeNumber) => {
  try {
    // 后端需要一个 /api/employee/details/{id} 接口来获取单个员工信息
    const response = await Axios.get(`/api/employee/details/${employeeNumber}`);
    if (response.data && response.data.status) {
      Object.assign(formData, response.data.data);
      // 如果有照片，设置预览
      if(response.data.data.has_photo) {
        formData.current_photo_url = `http://localhost:5001/api/employee/photo/${employeeNumber}`;
        photoFileList.value = [{ name: 'current_photo.jpg', url: formData.current_photo_url }];
      }
    } else {
      ElMessage.error('获取员工信息失败');
    }
  } catch (error) {
    ElMessage.error('获取员工信息失败，请检查网络');
  }
};

const handleFileChange = (uploadFile) => {
  formData.photo = uploadFile.raw; // 存储新文件
};

const handleRemove = () => {
  formData.photo = null;
  formData.current_photo_url = ''; // 移除预览
};

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true;
      const submitData = new FormData();
      // 只添加需要更新的字段
      submitData.append('employee_number', formData.employee_number);
      submitData.append('name', formData.name);
      submitData.append('job_number', formData.job_number);
      submitData.append('id_number', formData.id_number);
      submitData.append('phone_number', formData.phone_number);
      submitData.append('address', formData.address);
      if (formData.photo) {
        submitData.append('photo', formData.photo);
      }
      
      try {
        // 后端需要一个 PUT /api/employee/{id} 接口来更新员工信息
        const response = await Axios.put(`/api/employee/${formData.employee_number}`, submitData);
        if (response.data && response.data.status) {
          ElMessage.success('员工信息更新成功！');
          router.push('/admin/employee_management/information_list');
        } else {
          ElMessage.error(response.data.msg || '更新失败');
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.msg || '请求失败');
      } finally {
        submitLoading.value = false;
      }
    }
  });
};

onMounted(() => {
  const employeeId = route.params.id;
  if (employeeId) {
    fetchEmployeeData(employeeId);
  }
});
</script>

<template>
  <div class="page-container">
    <el-page-header :icon="Back" title="返回列表" @back="handleBack">
      <template #content><span class="page-title">编辑员工信息</span></template>
    </el-page-header>
    <el-divider />
    <div class="form-wrapper">
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px" style="max-width: 700px;">
        <h3 class="form-section-title">基本信息</h3>
        <el-form-item label="员工编号" prop="employee_number">
          <el-input v-model="formData.employee_number" disabled />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="姓名" prop="name"><el-input v-model="formData.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="工号" prop="job_number"><el-input v-model="formData.job_number" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="身份证号" prop="id_number"><el-input v-model="formData.id_number" /></el-form-item>
        <el-form-item label="手机号码" prop="phone_number"><el-input v-model="formData.phone_number" /></el-form-item>
        <el-form-item label="住址" prop="address"><el-input v-model="formData.address" type="textarea" :rows="2" /></el-form-item>
        
        <h3 class="form-section-title">员工照片</h3>
        <el-form-item label="更新照片" prop="photo">
          <el-upload
            v-model:file-list="photoFileList" action="#" list-type="picture-card"
            :limit="1" :auto-upload="false" :on-change="handleFileChange" :on-remove="handleRemove">
            <el-icon><PlusIcon /></el-icon>
            <template #tip><div class="el-upload__tip">如需更换照片请上传，否则将保留原照片。</div></template>
          </el-upload>
        </el-form-item>
        
        <el-divider />
        <el-form-item>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">保存修改</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
/* 样式可以复用 information_add.vue 的样式 */
.page-container { padding: 24px; background-color: #f9fafb; height: 100%; box-sizing: border-box; }
.page-title { font-size: 20px; font-weight: 600; color: #1f2937; }
.form-wrapper { margin-top: 20px; background-color: #fff; padding: 30px; border-radius: 8px; border: 1px solid #e5e7eb; }
.form-section-title { font-size: 16px; font-weight: 500; color: #374151; margin: 0 0 24px 0; padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
.el-upload__tip { color: #9ca3af; font-size: 12px; margin-top: 8px; line-height: 1.5; }
</style>