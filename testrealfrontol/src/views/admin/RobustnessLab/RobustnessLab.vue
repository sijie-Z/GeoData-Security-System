<!--
  RobustnessLab — 鲁棒性实验室（管理员）· v2（样板 A 重排 + 可理解性全家桶）
  页内分区（结构对齐已验收样板 A · Linear 风）：
    ① 页头：标题/副题 +「重新讲解」(ElTour) + 刷新
    ② Hero KPI 带：基线 NC ｜ 旧方案 n/6 ｜ D-QIM n/6 ｜ 转败为胜 +N（数据从当前 run rows 推导）
    ③ 发起实验 + 历史运行（并排两卡）
    ④ 实验是怎么做的（四步流程图解 + 实验设置 checklist，方法论透明）
    ⑤ 结果矩阵（行=方案/列=攻击；单元格胶囊化；攻击列头 hover 卡 = 攻击词典 + 查看代码）
    ⑥ 对比结论卡（自动结论 + 标签 + 1/6 → 4/6）
    ⑦ 导出 JSON / 刷新（矩阵头保留）
  可理解层：指标词典（ⓘ 悬停一句话 → 点击 el-popover 详解卡，含 0.75/0.95 阈值色条）、
  攻击词典（列头 hover 与单元格 tooltip 首行）、攻击源码抽屉（el-drawer + 等宽 pre，
  source 来自 GET /api/robustness/attacks/meta，只含攻击函数本体）。
  动效（克制）：KPI 数字 count-up 160ms、矩阵行首次入场 stagger 30ms/行、进行中状态徽点
  pulse、卡片 hover 仅边框变色（尊重 prefers-reduced-motion）。
  数据源：GET /api/robustness/runs、GET /api/robustness/runs/<id>（进度轮询）、
          GET /api/robustness/attacks/meta（源码抽屉）。
  颜色只消费 design-system.css 的 CSS 变量名（另一条线在改 token 值，不写死新色值）。
-->
<template>
  <div class="robustness-lab fade-in">
    <!-- ① 页头 -->
    <div id="lab-head" class="page-header">
      <div class="page-header-text">
        <h2>{{ $t('robustnessLab.title') }}</h2>
        <p class="subtitle">{{ $t('robustnessLab.subtitle') }}</p>
      </div>
      <div class="page-header-actions">
        <el-button :icon="ChatDotRound" @click="openTour">
          {{ $t('robustnessLab.tourReplay') }}
        </el-button>
        <el-button :icon="Refresh" :loading="runsLoading && detailLoading" @click="refreshAll">
          {{ $t('robustnessLab.refreshBtn') }}
        </el-button>
      </div>
    </div>

    <!-- ② Hero KPI 带（数据从当前 run rows 推导；无 run 时空态） -->
    <section id="lab-kpi" class="kpi-band" :aria-label="$t('robustnessLab.kpiAria')">
      <div class="kpi-card">
        <span class="kpi-label">
          {{ $t('robustnessLab.kpiBaselineLabel') }}
          <el-tooltip :content="$t('robustnessLab.metricNcShort')" placement="top" :show-after="120">
            <span
              ref="kpiGlossaryAnchor"
              class="info-dot kpi-dot"
              role="button"
              tabindex="0"
              :aria-label="$t('robustnessLab.metricGlossaryTitle')"
            >
              <el-icon :size="13"><InfoFilled /></el-icon>
            </span>
          </el-tooltip>
        </span>
        <span class="kpi-value mono-num">{{ baselineText }}</span>
        <span class="kpi-note">{{ baselineNoteText }}</span>
      </div>

      <div class="kpi-card">
        <span class="kpi-label">
          {{ $t('robustnessLab.scheme.legacy') }}
          <el-tooltip :content="$t('robustnessLab.schemeDesc.legacy')" placement="top" :show-after="120">
            <span class="info-dot" tabindex="0"><el-icon :size="13"><InfoFilled /></el-icon></span>
          </el-tooltip>
        </span>
        <span class="kpi-value mono-num">{{ schemeValueText('legacy') }}</span>
        <span class="kpi-note">{{ schemeNoteText('legacy') }}</span>
      </div>

      <div class="kpi-card">
        <span class="kpi-label">
          {{ $t('robustnessLab.scheme.dqim1') }}
          <el-tooltip :content="$t('robustnessLab.schemeDesc.dqim1')" placement="top" :show-after="120">
            <span class="info-dot" tabindex="0"><el-icon :size="13"><InfoFilled /></el-icon></span>
          </el-tooltip>
        </span>
        <span class="kpi-value mono-num">{{ schemeValueText('dqim1') }}</span>
        <span class="kpi-note">{{ schemeNoteText('dqim1') }}</span>
      </div>

      <div class="kpi-card is-win">
        <span class="kpi-label">
          {{ $t('robustnessLab.kpiWinLabel') }}
          <el-tooltip :content="$t('robustnessLab.kpiWinDesc')" placement="top" :show-after="120">
            <span class="info-dot" tabindex="0"><el-icon :size="13"><InfoFilled /></el-icon></span>
          </el-tooltip>
        </span>
        <span class="kpi-value mono-num">{{ winValueText }}</span>
        <span class="kpi-note">{{ winNoteText }}</span>
      </div>
    </section>
    <p v-if="!kpi" class="kpi-empty">
      {{ $t('robustnessLab.kpiEmpty') }} · {{ $t('robustnessLab.kpiEmptyHint') }}
    </p>

    <!-- ③ 发起实验 + 历史运行 -->
    <div class="control-grid">
      <el-card id="lab-run" shadow="never" class="lab-card run-card">
        <h4 class="card-title">{{ $t('robustnessLab.runTitle') }}</h4>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.dataLabel') }}</label>
          <el-select
            v-model="selectedDataId"
            class="data-select"
            filterable
            clearable
            :loading="dataLoading"
            :placeholder="$t('robustnessLab.dataPlaceholder')"
          >
            <el-option
              v-for="d in vectorDataList"
              :key="d.data_id"
              :label="dataOptionLabel(d)"
              :value="d.data_id"
            />
          </el-select>
        </div>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.dataIdLabel') }}</label>
          <el-input-number
            v-model="manualDataId"
            class="data-id-input"
            :min="1"
            :step="1"
            :controls="false"
            placeholder="data_id"
          />
        </div>
        <p class="form-hint">{{ $t('robustnessLab.dataIdHint') }}</p>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.schemesLabel') }}</label>
          <el-checkbox-group v-model="selectedSchemes" class="check-group">
            <el-checkbox v-for="s in SCHEMES" :key="s" :value="s" class="check-item">
              {{ $t(`robustnessLab.scheme.${s}`) }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.attacksLabel') }}</label>
          <el-checkbox-group v-model="selectedAttacks" class="check-group">
            <el-checkbox v-for="a in ATTACKS" :key="a" :value="a" class="check-item">
              {{ $t(`robustnessLab.attack.${a}`) }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.trialsLabel') }}</label>
          <el-select v-model="selectedTrials" class="trials-select">
            <el-option v-for="n in TRIAL_OPTIONS" :key="n" :label="String(n)" :value="n" />
          </el-select>
        </div>
        <p class="form-hint">{{ $t('robustnessLab.trialsHint') }}</p>

        <el-button
          type="primary"
          class="start-btn"
          :icon="VideoPlay"
          :loading="startLoading"
          @click="startRun"
        >
          {{ $t('robustnessLab.startBtn') }}
        </el-button>
      </el-card>

      <el-card id="lab-history" shadow="never" class="lab-card history-card">
        <h4 class="card-title">{{ $t('robustnessLab.historyTitle') }}</h4>
        <el-table
          v-loading="runsLoading"
          :data="runs"
          size="small"
          class="history-table"
          :empty-text="$t('robustnessLab.historyEmpty')"
          highlight-current-row
          :row-class-name="historyRowClass"
          @row-click="onRunRowClick"
        >
          <el-table-column :label="$t('robustnessLab.colRunId')" min-width="130">
            <template #default="{ row }">
              <HashText :value="row.run_id" :head="8" :tail="4" />
            </template>
          </el-table-column>
          <el-table-column :label="$t('robustnessLab.colDataRef')" min-width="100">
            <template #default="{ row }">
              <span class="mono-text">{{ row.data_ref }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('robustnessLab.colCreatedAt')" min-width="150">
            <template #default="{ row }">
              <span class="mono-text">{{ formatTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('robustnessLab.colProgress')" width="90" align="right">
            <template #default="{ row }">
              <span class="mono-text">{{ row.done }}/{{ row.total }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('robustnessLab.colStatus')" width="110" align="center">
            <template #default="{ row }">
              <span class="status-badge" :class="runStatusClass(row)">
                <i v-if="runStatusClass(row) === 'is-running'" class="pulse-dot"></i>
                {{ runStatusText(row) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        <p class="panel-foot">{{ $t('robustnessLab.trialsHint') }}</p>
      </el-card>
    </div>

    <!-- ④ 实验是怎么做的（四步流程图解 + 实验设置 checklist） -->
    <el-card id="lab-how" shadow="never" class="lab-card how-card">
      <div class="panel-head">
        <h4 class="card-title inline-title">{{ $t('robustnessLab.howTitle') }}</h4>
        <span class="head-note">{{ $t('robustnessLab.howSubtitle') }}</span>
      </div>
      <div class="flow">
        <template v-for="(node, i) in flowNodes" :key="node.name">
          <el-icon v-if="i > 0" class="flow-arrow" :size="16"><Right /></el-icon>
          <div class="flow-node">
            <span class="flow-icon"><el-icon :size="17"><component :is="node.icon" /></el-icon></span>
            <div class="flow-text">
              <span class="flow-name">{{ node.name }}</span>
              <p>{{ node.desc }}</p>
            </div>
          </div>
        </template>
      </div>
      <div class="setup-grid">
        <div v-for="item in setupItems" :key="item.label" class="setup-item">
          <span class="setup-label">{{ item.label }}</span>
          <span class="setup-text">
            {{ item.text }}
            <code v-if="item.code" class="setup-code">{{ item.code }}</code>
          </span>
        </div>
      </div>
    </el-card>

    <!-- ⑤ 结果矩阵（+ ⑥ 对比结论卡 + ⑦ 导出/刷新） -->
    <el-card id="lab-matrix" v-loading="detailLoading" shadow="never" class="lab-card matrix-card">
      <template v-if="runMeta">
        <div class="matrix-head">
          <div class="matrix-meta">
            <h4 class="card-title inline-title">{{ $t('robustnessLab.matrixTitle') }}</h4>
            <HashText :value="runMeta.run_id" :head="8" :tail="4" />
            <span class="meta-sep">·</span>
            <span class="mono-text">{{ runMeta.data_ref }}</span>
            <span class="meta-sep">·</span>
            <span class="mono-text">{{ formatTime(runMeta.created_at) }}</span>
          </div>
          <div class="matrix-actions">
            <div v-if="!matrixDone" class="progress-inline">
              <el-progress :percentage="progressPct" :stroke-width="8" :show-text="false" class="progress-bar" />
              <span class="mono-text progress-text">{{ runMeta.done }}/{{ runMeta.total }}</span>
            </div>
            <el-button size="small" :icon="Download" @click="exportJson">
              {{ $t('robustnessLab.exportBtn') }}
            </el-button>
            <el-button size="small" :icon="Refresh" @click="loadRun(runMeta.run_id)">
              {{ $t('robustnessLab.refreshBtn') }}
            </el-button>
          </div>
        </div>

        <p class="matrix-subtitle">
          <span>{{ $t('robustnessLab.matrixSubtitle') }}</span>
          <el-tooltip :content="$t('robustnessLab.metricNcShort')" placement="top" :show-after="100">
            <span
              ref="glossaryAnchor"
              class="info-dot glossary-dot"
              role="button"
              tabindex="0"
              :aria-label="$t('robustnessLab.metricGlossaryTitle')"
            >
              <el-icon :size="13"><InfoFilled /></el-icon>
            </span>
          </el-tooltip>
        </p>
        <el-popover
          :virtual-ref="glossaryAnchor"
          virtual-triggering
          trigger="click"
          :width="420"
          popper-class="glossary-popper"
        >
          <template #title>
            <span class="glossary-title">{{ $t('robustnessLab.metricGlossaryTitle') }}</span>
          </template>
          <MetricGlossary />
        </el-popover>
        <el-popover
          :virtual-ref="kpiGlossaryAnchor"
          virtual-triggering
          trigger="click"
          :width="420"
          popper-class="glossary-popper"
        >
          <template #title>
            <span class="glossary-title">{{ $t('robustnessLab.metricGlossaryTitle') }}</span>
          </template>
          <MetricGlossary />
        </el-popover>

        <el-table
          :data="matrixRows"
          class="matrix-table"
          :row-class-name="matrixRowClass"
          :row-style="matrixRowStyle"
        >
          <el-table-column :label="$t('robustnessLab.colScheme')" width="190" fixed>
            <template #default="{ row }">
              <span class="scheme-name" :class="`is-${row.scheme}`">
                {{ schemeLabel(row.scheme) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            v-for="(attack, idx) in matrixAttacks"
            :key="attack"
            align="right"
            min-width="118"
          >
            <!-- 攻击词典：列头 hover 卡（机制 + 参数 + 查看代码） -->
            <template #header>
              <el-popover
                placement="bottom"
                trigger="hover"
                :width="340"
                :show-after="140"
                :hide-after="120"
                popper-class="attack-head-popper"
              >
                <template #reference>
                  <span class="th-label">
                    {{ attackLabel(attack) }}
                    <el-icon class="th-info" :size="12"><InfoFilled /></el-icon>
                  </span>
                </template>
                <div class="attack-head-card">
                  <p class="ah-desc">{{ attackDescFor(attack) }}</p>
                  <div class="ah-foot">
                    <span v-if="metaParamsFor(attack)" class="ah-params mono-text">
                      {{ formatMetaParams(metaParamsFor(attack)) }}
                    </span>
                    <el-button
                      class="attack-code-link"
                      size="small"
                      text
                      type="primary"
                      @click="openAttackCode(attack)"
                    >
                      {{ $t('robustnessLab.codeBtn') }}
                    </el-button>
                  </div>
                </div>
              </el-popover>
            </template>
            <template #default="{ row }">
              <el-tooltip
                v-if="row.cells[idx] && cellHasResult(row.cells[idx])"
                placement="top"
                effect="dark"
                :show-after="120"
              >
                <template #content>
                  <div class="cell-tip">
                    <div class="tip-attack-desc">{{ attackDescFor(attack) }}</div>
                    <template v-if="cellMultiTrial(row.cells[idx])">
                      <div>{{ $t('robustnessLab.tipMeanNc') }}: {{ formatMeanNc(row.cells[idx]) }}</div>
                      <div>{{ $t('robustnessLab.tipStdNc') }}: {{ formatStdNc(row.cells[idx]) }}</div>
                      <div
                        v-for="r in row.cells[idx].rows"
                        :key="r.trial ?? 0"
                        class="tip-trial-line"
                      >
                        {{ $t('robustnessLab.tipTrial', { n: r.trial ?? 1 }) }}:
                        {{ trialResultText(r) }} · {{ formatParams(r.attack_params) }}
                      </div>
                    </template>
                    <template v-else>
                      <div>{{ $t('robustnessLab.tipParams') }}: {{ formatParams(cellSingleRow(row.cells[idx]).attack_params) }}</div>
                      <div>BER: {{ formatBer(cellSingleRow(row.cells[idx]).ber) }}</div>
                      <div>{{ $t('robustnessLab.tipDuration') }}: {{ formatDuration(cellSingleRow(row.cells[idx]).duration_ms) }}</div>
                    </template>
                    <div class="tip-metric-hint">{{ $t('robustnessLab.metricNcShort') }}</div>
                    <div class="tip-metric-hint">{{ $t('robustnessLab.metricBerShort') }}</div>
                  </div>
                </template>
                <span class="cell-value" :class="cellClass(row.cells[idx])">
                  {{ cellText(row.cells[idx]) }}
                  <i v-if="cellImproved(row.scheme, attack)" class="cell-up">↑</i>
                </span>
              </el-tooltip>
              <span v-else class="cell-value is-pending">{{ $t('robustnessLab.cellPending') }}</span>
            </template>
          </el-table-column>
        </el-table>

        <p class="footnote">
          <el-icon class="footnote-icon" :size="14"><InfoFilled /></el-icon>
          <span>{{ $t('robustnessLab.methodBoundary') }}</span>
        </p>
        <p class="footnote">
          <el-icon class="footnote-icon" :size="14"><InfoFilled /></el-icon>
          <span>{{ $t('robustnessLab.matrixFootnote') }}</span>
        </p>

        <!-- ⑥ 对比结论卡（自动生成，数字来自数据） -->
        <div id="lab-verdict" class="verdict-card" :class="{ 'is-ready': verdictReady }">
          <div class="verdict-main">
            <span class="verdict-icon"><el-icon :size="18"><Medal /></el-icon></span>
            <div class="verdict-text">
              <h4 class="verdict-title">{{ $t('robustnessLab.verdictTitle') }}</h4>
              <template v-if="verdictReady">
                <p v-for="(sentence, i) in verdictSentences" :key="i" class="verdict-line">{{ sentence }}</p>
              </template>
              <p v-else-if="!verdictComparable" class="verdict-line is-muted">
                {{ $t('robustnessLab.verdictNotComparable') }}
              </p>
              <p v-else class="verdict-line is-muted">
                {{ $t('robustnessLab.verdictPending', { done: runMeta.done, total: runMeta.total }) }}
              </p>
            </div>
          </div>
          <div v-if="verdictComparable" class="verdict-stat">
            <span class="verdict-stat-label">{{ $t('robustnessLab.verdictStatLabel') }}</span>
            <span class="verdict-stat-value mono-num">
              {{ verdictStatLegacy }} <i>→</i> {{ verdictStatDqim }}
            </span>
          </div>
          <div class="verdict-tags">
            <span
              v-for="item in verdictItems"
              :key="item.attack"
              class="verdict-tag"
              :class="`is-${item.kind}`"
            >
              {{ attackLabel(item.attack) }} · {{ tagText(item.kind) }}
            </span>
          </div>
        </div>
      </template>
      <EmptyState
        v-else
        variant="never"
        :title="$t('robustnessLab.noRun')"
      />
    </el-card>

    <!-- 攻击源码抽屉（rtl，宽 640；等宽 pre，零新依赖） -->
    <el-drawer
      v-model="codeDrawer.open"
      direction="rtl"
      size="640px"
      :title="drawerTitle"
      class="code-drawer"
      destroy-on-close
    >
      <div v-loading="codeDrawer.loading" class="code-drawer-body">
        <template v-if="drawerEntry">
          <div class="code-meta">
            <span class="code-params-label">{{ $t('robustnessLab.codeParamsLabel') }}</span>
            <span class="code-params mono-text">{{ formatMetaParams(drawerEntry.params_default) }}</span>
          </div>
          <pre class="code-block">{{ drawerEntry.code }}</pre>
          <p class="code-note">{{ $t('robustnessLab.codeNote') }}</p>
        </template>
        <p v-else-if="codeDrawer.error" class="code-error">{{ $t('robustnessLab.codeLoadFailed') }}</p>
      </div>
    </el-drawer>

    <!-- 首入引导 ElTour（6 步，localStorage tour:v1:lab；遮罩色随浅/深模式） -->
    <el-tour v-model="tourOpen" :mask="tourMask" @close="markTourSeen" @finish="markTourSeen">
      <el-tour-step
        v-for="(step, i) in tourSteps"
        :key="i"
        :target="step.target"
        :title="step.title"
        :description="step.description"
      />
    </el-tour>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  Aim,
  ChatDotRound,
  CircleCheck,
  Download,
  InfoFilled,
  Key,
  MagicStick,
  Medal,
  Refresh,
  Right,
  VideoPlay,
} from '@element-plus/icons-vue'

import HashText from '@/components/common/HashText.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import MetricGlossary from './MetricGlossary.vue'
import { getDataList } from '@/api/upload'
import {
  getRobustnessAttacksMeta,
  getRobustnessRun,
  getRobustnessRuns,
  startRobustnessRun,
} from '@/api/robustness'

const { t } = useI18n()

// 与后端白名单同名同序（schemes 决定矩阵行、attacks 决定矩阵列）
const SCHEMES = ['legacy', 'dqim1']
const ATTACKS = ['none', 'translate', 'scale', 'vertex_drop', 'noise', 'simplify']

// 矩阵行/列顺序（含栅格 kind 的白名单，历史里点到栅格运行也能如实成表）
const SCHEME_ORDER = ['legacy', 'dqim1', 'lsb', 'dwt', 'histogram', 'blind']
const ATTACK_ORDER = ['none', 'translate', 'scale', 'vertex_drop', 'noise', 'simplify', 'jpeg', 'resize', 'crop', 'rotate', 'blur']
const RASTER_ONLY_ATTACKS = new Set(['jpeg', 'resize', 'crop', 'rotate', 'blur'])

// 试验次数选项（1 = 文档化默认参数；>1 = 每格 N 次参数抖动试验，seed 固定可复现）
const TRIAL_OPTIONS = [1, 3, 5, 10]

const POLL_INTERVAL_MS = 5000
const TOUR_KEY = 'tour:v1:lab'
const COUNT_UP_MS = 160
const STAGGER_STEP_MS = 30

// ── 运行控制状态 ──
const vectorDataList = ref([])
const dataLoading = ref(false)
const selectedDataId = ref(null)
const manualDataId = ref(null)
const selectedSchemes = ref([...SCHEMES])
const selectedAttacks = ref([...ATTACKS])
const selectedTrials = ref(1)
const startLoading = ref(false)

// ── 历史列表状态 ──
const runs = ref([])
const runsLoading = ref(false)

// ── 当前 run（矩阵 + 结论 + KPI）状态 ──
const runMeta = ref(null)
const runRows = ref([])
const runSummary = ref([])
const detailLoading = ref(false)
let pollTimer = null

// ── 可理解层状态 ──
const attacksMeta = ref(null)
const codeDrawer = reactive({ open: false, attack: null, kind: 'vector', loading: false, error: false })
const glossaryAnchor = ref(null)
const kpiGlossaryAnchor = ref(null)

// ── ElTour 状态 ──
const tourOpen = ref(false)
const tourMask = ref(true)

// ──────────────────────────────────────
//  数据获取
// ──────────────────────────────────────

const fetchVectorData = async () => {
  dataLoading.value = true
  try {
    const res = await getDataList('vector', { page: 1, pageSize: 100 })
    const body = res.data
    if (body?.status) vectorDataList.value = body.data?.list || []
  } catch {
    // 矢量列表拉取失败不阻断：仍可手填 data_id
  } finally {
    dataLoading.value = false
  }
}

const fetchRuns = async () => {
  runsLoading.value = true
  try {
    const res = await getRobustnessRuns({ page: 1, per_page: 20 })
    const body = res.data
    if (body?.status) {
      runs.value = body.runs || []
    } else {
      ElMessage.error(body?.msg || t('robustnessLab.historyLoadFailed'))
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || t('robustnessLab.historyLoadFailed'))
  } finally {
    runsLoading.value = false
  }
}

// 攻击源码元数据：静默预取（列头 hover 卡与源码抽屉共用；失败不打扰，抽屉里会报错）
const fetchAttacksMeta = async () => {
  try {
    const res = await getRobustnessAttacksMeta()
    if (res.data?.status) attacksMeta.value = res.data
  } catch {
    // 静默：抽屉打开时会给出可见的失败提示
  }
}

const applyRunPayload = (run) => {
  runMeta.value = {
    run_id: run.run_id,
    data_ref: run.data_ref,
    created_at: run.created_at,
    kind: run.kind ?? 'vector',
    trials: run.trials ?? 1,
    done: run.done,
    total: run.total,
  }
  runRows.value = Array.isArray(run.rows) ? run.rows : []
  runSummary.value = Array.isArray(run.summary) ? run.summary : []
}

const loadRun = async (runId) => {
  if (!runId) return
  detailLoading.value = true
  try {
    const res = await getRobustnessRun(runId)
    const body = res.data
    if (body?.status && body.run) {
      applyRunPayload(body.run)
      if (body.run.done < body.run.total) startPolling()
      else stopPolling()
    } else {
      ElMessage.error(body?.msg || t('robustnessLab.matrixLoadFailed'))
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.msg || t('robustnessLab.matrixLoadFailed'))
  } finally {
    detailLoading.value = false
  }
}

// ── 轮询：实验进行中每 5s 刷新进度，完成后自动停止并刷新历史 ──
const startPolling = () => {
  stopPolling()
  pollTimer = setInterval(pollTick, POLL_INTERVAL_MS)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const pollTick = async () => {
  const runId = runMeta.value?.run_id
  if (!runId) {
    stopPolling()
    return
  }
  try {
    const res = await getRobustnessRun(runId)
    const run = res.data?.run
    if (!run) return
    applyRunPayload(run)
    if (run.done >= run.total) {
      stopPolling()
      fetchRuns()
    }
  } catch {
    // 单次轮询失败静默，下一个周期重试
  }
}

onBeforeUnmount(() => {
  stopPolling()
  if (staggerTimer) clearTimeout(staggerTimer)
})

// ──────────────────────────────────────
//  发起实验
// ──────────────────────────────────────

const resolvedDataId = computed(() => {
  const raw = manualDataId.value ?? selectedDataId.value
  return raw === null || raw === undefined || raw === '' ? null : Number(raw)
})

const startRun = async () => {
  const dataId = resolvedDataId.value
  if (dataId === null) {
    ElMessage.warning(t('robustnessLab.dataRequired'))
    return
  }
  if (!Number.isInteger(dataId) || dataId <= 0) {
    ElMessage.warning(t('robustnessLab.dataIdInvalid'))
    return
  }
  if (!selectedSchemes.value.length || !selectedAttacks.value.length) {
    ElMessage.warning(t('robustnessLab.comboRequired'))
    return
  }

  startLoading.value = true
  try {
    const res = await startRobustnessRun({
      data_id: dataId,
      schemes: [...selectedSchemes.value],
      attacks: [...selectedAttacks.value],
      trials: selectedTrials.value,
    })
    const body = res.data
    if (body?.status && body.data?.run_id) {
      ElMessage.success(t('robustnessLab.startOk', { total: body.data.total }))
      await fetchRuns()
      await loadRun(body.data.run_id)
    } else {
      ElMessage.error(body?.msg || t('robustnessLab.startFailed'))
    }
  } catch (e) {
    if (e.response?.status === 409) {
      ElMessage.warning(e.response?.data?.msg || t('robustnessLab.startBusy'))
    } else {
      ElMessage.error(e.response?.data?.msg || t('robustnessLab.startFailed'))
    }
  } finally {
    startLoading.value = false
  }
}

// ──────────────────────────────────────
//  历史列表
// ──────────────────────────────────────

const onRunRowClick = (row) => {
  loadRun(row.run_id)
}

const runStatusText = (row) => {
  if (row.error && row.done < row.total) return t('robustnessLab.statusError')
  if (row.total > 0 && row.done >= row.total) return t('robustnessLab.statusDone')
  return t('robustnessLab.statusRunning')
}

const runStatusClass = (row) => {
  if (row.error && row.done < row.total) return 'is-error'
  if (row.total > 0 && row.done >= row.total) return 'is-done'
  return 'is-running'
}

const historyRowClass = ({ row }) => {
  const cls = runMeta.value && row.run_id === runMeta.value.run_id ? 'is-active-row' : ''
  // §4.13 状态色带：行左 4px
  const s = runStatusClass(row)
  const band = s === 'is-done' ? 'row-band-success' : s === 'is-error' ? 'row-band-danger' : 'row-band-warning'
  return `${cls} ${band}`.trim()
}

const refreshAll = async () => {
  await fetchRuns()
  if (runMeta.value) await loadRun(runMeta.value.run_id)
}

// ──────────────────────────────────────
//  结果矩阵（行/列从 run rows 推导，未知方案/攻击也能如实成表）
// ──────────────────────────────────────

const matrixSchemes = computed(() => {
  const present = new Set(runRows.value.map((r) => r.scheme))
  const known = SCHEME_ORDER.filter((s) => present.has(s))
  const unknown = [...present].filter((s) => !SCHEME_ORDER.includes(s)).sort()
  return [...known, ...unknown]
})

const matrixAttacks = computed(() => {
  const present = new Set(runRows.value.map((r) => r.attack))
  const known = ATTACK_ORDER.filter((a) => present.has(a))
  const unknown = [...present].filter((a) => !ATTACK_ORDER.includes(a)).sort()
  return [...known, ...unknown]
})

// (scheme|attack) -> 行数组（按 trial 升序）；试验次数 > 1 时每格多行
const rowsByCell = computed(() => {
  const map = {}
  for (const r of runRows.value) {
    const key = `${r.scheme}|${r.attack}`
    if (!map[key]) map[key] = []
    map[key].push(r)
  }
  for (const key of Object.keys(map)) {
    map[key].sort((a, b) => (a.trial ?? 1) - (b.trial ?? 1))
  }
  return map
})

// 详情端点的聚合块（服务端计算的成功率 / NC 均值 / 标准差），按格索引
const summaryByCell = computed(() => {
  const map = {}
  for (const entry of runSummary.value) {
    map[`${entry.scheme}|${entry.attack}`] = entry
  }
  return map
})

const matrixRows = computed(() =>
  matrixSchemes.value.map((scheme) => ({
    scheme,
    cells: matrixAttacks.value.map((a) => {
      const rows = rowsByCell.value[`${scheme}|${a}`]
      if (!rows || !rows.length) return null
      return { rows, summary: summaryByCell.value[`${scheme}|${a}`] || null }
    }),
  }))
)

// 单元格显示：trials=1 维持原样（完成 → NC 四位小数；失败 ✗）；
// trials>1 显示「成功率 · NC 均值」，色阶按成功率（100% 绿 / ≥60% 黄 / <60% 红）。
const cellMultiTrial = (cell) => !!cell && cell.rows.length > 1

const isCellPending = (cell) => !cell || cell.rows.some((r) => r.decode_success === null)

const cellHasResult = (cell) => !!cell && cell.rows.some((r) => r.decode_success !== null)

const cellSingleRow = (cell) => cell.rows[0]

const cellSuccesses = (cell) => cell.rows.filter((r) => r.decode_success === true).length

const isCellAllPass = (cell) => !!cell && cell.rows.length > 0 && cell.rows.every((r) => r.decode_success === true)

const cellClass = (cell) => {
  if (isCellPending(cell)) return 'is-pending'
  if (cellMultiTrial(cell)) {
    const rate = cellSuccesses(cell) / cell.rows.length
    if (rate >= 1) return 'is-high'
    if (rate >= 0.6) return 'is-mid'
    return 'is-low'
  }
  const row = cellSingleRow(cell)
  if (!row.decode_success) return 'is-fail'
  if (Number(row.nc) >= 0.95) return 'is-high'
  if (Number(row.nc) >= 0.75) return 'is-mid'
  return 'is-low'
}

const cellText = (cell) => {
  if (isCellPending(cell)) return t('robustnessLab.cellPending')
  if (cellMultiTrial(cell)) {
    const base = `${cellSuccesses(cell)}/${cell.rows.length}`
    const mean = cell.summary?.mean_nc
    return mean === null || mean === undefined ? base : `${base} · ${Number(mean).toFixed(3)}`
  }
  const row = cellSingleRow(cell)
  if (!row.decode_success) return t('robustnessLab.cellFailed')
  return Number(row.nc).toFixed(4)
}

// D-QIM 单元格「转败为胜」小箭头（旧方案失败、D-QIM 全部试验成功）
const cellImproved = (scheme, attack) => {
  if (scheme !== 'dqim1') return false
  const legacy = rowsByCell.value[`legacy|${attack}`]
  const dqim = rowsByCell.value[`dqim1|${attack}`]
  if (!legacy || !legacy.length) return false
  return !isCellAllPass({ rows: legacy }) && isCellAllPass({ rows: dqim || [] })
}

// ── 矩阵行入场 stagger（仅首次渲染；150ms 后自动失效，不干预后续切换） ──
const staggerOn = ref(false)
let staggerTimer = null
let staggerConsumed = false

watch(
  () => runRows.value.length,
  (len) => {
    if (staggerConsumed || !len) return
    staggerConsumed = true
    staggerOn.value = true
    staggerTimer = setTimeout(() => {
      staggerOn.value = false
    }, len * STAGGER_STEP_MS + 400)
  }
)

const matrixRowClass = () => (staggerOn.value ? 'matrix-enter' : '')

const matrixRowStyle = ({ rowIndex }) =>
  staggerOn.value ? { '--row-delay': `${rowIndex * STAGGER_STEP_MS}ms` } : {}

const matrixDone = computed(() => !!runMeta.value && runMeta.value.done >= runMeta.value.total)

const progressPct = computed(() => {
  if (!runMeta.value || !runMeta.value.total) return 0
  return Math.min(100, Math.round((runMeta.value.done / runMeta.value.total) * 100))
})

// ──────────────────────────────────────
//  攻击词典 / 源码抽屉
// ──────────────────────────────────────

const attackKind = (attack) => {
  if (RASTER_ONLY_ATTACKS.has(attack)) return 'raster'
  if (attack === 'noise') return runMeta.value?.kind === 'raster' ? 'raster' : 'vector'
  return 'vector'
}

const attackLabel = (attack) =>
  attackKind(attack) === 'raster'
    ? t(`robustnessLab.attackRaster.${attack}`)
    : t(`robustnessLab.attack.${attack}`)

const attackDescFor = (attack) =>
  attackKind(attack) === 'raster'
    ? t(`robustnessLab.attackRasterDesc.${attack}`)
    : t(`robustnessLab.attackDesc.${attack}`)

// meta 里对应攻击的默认参数（预取未完成时返回 null，hover 卡省略参数行）
const metaParamsFor = (attack) => {
  const meta = attacksMeta.value
  if (!meta) return null
  const list = attackKind(attack) === 'raster' ? meta.raster : meta.vector
  const entry = (list || []).find((e) => e.name === attack)
  return entry ? entry.params_default : null
}

const formatMetaParams = (params) => {
  if (!params || typeof params !== 'object') return '—'
  const entries = Object.entries(params)
  if (!entries.length) return '—'
  return entries.map(([k, v]) => `${k}=${v === null ? 'auto' : v}`).join(', ')
}

const drawerEntry = computed(() => {
  const meta = attacksMeta.value
  if (!meta || !codeDrawer.attack) return null
  const list = codeDrawer.kind === 'raster' ? meta.raster : meta.vector
  return (list || []).find((e) => e.name === codeDrawer.attack) || null
})

const drawerTitle = computed(() =>
  codeDrawer.attack
    ? t('robustnessLab.codeDrawerTitle', { name: attackLabel(codeDrawer.attack) })
    : t('robustnessLab.codeBtn')
)

const openAttackCode = async (attack) => {
  codeDrawer.attack = attack
  codeDrawer.kind = attackKind(attack)
  codeDrawer.error = false
  codeDrawer.open = true
  if (!attacksMeta.value) {
    codeDrawer.loading = true
    try {
      const res = await getRobustnessAttacksMeta()
      if (res.data?.status) {
        attacksMeta.value = res.data
      } else {
        codeDrawer.error = true
      }
    } catch {
      codeDrawer.error = true
    } finally {
      codeDrawer.loading = false
    }
  }
}

// ──────────────────────────────────────
//  Hero KPI 带（全部数字从 run rows 推导；无 run → 空态）
// ──────────────────────────────────────

const cellMeanNc = (scheme, attack) => {
  const rows = rowsByCell.value[`${scheme}|${attack}`]
  if (!rows || !rows.length) return null
  const vals = rows
    .map((r) => r.nc)
    .filter((v) => v !== null && v !== undefined)
    .map(Number)
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null
}

const kpi = computed(() => {
  if (!runMeta.value || !runRows.value.length) return null
  const attacks = matrixAttacks.value
  const attacksCount = attacks.length
  if (!attacksCount) return null

  const noneRows = runRows.value.filter((r) => r.attack === 'none' && r.nc !== null && r.nc !== undefined)
  const baseline = noneRows.length
    ? noneRows.reduce((s, r) => s + Number(r.nc), 0) / noneRows.length
    : null

  const legacyPresent = runRows.value.some((r) => r.scheme === 'legacy')
  const dqimPresent = runRows.value.some((r) => r.scheme === 'dqim1')

  const schemeSuccess = (scheme) => {
    if (!runRows.value.some((r) => r.scheme === scheme)) return null
    return attacks.filter((a) => isCellAllPass({ rows: rowsByCell.value[`${scheme}|${a}`] || [] })).length
  }
  const schemeFailNames = (scheme) => {
    if (!runRows.value.some((r) => r.scheme === scheme)) return []
    return attacks.filter((a) => {
      const rows = rowsByCell.value[`${scheme}|${a}`]
      return rows && rows.length && !rows.every((r) => r.decode_success === true)
    })
  }

  const improved = attacks.filter((a) => {
    const legacy = rowsByCell.value[`legacy|${a}`]
    const dqim = rowsByCell.value[`dqim1|${a}`]
    return (
      legacy &&
      legacy.length &&
      dqim &&
      dqim.length &&
      !legacy.every((r) => r.decode_success === true) &&
      dqim.every((r) => r.decode_success === true)
    )
  })

  // 基线注记：两方案一致 / 不一致取均值 / 仅单一方案
  let baselineNoteKind = null
  let baselineNoteScheme = null
  const legacyBase = legacyPresent ? cellMeanNc('legacy', 'none') : null
  const dqimBase = dqimPresent ? cellMeanNc('dqim1', 'none') : null
  if (legacyBase !== null && dqimBase !== null) {
    baselineNoteKind = Math.abs(legacyBase - dqimBase) < 1e-9 ? 'same' : 'avg'
  } else if (legacyBase !== null || dqimBase !== null) {
    baselineNoteKind = 'scheme'
    baselineNoteScheme = legacyBase !== null ? 'legacy' : 'dqim1'
  }

  return {
    baseline,
    baselineNoteKind,
    baselineNoteScheme,
    attacksCount,
    legacy: schemeSuccess('legacy'),
    dqim: schemeSuccess('dqim1'),
    legacyFailNames: schemeFailNames('legacy'),
    dqimFailNames: schemeFailNames('dqim1'),
    improved: improved.map((a) => attackLabel(a)),
  }
})

// KPI 数字 count-up（160ms，rAF；尊重 prefers-reduced-motion）
const kpiAnim = reactive({ baseline: null, legacy: null, dqim: null, win: null })
const animTokens = { baseline: 0, legacy: 0, dqim: 0, win: 0 }

const prefersReducedMotion = () => {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

const animateTo = (key, target) => {
  const token = ++animTokens[key]
  if (target === null || target === undefined) {
    kpiAnim[key] = null
    return
  }
  if (prefersReducedMotion()) {
    kpiAnim[key] = target
    return
  }
  const from = kpiAnim[key] === null || Number.isNaN(kpiAnim[key]) ? 0 : Number(kpiAnim[key])
  const start = performance.now()
  const step = (now) => {
    if (token !== animTokens[key]) return
    const p = Math.min(1, (now - start) / COUNT_UP_MS)
    kpiAnim[key] = from + (target - from) * p
    if (p < 1) requestAnimationFrame(step)
    else kpiAnim[key] = target
  }
  requestAnimationFrame(step)
}

watch(
  kpi,
  (val) => {
    animateTo('baseline', val ? val.baseline : null)
    animateTo('legacy', val ? val.legacy : null)
    animateTo('dqim', val ? val.dqim : null)
    animateTo('win', val ? val.improved.length : null)
  },
  { immediate: true }
)

const baselineText = computed(() =>
  kpiAnim.baseline === null ? '—' : Number(kpiAnim.baseline).toFixed(4)
)

const schemeValueText = (scheme) => {
  const val = kpi.value
  if (!val) return '—'
  const n = scheme === 'legacy' ? kpiAnim.legacy : kpiAnim.dqim
  if (n === null) return '—'
  return `${Math.round(n)}/${val.attacksCount}`
}

const winValueText = computed(() =>
  kpiAnim.win === null ? '—' : t('robustnessLab.kpiWinValue', { n: Math.round(kpiAnim.win) })
)

const baselineNoteText = computed(() => {
  const val = kpi.value
  if (!val || !val.baselineNoteKind) return ''
  if (val.baselineNoteKind === 'same') return t('robustnessLab.kpiBaselineNoteSame')
  if (val.baselineNoteKind === 'avg') return t('robustnessLab.kpiBaselineNoteAvg')
  return t('robustnessLab.kpiBaselineNoteScheme', {
    scheme:
      val.baselineNoteScheme === 'legacy'
        ? t('robustnessLab.scheme.legacy')
        : t('robustnessLab.scheme.dqim1'),
  })
})

const schemeNoteText = (scheme) => {
  const val = kpi.value
  if (!val) return ''
  const success = scheme === 'legacy' ? val.legacy : val.dqim
  if (success === null) return ''
  const fails = scheme === 'legacy' ? val.legacyFailNames : val.dqimFailNames
  if (!fails.length) return t('robustnessLab.kpiNoteAllPass')
  if (fails.length >= val.attacksCount) return t('robustnessLab.kpiNoteAllFail')
  if (fails.length <= 3) {
    return t('robustnessLab.kpiNoteFailList', { list: fails.map((a) => attackLabel(a)).join(' · ') })
  }
  return t('robustnessLab.kpiNoteFail', { n: fails.length })
}

const winNoteText = computed(() => {
  const val = kpi.value
  if (!val) return ''
  if (!val.improved.length) return t('robustnessLab.kpiWinNoteNone')
  return t('robustnessLab.kpiWinNote', { list: val.improved.join(' · ') })
})

// ──────────────────────────────────────
//  对比结论（全部来自数据）
// ──────────────────────────────────────

const verdictComparable = computed(() => {
  const present = new Set(runRows.value.map((r) => r.scheme))
  return present.has('legacy') && present.has('dqim1')
})

const verdictItems = computed(() => {
  const incomplete = (rows) => !rows || !rows.length || rows.some((r) => r.decode_success === null)
  return matrixAttacks.value.map((attack) => {
    const legacyRows = rowsByCell.value[`legacy|${attack}`]
    const dqimRows = rowsByCell.value[`dqim1|${attack}`]
    if (incomplete(legacyRows) || incomplete(dqimRows)) {
      return { attack, kind: 'pending' }
    }
    // 多次试验时"成功" = 该格全部试验解码成功（trials=1 时与单行判定一致）
    const legacyOk = legacyRows.every((r) => r.decode_success === true)
    const dqimOk = dqimRows.every((r) => r.decode_success === true)
    if (!legacyOk && dqimOk) return { attack, kind: 'improved' }
    if (legacyOk && !dqimOk) return { attack, kind: 'regressed' }
    if (legacyOk && dqimOk) return { attack, kind: 'same-pass' }
    return { attack, kind: 'same-fail' }
  })
})

const verdictReady = computed(
  () =>
    matrixDone.value &&
    verdictComparable.value &&
    verdictItems.value.length > 0 &&
    verdictItems.value.every((i) => i.kind !== 'pending')
)

const verdictSentences = computed(() => {
  const items = verdictItems.value
  const improved = items.filter((i) => i.kind === 'improved')
  const regressed = items.filter((i) => i.kind === 'regressed')
  const samePass = items.filter((i) => i.kind === 'same-pass')
  const sameFail = items.filter((i) => i.kind === 'same-fail')
  const sentences = []
  if (improved.length) sentences.push(t('robustnessLab.verdictImproved', { n: improved.length }))
  if (regressed.length) sentences.push(t('robustnessLab.verdictRegressed', { n: regressed.length }))
  if (!improved.length && !regressed.length) {
    sentences.push(t('robustnessLab.verdictTie', { pass: samePass.length, fail: sameFail.length }))
  }
  return sentences
})

const verdictStatLegacy = computed(() => {
  const val = kpi.value
  if (!val || val.legacy === null) return '—'
  return `${val.legacy}/${val.attacksCount}`
})

const verdictStatDqim = computed(() => {
  const val = kpi.value
  if (!val || val.dqim === null) return '—'
  return `${val.dqim}/${val.attacksCount}`
})

const tagText = (kind) => t(`robustnessLab.tag.${kind}`)

// ──────────────────────────────────────
//  实验流程图解
// ──────────────────────────────────────

const flowNodes = computed(() => [
  { name: t('robustnessLab.stepEmbed'), desc: t('robustnessLab.stepEmbedDesc'), icon: MagicStick },
  { name: t('robustnessLab.stepAttack'), desc: t('robustnessLab.stepAttackDesc'), icon: Aim },
  { name: t('robustnessLab.stepExtract'), desc: t('robustnessLab.stepExtractDesc'), icon: Key },
  { name: t('robustnessLab.stepJudge'), desc: t('robustnessLab.stepJudgeDesc'), icon: CircleCheck },
])

const setupItems = computed(() => [
  {
    label: t('robustnessLab.setupHostLabel'),
    text: runMeta.value
      ? t('robustnessLab.setupHostValue', { ref: runMeta.value.data_ref })
      : t('robustnessLab.setupHostIdle'),
    code: null,
  },
  { label: t('robustnessLab.setupPayloadLabel'), text: t('robustnessLab.setupPayloadValue'), code: null },
  { label: t('robustnessLab.setupParamsLabel'), text: t('robustnessLab.setupParamsValue'), code: null },
  {
    label: t('robustnessLab.setupRepeatLabel'),
    text: runMeta.value
      ? t('robustnessLab.setupRepeatValue', { trials: runMeta.value.trials })
      : t('robustnessLab.setupRepeatIdle'),
    code: null,
  },
  { label: t('robustnessLab.setupMetricsLabel'), text: t('robustnessLab.setupMetricsValue'), code: null },
  {
    label: t('robustnessLab.setupReproLabel'),
    text: t('robustnessLab.setupReproValue'),
    code: 'python tests/robustness_trials_battle.py',
  },
])

// ──────────────────────────────────────
//  ElTour 首入引导（6 步；localStorage tour:v1:lab）
// ──────────────────────────────────────

const tourTarget = (selector, fallbackSelector) => () => {
  return document.querySelector(selector) || document.querySelector(fallbackSelector) || document.body
}

const tourSteps = computed(() => [
  {
    target: tourTarget('#lab-head'),
    title: t('robustnessLab.tour1Title'),
    description: t('robustnessLab.tour1Desc'),
  },
  {
    target: tourTarget('#lab-kpi'),
    title: t('robustnessLab.tour2Title'),
    description: t('robustnessLab.tour2Desc'),
  },
  {
    target: tourTarget('#lab-run'),
    title: t('robustnessLab.tour3Title'),
    description: t('robustnessLab.tour3Desc'),
  },
  {
    target: tourTarget('#lab-history'),
    title: t('robustnessLab.tour4Title'),
    description: t('robustnessLab.tour4Desc'),
  },
  {
    target: tourTarget('#lab-matrix'),
    title: t('robustnessLab.tour5Title'),
    description: t('robustnessLab.tour5Desc'),
  },
  {
    target: tourTarget('#lab-verdict', '#lab-matrix'),
    title: t('robustnessLab.tour6Title'),
    description: t('robustnessLab.tour6Desc'),
  },
])

const markTourSeen = () => {
  try {
    localStorage.setItem(TOUR_KEY, '1')
  } catch {
    // localStorage 不可用时仅本次会话生效
  }
}

const openTour = () => {
  // 遮罩色随浅/深模式：运行时读取 --el-mask-color（EP 在浅色为白霜、深色由
  // design-system.css 覆写为深海军蓝），只消费变量名，不写死色值。
  try {
    const color = getComputedStyle(document.documentElement).getPropertyValue('--el-mask-color').trim()
    tourMask.value = color ? { color } : true
  } catch {
    tourMask.value = true
  }
  tourOpen.value = true
}

watch(tourOpen, (open) => {
  if (!open) markTourSeen()
})

// ──────────────────────────────────────
//  格式化 / 导出
// ──────────────────────────────────────

const formatTime = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleString()
}

const dataOptionLabel = (d) => `${d.data_alias || d.name || 'dataset'} · #${d.data_id}`

const schemeLabel = (scheme) => t(`robustnessLab.scheme.${scheme}`)

const formatParams = (params) => {
  if (!params || typeof params !== 'object') return '—'
  const entries = Object.entries(params)
  if (!entries.length) return '—'
  return entries.map(([k, v]) => `${k}=${v}`).join(', ')
}

const formatBer = (ber) => (ber === null || ber === undefined ? '—' : Number(ber).toExponential(3))

const formatDuration = (ms) => (ms === null || ms === undefined ? '—' : `${(Number(ms) / 1000).toFixed(1)} s`)

// 多试验单元格：均值/标准差来自详情端点的 summary 块（nc 全空 → —）
const formatMeanNc = (cell) => {
  const mean = cell.summary?.mean_nc
  return mean === null || mean === undefined ? '—' : Number(mean).toFixed(4)
}

const formatStdNc = (cell) => {
  const std = cell.summary?.std_nc
  return std === null || std === undefined ? '—' : Number(std).toFixed(4)
}

// 第 r 次试验的结果文本：✓/✗ + 解码成功时的 NC（等待中显示 …）
const trialResultText = (row) => {
  if (row.decode_success === null) return '…'
  const nc = row.nc === null || row.nc === undefined ? null : Number(row.nc)
  if (!row.decode_success) return nc === null ? '✗' : `✗ · ${nc.toFixed(4)}`
  return `✓ · ${nc === null ? '—' : nc.toFixed(4)}`
}

const exportJson = () => {
  if (!runMeta.value) return
  const payload = {
    run_id: runMeta.value.run_id,
    data_ref: runMeta.value.data_ref,
    created_at: runMeta.value.created_at,
    trials: runMeta.value.trials,
    done: runMeta.value.done,
    total: runMeta.value.total,
    summary: runSummary.value,
    rows: runRows.value,
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `robustness_${runMeta.value.run_id.slice(0, 8)}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success(t('robustnessLab.exportOk'))
}

onMounted(async () => {
  fetchRuns()
  fetchVectorData()
  fetchAttacksMeta()
  try {
    if (!localStorage.getItem(TOUR_KEY)) openTour()
  } catch {
    // localStorage 不可用（隐私模式等）：不自动弹出，可从「重新讲解」手动打开
  }
})
</script>

<style scoped>
.robustness-lab {
  width: 100%;
}

/* ── 页头 ── */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.page-header h2 {
  font-size: 22px;
  color: var(--text-primary);
  margin: 0 0 6px;
}

.subtitle {
  color: var(--text-tertiary);
  font-size: 13.5px;
  line-height: 1.65;
  margin: 0;
  max-width: 860px;
}

.page-header-actions {
  display: flex;
  gap: 10px;
  flex: 0 0 auto;
}

/* ── 通用卡片（hover 仅边框变色，不做位移） ── */
.lab-card {
  border-radius: var(--radius-lg);
  margin-bottom: 16px;
  transition: border-color var(--transition-fast);
}

.lab-card:hover {
  border-color: var(--primary-300);
}

.card-title {
  margin: 0 0 12px;
  font-size: 15px;
  color: var(--text-primary);
}

.inline-title {
  margin: 0;
  display: inline-block;
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.head-note {
  font-size: 12.5px;
  color: var(--text-tertiary);
}

/* ── ② Hero KPI 带 ── */
.kpi-band {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 8px;
}

@media (max-width: 1000px) {
  .kpi-band {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.kpi-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px 16px;
  background: var(--bg-primary);
  /* §4.11 ring 描边（替代 border，避免双线） */
  border: none;
  box-shadow: var(--card-ring);
  border-radius: var(--radius-md);
  transition: box-shadow var(--transition-fast);
}

.kpi-card:hover {
  box-shadow: inset 0 0 0 1px var(--primary-300);
}

.kpi-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-secondary);
}

.kpi-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.kpi-card.is-win .kpi-value {
  color: var(--tint-success-text);
}

.kpi-note {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-tertiary);
}

.kpi-empty {
  margin: 0 0 16px;
  font-size: 12.5px;
  color: var(--text-tertiary);
}

/* 通用 ⓘ（悬停提示 + 点击词典） */
.info-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: var(--radius-full);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-fast), background var(--transition-fast);
}

.info-dot:hover,
.info-dot:focus-visible {
  color: var(--primary-600);
  background: var(--primary-50);
}

.mono-num {
  font-variant-numeric: tabular-nums;
}

/* ── ③ 控制 + 历史 ── */
.control-grid {
  display: grid;
  grid-template-columns: minmax(340px, 430px) 1fr;
  gap: 16px;
  align-items: stretch;
}

.control-grid .lab-card {
  margin-bottom: 16px;
}

@media (max-width: 1100px) {
  .control-grid {
    grid-template-columns: 1fr;
  }
}

.form-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}

.form-label {
  flex: 0 0 92px;
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 32px;
}

.data-select {
  flex: 1;
}

.data-id-input {
  width: 140px;
}

.trials-select {
  width: 140px;
}

.form-hint {
  margin: -4px 0 12px 102px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.check-group {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 10px;
  padding-top: 5px;
}

.check-item {
  margin-right: 0;
}

.start-btn {
  width: 100%;
  margin-top: 4px;
}

.history-table {
  width: 100%;
}

.history-table :deep(.el-table__row) {
  cursor: pointer;
}

.history-table :deep(.is-active-row td.el-table__cell) {
  background: var(--primary-50);
}

.history-table :deep(.is-active-row td.el-table__cell:first-child) {
  box-shadow: inset 2px 0 0 var(--primary-600);
}

.mono-text {
  font-family: var(--font-mono);
  font-size: 12.5px;
  color: var(--text-secondary);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 10px;
  font-size: 12px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.status-badge.is-done {
  color: var(--tint-success-text);
  background: var(--tint-success-bg);
}

.status-badge.is-running {
  color: var(--tint-warning-text);
  background: var(--tint-warning-bg);
}

.status-badge.is-error {
  color: var(--tint-danger-text);
  background: var(--tint-danger-bg);
}

/* 进行中状态徽点 pulse（克制：仅透明度呼吸） */
.pulse-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 6px;
  border-radius: var(--radius-full);
  background: var(--warning-500);
}

@media (prefers-reduced-motion: no-preference) {
  .pulse-dot {
    animation: labPulse 1.2s ease-in-out infinite;
  }
}

@keyframes labPulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

.panel-foot {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-tertiary);
}

/* ── ④ 实验流程图解 ── */
.flow {
  display: flex;
  align-items: stretch;
  gap: 8px;
  flex-wrap: wrap;
}

.flow-arrow {
  align-self: center;
  color: var(--text-tertiary);
  flex: 0 0 auto;
}

.flow-node {
  flex: 1 1 190px;
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
}

.flow-icon {
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--primary-50);
  color: var(--primary-600);
}

.flow-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.flow-text p {
  margin: 4px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
}

@media (max-width: 900px) {
  .flow-arrow {
    display: none;
  }
}

.setup-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 20px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--border-color-light);
}

.setup-item {
  display: flex;
  gap: 8px;
  font-size: 12.5px;
  line-height: 1.6;
}

.setup-label {
  flex: 0 0 58px;
  color: var(--text-tertiary);
}

.setup-text {
  color: var(--text-secondary);
}

.setup-code {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

@media (max-width: 900px) {
  .setup-grid {
    grid-template-columns: 1fr;
  }
}

/* ── ⑤ 结果矩阵 ── */
.matrix-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.matrix-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-sep {
  color: var(--text-tertiary);
}

.matrix-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  width: 160px;
}

.progress-text {
  white-space: nowrap;
}

.matrix-subtitle {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 0 0 12px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text-tertiary);
}

.glossary-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.matrix-table {
  width: 100%;
}

/* 单元格胶囊 + 44px 行高 + 等宽数字（对齐样板 A） */
.matrix-table :deep(.el-table__cell) {
  padding-top: 7px;
  padding-bottom: 7px;
}

.matrix-table :deep(th.el-table__cell) {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
}

.th-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: default;
}

.th-info {
  color: var(--text-tertiary);
}

.attack-head-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ah-desc {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--text-secondary);
}

.ah-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.ah-params {
  font-size: 11.5px;
  color: var(--text-tertiary);
  word-break: break-all;
}

.scheme-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
}

.scheme-name.is-dqim1,
.scheme-name.is-blind {
  color: var(--primary-600);
}

/* 单元格胶囊化：颜色与阈值一致（≥0.95 绿 / ≥0.75 黄 / <0.75 红） */
.cell-value {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-width: 104px;
  height: 30px;
  padding: 0 10px;
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  border-radius: var(--radius-sm);
}

.cell-value.is-high {
  color: var(--tint-success-text);
  background: var(--tint-success-bg);
  border: 1px solid var(--tint-success-border);
}

.cell-value.is-mid {
  color: var(--tint-warning-text);
  background: var(--tint-warning-bg);
  border: 1px solid var(--tint-warning-border);
}

.cell-value.is-low {
  color: var(--tint-danger-text);
  background: var(--tint-danger-bg);
  border: 1px solid var(--tint-danger-border);
}

.cell-value.is-fail {
  color: var(--tint-danger-text);
  background: var(--tint-danger-bg);
  border: 1px solid var(--tint-danger-border);
  font-size: 12.5px;
  font-weight: 500;
}

.cell-value.is-pending {
  color: var(--text-tertiary);
  background: var(--tint-neutral-bg);
  border: 1px dashed var(--border-color);
  font-weight: 400;
}

.cell-up {
  font-style: normal;
  font-size: 11px;
  transform: translateY(-2px);
}

/* 行入场 stagger（仅首次渲染；30ms/行） */
@media (prefers-reduced-motion: no-preference) {
  .matrix-table :deep(.matrix-enter .cell) {
    animation: labRowIn 0.24s ease both;
    animation-delay: var(--row-delay, 0ms);
  }
}

@keyframes labRowIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.cell-tip {
  font-size: 12px;
  line-height: 1.7;
  max-width: 340px;
}

.cell-tip .tip-attack-desc {
  color: inherit;
  opacity: 0.72;
  margin-bottom: 4px;
}

.cell-tip .tip-metric-hint {
  color: inherit;
  opacity: 0.72;
  margin-top: 4px;
  font-size: 11.5px;
  line-height: 1.55;
}

.cell-tip .tip-trial-line {
  font-variant-numeric: tabular-nums;
}

.footnote {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.65;
  color: var(--text-tertiary);
}

.footnote-icon {
  margin-top: 2px;
  flex: 0 0 auto;
}

/* ── ⑥ 对比结论卡（样板 A 排版：左图标+文本，右大数字，下标签行） ── */
.verdict-card {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px 24px;
  align-items: start;
  margin-top: 16px;
  padding: 16px 18px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  transition: border-color var(--transition-fast);
}

.verdict-card.is-ready {
  border-color: var(--primary-200);
}

.verdict-main {
  display: flex;
  gap: 12px;
}

.verdict-icon {
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--primary-50);
  border: 1px solid var(--primary-100);
  color: var(--primary-600);
}

.verdict-title {
  margin: 0;
  font-size: 15px;
  color: var(--text-primary);
}

.verdict-line {
  margin: 6px 0 0;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--text-primary);
}

.verdict-line.is-muted {
  color: var(--text-tertiary);
}

.verdict-stat {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.verdict-stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.verdict-stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.verdict-stat-value i {
  font-style: normal;
  color: var(--tint-success-text);
  padding: 0 5px;
}

.verdict-tags {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.verdict-tag {
  padding: 3px 12px;
  font-size: 12px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
}

.verdict-tag.is-improved {
  color: var(--tint-success-text);
  background: var(--tint-success-bg);
  border-color: var(--tint-success-border);
}

.verdict-tag.is-regressed {
  color: var(--tint-danger-text);
  background: var(--tint-danger-bg);
  border-color: var(--tint-danger-border);
}

.verdict-tag.is-same-pass {
  color: var(--primary-700);
  background: var(--primary-50);
  border-color: var(--primary-100);
}

.verdict-tag.is-same-fail {
  color: var(--text-secondary);
  background: var(--tint-neutral-bg);
  border-color: var(--border-color);
}

.verdict-tag.is-pending {
  color: var(--text-tertiary);
  background: var(--tint-neutral-bg);
  font-style: italic;
}

/* ── 攻击源码抽屉（等宽 pre，零新依赖） ── */
.code-drawer-body {
  min-height: 120px;
}

.code-meta {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
}

.code-params-label {
  font-size: 12px;
  color: var(--text-tertiary);
  flex: 0 0 auto;
}

.code-params {
  font-size: 12px;
  word-break: break-all;
}

.code-block {
  margin: 0;
  padding: 14px 16px;
  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
  overflow: auto;
  white-space: pre;
}

.code-note {
  margin: 12px 0 0;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-tertiary);
}

.code-error {
  margin: 0;
  font-size: 13px;
  color: var(--tint-danger-text);
}
</style>
