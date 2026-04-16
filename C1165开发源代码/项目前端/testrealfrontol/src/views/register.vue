<!-- <template>
  <div class="register">
    <div class="title">用户注册</div>

    <div class="form-container">
      <el-form :model="data" :rules="rules" ref="elFormRef">

        <el-form-item class="form-item" prop="name">
          <div class="label">姓名</div>
          <el-input v-model="data.name" class="custom-input" placeholder="请输入姓名" />
        </el-form-item>

        <el-form-item class="form-item" prop="employeeId">
          <div class="label">工号</div>
          <el-input v-model="data.employeeId" class="custom-input" placeholder="请输入工号" />
        </el-form-item>

        <el-form-item class="form-item" prop="idNumber">
          <div class="label">身份证号</div>
          <el-input v-model="data.idNumber" class="custom-input" placeholder="请输入身份证号" />
        </el-form-item>

        <el-form-item class="form-item" prop="phone">
          <div class="label">联系电话</div>
          <el-input v-model="data.phone" class="custom-input" placeholder="请输入联系电话" />
        </el-form-item>

        <el-form-item class="form-item" prop="password">
          <div class="label">密码</div>
          <el-input show-password v-model="data.password" class="custom-input" placeholder="请输入密码" />
        </el-form-item>

        <el-form-item class="form-item" prop="confirmPassword">
          <div class="label">确认密码</div>
          <el-input show-password v-model="data.confirmPassword" class="custom-input" placeholder="请再次输入密码" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" class="register-button" @click="register" :loading="loading">注册</el-button>
        </el-form-item>

      </el-form>
    </div>

    <div class="login-container">
      <el-link @click="login" class="login-link">已有账户？登录</el-link>
    </div>

  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { post } from '@/utils/Axios';

const router = useRouter();
const elFormRef = ref();

const data = reactive({
  name: '',
  employeeId: '',
  idNumber: '',
  phone: '',
  password: '',
  confirmPassword: ''
});

const rules = {
  name: [{ required: true, message: '请填写姓名', trigger: 'blur' }],
  employeeId: [{ required: true, message: '请填写工号', trigger: 'blur' }],
  idNumber: [{ required: true, message: '请填写身份证号', trigger: 'blur' }],
  phone: [{ required: true, message: '请填写联系电话', trigger: 'blur' }],
  password: [{ required: true, message: '请填写密码', trigger: 'blur' }],
  confirmPassword: [{ required: true, message: '请再次输入密码', trigger: 'blur' }]
};

const loading = ref(false);

const register = async () => {
  try {
    const valid = await elFormRef.value.validate();
    if (!valid) return;

    loading.value = true;

    const response = await post('/api/register', data);
    ElMessage.success(response.message + "，请登录");
    router.push('/login');
  } catch (err) {
    console.error('注册请求失败:', err);
    ElMessage.error('注册失败：' + (err.response?.data?.message || '未知错误'));
  } finally {
    loading.value = false;
  }
};

const login = () => {
  router.push('/login');
};


</script>



<style scoped>
.register {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background-color: #ffffff;
}

.title {
  font-size: 24px;
  font-weight: lighter;
  color: #666;
  margin-bottom: 30px;
}

.form-container {
  width: 300px;
  padding: 20px;
  background-color: #f7f8fa;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
}



.form-item {
  display: flex;
  flex-direction: column;
  /* 使标签和输入框垂直对齐 */
  margin-bottom: 20px;
  /* 缩小输入框之间的间距 */
}

.label {
  font-size: 0.8rem;
  /* 与登录页一致 */
  font-weight: 500;
  /* 使用中等粗细 */
  color: #000000;
  /* 设置标签颜色 */
  white-space: nowrap;
  /* 防止标签换行 */
  margin-bottom: 1px;
  /* 增加标签和输入框之间的距离 */
}

.register-button {
  width: 100%;
  background-color: #4caf50;
  color: #ffffff;
  margin-top: 8px;
}

.login-container {
  width: 319px;
  /* 与表单容器宽度一致 */
  display: flex;
  justify-content: center;
  padding: 10px;
  background-color: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-top: 20px;
}


.login-link {
  font-size: 0.8rem;
  /* 与登录页一致 */
  color: #0a8aeb;
  cursor: pointer;
}
</style> -->

<!-- 
<template>
  <div class="register-page-vector">
    <!-- 1. 全新的、契合主题的浅色矢量网络背景 -->
     <!--
    <div class="vector-background"></div>
    
    <div class="content-wrapper">
      <main class="form-container">
-->
        <!-- 2. 将系统名称作为主标题，更具身份感 -->
   <!---
        <h1 class="title">矢量数据安全分发与追踪溯源系统</h1>
        <p class="subtitle">Vector Data Security Distribution and Tracking System</p>

        <el-form
          :model="data"
          :rules="rules"
          ref="elFormRef"
          class="register-form"
          @submit.prevent="register"
        >
-->
          <!-- 表单项已适配浅色背景 -->
           <!--
          <el-form-item prop="name">
            <el-input v-model="data.name" placeholder="姓名" size="large" :prefix-icon="User" />
          </el-form-item>

          <el-form-item prop="employeeId">
            <el-input v-model="data.employeeId" placeholder="工号" size="large" :prefix-icon="Postcard" />
          </el-form-item>

          <el-form-item prop="idNumber">
            <el-input v-model="data.idNumber" placeholder="身份证号" size="large" :prefix-icon="CreditCard" />
          </el-form-item>

          <el-form-item prop="phone">
            <el-input v-model="data.phone" placeholder="联系电话" size="large" :prefix-icon="Iphone" />
          </el-form-item>

          <el-form-item prop="password">
            <el-input v-model="data.password" type="password" show-password placeholder="设置密码" size="large" :prefix-icon="Lock" />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input v-model="data.confirmPassword" type="password" show-password placeholder="确认密码" size="large" :prefix-icon="Lock" />
          </el-form-item>
          
          <el-form-item>
            <el-button native-type="submit" type="primary" class="register-button" :loading="loading" size="large">
              创建账户
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-prompt">
          <span>已有账户？ </span>
          <el-link type="primary" @click="login">立即登录</el-link>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
// Script部分与V7版本完全相同，这里省略以保持简洁。
// 您可以继续使用上一个版本中无误的<script>部分。
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Postcard, CreditCard, Iphone, Lock } from '@element-plus/icons-vue';
import { post } from '@/utils/Axios';

const router = useRouter();
const elFormRef = ref();
const data = reactive({ name: '', employeeId: '', idNumber: '', phone: '', password: '', confirmPassword: '' });
const validatePass = (rule, value, callback) => {
  if (value === '') { callback(new Error('请再次输入密码')); }
  else if (value !== data.password) { callback(new Error("两次输入的密码不一致!")); }
  else { callback(); }
};
const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  employeeId: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  idNumber: [{ required: true, message: '请输入身份证号', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入联系电话', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [{ validator: validatePass, trigger: 'blur', required: true }],
};
const loading = ref(false);
const register = async () => {
  if (!elFormRef.value) return;
  await elFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        const response = await post('/api/register', data);
        ElMessage.success(response.message + "，请登录");
        router.push('/login');
      } catch (err) {
        console.error('注册请求失败:', err);
        ElMessage.error('注册失败：' + (err.response?.data?.message || '未知错误'));
      } finally {
        loading.value = false;
      }
    }
  });
};
const login = () => { router.push('/login'); };
</script>

<style scoped>
.register-page-vector {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: grid;
  place-items: center;
  position: relative;
  background-color: #ffffff; /* 纯白底色 */
}

/* --- 全新矢量网络背景 --- */
.vector-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  /* 关键：在这里替换为您找到的背景图片 */
  background-image: url('https://www.transparenttextures.com/patterns/connected.png'), 
                    linear-gradient(to bottom, #eef2f5, #ffffff); /* 叠加一个从上到下的浅灰色渐变，增加深度 */
  background-repeat: repeat;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
  padding: 20px;
  box-sizing: border-box;
  display: grid;
  place-items: center;
}

.form-container {
  width: 100%;
  max-width: 420px;
  text-align: center;
}

.title {
  font-size: 28px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 16px;
  color: #7f8c8d;
  margin-bottom: 40px;
  font-family: 'Arial', sans-serif;
}

/* --- 表单样式，适配浅色背景 --- */
.register-form .el-form-item {
  margin-bottom: 22px;
}

:deep(.el-input__wrapper) {
  background-color: #fdfdfd !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
  border: 1px solid #e0e6ed;
  border-radius: 8px !important;
  transition: all 0.3s;
}
:deep(.el-input__wrapper:hover) {
  border-color: #c0c4cc;
}
:deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.2) !important;
}

.register-button {
  width: 100%;
  border-radius: 8px;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  border: none;
}

.login-prompt {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: #606266;
}
</style> -->




<!-- <template>
  <div class="register-page-vector">
    <div class="vector-background"></div>
    
    <div class="content-wrapper">
      <main class="form-container">
        <h1 class="title">矢量数据安全分发与追踪溯源系统</h1>
        <p class="subtitle">Vector Data Security Distribution and Tracking System</p>

        <el-form
          :model="data"
          :rules="rules"
          ref="elFormRef"
          class="register-form"
          @submit.prevent="register"
        >
          <el-form-item prop="name">
            <el-input v-model="data.name" placeholder="姓名" size="large" :prefix-icon="User" />
          </el-form-item>

          <el-form-item prop="employeeId">
            <el-input v-model="data.employeeId" placeholder="工号" size="large" :prefix-icon="Postcard" />
          </el-form-item>

          <el-form-item prop="idNumber">
            <el-input v-model="data.idNumber" placeholder="身份证号" size="large" :prefix-icon="CreditCard" />
          </el-form-item>

          <el-form-item prop="phone">
            <el-input v-model="data.phone" placeholder="联系电话" size="large" :prefix-icon="Iphone" />
          </el-form-item>

          <el-form-item prop="password">
            <el-input v-model="data.password" type="password" show-password placeholder="设置密码" size="large" :prefix-icon="Lock" />
          </el-form-item>

          <el-form-item prop="confirmPassword">
            <el-input v-model="data.confirmPassword" type="password" show-password placeholder="确认密码" size="large" :prefix-icon="Lock" />
          </el-form-item>
          
          <el-form-item>
            <el-button native-type="submit" type="primary" class="register-button" :loading="loading" size="large">
              创建账户
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login-prompt">
          <span>已有账户？ </span>
          <el-link type="primary" @click="login">立即登录</el-link>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Postcard, CreditCard, Iphone, Lock } from '@element-plus/icons-vue';
// 1. 【修改】导入标准的 axios，和 login.vue 保持一致
import axios from 'axios';

const router = useRouter();
const elFormRef = ref();

// 2. 【新增】定义后端 API 的基础 URL，和 login.vue 保持一致
const basic_url = import.meta.env.VITE_API_URL;

const data = reactive({
  name: '',
  employeeId: '', 
  idNumber: '',
  phone: '',
  password: '',
  confirmPassword: ''
});

// 确认密码的校验规则 (这个是正确的，无需修改)
const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'));
  } else if (value !== data.password) {
    callback(new Error("两次输入的密码不一致!"));
  } else {
    callback();
  }
};

const rules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  employeeId: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  idNumber: [{ required: true, message: '请输入身份证号', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入联系电话', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [{ validator: validatePass, trigger: 'blur', required: true }],
};

const loading = ref(false);

// 3. 【修改】改造 register 函数，使其使用标准的 axios
const register = async () => {
  if (!elFormRef.value) return;
  await elFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        // 构造要发送到后端的数据
        // 注意：我们不应该把 confirmPassword 发送到后端
        const payload = {
          name: data.name,
          employeeId: data.employeeId,
          idNumber: data.idNumber,
          phone: data.phone,
          password: data.password
        };
        
        // 使用 axios.post，并拼接完整的 URL
        const response = await axios.post(`${basic_url}/api/register`, payload);
        
        // 假设后端成功后会返回一个带有 message 的对象
        ElMessage.success(response.data.message || "注册成功，请登录");
        router.push('/login');
      } catch (err) {
        console.error('注册请求失败:', err);
        // 错误处理也和 login.vue 保持一致
        ElMessage.error('注册失败：' + (err.response?.data?.message || err.message || '未知错误'));
      } finally {
        loading.value = false;
      }
    }
  });
};

const login = () => { router.push('/login'); };
</script>

<style scoped>
.register-page-vector {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  display: grid;
  place-items: center;
  position: relative;
  background-color: #ffffff; /* 纯白底色 */
}

/* --- 全新矢量网络背景 --- */
.vector-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  /* 关键：在这里替换为您找到的背景图片 */
  background-image: url('https://www.transparenttextures.com/patterns/connected.png'), 
                    linear-gradient(to bottom, #eef2f5, #ffffff); /* 叠加一个从上到下的浅灰色渐变，增加深度 */
  background-repeat: repeat;
}

.content-wrapper {
  position: relative;
  z-index: 1;
  width: 100%;
  padding: 20px;
  box-sizing: border-box;
  display: grid;
  place-items: center;
}

.form-container {
  width: 100%;
  max-width: 420px;
  text-align: center;
}

.title {
  font-size: 28px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 16px;
  color: #7f8c8d;
  margin-bottom: 40px;
  font-family: 'Arial', sans-serif;
}

/* --- 表单样式，适配浅色背景 --- */
.register-form .el-form-item {
  margin-bottom: 22px;
}

:deep(.el-input__wrapper) {
  background-color: #fdfdfd !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
  border: 1px solid #e0e6ed;
  border-radius: 8px !important;
  transition: all 0.3s;
}
:deep(.el-input__wrapper:hover) {
  border-color: #c0c4cc;
}
:deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.2) !important;
}

.register-button {
  width: 100%;
  border-radius: 8px;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  border: none;
}

.login-prompt {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: #606266;
}
</style> -->



<template>
  <div class="register-container">
    <!-- 左翼：品牌视觉区 -->
    <div class="brand-panel">
      <div class="brand-content">
        <div class="shield-icon">
          <!-- 这是一个代表安全的SVG图标，您可以替换成自己的Logo -->
          <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
             <path d="M 50,5 L 95,25 L 95,75 L 50,95 L 5,75 L 5,25 Z" stroke="currentColor" stroke-width="3" fill="none" />
             <path d="M 50,20 L 80,35 L 80,65 L 50,80 L 20,65 L 20,35 Z" stroke="currentColor" stroke-width="2" fill="none" opacity="0.6"/>
             <polyline points="35,45 45,55 65,35" stroke="currentColor" stroke-width="4" fill="none" stroke-linecap="round"/>
          </svg>
        </div>
        <h1 class="brand-title">矢量地理数据安全分发与定责溯源系统</h1>
        <p class="brand-subtitle">构建数字身份的基石，守护每一份地理空间信息的价值。</p>
      </div>
       <div class="background-gradient"></div>
    </div>

    <!-- 右翼：表单功能区 -->
    <div class="form-panel">
      <div class="form-wrapper">
        <div class="form-header">
          <h2 class="form-title">创建您的安全账户</h2>
        </div>

        <el-form :model="data" :rules="rules" ref="elFormRef" class="register-form" @submit.prevent="register">
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item prop="name" label="真实姓名">
                <el-input v-model="data.name" placeholder="请输入" size="large" :prefix-icon="User" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="employeeId" label="员工工号">
                <el-input v-model="data.employeeId" placeholder="请输入" size="large" :prefix-icon="Postcard" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item prop="idNumber" label="身份证号">
                <el-input v-model="data.idNumber" placeholder="18位身份证号" size="large" :prefix-icon="CreditCard" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="phone" label="手机号码">
                <el-input v-model="data.phone" placeholder="11位手机号" size="large" :prefix-icon="Iphone" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="24">
            <el-col :span="12">
              <el-form-item prop="password" label="设置密码">
                <el-input v-model="data.password" type="password" show-password placeholder="设置登录密码" size="large" :prefix-icon="Lock" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item prop="confirmPassword" label="确认密码">
                <el-input v-model="data.confirmPassword" type="password" show-password placeholder="请再次输入密码" size="large" :prefix-icon="Lock" />
              </el-form-item>
            </el-col>
          </el-row>
          
          <el-form-item class="register-button-item">
            <el-button native-type="submit" type="primary" class="register-button" :loading="loading" size="large">
              立即创建账户
            </el-button>
          </el-form-item>
        </el-form>

        <div class="form-footer">
          <span>已有账户？ </span><el-link type="primary" :underline="false" @click="login">直接登录</el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { User, Postcard, CreditCard, Iphone, Lock } from '@element-plus/icons-vue';
import axios from 'axios';

const router = useRouter();
const elFormRef = ref();
const basic_url = import.meta.env.VITE_API_URL;

const data = reactive({
  name: '',
  employeeId: '', 
  idNumber: '',
  phone: '',
  password: '',
  confirmPassword: '',
});

const validatePass = (rule, value, callback) => {
  if (value === '') {
    callback(new Error('请再次输入密码'));
  } else if (value !== data.password) {
    callback(new Error("两次输入的密码不一致"));
  } else {
    callback();
  }
};

const rules = reactive({
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  employeeId: [{ required: true, message: '请输入工号', trigger: 'blur' }],
  idNumber: [
      { required: true, message: '请输入身份证号', trigger: 'blur' },
      { pattern: /^\d{17}(\d|X)$/i, message: '身份证号格式不正确', trigger: 'blur' }
  ],
  phone: [
      { required: true, message: '请输入联系电话', trigger: 'blur' },
      { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  password: [
      { required: true, message: '请输入密码', trigger: 'blur' },
      { min: 8, message: '密码长度不能少于8位', trigger: 'blur' }
  ],
  confirmPassword: [{ validator: validatePass, trigger: 'blur', required: true }],
});

const loading = ref(false);

const register = async () => {
  if (!elFormRef.value) return;
  await elFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        const payload = {
          name: data.name,
          employeeId: data.employeeId,
          idNumber: data.idNumber,
          phone: data.phone,
          password: data.password
        };
        const response = await axios.post(`${basic_url}/api/register`, payload);
        ElMessage.success(response.data.message || "注册成功，即将跳转到登录页");
        setTimeout(() => router.push('/login'), 1500);
      } catch (err) {
        ElMessage.error('注册失败：' + (err.response?.data?.message || err.message || '未知错误'));
      } finally {
        loading.value = false;
      }
    }
  });
};

const login = () => { router.push('/login'); };
</script>

<style scoped>
.register-container {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background-color: #f7f9fc;
}

/* 左翼：品牌视觉区 */
.brand-panel {
  width: 45%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  overflow: hidden;
  animation: slide-in-left 1.2s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.background-gradient {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(135deg, #4b89ff 0%, #0052d4 100%);
  z-index: 1;
}
.brand-content {
  position: relative; z-index: 2; text-align: center; color: #ffffff;
}
.shield-icon {
  width: 100px; height: 100px; margin: 0 auto 32px;
  color: #fff; animation: breathing-icon 4s infinite ease-in-out;
}
@keyframes breathing-icon {
  50% { transform: scale(1.1); filter: drop-shadow(0 0 15px rgba(255,255,255,0.5)); }
}
.brand-title {
  font-size: 36px; font-weight: 600; margin-bottom: 16px; line-height: 1.3;
}
.brand-subtitle {
  font-size: 16px; max-width: 350px; margin: 0 auto;
  opacity: 0.8; line-height: 1.6;
}

/* 右翼：表单功能区 */
.form-panel {
  width: 55%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  background-color: #f7f9fc;
  animation: fade-in 1.5s ease-out 0.5s;
  animation-fill-mode: backwards;
}
.form-wrapper {
  width: 100%;
  max-width: 600px;
}
.form-header {
  margin-bottom: 40px; /* 增加头部下边距 */
  text-align: center;
}
.form-title {
  font-size: 32px;
  font-weight: 700;
  color: #1f2d3d;
}

/* 表单与输入框 */
:deep(.el-form-item) {
  margin-bottom: 24px;
}
:deep(.el-form-item__label) {
  color: #5a6978;
  margin-bottom: 8px !important;
  font-size: 14px;
  font-weight: 500;
}
:deep(.el-input__wrapper) {
  height: 52px;
  border-radius: 10px !important;
  background-color: #fff !important;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05) !important;
  border: 1px solid #e5e7eb !important;
  transition: all 0.2s ease-in-out;
}
:deep(.el-input__wrapper:hover) {
  border-color: #3370ff !important;
}
:deep(.el-input__wrapper.is-focus) {
  border-color: #3370ff !important;
  box-shadow: 0 0 0 3px rgba(51, 112, 255, 0.2) !important;
}

/* 注册按钮 */
.register-button-item {
  margin-top: 32px;
}
.register-button {
  width: 100%;
  height: 52px;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  background: #3370ff;
  border: none;
  transition: all 0.2s ease-in-out;
}
.register-button:hover {
  background: #2563eb;
  transform: translateY(-2px);
  box-shadow: 0 7px 14px rgba(51, 112, 255, 0.2), 0 3px 6px rgba(0, 0, 0, 0.08);
}

/* 表单页脚 */
.form-footer {
  margin-top: 32px;
  text-align: center;
  font-size: 14px;
  color: #5a6978;
}
.form-footer .el-link {
  font-weight: 500;
  vertical-align: baseline;
}

/* 动画效果 */
@keyframes slide-in-left {
  from { transform: translateX(-50px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>