// src/main.js
import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';
import './assets/styles/design-system.css';
import * as ElementPlusIconsVue from '@element-plus/icons-vue';
import zhCn from 'element-plus/dist/locale/zh-cn.mjs';
import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
// import {useUserStore} from "@/stores/userStore.js";
import {useUserStore} from '@/stores/userStore.js'


// 创建 Vue 应用
const app = createApp(App);

// 创建并配置 Pinia
const pinia = createPinia();
pinia.use(piniaPluginPersistedstate);


// 使用 Pinia 和路由
app.use(pinia);
const userStore = useUserStore();
userStore.initializeStore()

app.use(router);


// 注册 ElementPlus 组件库中的所有图标到全局 Vue 应用中
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

// 使用 ElementPlus 并设置语言
app.use(ElementPlus, {
  locale: zhCn
});

// 挂载应用
app.mount("#app");






