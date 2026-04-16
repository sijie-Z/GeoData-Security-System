<!-- <script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Back, Plus as PlusIcon } from '@element-plus/icons-vue';
import Axios from '@/utils/Axios.js';

// --- 依赖与初始化 ---
const router = useRouter();
const formRef = ref(null);

// --- 响应式数据 ---

// 表单数据模型
const formData = reactive({
  employee_number: '',
  name: '',
  job_number: '',
  phone_number: '',
  address: '',
  photo: null, // 将存储待上传的 File 对象
});

// 用于驱动 el-upload UI 的文件列表
const photoFileList = ref([]);
const submitLoading = ref(false);

// --- 表单校验规则 (包含照片必填项) ---
const rules = reactive({
  employee_number: [{ required: true, message: '请输入员工编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  job_number: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  phone_number: [
    { required: true, message: '请输入手机号码', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号码', trigger: 'blur' }
  ],
  address: [{ required: true, message: '请输入住址', trigger: 'blur' }],
  // 照片的校验规则，确保它被视为必填项
  photo: [{ required: true, message: '必须上传一张员工照片', trigger: 'change' }]
});


// --- 方法与逻辑 ---

const handleBack = () => {
  router.back();
};

// el-upload 的钩子函数，在文件状态改变时触发 (选择、移除)
const handleFileChange = (uploadFile, uploadFiles) => {
  const rawFile = uploadFile.raw;
  const isJpgOrPng = ['image/jpeg', 'image/png'].includes(rawFile.type);
  const isLt5M = rawFile.size / 1024 / 1024 < 5;

  if (!isJpgOrPng) {
    ElMessage.error('照片只支持 JPG/PNG 格式!');
    photoFileList.value = uploadFiles.filter(f => f.uid !== uploadFile.uid); // 从UI移除不合格文件
    return;
  }
  if (!isLt5M) {
    ElMessage.error('照片大小不能超过 5MB!');
    photoFileList.value = uploadFiles.filter(f => f.uid !== uploadFile.uid); // 从UI移除不合格文件
    return;
  }
  
  // 校验通过，存储文件对象
  formData.photo = rawFile;
  // 手动触发照片字段的校验，以清除可能存在的错误提示
  formRef.value?.validateField('photo');
};

const handleRemove = () => {
  formData.photo = null;
};

const handleExceed = () => {
  ElMessage.warning('只能上传一张员工照片，请先移除当前照片再重新上传');
};

const submitForm = async () => {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true;
      try {
        const submitData = new FormData();
        for (const [key, value] of Object.entries(formData)) {
          if (value !== null) {
            submitData.append(key, value);
          }
        }
        
        // ========================================================
        // === 这里是与后端交互的核心，现在它会失败 ===
        const response = await Axios.post('/api/adm/add_employee', submitData);
        // ========================================================

        if (response.data && response.data.status) {
          ElMessage.success('新员工添加成功！');
          resetForm();
        } else {
          ElMessage.error(response.data.msg || '添加失败');
        }
      } catch (error) {
        // !!! 在没有后端的情况下，代码一定会进入这个 catch 块 !!!
        console.error('【前端调试信息】表单提交失败:', error);
        ElMessage.error('请求失败，请检查网络或联系管理员');
      } finally {
        submitLoading.value = false;
      }
    } else {
      ElMessage.error('表单信息填写不完整，请检查红色提示项');
    }
  });
};

const resetForm = () => {
  formRef.value?.resetFields();
  photoFileList.value = [];
  formData.photo = null;
};
</script>

<template>
  <div class="page-container">
    <el-page-header :icon="Back" title="返回" @back="handleBack">
      <template #content><span class="page-title">添加新员工</span></template>
    </el-page-header>
    <el-divider />
    <div class="form-wrapper">
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px" style="max-width: 700px;">
        <h3 class="form-section-title">基本信息</h3>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="员工编号" prop="employee_number"><el-input v-model="formData.employee_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="姓名" prop="name"><el-input v-model="formData.name" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="工号" prop="job_number"><el-input v-model="formData.job_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="手机号码" prop="phone_number"><el-input v-model="formData.phone_number" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="住址" prop="address"><el-input v-model="formData.address" type="textarea" :rows="2" /></el-form-item>
        
        <h3 class="form-section-title">员工照片</h3>
        <el-form-item label="上传照片" prop="photo">
          <el-upload
            v-model:file-list="photoFileList"
            action="#"
            list-type="picture-card"
            :limit="1"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleRemove"
            @exceed="handleExceed"
          >
            <el-icon><PlusIcon /></el-icon>
            <template #tip><div class="el-upload__tip">请上传JPG/PNG格式照片, 大小不超过5MB。</div></template>
          </el-upload>
        </el-form-item>
        
        <el-divider />
        <el-form-item>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">确认添加</el-button>
          <el-button @click="resetForm">重置所有</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.page-container { padding: 24px; background-color: #fff; height: 100%; }
.page-title { font-size: 18px; font-weight: 600; }
.form-wrapper { margin-top: 20px; }
.form-section-title { font-size: 16px; font-weight: 500; color: #303133; margin: 0 0 20px 0; padding-bottom: 10px; border-bottom: 1px solid #e4e7ed; }
.el-upload__tip { color: #909399; font-size: 12px; margin-top: 7px; }
</style> -->







<script setup>
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Back, Plus as PlusIcon } from '@element-plus/icons-vue';
import Axios from '@/utils/Axios.js';

const router = useRouter();
const formRef = ref(null);
const photoFileList = ref([]);
const submitLoading = ref(false);

const formData = reactive({
  employee_number: '',
  name: '',
  job_number: '',
  id_number: '',
  phone_number: '',
  address: '',
  photo: null,
  password: '',
});

const rules = reactive({
  employee_number: [{ required: true, message: '请输入员工编号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  job_number: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  id_number: [{ required: true, message: '请输入18位身份证号', trigger: 'blur' }, { len: 18, message: '身份证号必须为18位', trigger: 'blur' }],
  phone_number: [{ required: true, message: '请输入手机号码', trigger: 'blur' }, { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的手机号码', trigger: 'blur' }],
  address: [{ required: true, message: '请输入住址', trigger: 'blur' }],
  photo: [{ required: true, message: '必须上传一张员工照片', trigger: 'change' }],
  password: [{ required: true, message: '必须为新员工设置初始密码', trigger: 'blur' }],
});

const handleBack = () => router.back();

const handleFileChange = (uploadFile, uploadFiles) => {
  const rawFile = uploadFile.raw;
  const isJpgOrPng = ['image/jpeg', 'image/png'].includes(rawFile.type);
  const isLt5M = rawFile.size / 1024 / 1024 < 5;

  if (!isJpgOrPng) {
    ElMessage.error('照片只支持 JPG/PNG 格式!');
    photoFileList.value = uploadFiles.filter(f => f.uid !== uploadFile.uid);
    return;
  }
  if (!isLt5M) {
    ElMessage.error('照片大小不能超过 5MB!');
    photoFileList.value = uploadFiles.filter(f => f.uid !== uploadFile.uid);
    return;
  }
  formData.photo = rawFile;
  formRef.value?.validateField('photo');
};

const handleRemove = () => formData.photo = null;
const handleExceed = () => ElMessage.warning('只能上传一张员工照片');

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true;
      try {
        const submitData = new FormData();
        for (const [key, value] of Object.entries(formData)) {
          if (value !== null) {
            submitData.append(key, value);
          }
        }
        
        const response = await Axios.post('/api/adm/add_employee', submitData);

        if (response.data && response.data.status) {
          ElMessage.success(response.data.msg || '新员工添加成功！');
          router.push('/admin/employee_management/information_list');
        } else {
          ElMessage.error(response.data.msg || '添加失败');
        }
      } catch (error) {
        const backendMessage = error.response?.data?.msg || '请检查网络或联系管理员';
        ElMessage.error(`添加失败: ${backendMessage}`);
      } finally {
        submitLoading.value = false;
      }
    } else {
      ElMessage.error('表单信息填写不完整，请检查红色提示项');
    }
  });
};

const resetForm = () => {
  formRef.value?.resetFields();
  photoFileList.value = [];
  formData.photo = null;
};
</script>

<template>
  <div class="page-container">
    <el-page-header :icon="Back" title="返回" @back="handleBack">
      <template #content><span class="page-title">添加新员工</span></template>
    </el-page-header>
    <el-divider />
    <div class="form-wrapper">
      <el-form 
        ref="formRef" 
        :model="formData" 
        :rules="rules" 
        label-width="100px" 
        style="max-width: 700px;"
      >
        <h3 class="form-section-title">基本信息</h3>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="员工编号" prop="employee_number">
              <el-input v-model="formData.employee_number" placeholder="例如: employee3" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="姓名" prop="name">
              <el-input v-model="formData.name" placeholder="请输入真实姓名" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="工号" prop="job_number">
              <el-input v-model="formData.job_number" placeholder="请输入员工工号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号码" prop="phone_number">
              <el-input v-model="formData.phone_number" placeholder="请输入11位手机号" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="身份证号" prop="id_number">
          <el-input v-model="formData.id_number" placeholder="请输入18位身份证号" />
        </el-form-item>
        <el-form-item label="住址" prop="address">
          <el-input v-model="formData.address" type="textarea" :rows="2" placeholder="请输入联系地址" />
        </el-form-item>
        
        <h3 class="form-section-title">账户与安全</h3>
        <el-form-item label="初始密码" prop="password">
          <el-input v-model="formData.password" type="password" show-password placeholder="为员工设置登录密码" />
        </el-form-item>

        <h3 class="form-section-title">员工照片</h3>
        <el-form-item label="上传照片" prop="photo">
          <el-upload
            v-model:file-list="photoFileList" action="#" list-type="picture-card"
            :limit="1" :auto-upload="false" :on-change="handleFileChange"
            :on-remove="handleRemove" @exceed="handleExceed">
            <el-icon><PlusIcon /></el-icon>
            <template #tip><div class="el-upload__tip">请上传JPG/PNG格式照片, 大小不超过5MB。</div></template>
          </el-upload>
        </el-form-item>
        
        <el-divider />
        <el-form-item>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">确认添加</el-button>
          <el-button @click="resetForm">重置所有</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
/* 使用你喜欢的、更美观的样式 */
.page-container {
  padding: 24px;
  background-color: #f9fafb;
  height: 100%;
  box-sizing: border-box;
}
.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
}
.form-wrapper {
  margin-top: 20px;
  background-color: #fff;
  padding: 30px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}
.form-section-title {
  font-size: 16px;
  font-weight: 500;
  color: #374151;
  margin: 0 0 24px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #f3f4f6;
}
.el-upload__tip {
  color: #9ca3af;
  font-size: 12px;
  margin-top: 8px;
  line-height: 1.5;
}
</style>