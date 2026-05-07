<script setup>

</script>

<template>

   <router-view />

</template>

<style>
/* 全局圆角与界面优化 */
:root {
  --app-radius: 12px;
  --app-radius-lg: 16px;
}
* {
  box-sizing: border-box;
}
html, body, #app {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  max-width: 100%;
  overflow: hidden;
  background: #f0f2f5;
}
.el-card {
  border-radius: var(--app-radius-lg) !important;
}
.el-button {
  border-radius: var(--app-radius) !important;
}
.el-dialog {
  border-radius: var(--app-radius-lg) !important;
}
.el-table {
  border-radius: var(--app-radius) !important;
  overflow: hidden;
}
.el-input__wrapper,
.el-select .el-select__wrapper {
  border-radius: var(--app-radius) !important;
}
.el-tag {
  border-radius: calc(var(--app-radius) - 2px) !important;
}
</style>
<style scoped>

</style>


