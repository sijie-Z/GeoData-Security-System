# 空间数据追踪系统（Spatial Data Tracking System）

本系统为地理空间数据（矢量与栅格）的申请、审批、水印生成/嵌入/提取、下载与追踪的一体化平台，支持管理员与员工双角色、双级审批、站内通知与操作日志。

---

## 一、项目结构

- **testrealend**：后端（Flask + Flask-RESTful + JWT + MySQL）
- **testrealfrontol**：前端（Vue 3 + Vite + Element Plus + Pinia）

---

## 二、如何同时启动前后端

### 1. 环境要求

- Python 3.10+（后端）
- Node.js 18+（前端）
- MySQL（数据库）
- 后端依赖：见 `testrealend/requirements.txt`（若有）

### 2. 启动后端

```bash
cd testrealend
# 建议使用虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# 安装依赖后
python app.py
```

后端默认运行在 **http://localhost:5001**。  
首次运行会自动创建系统公告表、用户通知表等（若不存在）。

### 3. 启动前端

```bash
cd testrealfrontol
npm install
npm run dev
```

前端默认运行在 **http://localhost:5173**（或终端提示的端口）。  
请确保前端请求的后端地址正确（见下方「环境变量」）。

### 4. 环境变量（前端）

在 `testrealfrontol` 下创建 `.env`（或 `.env.development`）：

```env
VITE_API_URL=http://localhost:5001
```

这样前端会使用该地址请求后端接口；未配置时部分页面会回退到 `http://localhost:5001`。

### 5. 同时使用

1. 先启动后端（`python app.py`）。
2. 再启动前端（`npm run dev`）。
3. 浏览器访问前端地址（如 http://localhost:5173），登录后即可使用。

---

## 三、栅格数据是如何展示的

系统对栅格数据的展示分为两类：

### 1. 列表/卡片中的缩略图

- 后端提供栅格数据的**缩略图 URL**（如 `/api/raster_data/thumbnail/<id>` 或数据表中的 `preview_url`）。
- 前端在数据目录/列表中通过 `<img :src="basic_url + item.preview_url">` 等方式展示小图，用于快速浏览。

### 2. 地图上的瓦片展示（主要方式）

- 前端使用 **Leaflet**（或类似地图库）加载栅格时，不直接请求整幅 GeoTIFF，而是按**瓦片**请求。
- 瓦片请求格式为：  
  `GET /api/raster_tiles/<rasterId>/{z}/{x}/{y}.png`  
  其中 `z` 为缩放级别，`x`、`y` 为该级别下的瓦片坐标。
- 后端（`RasterTileServerResource`）会：
  1. 根据 `rasterId` 从数据库取出对应栅格文件的路径（如 GeoTIFF）；
  2. 使用 **rasterio** 按瓦片的地理范围从 GeoTIFF 中切出对应区域；
  3. 做坐标与像素处理（如 Web Mercator 与数据 CRS 的转换、归一化到 0–255 等）；
  4. 返回 PNG 图片给前端。
- 这样前端实现**按需加载**，只请求当前视野内的瓦片，保证大影像下的流畅浏览。

总结：**栅格数据 = 列表中用缩略图预览 + 地图中用瓦片服务（/api/raster_tiles/...）分块显示**。

---

## 四、主要功能概览

- **员工端**：数据目录（矢量/栅格浏览与检索）、数据申请、我的下载、操作历史、我的通知、个人中心、帮助与关于。
- **管理员端**：审批管理、矢量/栅格水印生成·嵌入·提取、系统公告、**站内通知（定向/全体）**、**系统操作日志（按用户编号/姓名/操作类型筛选）**、数据上传等。
- **二维码水印**：支持申请原因、备注写入二维码，可调 Version、纠错等级、格点等精度参数。

---

## 五、文档与说明

- 前端项目说明与脚本详见：**testrealfrontol/README.md**。
- 系统功能说明、帮助与关于内容见前端「帮助」与「关于」页面及本文档。
