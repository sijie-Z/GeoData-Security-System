<template>
  <div class="loading-skeleton" :class="[`skeleton-${variant}`]">
    <div v-if="variant === 'card'" class="skeleton-card">
      <div class="skeleton-image" />
      <div class="skeleton-content">
        <div class="skeleton-title" />
        <div class="skeleton-text" />
        <div class="skeleton-text short" />
      </div>
    </div>

    <div v-else-if="variant === 'table'" class="skeleton-table">
      <div v-for="i in rows" :key="i" class="skeleton-row">
        <div class="skeleton-cell" />
        <div class="skeleton-cell wide" />
        <div class="skeleton-cell" />
      </div>
    </div>

    <div v-else-if="variant === 'list'" class="skeleton-list">
      <div v-for="i in rows" :key="i" class="skeleton-list-item">
        <div class="skeleton-avatar" />
        <div class="skeleton-list-content">
          <div class="skeleton-title" />
          <div class="skeleton-text" />
        </div>
      </div>
    </div>

    <div v-else class="skeleton-block">
      <div v-for="i in rows" :key="i" class="skeleton-line" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'block',
    validator: (v) => ['block', 'card', 'table', 'list'].includes(v),
  },
  rows: {
    type: Number,
    default: 3,
  },
});
</script>

<style scoped>
.loading-skeleton {
  width: 100%;
}

.skeleton-card {
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.skeleton-image {
  width: 100%;
  height: 180px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-content {
  padding: 16px;
}

.skeleton-title {
  height: 20px;
  width: 60%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 12px;
}

.skeleton-text {
  height: 14px;
  width: 100%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 8px;
}

.skeleton-text.short {
  width: 40%;
}

.skeleton-table {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-row {
  display: flex;
  gap: 12px;
}

.skeleton-cell {
  height: 40px;
  flex: 1;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 6px;
}

.skeleton-cell.wide {
  flex: 2;
}

.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-list-item {
  display: flex;
  gap: 12px;
  align-items: center;
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  flex-shrink: 0;
}

.skeleton-list-content {
  flex: 1;
}

.skeleton-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-line {
  height: 16px;
  width: 100%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
