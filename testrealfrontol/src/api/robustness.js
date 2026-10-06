/**
 * @module api/robustness
 * Robustness experiment matrix — run control, history list and per-run
 * result rows (admin only).
 */
import axios from '@/utils/Axios'

// start 命中的是同步分支：解析数据源文件 + 预插 run 行，随后立即返回 202。
// 保持显式 30s（与共享实例默认一致），避免矩阵跑动后被误当成"接口超时"。
const START_CONFIG = { timeout: 30000 }

/**
 * List recent robustness runs (grouped by run_id, newest first).
 * @param {Object} [params] - Query parameters, e.g. { page: 1, per_page: 10 }
 * @returns {Promise<AxiosResponse>} data: { status, runs[], page, per_page, total_runs }
 */
export const getRobustnessRuns = (params) => axios.get('/api/robustness/runs', { params })

/**
 * Get one run's progress and per-(scheme, attack) result rows.
 * @param {string} runId
 * @returns {Promise<AxiosResponse>} data: { status, run: { run_id, data_ref, created_at, done, total, rows[] } }
 */
export const getRobustnessRun = (runId) => axios.get(`/api/robustness/runs/${runId}`)

/**
 * Queue one (scheme x attack) matrix run against a dataset.
 * Returns 202 with { run_id, total }; 409 when a run is already in flight.
 * @param {Object} data - { data_id: int, schemes?: string[], attacks?: string[] }
 * @returns {Promise<AxiosResponse>}
 */
export const startRobustnessRun = (data) => axios.post('/api/robustness/run', data, START_CONFIG)
