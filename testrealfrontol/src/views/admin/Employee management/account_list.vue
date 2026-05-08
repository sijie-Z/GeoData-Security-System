<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Back } from '@element-plus/icons-vue';
import { useI18n } from 'vue-i18n';
import { getEmployeeList, createAccount } from '@/api/admin';

// --- 依赖与初始化 ---
const { t } = useI18n();
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
    callback(new Error(t('employeeMgmt.enterConfirmPassword')));
  } else if (value !== accountForm.password) {
    callback(new Error(t('employeeMgmt.passwordMismatch')));
  } else {
    callback();
  }
};

const rules = reactive({
  employee_number: [{ required: true, message: () => t('employeeMgmt.selectEmployee'), trigger: 'change' }],
  username: [
    { required: true, message: () => t('employeeMgmt.enterAccountName'), trigger: 'blur' },
    { min: 3, max: 15, message: () => t('employeeMgmt.usernameLength'), trigger: 'blur' }
  ],
  password: [
    { required: true, message: () => t('employeeMgmt.enterPassword'), trigger: 'blur' },
    { min: 6, message: () => t('employeeMgmt.passwordMinLength'), trigger: 'blur' }
  ],
  confirmPassword: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }],
  role: [{ required: true, message: () => t('employeeMgmt.selectRole'), trigger: 'change' }]
});


// --- 方法与逻辑 ---

// 返回上一页
const handleBack = () => {
  router.back();
};

// 获取员工列表
const fetchEmployees = async () => {
  try {
    const response = await getEmployeeList();
    if (response.data && response.data.status) {
      employeeList.value = response.data.data.list;
    } else {
      ElMessage.error(t('employeeMgmt.fetchEmployeeListFailed'));
    }
  } catch (error) {
    console.error("Failed to fetch employees:", error);
    ElMessage.error(t('employeeMgmt.networkErrorLoadList'));
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
        const response = await createAccount(payload);

        if (response.data && response.data.status) {
          ElMessage.success(t('employeeMgmt.accountCreateSuccess'));
          formRef.value.resetFields();
        } else {
          ElMessage.error(response.data.msg || t('employeeMgmt.accountCreateFailed'));
        }
      } catch (error) {
        console.error("Failed to create account:", error);
        ElMessage.error(t('employeeMgmt.accountCreateError'));
      } finally {
        loading.value = false; // 无论成功失败，结束加载状态
      }
    } else {
      ElMessage.warning(t('employeeMgmt.formValidationFailed'));
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
    <el-page-header :icon="Back" :title="$t('employeeMgmt.back')" @back="handleBack">
      <template #content>
        <span class="page-title">{{ $t('employeeMgmt.createAccount') }}</span>
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
        <el-form-item :label="$t('employeeMgmt.linkedEmployee')" prop="employee_number">
          <el-select
            v-model="accountForm.employee_number"
            :placeholder="$t('employeeMgmt.linkedEmployeePlaceholder')"
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

        <el-form-item :label="$t('employeeMgmt.accountName')" prop="username">
          <el-input v-model="accountForm.username" :placeholder="$t('employeeMgmt.accountNamePlaceholder')" clearable />
        </el-form-item>

        <el-form-item :label="$t('employeeMgmt.setPassword')" prop="password">
          <el-input v-model="accountForm.password" type="password" show-password :placeholder="$t('employeeMgmt.passwordPlaceholderDefault')" />
        </el-form-item>

        <el-form-item :label="$t('employeeMgmt.confirmPassword')" prop="confirmPassword">
          <el-input v-model="accountForm.confirmPassword" type="password" show-password :placeholder="$t('employeeMgmt.confirmPasswordPlaceholder')" />
        </el-form-item>

        <el-form-item :label="$t('employeeMgmt.accountRole')" prop="role">
          <el-radio-group v-model="accountForm.role">
            <el-radio value="ADMIN">{{ $t('employeeMgmt.admin') }}</el-radio>
            <el-radio value="USER">{{ $t('employeeMgmt.normalUser') }}</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="loading" @click="submitForm">{{ $t('employeeMgmt.createNow') }}</el-button>
          <el-button @click="resetForm">{{ $t('employeeMgmt.reset') }}</el-button>
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