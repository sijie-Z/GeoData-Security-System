import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './assets/styles/design-system.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import enUs from 'element-plus/dist/locale/en.mjs'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { useUserStore } from '@/stores/userStore.js'
import i18n, { getLocale } from '@/locales/index.js'

const app = createApp(App)

// Global error handler
app.config.errorHandler = (err, instance, info) => {
  console.error('Global error:', err)
  console.error('Component:', instance?.$options?.name || 'unknown')
  console.error('Info:', info)
}

// Pinia state management
const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)
app.use(pinia)

// Initialize auth state from sessionStorage
const userStore = useUserStore()
userStore.initializeStore()

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
