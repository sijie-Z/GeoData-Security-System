<template>
  <div class="empty-state">
    <div class="empty-icon">
      <el-icon :size="64" color="#c0c4cc">
        <component :is="icon" />
      </el-icon>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-description">{{ description }}</p>
    <slot name="action" />
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
const { t } = useI18n()

defineProps({
  icon: {
    type: [String, Object],
    default: 'DocumentDelete',
  },
  title: {
    type: String,
    default: () => t('common.noData'),
  },
  description: {
    type: String,
    default: () => t('common.noDataDesc'),
  },
});
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: #606266;
  margin: 0 0 8px 0;
}

.empty-description {
  font-size: 14px;
  color: #909399;
  margin: 0 0 24px 0;
  max-width: 320px;
}
</style>
