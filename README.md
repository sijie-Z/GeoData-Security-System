# 空间数据安全分发与溯源系统

<div align="center">

![Version](https://img.shields.io/badge/version-v3.0-blue?style=flat-square)
![CI](https://img.shields.io/github/actions/workflow/status/sijie-Z/GeoData-Security-System/ci.yml?branch=main&style=flat-square&label=CI)
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

覆盖矢量（SHP）与栅格（GeoTIFF）数据的完整生命周期管理——从用户申请、双级审批、个性化指纹水印，到安全分发、泄露取证与可验证证据链。

[功能特性](#功能特性) · [系统架构](#系统架构) · [快速开始](#快速开始) · [API 文档](#api-文档) · [质量保障](#质量保障) · [部署指南](#部署指南) · [项目结构](#项目结构)

</div>

---

## 项目简介

系统当前版本为 **v3.0**（上一稳定版本：v2.4.0）。在地理空间数据的共享与分发场景中，数据泄露溯源和权限管控是核心难题。v3.0 将系统从"二维码水印 + 双级审批"升级为 **受控分发 → 个体指纹 → 泄露取证 → 可验证证据** 的完整闭环：

- **受控分发**：用户提交数据申请 → 管理员双级审批 → **每次授权生成独立的个性化交付物**（同一数据集，不同领取者得到不同副本）
- **个体指纹**：每份交付物携带 Ed25519 + COSE_Sign1 签名的 QR v2 短载荷（仅含 `fid / delivery_id / kid / issued_at`，不含任何个人信息）与产物哈希（artifact_root），指纹与交付记录一一绑定
- **泄露取证**：上传泄露副本，系统提取指纹并在候选交付中精确指认交付者与交付编号
- **可验证证据**：交付全流程事件写入 append-only 哈希链（canonical CBOR + Ed25519），批次 Merkle 根经 OpenTimestamps 锚定；EVM 第二锚定（AnchorRegistry 合约）测试就绪、待 Sepolia 部署
- 支持矢量数据（SHP）与栅格数据（GeoTIFF）两种主流空间数据格式

---

## 功能特性

### 交付与溯源（v3.0）

| 功能 | 说明 |
|------|------|
| **个性化交付（DownloadDelivery）** | 每次授权生成独立交付物，状态机 `PENDING → PROCESSING → READY / FAILED`；未领取的交付可被复用，用户再次授权则生成新交付与新指纹 |
| **指纹（FID）** | 每次交付一个 128-bit 随机指纹（CSPRNG），编入签名的 QR v2 载荷后随水印嵌入产物；旧 v1 文本 QR 保持兼容读取 |
| **Ed25519 + COSE_Sign1** | 采用 RFC 9052 标准签名结构与 RFC 8949 canonical CBOR（类型白名单、拒绝浮点）；替代旧 64-bit 截断 HMAC |
| **证据链** | 交付全流程事件按交付分链写入 append-only 哈希链（`stream + seq` 绑定、UTC 整秒规范化）；验证可检测篡改并定位断点（`broken_at`） |
| **Merkle 批次锚定** | Merkle 叶节点绑定批次大小与位置，批量快照生成根哈希；锚定记录携带事件数与链头哈希，保证完整性 |
| **OpenTimestamps 锚定** | 真实网络客户端（httpx 直连公共 OTS 日历）提交批次根；失败自动降级 `pending`，不阻塞业务 |
| **EVM 第二锚定（演示）** | `contracts/AnchorRegistry.sol`（permissionless，重复锚定 revert）+ EVMAnchorProvider（web3 本地签名）；eth-tester 内存链全流程测试通过；**部署状态：待 Sepolia 部署** |
| **CIDv1 内容标识** | 产物根哈希以 CIDv1（multiformats raw codec）写入个性化完成事件 |
| **泄露取证** | 管理端上传泄露副本（SHP / ZIP / 图片，含 zip 炸弹与路径穿越防护）→ 解码 QR 并验签 → 与候选交付指纹比对 → 定位用户与交付编号；验证接口不返回 PII |
| **交付台账检索** | 按 用户 / 指纹（前缀）/ 交付编号 / 时间段 四维组合检索（另支持申请 ID）；员工仅见本人，管理员全量 |

> **口径说明**：FID 用于唯一标识（并非保密载荷，安全来自签名与服务端绑定）；当前方案不承诺抗合谋攻击；OpenTimestamps 证明的是"该证据承诺在某时间之前已存在"。

### 鲁棒性实验室（v3.0）

| 功能 | 说明 |
|------|------|
| **矢量方案对比** | D-QIM（差分域 QIM：载体为边坐标差分，抗平移）vs legacy（绝对坐标域 QIM）；同一攻击矩阵下实测对比 |
| **栅格五算法** | LSB / DWT / 直方图平移（三者可逆）＋ blind_watermark（抗裁剪盲水印）＋ IW-DCT（invisible-watermark 风格 DCT 盲提取） |
| **攻击矩阵** | 矢量：平移 / 缩放 / 删点 / 噪声 / 简化；栅格：JPEG / 缩放 / 裁剪 / 旋转 / 噪声 / 模糊 |
| **多试验系统** | 固定种子可复现，1–10 轮重复试验，成功率与 NC 均值聚合 |
| **强度扫描** | 每类攻击 5 档强度阶梯，前端绘制检出率曲线 |
| **攻击源码可查** | 后端 `inspect.getsource` 返回真实攻击实现，前端 highlight.js 高亮，行号锚点（`#L{n}`）可分享 |
| **指标词典** | NC / BER / 解码成功率等指标的解释、阈值口径与文档抽屉 |

### 核心业务

| 功能 | 说明 |
|------|------|
| **双级审批流程** | 两级管理员依次审批，实时状态追踪，支持批量审批 |
| **二维码水印系统** | 在矢量/栅格数据中生成、嵌入、提取二维码水印（v2 短载荷，兼容 v1） |
| **多算法水印支持** | 矢量：D-QIM / legacy；栅格五种：LSB、DWT、直方图平移（可逆）、blind_watermark、IW-DCT，保留 GeoTIFF 坐标信息 |
| **Ed25519 签名** | 密码学签名防止水印伪造与篡改（RFC 9052 COSE_Sign1；旧 v1 HMAC 兼容读取） |
| **申请撤回** | 用户可在审批前撤回已提交的申请 |
| **数据召回投票** | 民主化召回机制，管理员反对比例 ≥50% 即触发数据召回（提案人回避） |
| **管理员晋升** | 员工可申请成为管理员，需 66% 现有管理员投票通过 |

### 平台能力

| 功能 | 说明 |
|------|------|
| **角色权限控制** | 员工、管理员（adm1/adm2/adm3），分阶段审批权限 |
| **JWT 认证** | Access + Refresh Token 双令牌，自动续期 |
| **实时聊天** | Socket.IO 事件驱动（threading 模式）；Windows 下自动降级为 HTTP 轮询 |
| **通知系统** | 定向通知 + 全局公告 |
| **操作审计日志** | 关键操作留痕，支持按用户/编号/动作/状态/时间段筛选，并可流式导出 CSV（5 万行上限，截断时响应头标记） |
| **批量嵌入作业** | 管理端多选申请发起后台批量嵌入（≤50 项/作业，单一活动作业），真实进度轮询、失败项一键重跑、僵尸作业自动清扫 |
| **下载统计看板** | 管理端仪表盘内置：7/14/30/90 天窗口、逐日趋势、Top10 用户 / 数据、周环比，支持 CSV 导出 |
| **数据看板** | 管理员/员工双视角仪表盘，ECharts 可视化 |
| **中英双语** | 44 个路由页面、2600+ 翻译键，中英键集完全对齐，运行时一键切换 |
| **Grafana 监控** | 自动配置 2 块仪表盘（业务概览 11 面板 + 日志 5 面板）与告警规则 |
| **日志聚合** | Loki + Promtail 集中日志查看 |

### 界面体系

| 功能 | 说明 |
|------|------|
| **双主题** | 深色（Linear 风 · 靛蓝）＋ 浅色（Vercel 风极简）双模式，员工端 / 管理端 / 实验室页面全覆盖；登录、注册等品牌页保持固定品牌视觉 |
| **设计令牌** | L1 色阶 + L2 语义映射的双值架构，一套 token 驱动两种模式；Element Plus 暗色变量品牌化覆写 |
| **动效纪律** | 主题切换过渡窗口、逐组件 reduced-motion 降级（循环动画关闭、骨架屏降频） |
| **辅助体系** | 指标词典（阈值口径解释 + 文档抽屉）、质量看板与鲁棒性实验室首访引导（ElTour）、哈希文本组件、水印图超采样预览 |

### 技术亮点

- **双数据库架构** — MySQL 存业务数据，PostgreSQL + PostGIS 存空间数据
- **进程内缓存层** — 内置内存缓存（无外部依赖，Redis 仅作为可选限流存储）
- **WebSocket 实时推送** — Socket.IO 驱动的申请状态变更通知（HTTP 轮询兜底）
- **Prometheus 指标** — 请求延迟、错误率、业务 KPI 暴露于 `/metrics`
- **用户级限流** — 基于 JWT 身份的限流（非 IP 级），覆盖所有敏感接口
- **可验证证据链** — canonical CBOR + Ed25519 + Hash Chain + Merkle + OpenTimestamps 外部锚定
- **请求拦截器** — Axios 拦截器自动注入 Token、401 自动刷新
- **路由懒加载** — Dynamic Import 实现代码分割，优化首屏加载
- **3D 可视化** — Three.js 粒子首屏 + 管理端数据流 3D 地球（three-globe，投递弧线实时来自交付统计）

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
                         │  │ SQLAlchemy   │ │    Cache     │ │ Prometheus  │ │
                         │  │   (ORM)      │ │ (进程内缓存) │ │  (指标采集)  │ │
                         │  └──────────────┘ └──────────────┘ └─────────────┘ │
                         │  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐ │
                         │  │ Flask-Limiter│ │   rasterio   │ │  水印算法    │ │
                         │  │  (接口限流)   │ │  (瓦片切片)   │ │ (矢量+栅格) │ │
                         │  └──────────────┘ └──────────────┘ │  证据链      │ │
                         └───────────┬─────────────────────────┴─────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
    ┌───────────────────┐  ┌──────────────┐  ┌───────────────────┐
    │    MySQL 8.0      │  │   Redis 7    │  │ PostgreSQL+PostGIS │
    │  用户/申请/日志    │  │ 可选限流存储 │  │  矢量/栅格空间数据  │
    └───────────────────┘  └──────────────┘  └───────────────────┘

    监控栈:
    ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
    │  Prometheus  │───▶│   Grafana    │◀───│  Loki + Promtail │
    │  (指标采集)   │    │ (可视化+告警) │    │   (日志聚合)      │
    └──────────────┘    └──────────────┘    └──────────────────┘
```

```
v3.0 交付与取证链路:

   申请获批 ─▶ 个性化交付物 ─┬─ FID：128-bit 随机指纹（每次交付唯一）
                           ├─ QR v2：Ed25519 + COSE_Sign1 签名（不含个人信息）
                           ├─ 水印嵌入：矢量 D-QIM / 栅格 LSB 等
                           └─ artifact_root：SHA-256 产物哈希
                                  │
                                  ▼ 授权下载
   证据链事件流 ─▶ Hash Chain ─▶ 批次 Merkle Root ─┬─▶ OpenTimestamps（Bitcoin）
                                                   └─▶ EVM AnchorRegistry（演示·待部署）

   泄露副本 ─▶ 取证上传 ─▶ 指纹比对 ─▶ 定位：用户 / 交付编号 ─▶ 证据链核查
```

---

## 技术栈

<table>
<tr><th>层级</th><th>技术</th><th>用途</th></tr>
<tr><td rowspan="10"><b>前端</b></td><td>Vue 3 + Composition API</td><td>响应式 UI 框架</td></tr>
<tr><td>Element Plus</td><td>企业级 UI 组件库</td></tr>
<tr><td>Pinia</td><td>状态管理</td></tr>
<tr><td>Vue Router</td><td>路由守卫 + 懒加载</td></tr>
<tr><td>vue-i18n</td><td>中英文国际化</td></tr>
<tr><td>Axios</td><td>HTTP 客户端 + 拦截器</td></tr>
<tr><td>Socket.IO Client</td><td>WebSocket 实时通信</td></tr>
<tr><td>Leaflet</td><td>地图渲染与瓦片加载</td></tr>
<tr><td>ECharts (vue-echarts)</td><td>数据看板图表</td></tr>
<tr><td>three.js + three-globe</td><td>3D 粒子首屏与数据流地球</td></tr>
<tr><td rowspan="11"><b>后端</b></td><td>Flask + Flask-RESTful</td><td>REST API 框架</td></tr>
<tr><td>Flask-JWT-Extended</td><td>JWT 认证</td></tr>
<tr><td>Flask-SocketIO</td><td>WebSocket 实时事件（threading 模式）</td></tr>
<tr><td>SQLAlchemy</td><td>ORM 双数据库绑定</td></tr>
<tr><td>Flask-Limiter</td><td>API 限流</td></tr>
<tr><td>rasterio / geopandas</td><td>空间数据处理</td></tr>
<tr><td>qrcode / pyzbar</td><td>二维码生成/提取</td></tr>
<tr><td>cryptography / cbor2</td><td>Ed25519 + COSE_Sign1 / canonical CBOR</td></tr>
<tr><td>blind_watermark</td><td>盲水印算法（DWT-DCT-SVD）</td></tr>
<tr><td>web3.py / eth-tester <sup>可选</sup></td><td>EVM 锚定与合约测试</td></tr>
<tr><td>prometheus_client</td><td>指标采集</td></tr>
<tr><td><b>合约</b></td><td>Solidity 0.8</td><td>AnchorRegistry 锚定合约（演示 · 待 Sepolia 部署）</td></tr>
<tr><td rowspan="3"><b>数据库</b></td><td>MySQL 8.0</td><td>业务数据</td></tr>
<tr><td>PostgreSQL + PostGIS</td><td>空间数据</td></tr>
<tr><td>Redis 7（可选）</td><td>限流存储（缓存为进程内实现）</td></tr>
<tr><td rowspan="5"><b>运维</b></td><td>Docker + docker-compose</td><td>容器化部署（可选，9 个服务）</td></tr>
<tr><td>Prometheus + Grafana</td><td>监控 + 告警 + 可视化（2 块仪表盘）</td></tr>
<tr><td>Loki + Promtail</td><td>日志聚合</td></tr>
<tr><td>GitHub Actions</td><td>CI 三 job + CodeQL + gitleaks</td></tr>
<tr><td>Ruff + ESLint + pre-commit</td><td>代码规范与 Git Hooks</td></tr>
</table>

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- MySQL 8.0
- PostgreSQL（需启用 PostGIS 扩展）
- Redis（可选：仅用于限流存储；缓存层为进程内实现，无外部依赖）

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

后端运行于 http://localhost:5003（首次启动自动建表；端口可用环境变量 `PORT` 覆盖）

### 前端启动

```bash
cd testrealfrontol
npm install
cp .env.example .env  # 默认连接 http://localhost:5003
npm run dev
```

前端运行于 http://localhost:5173（端口被占用时自动顺延）

### Docker 部署（可选）

> 项目提供了完整的 Docker 编排（`docker-compose.yml`、各服务 `Dockerfile`）；日常开发推荐在本机直接启动，如需容器化可一键启动全部服务：

```bash
docker-compose up -d
```

启动后访问：
- 前端：http://localhost
- 后端 API：http://localhost:5003
- Grafana 监控：http://localhost:3000（账号密码请在部署时通过环境变量覆盖）

---

## 项目结构

```
GeoData-Security-System/
├── testrealend/                        # Flask 后端
│   ├── app.py                          # 应用入口（统一注册 133 个 API 资源）
│   ├── config.py                       # 环境配置
│   ├── crypto/                         # COSE_Sign1(Ed25519) / canonical CBOR / QR v2 载荷 / 密钥管理
│   ├── delivery/                       # 个性化交付（指纹生成、QR v2 渲染、产物哈希与 CIDv1）
│   ├── evidence/                       # 证据链（Hash Chain / Merkle / OpenTimestamps / EVM 锚定）
│   ├── extension/
│   │   └── extension.py                # Flask 扩展初始化
│   ├── model/                          # SQLAlchemy 数据模型（34 个文件）
│   ├── resource/                       # API 资源（含 forensics / batch_embed / 日志与统计导出）
│   ├── algorithm/                      # 水印算法（矢量 D-QIM/legacy；栅格 5 种；鲁棒性实验引擎）
│   ├── utils/                          # 缓存 / 指标 / WebSocket / 限流 / 审计日志工具
│   ├── tests/                          # Pytest 测试套件（51 个文件 / 460+ 测试函数）
│   └── Dockerfile
│
├── testrealfrontol/                    # Vue 3 前端
│   ├── src/
│   │   ├── main.js                     # 应用入口
│   │   ├── assets/styles/design-system.css  # 双主题令牌体系（L1 色阶 + L2 语义）
│   │   ├── composables/useTheme.js     # 主题切换与本地持久化
│   │   ├── locales/                    # i18n（zh-CN / en-US，2600+ 键，完全对齐）
│   │   ├── router/index.js             # 路由定义 + 守卫
│   │   ├── views/                      # 视图组件（48 个，44 条路由）
│   │   ├── components/                 # 通用组件（哈希文本 / 通知中心 / 交付链 / 图像对比…）
│   │   └── api/                        # API 服务层（10 个模块）
│   └── Dockerfile
│
├── contracts/                          # AnchorRegistry.sol + Sepolia 部署脚本
├── docker-compose.yml                  # 容器编排（9 个服务）
├── grafana/provisioning/               # Grafana 自动配置（2 块仪表盘 / 数据源 / 告警规则）
├── prometheus.yml                      # Prometheus 采集配置
├── loki-config.yml                     # Loki 日志配置
├── promtail-config.yml                 # Promtail 日志采集
├── .github/workflows/                  # CI 三 job + CodeQL + gitleaks 等 5 个工作流
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
| POST | `/api/embedding_watermark` | 栅格水印嵌入（lsb / dwt / histogram / blind / iw_dct） |
| POST | `/api/vector/extract` | 提取水印 |
| GET | `/api/raster_tiles/{id}/{z}/{x}/{y}.png` | 栅格瓦片服务 |

### 交付与取证（v3.0）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/forensics/verify` | 样本验证与指纹定位（上传文件或 qr_text） |
| POST | `/api/forensics/trace` | 输出二维码溯源链路 |
| GET | `/api/forensics/deliveries` | 交付台账（四维检索：用户 / 指纹 / 编号 / 时间段） |
| GET | `/api/forensics/deliveries/{uuid}` | 交付详情（含证据链状态与锚定信息） |
| GET | `/api/forensics/deliveries/stats` | 交付统计（状态 / 算法 / 锚定桶 / 链健康度） |
| POST | `/api/forensics/anchor/build` | 构建批次锚定（默认 OpenTimestamps，可选 EVM） |
| GET | `/api/forensics/anchors` | 锚定批次列表 |
| GET | `/api/forensics/keyinfo` | 公钥信息（kid → 公钥指纹，供独立验签） |

### 批量作业与统计导出

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/watermark/batch_embed_jobs` | 创建批量嵌入作业 |
| GET | `/api/watermark/batch_embed_jobs` | 作业列表 |
| GET | `/api/watermark/batch_embed_jobs/{uuid}` | 作业进度与逐项结果 |
| GET | `/api/admin/logs/export` | 审计日志 CSV 导出 |
| GET | `/api/admin/download_stats` | 下载统计（看板数据源） |
| GET | `/api/admin/download_stats/export` | 下载统计 CSV 导出 |

### 鲁棒性实验

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/robustness/run` | 运行实验（矩阵 / 强度扫描，矢量或栅格） |
| GET | `/api/robustness/runs` | 历史运行列表 |
| GET | `/api/robustness/runs/{id}` | 运行详情（含汇总与强度档位） |
| GET | `/api/robustness/attacks/meta` | 攻击实现源码（供前端源码抽屉） |

### 系统管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查（DB + 缓存） |
| GET | `/metrics` | Prometheus 指标 |
| GET | `/api/admin/dashboard` | 管理员数据看板 |
| GET | `/api/admin/logs` | 操作审计日志 |
| POST | `/api/recall/create` | 创建数据召回提案 |
| POST | `/api/recall/{id}/vote` | 召回投票 |

> 安装可选依赖 `flasgger` 后，可在 `/apidocs/` 查看交互式 Swagger API 文档。

---

## 质量保障

- **后端测试**：`testrealend/tests/` 51 个测试文件、460+ 个测试函数（基于文件型 SQLite，无需外部数据库），覆盖指纹交付、证据链防篡改、取证定位（3 用户 E2E）、EVM 锚定（eth-tester）等核心链路

  ```bash
  cd testrealend
  python -m pytest
  ```

- **CI 流水线**（GitHub Actions）：`backend`（Ruff + 全量 Pytest）、`frontend`（ESLint + 构建）、`docker`（镜像构建）三个 job
- **安全扫描**：CodeQL（Python / JavaScript / TypeScript）+ gitleaks 密钥扫描
- **规范与钩子**：Ruff（lint + format）、ESLint、pre-commit hooks

---

## 部署指南

### 生产部署

- **后端**：容器镜像使用 Gunicorn 托管（完整命令见 `testrealend/Dockerfile`）；也可直接 `python app.py` 运行（内置线程化服务器，适合单机/演示环境）
- **前端**：`npm run build` 后将 `dist/` 交给 Nginx 托管；仓库 Compose 中的前端容器已内置该配置（`/api` 反向代理到后端）
- **扩展性说明**：Socket.IO 运行于 threading 模式，多进程/多副本横向扩展需外接消息队列（当前未内置）；Windows 环境下 Socket.IO 自动禁用，实时通知退化为 HTTP 轮询

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

> 建议先安装 pre-commit 钩子（配置见 `.pre-commit-config.yaml`）：`pip install pre-commit && pre-commit install`

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

<div align="center">

**为地理空间数据安全而生**

</div>
