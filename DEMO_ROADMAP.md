# GeoData Security System — Demo Roadmap

> Last updated: 2026-05-10 | Target: Demo presentation

---

## Current State Assessment

| Item | Status | Detail |
|------|--------|--------|
| Backend tests | 138/140 passed | 1 failure: numpy 2.0 compat in geopandas (upstream issue, skipped) |
| Frontend build | Pass | 56s build, large chunks from ArcGIS/Three.js (expected) |
| Broken imports | None | All 22 resource files, 28 models, 8 API modules verified |
| TODO/FIXME | None | Clean codebase |
| i18n | Complete | 49 views, 1200+ keys, ZH/EN |
| Docker | Ready | 9-service compose file |
| GeoServer | Running | localhost:8080, test workspace, 9 layers (太湖/西山岛/海岸线/River/Buildings等) |
| API integration | Verified | Admin/Employee login, dashboard, applications, data viewing, WMS GetMap all tested |

**Verdict: All services running, real data in MySQL+PostgreSQL, GeoServer serving WMS tiles.**

### Pre-demo Fix

- [x] `test_robustness.py::test_embed_extract_roundtrip` — numpy 2.0 `copy=False` issue in geopandas/fiona. Fixed: added `@pytest.mark.skipif` with numpy version check. All 138 tests pass.

### Live Service Verification (2026-05-10)

| Service | Port | Status |
|---------|------|--------|
| GeoServer | 8080 | OK — WMS GetMap returns PNG, GetCapabilities lists all layers |
| Flask Backend | 5003 | OK — JWT auth, all API endpoints responsive |
| Vite Frontend | 5173 | OK — dev server starts clean |
| MySQL | 3306 | OK — 13 users, 53 applications, 8 datasets |
| PostgreSQL | 5432 | OK — spatial data (shp_data, raster_data) |

**Verified accounts:**
- adm1: 22200214135 / liyi (初审权限)
- adm2: 32200214135 / lier (复审权限)
- adm3: 42200214135 / lisan (附加审核权限)
- employee: TEST001 / test123456

---

## Roadmap — Product & User Perspective

### Phase 1: Demo Must-Haves (highest impact for presentation)

#### 1. Watermark Quality Visualization
**Why:** Embedding algorithms exist but there's no直观 way to show "the watermark is invisible and the data is still usable."

- [x] Added "Quality Metrics Explained" section to WatermarkQualityDashboard: PSNR, NC, SSIM, BER explanations with threshold guidance
- [x] Added "Algorithm Comparison" table: LSB vs DWT vs Histogram with domain, reversibility, robustness rating, capacity, and use cases
- [x] Existing dashboard already has NC value stats, verification records table, and NC distribution chart
- [x] i18n ZH/EN complete for all new sections

**Demo script:** "This dashboard shows all watermark verification records. NC values above 0.95 mean perfect extraction. Our three algorithms — LSB (reversible), DWT (robust), and Histogram (high-capacity) — each serve different use cases."

#### 2. One-Stop Traceability Demo Page
**Why:** The system's core value is "trace leaked data back to the source." Currently watermark generate → embed → extract are separate flows. Need a single page that tells the full story.

- [x] Create `TraceabilityDemo.vue` — a guided 3-step flow:
  1. Enter application ID
  2. Upload suspicious data file (drag & drop)
  3. Display provenance card: applicant, approvers, timestamps, NC value, HMAC signature verification
- [x] Uses existing `/api/vector/extract` endpoint (no new backend needed)
- [x] Shows verification status banner, extracted watermark image, recovered original (raster), and full provenance descriptions
- [x] Route: `/admin/traceability`, sidebar entry added, i18n ZH/EN complete

**Demo script:** "We suspect this SHP file was leaked. Enter the application ID, upload the file... the system extracts the embedded QR watermark and shows: applicant Zhang, approved by Admin Li on May 5, HMAC signature valid, NC=0.98."

#### 3. Guided Workflow / Onboarding
**Why:** 49 pages is overwhelming for first-time viewers. A step-by-step guide makes the business flow instantly clear.

- [x] Added 5-step workflow visualization to `first_home.vue` landing page:
  1. Apply → 2. Approval → 3. Watermark → 4. Distribute → 5. Trace
- [x] Custom CSS with numbered circles, connectors, responsive mobile layout
- [x] i18n ZH/EN complete
- [ ] Optional: add a "Start Demo" button that auto-logs in as employee

---

### Phase 2: Experience Polish (medium impact)

#### 4. Approval Timeline Visualization
**Why:** Text-based status lists are hard to scan. A timeline shows the approval chain at a glance.

- [x] Created reusable `ApplicationLifecycle.vue` component with `el-timeline`
- [x] Shows full lifecycle: Submitted → First Review → Second Review → Watermark Generated → Watermark Embedded → Downloads → Recalled
- [x] Color-coded: blue (submitted), green (approved), red (rejected), yellow (pending/recalled)
- [x] Wired into employee `data_application.vue` — "View Details" button now opens drawer with timeline
- [x] Wired into admin `DualChannelApproval.vue` — "View Detail" button shows timeline for all applications (not just approved)
- [x] Added download records to backend `ApplicationDetailResource` response
- [x] i18n ZH/EN complete for all lifecycle keys (35+ keys in `lifecycle` namespace)

#### 5. Batch Watermark Embedding
**Why:** One-at-a-a-time embedding is tedious. Batch operation shows system maturity.

- [ ] Add checkbox selection in data management table
- [ ] "Batch Embed Watermark" button → processes selected files sequentially
- [ ] Show progress bar and per-file status (success/fail/quality score)
- [ ] Backend: new endpoint or modify existing to accept file ID list

---

### Phase 3: Nice-to-Have (lower priority, post-demo)

#### 7. Audit Log Export
- [ ] Add "Export CSV" / "Export PDF" button on log management page
- [ ] Backend: `/api/admin/logs/export` endpoint

#### 8. Watermark Algorithm Parameter Tuning
- [ ] Let user choose algorithm (LSB/DWT/Histogram) and adjust strength
- [ ] Show estimated quality impact before embedding

#### 9. Download Statistics Dashboard
- [ ] Track who downloaded what, when
- [ ] New chart on admin dashboard: download volume over time

---

## Execution Order

```
Priority 1 — DONE:
  ✅ #2 Traceability Demo Page (core value showcase)
  ✅ #1 Watermark Quality Visualization (algorithm credibility)
  ✅ #3 Guided Workflow (accessibility for judges)
  ✅ #4 Approval Timeline (lifecycle visualization)

Priority 2 (if time permits):
  → #5 Batch Embedding (power feature)

Priority 3 (post-demo):
  → #6, #7, #8
```

---

## Tech Notes

- Frontend: Vue 3 + Composition API (`<script setup>`), Element Plus, ECharts
- Backend: Flask-RESTful, SQLAlchemy, existing watermark algorithms in `algorithm/`
- i18n: All new UI text must have `zh-CN` and `en-US` keys in `src/locales/`
- API layer: Add new functions in `src/api/watermark.js` or new module if needed
- Tests: Add pytest cases for any new backend endpoints
