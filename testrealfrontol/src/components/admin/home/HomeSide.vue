<template>
  <!-- 侧栏即站点导航：<nav> 提供 navigation 地标（axe region / landmark-one-main 根因之一） -->
  <nav
    ref="navRef"
    class="sidebar"
    :class="{ collapsed: isCollapse }"
  >
    <el-menu
      ref="menuRef"
      router
      :unique-opened="uniqueOpened"
      :popper-offset="0"
      :default-active="$route.path"
      :collapse="isCollapse"
      class="sidebar-menu"
      @open="onMenuOpen"
    >
      <el-menu-item index="/admin">
        <el-icon><HomeFilled /></el-icon>
        <template #title>{{ $t('sidebar.admin.dashboard') }}</template>
      </el-menu-item>

      <el-sub-menu index="approval">
        <template #title>
          <el-icon><DocumentChecked /></el-icon>
          <span>{{ $t('sidebar.admin.approval') }}</span>
        </template>
        <el-menu-item index="/admin/approve_application/not_approved">{{ $t('sidebar.admin.firstReview') }}</el-menu-item>
        <el-menu-item index="/admin/approve_application/approved">{{ $t('sidebar.admin.secondReview') }}</el-menu-item>
        <el-menu-item index="/admin/approve_application/dual_channel">{{ $t('sidebar.admin.dualChannel') }}</el-menu-item>
        <el-menu-item index="/admin/recall">{{ $t('sidebar.admin.dataRecall') }}</el-menu-item>
        <el-menu-item index="/admin/admin-application">{{ $t('sidebar.admin.adminAppApproval') }}</el-menu-item>
      </el-sub-menu>

      <!-- 水印菜单（后端 API 已有角色限制，前端全部显示） -->
      <el-sub-menu index="watermark">
        <template #title>
          <el-icon><Picture /></el-icon>
          <span>{{ $t('sidebar.admin.watermark') }}</span>
        </template>
        <el-sub-menu index="vector-wm">
          <template #title>{{ $t('sidebar.admin.vectorData') }}</template>
          <el-menu-item index="/admin/watermark_generation">{{ $t('sidebar.admin.generate') }}</el-menu-item>
          <el-menu-item index="/admin/watermark_embedding">{{ $t('sidebar.admin.embed') }}</el-menu-item>
          <el-menu-item index="/admin/watermark_extraction">{{ $t('sidebar.admin.extract') }}</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="raster-wm">
          <template #title>{{ $t('sidebar.admin.rasterData') }}</template>
          <el-menu-item index="/admin/raster_watermark_generation">{{ $t('sidebar.admin.generate') }}</el-menu-item>
          <el-menu-item index="/admin/raster_watermark_embedding">{{ $t('sidebar.admin.embed') }}</el-menu-item>
          <el-menu-item index="/admin/raster_watermark_extraction">{{ $t('sidebar.admin.extract') }}</el-menu-item>
        </el-sub-menu>
      </el-sub-menu>

      <el-menu-item index="/admin/traceability">
        <el-icon><Aim /></el-icon>
        <template #title>{{ $t('sidebar.admin.traceability') }}</template>
      </el-menu-item>

      <el-menu-item index="/admin/watermark-quality">
        <el-icon><DataAnalysis /></el-icon>
        <template #title>{{ $t('sidebar.admin.watermarkQuality') }}</template>
      </el-menu-item>

      <el-menu-item index="/admin/forensics">
        <el-icon><Search /></el-icon>
        <template #title>{{ $t('sidebar.admin.forensics') }}</template>
      </el-menu-item>

      <el-menu-item index="/admin/anchors">
        <el-icon><Stamp /></el-icon>
        <template #title>{{ $t('sidebar.admin.anchorCenter') }}</template>
      </el-menu-item>

      <el-menu-item index="/admin/robustness">
        <el-icon><Cpu /></el-icon>
        <template #title>{{ $t('sidebar.admin.robustnessLab') }}</template>
      </el-menu-item>

      <el-sub-menu index="data">
        <template #title>
          <el-icon><Folder /></el-icon>
          <span>{{ $t('sidebar.admin.dataMgmt') }}</span>
        </template>
        <el-menu-item index="/admin/data/upload">{{ $t('sidebar.admin.dataUpload') }}</el-menu-item>
        <el-menu-item index="/admin/data/raster-upload">{{ $t('sidebar.admin.rasterUpload') }}</el-menu-item>
        <el-menu-item index="/admin/data/manage">{{ $t('adminDataManage.title') || '数据管理' }}</el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="employee">
        <template #title>
          <el-icon><User /></el-icon>
          <span>{{ $t('sidebar.admin.employeeMgmt') }}</span>
        </template>
        <el-menu-item index="/admin/employee_management/information_list">{{ $t('sidebar.admin.employeeList') }}</el-menu-item>
        <el-menu-item index="/admin/employee_management/information_add">{{ $t('sidebar.admin.addEmployee') }}</el-menu-item>
        <el-menu-item index="/admin/system/chat">{{ $t('sidebar.admin.onlineChat') }}</el-menu-item>
      </el-sub-menu>

      <el-sub-menu index="system">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>{{ $t('sidebar.admin.systemSettings') }}</span>
        </template>
        <el-menu-item index="/admin/logs">{{ $t('sidebar.admin.operationLogs') }}</el-menu-item>
        <el-menu-item index="/admin/system/announcements">{{ $t('sidebar.admin.systemAnnouncement') }}</el-menu-item>
        <el-menu-item index="/admin/system/notifications">{{ $t('sidebar.admin.messageSend') }}</el-menu-item>
        <el-menu-item index="/admin/guide">{{ $t('sidebar.admin.guide') }}</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </nav>
</template>

<script setup>
import { defineProps, ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import {
  HomeFilled, User, DocumentChecked, Setting,
  Picture, Folder, Aim, DataAnalysis, Search, Stamp, Cpu
} from '@element-plus/icons-vue'

const props = defineProps({
  isCollapse: {
    type: Boolean,
    default: false
  }
})

const route = useRoute()
const navRef = ref(null)
const menuRef = ref(null)
// unique-opened 常态为 true；仅在「豁免重开激活链」的同一批微任务内临时置 false（见 onMenuOpen）
const uniqueOpened = ref(true)
let scrollTimers = []
let exempting = false

// 路由前缀 → 激活项所在子菜单链的「最内层父菜单」index（与上方模板菜单结构一一对应）。
// unique-opened 会在打开其它菜单时关闭激活项所在的整条链；打开 menuRef.open(链尾) 时
// EP 会按 indexPath 逐级重开该链，激活项因此保持可见。无匹配路由（如仪表盘）时
// 维持 unique-opened 原生单开语义。
const ACTIVE_PARENT_PREFIXES = [
  ['/admin/approve_application', 'approval'],
  ['/admin/recall', 'approval'],
  ['/admin/admin-application', 'approval'],
  ['/admin/watermark_generation', 'vector-wm'],
  ['/admin/watermark_embedding', 'vector-wm'],
  ['/admin/watermark_extraction', 'vector-wm'],
  ['/admin/raster_watermark_generation', 'raster-wm'],
  ['/admin/raster_watermark_embedding', 'raster-wm'],
  ['/admin/raster_watermark_extraction', 'raster-wm'],
  ['/admin/data', 'data'],
  ['/admin/employee_management', 'employee'],
  ['/admin/system/chat', 'employee'],
  ['/admin/logs', 'system'],
  ['/admin/system/announcements', 'system'],
  ['/admin/system/notifications', 'system'],
  ['/admin/guide', 'system']
]

const findActiveParent = (path) => {
  let best = null
  for (const [prefix, index] of ACTIVE_PARENT_PREFIXES) {
    if (path.startsWith(prefix) && (!best || prefix.length > best.prefix.length)) {
      best = { prefix, index }
    }
  }
  return best ? best.index : null
}

// unique-opened 豁免：打开 B 时若 A 是当前激活项的祖先 → 把 A 重新展开（允许两菜单同开）。
// 注意 menuRef.open() 内部仍会再走一遍 unique 过滤（那样会把刚打开的 B 关掉），因此先
// 临时解除 unique-opened、重开激活链后再恢复；整个过程在同一批微任务内完成，
// 浏览器不会在中间绘制，无视觉闪烁。exempting 防止重开动作自身触发的 @open 递归。
const onMenuOpen = async (index) => {
  if (exempting || props.isCollapse) return
  const activeParent = findActiveParent(route.path)
  if (!activeParent || activeParent === index) return
  exempting = true
  uniqueOpened.value = false
  await nextTick()
  menuRef.value?.open(activeParent)
  uniqueOpened.value = true
  exempting = false
}

// 激活项滚入侧栏可视区（block: 'nearest' 语义；只调整侧栏自身滚动容器，绝不滚动外层壳）
const scrollActiveIntoView = () => {
  const nav = navRef.value
  if (!nav) return
  const active =
    nav.querySelector('.el-menu-item.is-active') ||
    nav.querySelector('.el-sub-menu.is-active > .el-sub-menu__title')
  if (!active) return
  const nr = nav.getBoundingClientRect()
  const ar = active.getBoundingClientRect()
  if (ar.width === 0 && ar.height === 0) return // 激活项在未展开的子菜单里（display:none）
  if (ar.top < nr.top) nav.scrollTop = Math.max(0, nav.scrollTop - (nr.top - ar.top))
  else if (ar.bottom > nr.bottom) nav.scrollTop += ar.bottom - nr.bottom
}

const scheduleScrollActive = () => {
  scrollTimers.forEach(clearTimeout)
  scrollTimers = []
  nextTick(() => {
    requestAnimationFrame(scrollActiveIntoView)
    // 子菜单开合带过渡（unique-opened 联动时位置会继续变化）：过渡中/后再校正两次
    scrollTimers.push(setTimeout(scrollActiveIntoView, 180))
    scrollTimers.push(setTimeout(scrollActiveIntoView, 380))
  })
}

// 路由变化与首挂载都要把激活项滚入可视区（keep-alive 返回页面同样触发 path 变化）
watch(() => route.path, scheduleScrollActive)
onMounted(scheduleScrollActive)
onBeforeUnmount(() => {
  scrollTimers.forEach(clearTimeout)
  scrollTimers = []
})
</script>

<style scoped>
.sidebar {
  width: 200px;
  background: var(--sidebar-solid-bg, #ffffff);
  border-right: 1px solid var(--border-color);
  /* 高度不写死：flex stretch 精确填满顶栏（60px）下的可用高度，自身即滚动容器 */
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain; /* 滚轮在侧栏尽头不链式带动外层壳 */
  transition: width 220ms var(--ease-drawer), background-color var(--duration-200) var(--ease-out-soft), border-color var(--duration-200) var(--ease-out-soft);
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-menu {
  border-right: none !important;
  background: transparent !important;
  height: 100%;
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 200px;
}

:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  height: 46px;
  line-height: 46px;
  color: var(--sidebar-text) !important;
  font-size: 14px;
  /* 显式属性过渡（原 transition: all 会在容器变宽时全量比对/重算）*/
  transition: background-color var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast) !important;
}

:deep(.el-menu-item:hover),
:deep(.el-sub-menu__title:hover) {
  background-color: var(--sidebar-item-hover) !important;
  color: var(--sidebar-text-active) !important;
}

:deep(.el-menu-item.is-active) {
  color: var(--sidebar-text-active) !important;
  background-color: var(--sidebar-item-active) !important;
  border-left: 3px solid var(--primary-500);
}

:deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--sidebar-text-active) !important;
}

:deep(.el-menu--inline) {
  background-color: transparent !important;
}

/* 折叠时 Element Plus 会把整块 <ul> 经 <transition name="horizontal-collapse-transition"> 换装；
   Vue 在该元素上等一个永远不会发生的 width transitionend（301ms 兜底超时），
   导致宽度动画结束后才做菜单换装、末尾卡顿。取消该等待：换装与折叠同帧完成。 */
:deep(.horizontal-collapse-transition) {
  transition: none !important;
}

:deep(.el-sub-menu .el-menu-item) {
  min-width: auto !important;
  padding-left: 50px !important;
  height: 42px;
  line-height: 42px;
}

.el-icon {
  font-size: 17px;
  margin-right: 8px;
}

.sidebar::-webkit-scrollbar {
  width: 6px;
}

.sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar::-webkit-scrollbar-thumb {
  background: var(--border-color-hover);
  border-radius: 3px;
}

.sidebar::-webkit-scrollbar-thumb:hover {
  background: var(--text-3);
}
</style>
