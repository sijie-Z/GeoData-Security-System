<!--
  证据哈希统一展示组件
  小白解释：页面上所有指纹、事件哈希、Merkle 根这类长串哈希都用这个组件显示——
  中间省略、悬浮看全串、点右侧小按钮一键复制。
  关键点：
  1) 显示形态 head…tail 中段省略（默认 8…6，短串不截断），title 悬浮展示完整原串；
  2) 复制优先走 navigator.clipboard（localhost / https 安全上下文可用），失败回退
     textarea + execCommand，两条路都失败才提示"复制失败"；
  3) 空值显示占位符 '—' 且不渲染复制按钮；等宽字体 ui-monospace；颜色/圆角/过渡
     全部复用 design-system.css 变量。
-->
<template>
  <span
    class="hash-text"
    :class="{ 'is-empty': !hasValue }"
    :title="fullText"
  >
    <code class="hash-text__code">{{ display }}</code>
    <button
      v-if="hasValue"
      type="button"
      class="hash-text__copy"
      :title="$t('common.copy')"
      @click.stop="copy"
    >
      <el-icon :size="13"><CopyDocument /></el-icon>
    </button>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'

const props = defineProps({
  // 完整哈希（字符串或数字）
  value: { type: [String, Number], default: '' },
  // 头部保留字符数
  head: { type: Number, default: 8 },
  // 尾部保留字符数
  tail: { type: Number, default: 6 }
})

const { t } = useI18n()

const hasValue = computed(() => props.value !== null && props.value !== undefined && String(props.value).length > 0)
const fullText = computed(() => (hasValue.value ? String(props.value) : ''))

const display = computed(() => {
  if (!hasValue.value) return '—'
  const s = String(props.value)
  const tail = props.tail > 0 ? props.tail : 0
  if (s.length <= props.head + tail + 1) return s // 短串不截断
  const tailPart = tail > 0 ? `…${s.slice(-tail)}` : '…'
  return `${s.slice(0, props.head)}${tailPart}`
})

// 回退方案：老浏览器/非安全上下文没有 navigator.clipboard 时用隐藏 textarea 复制
const fallbackCopy = (text) => {
  try {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.setAttribute('readonly', '')
    ta.style.position = 'fixed'
    ta.style.opacity = '0'
    document.body.appendChild(ta)
    ta.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(ta)
    return ok
  } catch (_err) {
    return false
  }
}

const copy = async () => {
  const text = fullText.value
  if (!text) return
  let ok = false
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      ok = true
    }
  } catch (_err) {
    ok = false
  }
  if (!ok) ok = fallbackCopy(text)
  if (ok) ElMessage.success(t('common.copied'))
  else ElMessage.error(t('common.copyFailed'))
}
</script>

<style scoped>
.hash-text {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  max-width: 100%;
  vertical-align: middle;
}

.hash-text__code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.7;
  letter-spacing: 0.2px;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 0 6px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hash-text.is-empty .hash-text__code {
  color: var(--text-tertiary);
  background: transparent;
  border-color: transparent;
  padding: 0;
}

.hash-text__copy {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-fast), background var(--transition-fast);
}

.hash-text__copy:hover {
  color: var(--primary-600);
  background: var(--primary-50);
}

.hash-text__copy:active {
  transform: scale(0.92);
}
</style>
