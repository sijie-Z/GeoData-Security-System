<!--
  水印/二维码图片统一展示组件
  小白解释：页面上所有水印、二维码缩略图都用这个组件显示。点击图片即可放大预览。
  关键点：preview-teleported 会把放大预览层传送到 <body> 上渲染，
  不会再被表格单元格（<td>）的层叠上下文困住、被其它行或固定列遮挡——
  这正是之前"点小图没反应"的根因。
-->
<template>
  <el-image
    class="wm-preview-image"
    :src="src"
    :preview-src-list="src ? [src] : []"
    preview-teleported
    :hide-on-click-modal="true"
    :fit="fit"
    :style="style"
  >
    <template #error>
      <div class="wm-img-error">
        <el-icon><Picture /></el-icon>
      </div>
    </template>
  </el-image>
</template>

<script setup>
import { Picture } from '@element-plus/icons-vue'

defineProps({
  // 图片地址：data URI 或普通 URL；为空时既显示占位图标，也不会打开空预览
  src: { type: String, default: '' },
  // 同 el-image 的 fit（cover / contain / fill 等）
  fit: { type: String, default: 'cover' },
  // 透传给 el-image 容器的尺寸样式，例如 style="width: 50px; height: 50px;"
  style: { type: [String, Object], default: '' }
})
</script>

<style scoped>
.wm-img-error {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-width: 24px;
  min-height: 24px;
  background: #f5f7fa;
  color: #c0c4cc;
  font-size: 20px;
  border-radius: 4px;
}
</style>
