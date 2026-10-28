<template>
  <div class="delivery-chain">
    <div
      v-for="(row, i) in rows"
      :key="row.key"
      class="dc-row"
      :class="[`is-${row.status}`, { 'is-hl': highlight === row.key }]"
      role="button"
      tabindex="0"
      @click="$emit('select', row.key)"
      @keydown.enter.prevent="$emit('select', row.key)"
      @keydown.space.prevent="$emit('select', row.key)"
    >
      <!-- 左：操作树 -->
      <div class="dc-tree">
        <span class="dc-node" />
        <span
          v-if="i < rows.length - 1"
          class="dc-line"
          :class="{ 'is-broken': row.status === 'missing' }"
        />
      </div>

      <!-- 右：水位条 -->
      <div class="dc-body">
        <div class="dc-head">
          <span class="dc-label">{{ row.label }}</span>
          <span class="dc-ts tnum-id">{{ row.tsLabel }}</span>
          <span class="dc-dur tnum-id">{{ row.durationLabel }}</span>
        </div>
        <div class="dc-track">
          <div
            v-if="row.status === 'done'"
            class="dc-bar"
            :class="{ 'is-first': i === 0 }"
            :style="{ left: row.left + '%', width: row.width + '%' }"
          />
          <div
            v-else-if="row.status === 'missing'"
            class="dc-bar is-missing"
            :style="{ left: row.left + '%' }"
          />
          <div
            v-else-if="row.status === 'pending'"
            class="dc-bar is-pending"
            :style="{ left: row.left + '%' }"
          />
        </div>
        <div
          v-if="row.status === 'missing'"
          class="dc-missing"
        >
          {{ $t('common.deliveryChain.missing') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

/**
 * §5.16 分发链水位图（Sentry 风格）：
 * 左操作树（申请→审批→交付→下载…），右侧每步时长条；
 * 时间戳缺失的步骤以虚线占位（断链可见）；点击节点 emit select 供调用方高亮/分享。
 *
 * steps: [{ key, label, ts: ISO string | null, status?: 'done'|'missing'|'pending' }]
 *   - status 缺省时按 ts 是否存在推断：有 ts → done，无 ts → missing
 */
const props = defineProps({
  steps: { type: Array, default: () => [] },
  highlight: { type: String, default: '' },
})
defineEmits(['select'])

const { t } = useI18n()

const toMs = (iso) => {
  if (!iso) return null
  const ms = Date.parse(iso)
  return Number.isNaN(ms) ? null : ms
}

const fmtTs = (iso) => {
  if (!iso) return '—'
  const ms = Date.parse(iso)
  if (Number.isNaN(ms)) return '—'
  const d = new Date(ms)
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const fmtDur = (ms) => {
  if (ms == null || ms < 0) return ''
  if (ms < 1000) return `${ms}ms`
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m${s % 60 ? ` ${s % 60}s` : ''}`
  const h = Math.floor(m / 60)
  const d = Math.floor(h / 24)
  if (d > 0) return `${d}d ${h % 24}h`
  return `${h}h ${m % 60}m`
}

const rows = computed(() => {
  const items = props.steps.map((s) => {
    const ms = toMs(s.ts)
    const status = s.status || (ms != null ? 'done' : 'missing')
    return { ...s, ms, status }
  })

  const known = items.filter((i) => i.ms != null).map((i) => i.ms)
  const t0 = known.length ? Math.min(...known) : 0
  const t1 = known.length ? Math.max(...known) : 1
  const span = Math.max(t1 - t0, 1)

  // 每步时长 = 与前一个"有时间戳"步骤的差
  let prevMs = null

  return items.map((item, idx) => {
    let durationLabel = ''
    if (item.ms != null && prevMs != null) {
      durationLabel = fmtDur(item.ms - prevMs)
    }
    const startMs = (idx === 0 || item.ms == null) ? item.ms : (prevMs ?? item.ms)
    if (item.ms != null) prevMs = item.ms

    const left = startMs != null ? Math.min(98, ((startMs - t0) / span) * 100) : 0
    const width = durationLabel && item.ms != null && startMs != null
      ? Math.max(2, ((item.ms - startMs) / span) * 100)
      : 0

    return {
      key: item.key,
      label: item.label,
      status: item.status,
      tsLabel: item.ms != null ? fmtTs(item.ts) : '—',
      durationLabel: item.status === 'done' ? (durationLabel || t('common.deliveryChain.startPoint')) : '',
      left: Math.round(left * 10) / 10,
      width: Math.round(width * 10) / 10,
    }
  })
})
</script>

<style scoped>
.delivery-chain {
  display: flex;
  flex-direction: column;
}

.dc-row {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  align-items: stretch;
  cursor: pointer;
  border-radius: var(--radius-md);
  padding: 2px 6px 2px 0;
  transition: background-color var(--duration-150) var(--ease-out-soft);
}

.dc-row:hover,
.dc-row:focus-visible {
  background: var(--bg-hover);
  outline: none;
}

.dc-row.is-hl {
  background: var(--tint-info-bg);
  box-shadow: inset 2px 0 0 var(--accent-9);
}

/* 左操作树 */
.dc-tree {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.dc-node {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-top: 12px;
  background: var(--accent-9);
  box-shadow: 0 0 0 3px var(--bg-surface);
  flex: none;
  z-index: 1;
}

.is-missing .dc-node {
  background: transparent;
  border: 1.5px dashed var(--text-placeholder);
}

.is-pending .dc-node {
  background: var(--text-placeholder);
}

.dc-line {
  width: 0;
  flex: 1;
  border-left: 1.5px solid var(--border-strong);
}

.dc-line.is-broken {
  border-left-style: dashed;
  border-left-color: var(--text-placeholder);
}

/* 右水位区 */
.dc-body {
  padding: 8px 0 10px 10px;
  min-width: 0;
}

.dc-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.dc-label {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--text-1);
  flex: none;
}

.dc-ts {
  font-size: var(--font-size-xs);
  color: var(--text-2);
  flex: none;
}

.dc-dur {
  font-size: var(--font-size-xs);
  color: var(--text-3);
  margin-left: auto;
  flex: none;
}

.dc-track {
  position: relative;
  height: 10px;
  margin-top: 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-inset);
  overflow: hidden;
}

.dc-bar {
  position: absolute;
  top: 0;
  height: 100%;
  min-width: 3px;
  border-radius: var(--radius-sm);
  background: linear-gradient(90deg, var(--accent-9), var(--accent-10));
}

.dc-bar.is-first {
  background: var(--border-strong);
}

/* 缺失：虚线断链条 */
.dc-bar.is-missing {
  width: 14%;
  background: transparent;
  border: 1.5px dashed var(--text-placeholder);
  border-radius: var(--radius-sm);
  box-sizing: border-box;
}

.dc-bar.is-pending {
  width: 6%;
  background: var(--text-placeholder);
  opacity: 0.5;
}

.dc-missing {
  margin-top: 4px;
  font-size: var(--font-size-xs);
  color: var(--text-placeholder);
}

.is-hl .dc-label {
  color: var(--accent-9);
}
</style>
