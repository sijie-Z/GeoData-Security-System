<!--
  MetricGlossary — 指标词典详解卡（RobustnessLab 专用）
  点说明行 / KPI 卡上的 ⓘ 弹出的详解内容：NC、BER、解码成功三项，各配
  一句话 + 详解文案（i18n，zh/en 成对），NC 附 0.75 / 0.95 刻度阈值色条
  （配色与矩阵单元格一致）。每条指标附「查看文档」入口 → 侧边文档抽屉
  （定义 / 怎么读 / 阈值口径 / 来源与局限，内容基线取本卡与
  WatermarkQuality GlossaryHelp 的既有文案，zh/en 成对）。
  所有颜色只消费 design-system.css 的 CSS 变量名。
-->
<template>
  <div class="metric-glossary">
    <section class="mg-item">
      <div class="mg-head">
        <span class="mg-name">
          <span class="mg-code">NC</span>
          {{ $t('robustnessLab.metricNcName') }}
        </span>
        <span class="mg-range">0 ~ 1</span>
      </div>
      <p class="mg-short">
        {{ $t('robustnessLab.metricNcShort') }}
      </p>
      <p class="mg-desc">
        {{ $t('robustnessLab.metricNcDesc') }}
      </p>
      <div
        class="mg-bar"
        aria-hidden="true"
      >
        <span
          class="mg-seg is-bad"
          :style="{ flex: 75 }"
        />
        <span
          class="mg-seg is-mid"
          :style="{ flex: 20 }"
        />
        <span
          class="mg-seg is-ok"
          :style="{ flex: 5 }"
        />
      </div>
      <div
        class="mg-scale"
        aria-hidden="true"
      >
        <span>0</span><span>0.75</span><span>0.95</span><span>1</span>
      </div>
      <p class="mg-hint">
        {{ $t('robustnessLab.metricScaleHint') }}
      </p>
      <div class="mg-doc-row">
        <el-button
          text
          size="small"
          type="primary"
          @click="openDoc('nc')"
        >
          {{ $t('robustnessLab.metricDocBtn') }}
        </el-button>
      </div>
    </section>

    <section class="mg-item">
      <div class="mg-head">
        <span class="mg-name">
          <span class="mg-code">BER</span>
          {{ $t('robustnessLab.metricBerName') }}
        </span>
        <span class="mg-range">0 ~ 0.5</span>
      </div>
      <p class="mg-short">
        {{ $t('robustnessLab.metricBerShort') }}
      </p>
      <p class="mg-desc">
        {{ $t('robustnessLab.metricBerDesc') }}
      </p>
      <div class="mg-doc-row">
        <el-button
          text
          size="small"
          type="primary"
          @click="openDoc('ber')"
        >
          {{ $t('robustnessLab.metricDocBtn') }}
        </el-button>
      </div>
    </section>

    <section class="mg-item">
      <div class="mg-head">
        <span class="mg-name">{{ $t('robustnessLab.metricDecodeName') }}</span>
        <span class="mg-range">✓ / ✗</span>
      </div>
      <p class="mg-short">
        {{ $t('robustnessLab.metricDecodeShort') }}
      </p>
      <p class="mg-desc">
        {{ $t('robustnessLab.metricDecodeDesc') }}
      </p>
      <div class="mg-doc-row">
        <el-button
          text
          size="small"
          type="primary"
          @click="openDoc('decode')"
        >
          {{ $t('robustnessLab.metricDocBtn') }}
        </el-button>
      </div>
    </section>

    <!-- 指标文档抽屉：定义 / 怎么读 / 阈值口径 / 来源与局限 -->
    <el-drawer
      v-model="docOpen"
      direction="rtl"
      size="480px"
      :title="docTitle"
      class="metric-doc-drawer"
    >
      <div class="md-body">
        <section
          v-for="section in docSections"
          :key="section.label"
          class="md-section"
        >
          <h5 class="md-label">
            {{ section.label }}
          </h5>
          <p class="md-text">
            {{ section.text }}
          </p>
        </section>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// 文档抽屉：nc / ber / decode 三个指标，键后缀与 metric{Nc|Ber|Decode}Name 对齐
const METRIC_KEY_SUFFIX = { nc: 'Nc', ber: 'Ber', decode: 'Decode' }
const docMetric = ref('nc')
const docOpen = ref(false)

const openDoc = (key) => {
  if (METRIC_KEY_SUFFIX[key]) docMetric.value = key
  docOpen.value = true
}

const docTitle = computed(() =>
  t('robustnessLab.metricDocDrawerTitle', {
    name: t(`robustnessLab.metric${METRIC_KEY_SUFFIX[docMetric.value]}Name`),
  })
)

const docSections = computed(() => {
  const suffix = METRIC_KEY_SUFFIX[docMetric.value]
  return [
    { label: t('robustnessLab.metricDocDefinitionLabel'), text: t(`robustnessLab.metric${suffix}DocDef`) },
    { label: t('robustnessLab.metricDocReadLabel'), text: t(`robustnessLab.metric${suffix}DocRead`) },
    { label: t('robustnessLab.metricDocThresholdLabel'), text: t(`robustnessLab.metric${suffix}DocThreshold`) },
    { label: t('robustnessLab.metricDocSourceLabel'), text: t(`robustnessLab.metric${suffix}DocSource`) },
  ]
})
</script>

<style scoped>
.metric-glossary {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.mg-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mg-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.mg-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.mg-code {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-600);
  margin-right: 4px;
}

.mg-range {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--text-tertiary);
}

.mg-short {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.mg-desc {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-secondary);
}

/* 阈值色条：0.75 / 0.95 刻度，红 / 黄 / 绿与矩阵单元格同源 */
.mg-bar {
  display: flex;
  gap: 2px;
  height: 8px;
  margin-top: 4px;
  border-radius: var(--radius-full);
  overflow: hidden;
}

.mg-seg {
  display: block;
  height: 100%;
}

.mg-seg.is-bad {
  background: var(--danger-500);
}

.mg-seg.is-mid {
  background: var(--warning-500);
}

.mg-seg.is-ok {
  background: var(--success-500);
}

.mg-scale {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  color: var(--text-tertiary);
}

.mg-hint {
  margin: 0;
  font-size: 11.5px;
  color: var(--text-tertiary);
}

/* 「查看文档」入口行 */
.mg-doc-row {
  display: flex;
  justify-content: flex-end;
  margin-top: -2px;
}

.mg-doc-row .el-button {
  padding: 2px 0;
  font-size: 12px;
}

/* ── 指标文档抽屉（定义 / 怎么读 / 阈值口径 / 来源与局限） ── */
.md-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 16px;
}

.md-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.md-label {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--primary-600);
}

.md-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.75;
  color: var(--text-secondary);
}
</style>
