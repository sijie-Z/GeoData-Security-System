# Changelog — GeoData Security System

All notable changes to this project are documented in this file.

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
5. **i18n coverage:** Core infrastructure files (router, Axios, Time) are translated; individual Vue view templates still use hardcoded Chinese (41 views × ~50 strings each = ~2000 strings to translate)

---

### Future Improvements (Not Yet Implemented)
- [x] ~~Translate all 41 Vue view templates~~ — Core views translated (login, register, first_home); remaining views pending
- [x] ~~Add Grafana dashboards for Prometheus metrics~~ — Done in v2.1
- [x] ~~Per-user rate limiting with Redis backend~~ — Done in v2.1 (Redis sorted sets)
- [x] ~~WebSocket authentication (JWT handshake)~~ — Done in v2.1
- [ ] Translate remaining 38 Vue view templates (~1800 strings)
- [ ] Increase test coverage to 80%+ (currently ~50% of endpoints covered)
- [ ] Add integration tests with real MySQL/PostgreSQL
- [ ] Add E2E tests with Playwright or Cypress
- [ ] Redis session store for multi-instance deployments
- [ ] Add alerting rules to Grafana (error rate thresholds, latency alerts)
- [ ] Add Loki for log aggregation in Grafana

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
