<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Back } from '@element-plus/icons-vue';
import Axios from '@/utils/Axios.js';

// --- 依赖与初始化 ---
const router = useRouter(); // 用于导航，如此处的返回功能
const formRef = ref(null); // 表单的引用，用于调用其方法

// --- 响应式数据 ---

// 表单的数据模型
const accountForm = reactive({
  employee_number: null, // 将与选中的员工绑定
  username: '',
  password: '',
  confirmPassword: '', // 仅用于前端校验，不会提交给后端
  role: 'USER' // 默认角色为普通用户，提供更好的用户体验
});

// 存储从后端获取的可选员工列表
const employeeList = ref([]);

// 控制提交按钮的加载状态，防止重复点击
const submitLoading = ref(false);

// --- 表单校验规则 ---

// 自定义校验：确认密码是否一致
const validateConfirmPassword = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入您的密码'));
  } else if (value !== accountForm.password) {
    callback(new Error('两次输入的密码不一致'));
  } else {
    callback(); // 校验通过
  }
};

// 完整的表单校验规则集
const rules = reactive({
  employee_number: [{ required: true, message: '必须选择一个关联的员工', trigger: 'change' }],
  username: [
    { required: true, message: '账号名称不能为空', trigger: 'blur' },
    { min: 3, max: 15, message: '长度应在 3 到 15 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '密码不能为空', trigger: 'blur' },
    { min: 6, message: '密码长度至少为 6 位', trigger: 'blur' }
  ],
  confirmPassword: [
    // 使用自定义校验器
    { required: true, validator: validateConfirmPassword, trigger: 'blur' }
  ],
  role: [{ required: true, message: '必须为账号指定一个角色', trigger: 'change' }]
});


// --- 方法与逻辑 ---

// 处理返回按钮点击事件
const handleBack = () => {
  router.back();
};

// 从后端获取员工列表，填充下拉框
const fetchEmployeesForSelection = async () => {
  try {
    // 假设此接口返回一个不分页的、包含所有员工基本信息的列表
    const response = await Axios.get('/api/adm/get_emp_info_list');
    if (response.data && response.data.status) {
      employeeList.value = response.data.data.list;
    } else {
      ElMessage.error(response.data.msg || '无法加载员工列表');
    }
  } catch (error) {
    console.error("Failed to fetch employees for selection:", error);
    ElMessage.error('网络错误，获取员工列表失败');
  }
};

// 提交表单的核心方法
const submitForm = async () => {
  if (!formRef.value) return;

  // 1. 对整个表单进行校验
  await formRef.value.validate(async (valid, fields) => {
    if (valid) {
      // 2. 校验通过，开始提交
      submitLoading.value = true;
      try {
        // 3. 构造要发送给后端的数据包 (Payload)
        // 注意：我们移除了前端专用的 `confirmPassword` 字段
        const payload = {
          employee_number: accountForm.employee_number,
          username: accountForm.username,
          password: accountForm.password,
          role: accountForm.role,
        };

        // ==========================================================
        // === 这里是与后端接口交互的地方 ===
        // TODO: 请与后端确认接口地址和请求方法是否正确
        const response = await Axios.post('/api/account/create', payload);
        // ==========================================================

        if (response.data && response.data.status) {
          ElMessage.success('新账号创建成功！');
          formRef.value.resetFields(); // 成功后清空表单，方便继续添加
        } else {
          // 后端返回的业务逻辑错误（如：用户名已存在）
          ElMessage.error(response.data.msg || '创建失败，请稍后重试');
        }
      } catch (error) {
        // 网络层或服务器500等错误
        console.error("Failed to create account:", error);
        ElMessage.error('账号创建请求失败，请检查网络或联系管理员');
      } finally {
        // 4. 无论成功或失败，都要结束加载状态
        submitLoading.value = false;
      }
    } else {
      // 校验不通过，提示用户检查
      console.log('Validation failed on fields:', fields);
      ElMessage.warning('表单信息不完整或格式不正确，请检查');
      return false;
    }
  });
};

// 重置表单到初始状态
const resetForm = () => {
  if (!formRef.value) return;
  formRef.value.resetFields();
};

// --- 生命周期钩子 ---
// 在组件挂载到页面后，立即获取员工列表数据
onMounted(() => {
  fetchEmployeesForSelection();
});
</script>

<template>
  <div class="page-container">
    <!-- 页面头部：提供上下文和导航 -->
    <el-page-header :icon="Back" title="返回" @back="handleBack">
      <template #content>
        <span class="page-title">添加新账号</span>
      </template>
    </el-page-header>

    <el-divider />

    <!-- 表单容器：提供一个合理的布局范围 -->
    <div class="form-wrapper">
      <el-form
        ref="formRef"
        :model="accountForm"
        :rules="rules"
        label-width="110px"
        label-position="right"
        status-icon
        style="max-width: 600px"
      >
        <el-form-item label="关联员工" prop="employee_number">
          <el-select
            v-model="accountForm.employee_number"
            placeholder="通过姓名或编号搜索员工"
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

        <el-form-item label="设置账号名称" prop="username">
          <el-input v-model="accountForm.username" placeholder="用于登录系统的唯一名称" clearable />
        </el-form-item>

        <el-form-item label="设置密码" prop="password">
          <el-input v-model="accountForm.password" type="password" show-password placeholder="至少6位，区分大小写" />
        </el-form-item>

        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="accountForm.confirmPassword" type="password" show-password placeholder="请再次输入以确认" />
        </el-form-item>

        <el-form-item label="指定角色" prop="role">
          <el-radio-group v-model="accountForm.role">
            <!-- TODO: 请与后端确认角色值 (label) 是否为 'ADMIN' 和 'USER' -->
            <el-radio label="ADMIN">管理员</el-radio>
            <el-radio label="USER">普通用户</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitLoading" @click="submitForm">
            确认创建
          </el-button>
          <el-button @click="resetForm">清空重填</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.page-container {
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
  /* 如果希望表单在页面中居中，可以取消下面的注释 */
  /* display: flex; */
  /* justify-content: center; */
}
</style>