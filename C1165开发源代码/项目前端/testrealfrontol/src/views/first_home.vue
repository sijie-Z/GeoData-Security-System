<!-- <template>

  <div class="container">
     
      <img src="/src/assets/back.png" alt="背景" class="background-image" />

      
      <div class="text-content">
          <h1 class="main-title">矢量数据安全分发与追踪溯源系统</h1>
          <h2 class="sub-title">Vector data security distribution and tracking system</h2>
      </div>

    
      <div class="buttons">
          <button @click="register_button" class="register-button">注册</button>
          <button @click="login_button" class="login-button">登录</button>
      </div>
  </div>

</template>

<script setup>
import { useRouter } from 'vue-router';

const router = useRouter();

const login_button = () => {
  router.push('/login');
}

const register_button = () => {
  router.push('/register');
}

</script>

<style scoped>

.container {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}


.background-image {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  object-fit: cover;
  z-index: -1;
}


.text-content {
  margin-bottom: 30px;
}

.main-title {

  color: #000;
  font-weight: bold;
  font-size: 3.5em;

}

.sub-title {
  font-size: 2em;
  color: #666;
  margin-top: 10px;
  letter-spacing: 0.5px;
}


.buttons {
  position: absolute;
  top: 15px;
  right: 100px;
  display: flex;
  gap: 20px;
}

.register-button, .login-button {
  padding: 10px 20px;
  border: none;
  border-radius: 20px;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.register-button {
  background-color: #3B82F6;
  color: white;
}

.login-button {
  background-color: white;
  color: #333;
  border: 1px solid #ccc;
}


.register-button:hover {
  background-color: #2563EB;
}

.login-button:hover {
  background-color: #f0f0f0;
}

</style> -->


<!-- <template>
  <div class="home-container">

    <canvas ref="canvasRef" class="background-canvas"></canvas>


    <div class="glow-effect"></div>


    <div class="content-overlay">
      <div class="brand-info">
        <h1 class="system-title">矢量数据安全分发与追踪溯源系统</h1>
        <p class="system-subtitle">守护每一比特数据的安全、主权与价值</p>
      </div>
      
      <div class="action-buttons">
          <button @click="register_button" class="action-btn register-btn">创建账户</button>
          <button @click="login_button" class="action-btn login-btn">授权访问</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import * as THREE from 'three';

const router = useRouter();
const login_button = () => router.push('/login');
const register_button = () => router.push('/register');

// --- Three.js 场景引用 ---
const canvasRef = ref(null);
let renderer, scene, camera, animationFrameId = null;
let instancedCubes, starField;
const clock = new THREE.Clock();

// --- 初始化 3D 场景 ---
const initThreeJS = () => {
  if (!canvasRef.value) return;

  // 1. 场景
  scene = new THREE.Scene();

  // 2. 相机
  camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 0, 15);

  // 3. 渲染器
  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    antialias: true,
    alpha: true // 使背景透明
  });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // 4. 添加元素
  createStarfield();
  createInstancedCubes();
  
  // 5. 灯光
  const ambientLight = new THREE.AmbientLight(0x406080, 0.8); // 蓝色环境光
  scene.add(ambientLight);
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
  directionalLight.position.set(1, 1, 5);
  scene.add(directionalLight);

  // 6. 启动动画循环
  animate();
};

// --- 创建静态星空背景 ---
const createStarfield = () => {
    const starCount = 8000;
    const positions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
        positions[i * 3 + 0] = (Math.random() - 0.5) * 200;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 200;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 200;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const material = new THREE.PointsMaterial({
        color: 0x88aaff,
        size: 0.05,
        transparent: true,
        opacity: 0.8
    });
    starField = new THREE.Points(geometry, material);
    scene.add(starField);
};

// --- 创建动态旋转的立方体 (高性能 InstancedMesh) ---
const createInstancedCubes = () => {
    const count = 400;
    const geometry = new THREE.BoxGeometry(0.3, 0.3, 0.3);
    const material = new THREE.MeshStandardMaterial({
        color: 0x60a5fa,      // 基础蓝色
        emissive: 0x3b82f6,   // 自发光颜色，使其看起来像光源
        emissiveIntensity: 0.8,
        metalness: 0.6,
        roughness: 0.3,
    });
    
    instancedCubes = new THREE.InstancedMesh(geometry, material, count);
    
    const dummy = new THREE.Object3D();
    for (let i = 0; i < count; i++) {
        // 随机分布在一个球体内
        const phi = Math.random() * Math.PI * 2;
        const costheta = Math.random() * 2 - 1;
        const u = Math.random();
        const theta = Math.acos(costheta);
        const r = 10 * Math.cbrt(u) + 5; // 在半径5到15的球体内分布

        dummy.position.set(
            r * Math.sin(theta) * Math.cos(phi),
            r * Math.sin(theta) * Math.sin(phi),
            r * Math.cos(theta)
        );

        dummy.rotation.set(
            Math.random() * Math.PI * 2,
            Math.random() * Math.PI * 2,
            Math.random() * Math.PI * 2
        );
        
        const scale = Math.random() * 0.5 + 0.3;
        dummy.scale.set(scale, scale, scale);

        dummy.updateMatrix();
        instancedCubes.setMatrixAt(i, dummy.matrix);
    }
    scene.add(instancedCubes);
};

// --- 动画循环 ---
const animate = () => {
  animationFrameId = requestAnimationFrame(animate);
  const delta = clock.getDelta();

  // 缓慢旋转整个场景
  if (starField) {
      starField.rotation.y += delta * 0.01;
  }
  if (instancedCubes) {
      instancedCubes.rotation.y += delta * 0.03;
  }
  
  // 缓慢移动相机，营造景深感
  camera.position.z -= Math.sin(clock.getElapsedTime() * 0.1) * 0.005;

  renderer.render(scene, camera);
};


// --- 处理窗口大小变化 ---
const handleResize = () => {
  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  }
};

// --- Vue 生命周期钩子 ---
onMounted(async () => {
  await nextTick();
  initThreeJS();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId);
  window.removeEventListener('resize', handleResize);
  // 清理 Three.js 资源
  if (renderer) renderer.dispose();
  if (scene) {
    scene.traverse(object => {
      if (object.geometry) object.geometry.dispose();
      if (object.material) {
        if (Array.isArray(object.material)) {
          object.material.forEach(material => material.dispose());
        } else {
          object.material.dispose();
        }
      }
    });
  }
});
</script>

<style scoped>
.home-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: #020617; /* 非常深的午夜蓝 */
  display: flex;
  justify-content: center;
  align-items: center;
}

.background-canvas {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1; /* 在背景和辉光之上 */
}

.glow-effect {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100vmin; /* 响应式辉光大小 */
  height: 100vmin;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, rgba(59, 130, 246, 0) 60%);
  z-index: 2; /* 在Canvas之上，内容之下 */
  pointer-events: none; /* 允许点击穿透 */
}

.content-overlay {
  position: relative;
  z-index: 3; /* 在最顶层 */
  text-align: center;
  color: white;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 40px;
  padding: 20px;
}

.brand-info {
  text-shadow: 0 3px 15px rgba(0, 0, 0, 0.5);
  animation: fadeIn 2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.system-title {
  font-size: clamp(2.5rem, 6vw, 4rem); /* 响应式字体 */
  font-weight: 700;
  line-height: 1.2;
  color: #f0f9ff;
  letter-spacing: 0.5px;
}

.system-subtitle {
  font-size: clamp(1rem, 2vw, 1.25rem);
  color: rgba(203, 213, 225, 0.8);
  margin-top: 20px;
  font-weight: 300;
  max-width: 600px;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap; /* 在小屏幕上换行 */
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
  animation: fadeIn 2s ease-out 0.5s;
  animation-fill-mode: backwards;
}

.action-btn {
  padding: 14px 40px;
  font-size: 16px;
  font-weight: 500;
  border-radius: 50px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid rgba(59, 130, 246, 0.5);
  background: rgba(17, 24, 39, 0.5);
  color: #e0f2fe;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.action-btn:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(59, 130, 246, 0.2);
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(96, 165, 250, 0.8);
}

.login-btn {
  background: #3b82f6; /* 主题蓝色 */
  border-color: #3b82f6;
  color: white;
}
.login-btn:hover {
  background: #60a5fa;
  border-color: #60a5fa;
  box-shadow: 0 8px 25px rgba(96, 165, 250, 0.3);
}
</style> -->



<template>
  <div class="home-container">
    <canvas ref="canvasRef" class="background-canvas"></canvas>
    
    <div class="content-overlay">
      <div class="brand-info">
        <h1 class="system-title">
          <span class="title-line">矢量地理数据安全分发</span>
          <span class="title-line">与定责溯源系统</span>
        </h1>
        <p class="system-subtitle">守护每一比特数据的安全、主权与价值</p>
      </div>
      
      <div class="action-buttons">
          <button @click="register_button" class="action-btn register-btn">创建账户</button>
          <button @click="login_button" class="action-btn login-btn">授权访问</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import * as THREE from 'three';

const router = useRouter();
const login_button = () => router.push('/login');
const register_button = () => router.push('/register');

// --- Refs and 3D variables ---
const canvasRef = ref(null);
let renderer, scene, camera, animationFrameId = null;
const clock = new THREE.Clock();
const mouse = new THREE.Vector2(-10, -10);

let dataParticles; // 数据元胞
const particlesData = [];
const particleCount = 150;
const curves = [];

// --- 初始化 3D 场景 ---
const initThreeJS = () => {
  if (!canvasRef.value) return;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 2000);
  camera.position.set(0, 0, 30);

  renderer = new THREE.WebGLRenderer({ canvas: canvasRef.value, antialias: true, alpha: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  createDataNetwork();
  createDataParticles();
  createSystemCore();

  const ambientLight = new THREE.AmbientLight(0x608dff, 0.5);
  scene.add(ambientLight);

  animate();
};

// [新] 创建数据神经网络路径
const createDataNetwork = () => {
    for (let i = 0; i < particleCount; i++) {
        const points = [];
        const startPoint = new THREE.Vector3(0, 0, 0); // 所有路径从核心发出
        points.push(startPoint);
        for (let j = 0; j < 4; j++) {
            points.push(new THREE.Vector3(
                (Math.random() - 0.5) * 60,
                (Math.random() - 0.5) * 60,
                (Math.random() - 0.5) * 60,
            ));
        }
        const curve = new THREE.CatmullRomCurve3(points);
        curves.push(curve);

        // 可视化路径 (可选，但效果很好)
        const curveGeometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(50));
        const curveMaterial = new THREE.LineBasicMaterial({ color: 0x1e40af, transparent: true, opacity: 0.2 });
        const curveObject = new THREE.Line(curveGeometry, curveMaterial);
        scene.add(curveObject);
    }
};

// [新] 创建数据元胞
const createDataParticles = () => {
    const geometry = new THREE.SphereGeometry(0.1, 16, 16);
    const material = new THREE.MeshBasicMaterial({ color: 0x7dd3fc });
    dataParticles = new THREE.InstancedMesh(geometry, material, particleCount);
    
    for (let i = 0; i < particleCount; i++) {
        particlesData.push({
            progress: Math.random(), // 初始位置
            speed: 0.01 + Math.random() * 0.02, // 随机速度
        });
    }
    scene.add(dataParticles);
};

// [新] 创建系统核心与能量波
const createSystemCore = () => {
    // 核心
    const coreGeometry = new THREE.IcosahedronGeometry(1.5, 5);
    const coreMaterial = new THREE.MeshBasicMaterial({ color: 0x93c5fd, wireframe: true, transparent: true, opacity: 0.8 });
    const core = new THREE.Mesh(coreGeometry, coreMaterial);
    scene.add(core);

    // 能量波
    const waveGeometry = new THREE.TorusGeometry(2, 0.1, 16, 100);
    const waveMaterial = new THREE.MeshBasicMaterial({ color: 0x60a5fa, transparent: true, opacity: 0.5 });
    const wave = new THREE.Mesh(waveGeometry, waveMaterial);
    wave.rotation.x = Math.PI / 2;
    wave.name = 'energyWave'; // 用于在动画中找到它
    scene.add(wave);
};


// --- 动画循环 ---
const animate = () => {
    animationFrameId = requestAnimationFrame(animate);
    const delta = clock.getDelta();
    const elapsedTime = clock.getElapsedTime();

    const dummy = new THREE.Object3D();

    // 更新数据元胞位置
    particlesData.forEach((particle, i) => {
        particle.progress += particle.speed * delta;
        if (particle.progress > 1) {
            particle.progress = 0.001; // 回到起点
        }
        const position = curves[i].getPoint(particle.progress);
        dummy.position.copy(position);

        // [新] 追踪光束效果：让元胞后面有一个小尾巴
        const scale = 1 + Math.sin(particle.progress * Math.PI) * 0.5;
        dummy.scale.set(scale, scale, scale);
        
        dummy.updateMatrix();
        dataParticles.setMatrixAt(i, dummy.matrix);
    });
    dataParticles.instanceMatrix.needsUpdate = true;

    // 更新系统核心动画
    const wave = scene.getObjectByName('energyWave');
    if (wave) {
        const waveProgress = (elapsedTime * 0.3) % 1;
        wave.scale.setScalar(1 + waveProgress * 15);
        wave.material.opacity = 0.5 * (1 - waveProgress);
    }

    // 鼠标交互：相机视差
    camera.position.x += (mouse.x * 5 - camera.position.x) * 0.05;
    camera.position.y += (-mouse.y * 5 - camera.position.y) * 0.05;
    camera.lookAt(scene.position);

    renderer.render(scene, camera);
};

// --- 事件处理与生命周期 ---
const handleResize = () => { /* ... */ };
const handleMouseMove = (event) => { /* ... */ };

onMounted(async () => {
  await nextTick();
  initThreeJS();
  window.addEventListener('resize', handleResize);
  window.addEventListener('mousemove', handleMouseMove);
});
onUnmounted(() => { /* ... */ });
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
  position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1;
}

.content-overlay {
  position: relative; z-index: 2; text-align: center;
  display: flex; flex-direction: column; align-items: center;
  gap: 48px; padding: 20px;
}

.brand-info {
  animation: text-focus-in 1.5s cubic-bezier(0.550, 0.085, 0.680, 0.530) both;
}

.system-title {
  font-size: clamp(3rem, 8vw, 5rem);
  font-weight: 800;
  line-height: 1.15;
  color: #fff;
  text-shadow: 0 0 15px rgba(147, 197, 253, 0.3), 0 0 40px rgba(96, 165, 250, 0.4);
  display: flex;
  flex-direction: column;
}
.title-line:last-child {
  margin-left: 2rem; /* 增加错位感 */
}

.system-subtitle {
  font-size: clamp(1.1rem, 2.5vw, 1.4rem);
  color: #a7c1e5;
  margin-top: 24px;
  font-weight: 400;
  letter-spacing: 0.5px;
}

.action-buttons {
  display: flex; gap: 24px; margin-top: 24px;
  animation: slide-in-bottom 1.2s cubic-bezier(0.250, 0.460, 0.450, 0.940) 0.8s both;
}

.action-btn {
  padding: 16px 48px; font-size: 1rem; font-weight: 600;
  border-radius: 50px; cursor: pointer;
  transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
  border: 1px solid rgba(96, 165, 250, 0.5);
  background: rgba(30, 64, 175, 0.3); color: #e0f2fe;
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  position: relative; overflow: hidden;
}
.action-btn::before {
  content: '';
  position: absolute;
  top: 0; left: -100%; width: 100%; height: 100%;
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
  background: #3b82f6; border-color: #3b82f6;
  color: white;
}
.login-btn:hover { background: #60a5fa; border-color: #93c5fd; }

/* 动画效果 */
@keyframes text-focus-in {
  0% { filter: blur(12px); opacity: 0; }
  100% { filter: blur(0px); opacity: 1; }
}
@keyframes slide-in-bottom {
  0% { transform: translateY(100px); opacity: 0; }
  100% { transform: translateY(0); opacity: 1; }
}
</style>