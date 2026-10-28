<template>
  <div class="img-compare">
    <!-- 对比舞台（卷帘 / 透明度） -->
    <div
      v-if="mode !== 'side'"
      class="img-compare__stage"
      :style="{ height }"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointerleave="onPointerUp"
    >
      <img
        v-if="afterSrc"
        :src="afterSrc"
        class="img-compare__img"
        :alt="afterLabel"
        draggable="false"
      >
      <div
        v-if="beforeSrc"
        class="img-compare__clip"
        :style="mode === 'wipe'
          ? { clipPath: `inset(0 ${100 - position}% 0 0)` }
          : { opacity: position / 100 }"
      >
        <img
          :src="beforeSrc"
          class="img-compare__img"
          :alt="beforeLabel"
          draggable="false"
        >
      </div>

      <!-- 卷帘把手（role=slider，键盘可达） -->
      <template v-if="mode === 'wipe' && beforeSrc">
        <div
          class="img-compare__divider"
          :style="{ left: position + '%' }"
        />
        <div
          class="img-compare__handle"
          role="slider"
          tabindex="0"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="Math.round(position)"
          :aria-label="`${beforeLabel} / ${afterLabel}`"
          :style="{ left: position + '%' }"
          @keydown.left.prevent="nudge(-2)"
          @keydown.right.prevent="nudge(2)"
          @keydown.up.prevent="nudge(2)"
          @keydown.down.prevent="nudge(-2)"
          @keydown.home.prevent="position = 0"
          @keydown.end.prevent="position = 100"
        >
          <span class="img-compare__handle-grip">‹ ›</span>
        </div>
      </template>

      <!-- 角标：标注嵌入前/后（可配置） -->
      <span
        v-if="beforeSrc"
        class="img-compare__tag is-before"
      >{{ beforeLabel }}</span>
      <span
        v-if="afterSrc"
        class="img-compare__tag is-after"
      >{{ afterLabel }}</span>
    </div>

    <!-- 并排模式（默认，保持既有外观） -->
    <div
      v-else
      class="img-compare__side"
      :style="{ '--stage-h': height }"
    >
      <div class="img-compare__pane">
        <div class="img-compare__pane-head">
          {{ beforeLabel }}
        </div>
        <div class="img-compare__pane-body">
          <img
            v-if="beforeSrc"
            :src="beforeSrc"
            class="img-compare__img"
            :alt="beforeLabel"
            draggable="false"
          >
          <span
            v-else
            class="img-compare__missing"
          >—</span>
        </div>
      </div>
      <div class="img-compare__pane">
        <div class="img-compare__pane-head">
          {{ afterLabel }}
        </div>
        <div class="img-compare__pane-body">
          <img
            v-if="afterSrc"
            :src="afterSrc"
            class="img-compare__img"
            :alt="afterLabel"
            draggable="false"
          >
          <span
            v-else
            class="img-compare__missing"
          >—</span>
        </div>
      </div>
    </div>

    <!-- 控制行：模式 + 位置（存百分比） -->
    <div class="img-compare__bar">
      <el-radio-group
        v-model="mode"
        size="small"
        :disabled="!beforeSrc || !afterSrc"
      >
        <el-radio-button value="side">
          {{ $t('common.imgCompare.side') }}
        </el-radio-button>
        <el-radio-button value="wipe">
          {{ $t('common.imgCompare.wipe') }}
        </el-radio-button>
        <el-radio-button value="opacity">
          {{ $t('common.imgCompare.opacity') }}
        </el-radio-button>
      </el-radio-group>
      <template v-if="mode !== 'side'">
        <el-slider
          v-model="position"
          class="img-compare__slider"
          :min="0"
          :max="100"
          :show-tooltip="false"
        />
        <span class="img-compare__pct tnum-id">{{ Math.round(position) }}%</span>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

/**
 * §5.17 图片对比组件：并排（默认）/ 卷帘 / 透明度 三模式。
 * - 位置以百分比（0–100）存储；
 * - 卷帘把手 role="slider"，支持方向键（±2）、Home/End；
 * - 指针拖拽舞台任意处即可移动卷帘。
 */
const props = defineProps({
  beforeSrc: { type: String, default: '' },
  afterSrc: { type: String, default: '' },
  beforeLabel: { type: String, default: '' },
  afterLabel: { type: String, default: '' },
  /** 对比舞台高度 */
  height: { type: String, default: '320px' },
  defaultMode: { type: String, default: 'side' },
})

const mode = ref(props.defaultMode)
const position = ref(50)

// 缺图时自动回退并排模式（卷帘/透明度需要两张图）
watch(
  () => [props.beforeSrc, props.afterSrc],
  () => {
    if ((!props.beforeSrc || !props.afterSrc) && mode.value !== 'side') {
      mode.value = 'side'
    }
  }
)

let dragging = false

const setFromEvent = (e) => {
  const el = e.currentTarget
  const rect = el.getBoundingClientRect()
  if (!rect.width) return
  const pct = ((e.clientX - rect.left) / rect.width) * 100
  position.value = Math.min(100, Math.max(0, Math.round(pct)))
}

const onPointerDown = (e) => {
  if (mode.value === 'side') return
  dragging = true
  el?.setPointerCapture?.(e.pointerId)
  setFromEvent(e)
}
const onPointerMove = (e) => {
  if (!dragging) return
  setFromEvent(e)
}
const onPointerUp = () => {
  dragging = false
}
const el = null

const nudge = (delta) => {
  position.value = Math.min(100, Math.max(0, position.value + delta))
}
</script>

<style scoped>
.img-compare {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.img-compare__stage {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: var(--radius-lg);
  background: var(--bg-inset);
  box-shadow: var(--card-ring);
  user-select: none;
  touch-action: none;
  cursor: ew-resize;
}

.img-compare__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  pointer-events: none;
}

.img-compare__clip {
  position: absolute;
  inset: 0;
}

.img-compare__divider {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  margin-left: -1px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 1px rgba(10, 10, 10, 0.25);
  pointer-events: none;
}

.img-compare__handle {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  box-shadow: var(--elevation-2);
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1;
  cursor: ew-resize;
}

.img-compare__handle:focus-visible {
  outline: none;
  box-shadow: var(--ring);
}

.img-compare__handle-grip {
  letter-spacing: 1px;
}

.img-compare__tag {
  position: absolute;
  top: 10px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: var(--text-inverse);
  background: rgba(10, 10, 10, 0.55);
  pointer-events: none;
}

.img-compare__tag.is-before {
  left: 10px;
}

.img-compare__tag.is-after {
  right: 10px;
}

.img-compare__side {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-width: 0;
}

.img-compare__pane {
  min-width: 0;
}

.img-compare__pane-head {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  margin-bottom: 8px;
  text-align: center;
}

.img-compare__pane-body {
  position: relative;
  height: var(--stage-h, 320px);
  border-radius: var(--radius-lg);
  background: var(--bg-inset);
  box-shadow: var(--card-ring);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.img-compare__pane-body .img-compare__img {
  position: static;
  width: 100%;
  height: 100%;
}

.img-compare__missing {
  color: var(--text-placeholder);
}

.img-compare__bar {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.img-compare__slider {
  flex: 1;
  min-width: 120px;
  max-width: 320px;
}

.img-compare__pct {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  min-width: 36px;
  text-align: right;
}
</style>
