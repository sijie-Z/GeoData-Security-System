<!-- <template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-form-section">
        <div class="title">用户登录</div>
        <el-form :model="data" :rules="rules" ref="elFormRef">
          <el-form-item class="form-item-spacing" prop="username">
            <div class="label">用户名</div>
            <el-input :suffix-icon="User" v-model="data.username" class="input-field" placeholder="请输入用户名" />
          </el-form-item>

          <el-form-item class="form-item-spacing" prop="password">
            <div class="label">密码</div>
            <el-input :suffix-icon="Lock" show-password v-model="data.password" class="input-field" placeholder="请输入密码" />
          </el-form-item>

          <el-form-item class="form-item-spacing" prop="role">
            <div class="label">角色</div>
            <el-radio-group v-model="data.role" class="role-selection">
              <el-radio value="admin">管理员</el-radio>
              <el-radio value="employee">员工</el-radio>
            </el-radio-group>
          </el-form-item>

          <el-form-item class="form-item-spacing">
            <el-button type="primary" class="signin-button" @click="login" :loading="loading">登录</el-button>
          </el-form-item>
        </el-form>
        <div class="signup-link-container">
          <div class="horizontal-line"></div>
          <span>还没有账户？ </span><el-link @click="register" class="signup-link">注册</el-link>
          <div class="horizontal-line"></div>
        </div>
      </div>
      <div class="login-image-section">
        <img src="https://images.unsplash.com/photo-1528699076429-048680035db9?ixlib=rb-1.2.1&auto=format&fit=crop&w=1000&q=80" alt="Login Illustration" class="login-image" /> 
      </div>
    </div>
  </div>
</template>

<script setup>
import { Lock, User } from '@element-plus/icons-vue';
import { reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import axios from "axios";
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/userStore';

const basic_url = import.meta.env.VITE_API_URL;

const userStore = useUserStore();
const router = useRouter();
const elFormRef = ref();

const data = reactive({
  username: '',
  password: '',
  role: ''
});

const rules = {
  username: [
    { required: true, message: '请填写用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度限制[ 2 - 20 ]个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请填写密码', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
};

const loading = ref(false);

const login = async () => {
  try {
    const valid = await elFormRef.value.validate();
    if (!valid) return;

    loading.value = true;
    const response = await axios.post(`${basic_url}/api/login`, {
      username: data.username,
      password: data.password,
      role: data.role
    });

    const responseData = response.data;
    if (responseData.access_token) {
      const userData = {
        user_number: responseData.user_number,
        role: responseData.role,
        token: responseData.access_token,
        refreshToken: responseData.refresh_token,
        permissions: responseData.permissions,
        user_name: responseData.user_name
      };
      userStore.setUserInfo(userData);

      ElMessage.success('登录成功');
      if (responseData.role === 'admin') {
        await router.push('/admin');
      } else if (responseData.role === 'employee') {
        await router.push('/employee');
      }
    } else {
      ElMessage.error(responseData.message || '登录失败');
    }
  } catch (err) {
    console.error('Login request failed:', err);
    ElMessage.error('登录请求失败：' + (err.response?.data?.message || err.message));
  } finally {
    loading.value = false;
  }
};

const register = () => {
  router.push('/register');
};
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background-color: #f0f2f5;
  padding: 20px;
  overflow: hidden;
}

.login-card {
  display: flex;
  width: 720px;
  max-width: 90%;
  background-color: #ffffff;
  border-radius: 15px;
  box-shadow: 0 12px 35px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.login-form-section {
  flex: 1;
  padding: 30px 25px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-image-section {
  flex: 1;
  background-color: #eef1f4;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.login-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.title {
  font-size: 24px;
  font-weight: bold;
  color: #333;
  margin-bottom: 20px;
  text-align: left;
}

.label {
  font-size: 14px;
  color: #555;
  margin-bottom: 6px;
  display: block;
  text-align: left;
}

.input-field .el-input__wrapper {
  border-radius: 8px !important;
  border: 1px solid #ddd !important;
  box-shadow: none !important;
}

.input-field .el-input__inner {
  height: 42px;
  line-height: 42px;
}

.input-field .el-input__suffix .el-icon {
  color: #888;
}

.form-item-spacing {
  margin-bottom: 20px;
}

.role-selection {
  display: flex;
  justify-content: space-between;
  gap: 50px;
  margin-left: 10px;
}

.signin-button {
  width: 100%;
  background-color: #4A5568 !important;
  border-color: #4A5568 !important;
  color: #ffffff !important;
  padding: 12px 0;
  font-size: 20px; /* 字体增大1/3 */
  border-radius: 6px !important;
  height: auto;
}

.signin-button:hover {
  background-color: #2D3748 !important;
  border-color: #2D3748 !important;
}

.signup-link-container {
  margin-top: 25px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 14px;
  color: #555;
}

.signup-link,
.signup-link .el-link__inner {
  color: #4A5568 !important;
  font-weight: bold;
}

.horizontal-line {
  height: 1px;
  background-color: #ddd;
  flex: 1;
}
</style> -->




<!--空间数据版本-->

<!-- <template>
  <div class="login-container">

    <div class="brand-panel">
      <div class="brand-content">
        <div class="qr-code-wrapper">
          <canvas ref="qrCanvasRef"></canvas>
        </div>
        <h1 class="system-title">矢量数据安全分发<br/>与追踪溯源系统</h1>
        <p class="system-subtitle">每一次访问，都由可信的数字凭证守护</p>
      </div>
    </div>

    <div class="form-panel-wrapper">
      <div class="login-card">
        <h2 class="form-title">系统访问</h2>
        <p class="form-subtitle">请输入您的凭证以进行验证</p>

        <el-form :model="data" :rules="rules" ref="elFormRef" class="login-form" @submit.prevent="login">
          <el-form-item prop="username">
            <el-input size="large" :prefix-icon="User" v-model="data.username" placeholder="用户名 / 工号" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input size="large" :prefix-icon="Lock" show-password v-model="data.password" type="password" placeholder="密码" @keyup.enter="login"/>
          </el-form-item>
          
          <el-form-item prop="role" class="role-selector-item">
            <div class="role-capsule-group">
              <div class="role-option" :class="{active: data.role === 'admin'}" @click="data.role = 'admin'">
                <el-icon><Platform /></el-icon><span>管理员</span>
              </div>
              <div class="role-option" :class="{active: data.role === 'employee'}" @click="data.role = 'employee'">
                  <el-icon><UserFilled /></el-icon><span>员工</span>
              </div>
              <div class="active-capsule" :style="capsuleStyle"></div>
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button class="login-button" @click="login" :loading="loading" native-type="submit">
              授 权 登 录
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="form-footer">
          <span>还没有账户？ </span><el-link type="primary" @click="register" :underline="false">立即注册</el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Lock, User, Platform, UserFilled } from '@element-plus/icons-vue';
import { reactive, ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/userStore';
import axios from 'axios';
import QRCode from 'qrcode';

const basic_url = import.meta.env.VITE_API_URL;
const userStore = useUserStore();
const router = useRouter();
const elFormRef = ref(null);

const data = reactive({ username: '', password: '', role: 'employee' });
const loading = ref(false);

const rules = reactive({
  username: [{ required: true, message: '请输入用户名或工号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择您的角色', trigger: 'change' }]
});

// [核心修复] 登录函数，增加更详细的错误处理
const login = async () => {
  if (!elFormRef.value) return;
  try {
    const valid = await elFormRef.value.validate();
    if (!valid) {
      ElMessage.warning('请填写完整的登录信息');
      return;
    }
    loading.value = true;
    const response = await axios.post(`${basic_url}/api/login`, data);
    const responseData = response.data;

    if (responseData && responseData.access_token) {
      userStore.setUserInfo({
        user_number: responseData.user_number,
        role: responseData.role,
        token: responseData.access_token,
        refreshToken: responseData.refresh_token,
        permissions: responseData.permissions,
        user_name: responseData.user_name
      });
      ElMessage.success('登录验证通过！');
      if (responseData.role === 'admin') await router.push('/admin');
      else await router.push('/employee');
    } else {
      ElMessage.error(responseData.message || '登录失败，凭证无效');
    }
  } catch (error) {
    console.error('登录请求失败:', error); // 在控制台打印完整的错误对象，便于调试
    let errorMessage = '登录请求失败，请稍后重试';
    if (error.response) {
      // 服务器返回了错误状态码 (e.g., 401, 403, 500)
      errorMessage = error.response.data?.message || `服务器错误，状态码: ${error.response.status}`;
    } else if (error.request) {
      // 请求已发出但没有收到响应
      errorMessage = '无法连接到服务器，请检查网络或后端服务是否正在运行';
    } else {
      // 设置请求时发生了错误
      errorMessage = '发生未知错误，请检查控制台';
    }
    ElMessage.error(errorMessage);
  } finally {
    loading.value = false;
  }
};

const register = () => { router.push('/register'); };

// 胶囊滑块动画逻辑
const capsuleStyle = computed(() => ({
  transform: `translateX(${data.role === 'admin' ? '0%' : '100%'})`
}));

// QR码逻辑
const qrCanvasRef = ref(null);
onMounted(() => {
  if (qrCanvasRef.value) {
    QRCode.toCanvas(qrCanvasRef.value, 'https://github.com/your-project-url', {
      width: 240, margin: 1,
      color: { dark: '#FFFFFF', light: '#00000000' }
    }, (error) => { if (error) console.error(error); });
  }
});
</script>

<style scoped>
.login-container {
  display: flex; height: 100vh; width: 100vw; overflow: hidden;
}

/* 左侧品牌区 */
.brand-panel {
  width: 50%;
  background: linear-gradient(145deg, #4285f4, #3367d6);
  display: flex; align-items: center; justify-content: center;
  padding: 40px;
  animation: slide-in-left 1s ease-out;
}
.brand-content { text-align: center; color: #fff; }
.qr-code-wrapper {
  padding: 16px; background: rgba(255, 255, 255, 0.1);
  border-radius: 28px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  margin-bottom: 40px; backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
canvas { display: block; border-radius: 16px; }
.system-title { font-size: 34px; font-weight: 600; line-height: 1.4; margin-bottom: 12px; }
.system-subtitle { font-size: 15px; opacity: 0.8; }

/* 右侧表单区 */
.form-panel-wrapper {
  width: 50%; display: flex; align-items: center; justify-content: center;
  background-color: #f0f4f8; padding: 40px;
  animation: fade-in-right 1s ease-out 0.2s;
  animation-fill-mode: backwards;
}
.login-card {
  width: 100%; max-width: 400px;
  background: #fdfdff; border-radius: 24px; padding: 40px;
  box-shadow: 0 16px 40px -12px rgba(0, 80, 200, 0.15);
}
.form-title { font-size: 26px; font-weight: 600; color: #1f2d3d; text-align: center; margin-bottom: 8px; }
.form-subtitle { font-size: 14px; color: #64748b; text-align: center; margin-bottom: 32px; }

/* 粘土质感UI元素 */
:deep(.el-input__wrapper) {
  height: 52px; background-color: #f4f8fc !important; border-radius: 16px !important;
  border: 1px solid #eaf0f6 !important;
  box-shadow: inset 2px 2px 5px #dce6f0, inset -2px -2px 5px #ffffff !important;
}
:deep(.el-input__wrapper.is-focus) {
  box-shadow: inset 3px 3px 6px #dce6f0, inset -3px -3px 6px #ffffff !important;
}
.role-selector-item { margin: 28px 0 !important; }
.role-capsule-group {
  width: 100%; height: 50px; background: #eaf2fa;
  border-radius: 16px; box-shadow: inset 2px 2px 5px #c8d7e9, inset -2px -2px 5px #ffffff;
  display: flex; position: relative; padding: 4px;
}
.role-option {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  z-index: 2; cursor: pointer; color: #5a7a9e; transition: color 0.4s ease;
}
.role-option.active { color: #fff; }
.active-capsule {
  position: absolute; top: 4px; bottom: 4px; left: 4px;
  width: calc(50% - 4px);
  background: linear-gradient(135deg, #4a90e2, #007bff);
  border-radius: 12px; box-shadow: 0 3px 10px rgba(66, 133, 244, 0.4);
  transition: transform 0.4s cubic-bezier(0.65, 0, 0.35, 1);
  z-index: 1;
}
.login-button {
  width: 100%; height: 52px; border-radius: 16px; font-size: 16px; font-weight: 500;
  color: #fff; background: #4285f4; border: none;
  box-shadow: 0 5px 15px rgba(66, 133, 244, 0.3);
  transition: all 0.2s ease-in-out;
}
.login-button:hover { background: #3367d6; transform: translateY(-2px); }

.form-footer { margin-top: 24px; text-align: center; font-size: 14px; }

/* 动画 */
@keyframes slide-in-left { from { transform: translateX(-30px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
@keyframes fade-in-right { from { transform: translateX(30px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
</style> -->







<template>
  <div class="login-container">
    <!-- 左侧品牌视觉区 (完美复刻版) -->
    <div class="brand-panel">
      <div class="brand-content">
        <div class="qr-code-wrapper">
          <canvas ref="qrCanvasRef"></canvas>
        </div>
        <h1 class="system-title">矢量地理数据安全分发<br/>与定责溯源系统</h1>
        <p class="system-subtitle">每一次访问，都由可信的数字凭证守护</p>
      </div>
    </div>

    <!-- 右侧：粘土质感登录面板 -->
    <div class="form-panel-wrapper">
      <div class="login-card">
        <h2 class="form-title">系统访问</h2>
        <p class="form-subtitle">请输入您的凭证以进行验证</p>

        <el-form :model="data" :rules="rules" ref="elFormRef" class="login-form" @submit.prevent="login">
          <el-form-item prop="username">
            <el-input size="large" :prefix-icon="User" v-model="data.username" placeholder="用户名 / 工号" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input size="large" :prefix-icon="Lock" show-password v-model="data.password" type="password" placeholder="密码" @keyup.enter="login"/>
          </el-form-item>

          <el-form-item prop="role" class="role-selector-item">
            <div class="role-capsule-group">
              <div class="role-option" :class="{active: data.role === 'admin'}" @click="data.role = 'admin'">
                <el-icon><Platform /></el-icon><span>管理员</span>
              </div>
              <div class="role-option" :class="{active: data.role === 'employee'}" @click="data.role = 'employee'">
                <el-icon><UserFilled /></el-icon><span>员工</span>
              </div>
              <div class="active-capsule" :style="capsuleStyle"></div>
            </div>
          </el-form-item>

          <el-form-item>
            <el-button class="login-button" @click="login" :loading="loading" native-type="submit">
              授 权 登 录
            </el-button>
          </el-form-item>
        </el-form>

        <div class="form-footer">
          <span>还没有账户？ </span><el-link type="primary" @click="register" :underline="false">立即注册</el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Lock, User, Platform, UserFilled } from '@element-plus/icons-vue';
import { reactive, ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/userStore';
import axios from 'axios';
import QRCode from 'qrcode';

// 导入环境变量中的 API URL
const basic_url = import.meta.env.VITE_API_URL;

const userStore = useUserStore();
const router = useRouter();
const elFormRef = ref(null);

const data = reactive({ username: '', password: '', role: 'employee' });
const loading = ref(false);

const rules = reactive({
  username: [{ required: true, message: '请输入用户名或工号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  role: [{ required: true, message: '请选择您的角色', trigger: 'change' }]
});

// 核心修复: 登录函数，确保在路由跳转前更新用户状态
const login = async () => {
  if (!elFormRef.value) return;
  try {
    // 1. 表单校验
    const valid = await elFormRef.value.validate();
    if (!valid) {
      ElMessage.warning('请填写完整的登录信息');
      return;
    }
    
    loading.value = true;
    
    // 2. 发起登录请求
    const response = await axios.post(`${basic_url}/api/login`, data);
    const responseData = response.data;

    // 3. 检查后端返回的数据是否包含 token，这是登录成功的标志
    if (responseData && responseData.access_token) {
      
      // 关键步骤: 在路由跳转前，立即更新用户状态
      userStore.setUserInfo({
        user_number: responseData.user_number,
        role: responseData.role,
        token: responseData.access_token,
        refreshToken: responseData.refresh_token,
        permissions: responseData.permissions,
        user_name: responseData.user_name
      });
      userStore.isLoginSuccess = true; // 标记登录成功

      ElMessage.success('登录验证通过！');

      // 4. 根据角色进行路由跳转
      if (responseData.role === 'admin') {
        await router.push('/admin');
      } else {
        await router.push('/employee');
      }
    } else {
      // 登录失败
      ElMessage.error(responseData.message || '登录失败，凭证无效');
    }
  } catch (error) {
    console.error('登录请求失败:', error); // 在控制台打印完整的错误对象，便于调试
    let errorMessage = '登录请求失败，请稍后重试';
    if (error.response) {
      // 服务器返回了错误状态码 (e.g., 401, 403, 500)
      errorMessage = error.response.data?.message || `服务器错误，状态码: ${error.response.status}`;
    } else if (error.request) {
      // 请求已发出但没有收到响应
      errorMessage = '无法连接到服务器，请检查网络或后端服务是否正在运行';
    } else {
      // 设置请求时发生了错误
      errorMessage = '发生未知错误，请检查控制台';
    }
    ElMessage.error(errorMessage);
  } finally {
    loading.value = false;
  }
};

const register = () => { router.push('/register'); };

// 胶囊滑块动画逻辑
const capsuleStyle = computed(() => ({
  transform: `translateX(${data.role === 'admin' ? '0%' : '100%'})`
}));

// QR码逻辑
const qrCanvasRef = ref(null);
onMounted(() => {
  if (qrCanvasRef.value) {
    QRCode.toCanvas(qrCanvasRef.value, 'https://github.com/your-project-url', {
      width: 240, margin: 1,
      color: { dark: '#FFFFFF', light: '#00000000' }
    }, (error) => { if (error) console.error(error); });
  }
});
</script>

<style scoped>
.login-container {
  display: flex; height: 100vh; width: 100vw; overflow: hidden;
}

/* 左侧品牌区 */
.brand-panel {
  width: 50%;
  background: linear-gradient(145deg, #4285f4, #3367d6);
  display: flex; align-items: center; justify-content: center;
  padding: 40px;
  animation: slide-in-left 1s ease-out;
}
.brand-content { text-align: center; color: #fff; }
.qr-code-wrapper {
  padding: 16px; background: rgba(255, 255, 255, 0.1);
  border-radius: 28px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  margin-bottom: 40px; backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}
canvas { display: block; border-radius: 16px; }
.system-title { font-size: 34px; font-weight: 600; line-height: 1.4; margin-bottom: 12px; }
.system-subtitle { font-size: 15px; opacity: 0.8; }

/* 右侧表单区 */
.form-panel-wrapper {
  width: 50%; display: flex; align-items: center; justify-content: center;
  background-color: #f0f4f8; padding: 40px;
  animation: fade-in-right 1s ease-out 0.2s;
  animation-fill-mode: backwards;
}
.login-card {
  width: 100%; max-width: 400px;
  background: #fdfdff; border-radius: 24px; padding: 40px;
  box-shadow: 0 16px 40px -12px rgba(0, 80, 200, 0.15);
}
.form-title { font-size: 26px; font-weight: 600; color: #1f2d3d; text-align: center; margin-bottom: 8px; }
.form-subtitle { font-size: 14px; color: #64748b; text-align: center; margin-bottom: 32px; }

/* 粘土质感UI元素 */
:deep(.el-input__wrapper) {
  height: 52px; background-color: #f4f8fc !important; border-radius: 16px !important;
  border: 1px solid #eaf0f6 !important;
  box-shadow: inset 2px 2px 5px #dce6f0, inset -2px -2px 5px #ffffff !important;
}
:deep(.el-input__wrapper.is-focus) {
  box-shadow: inset 3px 3px 6px #dce6f0, inset -3px -3px 6px #ffffff !important;
}
.role-selector-item { margin: 28px 0 !important; }
.role-capsule-group {
  width: 100%; height: 50px; background: #eaf2fa;
  border-radius: 16px; box-shadow: inset 2px 2px 5px #c8d7e9, inset -2px -2px 5px #ffffff;
  display: flex; position: relative; padding: 4px;
}
.role-option {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px;
  z-index: 2; cursor: pointer; color: #5a7a9e; transition: color 0.4s ease;
}
.role-option.active { color: #fff; }
.active-capsule {
  position: absolute; top: 4px; bottom: 4px; left: 4px;
  width: calc(50% - 4px);
  background: linear-gradient(135deg, #4a90e2, #007bff);
  border-radius: 12px; box-shadow: 0 3px 10px rgba(66, 133, 244, 0.4);
  transition: transform 0.4s cubic-bezier(0.65, 0, 0.35, 1);
  z-index: 1;
}
.login-button {
  width: 100%; height: 52px; border-radius: 16px; font-size: 16px; font-weight: 500;
  color: #fff; background: #4285f4; border: none;
  box-shadow: 0 5px 15px rgba(66, 133, 244, 0.3);
  transition: all 0.2s ease-in-out;
}
.login-button:hover { background: #3367d6; transform: translateY(-2px); }

.form-footer { margin-top: 24px; text-align: center; font-size: 14px; }

/* 动画 */
@keyframes slide-in-left { from { transform: translateX(-30px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
@keyframes fade-in-right { from { transform: translateX(30px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

/* 响应式设计 */
@media (max-width: 992px) {
  .login-container { flex-direction: column; }
  .brand-panel, .form-panel-wrapper { width: 100%; }
  .brand-panel { padding: 20px; }
  .form-panel-wrapper { padding: 20px; }
}
</style>


