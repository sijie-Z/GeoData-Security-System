<template>
  <section class="dfg-card">
    <header class="dfg-head">
      <div class="dfg-titles">
        <h2 class="dfg-title">{{ t('dataFlow.title') }}</h2>
        <p class="dfg-subtitle">{{ subtitleText }}</p>
      </div>
      <div class="dfg-legend">
        <span class="dfg-chip"><i class="dfg-dot dot-origin"></i>{{ t('dataFlow.legendOrigin') }}</span>
        <span class="dfg-chip"><i class="dfg-dot dot-vector"></i>{{ t('dataFlow.legendVector') }}</span>
        <span class="dfg-chip"><i class="dfg-dot dot-raster"></i>{{ t('dataFlow.legendRaster') }}</span>
      </div>
    </header>

    <div class="dfg-stage">
      <div v-if="loading" class="dfg-state">
        <el-icon class="dfg-spin motion-loop" :size="26"><Loading /></el-icon>
        <span>{{ t('common.loading') }}</span>
      </div>
      <el-empty v-else-if="arcs.length === 0" class="dfg-state" :description="t('dataFlow.empty')" :image-size="72" />
      <div
        v-show="!loading && arcs.length > 0"
        ref="stageRef"
        class="dfg-canvas-host"
        role="img"
        :aria-label="t('dataFlow.canvasLabel')"
      >
        <div v-if="tip.visible && tip.arc" class="dfg-tip" :style="tipStyle">
          <div class="dfg-tip-head">
            <i class="dfg-dot" :style="{ background: typeColor(tip.arc.type) }"></i>
            <span>{{ typeLabel(tip.arc.type) }}</span>
          </div>
          <div class="dfg-tip-row"><span>{{ t('dataFlow.hoverUser') }}</span><b>{{ tip.arc.user }}</b></div>
          <div class="dfg-tip-row"><span>{{ t('dataFlow.hoverDelivery') }}</span><b>{{ tip.arc.uuid.slice(0, 8) }}</b></div>
          <div class="dfg-tip-row"><span>{{ t('dataFlow.hoverFid') }}</span><b>{{ tip.arc.fid }}</b></div>
          <div class="dfg-tip-row"><span>{{ t('dataFlow.hoverTime') }}</span><b>{{ tip.arc.time }}</b></div>
          <div class="dfg-tip-row"><span>{{ t('dataFlow.hoverCity') }}</span><b>{{ tip.arc.city || t('dataFlow.cityPseudo') }}</b></div>
        </div>
      </div>
    </div>

    <p v-if="!loading && arcs.length > 0" class="dfg-footnote">
      {{ t('dataFlow.arcFootnote', { n: arcs.length }) }}
      <template v-if="pseudoCount > 0"> · {{ t('dataFlow.pseudoNote', { count: pseudoCount }) }}</template>
    </p>
  </section>
</template>

<script setup>
defineOptions({ name: 'DataFlowGlobe' });

import { ref, reactive, computed, watch, nextTick, onMounted, onActivated, onDeactivated, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { Loading } from '@element-plus/icons-vue';
import { getDeliveryStats, getDeliveries } from '@/api/forensics';
import { getEmployeeInfo } from '@/api/admin';

const { t, locale } = useI18n();
const router = useRouter();

// ── 常量：与 three-globe 内部几何保持一致 ──────────────────────────
const GLOBE_RADIUS = 100; // three-globe 世界单位半径
const ARC_ALT_AUTOSCALE = 0.5; // 弧线最高点自动缩放（拾取曲线必须同值复刻）
const ORIGIN = { lat: 39.9042, lng: 116.4074 }; // 起点：数据中心（北京）
const ORIGIN_COLOR = '#ffd166';
const TYPE_COLORS = { vector: '#4fc3f7', raster: '#F59E0B', unknown: '#8fa3b8' };
const RAD = Math.PI / 180;
const DEG = 180 / Math.PI;

// 中国主要城市名 → 经纬度（对 address 做「城市名包含匹配」，按列表顺序优先）
const CITY_COORDS = [
  ['北京', 39.9042, 116.4074], ['上海', 31.2304, 121.4737], ['广州', 23.1291, 113.2644],
  ['深圳', 22.5431, 114.0579], ['成都', 30.5728, 104.0668], ['重庆', 29.5630, 106.5516],
  ['杭州', 30.2741, 120.1551], ['武汉', 30.5928, 114.3055], ['西安', 34.3416, 108.9398],
  ['南京', 32.0603, 118.7969], ['天津', 39.3434, 117.3616], ['苏州', 31.2989, 120.5853],
  ['郑州', 34.7466, 113.6254], ['长沙', 28.2282, 112.9388], ['青岛', 36.0671, 120.3826],
  ['沈阳', 41.8057, 123.4315], ['宁波', 29.8683, 121.5440], ['昆明', 25.0389, 102.7183],
  ['合肥', 31.8206, 117.2272], ['佛山', 23.0218, 113.1219], ['无锡', 31.4912, 120.3119],
  ['厦门', 24.4798, 118.0894], ['济南', 36.6512, 117.1201], ['大连', 38.9140, 121.6147],
  ['福州', 26.0745, 119.2965], ['哈尔滨', 45.8038, 126.5340], ['温州', 27.9938, 120.6994],
  ['石家庄', 38.0428, 114.5149], ['南宁', 22.8170, 108.3665], ['长春', 43.8171, 125.3235],
  ['南昌', 28.6820, 115.8579], ['贵阳', 26.6470, 106.6302], ['太原', 37.8706, 112.5489],
  ['乌鲁木齐', 43.8256, 87.6168], ['兰州', 36.0611, 103.8343], ['海口', 20.0444, 110.1999],
  ['珠海', 22.2710, 113.5767], ['东莞', 23.0207, 113.7518], ['中山', 22.5176, 113.3927],
  ['呼和浩特', 40.8424, 111.7492], ['银川', 38.4872, 106.2309], ['西宁', 36.6171, 101.7782],
  ['拉萨', 29.6520, 91.1721],
];

// FNV-1a 32 位哈希：user_number → 确定性伪坐标（固定 seed → 固定点位）
function hashCode(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

// 伪坐标落在中国区域经纬度范围内（lat 20~47, lng 80~130），纯示意
function pseudoCoords(seed) {
  const h = hashCode(`dfg:${seed}`);
  const a = (h & 0xffff) / 0xffff;
  const b = ((h >>> 16) & 0xffff) / 0xffff;
  return { lat: 20 + a * 27, lng: 80 + b * 50 };
}

function matchCity(address) {
  if (!address) return null;
  for (const [name, lat, lng] of CITY_COORDS) {
    if (address.includes(name)) return { name, lat, lng };
  }
  return null;
}

// ── 状态 ──────────────────────────────────────────
const loading = ref(true);
const arcs = ref([]); // [{ key, uuid, user, fid, time, type, city, pseudo, startLat, ... }]
const totalDeliveries = ref(0);
const stageRef = ref(null);
const tip = reactive({ visible: false, x: 0, y: 0, arc: null });

const pseudoCount = computed(() => arcs.value.filter((a) => a.pseudo).length);
const coveredUsers = computed(() => new Set(arcs.value.map((a) => a.user)).size);
const subtitleText = computed(() =>
  t('dataFlow.subtitle', { total: totalDeliveries.value, arcs: arcs.value.length, users: coveredUsers.value })
);
const tipStyle = computed(() => ({ left: `${tip.x}px`, top: `${tip.y}px` }));

const typeColor = (type) => TYPE_COLORS[type] || TYPE_COLORS.unknown;
const typeLabel = (type) => {
  if (type === 'vector') return t('dataFlow.typeVector');
  if (type === 'raster') return t('dataFlow.typeRaster');
  return t('dataFlow.typeUnknown');
};

// ── 数据加载：stats 为主源 + 交付列表补充 data_type + 员工地址做城市映射 ──
async function loadData() {
  loading.value = true;
  const [statsRes, listRes, empRes] = await Promise.allSettled([
    getDeliveryStats(),
    getDeliveries({ limit: 10 }),
    getEmployeeInfo({ page: 1, pageSize: 500 }),
  ]);

  let recent = [];
  if (statsRes.status === 'fulfilled' && statsRes.value?.data?.stats) {
    const stats = statsRes.value.data.stats;
    recent = Array.isArray(stats.recent) ? stats.recent : [];
    totalDeliveries.value = stats.total || 0;
  } else if (statsRes.status === 'rejected') {
    console.warn('[DataFlowGlobe] deliveries/stats 获取失败:', statsRes.reason?.message || statsRes.reason);
  }

  // data_type 不在 stats.recent 中，用同排序（最近 10 条）的交付列表按 uuid 关联
  const typeByUuid = new Map();
  if (listRes.status === 'fulfilled') {
    for (const item of listRes.value?.data?.deliveries || []) {
      typeByUuid.set(item.uuid, item.data_type || 'unknown');
    }
  }

  const addressByNumber = new Map();
  if (empRes.status === 'fulfilled') {
    for (const emp of empRes.value?.data?.data?.list || []) {
      if (emp.employee_number) addressByNumber.set(emp.employee_number, emp.address || '');
    }
  }

  arcs.value = recent.map((r, i) => {
    const type = typeByUuid.get(r.uuid);
    const city = matchCity(addressByNumber.get(r.user_number) || '');
    const coords = city || pseudoCoords(r.user_number || r.uuid || `n${i}`);
    return {
      key: r.uuid || `arc-${i}`,
      i,
      uuid: r.uuid || '',
      user: r.user_number || '-',
      fid: (r.fid_short || '').slice(0, 12) || '-',
      time: r.created_at ? new Date(r.created_at).toLocaleString() : '-',
      type: type === 'vector' || type === 'raster' ? type : 'unknown',
      city: city ? city.name : null,
      pseudo: !city,
      startLat: ORIGIN.lat,
      startLng: ORIGIN.lng,
      endLat: coords.lat,
      endLng: coords.lng,
    };
  });

  loading.value = false;
  if (arcs.value.length > 0) {
    await nextTick();
    await initGlobe();
  }
}

// ── three / three-globe 运行时（非响应式，全部在 onBeforeUnmount 清理） ──
let THREE = null;
let globe = null;
let renderer = null;
let scene = null;
let camera = null;
let controls = null;
let resizeObserver = null;
let rafId = null;
let running = false;
let disposed = false;
let active = true;
let pointer = null;
let raycaster = null;
let pickCurves = []; // [{ data, curve, points }] 用于 hover 拾取（复刻 three-globe 曲线数学）
let hoverInfo = null;
let hoverOverlay = null;
let hoverMaterial = null;
let glowTexture = null;
const disposables = []; // 自建 texture/material/geometry 的销毁清单

const prefersReducedMotion =
  typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

function latLngToVec(lat, lng, relAlt = 0) {
  const phi = (90 - lat) * RAD;
  const theta = (90 - lng) * RAD;
  const r = GLOBE_RADIUS * (1 + relAlt);
  return new THREE.Vector3(r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

// 复刻 d3.geoInterpolate：大圆插值（输入/输出 [lng, lat]）
function geoInterp(a, b) {
  const x0 = a[0] * RAD, y0 = a[1] * RAD, x1 = b[0] * RAD, y1 = b[1] * RAD;
  const cy0 = Math.cos(y0), sy0 = Math.sin(y0), cy1 = Math.cos(y1), sy1 = Math.sin(y1);
  const kx0 = cy0 * Math.cos(x0), ky0 = cy0 * Math.sin(x0);
  const kx1 = cy1 * Math.cos(x1), ky1 = cy1 * Math.sin(x1);
  const hv = (v) => Math.sin(v / 2) ** 2;
  const d = 2 * Math.asin(Math.sqrt(hv(y1 - y0) + cy0 * cy1 * hv(x1 - x0)));
  const k = Math.sin(d);
  if (!d) return () => [a[0], a[1]];
  return (u) => {
    const B = Math.sin(u * d) / k;
    const A = Math.sin((1 - u) * d) / k;
    const x = A * kx0 + B * kx1;
    const y = A * ky0 + B * ky1;
    const z = A * sy0 + B * sy1;
    return [Math.atan2(y, x) * DEG, Math.atan2(z, Math.sqrt(x * x + y * y)) * DEG];
  };
}

// 复刻 three-globe arcsLayer 的 calcCurve（altitude 为 null 时按大圆距离自动取值）
function buildArcCurve(d) {
  const startAlt = 0, endAlt = 0;
  const hv = (v) => Math.sin(v / 2) ** 2;
  const dPhi = (d.endLat - d.startLat) * RAD;
  const dLam = (d.endLng - d.startLng) * RAD;
  const angular = 2 * Math.asin(
    Math.sqrt(hv(dPhi) + Math.cos(d.startLat * RAD) * Math.cos(d.endLat * RAD) * hv(dLam))
  );
  const altitude = (angular / 2) * ARC_ALT_AUTOSCALE + Math.max(startAlt, endAlt);
  const interp = geoInterp([d.startLng, d.startLat], [d.endLng, d.endLat]);
  const calcAltCp = (a0, a1) => a1 + (a1 - a0) * (a0 < a1 ? 0.5 : 0.25);
  const m1 = interp(0.25);
  const m2 = interp(0.75);
  return new THREE.CubicBezierCurve3(
    latLngToVec(d.startLat, d.startLng, startAlt),
    latLngToVec(m1[1], m1[0], calcAltCp(startAlt, altitude)),
    latLngToVec(m2[1], m2[0], calcAltCp(endAlt, altitude)),
    latLngToVec(d.endLat, d.endLng, endAlt)
  );
}

// canvas 径向渐变 → 大气光晕贴图（不引任何外网图片资源）
function makeGlowTexture() {
  const size = 512;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, 'rgba(90, 180, 255, 0)');
  g.addColorStop(0.5, 'rgba(90, 180, 255, 0)');
  g.addColorStop(0.6, 'rgba(96, 190, 255, 0.32)');
  g.addColorStop(0.7, 'rgba(70, 150, 240, 0.12)');
  g.addColorStop(1, 'rgba(40, 90, 180, 0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function addStars() {
  const count = 650;
  const pos = new Float32Array(count * 3);
  let seed = 20261006; // 固定 seed：星空稳定不闪烁
  const rnd = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
  for (let i = 0; i < count; i++) {
    const u = rnd() * 2 - 1;
    const theta = rnd() * Math.PI * 2;
    const r = 800 + rnd() * 800;
    const s = Math.sqrt(1 - u * u);
    pos[i * 3] = r * s * Math.cos(theta);
    pos[i * 3 + 1] = r * u;
    pos[i * 3 + 2] = r * s * Math.sin(theta);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.PointsMaterial({
    color: 0x9fb8d8, size: 2.2, sizeAttenuation: false,
    transparent: true, opacity: 0.55, depthWrite: false,
  });
  disposables.push(geo, mat);
  scene.add(new THREE.Points(geo, mat));
}

async function initGlobe() {
  if (globe || disposed || !stageRef.value) return; // WebGL 上下文单例：本组件至多一个
  const [threeMod, globeMod, controlsMod] = await Promise.all([
    import('three'),
    import('three-globe'),
    import('three/addons/controls/OrbitControls.js'),
  ]);
  if (disposed || !stageRef.value) return;
  THREE = threeMod;
  const ThreeGlobe = globeMod.default;
  const { OrbitControls } = controlsMod;

  const host = stageRef.value;
  const width = host.clientWidth || 600;
  const height = host.clientHeight || 340;

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(width, height);
  renderer.setClearColor(0x000000, 0);
  host.appendChild(renderer.domElement);

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(40, width / height, 1, 5000);
  const camDist = 370;
  camera.position.copy(latLngToVec(ORIGIN.lat, ORIGIN.lng, camDist / GLOBE_RADIUS - 1));
  camera.lookAt(0, 0, 0);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.enablePan = false;
  controls.enableZoom = false;
  controls.rotateSpeed = 0.55;
  controls.autoRotate = !prefersReducedMotion;
  controls.autoRotateSpeed = 0.35;
  controls.addEventListener('start', onControlStart);
  controls.addEventListener('end', onControlEnd);
  controls.update();

  scene.add(new THREE.AmbientLight(0xbcd4f5, 2.0));
  const sun = new THREE.DirectionalLight(0xffffff, 2.4);
  sun.position.copy(latLngToVec(25, 135, 4));
  scene.add(sun);

  // ── 地球：纯色球体 + 经纬网格 + 大气光晕，零外网贴图 ──
  globe = new ThreeGlobe()
    .showGraticules(true)
    .showAtmosphere(true)
    .atmosphereColor('#38bdf8')
    .atmosphereAltitude(0.16);
  globe.globeMaterial(new THREE.MeshPhongMaterial({
    color: '#0b1b30', emissive: '#050d1a', emissiveIntensity: 0.6,
    specular: '#173a5e', shininess: 14,
  }));
  const graticules = globe.children.find((c) => c.isLineSegments);
  if (graticules?.material?.color) {
    graticules.material.color.set('#5f7fa8');
    graticules.material.transparent = true;
    graticules.material.opacity = 0.22;
  }

  const endpoints = buildEndpoints(arcs.value);
  const dashTime = prefersReducedMotion ? 0 : 4800;
  globe
    .arcsData(arcs.value)
    .arcStartLat((d) => d.startLat)
    .arcStartLng((d) => d.startLng)
    .arcEndLat((d) => d.endLat)
    .arcEndLng((d) => d.endLng)
    .arcColor((d) => [ORIGIN_COLOR, typeColor(d.type)])
    .arcAltitudeAutoScale(ARC_ALT_AUTOSCALE)
    .arcStroke((d) => (d.type === 'unknown' ? 0.4 : 0.5))
    .arcDashLength(0.55)
    .arcDashGap(0.45)
    .arcDashInitialGap((d) => (d.i % 5) * 0.2)
    .arcDashAnimateTime(dashTime)
    .arcsTransitionDuration(prefersReducedMotion ? 0 : 1200)
    .pointsData(endpoints)
    .pointLat((d) => d.lat)
    .pointLng((d) => d.lng)
    .pointColor((d) => typeColor(d.type))
    .pointAltitude(0.01)
    .pointRadius((d) => (d.pseudo ? 0.45 : 0.55))
    .pointResolution(16)
    .pointsMerge(false)
    .pointsTransitionDuration(prefersReducedMotion ? 0 : 900)
    .ringsData([{ lat: ORIGIN.lat, lng: ORIGIN.lng }])
    .ringLat((d) => d.lat)
    .ringLng((d) => d.lng)
    .ringColor(() => (u) => `rgba(255, 209, 102, ${Math.max(0, 1 - u)})`)
    .ringMaxRadius(4.2)
    .ringPropagationSpeed(1.4)
    .ringRepeatPeriod(prefersReducedMotion ? 0 : 1500)
    .ringAltitude(0.002)
    .labelsData([{ lat: ORIGIN.lat, lng: ORIGIN.lng, text: t('dataFlow.originLabel') }])
    .labelText((d) => d.text)
    .labelSize(0.65)
    .labelColor(ORIGIN_COLOR)
    .labelDotRadius(0.18)
    .labelResolution(2)
    .labelsTransitionDuration(0);
  scene.add(globe);

  // 大气光晕 sprite（球体正面会遮挡 sprite 中心，只在轮廓外显光环）
  glowTexture = makeGlowTexture();
  const glowMat = new THREE.SpriteMaterial({
    map: glowTexture, color: 0x4fc3f7, transparent: true, opacity: 0.6,
    blending: THREE.AdditiveBlending, depthWrite: false,
  });
  disposables.push(glowMat);
  const glow = new THREE.Sprite(glowMat);
  glow.scale.set(330, 330, 1);
  scene.add(glow);

  addStars();

  // ── hover 拾取曲线（与 three-globe 渲染曲线同款数学，独立于场景图） ──
  raycaster = new THREE.Raycaster();
  pickCurves = arcs.value.map((d) => {
    const curve = buildArcCurve(d);
    const points = [];
    for (let s = 0; s <= 64; s++) points.push(curve.getPoint(s / 64));
    return { data: d, curve, points };
  });

  pointer = { inside: false, dragging: false, moved: 0, downX: 0, downY: 0, ndcX: 0, ndcY: 0, clientX: 0, clientY: 0, clickCandidate: null };
  bindPointerEvents(renderer.domElement);

  resizeObserver = new ResizeObserver(handleResize);
  resizeObserver.observe(host);
  document.addEventListener('visibilitychange', onVisibilityChange);

  if (import.meta.env.DEV) attachDebugHook();

  startLoop();
}

function buildEndpoints(list) {
  const merged = new Map();
  for (const a of list) {
    const key = `${a.endLat.toFixed(3)}:${a.endLng.toFixed(3)}:${a.type}`;
    if (!merged.has(key)) merged.set(key, { lat: a.endLat, lng: a.endLng, type: a.type, pseudo: a.pseudo });
  }
  return [...merged.values()];
}

// ── hover / 点击 ──────────────────────────────────
function occludedByGlobe(camPos, point) {
  const dir = point.clone().sub(camPos);
  const len = dir.length();
  dir.normalize();
  const b = camPos.dot(dir);
  const c = camPos.dot(camPos) - GLOBE_RADIUS * GLOBE_RADIUS;
  const disc = b * b - c;
  if (disc <= 0) return false;
  const tHit = -b - Math.sqrt(disc);
  return tHit > 0 && tHit < len - 1;
}

function pickArc() {
  if (!pointer?.inside || pointer.dragging || !pickCurves.length || !raycaster || !camera) return null;
  raycaster.setFromCamera({ x: pointer.ndcX, y: pointer.ndcY }, camera);
  const camPos = camera.position;
  const worldPerPx = (2 * camPos.length() * Math.tan((camera.fov * RAD) / 2)) / (renderer.domElement.clientHeight || 1);
  const tol = Math.max(worldPerPx * 9, 2.1);
  let best = null;
  let bestD = Infinity;
  let bestPt = null;
  for (const item of pickCurves) {
    for (const p of item.points) {
      const dist = raycaster.ray.distanceToPoint(p);
      if (dist < bestD) {
        bestD = dist;
        best = item;
        bestPt = p;
      }
    }
  }
  if (!best || bestD > tol) return null;
  if (occludedByGlobe(camPos, bestPt)) return null;
  return best;
}

function applyHover(item) {
  clearHover();
  hoverInfo = item;
  const group = item.data.__threeObjArc;
  if (group) {
    const child = group.children[0];
    const uniforms = child?.material?.uniforms;
    if (uniforms?.dashSize && uniforms?.gapSize) {
      hoverInfo.savedDashSize = uniforms.dashSize.value;
      hoverInfo.savedGapSize = uniforms.gapSize.value;
      hoverInfo.uniforms = uniforms;
      uniforms.dashSize.value = 1; // hover：实线高亮 + 叠加光效
      uniforms.gapSize.value = 0;
    }
    if (child?.geometry && THREE) {
      if (!hoverMaterial) {
        hoverMaterial = new THREE.MeshBasicMaterial({
          color: 0xd9f2ff, transparent: true, opacity: 0.35,
          blending: THREE.AdditiveBlending, depthWrite: false,
        });
        disposables.push(hoverMaterial);
      }
      hoverOverlay = new THREE.Mesh(child.geometry, hoverMaterial);
      group.add(hoverOverlay);
    }
  }
  tip.arc = item.data;
  tip.visible = true;
  updateTipPosition();
}

function clearHover() {
  if (hoverInfo?.uniforms && hoverInfo.uniforms.dashSize) {
    hoverInfo.uniforms.dashSize.value = hoverInfo.savedDashSize;
    hoverInfo.uniforms.gapSize.value = hoverInfo.savedGapSize;
  }
  if (hoverOverlay?.parent) hoverOverlay.parent.remove(hoverOverlay);
  hoverOverlay = null;
  hoverInfo = null;
  tip.visible = false;
  tip.arc = null;
}

function updateTipPosition() {
  const host = stageRef.value;
  if (!host || !pointer) return;
  const rect = host.getBoundingClientRect();
  let x = pointer.clientX - rect.left + 14;
  let y = pointer.clientY - rect.top + 14;
  if (x > rect.width - 240) x -= 268;
  if (y > rect.height - 170) y -= 200;
  tip.x = Math.max(6, x);
  tip.y = Math.max(6, y);
}

function updateHover() {
  if (!renderer) return;
  const hit = pickArc();
  if (hit && hoverInfo !== hit) applyHover(hit);
  else if (!hit && hoverInfo) clearHover();
  else if (hit) updateTipPosition();
  renderer.domElement.style.cursor = hit ? 'pointer' : '';
}

function onPointerMove(e) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.ndcX = ((e.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.ndcY = -((e.clientY - rect.top) / rect.height) * 2 + 1;
  pointer.clientX = e.clientX;
  pointer.clientY = e.clientY;
  pointer.inside = true;
  if (!pointer.dragging) updateHover();
}

function onPointerLeave() {
  pointer.inside = false;
  clearHover();
}

function onPointerDown(e) {
  pointer.downX = e.clientX;
  pointer.downY = e.clientY;
}

function onPointerUp(e) {
  const moved = Math.hypot(e.clientX - pointer.downX, e.clientY - pointer.downY);
  if (moved < 6 && pointer.clickCandidate) {
    router.push('/admin/forensics'); // 点击弧线 → 取证与交付审计页
  }
  pointer.clickCandidate = null;
}

function onControlStart() {
  if (!pointer) return;
  pointer.dragging = true;
  pointer.clickCandidate = hoverInfo;
  clearHover();
}

function onControlEnd() {
  if (!pointer) return;
  pointer.dragging = false;
}

let pointerEventsBound = false;
function bindPointerEvents(el) {
  el.addEventListener('pointermove', onPointerMove);
  el.addEventListener('pointerleave', onPointerLeave);
  el.addEventListener('pointerdown', onPointerDown);
  el.addEventListener('pointerup', onPointerUp);
  pointerEventsBound = true;
}

function unbindPointerEvents(el) {
  if (!pointerEventsBound || !el) return;
  el.removeEventListener('pointermove', onPointerMove);
  el.removeEventListener('pointerleave', onPointerLeave);
  el.removeEventListener('pointerdown', onPointerDown);
  el.removeEventListener('pointerup', onPointerUp);
  pointerEventsBound = false;
}

// ── 渲染循环 / 生命周期控制 ─────────────────────
function startLoop() {
  if (running || disposed || !renderer) return;
  running = true;
  let frame = 0;
  const tick = () => {
    if (!running || disposed) return;
    rafId = requestAnimationFrame(tick);
    controls.update();
    frame++;
    if (frame % 4 === 0 && pointer?.inside && !pointer.dragging) updateHover();
    if (hoverOverlay && hoverInfo?.data?.__threeObjArc?.children[0]?.geometry &&
        hoverOverlay.geometry !== hoverInfo.data.__threeObjArc.children[0].geometry) {
      hoverOverlay.geometry = hoverInfo.data.__threeObjArc.children[0].geometry;
    }
    renderer.render(scene, camera);
  };
  tick();
}

function stopLoop() {
  running = false;
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
}

function pause() {
  stopLoop();
  if (globe && typeof globe.pauseAnimation === 'function') globe.pauseAnimation();
}

function resume() {
  if (disposed || document.hidden || !active) return;
  if (globe && typeof globe.resumeAnimation === 'function') globe.resumeAnimation();
  startLoop();
}

function onVisibilityChange() {
  if (document.hidden) pause();
  else resume();
}

function handleResize() {
  if (!renderer || !stageRef.value || !camera) return;
  const w = stageRef.value.clientWidth;
  const h = stageRef.value.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

// DEV 专用：给自动化测试提供探针（生产构建会被 tree-shake）
function attachDebugHook() {
  window.__dfgDebug = {
    arcCount: () => pickCurves.length,
    matchCity: (addr) => matchCity(addr),
    pseudo: (seed) => pseudoCoords(seed),
    arcScreen: (i) => {
      const item = pickCurves[i];
      if (!item || !renderer || !camera) return null;
      camera.updateMatrixWorld();
      const rect = renderer.domElement.getBoundingClientRect();
      for (const u of [0.5, 0.42, 0.58, 0.35, 0.65]) {
        const p = item.curve.getPoint(u);
        if (occludedByGlobe(camera.position, p)) continue;
        const proj = p.clone().project(camera);
        return { x: rect.left + ((proj.x + 1) / 2) * rect.width, y: rect.top + ((1 - proj.y) / 2) * rect.height };
      }
      return null;
    },
  };
}

// ── 切换语言：原点标签实时更新（其余文案由模板响应式处理） ──
watch(locale, () => {
  if (globe) {
    globe.labelsData([{ lat: ORIGIN.lat, lng: ORIGIN.lng, text: t('dataFlow.originLabel') }]);
  }
});

onMounted(loadData);

onActivated(() => {
  active = true;
  resume();
});

onDeactivated(() => {
  active = false;
  pause();
});

onBeforeUnmount(() => {
  disposed = true;
  stopLoop();
  document.removeEventListener('visibilitychange', onVisibilityChange);
  if (resizeObserver) resizeObserver.disconnect();
  if (renderer) unbindPointerEvents(renderer.domElement);
  if (controls) {
    controls.removeEventListener('start', onControlStart);
    controls.removeEventListener('end', onControlEnd);
    controls.dispose();
  }
  if (globe) {
    if (typeof globe.pauseAnimation === 'function') globe.pauseAnimation();
    if (typeof globe._destructor === 'function') globe._destructor(); // 停止库内部 ticker 与补间
    if (scene) scene.remove(globe);
  }
  for (const d of disposables) {
    if (d && typeof d.dispose === 'function') d.dispose();
  }
  disposables.length = 0;
  if (glowTexture) glowTexture.dispose();
  glowTexture = null;
  if (hoverMaterial) hoverMaterial.dispose();
  hoverMaterial = null;
  if (renderer) {
    renderer.dispose();
    if (typeof renderer.forceContextLoss === 'function') renderer.forceContextLoss();
    renderer.domElement.remove(); // 移除 canvas，释放 DOM
  }
  renderer = null;
  scene = null;
  camera = null;
  globe = null;
  pickCurves = [];
  if (import.meta.env.DEV && typeof window !== 'undefined' && window.__dfgDebug) {
    delete window.__dfgDebug;
  }
});
</script>

<style scoped>
.dfg-card {
  margin-bottom: 20px;
  border-radius: 14px;
  padding: 18px 22px 14px;
  color: #e8f1fb;
  background:
    radial-gradient(120% 160% at 85% -20%, rgba(56, 122, 216, 0.30), transparent 55%),
    radial-gradient(90% 120% at 8% 110%, rgba(35, 198, 214, 0.16), transparent 60%),
    linear-gradient(135deg, #0a1424 0%, #0e1c33 48%, #0a1626 100%);
  border: 1px solid rgba(120, 170, 255, 0.16);
  box-shadow: 0 12px 32px -12px rgba(6, 18, 40, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.dfg-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}
.dfg-title {
  margin: 0;
  font-size: 18px;
  letter-spacing: 0.5px;
  color: #f2f7ff;
}
.dfg-subtitle {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: rgba(190, 210, 235, 0.75);
}
.dfg-legend {
  display: flex;
  gap: 14px;
  align-items: center;
  padding-top: 4px;
}
.dfg-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: rgba(200, 218, 240, 0.85);
}
.dfg-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot-origin { background: #ffd166; box-shadow: 0 0 8px rgba(255, 209, 102, 0.9); }
.dot-vector { background: #4fc3f7; }
.dot-raster { background: #F59E0B; }

.dfg-stage { position: relative; }
.dfg-state {
  height: 340px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: rgba(190, 210, 235, 0.7);
}
.dfg-canvas-host {
  position: relative;
  height: 340px;
  overflow: hidden;
  border-radius: 10px;
}
.dfg-canvas-host :deep(canvas) {
  display: block;
}
.dfg-tip {
  position: absolute;
  z-index: 3;
  min-width: 190px;
  max-width: 250px;
  padding: 10px 12px;
  border-radius: 10px;
  background: rgba(10, 22, 40, 0.92);
  border: 1px solid rgba(120, 170, 255, 0.25);
  box-shadow: 0 10px 24px -8px rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(6px);
  pointer-events: none;
}
.dfg-tip-head {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #cfe3ff;
  margin-bottom: 6px;
}
.dfg-tip-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  line-height: 20px;
  color: rgba(190, 210, 235, 0.75);
}
.dfg-tip-row b {
  color: #eaf3ff;
  font-weight: 600;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dfg-footnote {
  margin: 8px 0 0;
  font-size: 12px;
  color: rgba(170, 192, 220, 0.6);
}
.dfg-spin { animation: dfg-rotate 1s linear infinite; }
@keyframes dfg-rotate {
  to { transform: rotate(360deg); }
}
@media (max-width: 1200px) {
  .dfg-state,
  .dfg-canvas-host { height: 300px; }
}
</style>
