# Changelog — GeoData Security System

All notable changes to this project are documented in this file.

---

## [Unreleased] — 2026-10-10 (UI 收尾两波 + 全站 axe 无障碍修复波 + 构建分块)

> **范围与诚实声明**：本段全部提交位于**本地**（UI 两波已合入本地 `main`；axe 波在 `fix/a11y-axe`），**未推 GitHub**（账号暂停期间积压）。最近发布 tag 仍为 **v2.4.0**；v3.0 功能段见下节。

### 波 1 · UI 收尾（已合入本地 main）

- **管理仪表盘骨架高保真重建**（`eb7cd87`）：根因坐实 = v2.1 改版后遗留的死类 `.stats-grid`/`.stat-card`（全仓无定义）导致 loading 态乱条；改用真实布局类重建（hero / 地球 460px / KPI×4 / 快捷动作 / 图表×2），骨架块↔真实布局 Δ高 105 对中 103 对精确 0、最深残差 ±3px 且为数据驱动；390px 实测同步；全骨架带 `motion-shimmer` 标记（reduced-motion 下 3s 降频）。
- **员工仪表盘骨架补齐**（`9b6e721`）：新增图表行与快捷/公告行占位（原先只盖 hero+KPI，数据落地大幅跳动）。
- **v-loading 遮罩摘除**（`e29ae35`）：仪表盘 v-loading 与骨架重复 → 摘除遮罩，骨架即加载语言（`aria-busy` 保留）。
- **全站恰一 h1 收尾**（`13b7807` + 合并 `124fdb6`）：6 个旧页标题 h2→h1 + 5 个零 h1 路由收尾（data_download/data_application `span→h1`、watermark-quality/robustness `h2→h1`、employee chat 新增可见 h1）→ 40 路由（含 404）**恰一 h1**。
- **死类扫描结论**：53 个 loading 区域、423 个类、14 个候选逐条人工复核 = 12 条视觉惰性（报告不修）+ 2 条随重写移除。

### 波 2 · 全站 axe 无障碍修复（`fix/a11y-axe`，本地分支）

commits：`3e1b639`（地标骨架）、`f6789cf`（axe 修复波）、`3131d5c`（构建分块）、本条目所在提交（文档）。基线 = 40 路由 axe 全量扫描（主 checkout :5173）；修复项逐类：

- **地标体系**（`3e1b639`）：两个壳 `content-panel` → `<main tabindex="0">`（landmark-one-main 40/40 → 0；主内容区溢出时可键盘聚焦滚动）、侧栏 → `<nav>`；region 计数大幅下降。404 兜底路由经新增 `NotFoundRoute.vue` 包装补 `<main>`（NotFound.vue 按红线未动）。
- **el-tour 上游补丁**：WQ 与 RobustnessLab 引导打开后修正 EP 弹层（`header→role=presentation`、`title→aria-level=2`），landmark-no-duplicate-banner / landmark-unique / aria-required-attr 三规则清零；引导功能零回归（六步全走）。
- **可访问名**：图标圆钮 `aria-label` ×5；`el-select` ×5 与 `el-date-picker` 用 `aria-label`（EP 2.14 `ariaLabel` 直通内部 combobox，实测 axe 认）；`el-pagination` 内部「每页条数」选择器经 `utils/a11yPatches` 补丁补名（logs/anchors/notifications/operation_history/data_viewing）；上传触发区补 `.sr-only` 文本。
- **图片 alt**：information_list 头像用员工姓名；`WatermarkImage` 组件新增 `alt` prop，8 处调用点按场景传 alt（二维码列/预览、数据预览、恢复图、嵌入缩略图、抽取水印）。
- **对比度 6 处**：login 角色未选中 `#5b6b7d`（4.34→4.99:1）、employee chat append 按钮恢复正常字色、EmptyState CTA（plain 主按钮 3.98→≥4.5）、AdminGuide 三色快捷按钮改 tint 着色式、AdminNotifications 字数统计改语义 token。
- **可滚动区可聚焦**：hot-list / log-list / announcement-list 补 `tabindex=0 + aria-label`；el-table max-height 内部 `.el-scrollbar__wrap` 经补丁补 `tabindex/aria-label`。
- **heading-order 10 页清零**（9 页修复 + 1 页留档）：h1→h4 跳级改 h2（WQ/robustness/anchors 台账）、h1→h3 跳级改 h2（information_add/apply_admin/profile/help/about 等）；同步 scoped 样式选择器；H1 计数不变。
- **留档（含理由）**：`information_add` `.el-upload-list` 的 list×1（EP 将 `div[role=button]` 触发区直渲进 `<ul>`；DOM 重排实测触发 Vue `insertBefore` 崩溃，证据留档）；`approve_application/dual_channel` 的 label×2 / heading-order×1 / empty-table-header×1 已由收尾轮修复清零（`b0484f7`，fix/final-polish）。
- **构建分块**（`3131d5c`）：`vite manualChunks` 拆 `vendor-element`（1,061.60 kB）/ `vendor-echarts`（587.30 kB）/ `vendor-vue`（191.24 kB），入口 index **1,502.81 kB → 247.99 kB**（gzip 483.44 → 80.14 kB）。

### 波 3 · 工程收尾与 CI 无障碍门禁（2026-10-18，fix/final-polish + fix/ci-a11y，本地分支）

- **fix/final-polish 侧栏与审批页收尾**：侧栏 S1–S5（高度填满/自身滚动/激活项滚入/过渡与折叠持久化、折叠态弹出菜单贴齐、`unique-opened` 豁免激活项父菜单，`f5ed885`）；S2 性能（图表 `autoresize` 加 `throttle:160`、取消 EP 折叠换装 301ms 兜底等待，`512622f`/`7559bc3`）；DualChannel 审批页 axe 清零（`b0484f7`）。
- **CI axe 持续门禁（`a11y` job）**：`testrealfrontol/scripts/a11y-smoke.mjs`（playwright + `@axe-core/playwright`，固定版本 `playwright@1.64.1` / `@axe-core/playwright@4.14.0`）扫描公开页 `/login` `/register` `/first_home` 与认证页（`/admin`、`/admin/employee_management/information_list`、`/admin/watermark-quality`、`/employee`、`/employee/data_viewing`、`/employee/chat`）；`critical`/`serious` 违规即红（moderate/minor 仅打印）。CI 以 `FLASK_ENV=testing` SQLite + `testrealend/scripts/ci_seed.py` 种子用户（admin/admin123、TEST001/test123456）起后端，vite dev server（:4173）代理到 :5003；报告 `a11y-report.json` 作为 artifact 上传。门禁首跑即抓出 `/register` 两处对比度 serious（头像占位文字 `#94a3b8` 2.45:1、EP info 提示 `#909399` 3.07:1），本轮已修复为 `#5b6b7d`（5.22/5.46:1）。
- **门禁留档**：`information_add` 不纳入默认扫描 —— `.el-upload-list` 的 axe `list`（serious）为 EP 上游渲染缺陷（`div[role=button]` 直渲进 `<ul>`），DOM 重排实测触发 Vue `insertBefore` 崩溃；解除条件见 `a11y-smoke.mjs` 顶注。

### 波 4 · 安全加固（`fix/authz-round2`，本地分支，2026-10-18）

commits：`2a9d833`（主体）+ `446dc21`（对抗评审收口：CRMark recover/decode 限 admin2、QR_SECRET_KEY 生产 fail-closed、test_download 断言恢复）。依据只读安全审计（二审）修复 **4 高危 + 19 中危**，并收紧会话与密钥默认值：

- **高危 IDOR/越权**：`emp_download_zip` / `request_download_token` 增加 owner-or-admin（JWT number 比对申请人，杜绝枚举 `application_id` 下载他人已批数据）；申请详情与二维码三端点（`/api/applications/<id>`、`/qrcode`、`/qrcode/image`）PII 仅申请人或 admin 可读；`DELETE /api/data/<type>/<id>/delete` 加 admin 门，破坏性删除 + GeoServer 图层删除不再对任意登录用户开放。
- **数据管理写端点**：PUT 数据元信息、SHP/栅格上传、GeoServer 手动发布统一 `@admin_required`（前端均为 admin 路由）。
- **水印取证写面**：verification_records 与原始/提取/比对水印上传加 admin 门；`get_original_watermark` 改 owner-or-admin；`record_download_file` 禁止为他人申请伪造下载审计。
- **CRMark 任意路径**：recover/decode 解析后的 realpath 必须位于 `runtime/crmark` 与 UPLOAD/WATERMARK/EXTRACTED 根之下，越界 404；两端点同时限 `admin2`（与调用页 RasterWatermarkEmbedding 一致，避免跨租户取回/解码 stego 与原图）；正常 embed → decode/recover 流程回归通过。
- **审核子角色隔离**：`batch_review` 按 stage 映射 adm1→admin1 / adm2→admin2；`re_review`、`crmark/embed`、`watermark/batch_embed` 限 admin2；`watermark/batch_generate` 限 admin1；superadmin 始终放行。
- **跨角色信息暴露**：`/api/admin/nav/tree`、`/api/admin/nav/list` 仅 admin（employee 同名路径不受影响）。
- **会话**：logout 同时撤销 refresh token（显式 jti + 每身份登出标记，兼容前端无 body 的 logout），refresh 端点两条路径均校验；新签发 refresh 带亚秒级 `iat_ts`。
- **JWT role claim 收紧**：role claim 显式非 admin* 时直接 403，不再回退 `AdmAccount`（工号撞 `adm_number` 不再越权）；仅无 role claim 的 legacy token 保留 DB 兜底。
- **密钥默认值**：未配置 `SECRET_KEY` / `JWT_SECRET_KEY` 时每次启动生成 `secrets.token_hex` 临时密钥并打印 WARNING；Production 仍 fail-closed，TestingConfig 不受影响。`QR_SECRET_KEY` 同类处置：生产缺失或等于旧公开常量时启动 raise，dev/testing 可临时随机且 QR 往返回归通过；`docker-compose.yml` 与 `.env.example` 同步补为必填。
- **测试**：新增 `tests/test_authz_round2.py` **81** 个安全回归用例（含参数化的员工/adm1/adm3 拒绝用例；每个修复端点"越权拒绝 + 合法放行"双用例；`test_download` 成功路径恢复为 200 + 实体内容断言）；全量 **664 passed / 0 failed**；`ruff check` + `ruff format --check` 双绿。

### 波 5 · 前端工程化清理（`fix/frontend-cleanup`，本地分支，2026-10-28）

- **lint 4925 → 0**：`eslint --fix` 自动修复 4821 条，人工修 104 条残留（no-unused-vars×20、no-empty×5 等）；`no-console` 调整为 allow `[error, warn]`；`npm run lint` 改为 `--max-warnings 0` 硬门禁，CI `frontend` job 自动继承。
- **首屏减重**：`first_home.vue` 的静态 `import * as THREE` 改为挂载后动态 `import('three')`（699.49 kB 移出首访关键路径）；阻断 three 加载时页面完整渲染、仅背景降级。
- **全局错误兜底修复**：`main.js` 移除浏览器 ESM 不存在的 `require('element-plus')`，改为静态 `ElMessage` + i18n 键 + DOM alert banner 兜底（旧版用户提示永不显示，新版探针实测可弹）。
- **未使用依赖清理**：移除 6 个 0 引用依赖；lock 经 `npm install --package-lock-only` 更新。
- **硬编码中文 i18n**：10 处活动 UI 文案改 `$t()`，新增 8 个 zh/en 成对键（2690/2690 对齐）。
- **验证**：build 绿；3 页浅/深像素对照（掩掉时钟/动画后全 0）；axe 与基线一致；console 0。

### 波 6 · 后端性能与运维加固（`fix/backend-perf`，本地分支，2026-10-28）

commits：`7e27f5a`（依赖上限 + 索引/迁移）、`4323ef3`（N+1 批量化）、`23d3bc6` + `de32e53` + `8733f76`（watermark 批量预取）、`fe09b30`（异常口径 + 安全小修 + 回归测试）。

- **依赖防漂移**：`openai>=2.44.0,<3`、`pandas>=3.0.6,<3.1`、`numpy<3`、`pillow<14`（防 CI 自动跳未验证版本）。
- **索引**：`download_record` 四索引 + `download_token`/`embed_file_record`/`send_file_record` 各 application_id 索引；`migrate_add_columns.py` 幂等 CREATE INDEX。
- **N+1**：取证交付列表 200 条实测 **1002 → 6 SELECT**；`batch_generate` 5 → 1；批量端点一次 IN 预取。
- **异常口径**：公告 DB 异常 → 503；密码哈希校验失败关闭（legacy 明文仍可登录一次并升级）。
- **安全小修**：注册预检管理号牌/工号/账号名冲突；refresh 回查账号存在与角色；旧 `emp_download_zip` 补写 DownloadRecord；`record_download_file` 服务端字段；并发 logout 幂等；`re_review`/`adm3_additional_review` 严格布尔。
- **测试**：新增 `test_backend_perf.py` 26 例；全量 690 passed；ruff 双绿。

### 波 7 · 下载/交付路径越界封堵（`fix/path-guard`，本地分支，2026-10-28）

commits：`9b75071`（路径守卫主体）+ `c6a29fd`（评审收口：admin3 提取接口加固）。

- **封堵的漏洞链**：申请 `data_url` 客户端可控 + 下载/交付路径解析无根约束 → 员工提交指向服务器任意文件的"申请"，两级审批后即可下载（或经个性化交付复制下发）。
- **统一路径守卫**（`utils/path_guard.py`）：允许根来自配置（UPLOAD/WATERMARK/EXTRACTED/DELIVERY/runtime；`instance/` 明确排除），`realpath + normcase + commonpath`；越界与不存在统一 None（不泄露存在性）；替换 3 份历史拷贝。
- **申请数据权威化**：忽略客户端 `data_url`/`data_name`，按 `data_id + data_type` 反查 `Shp`/`RasterData`；不存在/非法 → 400。前端契约无影响。
- **交付链**：越界基底 → FAILED、不复制、不烧 token、清理半成品。
- **zip-slip**：两处前缀判断补齐分隔符语义。
- **评审挖出的预存高危已修**：`watermark_extract` 的 admin3 `application_id` 原始字符串拼路径 + `finally` 递归删目录（MySQL 隐式转换下可任意目录写/删）→ 入口整数化+范围校验、路径仅用 DB 整数、文件系统操作前 realpath 包含检查。
- **测试**：新增 `tests/test_path_guard.py` 31 例（UNC/`\?\`/8.3/ADS/盘符相对/junction/大小写矩阵、申请权威化、旧行越界拒绝、交付链、zip-slip、提取零副作用）；合并后全量 721 passed；ruff 双绿。
- **对抗评审**：路径矩阵实测全拒、8 个抽样用例分层回退必红、核心全 CONFIRMED 不可绕。

---

## [v3.0] — 2026-10-09 (Personalized Delivery, Verifiable Evidence Chain & Robustness Lab)

> **开发主线（unreleased on `main`）** — 最近发布 tag 仍为 **v2.4.0**。本段覆盖 v2.4.0 之后合入 main 的全部 v3.0 内容。

### Summary

Elevates the platform from "QR watermark + two-level approval" to a closed loop of **controlled delivery → per-recipient fingerprint → leak forensics → verifiable evidence**:

- **Personalized delivery (DownloadDelivery)**: every authorized download issues an independent artifact (same dataset, different recipient → different copy) carrying a 128-bit fingerprint (FID) in an Ed25519 + COSE_Sign1 signed **QR v2** payload (`v / kid / fid / delivery / issued_at`, no PII) and a recorded artifact hash (`artifact_root`, CIDv1).
- **Evidence chain**: append-only hash chain per delivery (canonical CBOR + Ed25519), Merkle batch snapshots anchored via OpenTimestamps; the EVM second anchor (AnchorRegistry) is test-ready — **pending Sepolia deployment**.
- **Leak forensics**: upload a leaked copy → decode + verify → match delivery fingerprints → lock the delivery record and confirm the deliverer.
- **Robustness lab**: vector matrix (legacy vs D-QIM) and the five raster schemes under one attack matrix, with multi-trial and strength-sweep modes and in-app attack source code.
- **Ops**: async batch embedding jobs, audit-log CSV export, download statistics board, four-dimension delivery search.
- **Design system**: site-wide dark/light dual themes on the two-tier (L1/L2) token architecture.
- **AI**: any OpenAI-compatible endpoint (incl. local models), configurable timeout.
- **Security**: hardcoded map key removed, compose secret hard-fail, non-PII audit trail on forensics endpoints.

**Commits:** 278 after v2.4.0 · **Total changes:** 262 files, +40,859 / −5,996

---

### Backend — Personalized Delivery (`delivery/`, `model/download_delivery.py`)

- **Per-recipient artifacts**: each authorized download runs the delivery pipeline with a `PENDING → PROCESSING → READY / FAILED` state machine; the returned artifact is personalized for that recipient (vector via the D-QIM/legacy embed pipeline, raster via the selected algorithm). Unclaimed, unexpired tokens reuse their READY delivery; FAILED deliveries are re-issued.
- **Fingerprint (FID)**: a 128-bit CSPRNG value per delivery, bound to the delivery record (`fingerprint_id`); `uuid`, `artifact_path`, `artifact_root` and embed metadata (`vr_data`) persisted per delivery; `delivery_id` linkage columns added to download/verification records.
- **Employee download** switched to the personalized delivery token flow.

### Backend — Crypto & QR v2 (`crypto/`)

- **Canonical CBOR** (RFC 8949): deterministic bytes for hashing/signing — sorted keys, type whitelist, floats rejected.
- **COSE_Sign1 (RFC 9052) with Ed25519** (`crypto/cose.py`), key registry with kid management (`model/key_registry.py`; key material git-ignored); public keys exportable via `/api/forensics/keyinfo` for independent verification — replaces the legacy 64-bit truncated HMAC.
- **QR v2 payload** (`crypto/payload.py`): compact short payload `v=2 / kid / fid / delivery / issued_at`; legacy v1 text QR still parses (`{"version": 1, "raw": ...}`), and v1 QR text is persisted at all four generation points so old copies remain verifiable.
- **Strict decode**: `QrPayloadError` contract for all parse/verify failures, payload-vs-header kid binding, empty unprotected header rejection, type-strict `alg` (two adversarial-review fix rounds, items A-1..B-6).

### Backend — Evidence Chain & Anchors (`evidence/`)

- **Hash chain** (`evidence/chain.py`): append-only, per-delivery streams; canonical CBOR + Ed25519 per event; `stream + seq` bound into every event hash (same-second genesis collision eliminated); event timestamps normalized to UTC whole seconds (MySQL DATETIME rounding can no longer break verification); tampering is detectable and localized (`broken_at`).
- **Merkle batch snapshots** (`evidence/merkle.py`): leaves bound to batch size/position; roots carry event count + chain head; anchor completeness checks.
- **OpenTimestamps** (`evidence/anchor.py`): real network client (httpx → public calendar pool); any network failure degrades to `PENDING` and never blocks business.
- **EVM second anchor**: `contracts/AnchorRegistry.sol` (permissionless; duplicate anchor reverts) + `EVMAnchorProvider` (web3 local signing; receipt + on-chain `getTimestamp` check) + py-solc-x deploy script; `POST /api/forensics/anchor/build` accepts `provider=evm` (default OpenTimestamps), embeds a JSON evidence pack and returns an explorer URL; eth-tester in-memory coverage in CI (auto-skip when solc is unavailable). **Deployment status: pending Sepolia.**
- **CIDv1**: artifact roots recorded as CIDv1 (multiformats raw codec, sha2-256, base32-lower — `delivery/artifact.py`) in the personalized completion event; anchor batch list/detail endpoints + safe proof download.

### Backend — Leak Forensics (`resource/forensics_resource.py`)

- **`POST /api/forensics/verify`**: upload a leaked sample (SHP / ZIP / image, zip-bomb + path-traversal defenses) or raw `qr_text` → decode + signature verify → compare against candidate delivery fingerprints → lock the delivery record (uuid / 交付编号) and confirm the deliverer; responses carry no PII.
- **`POST /api/forensics/trace`**: full QR provenance chain for a sample.
- **Delivery ledger** `GET /api/forensics/deliveries`: four-dimension search — user / fingerprint prefix / delivery uuid / time range (+ `application_id`); employees see only their own; id fragments are matched as safe prefixes, not wildcard patterns.
- **`GET /api/forensics/deliveries/stats`**: status / algorithm / anchor-bucket / chain-health aggregates; delivery detail exposes chain state + anchor info.
- **Audit trail**: verify/trace write audit rows with strictly non-PII details (size buckets, coarse context) — trace responses are PII-rich, the audit row is not.
- Tested end-to-end including **3-user localization** (`tests/test_delivery_flow.py::test_three_users_three_fids_roundtrip_and_copy_attack`).

### Backend — Watermark Schemes: D-QIM / blind / IW-DCT

- **D-QIM vector scheme** (`algorithm/vector_dqim.py`): difference-domain QIM — the carrier is edge coordinate differences, robust to translation; extraction dispatches on `vr_data.scheme` (legacy absolute-coordinate QIM still supported).
- **blind_watermark — 4th raster scheme** (`algorithm/raster_blind_watermark.py`): blind DWT-DCT-SVD embed/extract with GeoTIFF CRS preservation; crop recovery via host-template realignment.
- **IW-DCT — 5th raster scheme** (`algorithm/raster_iw_dct.py`): invisible-watermark-style blind extraction — Haar-LL 4×4 block DCT, fixed lowest mid-frequency pair, cyclic repetition; **blind block-grid realignment for crop attacks** (structure-score-gated 64-phase search — no host template, no format change, existing stegos stay valid) and **EMBED_MARGIN experimentally calibrated to 40** (scan of {16, 20, 26, 32, 40} × {none, JPEG q50–q85, noise σ2–σ15, crop 0.8}: 40 passes the noise σ15 probe and JPEG q50 at BER 0 for ~0.9 dB PSNR cost vs 26; mean PSNR 35.70 → 34.11 dB across the ladder; no-attack roundtrip bit-exact at every margin; crop cell NC 0.990).
- Raster dispatch wired through embed/extract/decode endpoints and the frontend embed dialogs (single + batch) + lab scheme list; 1024-host crop-recovery + load-overhead tests.

### Backend — Robustness Lab Engine (`algorithm/robustness*.py`, `resource/robustness_resource.py`)

- **Matrices**: vector — legacy vs D-QIM under translation / scale / point-drop / noise / simplification attacks; raster — the five schemes under JPEG / scale / crop / rotate / noise (/ blur, optional) image attacks. Admin run/list/detail endpoints with a background worker; `kind` switch for vector or raster.
- **Multi-trial**: fixed-seed reproducible engines, 1–10 trials per cell, success-rate + NC-mean aggregation, zombie-run sweep.
- **Strength sweep (WAVES-style)**: 5-tier ladders per attack, `strength_index` in results, detection-rate curves and collapse points in the UI (1–5 trials).
- **Attack source transparency**: `GET /api/robustness/attacks/meta` returns the true attack implementation (`inspect.getsource`), read-only — every published number is grounded in executable source.
- Real-machine scripts (`tests/robustness_matrix_realrun.py`, `tests/robustness_trials_battle.py`) run read-only against real datasets.

### Backend — Batch Jobs, Analytics & Exports

- **Batch embedding jobs** (`resource/batch_embed_resource.py`): create/list/detail; ≤50 de-duplicated items per job; one active job at a time (409 carries the active job's uuid); real per-item progress with failure reasons; stale-job zombie sweep; reuses the single-embed dispatch.
- **Audit-log CSV export** (`GET /api/admin/logs/export`): streamed CSV (UTF-8 BOM, csv-module escaping, CRLF), newest ≤50,000 rows, truncation flagged by `X-Truncated` header + warning log.
- **Download statistics** (`GET /api/admin/download_stats` + `/export`): window constrained to {7, 14, 30, 90} days, daily trend, Top-10 users / datasets, week-over-week comparison; CSV export; admin dashboard block.
- **Quality data layer**: `watermark_verification` gains BER / SSIM / algorithm / linkage columns (+ indexes); `GET /api/watermark/verification_stats` with from/to window; DB-backed benchmark results exposed at `/api/benchmark/stats` (JSON moved out of `static/`).

### Backend — AI Endpoints & Runtime Hardening

- **Any OpenAI-compatible endpoint**: `AI_API_BASE` / `AI_MODEL` / `AI_API_KEY` (legacy `DEEPSEEK_API_KEY` honored as fallback); defaults unchanged (DeepSeek), local models (e.g. Ollama) work by pointing the base URL; config centralized in `utils/ai_config.py` — the AI assistant (chat/stream) and the upload auto-description both resolve through it.
- **Configurable timeout**: `AI_TIMEOUT` (float > 0, default 120s; empty/invalid/nan/inf/≤0 falls back) read per request — local-model cold starts (~40s) no longer time out; the upload auto-description timeout was unified onto the same `_get_ai_timeout()` (previously hardcoded 30s).
- **Runtime**: `eventlet` dropped entirely; production CMD is gunicorn `-w 1 --threads 8 -k gthread`; numpy-2-compatible dependency floors; `opencv-python` declared explicitly.

### Backend — Security Fixes

- **Hardcoded Tianditu key removed**: the two pages (data viewing, watermark generation) now read `VITE_TIANDITU_KEY` from env only and degrade gracefully (map/search disabled with a notice) when unset.
- **Compose secret hard-fail**: no built-in default credentials anymore — missing `MYSQL_ROOT_PASSWORD` / `POSTGRES_PASSWORD` / `SECRET_KEY` / `JWT_SECRET_KEY` / `GRAFANA_PASSWORD` fails fast with a pointer to `.env.example`.
- **Non-PII audit trail** on forensics verify/trace (see Leak Forensics).
- **Authorization hardening (O1)**: review/approval read endpoints gated by reviewer sub-role; role matrix pinned by tests (`tests/test_authz_review.py`).
- **Secret hygiene**: plaintext credential files dropped from HEAD; gitleaks secret-scanning workflow; key material ignored in `.gitignore`; stray gitlinks removed.

### Backend — E2E Verification Campaign (integration fixes)

- Vector watermark embed → extract recovers the QR again (true-floor grid anchor + canonical seed string for negative coordinates); compact QR rendered for the blind path; v1 QR text persisted at all four generation points.
- Raster: GeoTIFF embed records the real stego artifact; float rasters stretched so tiles no longer render all-black; tile GET path aligned with the nested layout written by the generator; preview returns 4xx for non-images and confines paths to app roots; multi-band DWT embed/extract agree; insufficient histogram capacity maps to a readable 400.
- Platform: SQLite-safe dashboard aggregation (`func.date()`); testing DB fully SQLite; dict JWT identities accepted under modern PyJWT; token-download and recall-deadline datetimes compared without tz mixing; readable 4xx for registration conflicts; SHP upload stores EPSG (varchar(100) overflow fixed); dangling FK targets resolved (`add_employee` 500); admin chat-role vocabulary unified; untampered QR signature verification fixed.
- Regression coverage added for BUG-1..5 and the float-tile render path.

---

### Frontend — Delivery, Forensics & Evidence UI

- Employee download switched to the personalized delivery token flow.
- **Forensics page** (admin): delivery ledger tab (four-dimension filters) + leak forensics tab (verify / trace with uploaded file or QR text); `src/api/forensics.js`; route + sidebar + zh/en strings; multipart FormData only when needed; extended request timeout for long forensics scans; stale results cleared on input change.
- **Evidence presentation**: `HashText` monospace hash component (copy + paired i18n); QR provenance card rework (conclusion card, sectioned fields, raw data with signature); forensics dialog redo (summary card, DFIR event-timeline cards, evidence/anchor block); traceability result panels as bordered cards.
- **Attestation Center** (存证中心) page for anchor batches.

### Frontend — Robustness Lab & Quality Dashboards

- **Robustness lab page**: attack-matrix result table + comparison verdict + run controls + history + NC comparison chart; v2 layout; trials selector / success-rate cells / per-trial tooltips; strength-sweep curve mode; raster toggle; **attack source drawer** (highlight.js python highlighting, line numbers, shareable `#L{n}` anchors); metric/attack glossary with a per-metric documentation drawer (definition / how to read / thresholds / sources); first-visit ElTour (non-blocking, in-viewport).
- **Watermark quality dashboard v2**: hero KPI band + analytics gallery on real stats endpoints, threshold-visualized metric explainer, evidence-chain health zone with recent deliveries, benchmark capability matrix + stego overview + D-QIM card; glossary + tour.
- QR/watermark previews: nearest-neighbor upscale (cap 16×) and teleported previews site-wide.

### Frontend — Design System, Themes & Shell

- **Site-wide dark theme**: navy palette, Element Plus dark css-vars brand-overridden, `html.dark` token section, header toggle (`useTheme`); admin + employee page sweeps (dashboards, watermarks, forensics, approvals, data management/upload, logs, system management, recall).
- **Dual-mode token architecture v2.1** (`72d7725`): L1 ramps + a single L2 semantic map driving both modes (Linear-style dark / Vercel-style light); chart ink fully tokenized (thin grid lines, threshold reference lines); typography discipline (weight compliance for YaHei, ≤3 weights); motion params + per-component reduced-motion (loop animations off, skeleton de-sampled); self-hosted Noto subset; shell/nav alignment; primary-button variant fix; remaining inline colors tokenized.
- Login/register brand redesign (dual-column / grouped form) + paper-plate traceability-seal brand QR; de-AI-purple navy recolor across auth / quality / globe.
- Admin dashboard **data-flow 3D globe** hero (three-globe) with real delivery arcs sourced from delivery statistics.

### Frontend — Data, Maps & Charts

- Data management pages + Leaflet maps; dashboard/chat overhaul; GeoServer integration (uploads publish layers and store WMS URLs).
- **On-demand raster tiles**: rio-tiler replaces pre-generation; signed short-lived tokens for browser tile access (F1) — the frontend fetches the token for map layers.
- **vue-echarts 7.0.3** migration: admin dashboard (5 charts), watermark quality dashboard (5), employee dashboard (3).

---

### Infrastructure & CI

- **Container runtime smoke in CI** (docker job): the backend image boots (app factory + route check) and serves `/api/health` via the gunicorn CMD; the frontend image's nginx config is validated — image builds alone don't pass anymore.
- **pytest promoted to a blocking gate**; failing-test tails mirrored into an issue comment for remote diagnostics; libzbar0 installed for pyzbar QR decode on Linux; eth-tester pre-release floor so the docker build resolves.
- Dependabot (grouped action bumps), CodeQL, gitleaks secret scan, Scorecard and AI-review workflows; ruff/pre-commit kept in lock-step (0.15.x); issue/PR templates + CodeRabbit config.
- Dead code: frontend `socket.js` and the unused `socket.io-client` dependency removed.

### Tests

- 29 new test files (25 `test_*.py` + 4 real-run/helper scripts): crypto/COSE, key registry, evidence chain, EVM anchor (eth-tester), delivery flow (incl. three-user E2E), forensics API (filters / zip defenses / no-PII audit), anchor center, delivery stats, download stats, batch embed jobs, D-QIM, raster blind / IW / robustness matrices, strength sweep, experiment trials, quality stats, benchmark DB, authz review, AI endpoint / timeout / upload config (hermetic stdlib mock servers), metadata integrity, raster tiles.

### Files Changed Summary

| Area | Files | Highlights |
|------|-------|-------------|
| `testrealend/` (backend) | 123 | delivery / crypto / evidence / forensics / lab / batch / quality + 29 new test files |
| `testrealfrontol/` (frontend) | 87 | delivery & forensics UI, robustness lab, quality dashboards, dark theme + tokens, tiles, ECharts |
| `contracts/` | 3 | `AnchorRegistry.sol`, deploy script, README |
| Root / CI / docker / docs | 49 | CI workflows, compose, Dockerfiles, README, `.env.example` |
| **Total** | **262** | **+40,859 / −5,996** |

### Verification

- **Backend:** full suite **583 passed / 0 failed** (file-based SQLite; hermetic — no external network in tests).
- **Lint/format:** `ruff check .` and `ruff format --check .` clean (171 files).
- **Commits:** 278 after v2.4.0 (through `d63e347`).

### Known Limitations (v3.0)

1. **EVM second anchor** — contract + provider + eth-tester coverage are in-tree, but there is no Sepolia deployment yet; unless configured, anchoring stays on OpenTimestamps (the EVM path reports `PENDING`).
2. **OpenTimestamps semantics** — it proves a commitment existed before a point in time; it is not a real-time notary.
3. **FID is an identifier, not a secret** — security comes from the signature and server-side binding; the current scheme does not claim anti-collusion resistance.
4. **Dark theme residuals** — a few legacy pages are still converging to the dark palette.
5. **Frontend E2E** — still manual; no Cypress/Playwright suite.

---

## [v2.3.1] — 2026-05-09 (Codebase Cleanup, Bug Fixes, Deprecation Fix & Directory Normalization)

### Summary
Dead code removal, missing dependency fix, algorithm bug fix, security hardening, 5 pre-existing frontend build-breaking bugs fixed, `datetime.utcnow()` deprecation migrated across 29 files, frontend directory names normalized (17 directories renamed from spaces to camelCase), `watermark_resource.py` split into 4 focused modules, SQLAlchemy 2.0 `Query.get()` migration across 11 files, missing `@admin_required` on dashboard endpoint fixed, root temp files cleaned up, 22 more unused imports removed, dead `NC.py` deleted, 8 dead frontend files removed, duplicate APIs consolidated, bare `except:` fixed, QR_SECRET_KEY security hardened.

**Files changed:** 70+ files, ~2700 lines removed

---

### Backend — Fixes

#### 1. Missing `geoalchemy2` Dependency (`requirements.txt`)
- `model/Shp_File.py` imports `geoalchemy2` but it was not in `requirements.txt`
- Added `geoalchemy2` to prevent ImportError on clean install

#### 2. Incomplete Model Bootstrap (`app.py`)
- `_bootstrap_runtime_schema()` only included 20 of 27 models — 7 tables would not auto-create on first deploy
- Added: `Permission`, `AdmAccountPermissions`, `EmbedFileRecord`, `ExtractHelper`, `SendFileRecord`
- Added graceful import for `ShpFile` and `MysqlShpFile` (require geoalchemy2/mysql-specific types)

#### 3. Algorithm Bug Fix (`algorithm/get_coor.py`)
- **Empty feature crash:** When all points in a feature were deleted, `get_coor_array()` would throw an unhandled error. Now safely skips empty arrays.
- **Multi-geometry detection:** The `isinstance(coor_nested[:, i][0][0], np.ndarray)` check failed for nested arrays, causing MultiPolygon/MultiLineString to be processed in the wrong branch. Rewritten to use `shp_type` for branching instead of runtime type guessing.
- **`__main__` block:** Replaced undefined `select_file()` / `gpd` with `argparse`-style CLI.

#### 4. Security — `allow_unsafe_werkzeug` (`app.py`)
- Was always `True` regardless of environment. Now only enabled when `DEBUG=True`.

#### 5. Hardcoded Credentials (`.env.example`, `add_user_script.py`)
- `.env.example` had `root:root` database passwords — replaced with placeholders
- `add_user_script.py` hardcoded `root:root` — now reads from `.env` via `dotenv`

---

### Backend — Dead Code Removal

| Deleted File | Reason |
|---|---|
| `common/constants.py` | `LOGIN_SECRET = "MY_KEY"` never imported anywhere |
| `common/api_tools.py` | Empty file (8 bytes, whitespace only) |
| `common/__init__.py` | Package had no remaining modules |
| `Adm_Info.py` (project root) | Duplicate of `model/Adm_Info.py`, leftover from early development |

#### Filename Typo Fix
- `server/appliaction_server.py` → `server/application_server.py`

---

### Frontend — Build-Breaking Bug Fixes (5 files)

These were pre-existing bugs where imported API functions were redeclared as local `const`, causing either build failures or infinite recursion at runtime.

| File | Conflict | Fix |
|---|---|---|
| `employee_profile.vue` | `changePassword` (import vs local) | Renamed local to `openChangePasswordDialog` |
| `not_approved.vue` | `batchReview` (import vs local) | Aliased import as `batchReviewApi` |
| `raster_watermark_embedding.vue` | `crmarkEmbed/Recover/Decode` (import vs local) | Aliased imports as `*Api` |
| `employee_chat.vue` | `searchUsers` (import vs local) | Aliased import as `searchUsersApi` |
| `AdminNotifications.vue` | `sendNotification` (import vs local) | Aliased import as `sendNotificationApi` |

#### Import Source Fix
- `watermark_embedding.vue`: `QuestionFilled` was imported from `element-plus` (not exported) — moved to `@element-plus/icons-vue`

---

### Frontend — Dead Code Removal

| Deleted File | Lines | Reason |
|---|---|---|
| `api/data_viewing_api.js` | 23 | Marked `@deprecated`, replaced by `api/data.js`, zero imports |
| `views/employee/Data Viewing/data_viewing.vue` | 1520 | Superseded by `data_viewing_new.vue` (used in router) |
| `views/employee/Data Viewing/data_viewing_style.css` | 771 | Companion CSS for dead view |
| `styles/design-tokens.css` | 56 | Overlapping CSS variables with `design-system.css`, zero unique variables used |
| `stores/admin/nav.js` | 0 | Empty placeholder |
| `stores/employee/nav.js` | 0 | Empty placeholder |
| `types/data.ts` | 0 | Empty placeholder (abandoned TS migration) |

#### Config Cleanup
- `vite.config.js`: Removed 40-line commented-out proxy block (referenced stale port 5001)
- `main.js`: Removed unused `design-tokens.css` import

---

### Backend — `datetime.utcnow()` Deprecation Fix (29 files)

#### What
Replaced all `datetime.utcnow()` calls with `datetime.now(timezone.utc)` for Python 3.12+ compatibility.

#### How
- Model defaults: `default=datetime.utcnow` → `default=lambda: datetime.now(timezone.utc)`
- Direct calls: `datetime.utcnow()` → `datetime.now(timezone.utc)`
- Added `timezone` to all `from datetime import datetime` statements
- Fixed duplicate import in `download_file_resource.py` (two `from datetime import` lines consolidated)

#### Files Changed
- 18 model files (all `default=` and `onupdate=` parameters)
- 9 resource files (direct calls in business logic)
- 1 utility file (`websocket.py` — timestamp generation)
- 1 server file (`raster_watermark_server.py`)

---

### Frontend — Directory Name Normalization (17 directories)

#### What
Renamed all view directories containing spaces to camelCase for toolchain compatibility and consistency.

#### Before → After

| Before | After |
|---|---|
| `admin/Adm Dashboard` | `admin/AdmDashboard` |
| `admin/Approve Application` | `admin/ApproveApplication` |
| `admin/Employee management` | `admin/EmployeeManagement` |
| `admin/Log Management` | `admin/LogManagement` |
| `admin/System Management` | `admin/SystemManagement` |
| `admin/Watermark Embedding` | `admin/WatermarkEmbedding` |
| `admin/Watermark Extraction` | `admin/WatermarkExtraction` |
| `admin/Watermark Generation` | Deleted (empty directory) |
| `employee/Data Application` | `employee/DataApplication` |
| `employee/Data Download` | `employee/DataDownload` |
| `employee/Data Viewing` | `employee/DataViewing` |
| `employee/Employee About` | `employee/EmployeeAbout` |
| `employee/Employee Dashboard` | `employee/EmployeeDashboard` |
| `employee/Employee Help` | `employee/EmployeeHelp` |
| `employee/Employee Profile` | `employee/EmployeeProfile` |
| `employee/My Notifications` | `employee/MyNotifications` |
| `employee/Operation History` | `employee/OperationHistory` |

- Updated all 22 import paths in `router/index.js`

---

### Backend — watermark_resource.py Split (1234 → 4 files)

#### What
Monolithic `watermark_resource.py` (1234 lines, 13 classes) split into focused modules.

| New File | Classes | Lines |
|---|---|---|
| `watermark_utils.py` | Shared utilities (QR_SECRET_KEY, safe_extract_zip, build_qr_text, etc.) | ~100 |
| `watermark_generate_resource.py` | Adm1GetGenerateWatermarkApplications, GenerateWatermarkResource | ~110 |
| `watermark_embed_resource.py` | Adm2GetEmbeddingWatermarkApplications, EmbeddingWatermarkResource | ~178 |
| `watermark_extract_resource.py` | VectorExtractResource | ~209 |
| `watermark_upload_resource.py` | Upload, Records, Preview, Batch classes | ~606 |

- Updated `app.py` imports to reference new modules
- Deleted old `watermark_resource.py`

---

### Backend — SQLAlchemy 2.0 Deprecation Fix (11 files)

#### What
Replaced all `Model.query.get(id)` calls with `db.session.get(Model, id)` for SQLAlchemy 2.0 compatibility.

- 46 occurrences across 11 resource files
- Eliminates `LegacyAPIWarning` in test output

---

### Backend — Missing `@admin_required` on AdminDashboard

#### What
`AdminDashboardResource` was missing the `@admin_required` decorator — employees could access admin dashboard data.

- Added `@admin_required` decorator between `@jwt_required()` and `@relaxed_limit`

---

### Backend — Unused Import Cleanup (88 imports removed, 29 Python files)

#### What
Automated scan and removal of 88 unused Python imports across 29 backend files.

#### Side Effect Fix
The cleanup script broke 7 files by removing import lines but leaving references intact. All 7 manually fixed:
- `algorithm/extract.py` — restored trailing comma in import
- `algorithm/to_geodataframe.py` — restored `from shapely.geometry import (...)`
- `resource/download_file_resource.py` — restored `from utils.user_limiter import normal_limit, relaxed_limit`
- `utils/metrics.py` — restored `from prometheus_client import (...)`
- `tests/conftest.py` — restored `from model import (...)`
- `resource/watermark_generate_resource.py` — rewrote header with correct imports
- `resource/watermark_embed_resource.py` — rewrote header with correct imports

#### Additional Fixes (post-cleanup)
- `resource/watermark_extract_resource.py` — rewrote broken header, fixed `safe_extract_zip` / `decode_qr_from_image` / `parse_qr_text` function calls (were underscore-prefixed)
- `resource/watermark_upload_resource.py` — rewrote broken header, fixed `build_qr_text` / `get_qr_version` function calls
- `resource/watermark_generate_resource.py` — fixed `build_qr_text` / `get_qr_version` function calls
- `resource/watermark_extract_resource.py` — `datetime.now()` → `datetime.now(timezone.utc)`

---

### Backend — Dead Server File Removal (7 files)

| Deleted File | Reason |
|---|---|
| `server/adm_server.py` | Zero imports, superseded by `app.py` factory |
| `server/application_server.py` | Zero imports |
| `server/emp_server.py` | Zero imports |
| `server/nav_server.py` | Zero imports |
| `server/raster_data_server.py` | Zero imports |
| `server/raster_watermark_server.py` | Zero imports |
| `server/shp_data_server.py` | Zero imports |

---

### Backend — Second-Pass Cleanup (22 unused imports, dead code, security)

#### Unused Imports Removed (22 instances, 8 files)
| File | Removed |
|---|---|
| `resource/watermark_embed_resource.py` | `datetime`, `timezone`, `build_qr_text`, `get_qr_version`, `decode_reversible`, `extract_dwt`, `recover_dwt`, `extract_histogram`, `recover_histogram`, `compute_nc`, `compute_ssim_simple`, `compute_ber`, `record_watermark` |
| `resource/admin_application_resource.py` | `timedelta` |
| `resource/adm_resource.py` | `get_jwt_identity` |
| `resource/watermark_extract_resource.py` | `Shp` |
| `resource/watermark_upload_resource.py` | `normal_limit` |
| `algorithm/extract.py` | `NC` (from `algorithm.NC`) |
| `algorithm/raster_reversible_watermark.py` | `is_geotiff` |
| `tests/test_robustness.py` | `ImageFilter` |

#### Dead Code Deleted
| File | Reason |
|---|---|
| `algorithm/NC.py` | Duplicate of `quality_metrics.py`, zero runtime callers |
| `src/views/admin/EChartBar/echarts.vue` | Not in router, zero imports |
| `src/views/admin/EmployeeManagement/account_list.vue` | Not in router, zero imports |
| `src/views/admin/EmployeeManagement/account_add.vue` | Not in router, zero imports |
| `src/components/DataCard.vue` | Zero imports |
| `src/components/DataView.vue` | Zero imports |
| `src/components/common/LoadingSkeleton.vue` | Zero imports |
| `src/components/common/EmptyState.vue` | Zero imports |
| `src/api/NaviApi.js` | Zero imports |

#### Security Fixes
- `resource/application_resource.py:560` — Bare `except:` → `except Exception:` (was catching `KeyboardInterrupt`, `SystemExit`)
- `resource/wmark_utils.py` — `QR_SECRET_KEY` fallback now only uses dev key when `FLASK_DEBUG=1`; logs `ERROR` in production instead of silently using insecure key

#### Frontend Cleanup
- `src/api/watermark.js` — Removed duplicate `getShpApplications` / `getRasterApplications` (already defined in `admin.js`)
- `src/views/admin/AdmDashboard/adm_dashboard.vue` — Removed unused `onUnmounted` import

---

### Misc Cleanup
- Added `QR_SECRET_KEY` placeholder to `.env.example`
- Deleted root-level temp files: `temp_qrcode.png`, `filelist.txt` (both in `.gitignore`)

---

### Verification
- **Backend:** `create_app()` succeeds, 106 routes registered, zero import errors
- **Tests:** 126 passed, 1 failed (pre-existing numpy 2.0 compat), 2 skipped
- **Frontend:** `vite build` succeeds (36 modules, 62s)

---

## [v2.3.0] — 2026-05-09 (Security Hardening, Multi-Algorithm Watermark & Monitoring)

### Summary
Fixed critical security vulnerabilities (user impersonation, missing role enforcement), added admin sub-role differentiation (admin1/admin2/admin3), implemented 3 raster watermark algorithms (LSB, DWT, Histogram Shifting) with GeoTIFF CRS preservation, added application withdrawal lifecycle, centralized the frontend API service layer, upgraded chat to Socket.IO, and added Grafana alerting + Loki log aggregation.

**Total changes:** 40+ files modified/added

---

### Backend — Security Fixes

#### 1. Admin Sub-role Enforcement (`utils/required.py`, resource files)
- **What:** `admin_role_required(*roles)` decorator enforces specific admin sub-roles (admin1/admin2/admin3)
- **Applied to:**
  - `Adm1PassResource` / `Adm1FailResource` → `@admin_role_required('admin1')`
  - `Adm2PassResource` / `Adm2FailResource` → `@admin_role_required('admin2')`
  - `Adm3AdditionalReviewResource` → `@admin_role_required('admin3')`
- **Helper:** `is_admin_role(role)` replaces all hardcoded `== 'admin'` / `!= 'admin'` checks across 6 resource files
- **Files changed:** `application_resource.py`, `admin_application_resource.py`, `dashboard_resource.py`, `collaboration_resource.py`, `recall_resource.py`

#### 2. User Impersonation Fix (`resource/application_resource.py`, `download_file_resource.py`)
- **What:** `user_name` and `user_number` now derived from `get_jwt_identity()` instead of request body
- **Endpoints fixed:** `SubmitApplicationResource`, `get_applications`, `get_approved_applications`, `RecordDownloadResource`

#### 3. Input Validation
- Registration: password complexity (8+ chars, letters + digits)
- Profile update: email format validation
- Password change: old password verification required
- Chat messages: 2000-character limit

---

### Backend — New Features

#### 4. Application Withdrawal (`resource/application_resource.py`)
- **Endpoint:** `PUT /api/applications/<id>/withdraw`
- **Rules:** Only own applications, only before adm1 review starts
- **Side effects:** Audit log entry + dashboard cache invalidation
- **Registered in:** `app.py`

#### 5. Multi-Algorithm Raster Watermark (`algorithm/`, `resource/watermark_resource.py`, `resource/raster_resource.py`)
- **LSB** (`raster_reversible_watermark.py`) — Least Significant Bit embedding
- **DWT** (`raster_dwt_watermark.py`) — Discrete Wavelet Transform embedding
- **Histogram Shifting** (`raster_histogram_watermark.py`) — Histogram-based reversible watermarking
- **GeoTIFF preservation** (`raster_geotiff_utils.py`) — CRS and affine transform preserved through embed/extract
- **Dispatch:** Both `watermark_resource.py` and `raster_resource.py` route by `algorithm` parameter

#### 6. Algorithm Quality Metrics (`algorithm/quality_metrics.py`)
- PSNR, SSIM, NC (Normalized Correlation) computation for watermark quality assessment

---

### Backend — Test Suite Expansion

#### 7. Robustness Tests (`tests/test_robustness.py`) — 6 new tests
| Test | Description |
|------|-------------|
| `test_lsb_baseline_roundtrip` | Embed → extract → NC ≥ 0.99 |
| `test_jpeg_compression_robustness` | NC after JPEG quality 50 |
| `test_gaussian_noise_robustness` | NC after σ=10 noise |
| `test_crop_robustness` | NC after 10% crop |
| `test_watermark_recovery` | Recover original from watermarked |
| `test_vector_roundtrip` | Full vector embed → extract pipeline |

#### 8. Admin Workflow Tests Updated (`tests/test_approval_workflow.py`, `tests/test_integration.py`)
- Admin2 tests use dedicated `adm2_headers` fixture (role='admin2')
- `conftest.py` seeds admin1 (role='admin1') + admin2 (role='admin2')

**Test count:** 140 tests (up from 115), 138 passed, 2 skipped

---

### Backend — Monitoring & Logging

#### 9. Grafana Alerting Rules (`grafana/provisioning/alerting/alerts.yml`)
- Error rate > 5% for 5min → alert
- p95 latency > 2s for 5min → alert
- Database connection failure → immediate alert
- Cache hit rate < 50% → alert

#### 10. Loki Log Aggregation
- **Loki config:** `loki-config.yml` — local filesystem storage
- **Promtail config:** `promtail-config.yml` — scrapes `testrealend/logs/`
- **Grafana dashboard:** `grafana/provisioning/dashboards/json/logs.json` — log volume + error panels
- **Docker Compose:** Added `loki` and `promtail` services (total: 9 services)
- **Datasource:** `grafana/provisioning/datasources/datasource.yml` — added Loki

---

### Frontend — Architecture

#### 11. Centralized API Service Layer (`src/api/`)
| Module | File | Endpoints |
|--------|------|-----------|
| Auth | `auth.js` | login, register, refresh, logout |
| Admin | `admin.js` | dashboard, employees, approval, batch review, logs |
| Employee | `employee.js` | applications, profile, notifications, downloads |
| Watermark | `watermark.js` | generate, embed, extract |
| Chat | `chat.js` | conversations, messages, search, friend requests |
| Recall | `recall.js` | list, create, vote, detail |
| Upload | `upload.js` | SHP upload, raster upload |
| Data | `data.js` | vector data, raster data, tiles |
| Data Viewing | `data_viewing_api.js` | viewing, search |
| Navigation | `NaviApi.js` | nav tree |

- All 49 Vue components migrated from inline `axios` calls to centralized API modules

#### 12. Socket.IO Real-time Chat (`src/utils/socket.js`)
- **What:** Event-driven messaging replaces 30-second polling
- **Fallback:** Automatic HTTP polling when WebSocket unavailable
- **Events:** `new_message`, `typing`, `mark_read`, `friend_request`
- **Files changed:** `employee_chat.vue`, `AdminChat.vue`

#### 13. LogViewer Filter Fix (`views/admin/Log Management/LogViewer.vue`)
- Filter values changed from UI labels (用户登录) to backend action types (登录, 申请提交, 一审通过, etc.)

#### 14. Application Withdrawal UI (`views/employee/Data Application/data_application.vue`)
- "撤回" button with confirmation dialog for pending applications
- "已撤回" badge for recalled applications

---

### Files Changed Summary

| Category | Files | Description |
|----------|-------|-------------|
| Security fixes | 8 | required.py, application_resource.py, admin_application_resource.py, dashboard_resource.py, collaboration_resource.py, recall_resource.py, download_file_resource.py, common_resource.py |
| New algorithms | 4 | raster_dwt_watermark.py, raster_histogram_watermark.py, raster_geotiff_utils.py, quality_metrics.py |
| New tests | 1 | test_robustness.py (6 tests) |
| Modified tests | 3 | conftest.py, test_approval_workflow.py, test_integration.py |
| New Grafana/Loki | 4 | alerts.yml, loki-config.yml, promtail-config.yml, logs.json |
| New frontend utils | 1 | socket.js |
| New API modules | 6 | auth.js, recall.js, upload.js, data.js, watermark.js, chat.js |
| Modified frontend | 15+ | Vue components migrated to API modules |
| Modified infra | 2 | docker-compose.yml, datasource.yml |
| Documentation | 2 | README.md, CHANGELOG.md |

---

### Architecture Upgrade (Deep Audit Fixes)

#### 15. Frontend Admin Sub-role Bug Fix (`login.vue`, `router/index.js`)
- **Problem:** `login.vue` did not pass `admin_sub_role` to `setUserInfo()`, causing all admins to default to `adm1` on page refresh. Router guard used exact match `=== 'admin'` but backend returns `'admin1'`/`'admin2'`/`'admin3'`.
- **Fix:** `login.vue` now passes `admin_sub_role` from login response. Router guard normalizes role with `startsWith('admin')` check.

#### 16. QR_SECRET_KEY Crash Guard (`resource/watermark_resource.py`)
- **Problem:** If `QR_SECRET_KEY` env var is unset, `None.encode()` would crash watermark generation at runtime.
- **Fix:** Added dev-only fallback key with warning. Watermark generation no longer crashes; extraction already handled this gracefully.

#### 17. Per-user Rate Limiting Activated (`utils/user_limiter.py` → resource files)
- **Problem:** `strict_limit`/`normal_limit`/`relaxed_limit` decorators were defined but never applied to any endpoint.
- **Fix:** Applied to key endpoints:
  - `SubmitApplicationResource.post` — already had `@limiter.limit`
  - `WithdrawApplicationResource.put` — `@normal_limit`
  - `GetApplicationsResource.get` — `@relaxed_limit`
  - `Adm1PassResource.post` / `Adm2PassResource.post` — `@normal_limit`
  - `BatchReviewResource.post` — `@normal_limit`
  - `VectorExtractResource.post` — `@normal_limit`
  - `AdminDashboardResource.get` — `@relaxed_limit`

#### 18. Destructive `is_multiple.py` Fixed (`algorithm/is_multiple.py`)
- **Problem:** `is_multiple()` overwrote original shapefiles in place, permanently destroying all but the first sub-geometry of MultiPolygon/MultiLineString features.
- **Fix:** Now saves to `{filename}_single.shp` by default. Original file is never overwritten. Accepts optional `output_path` parameter. Returns output path for chaining.

#### 19. Algorithm Code Cleanup (`algorithm/embed.py`, `algorithm/is_multiple.py`)
- Removed 6 commented-out `print()` debug statements from `embed.py`
- Replaced hardcoded `E:\矢量数据\...` path in `embed.py` `__main__` with argparse CLI
- Replaced hardcoded `D:\Desktop\Projects\yingbianma` path in `is_multiple.py` `__main__` with env var

#### 20. Dev Key Warning (`config.py`)
- **Problem:** `DevelopmentConfig` silently used insecure default keys with no warning.
- **Fix:** Added logging warning when dev keys are detected in development mode.

---

### Known Limitations (v2.3)
1. **DWT/Histogram algorithms** — Only LSB has end-to-end integration tests; DWT and Histogram are tested via unit tests only
2. **`datetime.utcnow()`** — Used in several places; should migrate to `datetime.now(datetime.UTC)` for Python 3.12+
3. **Frontend E2E tests** — No Cypress/Playwright tests yet; all frontend testing is manual

---

## [v2.2.0] — 2026-05-07 (Full i18n Translation & UI Polish)

### Summary
Translated all 49 Vue view templates (~1595 Chinese strings) to vue-i18n, completing full internationalization coverage. Both `zh-CN.js` and `en-US.js` now contain 1200+ translation keys covering every user-facing string in the application.

**Files changed:** 49 Vue views, 2 locale files
**Total i18n keys:** 1200+ per locale (up from ~400 in v2.1)

---

### Frontend — Complete i18n Translation

#### New i18n Sections (30+ new modules)

| Module | Key Prefix | Views Covered |
|--------|-----------|---------------|
| Admin Dashboard | `adminDashboard` | adm_dashboard.vue |
| Employee Management | `employeeMgmt` | information_list, information_add, EditEmployee, account_list, account_add |
| Approval Workflow | `approval` | not_approved, approved, DualChannelApproval |
| Recall Proposals | `recall` | RecallProposalList.vue (expanded from 11 to 40+ keys) |
| Admin Application | `adminApp` | VotingPage.vue |
| Employee Dashboard | `empDashboard` | employee_dashboard.vue |
| Employee Profile | `empProfile` | employee_profile.vue |
| Employee Chat | `empChat` | employee_chat.vue |
| Employee Notifications | `empNotify` | my_notifications.vue |
| Employee History | `empHistory` | my_operation_history.vue |
| Employee About | `empAbout` | employee_about.vue |
| Employee Help | `empHelp` | employee_help.vue |
| Employee Admin App | `empAdminApp` | ApplicationForm.vue |
| Employee Data View | `empDataView` | data_viewing.vue |
| Employee Data Application | `empDataApp` | data_application.vue |
| Employee Data Download | `empDataDownload` | data_download.vue |
| Admin Chat | `adminChat` | AdminChat.vue |
| Admin Guide | `adminGuide` | AdminGuide.vue |
| Admin Notifications | `adminNotify` | AdminNotifications.vue |
| Admin Announcements | `adminAnnounce` | SystemAnnouncement.vue |
| Admin Log Viewer | `adminLogViewer` | LogViewer.vue |
| Admin Data Upload | `adminDataUpload` | DataUpload.vue |
| Watermark Generation | `wmGen` | watermark_generation.vue |
| Watermark Embedding | `wmEmbed` | watermark_embedding.vue |
| Watermark Extraction | `wmExtract` | watermark_extraction.vue |
| Raster Watermark Gen | `rasterWmGen` | raster_watermark_generation.vue |
| Raster Watermark Embed | `rasterWmEmbed` | raster_watermark_embedding.vue |
| Raster Watermark Extract | `rasterWmExtract` | raster_watermark_extraction.vue |
| Account Add | `accountAdd` | account_add.vue |
| ECharts Labels | `echarts` | echarts.vue |
| Employee Data View (New) | `empDataViewNew` | data_viewing_new.vue |

#### Shared Components Translated
- **HomeSide.vue (Admin)** — All 22 sidebar menu items use `$t('sidebar.admin.*')`
- **HomeSide.vue (Employee)** — All 8 sidebar menu items use `$t('sidebar.employee.*')`
- **HomeHeader.vue (Admin)** — System title, nav items, user dropdown use `$t('header.*')`
- **HomeHeader.vue (Employee)** — System title, nav menu, avatar messages use `$t('header.*')`
- **NotificationCenter.vue** — Panel title, tabs, empty states, time formatting use `$t('notification.*')`
- **EmptyState.vue** — Default title/description use `$t('common.noData')` / `$t('common.noDataDesc')`

#### Translation Approach
- **Template:** `$t('module.key')` for labels, placeholders, titles
- **Script:** `const { t } = useI18n(); t('module.key')` for ElMessage, validation rules
- **Validation rules:** Arrow functions for reactive messages: `message: () => t('key')`
- **Parameterized translations:** `t('key', { param: value })` for dynamic content

---

### Frontend — UI Improvements
- Consistent styling across all admin and employee views
- Clean card-based layouts with proper shadows and border radius
- Responsive table designs with proper column widths
- Improved dialog layouts with better spacing

---

### Files Changed Summary

| Category | Files | Description |
|----------|-------|-------------|
| Modified frontend views | 49 | All Vue views translated to i18n |
| Modified locale files | 2 | zh-CN.js (~1400 lines), en-US.js (~1400 lines) |
| Documentation | 1 | CHANGELOG.md |

---

## [v2.1.0] — 2026-05-07 (Security & Monitoring Upgrade)

### Summary
Hardened WebSocket authentication, upgraded rate limiter to Redis-backed sliding window, added Grafana dashboard provisioning, and translated core Vue views to i18n.

---

### Backend — Security Hardening

#### 1. WebSocket JWT Authentication (`utils/websocket.py`)
- **What:** Clients must authenticate after connecting by emitting `'authenticate'` event with JWT token
- **Verification:** `_verify_jwt_token(token, app)` uses `flask_jwt_extended.decode_token()`
- **Auto-join rooms:** On success, joins `user_{number}` room + `admins` room (if admin role)
- **Session tracking:** `authenticated_users` dict maps sid → identity; cleaned up on disconnect
- **All room operations** (join/leave/send) require prior authentication

#### 2. Redis-Backed Rate Limiting (`utils/user_limiter.py`)
- **What:** Per-user sliding window rate limiting using Redis sorted sets (ZREMRANGEBYSCORE, ZCARD, ZADD)
- **Fallback:** In-memory sliding window when Redis unavailable
- **Pre-configured limiters:**
  - `strict_limit` — 10 req/min (login, registration)
  - `normal_limit` — 60 req/min (standard endpoints)
  - `relaxed_limit` — 200 req/min (data viewing, dashboard)
- **Key improvement over v2.0:** Rate limit state survives server restarts and is shared across instances

---

### Backend — Monitoring

#### 3. Grafana Dashboard Provisioning (`grafana/`)
- **Datasource:** `grafana/provisioning/datasources/datasource.yml` — Prometheus at `http://prometheus:9090`
- **Dashboard provider:** `grafana/provisioning/dashboards/dashboards.yml` — auto-loads JSON dashboards
- **Dashboard:** `grafana/provisioning/dashboards/json/geodata-overview.json` with 11 panels:
  - Request Rate (req/s) — timeseries
  - Response Latency p50/p95/p99 — timeseries
  - In-Progress Requests — gauge
  - Error Rate (5xx) — stat
  - Applications Submitted — stat
  - Downloads — stat
  - Approvals vs Rejections — pie chart
  - Watermarks Generated — bar gauge
  - Cache Hit Rate — gauge
  - Request Status Distribution — pie chart
  - Database Errors — stat
- **Auto-refresh:** 30s, default time range: last 1 hour

---

### Frontend — i18n Expansion

#### 4. Core View Translations
- **`login.vue`** — All 20+ Chinese strings replaced with `$t('login.*')` calls (title, features, form labels, placeholders, validation messages, error messages)
- **`register.vue`** — All 25+ Chinese strings replaced with `$t('register.*')` calls (form labels, placeholders, validation, avatar upload messages, feature descriptions)
- **`first_home.vue`** — All 10+ Chinese strings replaced with `$t('firstHome.*')` calls (title, subtitle, buttons, feature cards, copyright)
- **New i18n keys:** ~60 keys added to both `zh-CN.js` and `en-US.js` across 3 new modules: `login`, `register`, `firstHome`

---

### Infrastructure

#### Docker Compose (7 services)
- **Added:** `grafana` service (Grafana latest, port 3000)
  - Auto-provisions Prometheus datasource and dashboards
  - Default home dashboard set to `geodata-overview.json`
  - Mounts `grafana/provisioning/` for datasource and dashboard configs
  - Depends on `prometheus` service
  - Credentials configurable via `GRAFANA_USER` / `GRAFANA_PASSWORD` env vars (default: admin/geodata_grafana)
- **Added:** `grafana_data` volume for persistent Grafana state

---

### Files Changed Summary

| Category | Files | Description |
|----------|-------|-------------|
| Modified backend | 2 | websocket.py (JWT auth), user_limiter.py (Redis sorted sets) |
| New Grafana config | 3 | datasource.yml, dashboards.yml, geodata-overview.json |
| Modified frontend | 5 | login.vue, register.vue, first_home.vue, zh-CN.js, en-US.js |
| Modified infra | 1 | docker-compose.yml (added grafana service + volume) |
| Documentation | 1 | CHANGELOG.md |

---

## [v2.0.0] — 2026-05-07 (Enterprise Upgrade)

### Summary
Transformed from a student-level project into a production-grade, resume-worthy enterprise platform. Added 6 major infrastructure systems, comprehensive test suite, and full internationalization.

**Commits:** `ea193ad` → `814f568` → `eac4d2f` → `5ca43a9` → `3c9df46`
**Total changes:** 47+ files, 3500+ lines added

---

### Backend — New Systems

#### 1. Redis Caching Layer (`utils/cache.py`)
- **What:** Hot query caching with Redis, graceful fallback when Redis unavailable
- **Where used:** `AdminDashboardResource` (120s TTL), extensible via `@cached` decorator
- **Cache invalidation:** `invalidate_prefix('dashboard')` called on application submit/approve/reject
- **Config:** `REDIS_URL` env var (default: `redis://localhost:6379/0`)
- **Key functions:** `init_cache(app)`, `cached(timeout, key_prefix)`, `invalidate_prefix(prefix)`

#### 2. WebSocket Real-time Notifications (`utils/websocket.py`)
- **What:** Flask-SocketIO for real-time push notifications
- **Events emitted:**
  - `notify_new_application()` → admins get notified on new application submission
  - `notify_application_update()` → applicant notified on approval/rejection (adm1 + adm2)
  - `notify_recall_update()` → admins notified on recall proposal changes
- **Rooms:** `user_{number}` for per-user, `admins` for broadcast
- **Config:** Uses `eventlet` async mode, works with Gunicorn

#### 3. Prometheus Metrics (`utils/metrics.py`)
- **What:** Request/business metrics exposed at `/metrics` endpoint
- **Metrics collected:**
  - `flask_request_total` — counter by method/endpoint/status
  - `flask_request_duration_seconds` — histogram with configurable buckets
  - `flask_requests_in_progress` — gauge of active requests
  - `geodata_applications_total` — counter by data_type
  - `geodata_approvals_total` — counter by result (approved/rejected) and level (adm1/adm2)
  - `geodata_downloads_total` — download counter
  - `geodata_watermarks_generated_total` — watermark counter by data_type
  - `geodata_cache_hits_total` — cache hit/miss counter
  - `geodata_db_errors_total` — database error counter
- **Instrumented endpoints:** `application_resource.py`, `download_file_resource.py`, `watermark_resource.py`
- **Compatibility:** Gracefully disabled on Windows Python 3.12 (AttributeError in prometheus_client)

#### 4. Per-User Rate Limiting (`utils/user_limiter.py`)
- **What:** JWT-identity-based rate limiting (not just IP)
- **Pre-configured limiters:**
  - `strict_limit` — 10 req/min (login, registration)
  - `normal_limit` — 60 req/min (standard endpoints)
  - `relaxed_limit` — 200 req/min (data viewing, dashboard)
- **Auto-cleanup:** Stale keys cleaned every 1000 requests
- **Response:** 429 with `retry_after` field

#### 5. Health Check Enhancement (`resource/health_resource.py`)
- **Added:** Redis connectivity check (`cache: connected/unavailable`)
- **Added:** Metrics status field
- **Fixed:** Uses `db.session.get_bind(bind_key='mysql_db')` instead of default engine (兼容 SQLALCHEMY_BINDS)

---

### Backend — Test Suite

#### Test Infrastructure
- **Framework:** pytest with fixtures in `conftest.py`
- **Fixtures:** `app`, `client`, `db`, `auth_headers`, `employee_headers`
- **Test data seeding:** Auto-creates admin (admin1/admin123) and employee (employee1/emp123) accounts
- **Config:** `pyproject.toml` with coverage settings (source: resource, model, utils)

#### Test Files (16 new files, 115 tests)
| File | Tests | Coverage |
|------|-------|----------|
| `test_health.py` | 5 | Health endpoint, status fields, cache field |
| `test_auth.py` | 7 | Login (missing fields, wrong creds, empty password), register, token refresh |
| `test_application.py` | 4 | Submit (auth required, missing fields), approval (auth required, nonexistent) |
| `test_approval_workflow.py` | 10 | Full workflow: adm1 pending/list, adm2 list, pass/fail nonexistent, batch review, all apps |
| `test_dashboard.py` | 5 | Admin dashboard (auth, role, success), employee dashboard (auth, success) |
| `test_watermark.py` | 7 | Generate (auth, missing app), embed (auth, list), extract (auth, missing fields) |
| `test_download.py` | 5 | Auth required, token invalid, record download |
| `test_recall.py` | 7 | List, create, vote, detail (all auth required), nonexistent |
| `test_announcement.py` | 4 | Get, create, update (auth required) |
| `test_profile.py` | 6 | Get/update profile, change password, photo (auth required) |
| `test_collaboration.py` | 10 | Notifications, my logs, chat (conversations, messages, send, search, friend requests) |
| `test_logs.py` | 5 | Auth required, admin role, pagination, filters |
| `test_nav.py` | 6 | Admin/employee nav tree and list (auth required) |
| `test_employee_mgmt.py` | 9 | List, add, create account, details, update, delete (auth required), nonexistent |
| `test_data_viewing.py` | 4 | Vector/raster viewing, SHP list, map search |
| `test_raster.py` | 7 | Preview, generate, CRMark embed/recover/decode, embed dispatch (auth required) |
| `test_upload.py` | 4 | SHP/raster upload (auth required, no file) |
| `test_admin_application.py` | 7 | Eligibility, submit, list, my, detail, vote (auth required) |
| `test_metrics.py` | 3 | Metrics endpoint, request counter, graceful degradation |

---

### Frontend — Internationalization (i18n)

#### i18n Infrastructure
- **Library:** `vue-i18n` v9 with Composition API (`legacy: false`)
- **Locale files:**
  - `src/locales/zh-CN.js` — Chinese (400+ translation keys)
  - `src/locales/en-US.js` — English (400+ translation keys)
  - `src/locales/index.js` — i18n configuration with localStorage persistence
- **Modules translated:** common, auth, nav, dashboard, application, watermark, employee, announcement, recall, chat, notification, profile, log, guide, upload, download, about, time

#### Language Switcher
- **Component:** `src/components/common/LanguageSwitcher.vue`
- **Location:** Added to both admin and employee header components
- **Behavior:** Dropdown with 中文/English, persists to localStorage, reloads to apply Element Plus locale

#### Files Updated for i18n
- `src/main.js` — Dynamic Element Plus locale (zhCn/enUs) based on stored preference
- `src/router/index.js` — 4 error messages use `t()` instead of hardcoded Chinese
- `src/utils/Axios.js` — 7 error messages use `t()`
- `src/utils/Time.js` — Time labels (days, hours, minutes, seconds, expired) use `t()`

---

### Infrastructure

#### Docker Compose (6 services)
- **Added:** `redis` (Redis 7 Alpine, appendonly, 256MB maxmemory, LRU eviction)
- **Added:** `prometheus` (Prometheus latest, scraping backend:5003/metrics)
- **Updated:** `backend` now depends on Redis, uses `REDIS_URL` env var
- **New file:** `prometheus.yml` — Prometheus scrape configuration

#### Backend Dockerfile
- **Changed:** CMD uses `eventlet` worker for Socket.IO support
- **Changed:** Health check URL updated to `/api/health`

#### CI/CD Pipeline (`.github/workflows/ci.yml`)
- **Added:** pytest step in backend job
- **Added:** `pytest-cov` to test dependencies

#### Dependencies Added
**Backend (`requirements.txt`):**
- `flask-socketio` — WebSocket support
- `eventlet` — Async worker for Socket.IO
- `redis` — Redis client
- `prometheus_client` — Metrics collection
- `pytest` — Test framework
- `pytest-cov` — Coverage reporting

**Frontend (`package.json`):**
- `vue-i18n` — Internationalization

---

### Config Changes

#### `config.py`
- **Added:** `REDIS_URL` setting (env: `REDIS_URL`, default: `redis://localhost:6379/0`)
- **Added:** `CACHE_DEFAULT_TIMEOUT` (env: `CACHE_DEFAULT_TIMEOUT`, default: 300s)
- **Added:** `CACHE_DASHBOARD_TIMEOUT` (env: `CACHE_DASHBOARD_TIMEOUT`, default: 120s)
- **Added:** `TestingConfig` class for test environment

#### `pyproject.toml`
- **Added:** `[tool.coverage.run]` — source paths, omit patterns
- **Added:** `[tool.coverage.report]` — show_missing, fail_under=50
- **Added:** `addopts = "-v --tb=short"` to pytest config

---

### Files Changed Summary

| Category | Files | Description |
|----------|-------|-------------|
| New backend utils | 4 | cache.py, metrics.py, websocket.py, user_limiter.py |
| New test files | 16 | test_*.py covering all API domains |
| New frontend files | 4 | LanguageSwitcher.vue, zh-CN.js, en-US.js, locales/index.js |
| Modified backend | 8 | app.py, config.py, extension.py, requirements.txt, health_resource.py, application_resource.py, dashboard_resource.py, download_file_resource.py, watermark_resource.py |
| Modified frontend | 6 | main.js, router/index.js, Axios.js, Time.js, HomeHeader.vue (x2), package.json |
| Modified infra | 4 | docker-compose.yml, prometheus.yml, ci.yml, Dockerfile |
| Documentation | 2 | README.md, CHANGELOG.md |

---

### Known Limitations
1. **Redis optional:** System works without Redis (cache disabled), but production should have Redis
2. **Prometheus on Windows:** `prometheus_client` fails on Windows Python 3.12 (`resource.getpagesize` missing) — metrics gracefully disabled
3. **WebSocket async mode:** Uses `eventlet` for production; `threading` mode for development
4. **Test DB:** Tests use SQLite (not MySQL/PostgreSQL), so spatial queries and UUID columns are skipped
5. **i18n coverage:** Core infrastructure files (router, Axios, Time) are translated; individual Vue view templates still use hardcoded Chinese (41 views × ~50 strings each = ~2000 strings to translate) — **Resolved in v2.2**

---

### Future Improvements (Not Yet Implemented)
- [x] ~~Translate all 41 Vue view templates~~ — Core views translated (login, register, first_home); remaining views pending
- [x] ~~Add Grafana dashboards for Prometheus metrics~~ — Done in v2.1
- [x] ~~Per-user rate limiting with Redis backend~~ — Done in v2.1 (Redis sorted sets)
- [x] ~~WebSocket authentication (JWT handshake)~~ — Done in v2.1
- [x] ~~Translate remaining 38 Vue view templates (~1800 strings)~~ — Done in v2.2 (all 49 views, 1200+ keys)
- [x] ~~Add alerting rules to Grafana~~ — Done in v2.3 (error rate, latency, DB, cache alerts)
- [x] ~~Add Loki for log aggregation in Grafana~~ — Done in v2.3 (Loki + Promtail + logs dashboard)
- [x] ~~Admin sub-role differentiation~~ — Done in v2.3 (admin1/admin2/admin3 enforcement)
- [x] ~~Application withdrawal~~ — Done in v2.3 (PUT /api/applications/{id}/withdraw)
- [x] ~~Multi-algorithm raster watermark~~ — Done in v2.3 (LSB, DWT, Histogram Shifting)
- [ ] Increase test coverage to 80%+ (currently ~50% of endpoints covered)
- [ ] Add integration tests with real MySQL/PostgreSQL
- [ ] Add E2E tests with Playwright or Cypress
- [ ] Redis session store for multi-instance deployments

---

## [v1.0.0] — 2026-05-06 (Initial Production Release)

### Features
- Flask backend with 76 API endpoints
- Vue 3 frontend with 41 views
- Dual-database (MySQL + PostgreSQL/PostGIS)
- QR code watermark generation/embedding/extraction
- Two-level approval workflow
- JWT authentication with refresh tokens
- Docker containerization
- GitHub Actions CI/CD
- Ruff + ESLint code quality
- Production logging with file rotation
- Database indexing for query performance
- Security headers middleware
- Health check endpoint
