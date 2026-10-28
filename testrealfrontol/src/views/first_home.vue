<template>
  <div class="home-container">
    <canvas
      ref="bgCanvas"
      class="background-canvas"
    />
    <!-- 主要内容区域 -->
    <div class="content-overlay">
      <!-- 品牌信息区域 -->
      <div class="brand-info">
        <h1 class="system-title">
          <span class="title-line">{{ $t('firstHome.title') }}</span>
        </h1>
        <p class="system-subtitle">
          {{ $t('firstHome.subtitle') }}
        </p>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button
          class="action-btn register-btn"
          @click="register_button"
        >
          <el-icon><Plus /></el-icon>
          {{ $t('firstHome.createAccount') }}
        </button>
        <button
          class="action-btn login-btn"
          @click="login_button"
        >
          <el-icon><Key /></el-icon>
          {{ $t('firstHome.accessLogin') }}
        </button>
      </div>

      <!-- 特色功能展示 -->
      <div class="features-section">
        <div class="feature-item">
          <div class="feature-icon">
            <el-icon><Lock /></el-icon>
          </div>
          <h2>{{ $t('firstHome.featureSecurity') }}</h2>
          <p>{{ $t('firstHome.featureSecurityDesc') }}</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">
            <el-icon><Compass /></el-icon>
          </div>
          <h2>{{ $t('firstHome.featureApproval') }}</h2>
          <p>{{ $t('firstHome.featureApprovalDesc') }}</p>
        </div>
        <div class="feature-item">
          <div class="feature-icon">
            <el-icon><TrendCharts /></el-icon>
          </div>
          <h2>{{ $t('firstHome.featureTracing') }}</h2>
          <p>{{ $t('firstHome.featureTracingDesc') }}</p>
        </div>
      </div>

      <!-- 工作流程引导 -->
      <div class="workflow-section">
        <h2 class="workflow-title">
          {{ $t('firstHome.workflowTitle') }}
        </h2>
        <div class="workflow-steps">
          <div
            v-for="(step, idx) in workflowSteps"
            :key="idx"
            class="workflow-step"
          >
            <div class="step-number">
              {{ idx + 1 }}
            </div>
            <div
              v-if="idx < workflowSteps.length - 1"
              class="step-connector"
            />
            <h3>{{ step.title }}</h3>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Language switcher in top-right corner -->
    <div class="lang-switcher">
      <LanguageSwitcher />
    </div>

    <!-- Scroll indicator -->
    <div class="scroll-indicator motion-rise">
      <div class="scroll-mouse">
        <div class="scroll-wheel motion-loop" />
      </div>
    </div>

    <!-- 底部信息 -->
    <div class="footer-info">
      <p>{{ $t('firstHome.copyright') }}</p>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { Plus, Key, Lock, Compass, TrendCharts } from '@element-plus/icons-vue';
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue';

const router = useRouter();
const { t } = useI18n();

const workflowSteps = computed(() => [
  { title: t('firstHome.wfStep1Title'), desc: t('firstHome.wfStep1Desc') },
  { title: t('firstHome.wfStep2Title'), desc: t('firstHome.wfStep2Desc') },
  { title: t('firstHome.wfStep3Title'), desc: t('firstHome.wfStep3Desc') },
  { title: t('firstHome.wfStep4Title'), desc: t('firstHome.wfStep4Desc') },
  { title: t('firstHome.wfStep5Title'), desc: t('firstHome.wfStep5Desc') },
]);
const bgCanvas = ref(null);
let renderer, scene, camera, particles;
let rings = [];
let animationId = null;
let disposed = false;
let bgInitToken = 0;

/**
 * 释放 3D 背景占用的 GPU/CPU 资源（幂等，可在加载中途调用）
 */
const disposeBg = () => {
  if (animationId) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }
  if (scene) {
    scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
        materials.forEach((m) => m.dispose());
      }
    });
  }
  if (renderer) {
    renderer.dispose();
    renderer = null;
  }
  scene = null;
  camera = null;
  particles = null;
  rings = [];
};

/**
 * 初始化3D背景（three 动态加载：装饰性背景不阻塞首屏，加载失败/慢网时页面照常可用）
 */
const initBg = async () => {
  if (!bgCanvas.value || disposed) return;
  const token = ++bgInitToken;
  let THREE;
  try {
    THREE = await import('three');
  } catch (err) {
    // 纯装饰背景：chunk 拉取失败时静默降级为纯 CSS 渐变，不打扰用户
    console.warn('three background failed to load, skipping decorative canvas', err);
    return;
  }
  if (disposed || token !== bgInitToken || !bgCanvas.value) return;

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 35;
  renderer = new THREE.WebGLRenderer({ canvas: bgCanvas.value, alpha: true, antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // 背景粒子 - reduce count on mobile
  const geometry = new THREE.BufferGeometry();
  const isMobile = window.innerWidth <= 768;
  const count = isMobile ? 200 : 500;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count * 3; i++) positions[i] = (Math.random() - 0.5) * 90;
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({ size: 0.7, color: 0xffffff, transparent: true, opacity: 0.35 });
  particles = new THREE.Points(geometry, material);
  scene.add(particles);

  // 轨道环 - 简洁的科技感
  rings = [];
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

  // 无障碍：prefers-reduced-motion 时仅渲染一帧静态画面，不启动动画循环（写法同 DataFlowGlobe.vue 先例）
  const prefersReducedMotion =
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false;
  if (prefersReducedMotion) {
    renderer.render(scene, camera);
    return;
  }

  const animate = () => {
    particles.rotation.x += 0.0006;
    particles.rotation.y += 0.001;
    rings.forEach((r, idx) => {
      r.rotation.z += 0.002 + idx * 0.001;
      r.material.opacity = 0.3 + 0.15 * Math.sin(Date.now() * 0.001 + idx);
    });
    renderer.render(scene, camera);
    animationId = requestAnimationFrame(animate);
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

onBeforeUnmount(() => {
  disposed = true;
  bgInitToken += 1; // 使尚未完成的动态 import 回调失效
  window.removeEventListener('resize', handleResize);
  disposeBg();
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
  font-weight: 700;
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
  font-weight: 400;
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
  gap: 24px;
  margin-top: 40px;
}

.feature-item {
  text-align: center;
  width: 32%;
  min-width: 200px;
  transition: all var(--transition-base, 250ms cubic-bezier(0.4, 0, 0.2, 1));
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
}

.feature-item:hover {
  transform: translateY(-8px);
  background: rgba(255, 255, 255, 0.05);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
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

.feature-item h2 {
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

/* Language switcher */
.lang-switcher {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10;
  border-radius: 999px;
  padding: 2px 6px;
  background: rgba(3, 7, 18, 0.5);
  border: 1px solid rgba(147, 197, 253, 0.35);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 6px 18px -6px rgba(0, 0, 0, 0.4);
}

/* 恒深色页面上给 EP 按钮固定浅字与玻璃 hover，两种主题同貌 */
.lang-switcher :deep(.el-button) {
  color: #e0f2fe;
}

.lang-switcher :deep(.el-button:hover) {
  background: rgba(96, 165, 250, 0.18);
}

/* Scroll indicator */
.scroll-indicator {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  animation: fadeInBounce 2s ease-out 1.5s both;
}

.scroll-mouse {
  width: 26px;
  height: 40px;
  border: 2px solid rgba(147, 197, 253, 0.6);
  border-radius: 13px;
  display: flex;
  justify-content: center;
  padding-top: 8px;
}

.scroll-wheel {
  width: 4px;
  height: 8px;
  background: rgba(147, 197, 253, 0.8);
  border-radius: 2px;
  animation: scrollPulse 1.5s ease-in-out infinite;
}

@keyframes scrollPulse {
  0% { opacity: 1; transform: translateY(0); }
  50% { opacity: 0.3; transform: translateY(6px); }
  100% { opacity: 1; transform: translateY(0); }
}

@keyframes fadeInBounce {
  from { opacity: 0; transform: translateX(-50%) translateY(10px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* 工作流程 */
.workflow-section {
  width: 100%;
  max-width: 900px;
  margin-top: 20px;
}

.workflow-title {
  font-size: clamp(1rem, 2vw, 1.2rem);
  color: #93c5fd;
  text-align: center;
  margin-bottom: 28px;
  font-weight: 400;
}

.workflow-steps {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  position: relative;
}

.workflow-step {
  flex: 1;
  text-align: center;
  position: relative;
  padding: 0 8px;
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
  position: relative;
  z-index: 2;
}

.step-connector {
  position: absolute;
  top: 20px;
  left: calc(50% + 24px);
  width: calc(100% - 48px);
  height: 2px;
  background: linear-gradient(90deg, #3b82f6, rgba(96, 165, 250, 0.3));
  z-index: 1;
}

.workflow-step h3 {
  font-size: 13px;
  color: #fff;
  margin: 0 0 4px;
  font-weight: 600;
}

.workflow-step p {
  font-size: 11px;
  color: #94a3b8;
  margin: 0;
  line-height: 1.4;
}

/* 响应式设计 */
@media (max-width: 768px) {
  /* 移动端：内容可纵向滚动，起点从顶部开始（修 CTA 贴顶裁切），页脚回到文档流（修步骤条与版权重叠） */
  .home-container {
    height: 100vh;
    overflow-x: hidden;
    overflow-y: auto;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center;
  }

  .content-overlay {
    padding: 64px 10px 24px;
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

  .workflow-steps {
    flex-direction: column;
    gap: 20px;
  }

  .step-connector {
    display: none;
  }

  .workflow-step {
    display: flex;
    align-items: center;
    gap: 16px;
    text-align: left;
  }

  .step-number {
    margin: 0;
    flex-shrink: 0;
  }

  .system-title {
    font-size: clamp(2rem, 5vw, 3rem);
  }

  .lang-switcher {
    top: 10px;
    right: 10px;
  }

  /* 页脚：脱离绝对定位，随文档流排在步骤条之后 */
  .footer-info {
    position: static;
    left: auto;
    transform: none;
    padding: 4px 12px 22px;
  }

  /* 滚动指示器在移动端无需提示滚动，且绝对定位会压住步骤条 */
  .scroll-indicator {
    display: none;
  }
}
</style>
