import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})


// // vite.config.js
// import { fileURLToPath, URL } from 'node:url'
// import { defineConfig, loadEnv } from 'vite' // 引入 loadEnv
// import vue from '@vitejs/plugin-vue'

// // https://vitejs.dev/config/
// export default defineConfig(({ mode }) => { // 将 defineConfig 改为函数形式以访问 mode
//   // 加载特定模式的环境变量 (例如 .env.development)
//   const env = loadEnv(mode, process.cwd(), ''); // process.cwd() 是项目根目录, '' 表示加载所有VITE_开头的变量

//   return {
//     plugins: [
//       vue(),
//     ],
//     resolve: {
//       alias: {
//         '@': fileURLToPath(new URL('./src', import.meta.url))
//       }
//     },
//     server: {
//       port: 5173, // 你前端的开发端口
//       proxy: {
//         // 将所有以 /api 开头的请求代理到你的Flask后端
//         '/api': {
//           target: env.VITE_API_URL || 'http://localhost:5001', // 从环境变量读取后端地址，如果没有则使用默认值
//           changeOrigin: true, // 需要虚拟主机站点
//           // secure: false, // 如果你的后端是http而你想代理https，或者反之，可能需要这个
//           // rewrite: (path) => path.replace(/^\/api/, '/api') // 如果后端API路径本身就包含/api，则不需要重写或这样重写
//                                                             // 如果后端的路径不包含/api，例如直接是/login，而你想让前端请求/api/login，则 rewrite: (path) => path.replace(/^\/api/, '')
//         },
//         // 如果你还有其他需要代理的路径，例如天地图的 /api-tdt
//         '/api-tdt': {
//           target: 'https://api.tianditu.gov.cn',
//           changeOrigin: true,
//           rewrite: (path) => path.replace(/^\/api-tdt/, ''),
//         }
//       }
//     }
//   }
// })