/**
 * Element Plus 2.14 上游可访问性缺陷的前端补丁集合。
 *
 * 背景：axe-core 全量扫描（40 路由）命中三处 EP 内部渲染、且无法通过组件的
 * props / slots 修正的无障碍缺陷。上游修复前，这里以「打开/挂载后补属性」的
 * 最小侵入方式修补；全部为属性级改动，不动 DOM 结构、不碰数据流。
 * 一旦升级到修复了这些问题的 EP 版本，本文件应整体移除（并删除调用点）。
 */

/**
 * EP 上游补丁 1：el-tour 弹层。
 * - `.el-tour__header` 是 EP 用 <header> 渲染的弹层头部，会被辅助技术识别为
 *   页面第二个 banner 地标（axe: landmark-no-duplicate-banner / landmark-unique）；
 * - `.el-tour__title` 是 span[role=heading]，缺必需的 aria-level（axe: aria-required-attr）。
 * 在引导「打开后」调用；弹层由 EP 动态挂载，未就绪时短暂重试。
 */
export function patchElTourOverlay(retries = 25) {
  const apply = () => {
    const header = document.querySelector('.el-tour__header')
    if (header) header.setAttribute('role', 'presentation')
    const title = document.querySelector('.el-tour__title[role="heading"]')
    if (title && !title.hasAttribute('aria-level')) title.setAttribute('aria-level', '2')
    return !!header && !!title
  }
  if (!apply() && retries > 0) setTimeout(() => patchElTourOverlay(retries - 1), 80)
}

/**
 * EP 上游补丁 2：el-pagination 的「每页条数」选择器。
 * 该选择器由 EP 内部 sizes 子组件渲染（不接收外部 aria-label），其 role=combobox
 * 输入框在辅助技术里没有名字（axe label 规则）。给分页根元素内的输入框补 aria-label。
 * @param {Element|undefined} rootEl 包含 el-pagination 的根元素（组件 $el 或容器 ref）
 * @param {string} label 可访问名（调用方传入已翻译文本）
 */
export function patchPaginationSizeLabel(rootEl, label, retries = 20) {
  const apply = () => {
    const input = rootEl?.querySelector?.('.el-pagination__sizes .el-select__input')
    if (input) {
      input.setAttribute('aria-label', label)
      return true
    }
    return false
  }
  if (!apply() && retries > 0) setTimeout(() => patchPaginationSizeLabel(rootEl, label, retries - 1), 120)
}

/**
 * EP 上游补丁 3：el-table 内部纵向滚动包裹层。
 * max-height 表格的 `.el-table__body-wrapper .el-scrollbar__wrap` 可滚动但不可聚焦
 * （axe: scrollable-region-focusable）。补 tabindex=0（+ aria-label）让键盘用户可聚焦滚动。
 * @param {Element|undefined} rootEl 包含目标表格的根元素（组件 $el 或容器 ref）
 * @param {string} label 可访问名（调用方传入已翻译文本）
 */
export function focusTableScrollWraps(rootEl, label, retries = 25) {
  const apply = () => {
    const wraps = rootEl?.querySelectorAll?.('.el-table__body-wrapper .el-scrollbar__wrap')
    if (wraps && wraps.length) {
      wraps.forEach((wrap) => {
        if (wrap.getAttribute('tabindex') !== '0') wrap.setAttribute('tabindex', '0')
        if (label && !wrap.hasAttribute('aria-label')) wrap.setAttribute('aria-label', label)
      })
      return true
    }
    return false
  }
  if (!apply() && retries > 0) setTimeout(() => focusTableScrollWraps(rootEl, label, retries - 1), 120)
}
