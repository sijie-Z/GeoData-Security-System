<template>
  <div class="home-container">
    <canvas ref="bgCanvas" class="background-canvas"></canvas>
    <!-- 主要内容区域 -->
    <div class="content-overlay">
      <!-- 品牌信息区域 -->
      <div class="brand-info">
        <h1 class="system-title">
          <span class="title-line">空间数据跟踪系统</span>
        </h1>
        <p class="system-subtitle">守护每一比特数据的安全、主权与价值</p>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button @click="register_button" class="action-btn register-btn">
          <el-icon><Plus /></el-icon>
          创建账户
        </button>
        <button @click="login_button" class="action-btn login-btn">
          <el-icon><Key /></el-icon>
          授权访问
        </button>
      </div>

      <!-- 特色功能展示 -->
      <div class="features-section">
        <div class="feature-item">
          <div class="feature-icon">
            <el-icon><Lock /></el-icon>
          </div>
          <h4>数据安全</h4>
          <p>水印追踪保护数据主权</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">
            <el-icon><Compass /></el-icon>
          </div>
          <h4>流程审批</h4>
          <p>规范的数据流转机制</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <h4>溯源追踪</h4>
          <p>完整的数据使用记录</p>
        </div>
      </div>
    </div>

    <!-- 底部信息 -->
    <div class="footer-info">
      <p>© 2024 空间数据跟踪系统 | 专业 · 安全 · 可信赖</p>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { ref, onMounted, onUnmounted } from 'vue';
import * as THREE from 'three';
import { Plus, Key, Lock, Compass, TrendCharts } from '@element-plus/icons-vue';

const router = useRouter();
const bgCanvas = ref(null);
let renderer, scene, camera, particles;

/**
 * 初始化3D背景
 */
const initBg = () => {
  if (!bgCanvas.value) return;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 35;
  renderer = new THREE.WebGLRenderer({ canvas: bgCanvas.value, alpha: true, antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // 背景粒子
  const geometry = new THREE.BufferGeometry();
  const count = 500;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count * 3; i++) positions[i] = (Math.random() - 0.5) * 90;
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({ size: 0.7, color: 0xffffff, transparent: true, opacity: 0.35 });
  particles = new THREE.Points(geometry, material);
  scene.add(particles);

  // 轨道环 - 简洁的科技感
  const rings = [];
  for (let i = 0; i < 3; i++) {
    const rGeo = new THREE.TorusGeometry(3 + i * 0.8, 0.03, 16, 200);
    const rMat = new THREE.MeshBasicMaterial({ color: 0x60a5fa, transparent: true, opacity: 0.4 });
    const ring = new THREE.Mesh(rGeo, rMat);
    ring.rotation.x = Math.PI / (i % 2 === 0 ? 2 : 2.5);
    ring.rotation.y = i * 0.3;
    ring.name = `ring_${i}`;
    rings.push(ring);
    scene.add(ring);
  }

  // 灯光
  const ambient = new THREE.AmbientLight(0x3b82f6, 0.5);
  scene.add(ambient);

  const animate = () => {
    particles.rotation.x += 0.0006;
    particles.rotation.y += 0.001;
    rings.forEach((r, idx) => {
      r.rotation.z += 0.002 + idx * 0.001;
      r.material.opacity = 0.3 + 0.15 * Math.sin(Date.now() * 0.001 + idx);
    });
    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  };
  animate();
};

const handleResize = () => {
  if (!renderer || !camera) return;
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
};

onMounted(() => {
  initBg();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (renderer) renderer.dispose();
});

const login_button = () => router.push('/login');
const register_button = () => router.push('/register');
</script>

<style scoped>
.home-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-image: radial-gradient(circle, #1e3a8a, #030712 60%);
  display: flex;
  justify-content: center;
  align-items: center;
  color: #e0f2fe;
}

.background-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  pointer-events: none;
}

.content-overlay {
  position: relative;
  z-index: 3;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
  padding: 40px 20px;
  max-width: 1200px;
  width: 100%;
}

.brand-info {
  animation: fadeIn 2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.system-title {
  font-size: clamp(2.3rem, 5.5vw, 3.6rem);
  font-weight: 800;
  line-height: 1.15;
  color: #fff;
  text-shadow: 0 0 15px rgba(147, 197, 253, 0.3), 0 0 40px rgba(96, 165, 250, 0.4);
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
}

.title-line {
  background: linear-gradient(180deg, #ffffff 0%, #bfdbfe 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.system-subtitle {
  font-size: clamp(1rem, 2.3vw, 1.3rem);
  color: #a7c1e5;
  margin-top: 20px;
  font-weight: 300;
  letter-spacing: 0.5px;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 24px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 20px;
}

.action-btn {
  padding: 16px 48px;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 50px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
  border: 1px solid rgba(96, 165, 250, 0.5);
  background: rgba(30, 64, 175, 0.3);
  color: #e0f2fe;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  overflow: hidden;
}

.action-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(120deg, transparent, rgba(191, 219, 254, 0.3), transparent);
  transition: all 0.6s;
}

.action-btn:hover::before {
  left: 100%;
}

.action-btn:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 35px rgba(96, 165, 250, 0.3);
  border-color: #93c5fd;
  color: #fff;
}

.login-btn {
  background: #3b82f6;
  border-color: #3b82f6;
  color: white;
}

.login-btn:hover {
  background: #60a5fa;
  border-color: #93c5fd;
  box-shadow: 0 12px 35px rgba(96, 165, 250, 0.3);
}

/* 特色功能 */
.features-section {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0;
  margin-top: 40px;
}

.feature-item {
  text-align: center;
  width: 32%;
  min-width: 200px;
  transition: transform 0.3s ease;
}

.feature-item:hover {
  transform: translateY(-5px);
}

.feature-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.2) 0%, rgba(103, 194, 58, 0.2) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  font-size: 32px;
  color: #93c5fd;
  border: 2px solid rgba(147, 197, 253, 0.3);
  transition: all 0.3s ease;
}

.feature-item:hover .feature-icon {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.3) 0%, rgba(103, 194, 58, 0.3) 100%);
  color: #fff;
  border-color: rgba(147, 197, 253, 0.5);
}

.feature-item h4 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 8px 0;
}

.feature-item p {
  font-size: 14px;
  color: #a7c1e5;
  margin: 0;
  line-height: 1.5;
}

/* 底部信息 */
.footer-info {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
}

.footer-info p {
  font-size: 12px;
  color: rgba(160, 180, 220, 0.8);
  margin: 0;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .content-overlay {
    padding: 20px 10px;
    gap: 30px;
  }

  .action-buttons {
    flex-direction: column;
    width: 100%;
    max-width: 300px;
  }

  .action-btn {
    width: 100%;
    justify-content: center;
  }

  .features-section {
    flex-direction: column;
    align-items: center;
  }

  .system-title {
    font-size: clamp(2rem, 5vw, 3rem);
  }
}
</style>
