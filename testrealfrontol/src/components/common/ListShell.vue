<!--
  ListShell —— 共享列表壳（审计系统性观察 2 收官组件，与 PageHeader / EmptyState 构成
  "页头 - 列表壳 - 空态"统一骨架）。

  背景：站内各列表页的"筛选条 + 表格 + 分页 + 空态"此前各自手写，形成三类漂移：
  分页有"卡内 / 卡外"两套位置与"el-pagination / 自绘按钮"两套样式；空态有三种待遇
  （el-empty / EmptyState 注入表格 / 表格默认文案）；筛选条间距与换行规则各页不一
  （8 / 10 / 12 / 20px 混用）。本组件收敛为唯一列表壳三层结构：
    filters 槽（统一间距与换行）→ 表格区（主槽）→ 分页带（统一位置与令牌样式）。

  约定：
  - `empty` 为真时主槽不渲染，改渲染 EmptyState（variant / title / description / ctaText /
    compact 经 props 透传，也可用 `empty` 具名槽整体覆盖）；分页带在 total <= 0 时整条隐藏。
  - `pagination` 对象透传给 el-pagination（令牌样式见 design-system.css "分页主题化"），
    字段：{ page, pageSize, total, layout, pageSizes?, background? }；翻页 / 改每页大小经
    `page-change` / `size-change` 事件回抛调用页，由调用页沿用其既有数据逻辑处理（组件自身
    不持有分页状态、不发请求）。
  - 只统一"壳"：表格列、操作列与数据流由调用页原样提供，组件不触碰。
  - 窄屏（<768px）：筛选条换行（flex-wrap）；分页带沿用移动端壳层已定的
    "el-pagination 内部换行"全局规则（design-system.css），本组件容器允许换行并向右对齐。
  - data-ls 属性为壳层语义标记（filters / main / pagination），供像素与几何核验脚本定位。
-->
<template>
  <div class="list-shell">
    <div v-if="$slots.filters" class="list-shell__filters" data-ls="filters">
      <slot name="filters" />
    </div>

    <div class="list-shell__main" data-ls="main">
      <slot v-if="!empty" />
      <slot v-else name="empty">
        <EmptyState
          :variant="emptyVariant"
          :title="emptyTitle"
          :description="emptyDescription"
          :cta-text="emptyCtaText"
          :compact="emptyCompact"
          @cta="$emit('empty-cta')"
        />
      </slot>
    </div>

    <div v-if="showPagination" class="list-shell__pagination" data-ls="pagination">
      <el-pagination
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :total="pagination.total"
        :layout="pagination.layout || 'prev, pager, next'"
        :page-sizes="pagination.pageSizes"
        :background="!!pagination.background"
        @current-change="$emit('page-change', $event)"
        @size-change="$emit('size-change', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  empty: { type: Boolean, default: false },
  emptyVariant: { type: String, default: 'never' },
  emptyTitle: { type: String, default: '' },
  emptyDescription: { type: String, default: '' },
  emptyCtaText: { type: String, default: '' },
  emptyCompact: { type: Boolean, default: true },
  pagination: { type: Object, default: null },
})

defineEmits(['page-change', 'size-change', 'empty-cta'])

const showPagination = computed(() => !!(props.pagination && (props.pagination.total ?? 0) > 0))
</script>

<style scoped>
.list-shell {
  display: flex;
  flex-direction: column;
}

/* 筛选条带：统一间距/换行规则（--spacing-md：桌面与移动端同为 16px） */
.list-shell__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

/* 表格区：弹性列容器，兼容调用页的 fill 布局（如 information_list 的 flex-grow 表格） */
.list-shell__main {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

/* 分页带：统一右对齐 + 与既有 .pagination-wrap 相同的 20px 上间距（站内多处沿用） */
.list-shell__pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
  flex-wrap: wrap;
}

/* 窄屏：分页元素在容器内收缩并内部换行，
   避免 flex-end 容器把超宽控件推到左缘外被卡片裁切 */
@media (max-width: 767px) {
  .list-shell__pagination .el-pagination {
    max-width: 100%;
  }
}
</style>
