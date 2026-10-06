<!--
  水印/二维码图片统一展示组件
  小白解释：页面上所有水印、二维码缩略图都用这个组件显示。点击图片即可放大预览。
  关键点：
  1) preview-teleported 把放大预览层传送到 <body> 上渲染，不会被表格单元格（<td>）
     的层叠上下文困住、被其它行或固定列遮挡——这是"点小图没反应"的根因修复。
  2) 老二维码原图只有一两百像素，直接点开放大仍是模糊小图；组件会在 src 变化时用
     离屏 Image + canvas 以最近邻（nearest-neighbor）整数倍超采样到短边 ≥800（上限 8×），
     仅用于放大预览（thumbnail 的 :src 保持原图不变）。最近邻不会糊掉二维码模块边缘，
     更利于查看；≥800 的大图（如 890px 的 v16 QR）原样使用，不做处理。
-->
<template>
  <el-image
    class="wm-preview-image"
    :src="src"
    :preview-src-list="previewSrc ? [previewSrc] : []"
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
import { ref, watch } from 'vue'
import { Picture } from '@element-plus/icons-vue'

const props = defineProps({
  // 图片地址：data URI 或普通 URL；为空时既显示占位图标，也不会打开空预览
  src: { type: String, default: '' },
  // 同 el-image 的 fit（cover / contain / fill 等）
  fit: { type: String, default: 'cover' },
  // 透传给 el-image 容器的尺寸样式，例如 style="width: 50px; height: 50px;"
  style: { type: [String, Object], default: '' }
})

// 预览专用地址：小图经最近邻超采样后的 PNG data URI；thumbnail 的 :src 仍用原图
const previewSrc = ref('')
let loadToken = 0 // 并发保护：src 连续变化时只采纳最后一次加载的结果

const TARGET_SHORT_SIDE = 800 // 预览短边目标像素
const MAX_SCALE = 8           // 放大倍数上限

/**
 * 用离屏 Image 加载原图；若短边 < TARGET_SHORT_SIDE，用 canvas 最近邻整数倍放大到
 * 短边 ≥800（倍数上限 MAX_SCALE），输出 PNG data URI 供预览。
 * data URI 画 canvas 无 CORS 问题；任何失败（加载失败 / 画布被污染 / 环境不支持）
 * 都回退为原图，保证预览始终可用。
 */
const buildPreviewSrc = (rawSrc, token) => {
  const image = new Image()
  image.onload = () => {
    if (token !== loadToken) return // src 已变化，丢弃过期结果
    try {
      const w = image.naturalWidth || image.width
      const h = image.naturalHeight || image.height
      const shortSide = Math.min(w, h)
      if (!w || !h || shortSide >= TARGET_SHORT_SIDE) {
        previewSrc.value = rawSrc // 原图已足够大，原样使用
        return
      }
      const scale = Math.min(Math.ceil(TARGET_SHORT_SIDE / shortSide), MAX_SCALE)
      const canvas = document.createElement('canvas')
      canvas.width = w * scale
      canvas.height = h * scale
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        previewSrc.value = rawSrc
        return
      }
      ctx.imageSmoothingEnabled = false // 最近邻放大，二维码模块边缘保持锐利
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
      previewSrc.value = canvas.toDataURL('image/png')
    } catch (_err) {
      previewSrc.value = rawSrc // 画布不可用（如跨域图片被污染）时回退原图
    }
  }
  image.onerror = () => {
    if (token !== loadToken) return
    previewSrc.value = rawSrc // 加载失败：回退原图
  }
  image.src = rawSrc
}

watch(() => props.src, (val) => {
  const token = ++loadToken
  previewSrc.value = val || ''
  if (val) buildPreviewSrc(val, token)
}, { immediate: true })
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
