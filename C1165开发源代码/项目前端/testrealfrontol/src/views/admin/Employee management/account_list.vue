<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Back } from '@element-plus/icons-vue'; // 引入图标
import Axios from '@/utils/Axios.js';

// --- 依赖与初始化 ---
const router = useRouter();
const formRef = ref(null);

// --- 响应式数据 ---
const accountForm = reactive({
  employee_number: null,
  username: '',
  password: '',
  confirmPassword: '',
  role: 'USER' // 默认选中一个，体验更佳
});

const employeeList = ref([]);
const loading = ref(false); // 用于控制提交按钮的加载状态

// --- 校验规则 (与之前版本相同，保持健壮性) ---
const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'));
  } else if (value !== accountForm.password) {
    callback(new Error('两次输入的密码不一致!'));
  } else {
    callback();
  }
};

const rules = reactive({
  employee_number: [{ required: true, message: '请选择关联的员工', trigger: 'change' }],
  username: [
    { required: true, message: '请输入账号名称', trigger: 'blur' },
    { min: 3, max: 15, message: '长度应在 3 到 15 个字符之间', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirmPassword: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
  role: [{ required: true, message: '请选择账号角色', trigger: 'change' }]
});


// --- 方法与逻辑 ---

// 返回上一页
const handleBack = () => {
  router.back();
};

// 获取员工列表
const fetchEmployees = async () => {
  try {
    const response = await Axios.get('/api/adm/get_emp_info_list');
    if (response.data && response.data.status) {
      employeeList.value = response.data.data.list;
    } else {
      ElMessage.error('获取员工列表失败');
    }
  } catch (error) {
    console.error("Failed to fetch employees:", error);
    ElMessage.error('网络错误，无法加载员工列表');
  }
};

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return;

  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true; // 开始提交，按钮显示加载中
      try {
        const payload = {
          employee_number: accountForm.employee_number,
          username: accountForm.username,
          password: accountForm.password,
          // TODO: 请与后端确认实际的角色值是 'ADMIN'/'USER' 还是其他
          role: accountForm.role,
        };
        // 假设创建账号的后端接口是 '/api/account/create'
        const response = await Axios.post('/api/account/create', payload);

        if (response.data && response.data.status) {
          ElMessage.success('账号创建成功！');
          formRef.value.resetFields();
        } else {
          ElMessage.error(response.data.msg || '创建失败，请检查输入');
        }
      } catch (error) {
        console.error("Failed to create account:", error);
        ElMessage.error('账号创建失败，服务器或网络错误');
      } finally {
        loading.value = false; // 无论成功失败，结束加载状态
      }
    } else {
      ElMessage.warning('表单校验未通过，请检查红色提示项');
      return false;
    }
  });
};

// 重置表单
const resetForm = () => {
  if (!formRef.value) return;
  formRef.value.resetFields();
};

// --- 生命周期钩子 ---
onMounted(fetchEmployees);
</script>

<template>
  <div class="page-container">
    <!-- 1. 使用 Page Header, 专业的页面标题和返回功能 -->
    <el-page-header :icon="Back" title="返回" @back="handleBack">
      <template #content>
        <span class="page-title">创建新员工账号</span>
      </template>
    </el-page-header>

    <!-- 2. 使用分隔线替代Card的阴影，视觉上更清爽 -->
    <el-divider />

    <!-- 3. 表单区域，占据合理的页面宽度 -->
    <div class="form-wrapper">
      <el-form
        ref="formRef"
        :model="accountForm"
        :rules="rules"
        label-width="100px"
        label-position="right"
        status-icon
        style="max-width: 600px"
      >
        <el-form-item label="关联员工" prop="employee_number">
          <el-select
            v-model="accountForm.employee_number"
            placeholder="请搜索或选择要绑定的员工"
            filterable
            style="width: 100%;"
          >
            <el-option
              v-for="employee in employeeList"
              :key="employee.employee_number"
              :label="`${employee.name} (${employee.employee_number})`"
              :value="employee.employee_number"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="账号名称" prop="username">
          <el-input v-model="accountForm.username" placeholder="请输入登录用户名" clearable />
        </el-form-item>

        <el-form-item label="设置密码" prop="password">
          <el-input v-model="accountForm.password" type="password" show-password placeholder="请输入至少6位密码" />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="accountForm.confirmPassword" type="password" show-password placeholder="请再次输入密码" />
        </el-form-item>

        <el-form-item label="账号角色" prop="role">
          <el-radio-group v-model="accountForm.role">
            <el-radio label="ADMIN">管理员</el-radio>
            <el-radio label="USER">普通用户</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="submitForm">立即创建</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.page-container {
  /* 使用内边距创造呼吸感，而不是外部空白 */
  padding: 24px;
  background-color: #fff;
  height: 100%;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.form-wrapper {
  margin-top: 20px;
}

/* 覆盖 Element Plus 默认样式，让 PageHeader 的标题更突出 */
:deep(.el-page-header__content) {
  align-items: center;
}
</style>