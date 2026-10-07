<template>
  <div class="auth-page">
    <!-- 顶栏小工具：语言切换（复用现有机制） -->
    <div class="auth-lang">
      <LanguageSwitcher />
    </div>

    <div class="auth-layout">
      <!-- 左侧品牌栏 -->
      <AuthBrandPanel />

      <!-- 右侧表单栏 -->
      <main class="auth-main">
        <section class="auth-card">
          <header class="auth-card-header">
            <h2 class="auth-form-title">{{ $t('login.formTitle') }}</h2>
            <p class="auth-form-subtitle">{{ $t('login.formSubtitle') }}</p>
          </header>

          <el-form :model="data" :rules="rules" ref="elFormRef" class="auth-form" @submit.prevent="login">
            <el-form-item prop="username">
              <el-input
                size="large"
                :prefix-icon="User"
                v-model="data.username"
                :placeholder="$t('login.usernamePlaceholder')"
                class="auth-input"
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
                class="auth-input"
              />
            </el-form-item>

            <el-form-item prop="role" class="role-selector-item">
              <div class="role-capsule-group" role="radiogroup">
                <div
                  class="role-option"
                  :class="{ active: data.role === 'admin' }"
                  role="radio"
                  :aria-checked="data.role === 'admin'"
                  @click="data.role = 'admin'"
                >
                  <el-icon><Platform /></el-icon><span>{{ $t('auth.admin') }}</span>
                </div>
                <div
                  class="role-option"
                  :class="{ active: data.role === 'employee' }"
                  role="radio"
                  :aria-checked="data.role === 'employee'"
                  @click="data.role = 'employee'"
                >
                  <el-icon><UserFilled /></el-icon><span>{{ $t('auth.employee') }}</span>
                </div>
                <div class="active-capsule" :style="capsuleStyle"></div>
              </div>
            </el-form-item>

            <el-form-item class="submit-item">
              <el-button
                class="auth-submit"
                @click="login"
                :loading="loading"
                native-type="submit"
              >
                <el-icon v-if="!loading" class="submit-icon"><Key /></el-icon>
                {{ $t('login.loginButton') }}
              </el-button>
            </el-form-item>
          </el-form>

          <div class="auth-card-footer">
            <span>{{ $t('login.noAccount') }}</span>
            <el-link type="primary" @click="register" :underline="false" class="auth-link">
              {{ $t('login.registerNow') }}
            </el-link>
          </div>

          <!-- 安全提示 -->
          <div class="security-notice">
            <el-icon><Warning /></el-icon>
            <span>{{ $t('login.securityNotice') }}</span>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { Lock, User, Platform, UserFilled, Key, Warning } from '@element-plus/icons-vue';
import { reactive, ref, computed } from 'vue';
import { ElMessage } from 'element-plus';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useUserStore } from '@/stores/userStore';
import { login as loginApi } from '@/api/auth';
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue';
import AuthBrandPanel from '@/components/common/AuthBrandPanel.vue';

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
  userStore.clearUserInfo()
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
      if (responseData.role && responseData.role.startsWith('admin')) await router.push('/admin');
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
</script>

<style scoped>
.auth-page {
  position: relative;
  min-height: 100vh;
  overflow-x: hidden;
  background: #f4f6fb;
}

/* 顶栏语言切换：悬浮胶囊，明暗底上均可见 */
.auth-lang {
  position: absolute;
  top: 18px;
  right: 22px;
  z-index: 60;
  padding: 2px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 6px 18px -6px rgba(15, 23, 42, 0.22);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.auth-layout {
  display: flex;
  min-height: 100vh;
}

/* ---------- 右侧表单栏 ---------- */
.auth-main {
  flex: 1 1 auto;
  display: flex;
  padding: 56px 32px;
  background:
    radial-gradient(60% 50% at 85% 12%, rgba(59, 130, 246, 0.07), transparent 70%),
    radial-gradient(50% 45% at 12% 88%, rgba(37, 99, 235, 0.06), transparent 70%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f9 100%);
}

.auth-card {
  width: 100%;
  max-width: 460px;
  margin: auto;
  padding: 44px 40px 36px;
  background: #ffffff;
  border: 1px solid #e9eef5;
  border-radius: 24px;
  box-shadow: 0 24px 56px -28px rgba(15, 23, 42, 0.25), 0 4px 16px -8px rgba(15, 23, 42, 0.08);
  animation: card-in 0.55s cubic-bezier(0.22, 0.8, 0.36, 1) both;
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; }
}

.auth-card-header {
  margin-bottom: 30px;
}

.auth-form-title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: #0f172a;
}

.auth-form-subtitle {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

/* ---------- 输入框 ---------- */
.auth-form :deep(.el-form-item) {
  margin-bottom: 22px;
}

.auth-form :deep(.auth-input .el-input__wrapper) {
  height: 52px;
  border-radius: 14px;
  background: #f8fafc;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  transition: box-shadow 0.25s ease, background 0.25s ease;
}

.auth-form :deep(.auth-input .el-input__wrapper:hover) {
  background: #ffffff;
  box-shadow: 0 0 0 1px #cbd5e1 inset;
}

.auth-form :deep(.auth-input .el-input__wrapper.is-focus) {
  background: #ffffff;
  box-shadow: 0 0 0 1.5px #3b82f6 inset, 0 0 0 4px rgba(59, 130, 246, 0.14);
}

.auth-form :deep(.auth-input .el-input__prefix) {
  color: #94a3b8;
  font-size: 17px;
}

/* 浅色卡片在两种页面主题下保持同一体系：钉住输入文字色，
   避免深色主题继承 --el-text-color-regular（#a0a0ab 在浅底上仅 ≈2.5:1） */
.auth-form :deep(.auth-input .el-input__inner) {
  color: #0f172a;
}

/* 占位符同属浅色卡片体系：钉到 slate-500，两种主题下均 ≥4.5:1
   （浅色默认 token #8f8f8f 在 #f8fafc 上仅 ≈3.1:1） */
.auth-form :deep(.auth-input .el-input__inner::placeholder) {
  color: #64748b;
}

/* 焦点反馈：统一用本页设计的蓝色双层环（双主题一致）。
   design-system 的 .el-input__wrapper:focus-within 带 !important 的双层 --ring
   在深色主题下会叠出 #18191b 深色重影，这里按本页设计值钉回 */
.auth-form :deep(.auth-input .el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 1px #3b82f6 inset, 0 0 0 4px rgba(59, 130, 246, 0.14) !important;
}

.auth-form :deep(.auth-input .el-input__inner:focus-visible) {
  box-shadow: none;
}

/* ---------- 角色胶囊分段控件 ---------- */
.role-selector-item {
  margin: 26px 0 22px !important;
}

.role-selector-item :deep(.el-form-item__content) {
  width: 100%;
}

.role-capsule-group {
  position: relative;
  display: flex;
  width: 100%;
  height: 52px;
  padding: 4px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
}

.role-option {
  flex: 1;
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: 11px;
  cursor: pointer;
  user-select: none;
  font-size: 14.5px;
  font-weight: 600;
  color: #64748b;
  transition: color 0.3s ease;
}

.role-option .el-icon {
  font-size: 17px;
}

.role-option.active {
  color: #ffffff;
}

.active-capsule {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 4px;
  width: calc(50% - 4px);
  z-index: 1;
  border-radius: 11px;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  box-shadow: 0 8px 18px -6px rgba(59, 130, 246, 0.55);
  transition: transform 0.38s cubic-bezier(0.65, 0, 0.35, 1);
}

/* ---------- 登录按钮 ---------- */
.submit-item {
  margin-bottom: 6px !important;
}

.submit-item :deep(.el-form-item__content) {
  width: 100%;
}

.auth-submit {
  width: 100%;
  height: 52px;
  border: none;
  border-radius: 14px;
  font-size: 15.5px;
  font-weight: 600;
  letter-spacing: 0.5px;
  color: #ffffff;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
  box-shadow: 0 14px 28px -12px rgba(37, 99, 235, 0.6);
  transition: transform 0.25s ease, box-shadow 0.25s ease, filter 0.25s ease;
}

.auth-submit:hover,
.auth-submit:focus-visible {
  color: #ffffff;
  transform: translateY(-1px);
  filter: brightness(1.06);
  box-shadow: 0 18px 32px -12px rgba(37, 99, 235, 0.7);
}

.auth-submit:active {
  transform: translateY(0);
}

.submit-icon {
  font-size: 17px;
  margin-right: 2px;
}

/* ---------- 底部链接与安全提示 ---------- */
.auth-card-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 22px;
  font-size: 14px;
  color: #64748b;
}

.auth-link {
  font-weight: 600;
}

.security-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 22px;
  padding: 11px 14px;
  border-radius: 12px;
  font-size: 13px;
  color: #92400e;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.22);
}

.security-notice .el-icon {
  flex-shrink: 0;
  font-size: 15px;
  color: #f59e0b;
}

/* ---------- 响应式 ---------- */
@media (max-width: 1024px) {
  .auth-layout {
    flex-direction: column;
  }

  .auth-main {
    padding: 32px 20px 48px;
  }
}

@media (max-width: 640px) {
  .auth-main {
    padding: 24px 14px 40px;
  }

  .auth-card {
    padding: 28px 18px 24px;
    border-radius: 20px;
  }

  .auth-form-title {
    font-size: 22px;
  }
}
</style>
