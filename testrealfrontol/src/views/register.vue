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
        <section class="auth-card auth-card-register">
          <header class="auth-card-header">
            <h2 class="auth-form-title">
              {{ $t('register.title') }}
            </h2>
            <p class="auth-form-subtitle">
              {{ $t('register.subtitle') }}
            </p>
          </header>

          <el-form
            ref="elFormRef"
            :model="data"
            :rules="rules"
            label-position="top"
            status-icon
            class="auth-form"
          >
            <el-form-item
              :label="$t('register.avatar')"
              prop="avatar"
              class="avatar-item"
            >
              <div class="avatar-upload-section">
                <div
                  class="avatar-preview"
                  @click="triggerFileInput"
                >
                  <img
                    v-if="data.avatarUrl"
                    :src="data.avatarUrl"
                    :alt="$t('register.avatarPreview')"
                    class="avatar-image"
                  >
                  <div
                    v-else
                    class="avatar-placeholder"
                  >
                    <el-icon
                      size="30"
                      color="#94a3b8"
                    >
                      <User />
                    </el-icon>
                    <span class="avatar-text">{{ $t('register.avatarUpload') }}</span>
                  </div>
                  <div class="avatar-overlay">
                    <el-icon
                      color="white"
                      size="20"
                    >
                      <Camera />
                    </el-icon>
                    <span>{{ $t('register.avatarChange') }}</span>
                  </div>
                </div>
                <div class="avatar-tips">
                  <el-text
                    type="info"
                    size="small"
                  >
                    {{ $t('register.avatarTip') }}
                  </el-text>
                </div>
                <input
                  ref="fileInput"
                  type="file"
                  accept="image/*"
                  style="display: none"
                  @change="handleAvatarChange"
                >
              </div>
            </el-form-item>

            <!-- 分组：个人信息 -->
            <div class="form-group-title">
              <el-icon><User /></el-icon>
              <span>{{ $t('register.groupPersonal') }}</span>
            </div>

            <el-form-item
              :label="$t('register.nameLabel')"
              prop="name"
            >
              <el-input
                v-model="data.name"
                :placeholder="$t('register.namePlaceholder')"
                :prefix-icon="User"
                class="auth-input"
              />
            </el-form-item>

            <el-form-item
              :label="$t('register.idNumberLabel')"
              prop="idNumber"
            >
              <el-input
                v-model="data.idNumber"
                :placeholder="$t('register.idNumberPlaceholder')"
                :prefix-icon="CreditCard"
                class="auth-input"
              />
            </el-form-item>

            <el-form-item
              :label="$t('register.phoneLabel')"
              prop="phone"
            >
              <el-input
                v-model="data.phone"
                :placeholder="$t('register.phonePlaceholder')"
                :prefix-icon="Phone"
                class="auth-input"
              />
            </el-form-item>

            <!-- 分组：账号信息 -->
            <div class="form-group-title">
              <el-icon><Key /></el-icon>
              <span>{{ $t('register.groupAccount') }}</span>
            </div>

            <el-form-item
              :label="$t('register.employeeIdLabel')"
              prop="employeeId"
            >
              <el-input
                v-model="data.employeeId"
                :placeholder="$t('register.employeeIdPlaceholder')"
                :prefix-icon="Key"
                class="auth-input"
              />
            </el-form-item>

            <el-form-item
              :label="$t('register.passwordLabel')"
              prop="password"
            >
              <el-input
                v-model="data.password"
                show-password
                :placeholder="$t('register.passwordPlaceholder')"
                :prefix-icon="Lock"
                class="auth-input"
              />
            </el-form-item>

            <el-form-item
              :label="$t('register.confirmPasswordLabel')"
              prop="confirmPassword"
            >
              <el-input
                v-model="data.confirmPassword"
                show-password
                :placeholder="$t('register.confirmPasswordPlaceholder')"
                :prefix-icon="Lock"
                class="auth-input"
              />
            </el-form-item>

            <el-form-item class="submit-item">
              <el-button
                class="auth-submit"
                :loading="loading"
                @click="register"
              >
                <el-icon
                  v-if="!loading"
                  class="submit-icon"
                >
                  <CircleCheck />
                </el-icon>
                {{ $t('register.createButton') }}
              </el-button>
            </el-form-item>
          </el-form>

          <div class="auth-card-footer">
            <span class="login-text">{{ $t('register.hasAccount') }}</span>
            <el-link
              type="primary"
              :underline="false"
              class="auth-link"
              @click="login"
            >
              {{ $t('register.loginNow') }}
            </el-link>
          </div>

          <!-- 服务保障 -->
          <div class="trust-row">
            <span class="trust-item"><el-icon color="#67C23A"><Check /></el-icon>{{ $t('register.featureSecure') }}</span>
            <span class="trust-item"><el-icon color="#67C23A"><Check /></el-icon>{{ $t('register.featureService') }}</span>
            <span class="trust-item"><el-icon color="#67C23A"><Check /></el-icon>{{ $t('register.featureSupport') }}</span>
          </div>
        </section>
      </main>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';
import { post } from '@/utils/Axios';
import { User, Key, CreditCard, Phone, Lock, CircleCheck, Camera, Check } from '@element-plus/icons-vue';
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue';
import AuthBrandPanel from '@/components/common/AuthBrandPanel.vue';

const { t } = useI18n();
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
  name: [{ required: true, message: () => t('register.nameRequired'), trigger: 'blur' }],
  employeeId: [{ required: true, message: () => t('register.employeeIdRequired'), trigger: 'blur' }],
  idNumber: [{ required: true, message: () => t('register.idNumberRequired'), trigger: 'blur' }],
  phone: [{ required: true, message: () => t('register.phoneRequired'), trigger: 'blur' }],
  password: [{ required: true, message: () => t('register.passwordRequired'), trigger: 'blur' }],
  confirmPassword: [{ required: true, message: () => t('register.confirmPasswordRequired'), trigger: 'blur' }]
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
    ElMessage.error(t('register.avatarFormatError'));
    return;
  }

  // 验证文件大小
  const maxSize = 2 * 1024 * 1024; // 2MB
  if (file.size > maxSize) {
    ElMessage.error(t('register.avatarSizeError'));
    return;
  }

  // 读取文件并显示预览
  const reader = new FileReader();
  reader.onload = (e) => {
    data.avatarUrl = e.target.result;
    data.avatar = file;
    ElMessage.success(t('register.avatarUploadSuccess'));
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

    ElMessage.success(response.message + "，" + t('register.pleaseLogin'));
    router.push('/login');
  } catch (err) {
    console.error('注册请求失败:', err);
    ElMessage.error(t('register.registerFailed') + (err.response?.data?.message || t('common.unknown')));
  } finally {
    loading.value = false;
  }
};

const login = () => { router.push('/login'); };
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

.auth-card-register {
  max-width: 500px;
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: none; }
}

.auth-card-header {
  margin-bottom: 26px;
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

/* ---------- 输入框与校验态 ---------- */
.auth-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.auth-form :deep(.el-form-item__label) {
  padding-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  line-height: 1.4;
}

.auth-form :deep(.auth-input .el-input__wrapper) {
  height: 50px;
  border-radius: 13px;
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
  font-size: 16px;
}

/* 浅色卡片在两种页面主题下保持同一体系：钉住输入文字色，
   避免深色主题继承 --el-text-color-regular（#a0a0ab 在浅底上仅 ≈2.5:1） */
.auth-form :deep(.auth-input .el-input__inner) {
  color: #0f172a;
}

/* 占位符同属浅色卡片体系：钉到 slate 深灰（#5b6b80），
   最差（静止态 #f8fafc 底）对比 ≈5.3:1，两种主题下均稳定过 AA
   （浅色默认 token #8f8f8f 在 #f8fafc 上仅 ≈3.1:1） */
.auth-form :deep(.auth-input .el-input__inner::placeholder) {
  color: #5b6b80;
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

/* 校验态：成功绿 / 错误红 */
.auth-form :deep(.el-form-item.is-success .auth-input .el-input__wrapper) {
  box-shadow: 0 0 0 1px #10b981 inset;
}

.auth-form :deep(.el-form-item.is-error .auth-input .el-input__wrapper) {
  box-shadow: 0 0 0 1px #ef4444 inset;
}

.auth-form :deep(.el-form-item__error) {
  padding-top: 4px;
  font-size: 12px;
  color: #ef4444;
}

/* ---------- 分组标题 ---------- */
.form-group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 18px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #1d4ed8;
}

.form-group-title .el-icon {
  font-size: 15px;
}

.form-group-title::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.35), transparent);
}

/* ---------- 头像上传 ---------- */
.avatar-item {
  margin-bottom: 10px !important;
}

.avatar-item :deep(.el-form-item__content) {
  justify-content: center;
}

.avatar-upload-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.avatar-preview {
  position: relative;
  width: 92px;
  height: 92px;
  border-radius: 50%;
  border: 2px dashed #cbd5e1;
  background: #f8fafc;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
}

.avatar-preview:hover {
  border-color: #3b82f6;
  box-shadow: 0 0 0 5px rgba(59, 130, 246, 0.12);
  transform: translateY(-1px);
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
  gap: 4px;
  /* axe color-contrast: #94a3b8 on #f8fafc = 2.45:1; #5b6b7d = 5.22:1.
     Fixed color (not var(--text-3)) because this page's surfaces are hardcoded
     light and --text-3 flips to a light value under html.dark. */
  color: #5b6b7d;
}

.avatar-text {
  font-size: 11px;
  line-height: 1.3;
  padding: 0 8px;
  text-align: center;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #ffffff;
  font-size: 12px;
  background: rgba(15, 23, 42, 0.55);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.avatar-preview:hover .avatar-overlay {
  opacity: 1;
}

.avatar-tips {
  text-align: center;
}

/* axe color-contrast: EP info text #909399 on white = 3.07:1; #5b6b7d = 5.46:1.
   Fixed color for the same hardcoded-light-surface reason as .avatar-placeholder. */
.avatar-tips :deep(.el-text) {
  color: #5b6b7d;
}

/* ---------- 提交按钮 ---------- */
.submit-item {
  margin: 24px 0 6px !important;
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

/* ---------- 底部链接与服务保障 ---------- */
.auth-card-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 20px;
  font-size: 14px;
  color: #64748b;
}

.auth-link {
  font-weight: 600;
}

.trust-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px 18px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid #f1f5f9;
}

.trust-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12.5px;
  color: #64748b;
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

  .trust-row {
    gap: 8px 12px;
  }
}
</style>
