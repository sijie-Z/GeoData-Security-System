# 空间数据安全分发与溯源系统

<div align="center">

![Vue 3](https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-336791?style=flat-square&logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis)
![Docker](https://img.shields.io/badge/Docker-Optional-2496ED?style=flat-square&logo=docker)
![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?style=flat-square&logo=prometheus)
![Grafana](https://img.shields.io/badge/Grafana-Dashboards-F46800?style=flat-square&logo=grafana)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

**一个面向地理空间数据的企业级安全分发与全链路溯源平台**

覆盖矢量（SHP）与栅格（GeoTIFF）数据的完整生命周期管理——从用户申请、双级审批、二维码水印嵌入，到安全分发与来源追踪。

[功能特性](#功能特性) · [系统架构](#系统架构) · [快速开始](#快速开始) · [API 文档](#api-文档) · [部署指南](#部署指南) · [项目结构](#项目结构)

</div>

---

## 项目简介

在地理空间数据的共享与分发场景中，数据泄露溯源和权限管控是核心难题。本系统通过 **二维码水印技术** 与 **双级审批流程**，实现了空间数据从申请到分发的全链路安全管控：

- 用户提交数据申请 → 管理员双级审批 → 水印嵌入 → 安全分发
- 一旦数据泄露，可通过提取水印中的二维码信息追溯到具体申请人
- 支持矢量数据（SHP）和栅格数据（GeoTIFF）两种主流空间数据格式

---

## 功能特性

### 核心业务

| 功能 | 说明 |
|------|------|
| **双级审批流程** | 两级管理员依次审批，实时状态追踪，支持批量审批 |
| **二维码水印系统** | 在矢量/栅格数据中生成、嵌入、提取二维码水印 |
| **多算法水印支持** | LSB、DWT（离散小波变换）、直方图平移三种栅格水印算法，保留 GeoTIFF 坐标信息 |
| **HMAC-SHA256 签名** | 密码学签名防止水印伪造与篡改 |
| **申请撤回** | 用户可在审批前撤回已提交的申请 |
| **数据召回投票** | 民主化召回机制，超过 50% 管理员反对即触发数据召回 |
| **管理员晋升** | 员工可申请成为管理员，需 66% 现有管理员投票通过 |

### 平台能力

| 功能 | 说明 |
|------|------|
| **角色权限控制** | 员工、管理员（adm1/adm2/adm3），分阶段审批权限 |
| **JWT 认证** | Access + Refresh Token 双令牌，自动续期 |
| **实时聊天** | Socket.IO 事件驱动，HTTP 轮询兜底 |
| **通知系统** | 定向通知 + 全局公告 |
| **操作审计日志** | 全量操作记录，支持按用户、操作类型、时间范围筛选 |
| **数据看板** | 管理员/员工双视角仪表盘，ECharts 可视化 |
| **中英双语** | 全站 49 个页面、1200+ 翻译键，运行时一键切换 |
| **Grafana 监控** | 自动配置 11 个监控面板（请求量、延迟、错误率、业务指标） |
| **日志聚合** | Loki + Promtail 集中日志查看 |

### 技术亮点

- **双数据库架构** — MySQL 存业务数据，PostgreSQL + PostGIS 存空间数据
- **Redis 缓存层** — 热点查询缓存，优雅降级（缓存不可用时自动回源）
- **WebSocket 实时推送** — Socket.IO 驱动的申请状态变更通知
- **Prometheus 指标** — 请求延迟、错误率、业务 KPI 暴露于 `/metrics`
- **用户级限流** — 基于 JWT 身份的限流（非 IP 级），覆盖所有敏感接口
- **请求拦截器** — Axios 拦截器自动注入 Token、401 自动刷新
- **路由懒加载** — Dynamic Import 实现代码分割，优化首屏加载
- **3D 粒子背景** — Three.js 驱动的登录页动态效果

---

## 系统架构

```
                         ┌─────────────────────────────────────────────────────┐
                         │                   前端 (Vue 3)                      │
                         │  ┌──────────┐ ┌──────────────┐ ┌───────────┐       │
                         │  │  Vue 3   │ │ Element Plus │ │   Pinia   │       │
                         │  │  (SFC)   │ │  (UI 组件库)  │ │ (状态管理) │       │
                         │  └──────────┘ └──────────────┘ └───────────┘       │
                         │  ┌──────────┐ ┌──────────────┐ ┌───────────┐       │
                         │  │vue-router│ │ vue-i18n     │ │ Socket.IO │       │
                         │  │ (懒加载)  │ │ (中/英文)    │ │ (实时通信) │       │
                         │  └──────────┘ └──────────────┘ └───────────┘       │
                         └───────────────────────┬─────────────────────────────┘
                                                 │ HTTP (JWT) + WebSocket
                                                 ▼
                         ┌─────────────────────────────────────────────────────┐
                         │                   后端 (Flask)                      │
                         │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
                         │  │ Flask-RESTful│ │ Flask-JWT    │ │Flask-SocketIO│ │
                         │  │   (API)      │ │  (认证)      │ │ (WebSocket) │ │
                         │  └──────────────┘ └──────────────┘ └─────────────┘ │
                         │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
                         │  │ SQLAlchemy   │ │  Redis Cache │ │ Prometheus  │ │
                         │  │   (ORM)      │ │  (缓存层)    │ │  (指标采集)  │ │
                         │  └──────────────┘ └──────────────┘ └─────────────┘ │
                         │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
                         │  │ Flask-Limiter│ │   rasterio   │ │ LSB/DWT/   │ │
                         │  │  (接口限流)   │ │  (瓦片切片)   │ │ Histogram  │ │
                         │  └──────────────┘ └──────────────┘ │ (水印算法)  │ │
                         └───────────┬─────────────────────────┴─────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
    ┌───────────────────┐  ┌──────────────┐  ┌───────────────────┐
    │    MySQL 8.0      │  │   Redis 7    │  │ PostgreSQL+PostGIS │
    │  用户/申请/日志    │  │   缓存层     │  │  矢量/栅格空间数据  │
    └───────────────────┘  └──────────────┘  └───────────────────┘

    监控栈:
    ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
    │  Prometheus  │───▶│   Grafana    │◀───│  Loki + Promtail │
    │  (指标采集)   │    │ (可视化+告警) │    │   (日志聚合)      │
    └──────────────┘    └──────────────┘    └──────────────────┘
```

---

## 技术栈

<table>
<tr><th>层级</th><th>技术</th><th>用途</th></tr>
<tr><td rowspan="9"><b>前端</b></td><td>Vue 3 + Composition API</td><td>响应式 UI 框架</td></tr>
<tr><td>Element Plus</td><td>企业级 UI 组件库</td></tr>
<tr><td>Pinia</td><td>状态管理</td></tr>
<tr><td>Vue Router</td><td>路由守卫 + 懒加载</td></tr>
<tr><td>vue-i18n</td><td>中英文国际化</td></tr>
<tr><td>Axios</td><td>HTTP 客户端 + 拦截器</td></tr>
<tr><td>Socket.IO Client</td><td>WebSocket 实时通信</td></tr>
<tr><td>Leaflet</td><td>地图渲染与瓦片加载</td></tr>
<tr><td>ECharts</td><td>数据看板图表</td></tr>
<tr><td rowspan="8"><b>后端</b></td><td>Flask + Flask-RESTful</td><td>REST API 框架</td></tr>
<tr><td>Flask-JWT-Extended</td><td>JWT 认证</td></tr>
<tr><td>Flask-SocketIO</td><td>WebSocket 实时事件</td></tr>
<tr><td>SQLAlchemy</td><td>ORM 双数据库绑定</td></tr>
<tr><td>Flask-Limiter</td><td>API 限流</td></tr>
<tr><td>rasterio / geopandas</td><td>空间数据处理</td></tr>
<tr><td>qrcode / pyzbar</td><td>二维码水印生成/提取</td></tr>
<tr><td>prometheus_client</td><td>指标采集</td></tr>
<tr><td rowspan="3"><b>数据库</b></td><td>MySQL 8.0</td><td>业务数据</td></tr>
<tr><td>PostgreSQL + PostGIS</td><td>空间数据</td></tr>
<tr><td>Redis 7</td><td>缓存与会话存储</td></tr>
<tr><td rowspan="5"><b>运维</b></td><td>Docker + docker-compose</td><td>容器化部署（可选，9 个服务）</td></tr>
<tr><td>Prometheus + Grafana</td><td>监控 + 告警 + 可视化</td></tr>
<tr><td>Loki + Promtail</td><td>日志聚合</td></tr>
<tr><td>GitHub Actions</td><td>CI/CD 流水线</td></tr>
<tr><td>Ruff + ESLint + pre-commit</td><td>代码规范与 Git Hooks</td></tr>
</table>

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0
- PostgreSQL（需启用 PostGIS 扩展）
- Redis 7（可选，缓存功能会在不可用时优雅降级）

### 后端启动

```bash
cd testrealend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env  # 编辑 .env 填写数据库配置
python app.py
```

后端运行于 http://localhost:5003

### 前端启动

```bash
cd testrealfrontol
npm install
cp .env.example .env  # 默认连接 http://localhost:5003
npm run dev
```

前端运行于 http://localhost:5173

### Docker 部署（可选）

> 项目提供了 Docker 配置文件（`docker-compose.yml`、各服务 `Dockerfile`），但实际开发中并未使用。如果你熟悉 Docker，可以尝试一键启动全部服务：

```bash
docker-compose up -d
```

启动后访问：
- 前端：http://localhost
- 后端 API：http://localhost:5003
- Grafana 监控：http://localhost:3000（默认账号 admin / geodata_grafana）

---

## 项目结构

```
GeoData-Security-System/
├── testrealend/                        # Flask 后端
│   ├── app.py                          # 应用入口
│   ├── config.py                       # 环境配置
│   ├── extension/
│   │   └── extension.py                # Flask 扩展初始化
│   ├── model/                          # SQLAlchemy 数据模型（29 个）
│   ├── resource/                       # API 接口（76 个路由）
│   ├── algorithm/                      # 水印算法（LSB / DWT / 直方图平移）
│   ├── utils/
│   │   ├── cache.py                    # Redis 缓存层
│   │   ├── metrics.py                  # Prometheus 指标
│   │   ├── websocket.py                # Socket.IO 事件处理
│   │   ├── user_limiter.py             # 用户级限流
│   │   ├── logging_config.py           # 日志配置
│   │   └── log_helper.py              # 审计日志工具
│   ├── tests/                          # Pytest 测试套件
│   └── Dockerfile
│
├── testrealfrontol/                    # Vue 3 前端
│   ├── src/
│   │   ├── main.js                     # 应用入口
│   │   ├── locales/                    # i18n 语言包
│   │   │   ├── zh-CN.js                # 中文
│   │   │   └── en-US.js                # 英文
│   │   ├── router/index.js             # 路由定义 + 守卫
│   │   ├── stores/userStore.js         # Pinia 认证状态
│   │   ├── views/                      # 页面组件（49 个）
│   │   ├── components/                 # 通用组件
│   │   │   └── common/
│   │   │       ├── LanguageSwitcher.vue # 语言切换器
│   │   │       ├── LoadingSkeleton.vue  # 骨架屏
│   │   │       ├── EmptyState.vue       # 空状态
│   │   │       └── NotificationCenter.vue # 通知中心
│   │   └── api/                        # API 服务层（10 个模块）
│   └── Dockerfile
│
├── docker-compose.yml                  # 容器编排（9 个服务）
├── prometheus.yml                      # Prometheus 采集配置
├── loki-config.yml                     # Loki 日志配置
├── promtail-config.yml                 # Promtail 日志采集
├── grafana/provisioning/               # Grafana 自动配置
│   ├── datasources/                    # 数据源（Prometheus + Loki）
│   ├── dashboards/                     # 仪表盘 JSON
│   └── alerting/                       # 告警规则
├── .github/workflows/ci.yml           # GitHub Actions CI
├── .pre-commit-config.yaml             # Pre-commit Hooks
└── LICENSE
```

---

## API 文档

后端提供 RESTful API，主要接口如下：

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/register` | 员工注册 |
| POST | `/api/login` | 登录（员工/管理员） |
| POST | `/api/refresh-token` | 刷新 Token |
| POST | `/api/logout` | 退出登录 |

### 数据申请

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/submit_application` | 提交数据申请 |
| GET | `/api/get_applications` | 获取申请列表 |
| PUT | `/api/applications/{id}/withdraw` | 撤回待审申请 |
| POST | `/api/adm1_pass` | 一级审批 |
| POST | `/api/adm2_pass` | 二级审批 |
| POST | `/api/admin/batch_review` | 批量审批 |

### 水印

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/generate_watermark` | 生成二维码水印 |
| POST | `/api/embedding_watermark` | 嵌入水印 |
| POST | `/api/vector/extract` | 提取水印 |
| GET | `/api/raster_tiles/{id}/{z}/{x}/{y}.png` | 栅格瓦片服务 |

### 系统管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查（DB + Redis） |
| GET | `/metrics` | Prometheus 指标 |
| GET | `/api/admin/dashboard` | 管理员数据看板 |
| GET | `/api/admin/logs` | 操作审计日志 |
| POST | `/api/recall/create` | 创建数据召回提案 |
| POST | `/api/recall/{id}/vote` | 召回投票 |

> 运行时访问 `/apidocs/` 可查看完整的 Swagger API 文档。

---

## 部署指南

### 生产环境

**后端**（Gunicorn + eventlet，支持 Socket.IO）

```bash
cd testrealend
gunicorn -w 4 -b 0.0.0.0:5003 -k eventlet "app:create_app()"
```

**前端**（构建后用 Nginx 托管）

```bash
cd testrealfrontol
npm run build
# 将 dist/ 目录配置到 Nginx
```

### Docker 部署（可选）

```bash
docker-compose up -d --build    # 启动全部服务
docker-compose logs -f backend  # 查看后端日志
docker-compose down             # 停止全部服务
```

---

## 贡献指南

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/你的功能`
3. 提交更改：`git commit -m 'feat: 添加某个功能'`
4. 推送分支：`git push origin feature/你的功能`
5. 提交 Pull Request

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

<div align="center">

**为地理空间数据安全而生**

</div>
