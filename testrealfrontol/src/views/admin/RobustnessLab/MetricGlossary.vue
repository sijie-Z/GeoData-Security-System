<!--
  MetricGlossary — 指标词典详解卡（RobustnessLab 专用）
  点说明行 / KPI 卡上的 ⓘ 弹出的详解内容：NC、BER、解码成功三项，各配
  一句话 + 详解文案（i18n，zh/en 成对），NC 附 0.75 / 0.95 刻度阈值色条
  （配色与矩阵单元格一致）。所有颜色只消费 design-system.css 的 CSS 变量名。
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
      <p class="mg-short">{{ $t('robustnessLab.metricNcShort') }}</p>
      <p class="mg-desc">{{ $t('robustnessLab.metricNcDesc') }}</p>
      <div class="mg-bar" aria-hidden="true">
        <span class="mg-seg is-bad" :style="{ flex: 75 }"></span>
        <span class="mg-seg is-mid" :style="{ flex: 20 }"></span>
        <span class="mg-seg is-ok" :style="{ flex: 5 }"></span>
      </div>
      <div class="mg-scale" aria-hidden="true">
        <span>0</span><span>0.75</span><span>0.95</span><span>1</span>
      </div>
      <p class="mg-hint">{{ $t('robustnessLab.metricScaleHint') }}</p>
    </section>

    <section class="mg-item">
      <div class="mg-head">
        <span class="mg-name">
          <span class="mg-code">BER</span>
          {{ $t('robustnessLab.metricBerName') }}
        </span>
        <span class="mg-range">0 ~ 0.5</span>
      </div>
      <p class="mg-short">{{ $t('robustnessLab.metricBerShort') }}</p>
      <p class="mg-desc">{{ $t('robustnessLab.metricBerDesc') }}</p>
    </section>

    <section class="mg-item">
      <div class="mg-head">
        <span class="mg-name">{{ $t('robustnessLab.metricDecodeName') }}</span>
        <span class="mg-range">✓ / ✗</span>
      </div>
      <p class="mg-short">{{ $t('robustnessLab.metricDecodeShort') }}</p>
      <p class="mg-desc">{{ $t('robustnessLab.metricDecodeDesc') }}</p>
    </section>
  </div>
</template>

<script setup></script>

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
</style>
