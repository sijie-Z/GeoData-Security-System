<template>
  <div class="register-container">
    <div ref="particlesContainer" class="particles-background"></div>
    
    <div class="register-content">
      <el-card class="register-card" shadow="hover">
        <template #header>
          <div class="card-header">
            <h1 class="register-title">创建账户</h1>
            <p class="register-subtitle">加入我们的空间数据平台</p>
          </div>
        </template>
        
        <el-form :model="data" :rules="rules" ref="elFormRef" label-position="top">
          <el-form-item label="头像" prop="avatar">
            <div class="avatar-upload-section">
              <div class="avatar-preview" @click="triggerFileInput">
                <img v-if="data.avatarUrl" :src="data.avatarUrl" alt="头像预览" class="avatar-image" />
                <div v-else class="avatar-placeholder">
                  <el-icon size="32" color="#909399"><User /></el-icon>
                  <span class="avatar-text">点击上传头像</span>
                </div>
                <div class="avatar-overlay">
                  <el-icon color="white" size="20"><Camera /></el-icon>
                  <span>更换头像</span>
                </div>
              </div>
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                style="display: none"
                @change="handleAvatarChange"
              />
              <div class="avatar-tips">
                <el-text type="info" size="small">
                  支持 JPG、PNG 格式，大小不超过 2MB
                </el-text>
              </div>
            </div>
          </el-form-item>

          <el-form-item label="姓名" prop="name">
            <el-input v-model="data.name" placeholder="请输入您的真实姓名" :prefix-icon="User" />
          </el-form-item>

          <el-form-item label="工号" prop="employeeId">
            <el-input v-model="data.employeeId" placeholder="请输入您的工号" :prefix-icon="Key" />
          </el-form-item>

          <el-form-item label="身份证号" prop="idNumber">
            <el-input v-model="data.idNumber" placeholder="请输入您的身份证号" :prefix-icon="CreditCard" />
          </el-form-item>

          <el-form-item label="联系电话" prop="phone">
            <el-input v-model="data.phone" placeholder="请输入您的手机号码" :prefix-icon="Phone" />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input show-password v-model="data.password" placeholder="请设置登录密码" :prefix-icon="Lock" />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input show-password v-model="data.confirmPassword" placeholder="请再次输入密码" :prefix-icon="Lock" />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" class="register-button" @click="register" :loading="loading" size="large">
              <el-icon><CircleCheck /></el-icon>
              创建账户
            </el-button>
          </el-form-item>

          <div class="login-link-container">
            <span class="login-text">已有账户？</span>
            <el-link type="primary" @click="login" :underline="false">立即登录</el-link>
          </div>
        </el-form>
      </el-card>
      
      <div class="features-section">
        <div class="feature-item"><el-icon color="#67C23A"><Check /></el-icon><span>安全可靠的数据保护</span></div>
        <div class="feature-item"><el-icon color="#67C23A"><Check /></el-icon><span>专业的空间数据服务</span></div>
        <div class="feature-item"><el-icon color="#67C23A"><Check /></el-icon><span>7×24小时技术支持</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, onUnmounted } from 'vue';
import * as THREE from 'three';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { post } from '@/utils/Axios';
import { User, Key, CreditCard, Phone, Lock, CircleCheck, Camera, Check } from '@element-plus/icons-vue';

const router = useRouter();
const elFormRef = ref();

const data = reactive({
  name: '',
  employeeId: '',
  idNumber: '',
  phone: '',
  password: '',
  confirmPassword: '',
  avatar: null,
  avatarUrl: ''
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
const fileInput = ref(null);

/**
 * 头像上传处理 - 小白说明：
 * 点击头像区域，打开系统的文件选择窗口，让你挑一张图片当头像。
 */
const triggerFileInput = () => {
  fileInput.value?.click();
};

/**
 * 处理头像文件变更 - 小白说明：
 * 检查图片的格式和大小，合格就用来显示预览，并保存到表单里。
 */
const handleAvatarChange = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // 验证文件类型
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png'];
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('请上传 JPG、JPEG 或 PNG 格式的图片');
    return;
  }

  // 验证文件大小
  const maxSize = 2 * 1024 * 1024; // 2MB
  if (file.size > maxSize) {
    ElMessage.error('头像大小不能超过 2MB');
    return;
  }

  // 读取文件并显示预览
  const reader = new FileReader();
  reader.onload = (e) => {
    data.avatarUrl = e.target.result;
    data.avatar = file;
    ElMessage.success('头像上传成功！');
  };
  reader.readAsDataURL(file);
};

/**
 * 提交注册信息 - 小白说明：
 * 先校验表单是否填完整，再把数据（含头像）打包发到后端。
 */
const register = async () => {
  try {
    const valid = await elFormRef.value.validate();
    if (!valid) return;

    loading.value = true;

    // 创建 FormData 对象，支持文件上传
    const formData = new FormData();
    formData.append('name', data.name);
    formData.append('employeeId', data.employeeId);
    formData.append('idNumber', data.idNumber);
    formData.append('phone', data.phone);
    formData.append('password', data.password);
    formData.append('confirmPassword', data.confirmPassword);
    
    // 如果有头像文件，添加到 FormData
    if (data.avatar) {
      formData.append('avatar', data.avatar);
    }

    const response = await post('/api/register', formData);
    
    ElMessage.success(response.message + "，请登录");
    router.push('/login');
  } catch (err) {
    console.error('注册请求失败:', err);
    ElMessage.error('注册失败：' + (err.response?.data?.message || '未知错误'));
  } finally {
    loading.value = false;
  }
};

const login = () => { router.push('/login'); };

/**
 * 3D粒子背景效果 - 小白说明：
 * 用 THREE.js 创建会缓慢旋转的小点点，让页面更有科技感。
 */
const particlesContainer = ref(null);
let scene, camera, renderer, particles;

/**
 * 初始化粒子场景 - 小白说明：
 * 搭建三要素：场景、相机、渲染器，然后生成一堆随机点。
 */
const initParticles = () => {
  if (!particlesContainer.value) return;
  
  // 创建场景
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x000000, 0);
  particlesContainer.value.appendChild(renderer.domElement);
  
  // 创建粒子几何体
  const particlesGeometry = new THREE.BufferGeometry();
  const particlesCount = 600;
  const posArray = new Float32Array(particlesCount * 3);
  
  for (let i = 0; i < particlesCount * 3; i++) {
    posArray[i] = (Math.random() - 0.5) * 80;
  }
  
  particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
  
  // 创建粒子材质
  const particlesMaterial = new THREE.PointsMaterial({
    size: 0.6,
    color: 0x10b981,
    transparent: true,
    opacity: 0.5,
    sizeAttenuation: true
  });
  
  particles = new THREE.Points(particlesGeometry, particlesMaterial);
  scene.add(particles);
  
  camera.position.z = 25;
  
  // 动画循环
  const animate = () => {
    requestAnimationFrame(animate);
    
    particles.rotation.x += 0.0008;
    particles.rotation.y += 0.0015;
    
    renderer.render(scene, camera);
  };
  
  animate();
};

/**
 * 窗口大小调整 - 小白说明：
 * 浏览器变宽变窄时，更新相机比例和画布尺寸，避免拉伸变形。
 */
const handleResize = () => {
  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }
};

/**
 * 组件挂载时执行 - 小白说明：
 * 页面加载完成后，启动粒子背景，并监听窗口大小变化。
 */
onMounted(() => {
  // 初始化3D粒子背景
  initParticles();
  window.addEventListener('resize', handleResize);
});

/**
 * 组件卸载时执行 - 小白说明：
 * 页面关闭或切换路由时，移除事件监听，并清理画布。
 */
onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (renderer && particlesContainer.value) {
    particlesContainer.value.removeChild(renderer.domElement);
  }
});
</script>

<style scoped>
.register-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background-color: #ffffff;
}

.register-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 500px;
  padding: 20px;
}

.register-card {
  border-radius: 16px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);
}

.card-header {
  text-align: center;
  padding: 20px 0;
}

.register-title {
  font-size: 28px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 8px 0;
}

.register-subtitle {
  font-size: 16px;
  color: #7f8c8d;
  margin: 0;
}

.avatar-upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.avatar-preview {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 2px dashed #dcdfe6;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.avatar-preview:hover {
  border-color: #409eff;
  transform: scale(1.05);
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #909399;
}

.avatar-text {
  font-size: 12px;
  margin-top: 4px;
}

.avatar-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.avatar-tips {
  text-align: center;
}

.register-button {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  background: linear-gradient(135deg, #4caf50, #45a049);
  border: none;
  transition: all 0.3s ease;
}

.register-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(76, 175, 80, 0.3);
}

.login-link-container {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: #606266;
}

.login-text {
  margin-right: 8px;
}

.features-section {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin-top: 30px;
  flex-wrap: wrap;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #67c23a;
}

.particles-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  pointer-events: none;
}

:deep(.el-input__wrapper) {
  border-radius: 8px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1) !important;
  border: 1px solid #e4e7ed !important;
  transition: all 0.3s ease;
}

:deep(.el-input__wrapper:hover) {
  border-color: #409eff !important;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2) !important;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #409eff !important;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2) !important;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #2c3e50;
}

@media (max-width: 768px) {
  .register-content {
    padding: 10px;
  }
  
  .features-section {
    flex-direction: column;
    align-items: center;
    gap: 15px;
  }
  
  .feature-item {
    justify-content: center;
  }
}
</style>