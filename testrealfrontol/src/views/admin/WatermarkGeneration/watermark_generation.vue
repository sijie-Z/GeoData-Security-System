<template>
  <div class="watermark-generation-page">
    <div class="page-header">
      <h1 class="page-title">
        {{ $t('wmGen.pageTitle') }}
      </h1>
      <p class="page-desc">
        {{ $t('wmGen.pageDesc') }}
      </p>
    </div>

    <el-card
      class="table-card"
      shadow="hover"
    >
      <el-table
        v-loading="loading"
        :data="data.list"
        border
        stripe
        :empty-text="$t('wmGen.emptyText')"
      >
        <el-table-column
          prop="id"
          :label="$t('wmGen.colApplicationId')"
          width="90"
        />
        <el-table-column
          prop="data_alias"
          :label="$t('wmGen.colDataName')"
          min-width="140"
        />
        <el-table-column
          prop="data_id"
          :label="$t('wmGen.colDataId')"
          width="120"
        />
        <el-table-column
          prop="applicant_user_number"
          :label="$t('wmGen.colApplicantNo')"
          width="120"
        />
        <el-table-column
          prop="applicant_name"
          :label="$t('wmGen.colApplicantName')"
          width="120"
        />
        <el-table-column
          :label="$t('wmGen.colFirstStatus')"
          width="100"
          align="center"
        >
          <template #default="scope">
            {{ getStatusText(scope.row.first_statu) }}
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('wmGen.colSecondStatus')"
          width="100"
          align="center"
        >
          <template #default="scope">
            {{ getStatusText(scope.row.second_statu) }}
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('wmGen.colWatermark')"
          width="100"
          align="center"
        >
          <template #default="scope">
            <WatermarkImage
              v-if="scope.row.qrcode"
              :src="`data:image/png;base64,${scope.row.qrcode}`"
              :alt="$t('wmGen.colWatermark')"
              fit="cover"
              style="width: 72px; height: 72px; border-radius: 6px;"
            />
            <span
              v-else
              style="color:var(--text-tertiary, #909399);"
            >{{ $t('wmGen.notGenerated') }}</span>
          </template>
        </el-table-column>
        <el-table-column
          :label="$t('wmGen.colAction')"
          width="240"
          align="center"
          fixed="right"
        >
          <template #default="scope">
            <el-button
              size="small"
              @click="openMapDialog(scope.row)"
            >
              {{ $t('wmGen.mapPreview') }}
            </el-button>
            <el-button
              size="small"
              type="primary"
              @click="openRequestDialog(scope.row)"
            >
              {{ $t('wmGen.generateWatermark') }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="prev, pager, next, jumper, total"
        @current-change="pageChanged"
      />
    </div>

    <el-dialog
      v-model="requestDataVisible"
      width="680px"
      :close-on-click-modal="false"
      :title="$t('wmGen.generateWatermark')"
    >
      <el-form
        ref="requestFormRef"
        :model="requestInformation"
        :rules="rules"
        label-width="110px"
        class="gen-form"
      >
        <el-divider content-position="left">
          {{ $t('wmGen.sectionBasic') }}
        </el-divider>
        <div class="form-row">
          <el-form-item
            :label="$t('wmGen.formApplicationId')"
            prop="application_id"
            class="form-half"
          >
            <el-input
              v-model="requestInformation.application_id"
              readonly
            />
          </el-form-item>
          <el-form-item
            :label="$t('wmGen.formDataId')"
            prop="data_id"
            class="form-half"
          >
            <el-input
              v-model="requestInformation.data_id"
              readonly
            />
          </el-form-item>
        </div>
        <el-form-item
          :label="$t('wmGen.formDataName')"
          prop="data_alias"
        >
          <el-input
            v-model="requestInformation.data_alias"
            readonly
          />
        </el-form-item>

        <el-divider content-position="left">
          {{ $t('wmGen.sectionApplicant') }}
        </el-divider>
        <div class="form-row">
          <el-form-item
            :label="$t('wmGen.formApplicantName')"
            prop="applicant_name"
            class="form-half"
          >
            <el-input
              v-model="requestInformation.applicant_name"
              readonly
            />
          </el-form-item>
          <el-form-item
            :label="$t('wmGen.formApplicantNo')"
            prop="applicant_user_number"
            class="form-half"
          >
            <el-input
              v-model="requestInformation.applicant_user_number"
              readonly
            />
          </el-form-item>
        </div>

        <el-divider content-position="left">
          {{ $t('wmGen.sectionReviewers') }}
        </el-divider>
        <div class="form-row">
          <el-form-item
            :label="$t('wmGen.formAdm1')"
            class="form-half"
          >
            <el-input
              :model-value="requestInformation.adm1_name || '—'"
              readonly
            />
          </el-form-item>
          <el-form-item
            :label="$t('wmGen.formAdm2')"
            class="form-half"
          >
            <el-input
              :model-value="requestInformation.adm2_name || '—'"
              readonly
            />
          </el-form-item>
        </div>
        <el-form-item :label="$t('wmGen.formGenTime')">
          <el-input
            :model-value="requestInformation.generation_time || '—'"
            readonly
          />
        </el-form-item>

        <el-divider content-position="left">
          {{ $t('wmGen.sectionOptional') }}
        </el-divider>
        <el-form-item
          :label="$t('wmGen.formReason')"
          prop="reason"
        >
          <el-input
            v-model="requestInformation.reason"
            type="textarea"
            :rows="2"
            :placeholder="$t('wmGen.reasonPlaceholder')"
          />
        </el-form-item>
        <el-form-item
          :label="$t('wmGen.formPurpose')"
          prop="purpose"
        >
          <el-input
            v-model="requestInformation.purpose"
            type="textarea"
            :rows="2"
            :placeholder="$t('wmGen.purposePlaceholder')"
          />
        </el-form-item>
        <div class="form-row">
          <el-form-item
            :label="$t('wmGen.formUsageScope')"
            prop="usage_scope"
            class="form-half"
          >
            <el-input
              v-model="requestInformation.usage_scope"
              :placeholder="$t('wmGen.scopePlaceholder')"
            />
          </el-form-item>
          <el-form-item
            :label="$t('wmGen.formSecurityLevel')"
            prop="security_level"
            class="form-half"
          >
            <el-select
              v-model="requestInformation.security_level"
              style="width:100%;"
              :placeholder="$t('wmGen.selectPlaceholder')"
            >
              <el-option
                :label="$t('wmGen.levelNormal')"
                value="normal"
              />
              <el-option
                :label="$t('wmGen.levelInternal')"
                value="internal"
              />
              <el-option
                :label="$t('wmGen.levelSensitive')"
                value="sensitive"
              />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item
          :label="$t('wmGen.formCustomTag')"
          prop="custom_tag"
        >
          <el-input
            v-model="requestInformation.custom_tag"
            :placeholder="$t('wmGen.tagPlaceholder')"
          />
        </el-form-item>

        <el-divider content-position="left">
          {{ $t('wmGen.sectionQrPreview') }}
        </el-divider>
        <el-form-item>
          <div class="qr-preview-area">
            <WatermarkImage
              v-if="generatedQrcode"
              :src="`data:image/png;base64,${generatedQrcode}`"
              :alt="$t('wmGen.sectionQrPreview')"
              fit="contain"
              style="width: 140px; height: 140px; border: 1px solid var(--border-color, #e5e7eb); border-radius: 8px;"
            />
            <span
              v-else
              style="color:var(--text-tertiary, #909399);"
            >{{ $t('wmGen.qrPreviewAfter') }}</span>
            <div
              v-if="generatedQrcode"
              class="qr-meta"
            >
              <p v-if="generatedQrVersion">
                {{ $t('wmGen.version') }} V{{ generatedQrVersion }}
              </p>
              <p v-if="generatedSignature">
                {{ $t('wmGen.signature') }} {{ generatedSignature }}
              </p>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="requestDataVisible=false">
          {{ $t('wmGen.cancel') }}
        </el-button>
        <el-button
          type="primary"
          @click="generate"
        >
          {{ $t('wmGen.confirmGenerate') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="mapDialogVisible"
      :title="$t('wmGen.mapDialogTitle')"
      width="74%"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="destroyMapView"
    >
      <div class="map-toolbar">
        <el-input
          v-model="mapSearchKeyword"
          clearable
          :placeholder="$t('wmGen.mapSearchPlaceholder')"
          style="width: 320px"
          @keyup.enter="searchMap"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button
          type="primary"
          @click="searchMap"
        >
          {{ $t('wmGen.searchLocation') }}
        </el-button>
        <el-button @click="goInitialExtent">
          {{ $t('wmGen.resetView') }}
        </el-button>
        <el-button @click="clearSearchResult">
          {{ $t('wmGen.clearLocation') }}
        </el-button>
      </div>
      <div class="map-dialog-layout">
        <div class="map-pane">
          <div
            ref="mapContainer"
            class="map-container"
          />
          <div
            v-if="mapLoading"
            class="map-loading-overlay"
          >
            <el-icon
              class="is-loading"
              :size="32"
            >
              <Loading />
            </el-icon>
            <span style="margin-top: 8px; color: var(--text-secondary, #6b7280); font-size: 14px;">{{ $t('wmGen.mapLoadingText') }}</span>
          </div>
          <div
            v-if="!selectedMapRow.data_url"
            class="map-placeholder"
          >
            <el-empty :description="$t('wmGen.mapEmptyDesc')" />
          </div>
        </div>
        <div class="info-pane">
          <el-descriptions
            :column="1"
            border
            size="small"
          >
            <el-descriptions-item :label="$t('wmGen.descApplicationId')">
              {{ selectedMapRow.id }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('wmGen.descDataName')">
              {{ selectedMapRow.data_alias }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('wmGen.descDataId')">
              {{ selectedMapRow.data_id }}
            </el-descriptions-item>
            <el-descriptions-item :label="$t('wmGen.descApplicant')">
              {{ selectedMapRow.applicant_name }} ({{ selectedMapRow.applicant_user_number }})
            </el-descriptions-item>
            <el-descriptions-item :label="$t('wmGen.descMapServiceUrl')">
              <span
                class="url-text"
                :title="selectedMapRow.data_url"
              >{{ selectedMapRow.data_url || '—' }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage, ElDivider } from 'element-plus';
import { getApplicationsGenerateWatermark, generateWatermark } from '@/api/watermark';
import { Search, Loading } from '@element-plus/icons-vue';
import WatermarkImage from '@/components/common/WatermarkImage.vue';

// 天地图 key 从本地 .env（VITE_TIANDITU_KEY）读取；未配置时不创建天地图图层，底图降级为 OSM
const tiandituKey = import.meta.env.VITE_TIANDITU_KEY || '';

const { t } = useI18n();

const data = reactive({ list: [] });
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const loading = ref(false);

const requestDataVisible = ref(false);
const requestFormRef = ref(null);
const generatedQrcode = ref('');
const generatedQrVersion = ref(null);
const generatedSignature = ref('');

const requestInformation = reactive({
  application_id: '',
  data_id: '',
  data_url: '',
  data_alias: '',
  applicant_name: '',
  applicant_user_number: '',
  adm1_name: '',
  adm2_name: '',
  generation_time: '',
  reason: '',
  purpose: '',
  usage_scope: '',
  security_level: 'internal',
  custom_tag: ''
});

const rules = {
  application_id: [{ required: true, message: t('wmGen.missingApplicationId'), trigger: 'blur' }],
  data_id: [{ required: true, message: t('wmGen.missingDataId'), trigger: 'blur' }],
  data_alias: [{ required: true, message: t('wmGen.missingDataName'), trigger: 'blur' }],
  applicant_name: [{ required: true, message: t('wmGen.missingApplicantName'), trigger: 'blur' }]
};

const pageChanged = (newPage) => {
  page.value = newPage;
};

watch(page, (n, o) => {
  if (n !== o) get_applications();
});

watch(pageSize, () => {
  page.value = 1;
  get_applications();
});

const getStatusText = (status) => {
  if (status === true) return t('wmGen.statusPassed');
  if (status === false) return t('wmGen.statusRejected');
  return t('wmGen.statusPending');
};

const get_applications = async () => {
  loading.value = true;
  try {
    const response = await getApplicationsGenerateWatermark({ page: page.value, pageSize: pageSize.value });
    if (!response.data?.status) {
      data.list = [];
      total.value = 0;
      ElMessage.error(response.data?.msg || t('wmGen.fetchFailed'));
      return;
    }
    data.list = response.data.application_data || [];
    total.value = response.data.pages?.total ?? 0;
  } catch (_err) {
    ElMessage.error(t('wmGen.fetchFailed'));
  } finally {
    loading.value = false;
  }
};

const openRequestDialog = async (row) => {
  Object.assign(requestInformation, {
    application_id: row.id,
    data_id: row.data_id,
    data_url: row.data_url || '',
    data_alias: row.data_alias,
    applicant_name: row.applicant_name,
    applicant_user_number: row.applicant_user_number,
    adm1_name: row.adm1_name,
    adm2_name: row.adm2_name,
    generation_time: row.generation_timestamp || '',
    reason: row.reason || '',
    purpose: row.purpose || '',
    usage_scope: row.usage_scope || '',
    security_level: row.security_level || 'internal',
    custom_tag: row.custom_tag || ''
  });
  generatedQrcode.value = row.qrcode || '';
  generatedQrVersion.value = row.qr_version || null;
  generatedSignature.value = row.qr_signature || '';
  requestDataVisible.value = true;
  await nextTick();
  requestFormRef.value?.clearValidate();
};

const generate = async () => {
  await requestFormRef.value?.validate();
  const resp = await generateWatermark(requestInformation);
  if (!resp.data?.status) {
    ElMessage.error(resp.data?.msg || t('wmGen.generateFailed'));
    return;
  }
  generatedQrcode.value = resp.data?.qrcode || '';
  generatedQrVersion.value = resp.data?.qr_version || null;
  generatedSignature.value = resp.data?.signature || '';
  ElMessage.success(t('wmGen.generateSuccess', { version: generatedQrVersion.value }));
  requestDataVisible.value = false;
  await get_applications();
};

const mapDialogVisible = ref(false);
const mapContainer = ref(null);
const mapSearchKeyword = ref('');
const mapLoading = ref(false);
const selectedMapRow = reactive({
  id: '',
  data_alias: '',
  data_id: '',
  applicant_name: '',
  applicant_user_number: '',
  data_url: ''
});
let olMap = null;         // OpenLayers Map instance
let markerSource = null;  // ol/source/Vector for search markers
let initialView = null;   // { center, zoom } to reset to
let mapInitSeq = 0;       // sequence counter to cancel stale init calls

const destroyMapView = () => {
  mapInitSeq++; // invalidate any in-flight initializeMap
  if (olMap) {
    try { olMap.setTarget(null) } catch (_) { /* best-effort teardown */ }
    try { olMap.dispose() } catch (_) { /* best-effort teardown */ }
    olMap = null;
  }
  markerSource = null;
  initialView = null;
};

onBeforeUnmount(() => {
  destroyMapView();
});

/**
 * Try to extract GeoServer workspace:layer from a data_url.
 * Typical URL: http://host/geoserver/workspace/wms  →  workspace
 * We try GetCapabilities to find a matching layer, then load it as WMS.
 */
const tryLoadWmsLayer = async (map, dataUrl) => {
  try {
    // Parse workspace from URL like http://host/geoserver/workspace/wms
    const urlObj = new URL(dataUrl);
    const pathParts = urlObj.pathname.split('/').filter(Boolean);
    // Find 'geoserver' in path, workspace is the segment after it
    const gsIdx = pathParts.findIndex(p => p.toLowerCase() === 'geoserver');
    if (gsIdx < 0 || gsIdx + 1 >= pathParts.length) return false;

    const workspace = pathParts[gsIdx + 1];
    const wmsBaseUrl = `${urlObj.protocol}//${urlObj.host}${urlObj.pathname.replace(/\/$/, '')}`;
    // Ensure we're hitting the WMS endpoint
    const wmsUrl = wmsBaseUrl.endsWith('/wms') ? wmsBaseUrl : `${wmsBaseUrl}/wms`;

    const { TileWMS } = await import('ol/source');
    const { default: TileLayer } = await import('ol/layer/Tile');

    // Fetch GetCapabilities to find layers in this workspace
    const resp = await fetch(`${wmsUrl}?service=WMS&version=1.3.0&request=GetCapabilities`);
    const xmlText = await resp.text();
    const xmlDoc = new DOMParser().parseFromString(xmlText, 'text/xml');
    const layerNodes = xmlDoc.querySelectorAll('Layer > Name');

    // Find first layer that starts with our workspace
    const prefix = `${workspace}:`;
    const targetNode = Array.from(layerNodes).find(n => n.textContent.startsWith(prefix));
    if (!targetNode) return false;

    const fullLayerName = targetNode.textContent;
    const wmsLayer = new TileLayer({
      source: new TileWMS({
        url: wmsUrl,
        params: { LAYERS: fullLayerName, TILED: true },
        serverType: 'geoserver'
      }),
      zIndex: 2
    });

    wmsLayer.getSource().once('tileloadend', () => { mapLoading.value = false; });
    wmsLayer.getSource().once('tileloaderror', () => { mapLoading.value = false; });
    map.addLayer(wmsLayer);

    // Auto-fit to layer extent from GetCapabilities
    const layerNameToMatch = fullLayerName.includes(':') ? fullLayerName.split(':')[1] : fullLayerName;
    const targetParent = Array.from(layerNodes).find(n => n.textContent === layerNameToMatch)?.parentNode;
    if (targetParent) {
      const bboxNode = targetParent.querySelector('BoundingBox[CRS="CRS:84"]');
      if (bboxNode) {
        const bbox = [
          parseFloat(bboxNode.getAttribute('minx')),
          parseFloat(bboxNode.getAttribute('miny')),
          parseFloat(bboxNode.getAttribute('maxx')),
          parseFloat(bboxNode.getAttribute('maxy'))
        ];
        if (bbox.every(v => !isNaN(v))) {
          map.getView().fit(bbox, { size: map.getSize(), duration: 800, padding: [50, 50, 50, 50] });
          initialView = {
            center: map.getView().getCenter(),
            zoom: map.getView().getZoom()
          };
        }
      }
    }
    return true;
  } catch {
    return false;
  }
};

const initializeMap = async (dataUrl) => {
  destroyMapView();
  if (!mapContainer.value) return;
  mapLoading.value = true;
  const seq = ++mapInitSeq; // capture current sequence

  try {
    // Lazy-load OpenLayers (same pattern as data_viewing_new.vue)
    const [{ default: Map }, { default: OlView }, { default: TileLayer }, olSource, olControl] =
      await Promise.all([
        import('ol/Map'),
        import('ol/View'),
        import('ol/layer/Tile'),
        import('ol/source'),
        import('ol/control')
      ]);
    await import('ol/ol.css');
    if (mapInitSeq !== seq) return; // stale, abandon

    const { XYZ, OSM, Vector: VectorSource } = olSource;
    const { ScaleLine, defaults: defaultControls } = olControl;
    const { default: VectorLayer } = await import('ol/layer/Vector');
    const { Style, Fill, Stroke, Circle: CircleStyle } = await import('ol/style');

    // Base layers: Tianditu only when a key is configured; without a key OSM is
    // the base map and no Tianditu tile requests are ever made.
    // #24 深色适配（方案 A）：仅底图瓦片层挂 dark-tile-layer class，由全局
    // design-system.css 在 html.dark 下施加 invert+hue-rotate filter；零外部依赖。
    // 标记/矢量要素/控件/比例尺/WMS 数据图层均不含该 class，天然不受影响。
    // 注：底图与注记层再各挂互异后缀 class —— OL canvas 渲染器会复用 className
    //     完全相同的容器（useContainer），互异可避免底图/注记层共用同一 canvas。
    const DARK_TILE_CLASS = 'ol-layer dark-tile-layer dark-tile-base';
    const osmFallback = new TileLayer({
      source: new OSM(),
      className: DARK_TILE_CLASS, // #24
      zIndex: 0,
      visible: !tiandituKey
    });

    let tiandituBase = null;
    let tiandituLabel = null;
    if (tiandituKey) {
      tiandituBase = new TileLayer({
        source: new XYZ({
          url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=vec_w&x={x}&y={y}&l={z}&tk=${tiandituKey}`
        }),
        className: DARK_TILE_CLASS, // #24 底图 vec_w
        zIndex: 0
      });
      tiandituLabel = new TileLayer({
        source: new XYZ({
          url: `https://t{0-7}.tianditu.gov.cn/DataServer?T=cva_w&x={x}&y={y}&l={z}&tk=${tiandituKey}`
        }),
        className: 'ol-layer dark-tile-layer dark-tile-label', // #24 注记 cva_w（与底图同滤；独立 class 防 OL 容器复用）
        zIndex: 1
      });

      // #38 天地图故障降级：OL 瓦片源派发 tileloaderror（逐瓦片多次触发），
      //     用 once 保证仅生效一次；原先监听的 'error' 事件并不存在。
      tiandituBase.getSource().once('tileloaderror', () => {
        tiandituBase.setVisible(false);
        tiandituLabel.setVisible(false);
        osmFallback.setVisible(true);
      });
    }

    // Marker layer for search results
    markerSource = new VectorSource();
    const markerLayer = new VectorLayer({
      source: markerSource,
      zIndex: 10,
      style: new Style({
        image: new CircleStyle({
          radius: 7,
          fill: new Fill({ color: '#ef4444' }),
          stroke: new Stroke({ color: '#ffffff', width: 2 })
        })
      })
    });

    const map = new Map({
      target: mapContainer.value,
      layers: [osmFallback, tiandituBase, tiandituLabel, markerLayer].filter(Boolean),
      view: new OlView({
        projection: 'EPSG:4326',
        center: [104.0, 35.0],
        zoom: 4
      }),
      controls: defaultControls().extend([
        new ScaleLine({ units: 'metric' })
      ])
    });

    olMap = map;
    initialView = { center: [104.0, 35.0], zoom: 4 };

    // Try to load WMS data layer if dataUrl is available
    if (dataUrl) {
      const loaded = await tryLoadWmsLayer(map, dataUrl);
      // Guard: a newer init has started, abandon this one
      if (mapInitSeq !== seq) return;
      if (!loaded) {
        mapLoading.value = false;
      }
    } else {
      mapLoading.value = false;
    }
  } catch (error) {
    if (mapInitSeq !== seq) return; // stale, ignore
    console.error('地图加载失败:', error);
    mapLoading.value = false;
    ElMessage.error(t('wmGen.mapLoadFailed'));
  }
};

const openMapDialog = async (row) => {
  selectedMapRow.id = row.id || '';
  selectedMapRow.data_alias = row.data_alias || '';
  selectedMapRow.data_id = row.data_id || '';
  selectedMapRow.applicant_name = row.applicant_name || '';
  selectedMapRow.applicant_user_number = row.applicant_user_number || '';
  selectedMapRow.data_url = row.data_url || '';
  mapSearchKeyword.value = '';
  mapDialogVisible.value = true;
  await nextTick();
  await initializeMap(row.data_url);
};

/**
 * Geocode location — tries TianDiTu first, falls back to Nominatim (OSM).
 * The old code used the broken backend /api/geocoding/search which returns
 * DB records without coordinates — always landing at 0,0 (Null Island).
 */
const searchMap = async () => {
  const keyword = mapSearchKeyword.value.trim();
  if (!keyword) {
    ElMessage.warning(t('wmGen.enterKeyword'));
    return;
  }
  if (!olMap) {
    ElMessage.warning(t('wmGen.mapNotLoaded'));
    return;
  }

  let lon = null, lat = null, displayName = keyword;

  if (tiandituKey) {
    try {
      // --- Try TianDiTu geocoding first ---
      const params = new URLSearchParams({
        postStr: JSON.stringify({ keyword }),
        type: 'query',
        tk: tiandituKey,
      });
      const geoResp = await fetch(`https://api.tianditu.gov.cn/v2/search?${params}`);
      if (geoResp.ok) {
        const geoData = await geoResp.json();
        const pois = geoData.pois || [];
        if (pois.length > 0 && pois[0].lonlat) {
          const coords = String(pois[0].lonlat).split(',').map(Number);
          if (!Number.isNaN(coords[0]) && !Number.isNaN(coords[1])
              && coords[0] >= -180 && coords[0] <= 180
              && coords[1] >= -90 && coords[1] <= 90) {
            [lon, lat] = coords;
            displayName = pois[0].name || keyword;
          }
        }
      }
    } catch {
      // TianDiTu failed — will try fallback below
    }
  }

  // --- Fallback: Nominatim (OpenStreetMap, no key needed) ---
  if (lon === null) {
    try {
      const nomUrl = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(keyword)}&limit=1`;
      const nomResp = await fetch(nomUrl, {
        headers: { 'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.5' }
      });
      if (nomResp.ok) {
        const nomData = await nomResp.json();
        if (nomData.length > 0) {
          lon = parseFloat(nomData[0].lon);
          lat = parseFloat(nomData[0].lat);
          displayName = nomData[0].display_name?.split(',')[0] || keyword;
        }
      }
    } catch {
      // Both services failed
    }
  }

  if (lon === null || lat === null) {
    ElMessage.warning(t('wmGen.noResults'));
    return;
  }

  try {
    markerSource.clear();
    const { default: Feature } = await import('ol/Feature');
    const { default: Point } = await import('ol/geom/Point');
    markerSource.addFeature(new Feature({ geometry: new Point([lon, lat]) }));
    olMap.getView().animate({ center: [lon, lat], zoom: 13, duration: 1000 });
    ElMessage.success(t('wmGen.locationSuccess', { name: displayName }));
  } catch (err) {
    console.error('地图标记失败:', err);
    ElMessage.error(t('wmGen.searchFailed'));
  }
};

const goInitialExtent = () => {
  if (!olMap || !initialView) {
    ElMessage.warning(t('wmGen.noViewToReset'));
    return;
  }
  olMap.getView().animate({
    center: initialView.center,
    zoom: initialView.zoom,
    duration: 800
  });
};

const clearSearchResult = () => {
  markerSource?.clear();
};

onMounted(() => {
  get_applications();
});
</script>

<style scoped>
.watermark-generation-page { padding: 20px 24px; }
.page-header { margin-bottom: 16px; }
.page-title { margin: 0 0 8px; font-size: 22px; color: var(--text-primary, #1f2937); }
.page-desc { margin: 0; color: var(--text-secondary, #6b7280); }
.table-card { border-radius: 12px; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }

/* Form layout */
.gen-form :deep(.el-divider) { margin: 16px 0 12px; }
.gen-form :deep(.el-divider__text) { font-size: 13px; font-weight: 600; color: var(--text-secondary, #475569); }
.form-row { display: flex; gap: 16px; }
.form-half { flex: 1; }

/* Map dialog */
.map-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.map-dialog-layout { display: flex; gap: 16px; }
.map-pane { flex: 3; position: relative; height: 500px; border-radius: 10px; overflow: hidden; background: var(--bg-tertiary, #f1f5f9); }
.map-container { width: 100%; height: 100%; }
.map-placeholder { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; background: var(--bg-secondary, #f8fafc); }
.map-loading-overlay {
  position: absolute; inset: 0; z-index: 100;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: var(--glass-bg, rgba(255, 255, 255, 0.85));
}
.info-pane { flex: 1; min-width: 260px; }
.url-text { word-break: break-all; color: var(--text-secondary, #6b7280); font-size: 12px; }

/* QR preview */
.qr-preview-area { display: flex; flex-direction: column; gap: 8px; }
.qr-meta { font-size: 12px; color: var(--text-secondary, #6b7280); }
.qr-meta p { margin: 4px 0; }
</style>
