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
  攻击词典（列头 hover 与单元格 tooltip 首行）、攻击源码抽屉（el-drawer + highlight.js
  python 高亮 + 行号 + #L{n} 行锚点，source 来自 GET /api/robustness/attacks/meta）。
  动效（克制）：KPI 数字 count-up 160ms、矩阵行首次入场 stagger 30ms/行、进行中状态徽点
  pulse、卡片 hover 仅边框变色（尊重 prefers-reduced-motion）。
  数据源：GET /api/robustness/runs、GET /api/robustness/runs/<id>（进度轮询）、
          GET /api/robustness/attacks/meta（源码抽屉）。
  颜色只消费 design-system.css 的 CSS 变量名（另一条线在改 token 值，不写死新色值）。
-->
<template>
  <div class="robustness-lab fade-in">
    <!-- ① 页头 -->
    <div
      id="lab-head"
      class="page-header"
    >
      <div class="page-header-text">
        <h1>{{ $t('robustnessLab.title') }}</h1>
        <p class="subtitle">
          {{ subtitleText }}
        </p>
      </div>
      <div class="page-header-actions">
        <el-button
          :icon="ChatDotRound"
          @click="openTour"
        >
          {{ $t('robustnessLab.tourReplay') }}
        </el-button>
        <el-button
          :icon="Refresh"
          :loading="runsLoading && detailLoading"
          @click="refreshAll"
        >
          {{ $t('robustnessLab.refreshBtn') }}
        </el-button>
      </div>
    </div>

    <!-- ② Hero KPI 带（数据从当前 run rows 推导；无 run 时空态；扫描 run 用曲线视图代替） -->
    <section
      v-if="!isSweepRun"
      id="lab-kpi"
      class="kpi-band"
      :aria-label="$t('robustnessLab.kpiAria')"
    >
      <div class="kpi-card">
        <span class="kpi-label">
          {{ $t('robustnessLab.kpiBaselineLabel') }}
          <el-tooltip
            :content="$t('robustnessLab.metricNcShort')"
            placement="top"
            :show-after="120"
          >
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

      <div
        v-for="(scheme, i) in kpiPair"
        :key="scheme"
        class="kpi-card"
      >
        <span class="kpi-label">
          {{ schemeLabel(scheme) }}
          <el-tooltip
            :content="$t(`robustnessLab.schemeDesc.${scheme}`)"
            placement="top"
            :show-after="120"
          >
            <span
              class="info-dot"
              tabindex="0"
            ><el-icon :size="13"><InfoFilled /></el-icon></span>
          </el-tooltip>
        </span>
        <span class="kpi-value mono-num">{{ schemeValueText(i) }}</span>
        <span class="kpi-note">{{ schemeNoteText(i) }}</span>
      </div>

      <div class="kpi-card is-win">
        <span class="kpi-label">
          {{ $t('robustnessLab.kpiWinLabel') }}
          <el-tooltip
            :content="kpiWinDescText"
            placement="top"
            :show-after="120"
          >
            <span
              class="info-dot"
              tabindex="0"
            ><el-icon :size="13"><InfoFilled /></el-icon></span>
          </el-tooltip>
        </span>
        <span class="kpi-value mono-num">{{ winValueText }}</span>
        <span class="kpi-note">{{ winNoteText }}</span>
      </div>
    </section>
    <p
      v-if="!isSweepRun && !kpi"
      class="kpi-empty"
    >
      {{ $t('robustnessLab.kpiEmpty') }} · {{ $t('robustnessLab.kpiEmptyHint') }}
    </p>

    <!-- ③ 发起实验 + 历史运行 -->
    <div class="control-grid">
      <el-card
        id="lab-run"
        shadow="never"
        class="lab-card run-card"
      >
        <h2 class="card-title">
          {{ $t('robustnessLab.runTitle') }}
        </h2>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.kindLabel') }}</label>
          <el-radio-group
            v-model="runKind"
            class="kind-segment"
          >
            <el-radio-button value="vector">
              {{ $t('robustnessLab.kind.vector') }}
            </el-radio-button>
            <el-radio-button value="raster">
              {{ $t('robustnessLab.kind.raster') }}
            </el-radio-button>
          </el-radio-group>
        </div>

        <!-- 实验模式：单点矩阵（现行为）/ 强度扫描（WAVES 式梯度 → 检出率曲线） -->
        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.modeLabel') }}</label>
          <el-radio-group
            v-model="runMode"
            class="kind-segment"
          >
            <el-radio-button value="matrix">
              {{ $t('robustnessLab.mode.matrix') }}
            </el-radio-button>
            <el-radio-button value="sweep">
              {{ $t('robustnessLab.mode.sweep') }}
            </el-radio-button>
          </el-radio-group>
        </div>
        <template v-if="runMode === 'sweep'">
          <p class="form-hint">
            {{ $t('robustnessLab.sweepHint') }}
          </p>
          <p class="form-hint">
            {{ $t('robustnessLab.sweepYHint') }}
          </p>
        </template>

        <template v-if="runKind === 'vector'">
          <div class="form-row">
            <label class="form-label">{{ $t('robustnessLab.dataLabel') }}</label>
            <el-select
              v-model="selectedDataId"
              class="data-select"
              filterable
              clearable
              :aria-label="$t('robustnessLab.dataLabel')"
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
          <p class="form-hint">
            {{ $t('robustnessLab.dataIdHint') }}
          </p>
        </template>
        <p
          v-else
          class="form-hint is-kind"
        >
          {{ $t('robustnessLab.hostLineRaster') }}
        </p>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.schemesLabel') }}</label>
          <el-checkbox-group
            v-model="selectedSchemes"
            class="check-group"
          >
            <el-checkbox
              v-for="s in kindSchemeOptions"
              :key="s"
              :value="s"
              class="check-item"
            >
              {{ schemeLabel(s) }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.attacksLabel') }}</label>
          <el-checkbox-group
            v-model="selectedAttacks"
            class="check-group"
          >
            <el-checkbox
              v-for="a in kindAttackOptions"
              :key="a"
              :value="a"
              class="check-item"
            >
              {{ attackLabel(a, runKind) }}
            </el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="form-row">
          <label class="form-label">{{ $t('robustnessLab.trialsLabel') }}</label>
          <el-select
            v-model="selectedTrials"
            class="trials-select"
            :aria-label="$t('robustnessLab.trialsLabel')"
          >
            <el-option
              v-for="n in trialOptions"
              :key="n"
              :label="String(n)"
              :value="n"
            />
          </el-select>
        </div>
        <p class="form-hint">
          {{ $t('robustnessLab.trialsHint') }}
        </p>

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

      <el-card
        id="lab-history"
        shadow="never"
        class="lab-card history-card"
      >
        <h2 class="card-title">
          {{ $t('robustnessLab.historyTitle') }}
        </h2>
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
          <el-table-column
            :label="$t('robustnessLab.colRunId')"
            min-width="130"
          >
            <template #default="{ row }">
              <HashText
                :value="row.run_id"
                :head="8"
                :tail="4"
              />
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('robustnessLab.colKind')"
            width="76"
            align="center"
          >
            <template #default="{ row }">
              <span
                class="kind-badge"
                :class="`is-${historyKind(row)}`"
              >
                {{ $t(`robustnessLab.kind.${historyKind(row)}`) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('robustnessLab.colMode')"
            width="76"
            align="center"
          >
            <template #default="{ row }">
              <span
                class="mode-badge"
                :class="`is-${historyMode(row)}`"
              >
                {{ $t(`robustnessLab.modeBadge.${historyMode(row)}`) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('robustnessLab.colDataRef')"
            min-width="100"
          >
            <template #default="{ row }">
              <span class="mono-text">{{ row.data_ref }}</span>
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('robustnessLab.colCreatedAt')"
            min-width="150"
          >
            <template #default="{ row }">
              <span class="mono-text">{{ formatTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('robustnessLab.colProgress')"
            width="90"
            align="right"
          >
            <template #default="{ row }">
              <span class="mono-text">{{ row.done }}/{{ row.total }}</span>
            </template>
          </el-table-column>
          <el-table-column
            :label="$t('robustnessLab.colStatus')"
            width="110"
            align="center"
          >
            <template #default="{ row }">
              <span
                class="status-badge"
                :class="runStatusClass(row)"
              >
                <i
                  v-if="runStatusClass(row) === 'is-running'"
                  class="pulse-dot"
                />
                {{ runStatusText(row) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        <p class="panel-foot">
          {{ $t('robustnessLab.trialsHint') }}
        </p>
      </el-card>
    </div>

    <!-- ④ 实验是怎么做的（四步流程图解 + 实验设置 checklist） -->
    <el-card
      id="lab-how"
      shadow="never"
      class="lab-card how-card"
    >
      <div class="panel-head">
        <h2 class="card-title inline-title">
          {{ $t('robustnessLab.howTitle') }}
        </h2>
        <span class="head-note">{{ $t('robustnessLab.howSubtitle') }}</span>
      </div>
      <div class="flow">
        <template
          v-for="(node, i) in flowNodes"
          :key="node.name"
        >
          <el-icon
            v-if="i > 0"
            class="flow-arrow"
            :size="16"
          >
            <Right />
          </el-icon>
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
        <div
          v-for="item in setupItems"
          :key="item.label"
          class="setup-item"
        >
          <span class="setup-label">{{ item.label }}</span>
          <span class="setup-text">
            {{ item.text }}
            <code
              v-if="item.code"
              class="setup-code"
            >{{ item.code }}</code>
          </span>
        </div>
      </div>
    </el-card>

    <!-- ⑤ 结果矩阵（+ ⑥ 对比结论卡 + ⑦ 导出/刷新） -->
    <el-card
      id="lab-matrix"
      v-loading="detailLoading"
      shadow="never"
      class="lab-card matrix-card"
    >
      <template v-if="runMeta">
        <div class="matrix-head">
          <div class="matrix-meta">
            <h2 class="card-title inline-title">
              {{ isSweepRun ? $t('robustnessLab.sweepTitle') : $t('robustnessLab.matrixTitle') }}
            </h2>
            <HashText
              :value="runMeta.run_id"
              :head="8"
              :tail="4"
            />
            <span class="meta-sep">·</span>
            <span class="mono-text">{{ runMeta.data_ref }}</span>
            <span class="meta-sep">·</span>
            <span class="mono-text">{{ formatTime(runMeta.created_at) }}</span>
          </div>
          <div class="matrix-actions">
            <div
              v-if="!matrixDone"
              class="progress-inline"
            >
              <el-progress
                :percentage="progressPct"
                :stroke-width="8"
                :show-text="false"
                class="progress-bar"
              />
              <span class="mono-text progress-text">{{ runMeta.done }}/{{ runMeta.total }}</span>
            </div>
            <el-button
              size="small"
              :icon="Download"
              @click="exportJson"
            >
              {{ $t('robustnessLab.exportBtn') }}
            </el-button>
            <el-button
              size="small"
              :icon="Refresh"
              @click="loadRun(runMeta.run_id)"
            >
              {{ $t('robustnessLab.refreshBtn') }}
            </el-button>
          </div>
        </div>

        <!-- 强度扫描 run：每攻击一张「强度档 → 检出成功率」小图（2 列网格，
             x=档位 label、y=成功率 0-100%，每方案一条线；悬停看档位参数与 n/N） -->
        <template v-if="isSweepRun">
          <p class="matrix-subtitle">
            <span>{{ $t('robustnessLab.sweepSubtitle') }}</span>
          </p>
          <div class="sweep-grid">
            <div
              v-for="attack in sweepAttacks"
              :key="attack"
              class="sweep-card"
            >
              <div class="sweep-card-head">
                <span class="sweep-attack-name">{{ attackLabel(attack) }}</span>
                <span class="sweep-card-note mono-num">
                  {{ $t('robustnessLab.sweepCardMeta', { trials: runMeta.trials }) }}
                </span>
              </div>
              <v-chart
                class="sweep-chart"
                :option="sweepOption(attack)"
                :autoresize="{ throttle: 160 }"
              />
              <p
                v-if="sweepErrorCount(attack)"
                class="sweep-anomaly mono-num"
              >
                {{ $t('robustnessLab.sweepCardAnomalies', { n: sweepErrorCount(attack) }) }}
              </p>
            </div>
          </div>

          <!-- 扫描结论卡：崩塌点摘要 = 首个档内成功率 < 0.5 的档位（无则全档存活），每方案一行 -->
          <div
            id="lab-collapse"
            class="verdict-card"
            :class="{ 'is-ready': matrixDone }"
          >
            <div class="verdict-main">
              <span class="verdict-icon"><el-icon :size="18"><TrendCharts /></el-icon></span>
              <div class="verdict-text">
                <h3 class="verdict-title">
                  {{ $t('robustnessLab.collapseTitle') }}
                </h3>
                <template v-if="matrixDone">
                  <div
                    v-for="line in collapseLines"
                    :key="line.scheme"
                    class="collapse-line"
                  >
                    <p class="verdict-line">
                      <span
                        class="collapse-scheme"
                        :class="`is-${line.scheme}`"
                      >{{ line.name }}</span>
                      <span
                        v-if="line.tierIndex === null"
                        class="collapse-alive"
                      >
                        {{ $t('robustnessLab.collapseAllAlive') }}
                      </span>
                      <span
                        v-else
                        class="collapse-hit"
                      >
                        {{ $t('robustnessLab.collapseAt', { tier: line.tierIndex + 1, rate: line.rateText }) }}
                      </span>
                    </p>
                    <p
                      v-if="line.detail"
                      class="collapse-detail"
                    >
                      {{ line.detail }}
                    </p>
                  </div>
                </template>
                <p
                  v-else
                  class="verdict-line is-muted"
                >
                  {{ $t('robustnessLab.verdictPending', { done: runMeta.done, total: runMeta.total }) }}
                </p>
              </div>
            </div>
          </div>
        </template>

        <!-- 单点矩阵 run：行=方案 列=攻击 的结果矩阵（原视图） -->
        <template v-else>
          <p class="matrix-subtitle">
            <span>{{ $t('robustnessLab.matrixSubtitle') }}</span>
            <el-tooltip
              :content="$t('robustnessLab.metricNcShort')"
              placement="top"
              :show-after="100"
            >
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
            <el-table-column
              :label="$t('robustnessLab.colScheme')"
              width="190"
              fixed
            >
              <template #default="{ row }">
                <span
                  class="scheme-name"
                  :class="`is-${row.scheme}`"
                >
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
                      <el-icon
                        class="th-info"
                        :size="12"
                      ><InfoFilled /></el-icon>
                    </span>
                  </template>
                  <div class="attack-head-card">
                    <p class="ah-desc">
                      {{ attackDescFor(attack) }}
                    </p>
                    <div class="ah-foot">
                      <span
                        v-if="metaParamsFor(attack)"
                        class="ah-params mono-text"
                      >
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
                      <div class="tip-attack-desc">
                        {{ attackDescFor(attack) }}
                      </div>
                      <template v-if="cellMultiTrial(row.cells[idx])">
                        <div>{{ $t('robustnessLab.tipMeanNc') }}: {{ formatMeanNc(row.cells[idx]) }}</div>
                        <div>{{ $t('robustnessLab.tipStdNc') }}: {{ formatStdNc(row.cells[idx]) }}</div>
                        <template
                          v-for="r in row.cells[idx].rows"
                          :key="r.trial ?? 0"
                        >
                          <div class="tip-trial-line">
                            {{ $t('robustnessLab.tipTrial', { n: r.trial ?? 1 }) }}:
                            {{ trialResultText(r) }} · {{ formatParams(r.attack_params) }}
                          </div>
                          <div
                            v-if="r.error"
                            class="tip-trial-error"
                          >
                            {{ r.error }}
                          </div>
                        </template>
                      </template>
                      <template v-else>
                        <div>{{ $t('robustnessLab.tipParams') }}: {{ formatParams(cellSingleRow(row.cells[idx]).attack_params) }}</div>
                        <div>BER: {{ formatBer(cellSingleRow(row.cells[idx]).ber) }}</div>
                        <div>{{ $t('robustnessLab.tipDuration') }}: {{ formatDuration(cellSingleRow(row.cells[idx]).duration_ms) }}</div>
                        <div
                          v-if="cellSingleRow(row.cells[idx]).error"
                          class="tip-trial-error"
                        >
                          {{ $t('robustnessLab.tipError') }}: {{ cellSingleRow(row.cells[idx]).error }}
                        </div>
                      </template>
                      <div class="tip-metric-hint">
                        {{ $t('robustnessLab.metricNcShort') }}
                      </div>
                      <div class="tip-metric-hint">
                        {{ $t('robustnessLab.metricBerShort') }}
                      </div>
                    </div>
                  </template>
                  <span
                    class="cell-value"
                    :class="cellClass(row.cells[idx])"
                  >
                    {{ cellText(row.cells[idx]) }}
                    <i
                      v-if="cellImproved(row.scheme, attack)"
                      class="cell-up"
                    >↑</i>
                  </span>
                </el-tooltip>
                <span
                  v-else
                  class="cell-value is-pending"
                >{{ $t('robustnessLab.cellPending') }}</span>
              </template>
            </el-table-column>
          </el-table>

          <p class="footnote">
            <el-icon
              class="footnote-icon"
              :size="14"
            >
              <InfoFilled />
            </el-icon>
            <span>{{ runMeta.kind === 'raster' ? $t('robustnessLab.methodBoundaryRaster') : $t('robustnessLab.methodBoundary') }}</span>
          </p>
          <p class="footnote">
            <el-icon
              class="footnote-icon"
              :size="14"
            >
              <InfoFilled />
            </el-icon>
            <span>{{ runMeta.kind === 'raster' ? $t('robustnessLab.matrixFootnoteRaster') : $t('robustnessLab.matrixFootnote') }}</span>
          </p>

          <!-- ⑥ 对比结论卡（自动生成，数字来自数据） -->
          <div
            id="lab-verdict"
            class="verdict-card"
            :class="{ 'is-ready': verdictReady }"
          >
            <div class="verdict-main">
              <span class="verdict-icon"><el-icon :size="18"><Medal /></el-icon></span>
              <div class="verdict-text">
                <h3 class="verdict-title">
                  {{ $t('robustnessLab.verdictTitle') }}
                </h3>
                <template v-if="verdictReady">
                  <p
                    v-for="(sentence, i) in verdictSentences"
                    :key="i"
                    class="verdict-line"
                  >
                    {{ sentence }}
                  </p>
                </template>
                <p
                  v-else-if="!verdictComparable"
                  class="verdict-line is-muted"
                >
                  {{ runMeta.kind === 'raster' ? $t('robustnessLab.verdictNotComparableRaster') : $t('robustnessLab.verdictNotComparable') }}
                </p>
                <p
                  v-else
                  class="verdict-line is-muted"
                >
                  {{ $t('robustnessLab.verdictPending', { done: runMeta.done, total: runMeta.total }) }}
                </p>
              </div>
            </div>
            <div
              v-if="verdictComparable"
              class="verdict-stat"
            >
              <span class="verdict-stat-label">{{ $t('robustnessLab.verdictStatLabel') }}</span>
              <span class="verdict-stat-value mono-num">
                {{ verdictStatA }} <i>→</i> {{ verdictStatB }}
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
      </template>
      <EmptyState
        v-else
        variant="never"
        :title="$t('robustnessLab.noRun')"
      />
    </el-card>

    <!-- 攻击源码抽屉（rtl，宽 640；highlight.js python 高亮 + 行号 + #L{n} 行锚点） -->
    <el-drawer
      v-model="codeDrawer.open"
      direction="rtl"
      size="640px"
      :title="drawerTitle"
      class="code-drawer"
      destroy-on-close
    >
      <div
        v-loading="codeDrawer.loading"
        class="code-drawer-body"
      >
        <template v-if="drawerEntry">
          <div class="code-meta">
            <span class="code-params-label">{{ $t('robustnessLab.codeParamsLabel') }}</span>
            <span class="code-params mono-text">{{ formatMetaParams(drawerEntry.params_default) }}</span>
          </div>
          <AttackCodeViewer :code="drawerEntry.code" />
          <p class="code-note">
            {{ $t('robustnessLab.codeNote') }}
          </p>
          <p class="code-note">
            {{ $t('robustnessLab.codeAnchorHint') }}
          </p>
        </template>
        <p
          v-else-if="codeDrawer.error"
          class="code-error"
        >
          {{ $t('robustnessLab.codeLoadFailed') }}
        </p>
      </div>
    </el-drawer>

    <!-- 首入引导 ElTour（6 步，localStorage tour:v1:lab；遮罩=纯视觉聚焦层，不拦交互） -->
    <el-tour
      v-model="tourOpen"
      :mask="tourMask"
      @close="markTourSeen"
      @finish="markTourSeen"
    >
      <template #indicators="{ current, total }">
        <span
          v-for="i in total"
          :key="i"
          class="el-tour-indicator"
          :class="{ 'is-active': i - 1 === current }"
        />
        <button
          type="button"
          class="el-tour-skip"
          @click="closeTour"
        >
          {{ $t('robustnessLab.tourSkip') }}
        </button>
      </template>
      <el-tour-step
        v-for="(step, i) in tourSteps"
        :key="i"
        :target="step.target"
        :placement="step.placement"
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
  TrendCharts,
  VideoPlay,
} from '@element-plus/icons-vue'
// 强度扫描曲线：ECharts 按需注册（折线 + 提示/图例/网格），颜色走 chartInk
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import VChart from 'vue-echarts'

import HashText from '@/components/common/HashText.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { patchElTourOverlay } from '@/utils/a11yPatches'
import { useTheme } from '@/composables/useTheme.js'
import AttackCodeViewer from './AttackCodeViewer.vue'
import MetricGlossary from './MetricGlossary.vue'
import { getDataList } from '@/api/upload'
import {
  getRobustnessAttacksMeta,
  getRobustnessRun,
  getRobustnessRuns,
  startRobustnessRun,
} from '@/api/robustness'

use([CanvasRenderer, LineChart, TooltipComponent, LegendComponent, GridComponent])

const { t } = useI18n()
const { isDark } = useTheme()

// 与后端白名单同名同序（schemes 决定矩阵行、attacks 决定矩阵列）
const SCHEMES = ['legacy', 'dqim1']
const ATTACKS = ['none', 'translate', 'scale', 'vertex_drop', 'noise', 'simplify']
// 栅格 kind：宿主由后端程序化生成（512×512 GeoTIFF，data_id 忽略）；
// 攻击默认勾选含 blur（后端白名单支持，已实测 202 接受）
const RASTER_SCHEMES = ['lsb', 'dwt', 'histogram', 'blind', 'iw_dct']
const RASTER_ATTACKS = ['none', 'jpeg', 'resize', 'crop', 'rotate', 'noise', 'blur']
const RASTER_ONLY_ATTACKS = new Set(['jpeg', 'resize', 'crop', 'rotate', 'blur'])
// 实验规模上限（与后端 MAX_MATRIX_ROWS 一致）：格子数 × 试验次数 ≤ 200
const MAX_MATRIX_ROWS = 200

// 试验次数选项（1 = 文档化默认参数；>1 = 每格 N 次参数抖动试验，seed 固定可复现）
const TRIAL_OPTIONS = [1, 3, 5, 10]
// 强度扫描的试验次数选项/上限（与后端 SWEEP_MAX_TRIALS=5 一致）：每攻击 ×5 档，防行数爆炸
const SWEEP_TRIAL_OPTIONS = [1, 3, 5]
// 强度扫描：每攻击 5 档（与后端 SWEEP_TIER_COUNT 一致）
const SWEEP_TIERS = 5
// 扫描行数上限（与后端 MAX_SWEEP_ROWS=600 一致）
const MAX_SWEEP_ROWS = 600

const POLL_INTERVAL_MS = 5000
const TOUR_KEY = 'tour:v1:lab'
const COUNT_UP_MS = 160
const STAGGER_STEP_MS = 30

// ── 运行控制状态 ──
const runKind = ref('vector')
const runMode = ref('matrix')
const vectorDataList = ref([])
const dataLoading = ref(false)
const selectedDataId = ref(null)
const manualDataId = ref(null)
const selectedSchemes = ref([...SCHEMES])
const selectedAttacks = ref([...ATTACKS])
const selectedTrials = ref(1)
const startLoading = ref(false)

// 强度扫描态的选择器不变量：攻击不含 none（基线不参与梯度）、试验数钳制 ≤ 5
const sweepableAttacks = () => (runKind.value === 'raster' ? RASTER_ATTACKS : ATTACKS).filter((a) => a !== 'none')
const reconcileSweep = () => {
  if (runMode.value !== 'sweep') return
  const options = sweepableAttacks()
  const filtered = selectedAttacks.value.filter((a) => options.includes(a))
  selectedAttacks.value = filtered.length ? filtered : [options[0]]
  if (selectedTrials.value > 5) selectedTrials.value = 3
}

// 各 kind 分开记住勾选；切换"数据类型"时恢复对应 kind 的选择
const kindSelections = {
  vector: { schemes: [...SCHEMES], attacks: [...ATTACKS] },
  raster: { schemes: [...RASTER_SCHEMES], attacks: [...RASTER_ATTACKS] },
}
watch(runKind, (nv, ov) => {
  kindSelections[ov].schemes = [...selectedSchemes.value]
  kindSelections[ov].attacks = [...selectedAttacks.value]
  selectedSchemes.value = [...kindSelections[nv].schemes]
  selectedAttacks.value = [...kindSelections[nv].attacks]
  reconcileSweep()
})

// 切模式：进入强度扫描默认单算法（矢量 dqim1 / 栅格 lsb），并收敛扫描态选择
watch(runMode, (nv) => {
  if (nv === 'sweep') {
    selectedSchemes.value = [runKind.value === 'raster' ? 'lsb' : 'dqim1']
    reconcileSweep()
  }
})

// ── 文案按 kind 自适应：运行态 kind 优先，否则跟随发起卡所选 kind ──
// 矢量文案讲 QIM / 绝对坐标的机制边界，栅格文案讲各栅格算法的边界——
// 现文案默认在讲矢量（QIM 平移 / 缩放边界），栅格模式下语义不符。
const uiKind = computed(() => ((runMeta.value?.kind ?? runKind.value) === 'raster' ? 'raster' : 'vector'))
const subtitleText = computed(() =>
  t(uiKind.value === 'raster' ? 'robustnessLab.subtitleRaster' : 'robustnessLab.subtitle')
)

// 发起卡的方案/攻击/试验数选项随"数据类型"与"模式"切换
const trialOptions = computed(() => (runMode.value === 'sweep' ? SWEEP_TRIAL_OPTIONS : TRIAL_OPTIONS))
const kindSchemeOptions = computed(() => (runKind.value === 'raster' ? RASTER_SCHEMES : SCHEMES))
const kindAttackOptions = computed(() => {
  const base = runKind.value === 'raster' ? RASTER_ATTACKS : ATTACKS
  return runMode.value === 'sweep' ? base.filter((a) => a !== 'none') : base
})

// ── 历史列表状态 ──
const runs = ref([])
const runsLoading = ref(false)

// ── 当前 run（矩阵 + 结论 + KPI）状态 ──
const runMeta = ref(null)
const runRows = ref([])
const runSummary = ref([])
// 扫描 run 的档位表（后端 ladders：attack -> [{index,label,params}]）
const runLadders = ref({})
const detailLoading = ref(false)
let pollTimer = null

// 当前 run 是否为强度扫描（后端按「行有 strength_index」推导；旧数据缺省矩阵）
const isSweepRun = computed(() => runMeta.value?.mode === 'sweep')

// ── 可理解层状态 ──
const attacksMeta = ref(null)
const codeDrawer = reactive({ open: false, attack: null, kind: 'vector', loading: false, error: false })
const glossaryAnchor = ref(null)
const kpiGlossaryAnchor = ref(null)

// ── ElTour 状态 ──
const tourOpen = ref(false)
// 遮罩与质量页同规格（纯视觉聚焦层：全局 CSS 已保证不拦截点击、不盖侧栏/顶栏）
const tourMask = computed(() => (isDark.value
  ? { color: 'rgba(10,10,12,0.55)' }
  : { color: 'rgba(10,10,12,0.32)' }))

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
    mode: run.mode === 'sweep' ? 'sweep' : 'matrix',
    trials: run.trials ?? 1,
    done: run.done,
    total: run.total,
  }
  runRows.value = Array.isArray(run.rows) ? run.rows : []
  runSummary.value = Array.isArray(run.summary) ? run.summary : []
  runLadders.value = run.ladders && typeof run.ladders === 'object' ? run.ladders : {}
}

const loadRun = async (runId) => {
  if (!runId) return
  detailLoading.value = true
  try {
    const res = await getRobustnessRun(runId)
    const body = res.data
    if (body?.status && body.run) {
      applyRunPayload(body.run)
      if (body.run.done < body.run.total) {
        startPolling()
      } else {
        stopPolling()
        // 已完成 run：同步一次历史列表，避免行内"运行中 0/N"进度残留
        fetchRuns()
      }
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
  const isRaster = runKind.value === 'raster'
  const isSweep = runMode.value === 'sweep'
  let dataId = null
  if (!isRaster) {
    dataId = resolvedDataId.value
    if (dataId === null) {
      ElMessage.warning(t('robustnessLab.dataRequired'))
      return
    }
    if (!Number.isInteger(dataId) || dataId <= 0) {
      ElMessage.warning(t('robustnessLab.dataIdInvalid'))
      return
    }
  }
  // 扫描态的攻击集不含 none（基线不参与梯度；选择器已收敛，这里防御性过滤）
  const attacks = isSweep ? selectedAttacks.value.filter((a) => a !== 'none') : [...selectedAttacks.value]
  if (!selectedSchemes.value.length || !attacks.length) {
    ElMessage.warning(t('robustnessLab.comboRequired'))
    return
  }
  const tiers = isSweep ? SWEEP_TIERS : 1
  const cells = selectedSchemes.value.length * attacks.length * tiers
  if (isSweep) {
    if (cells * selectedTrials.value > MAX_SWEEP_ROWS) {
      ElMessage.warning(
        t('robustnessLab.sweepScaleLimit', {
          cells,
          trials: selectedTrials.value,
          total: cells * selectedTrials.value,
        })
      )
      return
    }
  } else if (cells * selectedTrials.value > MAX_MATRIX_ROWS) {
    ElMessage.warning(t('robustnessLab.scaleLimit', { cells, trials: selectedTrials.value }))
    return
  }

  startLoading.value = true
  try {
    const payload = {
      kind: runKind.value,
      mode: runMode.value,
      schemes: [...selectedSchemes.value],
      attacks,
      trials: selectedTrials.value,
    }
    // data_id 仅矢量必填；栅格宿主由后端程序化生成（data_id 忽略）
    if (!isRaster) payload.data_id = dataId
    const res = await startRobustnessRun(payload)
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

// 历史行 kind 徽章（后端列表已带 kind 字段；缺省按矢量）
const historyKind = (row) => (row.kind === 'raster' ? 'raster' : 'vector')

// 历史行 mode 徽章（后端按行有无 strength_index 推导；缺省按矩阵）
const historyMode = (row) => (row.mode === 'sweep' ? 'sweep' : 'matrix')

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
//  结果矩阵（行/列一律从 run rows 推导——按首次出现顺序 = 后端入库顺序，
//  不绑定任何 kind 的方案/攻击常量，未知值也能如实成表）
// ──────────────────────────────────────

const firstSeenValues = (key) => {
  const seen = []
  for (const r of runRows.value) {
    if (!seen.includes(r[key])) seen.push(r[key])
  }
  return seen
}

const matrixSchemes = computed(() => firstSeenValues('scheme'))

const matrixAttacks = computed(() => firstSeenValues('attack'))

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
//  强度扫描：曲线视图 + 崩塌点摘要
// ──────────────────────────────────────

// 扫描 run 的攻击列（按 rows 首现顺序；强度档行由后端 strength_index 标记）
const sweepAttacks = computed(() => firstSeenValues('attack'))

const sweepLadderFor = (attack) => {
  const ladder = runLadders.value[attack]
  return Array.isArray(ladder) && ladder.length ? ladder : null
}

// (attack|tier|scheme) -> { ok 成功数, done 已完成数, pending 待完成, error 异常, ncs : NC 列表 }
const sweepStats = computed(() => {
  const map = {}
  for (const r of runRows.value) {
    if (r.strength_index === null || r.strength_index === undefined) continue
    const key = `${r.attack}|${r.strength_index}|${r.scheme}`
    if (!map[key]) map[key] = { ok: 0, done: 0, pending: 0, error: 0, ncs: [] }
    const stat = map[key]
    if (r.decode_success === null) {
      stat.pending += 1
    } else {
      stat.done += 1
      if (r.decode_success) stat.ok += 1
      if (r.nc !== null && r.nc !== undefined) stat.ncs.push(Number(r.nc))
    }
    if (r.error) stat.error += 1
  }
  return map
})

const sweepStat = (attack, tierIndex, scheme) => sweepStats.value[`${attack}|${tierIndex}|${scheme}`] || null

// 档位成功率（0-100 整数；无已完成行 -> null，曲线留断点、tooltip 如实标注）
const sweepRate = (attack, tierIndex, scheme) => {
  const stat = sweepStat(attack, tierIndex, scheme)
  if (!stat || !stat.done) return null
  return Math.round((stat.ok / stat.done) * 100)
}

const sweepMeanNc = (attack, tierIndex, scheme) => {
  const stat = sweepStat(attack, tierIndex, scheme)
  if (!stat || !stat.ncs.length) return null
  return stat.ncs.reduce((a, b) => a + b, 0) / stat.ncs.length
}

// 异常格数（该攻击下有 error 的行；卡片脚注的诚实标注）
const sweepErrorCount = (attack) => runRows.value.filter((r) => r.attack === attack && r.error).length

// 图表配色（canvas 内无法用 CSS 变量，随 isDark 切换；对齐质量页 chartInk 体系）
const chartInk = computed(() =>
  isDark.value
    ? {
        axisLabel: '#a0a0ab',
        chartLabel: '#a0a0ab',
        tooltipBg: 'rgba(17,17,20,0.96)',
        tooltipBorder: 'rgba(94,106,210,0.35)',
        tooltipText: '#ededf0',
        chainTrack: 'rgba(255,255,255,0.08)',
        accent: '#5e6ad2',
        green: '#5cc08f',
        amber: '#d6a75c',
        neutral: '#6e6e7a',
      }
    : {
        axisLabel: '#666666',
        chartLabel: '#666666',
        tooltipBg: 'rgba(255,255,255,0.98)',
        tooltipBorder: '#eaeaea',
        tooltipText: '#0a0a0a',
        chainTrack: '#eaeaea',
        accent: '#0070f3',
        green: '#0e7a4e',
        amber: '#9a6b15',
        neutral: '#8f8f8f',
      }
)

const sweepPalette = computed(() => [
  chartInk.value.accent,
  chartInk.value.green,
  chartInk.value.amber,
  chartInk.value.neutral,
])

// 「强度档 -> 检出成功率」折线图：x=档位 label、y=成功率 0-100%，每方案一条线；
// tooltip 含档位实际参数、成功数/N 与 NC 均值；未完成/异常档如实标注
const sweepOption = (attack) => {
  const ink = chartInk.value
  const palette = sweepPalette.value
  const ladder =
    sweepLadderFor(attack) ||
    Array.from({ length: SWEEP_TIERS }, (_, i) => ({ index: i, label: `#${i + 1}`, params: {} }))
  const schemes = matrixSchemes.value
  return {
    grid: { left: 6, right: 16, top: 30, bottom: 24, containLabel: true },
    legend: { bottom: 0, itemWidth: 12, itemHeight: 8, textStyle: { fontSize: 11, color: ink.chartLabel } },
    tooltip: {
      trigger: 'axis',
      backgroundColor: ink.tooltipBg,
      borderColor: ink.tooltipBorder,
      textStyle: { color: ink.tooltipText, fontSize: 12 },
      formatter: (items) => {
        if (!items || !items.length) return ''
        const tierIndex = items[0].dataIndex
        const tier = ladder[tierIndex] || {}
        const lines = [`<div style="font-weight:600">${tier.label || `#${tierIndex + 1}`}</div>`]
        lines.push(`<div style="opacity:.75">${attackLabel(attack)} · ${formatParams(tier.params)}</div>`)
        schemes.forEach((scheme, idx) => {
          const stat = sweepStat(attack, tierIndex, scheme)
          const color = palette[idx % palette.length]
          const dot = `<span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${color};margin-right:6px;"></span>`
          if (!stat || (!stat.done && !stat.pending)) {
            lines.push(`<div>${dot}${schemeLabel(scheme)}: ${t('robustnessLab.sweepNoData')}</div>`)
            return
          }
          const mean = sweepMeanNc(attack, tierIndex, scheme)
          const meanText = mean === null ? '' : ` · ${t('robustnessLab.sweepMeanNc', { nc: mean.toFixed(3) })}`
          lines.push(
            `<div>${dot}${schemeLabel(scheme)}: ${t('robustnessLab.sweepSuccess', { ok: stat.ok, n: stat.done })}${meanText}</div>`
          )
          if (stat.pending) {
            lines.push(
              `<div style="opacity:.7;margin-left:14px">${t('robustnessLab.sweepPending', { n: stat.pending })}</div>`
            )
          }
          if (stat.error) {
            lines.push(`<div style="margin-left:14px">${t('robustnessLab.sweepErr', { n: stat.error })}</div>`)
          }
        })
        return lines.join('')
      },
    },
    xAxis: {
      type: 'category',
      data: ladder.map((tier) => tier.label),
      axisLabel: { fontSize: 10, color: ink.axisLabel, interval: 0, width: 96, overflow: 'truncate' },
      axisTick: { alignWithLabel: true },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      interval: 25,
      axisLabel: { fontSize: 10, color: ink.axisLabel, formatter: '{value}%' },
      splitLine: { lineStyle: { color: ink.chainTrack } },
    },
    series: schemes.map((scheme, idx) => ({
      name: schemeLabel(scheme),
      type: 'line',
      symbol: 'circle',
      symbolSize: 8,
      connectNulls: false,
      lineStyle: { width: 2.5, color: palette[idx % palette.length] },
      itemStyle: { color: palette[idx % palette.length] },
      data: ladder.map((_tier, tierIndex) => sweepRate(attack, tierIndex, scheme)),
    })),
  }
}

// 崩塌点摘要：每方案一行 = 首个「档内成功率 < 0.5」的档位（跨该 run 的攻击按档聚合；
// 无则全档存活），附每攻击各自的崩点 label 明细
const collapseLines = computed(() => {
  if (!isSweepRun.value) return []
  return matrixSchemes.value.map((scheme) => {
    let tierIndex = null
    let rateText = ''
    for (let i = 0; i < SWEEP_TIERS; i += 1) {
      const tierRows = runRows.value.filter(
        (r) => r.scheme === scheme && r.strength_index === i && r.decode_success !== null
      )
      if (!tierRows.length) continue
      const ok = tierRows.filter((r) => r.decode_success === true).length
      if (ok / tierRows.length < 0.5) {
        tierIndex = i
        rateText = `${ok}/${tierRows.length}`
        break
      }
    }
    const details = matrixAttacks.value.map((attack) => {
      const ladder = sweepLadderFor(attack) || []
      let hit = null
      for (let i = 0; i < SWEEP_TIERS; i += 1) {
        const rows = runRows.value.filter(
          (r) => r.scheme === scheme && r.attack === attack && r.strength_index === i && r.decode_success !== null
        )
        if (!rows.length) continue
        const ok = rows.filter((r) => r.decode_success === true).length
        if (ok / rows.length < 0.5) {
          hit = ladder[i]?.label || `#${i + 1}`
          break
        }
      }
      const text = hit ? t('robustnessLab.collapseAtLabel', { label: hit }) : t('robustnessLab.collapseAllAliveShort')
      return `${attackLabel(attack)} · ${text}`
    })
    return { scheme, name: schemeLabel(scheme), tierIndex, rateText, detail: details.join(' · ') }
  })
})

// ──────────────────────────────────────
//  攻击词典 / 源码抽屉
// ──────────────────────────────────────

// 攻击名/词典的 kind 归属：栅格专属攻击（jpeg/resize/crop/rotate/blur）始终按栅格，
// noise 按调用方上下文（默认=当前加载 run 的 kind；发起卡传表单选择的 kind）
const attackKind = (attack, kind = runMeta.value?.kind ?? 'vector') => {
  if (RASTER_ONLY_ATTACKS.has(attack)) return 'raster'
  if (attack === 'noise') return kind === 'raster' ? 'raster' : 'vector'
  return 'vector'
}

const attackLabel = (attack, kind) =>
  attackKind(attack, kind) === 'raster'
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

// KPI / 结论卡对比的一对方案：矢量 = 旧方案 vs D-QIM；栅格 = 该 run 的前两个方案（数据推导）
const kpiPair = computed(() => {
  if (runMeta.value?.kind === 'raster') {
    const pair = matrixSchemes.value.slice(0, 2)
    for (const s of RASTER_SCHEMES) {
      if (pair.length >= 2) break
      if (!pair.includes(s)) pair.push(s)
    }
    return pair
  }
  return ['legacy', 'dqim1']
})

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

  const [slotA, slotB] = kpiPair.value
  const slotAPresent = runRows.value.some((r) => r.scheme === slotA)
  const slotBPresent = runRows.value.some((r) => r.scheme === slotB)

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
    const rowsA = rowsByCell.value[`${slotA}|${a}`]
    const rowsB = rowsByCell.value[`${slotB}|${a}`]
    return (
      rowsA &&
      rowsA.length &&
      rowsB &&
      rowsB.length &&
      !rowsA.every((r) => r.decode_success === true) &&
      rowsB.every((r) => r.decode_success === true)
    )
  })

  // 基线注记：两方案一致 / 不一致取均值 / 仅单一方案
  let baselineNoteKind = null
  let baselineNoteScheme = null
  const baseA = slotAPresent ? cellMeanNc(slotA, 'none') : null
  const baseB = slotBPresent ? cellMeanNc(slotB, 'none') : null
  if (baseA !== null && baseB !== null) {
    baselineNoteKind = Math.abs(baseA - baseB) < 1e-9 ? 'same' : 'avg'
  } else if (baseA !== null || baseB !== null) {
    baselineNoteKind = 'scheme'
    baselineNoteScheme = baseA !== null ? slotA : slotB
  }

  return {
    baseline,
    baselineNoteKind,
    baselineNoteScheme,
    attacksCount,
    slotA: schemeSuccess(slotA),
    slotB: schemeSuccess(slotB),
    slotAFailNames: schemeFailNames(slotA),
    slotBFailNames: schemeFailNames(slotB),
    improved: improved.map((a) => attackLabel(a)),
  }
})

// KPI 数字 count-up（160ms，rAF；尊重 prefers-reduced-motion）
const kpiAnim = reactive({ baseline: null, s0: null, s1: null, win: null })
const animTokens = { baseline: 0, s0: 0, s1: 0, win: 0 }

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
    animateTo('s0', val ? val.slotA : null)
    animateTo('s1', val ? val.slotB : null)
    animateTo('win', val ? val.improved.length : null)
  },
  { immediate: true }
)

const baselineText = computed(() =>
  kpiAnim.baseline === null ? '—' : Number(kpiAnim.baseline).toFixed(4)
)

// idx=0/1 对应 kpiPair 的甲/乙方案卡片
const schemeValueText = (idx) => {
  const val = kpi.value
  if (!val) return '—'
  const n = idx === 0 ? kpiAnim.s0 : kpiAnim.s1
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
    scheme: schemeLabel(val.baselineNoteScheme),
  })
})

const schemeNoteText = (idx) => {
  const val = kpi.value
  if (!val) return ''
  const success = idx === 0 ? val.slotA : val.slotB
  if (success === null) return ''
  const fails = idx === 0 ? val.slotAFailNames : val.slotBFailNames
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

// 转败为胜卡 tooltip：栅格按 run 的方案对切换文案
const kpiWinDescText = computed(() => {
  if (runMeta.value?.kind === 'raster') {
    return t('robustnessLab.kpiWinDescRaster', {
      a: schemeLabel(kpiPair.value[0]),
      b: schemeLabel(kpiPair.value[1]),
    })
  }
  return t('robustnessLab.kpiWinDesc')
})

// ──────────────────────────────────────
//  对比结论（全部来自数据）
// ──────────────────────────────────────

const verdictComparable = computed(() => {
  const present = new Set(runRows.value.map((r) => r.scheme))
  const [slotA, slotB] = kpiPair.value
  return present.has(slotA) && present.has(slotB)
})

const verdictItems = computed(() => {
  const incomplete = (rows) => !rows || !rows.length || rows.some((r) => r.decode_success === null)
  const [slotA, slotB] = kpiPair.value
  return matrixAttacks.value.map((attack) => {
    const rowsA = rowsByCell.value[`${slotA}|${attack}`]
    const rowsB = rowsByCell.value[`${slotB}|${attack}`]
    if (incomplete(rowsA) || incomplete(rowsB)) {
      return { attack, kind: 'pending' }
    }
    // 多次试验时"成功" = 该格全部试验解码成功（trials=1 时与单行判定一致）
    const aOk = rowsA.every((r) => r.decode_success === true)
    const bOk = rowsB.every((r) => r.decode_success === true)
    if (!aOk && bOk) return { attack, kind: 'improved' }
    if (aOk && !bOk) return { attack, kind: 'regressed' }
    if (aOk && bOk) return { attack, kind: 'same-pass' }
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
  // 栅格 run 按 run 的方案对给句子（方案名来自数据推导）；矢量维持原文案
  const isRaster = runMeta.value?.kind === 'raster'
  const winner = schemeLabel(kpiPair.value[1])
  if (improved.length) {
    sentences.push(
      isRaster
        ? t('robustnessLab.verdictImprovedRaster', { scheme: winner, n: improved.length })
        : t('robustnessLab.verdictImproved', { n: improved.length })
    )
  }
  if (regressed.length) {
    sentences.push(
      isRaster
        ? t('robustnessLab.verdictRegressedRaster', { scheme: winner, n: regressed.length })
        : t('robustnessLab.verdictRegressed', { n: regressed.length })
    )
  }
  if (!improved.length && !regressed.length) {
    sentences.push(t('robustnessLab.verdictTie', { pass: samePass.length, fail: sameFail.length }))
  }
  return sentences
})

const verdictStatA = computed(() => {
  const val = kpi.value
  if (!val || val.slotA === null) return '—'
  return `${val.slotA}/${val.attacksCount}`
})

const verdictStatB = computed(() => {
  const val = kpi.value
  if (!val || val.slotB === null) return '—'
  return `${val.slotB}/${val.attacksCount}`
})

const tagText = (kind) => t(`robustnessLab.tag.${kind}`)

// ──────────────────────────────────────
//  实验流程图解
// ──────────────────────────────────────

const flowNodes = computed(() => [
  {
    name: t('robustnessLab.stepEmbed'),
    desc: t(uiKind.value === 'raster' ? 'robustnessLab.stepEmbedDescRaster' : 'robustnessLab.stepEmbedDesc'),
    icon: MagicStick,
  },
  { name: t('robustnessLab.stepAttack'), desc: t('robustnessLab.stepAttackDesc'), icon: Aim },
  { name: t('robustnessLab.stepExtract'), desc: t('robustnessLab.stepExtractDesc'), icon: Key },
  { name: t('robustnessLab.stepJudge'), desc: t('robustnessLab.stepJudgeDesc'), icon: CircleCheck },
])

const setupItems = computed(() => {
  // 宿主行随 run/表单的 kind 切换（栅格 = 程序化生成的 512×512 GeoTIFF）
  const isRaster = (runMeta.value?.kind ?? runKind.value) === 'raster'
  return [
    {
      label: t('robustnessLab.setupHostLabel'),
      text: runMeta.value
        ? t(isRaster ? 'robustnessLab.setupHostValueRaster' : 'robustnessLab.setupHostValue', {
            ref: runMeta.value.data_ref,
          })
        : t(isRaster ? 'robustnessLab.setupHostIdleRaster' : 'robustnessLab.setupHostIdle'),
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
  ]
})

// ──────────────────────────────────────
//  ElTour 首入引导（6 步；localStorage tour:v1:lab）
// ──────────────────────────────────────

// 目标锚点：按序取第一个命中的选择器（末级兜底 body）。
// 注意：优先锚定"小节标题"等小元素——整卡常是数百像素高的巨块，
// ElTour 2.7.4 的 flip/shift 无法把高块旁弹窗摆进视口（会跑到屏幕外）。
const tourTarget = (...selectors) => () => {
  for (const sel of selectors) {
    const el = document.querySelector(sel)
    if (el) return el
  }
  return document.body
}

const tourSteps = computed(() => [
  {
    // 首步总览：锚定 KPI 带 + placement=top——气泡整体悬在 KPI 数据之上
    // （bottom 恒定贴在 KPI 上沿，任何文案行数/语言都不会盖住 KPI 数值）
    target: tourTarget('#lab-kpi', '.control-grid'),
    placement: 'top',
    title: t('robustnessLab.tour1Title'),
    description: t(uiKind.value === 'raster' ? 'robustnessLab.tour1DescRaster' : 'robustnessLab.tour1Desc'),
  },
  {
    target: tourTarget('#lab-kpi', '.control-grid'),
    title: t('robustnessLab.tour2Title'),
    description: t(uiKind.value === 'raster' ? 'robustnessLab.tour2DescRaster' : 'robustnessLab.tour2Desc'),
  },
  {
    target: tourTarget('#lab-run .card-title', '#lab-run'),
    title: t('robustnessLab.tour3Title'),
    description: t('robustnessLab.tour3Desc'),
  },
  {
    target: tourTarget('#lab-history .card-title', '#lab-history'),
    title: t('robustnessLab.tour4Title'),
    description: t('robustnessLab.tour4Desc'),
  },
  {
    target: tourTarget('#lab-matrix .card-title', '#lab-matrix'),
    title: t('robustnessLab.tour5Title'),
    description: t('robustnessLab.tour5Desc'),
  },
  {
    target: tourTarget('#lab-verdict', '#lab-matrix .card-title', '#lab-matrix'),
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
  tourOpen.value = true
}

// 「跳过」：收起引导（watch 里统一记 tour:v1:lab 已看）
const closeTour = () => {
  tourOpen.value = false
}

watch(tourOpen, (open) => {
  // EP 上游补丁：引导打开后修正 el-tour 弹层的 banner 地标 / aria-level 缺陷
  // （axe: landmark-no-duplicate-banner / landmark-unique / aria-required-attr，详见 utils/a11yPatches.js）
  if (open) patchElTourOverlay()
  else markTourSeen()
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
    kind: runMeta.value.kind,
    mode: runMeta.value.mode,
    data_ref: runMeta.value.data_ref,
    created_at: runMeta.value.created_at,
    trials: runMeta.value.trials,
    done: runMeta.value.done,
    total: runMeta.value.total,
    summary: runSummary.value,
    ladders: runLadders.value,
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

.page-header h1 {
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
  font-weight: 400;
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

.form-hint.is-kind {
  margin-top: 0;
  line-height: 1.6;
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

/* 历史行 kind 徽章（矢量 / 栅格） */
.kind-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 9px;
  font-size: 12px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.kind-badge.is-vector {
  color: var(--text-secondary);
  background: var(--tint-neutral-bg);
}

.kind-badge.is-raster {
  color: var(--primary-700);
  background: var(--primary-50);
}

/* 历史行 mode 徽章（单点矩阵 / 强度扫描） */
.mode-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 9px;
  font-size: 12px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.mode-badge.is-matrix {
  color: var(--text-secondary);
  background: var(--tint-neutral-bg);
}

.mode-badge.is-sweep {
  color: var(--primary-700);
  background: var(--primary-50);
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
  font-weight: 400;
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
.scheme-name.is-blind,
.scheme-name.is-iw_dct {
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
  font-weight: 400;
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

.cell-tip .tip-trial-error {
  color: inherit;
  opacity: 0.72;
  font-size: 11.5px;
  line-height: 1.55;
  word-break: break-all;
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

/* ── 攻击源码抽屉（highlight.js 高亮查看器自绘，此处只留元信息行） ── */
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

/* ── 强度扫描：曲线网格 + 崩塌点摘要 ── */
.sweep-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin: 4px 0 16px;
}

@media (max-width: 1100px) {
  .sweep-grid {
    grid-template-columns: 1fr;
  }
}

.sweep-card {
  padding: 12px 14px 8px;
  background: var(--bg-primary);
  /* §4.11 ring 描边（与 KPI 卡一致） */
  box-shadow: var(--card-ring);
  border-radius: var(--radius-md);
}

.sweep-card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.sweep-attack-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.sweep-card-note {
  font-size: 11.5px;
  color: var(--text-tertiary);
}

.sweep-chart {
  width: 100%;
  height: 230px;
}

.sweep-anomaly {
  margin: 2px 0 6px;
  font-size: 12px;
  color: var(--tint-warning-text);
}

.collapse-line {
  margin: 2px 0 8px;
}

.collapse-scheme {
  font-weight: 500;
  color: var(--text-primary);
}

.collapse-alive {
  margin-left: 8px;
  color: var(--tint-success-text);
}

.collapse-hit {
  margin-left: 8px;
  color: var(--text-secondary);
}

.collapse-detail {
  margin: 2px 0 0 14px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}
</style>
