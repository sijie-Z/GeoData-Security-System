// 主题切换（浅色 / 深色），遵循 Element Plus 官方 html.dark 约定。
// 持久化键：geodata-theme ('light' | 'dark')，默认浅色。
import { ref } from 'vue'

export const THEME_KEY = 'geodata-theme'

const isDark = ref(false)

function readStoredDark() {
  try {
    return localStorage.getItem(THEME_KEY) === 'dark'
  } catch {
    return false
  }
}

/** 应用主题：切换 html.dark 类名并持久化 */
export function applyTheme(dark) {
  isDark.value = dark
  document.documentElement.classList.toggle('dark', dark)
  try {
    localStorage.setItem(THEME_KEY, dark ? 'dark' : 'light')
  } catch {
    /* localStorage 不可用时仅本次会话生效 */
  }
}

/** 启动时初始化（不写回 localStorage），需在挂载前调用以避免闪烁 */
export function initTheme() {
  const dark = readStoredDark()
  isDark.value = dark
  document.documentElement.classList.toggle('dark', dark)
}

export function toggleTheme() {
  applyTheme(!isDark.value)
}

export function useTheme() {
  return { isDark, toggleTheme }
}
