# GeoData Security System

<div align="center">

![Vue 3](https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-336791?style=flat-square&logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)
![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-E6522C?style=flat-square&logo=prometheus)
![i18n](https://img.shields.io/badge/i18n-ZH%20%7C%20EN-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

**Enterprise-grade spatial data security distribution and traceability platform**

A full-stack platform for geospatial data (vector & raster) lifecycle management — from application, dual-level approval, QR-code watermark embedding, to secure distribution and source tracing.

[Features](#features) · [Architecture](#architecture) · [Quick Start](#quick-start) · [API Docs](#api-documentation) · [Deployment](#deployment)

</div>

---

## Features

### Core Capabilities
- **Dual-level Approval Workflow** — Two-admin review pipeline with real-time status tracking
- **QR Code Watermark System** — Generate, embed, and extract QR-code watermarks in vector (SHP) and raster (GeoTIFF) data
- **HMAC-SHA256 Signature** — Cryptographic signature prevents watermark forgery
- **Tile-based Raster Rendering** — On-demand tile slicing via `rasterio` for large GeoTIFF files
- **Data Recall Voting** — Democratic recall mechanism with admin voting (>50% opposition triggers recall)
- **Admin Promotion System** — Employee-to-admin application with 66% approval threshold

### Platform Features
- **Role-based Access Control** — Employee, Admin (adm1/adm2/adm3), fine-grained route-level permissions
- **JWT Authentication** — Access + refresh token flow with automatic renewal
- **Real-time Chat** — Internal messaging with friend system and read receipts
- **Notification System** — Targeted and broadcast announcements
- **Operation Audit Log** — Full activity trail with filtering by user, action type, and time range
- **Dashboard Analytics** — Admin and employee dashboards with ECharts visualizations
- **Internationalization (i18n)** — Chinese and English language support with runtime switching

### Technical Highlights
- **Dual-database Architecture** — MySQL for business data, PostgreSQL + PostGIS for spatial data
- **Redis Caching** — Hot query caching for dashboards and data listings with graceful fallback
- **WebSocket Notifications** — Real-time push via Socket.IO for application status updates
- **Prometheus Metrics** — Request latency, error rates, business KPIs exposed at `/metrics`
- **Per-user Rate Limiting** — JWT-identity-based rate limiting (not just IP)
- **Rate Limiting** — Flask-Limiter with configurable per-endpoint limits
- **Request Interceptors** — Axios interceptors for automatic token injection and 401 refresh
- **Lazy-loaded Routes** — Code splitting via dynamic imports for optimal bundle size
- **3D Particle Background** — Three.js powered login page with responsive canvas

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Vue 3)                        │
│  ┌──────────┐ ┌──────────────┐ ┌───────────┐ ┌───────────┐ │
│  │  Vue 3   │ │ Element Plus │ │   Pinia   │ │ vue-i18n  │ │
│  │ (SFC)    │ │  (UI Kit)    │ │ (State)   │ │ (ZH/EN)   │ │
│  └──────────┘ └──────────────┘ └───────────┘ └───────────┘ │
│  ┌──────────┐ ┌──────────────┐ ┌───────────┐               │
│  │ Vue Router│ │   Axios      │ │ Socket.IO │               │
│  │ (Lazy)   │ │ (Intercept)  │ │ (Realtime)│               │
│  └──────────┘ └──────────────┘ └───────────┘               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/JSON (JWT Bearer) + WebSocket
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Flask)                            │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │ Flask-RESTful│ │ Flask-JWT    │ │   Flask-SocketIO    │ │
│  │  (API)       │ │ (Auth)       │ │   (WebSocket)       │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │ SQLAlchemy   │ │  Redis Cache │ │   Prometheus        │ │
│  │  (ORM)       │ │ (Hot Query)  │ │   (Metrics)         │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │ Flask-Limiter│ │  rasterio    │ │   qrcode + pyzbar   │ │
│  │ (Rate Limit) │ │ (Tile Slice) │ │   (Watermark)       │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└──────────┬──────────────────────────────────┬───────────────┘
           ▼                                  ▼
┌─────────────────────┐  ┌──────────────┐  ┌──────────────────┐
│   MySQL 8.0         │  │ Redis 7      │  │ PostgreSQL+PostGIS│
│  users, apps, logs  │  │ Cache layer  │  │ vector/raster data│
└─────────────────────┘  └──────────────┘  └──────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Vue 3 + Composition API | Reactive UI framework |
| | Element Plus | Enterprise UI component library |
| | Pinia | State management |
| | Vue Router | Client-side routing with guards |
| | vue-i18n | Internationalization (ZH/EN) |
| | Axios | HTTP client with interceptors |
| | Socket.IO Client | Real-time WebSocket notifications |
| | Leaflet | Map rendering and tile layers |
| | ECharts | Dashboard analytics charts |
| | Three.js | 3D particle effects (login page) |
| **Backend** | Flask + Flask-RESTful | REST API framework |
| | Flask-JWT-Extended | JWT authentication |
| | Flask-SocketIO | WebSocket real-time events |
| | SQLAlchemy | ORM with dual-database binds |
| | Flask-Migrate (Alembic) | Database migrations |
| | Flask-Limiter | API rate limiting |
| | Redis | Response caching layer |
| | prometheus_client | Metrics collection |
| | rasterio / geopandas | Spatial data processing |
| | qrcode / pyzbar | QR watermark generation/extraction |
| **Database** | MySQL 8.0 | Business data (users, apps, logs) |
| | PostgreSQL + PostGIS | Spatial data (vectors, rasters) |
| | Redis 7 | Cache and session store |
| **DevOps** | Docker + docker-compose | Containerized deployment (6 services) |
| | Prometheus | Metrics monitoring |
| | GitHub Actions | CI/CD pipeline |
| | Ruff | Python linting |
| | ESLint | JS/Vue linting |
| | pre-commit | Git hooks |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- MySQL 8.0
- PostgreSQL with PostGIS extension
- Redis 7 (optional, caching works without it)

### 1. Clone the repository
```bash
git clone https://github.com/sijie-Z/GeoData-Security-System.git
cd GeoData-Security-System
```

### 2. Backend setup
```bash
cd testrealend

# Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run the server
python app.py
```
Backend starts at **http://localhost:5003**

### 3. Frontend setup
```bash
cd testrealfrontol

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env if needed (default: http://localhost:5003)

# Start dev server
npm run dev
```
Frontend starts at **http://localhost:5173**

### 4. Docker (recommended)
```bash
docker-compose up -d
```
This starts all 6 services: frontend, backend, MySQL, PostgreSQL, Redis, Prometheus.

---

## Project Structure

```
GeoData-Security-System/
├── testrealend/                    # Flask backend
│   ├── app.py                      # Application entry point
│   ├── config.py                   # Environment-based configuration
│   ├── requirements.txt            # Python dependencies
│   ├── pyproject.toml              # Ruff, pytest, coverage config
│   ├── extension/
│   │   └── extension.py            # Flask extensions (db, limiter)
│   ├── model/                      # SQLAlchemy models (29 classes)
│   ├── resource/                   # API endpoints (76 routes)
│   ├── algorithm/                  # Watermark algorithms
│   ├── utils/
│   │   ├── cache.py                # Redis caching layer
│   │   ├── metrics.py              # Prometheus metrics
│   │   ├── websocket.py            # Socket.IO event handlers
│   │   ├── user_limiter.py         # Per-user JWT rate limiting
│   │   ├── logging_config.py       # Production logging
│   │   └── log_helper.py           # Audit logging utility
│   ├── tests/                      # Pytest test suite (15+ files)
│   └── Dockerfile
│
├── testrealfrontol/                # Vue 3 frontend
│   ├── src/
│   │   ├── main.js                 # App entry point
│   │   ├── locales/                # i18n locale files
│   │   │   ├── zh-CN.js            # Chinese translations
│   │   │   ├── en-US.js            # English translations
│   │   │   └── index.js            # i18n configuration
│   │   ├── router/index.js         # Route definitions + guards
│   │   ├── stores/userStore.js     # Pinia auth state
│   │   ├── utils/
│   │   │   ├── Axios.js            # HTTP client + interceptors
│   │   │   └── Time.js             # Time utilities
│   │   ├── views/                  # 41 view components
│   │   ├── components/             # Reusable components
│   │   │   └── common/
│   │   │       ├── LanguageSwitcher.vue
│   │   │       ├── LoadingSkeleton.vue
│   │   │       ├── EmptyState.vue
│   │   │       └── NotificationCenter.vue
│   │   └── api/                    # API service layer
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml              # Multi-container orchestration (6 services)
├── prometheus.yml                  # Prometheus scrape config
├── .github/workflows/ci.yml        # GitHub Actions CI
├── .pre-commit-config.yaml         # Pre-commit hooks
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## API Documentation

The backend exposes a RESTful API. Key endpoints:

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/register` | Employee registration |
| POST | `/api/login` | Login (employee/admin) |
| POST | `/api/refresh-token` | Refresh access token |
| POST | `/api/logout` | Logout |

### Applications
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/submit_application` | Submit data application |
| GET | `/api/get_applications` | Get user's applications |
| POST | `/api/adm1_pass` | Admin 1 approve |
| POST | `/api/adm2_pass` | Admin 2 approve |
| POST | `/api/admin/batch_review` | Batch review |

### Watermark
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generate_watermark` | Generate QR watermark |
| POST | `/api/embedding_watermark` | Embed watermark in data |
| POST | `/api/vector/extract` | Extract watermark from data |
| GET | `/api/raster_tiles/{id}/{z}/{x}/{y}.png` | Raster tile serving |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check (DB + Redis) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/api/admin/dashboard` | Admin dashboard stats |
| GET | `/api/admin/logs` | System operation logs |
| POST | `/api/recall/create` | Create recall proposal |
| POST | `/api/recall/{id}/vote` | Vote on recall |

Full API documentation available at `/apidocs/` when running (Swagger UI via Flasgger).

---

## Deployment

### Docker Production
```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

### Manual Production
```bash
# Backend (Gunicorn with eventlet for Socket.IO)
cd testrealend
gunicorn -w 4 -b 0.0.0.0:5003 -k eventlet "app:create_app()"

# Frontend (Nginx)
cd testrealfrontol
npm run build
# Serve dist/ with Nginx
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
Made with passion for geospatial data security
</div>
