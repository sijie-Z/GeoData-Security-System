import { fileURLToPath, URL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

function getBackendPort() {
  const portFile = path.resolve(
    path.dirname(fileURLToPath(import.meta.url)),
    '..', 'testrealend', '.backend-port'
  )
  try {
    const port = parseInt(fs.readFileSync(portFile, 'utf8').trim(), 10)
    if (port >= 1024 && port <= 65535) return port
  } catch {
    // ignore
  }
  return 5003
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    strictPort: false,  // Auto-try next port if 5173 is occupied
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${getBackendPort()}`,
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.warn('[vite proxy] backend unreachable:', err.message);
          });
        },
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // 构建分块：把大体积、低频变更的第三方库拆成独立 vendor 块，
        // 入口/业务 chunk 变小，浏览器可长期缓存 vendor（变更时只失效业务块）。
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('echarts') || id.includes('zrender')) return 'vendor-echarts';
          if (id.includes('element-plus')) return 'vendor-element';
          if (
            id.includes('/vue/') || id.includes('/vue-router/') || id.includes('/pinia/') ||
            id.includes('pinia-plugin-persistedstate') || id.includes('/vue-i18n/') ||
            id.includes('/@vueuse/') || id.includes('/@vue/') || id.includes('vue-demi')
          ) return 'vendor-vue';
          return undefined;
        },
      },
    },
  },
})
