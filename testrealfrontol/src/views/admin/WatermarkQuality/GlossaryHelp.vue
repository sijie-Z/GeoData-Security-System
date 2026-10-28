<template>
  <!-- ⓘ 指标解释：悬浮出一句话 tooltip，点击弹 420px 详解卡（定义/公式/阈值色条/口径注） -->
  <el-tooltip
    :content="tip"
    placement="top"
    :show-after="150"
    :hide-after="0"
  >
    <span class="glossary-help">
      <el-popover
        trigger="click"
        :width="420"
        placement="bottom-start"
      >
        <template #reference>
          <el-icon
            class="glossary-help__icon"
            :size="14"
          ><InfoFilled /></el-icon>
        </template>

        <div class="glossary-card">
          <div
            v-if="title"
            class="glossary-card__title"
          >{{ title }}</div>
          <p
            v-if="desc"
            class="glossary-card__desc"
          >{{ desc }}</p>

          <div
            v-if="formula"
            class="glossary-card__section"
          >
            <span class="glossary-card__label">{{ formulaLabel }}</span>
            <code class="glossary-card__formula">{{ formula }}</code>
          </div>

          <div
            v-if="scale"
            class="glossary-card__section"
          >
            <span class="glossary-card__label">{{ thresholdLabel }}</span>
            <div class="glossary-scale">
              <div
                class="glossary-scale__bar"
                :style="{ background: scale.gradient }"
              >
                <span
                  v-for="mk in scale.markers"
                  :key="mk.label"
                  class="glossary-scale__tick"
                  :style="{ left: pct(mk.value) + '%' }"
                >
                  <span class="glossary-scale__tag">{{ mk.label }}</span>
                </span>
              </div>
              <div class="glossary-scale__labels">
                <span>{{ scale.labels[0] }}</span>
                <span>{{ scale.labels[1] }}</span>
                <span>{{ scale.labels[2] }}</span>
              </div>
            </div>
          </div>

          <div
            v-if="caveat"
            class="glossary-card__caveat"
          >{{ caveat }}</div>
        </div>
      </el-popover>
    </span>
  </el-tooltip>
</template>

<script setup>
import { InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  // 悬浮一句话
  tip: { type: String, default: '' },
  // 详解卡：标题 / 定义 / 公式 / 口径注
  title: { type: String, default: '' },
  desc: { type: String, default: '' },
  formula: { type: String, default: '' },
  caveat: { type: String, default: '' },
  // 区块标签（复用页面 i18n）
  formulaLabel: { type: String, default: '' },
  thresholdLabel: { type: String, default: '' },
  // 阈值色条：{ gradient, min, max, markers: [{ value, label }], labels: [差, 良, 优] }
  scale: { type: Object, default: null },
})

const pct = (v) => {
  if (!props.scale) return 0
  const { min, max } = props.scale
  return Math.min(100, Math.max(0, ((v - min) / (max - min)) * 100))
}
</script>

<style scoped>
.glossary-help {
  display: inline-flex;
  align-items: center;
  margin-left: 6px;
  vertical-align: middle;
  line-height: 1;
}

.glossary-help__icon {
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color 0.15s ease;
}

.glossary-help__icon:hover {
  color: var(--primary-500);
}

.glossary-card__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.glossary-card__desc {
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-secondary);
  margin: 0 0 10px;
}

.glossary-card__section {
  margin-bottom: 10px;
}

.glossary-card__label {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 4px;
  letter-spacing: 0.02em;
}

.glossary-card__formula {
  display: block;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  white-space: pre-wrap;
  word-break: break-all;
}

.glossary-scale__bar {
  position: relative;
  height: 8px;
  border-radius: var(--radius-full);
  margin: 16px 0 6px;
}

.glossary-scale__tick {
  position: absolute;
  top: -3px;
  width: 2px;
  height: 14px;
  background: var(--bg-primary);
  box-shadow: 0 0 0 1px var(--border-color-hover);
  border-radius: 2px;
}

.glossary-scale__tag {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.glossary-scale__labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--text-tertiary);
}

.glossary-card__caveat {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-tertiary);
  border-top: 1px solid var(--border-color-light);
  padding-top: 8px;
  margin-top: 2px;
}

/* 深色下三级文字在弹层深底（--bg-raised）上仅 ~3.2:1，未达 AA：
   令牌值由 token 线统一调整，本组件深色内提及一级到 --text-2（浅色不动） */
html.dark .glossary-card__label,
html.dark .glossary-scale__tag,
html.dark .glossary-scale__labels,
html.dark .glossary-card__caveat {
  color: var(--text-2);
}
</style>
