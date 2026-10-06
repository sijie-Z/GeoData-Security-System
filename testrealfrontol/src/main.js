import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
// Element Plus 官方深色变量（html.dark 约定），须在 design-system.css 之前加载，
// 以便后者在其基础上做品牌化覆写
import 'element-plus/theme-chalk/dark/css-vars.css'
import './assets/styles/design-system.css'
import { initTheme } from '@/composables/useTheme.js'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import enUs from 'element-plus/dist/locale/en.mjs'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { useUserStore } from '@/stores/userStore.js'
import i18n, { getLocale } from '@/locales/index.js'

const app = createApp(App)

// 挂载前应用持久化主题（html.dark），避免深色用户首帧闪烁
initTheme()

// Global error handler — log + notify user, prevent silent white screen
app.config.errorHandler = (err, instance, info) => {
  console.error('Global error:', err)
  console.error('Component:', instance?.$options?.name || 'unknown')
  console.error('Info:', info)
  // Show user-facing notification (if ElMessage is available)
  try {
    const { ElMessage } = require('element-plus')
    ElMessage.error('页面渲染出错，请刷新重试')
  } catch (_) { /* ignore if not available */ }
}

// Catch unhandled promise rejections (e.g. async onMounted failures)
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason)
  event.preventDefault() // prevent silent crash
})

// Pinia state management
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)

// Initialize auth state from sessionStorage
const userStore = useUserStore()
userStore.initializeStore()

// Proactive token refresh on startup — if the stored token is already expired,
// refresh it immediately so the first API call doesn't fail with 401/422.
if (userStore.token && userStore.refreshToken) {
  const apiBase = import.meta.env.VITE_API_URL || ''
  fetch(`${apiBase}/api/refresh-token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: userStore.refreshToken }),
  })
    .then(r => r.json())
    .then(data => {
      if (data?.access_token) {
        userStore.updateTokens(data.access_token, data.refresh_token)
      }
    })
    .catch(() => {
      // Refresh failed — stored token may be too old; user will land on login page.
      // Don't clear here — let the first actual API call handle it.
    })
}

// i18n
app.use(i18n)

// Router
app.use(router)

// Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Element Plus with dynamic locale based on i18n
const currentLocale = getLocale()
const epLocale = currentLocale === 'en-US' ? enUs : zhCn
app.use(ElementPlus, { locale: epLocale })

app.mount('#app')
