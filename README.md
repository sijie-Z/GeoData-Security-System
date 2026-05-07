# GeoData Security System

<div align="center">

![Vue 3](https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat-square&logo=flask)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-336791?style=flat-square&logo=postgresql)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker)
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

### Technical Highlights
- **Dual-database Architecture** — MySQL for business data, PostgreSQL + PostGIS for spatial data
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
│  │  Vue 3   │ │ Element Plus │ │   Pinia   │ │ Leaflet   │ │
│  │ (SFC)    │ │  (UI Kit)    │ │ (State)   │ │ (Maps)    │ │
│  └──────────┘ └──────────────┘ └───────────┘ └───────────┘ │
│  ┌──────────┐ ┌──────────────┐ ┌───────────┐               │
│  │ Vue Router│ │   Axios      │ │ Three.js  │               │
│  │ (Lazy)   │ │ (Intercept)  │ │ (3D BG)   │               │
│  └──────────┘ └──────────────┘ └───────────┘               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/JSON (JWT Bearer)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Flask)                            │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │ Flask-RESTful│ │ Flask-JWT    │ │   Flask-Limiter     │ │
│  │  (API)       │ │ (Auth)       │ │   (Rate Limit)      │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │ SQLAlchemy   │ │  rasterio    │ │   qrcode + pyzbar   │ │
│  │  (ORM)       │ │ (Tile Slice) │ │   (Watermark)       │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└──────────┬──────────────────────────────────┬───────────────┘
           ▼                                  ▼
┌─────────────────────┐          ┌──────────────────────────┐
│   MySQL 8.0         │          │  PostgreSQL + PostGIS    │
│  ┌───────────────┐  │          │  ┌────────────────────┐  │
│  │ users         │  │          │  │ vector_data (shp)  │  │
│  │ applications  │  │          │  │ raster_data (tif)  │  │
│  │ logs          │  │          │  │ spatial queries    │  │
│  │ chat          │  │          │  └────────────────────┘  │
│  │ notifications │  │          │                          │
│  └───────────────┘  │          │                          │
└─────────────────────┘          └──────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Vue 3 + Composition API | Reactive UI framework |
| | Element Plus | Enterprise UI component library |
| | Pinia | State management |
| | Vue Router | Client-side routing with guards |
| | Axios | HTTP client with interceptors |
| | Leaflet | Map rendering and tile layers |
| | ECharts | Dashboard analytics charts |
| | Three.js | 3D particle effects (login page) |
| **Backend** | Flask + Flask-RESTful | REST API framework |
| | Flask-JWT-Extended | JWT authentication |
| | SQLAlchemy | ORM with dual-database binds |
| | Flask-Migrate (Alembic) | Database migrations |
| | Flask-Limiter | API rate limiting |
| | rasterio / geopandas | Spatial data processing |
| | qrcode / pyzbar | QR watermark generation/extraction |
| **Database** | MySQL 8.0 | Business data (users, apps, logs) |
| | PostgreSQL + PostGIS | Spatial data (vectors, rasters) |
| **DevOps** | Docker + docker-compose | Containerized deployment |
| | GitHub Actions | CI/CD pipeline |
| | Ruff | Python linting |
| | ESLint + Prettier | JS/Vue linting |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- MySQL 8.0
- PostgreSQL with PostGIS extension

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
This starts all services: frontend, backend, MySQL, PostgreSQL.

---

## Project Structure

```
GeoData-Security-System/
├── testrealend/                    # Flask backend
│   ├── app.py                      # Application entry point
│   ├── config.py                   # Environment-based configuration
│   ├── requirements.txt            # Python dependencies
│   ├── extension/
│   │   └── extension.py            # Flask extensions (db, limiter)
│   ├── model/                      # SQLAlchemy models
│   │   ├── Application.py          # Data application model
│   │   ├── Employee_Account.py     # Employee account model
│   │   ├── Adm_Account.py          # Admin account model
│   │   ├── RecallProposal.py       # Recall voting model
│   │   └── ...
│   ├── resource/                   # API endpoints (Flask-RESTful)
│   │   ├── common_resource.py      # Auth (login/register/refresh)
│   │   ├── application_resource.py # Application CRUD + approval
│   │   ├── watermark_resource.py   # Watermark generate/embed/extract
│   │   ├── recall_resource.py      # Recall voting system
│   │   └── ...
│   ├── algorithm/                  # Watermark algorithms
│   │   ├── embed.py                # Vector watermark embedding
│   │   ├── extract.py              # Vector watermark extraction
│   │   ├── raster_embed_lsb.py     # Raster LSB steganography
│   │   └── ...
│   ├── utils/
│   │   └── log_helper.py           # Audit logging utility
│   ├── migrations/                 # Alembic migrations
│   └── Dockerfile
│
├── testrealfrontol/                # Vue 3 frontend
│   ├── src/
│   │   ├── main.js                 # App entry point
│   │   ├── App.vue                 # Root component
│   │   ├── router/index.js         # Route definitions + guards
│   │   ├── stores/
│   │   │   └── userStore.js        # Pinia auth state
│   │   ├── utils/
│   │   │   └── Axios.js            # HTTP client + interceptors
│   │   ├── views/
│   │   │   ├── admin/              # Admin pages (25+ views)
│   │   │   ├── employee/           # Employee pages (15+ views)
│   │   │   ├── login.vue           # Login with 3D background
│   │   │   └── register.vue        # Registration
│   │   ├── components/             # Reusable components
│   │   └── api/                    # API service layer
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml              # Multi-container orchestration
├── .github/workflows/ci.yml        # GitHub Actions CI
├── .gitignore
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
docker-compose -f docker-compose.yml up -d --build

# View logs
docker-compose logs -f backend

# Stop all services
docker-compose down
```

### Manual Production
```bash
# Backend (Gunicorn)
cd testrealend
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5003 "app:create_app()"

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
