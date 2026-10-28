<template>
  <el-tooltip
    :disabled="!reason"
    :content="reason"
    placement="top"
    :show-after="120"
    :hide-after="0"
  >
    <span
      class="disabled-tip-wrap"
      :class="{ 'is-block': block }"
    ><slot /></span>
  </el-tooltip>
</template>

<script setup>
/**
 * §4.15 disabled 制度：禁用按钮的 disabledReason tooltip 包装。
 * Element Plus 原生 disabled 按钮不触发鼠标事件，外层套 span 承接 tooltip；
 * reason 为空字符串时 tooltip 自动禁用（按钮可用时不打扰）。
 * block: 包裹块级内容（如 el-upload）时置真，避免收缩宽度。
 */
defineProps({
  reason: { type: String, default: '' },
  block: { type: Boolean, default: false },
})
</script>

<style scoped>
.disabled-tip-wrap {
  display: inline-flex;
  vertical-align: middle;
}

.disabled-tip-wrap.is-block {
  display: flex;
}
</style>
