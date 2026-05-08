# Changelog — GeoData Security System

All notable changes to this project are documented in this file.

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
