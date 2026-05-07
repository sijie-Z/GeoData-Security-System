# 空间数据追踪系统 - 前端

Vue 3 + Vite + Element Plus + Pinia + vue-i18n，用于空间数据申请、审批、水印与数据目录等功能的 Web 端。

## 国际化 (i18n)

系统已全面支持中英文切换，覆盖全部 49 个视图页面、1200+ 翻译键。

- **中文：** `src/locales/zh-CN.js`
- **English：** `src/locales/en-US.js`
- **切换方式：** 页面右上角语言切换器，选择后自动保存到 localStorage

## 环境与配置

- Node.js 18+
- 后端接口地址通过环境变量配置，见下方。

### 环境变量

在项目根目录创建 `.env` 或 `.env.development`：

```env
VITE_API_URL=http://localhost:5001
```

未配置时，部分请求会回退到 `http://localhost:5001`。生产构建时请改为实际后端地址。

## 安装依赖

```bash
npm install
```

## 开发（热更新）

```bash
npm run dev
```

默认运行在 http://localhost:5173（或终端提示的端口）。**请先启动后端**（见项目根目录 README.md）。

## 构建生产

```bash
npm run build
```

产物在 `dist/`，可部署到任意静态服务器；需保证请求能发到配置的 `VITE_API_URL`。

## 推荐 IDE

[VSCode](https://code.visualstudio.com/) + [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar)（可关闭 Vetur）。

## 配置参考

[Vite 配置](https://vitejs.dev/config/)。
