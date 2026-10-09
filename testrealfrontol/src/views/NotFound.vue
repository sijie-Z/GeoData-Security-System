<!--
  404 兜底页：router catch-all 的目标（任何未匹配路径）。
  轻量单页：设计系统 token、深浅双模式自动适配；
  i18n：notFound.message / notFound.backHome（zh/en 成对）；
  语义：整页恰一个主标题（h1 = 404）。
-->
<template>
  <div class="not-found">
    <h1 class="nf-code">404</h1>
    <p class="nf-message">{{ $t('notFound.message') }}</p>
    <el-button type="primary" size="large" class="nf-home" @click="goHome">
      {{ $t('notFound.backHome') }}
    </el-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
const goHome = () => router.push('/')
</script>

<style scoped>
.not-found {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-xl);
  background: var(--bg-canvas);
  text-align: center;
}

.nf-code {
  margin: 0;
  font-size: 120px;
  font-weight: var(--font-weight-semibold);
  line-height: 1;
  letter-spacing: 0.02em;
  color: var(--primary-500);
}

.nf-message {
  margin: 0;
  font-size: var(--font-size-lg);
  color: var(--text-3);
}

.nf-home {
  margin-top: var(--spacing-sm);
}
</style>
