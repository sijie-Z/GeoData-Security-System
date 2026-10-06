<template>
  <aside class="auth-aside">
    <div class="brand-panel">
      <!-- 程序化装饰：网格 / 光斑 / 轨道 / 漂浮粒子（纯 CSS，无外网资源） -->
      <div class="decor" aria-hidden="true">
        <div class="decor-grid"></div>
        <div class="decor-orb orb-a"></div>
        <div class="decor-orb orb-b"></div>
        <div class="decor-orbit">
          <span class="orbit-ring"></span>
          <span class="orbit-dot"></span>
        </div>
        <span class="particle p1"></span>
        <span class="particle p2"></span>
        <span class="particle p3"></span>
        <span class="particle p4"></span>
        <span class="particle p5"></span>
        <span class="particle p6"></span>
      </div>

      <div class="brand-content">
        <div class="brand-mark">
          <el-icon :size="24"><MapLocation /></el-icon>
        </div>
        <h1 class="brand-title">{{ $t('common.appName') }}</h1>
        <p class="brand-tagline">{{ $t('login.brandTagline') }}</p>

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
      </div>

      <p class="brand-footer">{{ $t('login.brandFooter') }}</p>
    </div>
  </aside>
</template>

<script setup>
import { MapLocation, Checked, Stamp, Aim, Link } from '@element-plus/icons-vue';
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
    radial-gradient(90% 70% at 88% 8%, rgba(99, 102, 241, 0.38) 0%, transparent 55%),
    radial-gradient(80% 65% at 6% 94%, rgba(37, 99, 235, 0.30) 0%, transparent 60%),
    linear-gradient(158deg, #16204a 0%, #1d1a4d 42%, #070b18 100%);
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
  background: rgba(79, 70, 229, 0.55);
}

.orb-b {
  width: 360px;
  height: 360px;
  bottom: -110px;
  left: -110px;
  background: rgba(37, 99, 235, 0.42);
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
  border: 1px dashed rgba(129, 140, 248, 0.28);
}

.orbit-ring::before {
  content: '';
  position: absolute;
  inset: 62px;
  border-radius: 50%;
  border: 1px solid rgba(129, 140, 248, 0.14);
}

.orbit-dot {
  position: absolute;
  top: -4px;
  left: 50%;
  width: 8px;
  height: 8px;
  margin-left: -4px;
  border-radius: 50%;
  background: #a5b4fc;
  box-shadow: 0 0 12px 3px rgba(129, 140, 248, 0.65);
}

@keyframes orbit-spin {
  to { transform: rotate(360deg); }
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: rgba(165, 180, 252, 0.9);
  box-shadow: 0 0 10px 2px rgba(129, 140, 248, 0.5);
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
  background: linear-gradient(135deg, #6366f1 0%, #2563eb 100%);
  box-shadow: 0 12px 28px -8px rgba(79, 70, 229, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.25);
  margin-bottom: 28px;
}

.brand-title {
  margin: 0 0 14px;
  font-size: clamp(28px, 2.7vw, 38px);
  font-weight: 800;
  letter-spacing: 0.5px;
  line-height: 1.25;
  color: #ffffff;
}

.brand-tagline {
  margin: 0 0 44px;
  font-size: 15.5px;
  line-height: 1.7;
  color: rgba(199, 210, 254, 0.92);
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
  border-color: rgba(129, 140, 248, 0.35);
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
  color: #c7d2fe;
  background: rgba(99, 102, 241, 0.18);
  border: 1px solid rgba(129, 140, 248, 0.28);
}

.feature-text {
  font-size: 14.5px;
  font-weight: 500;
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

  .decor-orbit {
    display: none;
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
