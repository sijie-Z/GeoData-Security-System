<template>
  <div
    class="empty-2col"
    :class="[`is-${variant}`, { 'is-compact': compact }]"
    role="status"
  >
    <div class="empty-2col__text">
      <p class="empty-2col__title">{{ title }}</p>
      <p v-if="description" class="empty-2col__desc">{{ description }}</p>
      <el-button
        v-if="ctaText"
        class="empty-2col__cta"
        type="primary"
        plain
        size="small"
        @click="$emit('cta')"
      >
        {{ ctaText }}
      </el-button>
    </div>
    <div class="empty-2col__art" aria-hidden="true">
      <slot name="art">
        <svg class="empty-2col__svg" viewBox="0 0 120 96" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="17" y="16" width="86" height="64" rx="8" stroke="currentColor" stroke-width="1.5" stroke-dasharray="5 4" />
          <path d="M34 64l15-18 10 12 9-10 18 20" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          <circle cx="45" cy="34" r="5" stroke="currentColor" stroke-width="1.5" />
        </svg>
      </slot>
    </div>
  </div>
</template>

<script setup>
/**
 * §4.14 空态升级：两栏结构（左说明+CTA，右单色线性插画，stroke 1.5 / currentColor）。
 * variant 由调用方依据"真状态"传入：
 *   never    = 从未有过数据（接口 total 为 0 且无筛选条件）
 *   filtered = 筛选 / 搜索后为空
 */
defineProps({
  title: { type: String, default: '' },
  description: { type: String, default: '' },
  ctaText: { type: String, default: '' },
  variant: { type: String, default: 'never' },
  compact: { type: Boolean, default: false },
})
defineEmits(['cta'])
</script>

<style scoped>
.empty-2col {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  align-items: center;
  gap: 24px;
  padding: 28px 24px;
  color: var(--text-tertiary);
}

.empty-2col.is-compact {
  gap: 16px;
  padding: 18px 20px;
}

.empty-2col__title {
  margin: 0 0 6px;
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-secondary);
}

.empty-2col__desc {
  margin: 0 0 12px;
  font-size: var(--font-size-sm);
  line-height: var(--line-height-body);
  color: var(--text-tertiary);
}

.empty-2col__cta {
  margin-top: 2px;
}

.empty-2col__art {
  display: flex;
  justify-content: center;
  color: var(--text-placeholder);
}

.empty-2col__svg {
  width: 120px;
  height: 96px;
}

.is-compact .empty-2col__svg {
  width: 84px;
  height: 68px;
}

.is-filtered .empty-2col__desc {
  color: var(--text-placeholder);
}
</style>
