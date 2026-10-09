<!--
  统一页头（PageHeader）—— 审计系统性观察 2 收口组件。

  背景：原 20 个视图各自复制 .page-header 样式，形成 6 种页头模式
  （无标题 / H1 卡外 / 卡内 / Hero 卡 / 居中 / 标题+副标题），标题字号
  20/24/28/32 混用、内容左缘漂移。本组件收敛为唯一页头结构。

  设计规范（与 design-system.css token 体系一致）：
  - 标题 24px / 600 / var(--text-1)（--font-size-2xl / --font-weight-semibold）
  - 副标题 13px / var(--text-3)（--font-size-sm）
  - 上下留白对齐卡间距节奏：margin-bottom 走 --spacing-lg（桌面 24px，≤768px 自动收窄为 16px）
  - 不含水平缩进：左缘与所在页面内容区（.content-panel padding）自然对齐
  - 深浅双模式全走语义 token；<768px 标题/actions 换行退让
  - 不引入面包屑
-->
<template>
  <div class="page-header" :class="{ 'is-sticky': sticky }">
    <div class="page-header-text">
      <h1 class="page-header-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header-subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.default" class="page-header-actions">
      <slot />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  sticky: { type: Boolean, default: false },
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  margin-bottom: var(--spacing-lg);
}

/* 预留：吸顶页头（本轮无页面启用） */
.page-header.is-sticky {
  position: sticky;
  top: 0;
  z-index: 5;
  padding-block: var(--spacing-sm);
  background-color: var(--bg-primary);
}

.page-header-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  line-height: 1.35;
  color: var(--text-1);
}

.page-header-subtitle {
  margin: var(--spacing-sm) 0 0;
  font-size: var(--font-size-sm);
  line-height: 1.5;
  color: var(--text-3);
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

/* 窄屏（<768px，与移动端壳层断点一致）：actions 换行退让为整行左对齐 */
@media (max-width: 767px) {
  .page-header {
    gap: var(--spacing-sm);
  }

  .page-header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
