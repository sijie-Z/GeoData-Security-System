<!--
  404 路由包装（fix/a11y-axe）：catch-all 的 NotFound 页此前整页无主地标
  （axe landmark-one-main / region）。这里仅用 <main> 包一层补齐地标；
  NotFound.vue 本体按红线要求不回改。main 无任何样式，块级流对原布局零影响。
-->
<template>
  <main>
    <NotFound />
  </main>
</template>

<script setup>
import NotFound from '@/views/NotFound.vue'
</script>
