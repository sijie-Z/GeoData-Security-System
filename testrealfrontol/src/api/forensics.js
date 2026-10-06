/**
 * @module api/forensics
 * Delivery forensics — signature verification, leak tracing, delivery ledger,
 * anchor batch building and signing-key info
 */
import axios from '@/utils/Axios'

// verify/trace 需逐条提取水印，真机实测约 60-100s，远超共享实例默认 30s 超时，故单独放宽到 300s。
// FormData 走 multipart（浏览器自动补 boundary）；JSON（如 {qr_text}）保持实例默认头。
const longConfig = (data) => ({
  timeout: 300000,
  ...(data instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {})
})

// ──────────────────────────────────────
//  Verification / Tracing
// ──────────────────────────────────────

/**
 * Verify a leaked copy (uploaded file or pasted QR text) against the delivery ledger.
 * Never returns PII — use traceForensics for the full provenance chain.
 * @param {FormData|Object} data - FormData with 'file' (zip/shp/shx/dbf/prj/tif/tiff/png/jpg), or { qr_text: '...' }
 * @returns {Promise<AxiosResponse>}
 */
export const verifyForensics = (data) => axios.post('/api/forensics/verify', data, longConfig(data))

/**
 * Verify and trace a leaked copy back to the applicant (admin only).
 * Returns all verifyForensics fields plus provenance (applicant, approvals, downloads).
 * @param {FormData|Object} data - FormData with 'file', or { qr_text: '...' }
 * @returns {Promise<AxiosResponse>}
 */
export const traceForensics = (data) => axios.post('/api/forensics/trace', data, longConfig(data))

// ──────────────────────────────────────
//  Delivery Ledger
// ──────────────────────────────────────

/**
 * List deliveries, optionally filtered by application ID.
 * @param {Object} [params]
 * @param {number|string} [params.application_id]
 * @returns {Promise<AxiosResponse>}
 */
export const getDeliveries = (params) => axios.get('/api/forensics/deliveries', { params })

/**
 * Get a single delivery with its event chain and anchor info.
 * @param {string} uuid - Delivery UUID
 * @returns {Promise<AxiosResponse>}
 */
export const getDeliveryDetail = (uuid) => axios.get(`/api/forensics/deliveries/${uuid}`)

/**
 * Build an anchor batch over pending delivery chain roots (admin).
 * @param {Object} [body]
 * @param {'ots'|'evm'} [body.provider] - anchor backend, default 'ots' (OpenTimestamps);
 *   'evm' anchors to the Sepolia AnchorRegistry (PENDING + error when not configured)
 * @returns {Promise<AxiosResponse>}
 */
export const buildAnchorBatch = (body = {}) => axios.post('/api/forensics/anchor/build', body)

/**
 * List anchor batches (存证中心 ledger), newest first.
 * @param {Object} [params]
 * @param {number} [params.page] - 1-based, default 1
 * @param {number} [params.page_size] - default 20, clamped to <=100
 * @returns {Promise<AxiosResponse>} {status, anchors:[…], summary:{total,
 *   by_provider, by_status}, pages:{total, page, page_size}}
 */
export const getAnchors = (params) => axios.get('/api/forensics/anchors', { params })

/**
 * Get one anchor batch: full record + events_digest (snapshot coverage).
 * @param {string} batchId
 * @returns {Promise<AxiosResponse>}
 */
export const getAnchorDetail = (batchId) => axios.get(`/api/forensics/anchors/${batchId}`)

/**
 * Download the stored evidence pack for a batch (.ots / .proof.json).
 * @param {string} batchId
 * @returns {Promise<AxiosResponse>} blob response
 */
export const downloadAnchorProof = (batchId) =>
  axios.get(`/api/forensics/anchors/${batchId}/proof`, { responseType: 'blob' })

// ──────────────────────────────────────
//  Signing Key
// ──────────────────────────────────────

/**
 * Get the watermark signing key info (kid, algorithm, fingerprint, public key).
 * @returns {Promise<AxiosResponse>}
 */
export const getKeyInfo = () => axios.get('/api/forensics/keyinfo')

/**
 * Get server-side delivery aggregation stats for the quality dashboard:
 * status distribution, anchor states, chain validity and recent deliveries.
 * @returns {Promise<AxiosResponse>} {status, stats:{total, by_status, by_algorithm,
 *   by_data_type, downloaded_count, anchor:{submitted,pending,none},
 *   chain_valid_count, chain_checked, recent:[…]}}
 */
export const getDeliveryStats = () => axios.get('/api/forensics/deliveries/stats')
