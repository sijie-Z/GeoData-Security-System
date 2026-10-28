<template>
  <aside class="auth-aside">
    <div
      ref="panelRef"
      class="brand-panel"
    >
      <!-- 程序化装饰：网格 / 光斑 / 轨道 / 漂浮粒子（纯 CSS，无外网资源） -->
      <div
        class="decor"
        aria-hidden="true"
      >
        <div class="decor-grid" />
        <div class="decor-orb orb-a" />
        <div class="decor-orb orb-b" />
        <div class="decor-orbit">
          <span class="orbit-ring" />
          <span class="orbit-dot" />
        </div>
        <span class="particle p1" />
        <span class="particle p2" />
        <span class="particle p3" />
        <span class="particle p4" />
        <span class="particle p5" />
        <span class="particle p6" />
      </div>

      <div class="brand-content">
        <div class="brand-mark">
          <el-icon :size="24">
            <MapLocation />
          </el-icon>
        </div>
        <h1 class="brand-title">
          {{ $t('common.appName') }}
        </h1>
        <p class="brand-tagline">
          {{ $t('login.brandTagline') }}
        </p>

        <ul class="brand-features">
          <li class="brand-feature">
            <span class="feature-icon"><el-icon :size="16"><Checked /></el-icon></span>
            <span class="feature-text">{{ $t('login.brandFeatureApproval') }}</span>
          </li>
          <li class="brand-feature">
            <span class="feature-icon"><el-icon :size="16"><Stamp /></el-icon></span>
            <span class="feature-text">{{ $t('login.brandFeatureWatermark') }}</span>
          </li>
          <li class="brand-feature">
            <span class="feature-icon"><el-icon :size="16"><Aim /></el-icon></span>
            <span class="feature-text">{{ $t('login.brandFeatureTracing') }}</span>
          </li>
          <li class="brand-feature">
            <span class="feature-icon"><el-icon :size="16"><Link /></el-icon></span>
            <span class="feature-text">{{ $t('login.brandFeatureBlockchain') }}</span>
          </li>
        </ul>

        <!-- 装饰性数字印记（QR）：固定品牌串渲染，不含任何真实地址/信息；
             深墨浅底 + 充分静区，纸面印记与铭文同栏排布 -->
        <div class="brand-qr">
          <div
            class="qr-plate"
            aria-hidden="true"
          >
            <canvas
              ref="qrCanvasRef"
              class="qr-canvas"
            />
          </div>
          <div class="qr-caption">
            <span class="qr-caption-text">{{ $t('login.brandQrCaption') }}</span>
            <span
              class="qr-caption-meta"
              aria-hidden="true"
            >GEODATA · TRACE</span>
          </div>
        </div>
      </div>

      <p class="brand-footer">
        {{ $t('login.brandFooter') }}
      </p>
    </div>
  </aside>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import QRCode from 'qrcode';
import { MapLocation, Checked, Stamp, Aim, Link } from '@element-plus/icons-vue';

// 装饰性 QR 载荷：固定品牌串，不携带任何真实地址或内部信息
const QR_PAYLOAD = 'GEODATA-TRACKING';

const panelRef = ref(null);
const qrCanvasRef = ref(null);

function cssVar(el, name, fallback) {
  const value = el ? getComputedStyle(el).getPropertyValue(name).trim() : '';
  return value || fallback;
}

/**
 * 轻量重绘：从 QR 矩阵出发自绘方形模块。
 * - 内圈静区 quiet（模块数）+ plate 内边距，合计 ≥ 4 模块，符合 QR 静区惯例
 * - 墨色由 CSS 令牌注入（--brand-qr-ink），不散落魔法色值
 * - 高分辨率缓冲（module=12），显示时缩小，相当于 2x+ 超采样
 */
function drawDecorativeQr(canvas, text, { ink, module = 12, quiet = 2 }) {
  const { modules } = QRCode.create(text, { errorCorrectionLevel: 'M' });
  const n = modules.size;
  const total = (n + quiet * 2) * module;
  canvas.width = total;
  canvas.height = total;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, total, total);
  ctx.fillStyle = ink;
  for (let r = 0; r < n; r += 1) {
    for (let c = 0; c < n; c += 1) {
      if (!modules.get(r, c)) continue;
      ctx.fillRect((c + quiet) * module, (r + quiet) * module, module, module);
    }
  }
}

onMounted(() => {
  const panel = panelRef.value;
  const canvas = qrCanvasRef.value;
  if (!panel || !canvas) return;
  const ink = cssVar(panel, '--brand-qr-ink', '#0a1b3d');
  drawDecorativeQr(canvas, QR_PAYLOAD, { ink });
});
</script>

<style scoped>
.auth-aside {
  width: 45%;
  flex: 0 0 45%;
  position: relative;
}

.brand-panel {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 64px clamp(32px, 5vw, 76px);
  overflow: hidden;
  color: #eef2ff;
  background:
    radial-gradient(90% 70% at 88% 8%, rgba(59, 130, 246, 0.35) 0%, transparent 55%),
    radial-gradient(80% 65% at 6% 94%, rgba(14, 165, 233, 0.26) 0%, transparent 60%),
    linear-gradient(158deg, #0b1e3f 0%, #10306b 45%, #050d1f 100%);

  /* —— 组件级令牌：印记墨色 / 纸面 / 细线 / 铭文排印统一从此取值 —— */
  --brand-hairline: rgba(255, 255, 255, 0.12);
  --brand-qr-ink: #0a1b3d;                 /* 纸面墨色（深海军蓝） */
  --brand-qr-paper-a: #f6f9ff;
  --brand-qr-paper-b: #e9f0fd;
  --brand-qr-glow: rgba(96, 165, 250, 0.16);
  --brand-caption: rgba(232, 240, 255, 0.95);
  --brand-caption-meta: rgba(163, 190, 255, 0.85);
}

/* 深色页面主题下品牌面板再压一档明度，与 Linear 风画布衔接 */
html.dark .brand-panel {
  background:
    radial-gradient(90% 70% at 88% 8%, rgba(59, 130, 246, 0.28) 0%, transparent 55%),
    radial-gradient(80% 65% at 6% 94%, rgba(14, 165, 233, 0.20) 0%, transparent 60%),
    linear-gradient(158deg, #091733 0%, #0c2657 45%, #04081a 100%);
}

/* ---------- 装饰层 ---------- */
.decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.decor-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.085) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.085) 1px, transparent 1px);
  background-size: 46px 46px;
  -webkit-mask-image: radial-gradient(78% 68% at 50% 42%, #000 28%, transparent 100%);
  mask-image: radial-gradient(78% 68% at 50% 42%, #000 28%, transparent 100%);
}

.decor-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.55;
}

.orb-a {
  width: 420px;
  height: 420px;
  top: -130px;
  right: -130px;
  background: rgba(59, 130, 246, 0.5);
}

.orb-b {
  width: 360px;
  height: 360px;
  bottom: -110px;
  left: -110px;
  background: rgba(14, 165, 233, 0.34);
}

.decor-orbit {
  position: absolute;
  right: -140px;
  bottom: -130px;
  width: 420px;
  height: 420px;
  animation: orbit-spin 32s linear infinite;
}

.orbit-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 1px dashed rgba(96, 165, 250, 0.28);
}

.orbit-ring::before {
  content: '';
  position: absolute;
  inset: 62px;
  border-radius: 50%;
  border: 1px solid rgba(96, 165, 250, 0.14);
}

.orbit-dot {
  position: absolute;
  top: -4px;
  left: 50%;
  width: 8px;
  height: 8px;
  margin-left: -4px;
  border-radius: 50%;
  background: #7dd3fc;
  box-shadow: 0 0 12px 3px rgba(56, 189, 248, 0.65);
}

@keyframes orbit-spin {
  to { transform: rotate(360deg); }
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(125, 211, 252, 0.9);
  box-shadow: 0 0 10px 2px rgba(56, 189, 248, 0.5);
  opacity: 0;
  animation: float-up 12s ease-in-out infinite;
}

.p1 { left: 10%; bottom: 6%; animation-delay: 0s; animation-duration: 11s; }
.p2 { left: 24%; bottom: 3%; animation-delay: 1.4s; animation-duration: 14s; width: 3px; height: 3px; }
.p3 { left: 38%; bottom: 9%; animation-delay: 3.1s; animation-duration: 12s; }
.p4 { left: 55%; bottom: 4%; animation-delay: 4.5s; animation-duration: 15s; width: 5px; height: 5px; }
.p5 { left: 70%; bottom: 8%; animation-delay: 2.2s; animation-duration: 13s; }
.p6 { left: 84%; bottom: 3%; animation-delay: 5.8s; animation-duration: 16s; width: 3px; height: 3px; }

@keyframes float-up {
  0% { transform: translate(0, 0); opacity: 0; }
  12% { opacity: 0.9; }
  85% { opacity: 0.45; }
  100% { transform: translate(26px, -46vh); opacity: 0; }
}

/* ---------- 品牌内容 ---------- */
.brand-content {
  position: relative;
  z-index: 2;
  max-width: 520px;
}

.brand-mark {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  box-shadow: 0 12px 28px -8px rgba(29, 78, 216, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.25);
  margin-bottom: 28px;
}

.brand-title {
  margin: 0 0 14px;
  font-size: clamp(28px, 2.7vw, 38px);
  font-weight: 700;
  letter-spacing: 0.5px;
  line-height: 1.25;
  color: #ffffff;
}

.brand-tagline {
  margin: 0 0 44px;
  font-size: 15.5px;
  line-height: 1.7;
  color: rgba(186, 230, 253, 0.92);
}

.brand-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.brand-feature {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  transition: background 0.3s ease, border-color 0.3s ease, transform 0.3s ease;
}

.brand-feature:hover {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(56, 189, 248, 0.35);
  transform: translateX(6px);
}

.feature-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #bae6fd;
  background: rgba(56, 189, 248, 0.14);
  border: 1px solid rgba(56, 189, 248, 0.28);
}

.feature-text {
  font-size: 14.5px;
  font-weight: 400;
  letter-spacing: 0.3px;
  color: rgba(226, 232, 240, 0.95);
}

.brand-footer {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 28px;
  z-index: 2;
  margin: 0;
  text-align: center;
  font-size: 12px;
  letter-spacing: 0.4px;
  color: rgba(148, 163, 184, 0.55);
}

/* ---------- 装饰性数字印记（QR） ----------
   细线轨线将印记区与功能列表分离；左侧纸面印记 + 右侧两行铭文，
   与内容栏同轴（取代此前的居中小方块）。 */
.brand-qr {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 20px;
  margin-top: 30px;
  padding-top: 28px;
  border-top: 1px solid var(--brand-hairline);
  animation: qr-rise var(--duration-500, 500ms) var(--ease-out, cubic-bezier(0.16, 1, 0.3, 1)) 140ms both;
}

@keyframes qr-rise {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: none; }
}

.qr-plate {
  position: relative;
  flex-shrink: 0;
  width: 124px;
  height: 124px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  background: linear-gradient(165deg, var(--brand-qr-paper-a) 0%, var(--brand-qr-paper-b) 100%);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.65),
    0 22px 44px -22px rgba(2, 6, 23, 0.85);
}

/* 极低透明度光晕：把纸面印记从深蓝底上轻轻托起 */
.qr-plate::before {
  content: '';
  position: absolute;
  inset: -30px;
  z-index: -1;
  border-radius: 50%;
  background: radial-gradient(50% 50% at 50% 50%, var(--brand-qr-glow) 0%, transparent 72%);
}

.qr-canvas {
  display: block;
  /* 100px = 25 模块（21+静区2×2）× 4px/模块：dsf≥1 下均为整数像素步长，缩放 3.0x 精确 */
  width: 100px;
  height: 100px;
}

.qr-caption {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.qr-caption-text {
  font-size: var(--font-size-sm, 13px);
  font-weight: var(--font-weight-medium, 500);
  letter-spacing: 0.4px;
  color: var(--brand-caption);
}

.qr-caption-meta {
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.22em;
  color: var(--brand-caption-meta);
}

@media (prefers-reduced-motion: reduce) {
  .brand-qr {
    animation: none;
  }

  .decor-orbit {
    animation: none;
  }

  .particle {
    animation: none;
  }
}

/* ---------- 响应式：窄屏转为顶部横幅 ---------- */
@media (max-width: 1024px) {
  .auth-aside {
    width: 100%;
    flex: none;
  }

  .brand-panel {
    position: static;
    height: auto;
    justify-content: flex-start;
    padding: 40px 28px 34px;
  }

  .brand-mark {
    display: none;
  }

  .brand-title {
    font-size: 24px;
    margin-bottom: 8px;
  }

  .brand-tagline {
    margin-bottom: 22px;
  }

  .brand-features {
    flex-direction: row;
    flex-wrap: wrap;
    gap: 10px;
  }

  .brand-feature {
    padding: 8px 12px;
    gap: 8px;
  }

  .brand-feature:hover {
    transform: none;
  }

  .feature-icon {
    width: 26px;
    height: 26px;
    border-radius: 8px;
  }

  .feature-text {
    font-size: 13px;
  }

  .brand-footer {
    position: static;
    margin-top: 20px;
    text-align: left;
  }

  /* 窄屏单栏横幅：隐藏 QR，避免挤破布局 */
  .brand-qr {
    display: none;
  }

  .decor-orbit {
    display: none;
  }
}

/* 矮视口（桌面双栏）压缩纵向节奏，保证 QR 与页脚不被裁切 */
@media (max-height: 820px) and (min-width: 1025px) {
  .brand-panel {
    padding-top: 40px;
    padding-bottom: 48px;
  }

  .brand-mark {
    margin-bottom: 18px;
  }

  .brand-tagline {
    margin-bottom: 18px;
  }

  .brand-features {
    gap: 8px;
  }

  .brand-feature {
    padding: 8px 14px;
  }

  .brand-qr {
    margin-top: 20px;
    padding-top: 20px;
  }

  .qr-plate {
    width: 105px;
    height: 105px;
  }

  .qr-canvas {
    /* 75px = 25 × 3px/模块：dsf1 3 / dsf2 6 设备像素，整数步长且画布原点落整数位 */
    width: 75px;
    height: 75px;
  }
}

@media (max-width: 640px) {
  .brand-panel {
    padding: 30px 20px 26px;
  }

  .brand-features,
  .brand-footer {
    display: none;
  }

  .brand-tagline {
    margin-bottom: 4px;
    font-size: 14px;
  }
}
</style>
