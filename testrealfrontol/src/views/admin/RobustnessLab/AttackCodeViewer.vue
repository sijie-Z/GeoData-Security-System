<!--
  AttackCodeViewer — 攻击源码语法高亮查看器（RobustnessLab 源码抽屉内）
  · 语法高亮：highlight.js core + python 语言包按需注册（不引全量包 / shiki）；
  · 行号 + 行锚点：每行 id="L{n}"，点击行号把 #L{n} 写入地址栏（URL hash 可分享）；
  · 打开抽屉时地址栏若带 #L{n}，自动滚动定位并高亮该行；
  · 配色只消费 design-system.css 的 CSS 变量（深浅主题自动切换，不写死色值）。
-->
<template>
  <div ref="root" class="code-viewer" :style="{ '--cv-gutter-ch': gutterCh }">
    <div
      v-for="(line, i) in lines"
      :id="`L${i + 1}`"
      :key="i"
      class="cv-line"
      :class="{ 'is-target': targetLine === i + 1 }"
    >
      <a
        class="cv-lineno"
        :href="`#L${i + 1}`"
        :title="$t('robustnessLab.codeAnchorHint')"
        @click.prevent="jumpToLine(i + 1)"
        >{{ i + 1 }}</a
      >
      <code class="cv-code" v-html="line"></code>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import hljs from 'highlight.js/lib/core'
import python from 'highlight.js/lib/languages/python'

hljs.registerLanguage('python', python)

const props = defineProps({
  // 攻击函数源码（后端 inspect.getsource 原样返回）
  code: { type: String, default: '' },
})

const root = ref(null)
const targetLine = ref(null)

/**
 * 按行切分 highlight.js 输出：多行字符串 / 注释的 <span> 会跨行，
 * 在换行处闭合再重开（维护未闭合标签栈），保证每行 HTML 平衡可 v-html。
 */
const splitHighlightedLines = (html) => {
  const lines = []
  const stack = []
  const closeTags = () => stack.map(() => '</span>').join('')
  const openTags = () => stack.map((cls) => (cls ? `<span class="${cls}">` : '<span>')).join('')
  let current = ''
  const re = /(<span[^>]*>)|(<\/span>)|([^<]+)|(<[^>]*>)/g
  let m
  while ((m = re.exec(html)) !== null) {
    if (m[1]) {
      const cls = /class="([^"]*)"/.exec(m[1])
      stack.push(cls ? cls[1] : '')
      current += m[1]
    } else if (m[2]) {
      stack.pop()
      current += m[2]
    } else {
      const text = m[3] ?? m[4] ?? ''
      const parts = text.split('\n')
      for (let i = 0; i < parts.length; i += 1) {
        if (i > 0) {
          lines.push(current + closeTags())
          current = openTags()
        }
        current += parts[i]
      }
    }
  }
  lines.push(current + closeTags())
  return lines
}

const lines = computed(() => {
  const code = props.code || ''
  let html
  try {
    html = hljs.highlight(code, { language: 'python', ignoreIllegals: true }).value
  } catch {
    // 高亮失败时退化为纯文本转义（不再抛错）
    html = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  }
  return splitHighlightedLines(html)
})

const gutterCh = computed(() => Math.max(2, String(lines.value.length).length) + 1)

const scrollToLine = (n) => {
  nextTick(() => {
    const el = root.value?.querySelector(`#L${n}`)
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ block: 'center' })
    }
  })
}

// 点击行号：写地址栏 hash（可分享该行定位）并滚动到该行
const jumpToLine = (n) => {
  targetLine.value = n
  try {
    window.history.replaceState(null, '', `#L${n}`)
  } catch {
    // 沙箱 / 特殊协议下 replaceState 不可用：仅本地滚动
  }
  scrollToLine(n)
}

// 打开抽屉时自动定位：地址栏 #L42 -> 滚动到底 42 行并高亮
onMounted(() => {
  const m = /^#L(\d+)$/.exec(window.location.hash || '')
  if (!m) return
  const n = Number(m[1])
  if (n >= 1 && n <= lines.value.length) {
    targetLine.value = n
    scrollToLine(n)
  }
})
</script>

<style scoped>
.code-viewer {
  margin: 0;
  padding: 10px 0;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
}

.cv-line {
  display: flex;
  align-items: flex-start;
  min-height: 19px;
}

.cv-lineno {
  flex: 0 0 auto;
  width: calc(var(--cv-gutter-ch, 3) * 1ch);
  padding: 0 10px 0 6px;
  text-align: right;
  color: var(--text-tertiary);
  text-decoration: none;
  user-select: none;
  /* 横向滚动时行号列吸附在左侧 */
  position: sticky;
  left: 0;
  background: var(--bg-tertiary);
}

.cv-lineno:hover {
  color: var(--primary-600);
}

.cv-code {
  flex: 1 1 auto;
  padding-right: 14px;
  white-space: pre;
  font: inherit;
}

/* 行锚点高亮（点击行号 / 打开抽屉时命中 #L{n}） */
.cv-line.is-target {
  background: var(--primary-50);
}

.cv-line.is-target .cv-lineno {
  background: var(--primary-50);
  color: var(--primary-600);
  font-weight: 600;
}

/* ── 语法高亮配色（hljs token -> design-system 变量，深浅主题自动切换） ── */
:deep(.hljs-keyword),
:deep(.hljs-built_in),
:deep(.hljs-type) {
  color: var(--primary-600);
}

:deep(.hljs-string),
:deep(.hljs-meta .hljs-string) {
  color: var(--tint-success-text);
}

:deep(.hljs-comment),
:deep(.hljs-quote) {
  color: var(--text-tertiary);
  font-style: italic;
}

:deep(.hljs-number),
:deep(.hljs-literal) {
  color: var(--tint-warning-text);
}

:deep(.hljs-title),
:deep(.hljs-function .hljs-title) {
  color: var(--primary-700);
}

:deep(.hljs-attr),
:deep(.hljs-variable),
:deep(.hljs-params) {
  color: var(--tint-info-text);
}

:deep(.hljs-meta) {
  color: var(--text-tertiary);
}
</style>
