<template>
  <div class="login-container">
    <!-- 3D背景粒子效果 -->
    <div class="particles-background" ref="particlesContainer"></div>
    
    <!-- 左侧品牌区 -->
    <div class="brand-panel">
      <div class="brand-content">
        <div class="qr-code-wrapper">
          <canvas ref="qrCanvasRef"></canvas>
        </div>
        <h1 class="system-title" v-html="$t('login.title')"></h1>
        <p class="system-subtitle">{{ $t('login.subtitle') }}</p>
        
        <!-- 系统特性展示 -->
        <div class="system-features">
          <div class="feature-item">
            <el-icon><Lock /></el-icon>
            <span>{{ $t('login.featureSecurity') }}</span>
          </div>
          <div class="feature-item">
            <el-icon><Location /></el-icon>
            <span>{{ $t('login.featureDataMgmt') }}</span>
          </div>
          <div class="feature-item">
            <el-icon><TrendCharts /></el-icon>
            <span>{{ $t('login.featureTracing') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="form-panel-wrapper">
      <div class="login-card">
        <div class="card-header">
          <h2 class="form-title">{{ $t('login.formTitle') }}</h2>
          <p class="form-subtitle">{{ $t('login.formSubtitle') }}</p>
        </div>

        <el-form :model="data" :rules="rules" ref="elFormRef" class="login-form" @submit.prevent="login">
          <el-form-item prop="username">
            <el-input 
              size="large" 
              :prefix-icon="User" 
              v-model="data.username" 
              :placeholder="$t('login.usernamePlaceholder')"
              class="custom-input"
            />
          </el-form-item>
          
          <el-form-item prop="password">
            <el-input 
              size="large" 
              :prefix-icon="Lock" 
              show-password 
              v-model="data.password" 
              type="password" 
              :placeholder="$t('login.passwordPlaceholder')"
              @keyup.enter="login"
              class="custom-input"
            />
          </el-form-item>
          
          <el-form-item prop="role" class="role-selector-item">
            <div class="role-capsule-group">
              <div class="role-option" :class="{active: data.role === 'admin'}" @click="data.role = 'admin'">
                <el-icon><Platform /></el-icon><span>{{ $t('auth.admin') }}</span>
              </div>
              <div class="role-option" :class="{active: data.role === 'employee'}" @click="data.role = 'employee'">
                  <el-icon><UserFilled /></el-icon><span>{{ $t('auth.employee') }}</span>
              </div>
              <div class="active-capsule" :style="capsuleStyle"></div>
            </div>
          </el-form-item>
          
          <el-form-item>
            <el-button 
              class="login-button" 
              @click="login" 
              :loading="loading" 
              native-type="submit"
            >
              <el-icon class="login-icon"><Key /></el-icon>
              {{ $t('login.loginButton') }}
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="form-footer">
          <span>{{ $t('login.noAccount') }} </span>
          <el-link type="primary" @click="register" :underline="false" class="register-link">
            {{ $t('login.registerNow') }}
          </el-link>
        </div>
        
        <!-- 安全提示 -->
        <div class="security-notice">
          <el-icon><Warning /></el-icon>
          <span>{{ $t('login.securityNotice') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Lock, User, Platform, UserFilled, Key, Location, TrendCharts, Warning } from '@element-plus/icons-vue';
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useUserStore } from '@/stores/userStore';
import { login as loginApi } from '@/api/auth';
import QRCode from 'qrcode';
import * as THREE from 'three';

const { t } = useI18n();
const userStore = useUserStore();
const router = useRouter();
const elFormRef = ref(null);

const data = reactive({ username: '', password: '', role: 'employee' });
const loading = ref(false);

const rules = reactive({
  username: [{ required: true, message: () => t('login.usernameRequired'), trigger: 'blur' }],
  password: [{ required: true, message: () => t('login.passwordRequired'), trigger: 'blur' }],
  role: [{ required: true, message: () => t('login.roleRequired'), trigger: 'change' }]
});

// [核心修复] 登录函数，增加更详细的错误处理
const login = async () => {
  if (!elFormRef.value) return;
  try {
    const valid = await elFormRef.value.validate();
    if (!valid) {
      ElMessage.warning(t('login.fillComplete'));
      return;
    }
    loading.value = true;
    const payload = {
      username: (data.username || '').trim(),
      password: (data.password || '').trim(),
      role: data.role === 'admin' ? 'admin' : 'employee'
    };
    const response = await loginApi(payload);
    const responseData = response.data;

    if (responseData && responseData.access_token) {
      userStore.setUserInfo({
        user_number: responseData.user_number,
        role: responseData.role,
        token: responseData.access_token,
        refreshToken: responseData.refresh_token,
        permissions: responseData.permissions,
        user_name: responseData.user_name,
        admin_sub_role: responseData.admin_sub_role || null
      });
      ElMessage.success(t('login.loginSuccess'));
      if (responseData.role === 'admin') await router.push('/admin');
      else await router.push('/employee');
    } else {
      ElMessage.error(responseData.message || t('login.loginFailed'));
    }
  } catch (error) {
    console.error('登录请求失败:', error); // 在控制台打印完整的错误对象，便于调试
    let errorMessage = t('login.requestFailed');
    if (error.response) {
      errorMessage = error.response.data?.message || `${t('login.serverError')} ${error.response.status}`;
    } else if (error.request) {
      errorMessage = t('login.networkError');
    } else {
      errorMessage = t('login.unknownError');
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
const particlesContainer = ref(null);
let scene, camera, renderer, particles;
let animationId = null;

// 3D粒子背景效果
const initParticles = () => {
  if (!particlesContainer.value) return;

  // 创建场景
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });

  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x000000, 0);
  particlesContainer.value.appendChild(renderer.domElement);

  // 创建粒子几何体 - reduce particle count on mobile
  const particlesGeometry = new THREE.BufferGeometry();
  const isMobile = window.innerWidth <= 768;
  const particlesCount = isMobile ? 300 : 800;
  const posArray = new Float32Array(particlesCount * 3);

  for (let i = 0; i < particlesCount * 3; i++) {
    posArray[i] = (Math.random() - 0.5) * 100;
  }

  particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

  // 创建粒子材质
  const particlesMaterial = new THREE.PointsMaterial({
    size: 0.8,
    color: 0x4285f4,
    transparent: true,
    opacity: 0.6,
    sizeAttenuation: true
  });

  particles = new THREE.Points(particlesGeometry, particlesMaterial);
  scene.add(particles);

  camera.position.z = 30;

  // 动画循环
  const animate = () => {
    particles.rotation.x += 0.001;
    particles.rotation.y += 0.002;

    renderer.render(scene, camera);
    animationId = requestAnimationFrame(animate);
  };

  animate();
};

// 窗口大小调整
const handleResize = () => {
  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }
};

onMounted(() => {
  // 初始化QR码
  if (qrCanvasRef.value) {
    QRCode.toCanvas(qrCanvasRef.value, window.location.origin || 'http://localhost:5173', {
      width: 240, margin: 1,
      color: { dark: '#FFFFFF', light: '#00000000' }
    }, (error) => { if (error) console.error(error); });
  }
  
  // 初始化3D粒子背景
  initParticles();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (animationId) cancelAnimationFrame(animationId);
  if (particles) {
    particles.geometry?.dispose();
    particles.material?.dispose();
  }
  if (renderer) {
    renderer.dispose();
    if (particlesContainer.value && renderer.domElement.parentNode === particlesContainer.value) {
      particlesContainer.value.removeChild(renderer.domElement);
    }
  }
});
</script>

<style scoped>
.login-container {
  display: flex; 
  height: 100vh; 
  width: 100vw; 
  overflow: hidden;
  position: relative;
}

/* 3D粒子背景 */
.particles-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
  pointer-events: none;
}

/* 左侧品牌区 */
.brand-panel {
  width: 50%;
  background: var(--gradient-hero, linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #3b82f6 100%));
  display: flex; 
  align-items: center; 
  justify-content: center;
  padding: 40px;
  animation: slide-in-left 1s ease-out;
  position: relative;
  overflow: hidden;
}

/* 添加动态背景效果 */
.brand-panel::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
  animation: shimmer 3s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%) translateY(-100%) rotate(45deg); }
  100% { transform: translateX(100%) translateY(100%) rotate(45deg); }
}

.brand-content { 
  text-align: center; 
  color: #fff; 
  z-index: 1;
  position: relative;
}

.qr-code-wrapper {
  padding: 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px; /* 从28px改为20px，更协调 */
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  margin: 0 auto 24px; 
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 272px; /* 240 + 左右各16 的四边等距视觉 */
}

.qr-code-wrapper::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
  transition: left 0.5s;
}

.qr-code-wrapper:hover::before {
  left: 100%;
}

.qr-code-wrapper:hover {
  transform: translateY(-5px) scale(1.02);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.15);
}

canvas { 
  display: block; 
  border-radius: 12px; /* 从16px改为12px，与容器更协调 */
}

.system-title { 
  font-size: 36px; 
  font-weight: 700; 
  line-height: 1.4; 
  margin-bottom: 16px; 
  text-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

.system-subtitle { 
  font-size: 16px; 
  opacity: 0.9; 
  margin-bottom: 40px;
}

/* 系统特性展示 */
.system-features {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 40px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  backdrop-filter: blur(5px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateX(5px);
}

.feature-item .el-icon {
  font-size: 20px;
  color: #60a5fa;
}

.feature-item span {
  font-size: 14px;
  font-weight: 500;
}

/* 右侧表单区 */
.form-panel-wrapper {
  width: 50%; 
  display: flex; 
  align-items: center; 
  justify-content: center;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
  padding: 40px;
  animation: fade-in-right 1s ease-out 0.2s;
  animation-fill-mode: backwards;
  position: relative;
}

.login-card {
  width: 100%;
  max-width: 420px;
  background: var(--surface-glass, rgba(255, 255, 255, 0.85));
  border-radius: var(--radius-xl, 24px);
  padding: 48px;
  box-shadow: var(--shadow-xl, 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1));
  position: relative;
  overflow: hidden;
  transition: all var(--transition-base, 250ms cubic-bezier(0.4, 0, 0.2, 1));
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #3b82f6, #10b981, #f59e0b, #ef4444);
  animation: gradient-bar 3s ease infinite;
}

@keyframes gradient-bar {
  0%, 100% { transform: translateX(-100%); }
  50% { transform: translateX(100%); }
}

.login-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-xl, 0 20px 25px -5px rgba(0, 0, 0, 0.1)), var(--shadow-glow, 0 0 20px rgba(59, 130, 246, 0.3));
  background: var(--surface-glass-hover, rgba(255, 255, 255, 0.95));
}

.card-header {
  text-align: center;
  margin-bottom: 32px;
}

.form-title { 
  font-size: 28px; 
  font-weight: 700; 
  color: #1e293b; 
  text-align: center; 
  margin-bottom: 8px; 
}

.form-subtitle { 
  font-size: 15px; 
  color: #64748b; 
  text-align: center; 
  margin-bottom: 32px; 
}

/* 自定义输入框样式 */
.custom-input {
  --el-input-height: 56px;
}

:deep(.custom-input .el-input__wrapper) {
  height: 56px; 
  background: rgba(255, 255, 255, 0.8); 
  border-radius: 16px !important;
  border: 1px solid #e2e8f0 !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
  transition: all 0.3s ease;
}

:deep(.custom-input .el-input__wrapper:hover) {
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
  transform: translateY(-1px);
}

:deep(.custom-input .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1), 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
  border-color: #3b82f6 !important;
}

.role-selector-item { 
  margin: 28px 0 !important; 
}

.role-capsule-group {
  width: 100%; 
  height: 56px; 
  background: rgba(255, 255, 255, 0.6);
  border-radius: 16px; 
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.06);
  display: flex; 
  position: relative; 
  padding: 4px;
  border: 1px solid #e2e8f0;
}

.role-option {
  flex: 1; 
  display: flex; 
  align-items: center; 
  justify-content: center; 
  gap: 8px;
  z-index: 2; 
  cursor: pointer; 
  color: #64748b; 
  transition: all 0.4s ease;
  font-weight: 500;
  border-radius: 12px;
}

.role-option.active { 
  color: #fff; 
}

.role-option .el-icon {
  font-size: 18px;
}

.active-capsule {
  position: absolute; 
  top: 4px; 
  bottom: 4px; 
  left: 4px;
  width: calc(50% - 4px);
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  border-radius: 12px; 
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
  transition: transform 0.4s cubic-bezier(0.65, 0, 0.35, 1);
  z-index: 1;
}

.login-button {
  width: 100%; 
  height: 56px; 
  border-radius: 16px; 
  font-size: 16px; 
  font-weight: 600;
  color: #fff; 
  background: linear-gradient(135deg, #3b82f6, #2563eb); 
  border: none;
  box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3), 0 2px 4px -1px rgba(59, 130, 246, 0.2);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.login-button:hover { 
  background: linear-gradient(135deg, #2563eb, #1d4ed8); 
  transform: translateY(-2px); 
  box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4), 0 4px 6px -2px rgba(59, 130, 246, 0.2);
}

.login-button:active {
  transform: translateY(0);
}

.login-icon {
  font-size: 18px;
}

.form-footer { 
  margin-top: 24px; 
  text-align: center; 
  font-size: 14px; 
  color: #64748b;
}

.register-link {
  font-weight: 600;
  transition: all 0.3s ease;
}

.register-link:hover {
  transform: translateX(2px);
}

/* 安全提示 */
.security-notice {
  margin-top: 24px;
  padding: 12px 16px;
  background: rgba(245, 158, 11, 0.1);
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #92400e;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.security-notice .el-icon {
  font-size: 16px;
  color: #f59e0b;
}

/* 动画 */
@keyframes slide-in-left { 
  from { transform: translateX(-30px); opacity: 0; } 
  to { transform: translateX(0); opacity: 1; } 
}

@keyframes fade-in-right { 
  from { transform: translateX(30px); opacity: 0; } 
  to { transform: translateX(0); opacity: 1; } 
}

/* 响应式设计 */
@media (max-width: 992px) {
  .login-container { 
    flex-direction: column; 
  }
  
  .brand-panel, 
  .form-panel-wrapper { 
    width: 100%; 
    min-height: 50vh;
  }
  
  .brand-panel { 
    padding: 30px 20px; 
  }
  
  .form-panel-wrapper { 
    padding: 30px 20px; 
  }
  
  .system-title { 
    font-size: 28px; 
  }
  
  .system-features { 
    flex-direction: row; 
    flex-wrap: wrap; 
    justify-content: center; 
    gap: 12px; 
  }
  
  .feature-item { 
    flex: 1; 
    min-width: 120px; 
    padding: 10px 12px; 
  }
  
  .login-card { 
    padding: 32px 24px; 
  }
}

@media (max-width: 480px) {
  .login-card {
    padding: 24px 16px;
  }
  
  .form-title {
    font-size: 24px;
  }
  
  .system-title {
    font-size: 24px;
  }
}
</style>




