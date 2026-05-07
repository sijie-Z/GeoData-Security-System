<template>
  <el-dropdown @command="handleSwitch" trigger="click">
    <el-button text>
      <el-icon><Switch /></el-icon>
      <span style="margin-left: 4px">{{ currentLabel }}</span>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="zh-CN" :class="{ active: locale === 'zh-CN' }">
          中文
        </el-dropdown-item>
        <el-dropdown-item command="en-US" :class="{ active: locale === 'en-US' }">
          English
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale } from '@/locales/index.js'

const { locale } = useI18n()

const currentLabel = computed(() => {
  return locale.value === 'zh-CN' ? '中文' : 'English'
})

function handleSwitch(lang) {
  setLocale(lang)
  // Reload to apply Element Plus locale change
  window.location.reload()
}
</script>

<style scoped>
.active {
  color: var(--el-color-primary);
  font-weight: 600;
}
</style>
