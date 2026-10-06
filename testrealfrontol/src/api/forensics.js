/**
 * @module api/forensics
 * Delivery forensics — signature verification, leak tracing, delivery ledger,
 * anchor batch building and signing-key info
 */
import axios from '@/utils/Axios'

// FormData 走 multipart（浏览器自动补 boundary）；JSON（如 {qr_text}）保持实例默认头
const formConfig = (data) =>
  data instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {}

// ──────────────────────────────────────
//  Verification / Tracing
// ──────────────────────────────────────

/**
 * Verify a leaked copy (uploaded file or pasted QR text) against the delivery ledger.
 * Never returns PII — use traceForensics for the full provenance chain.
 * @param {FormData|Object} data - FormData with 'file' (zip/shp/shx/dbf/prj/tif/tiff/png/jpg), or { qr_text: '...' }
 * @returns {Promise<AxiosResponse>}
 */
export const verifyForensics = (data) => axios.post('/api/forensics/verify', data, formConfig(data))

/**
 * Verify and trace a leaked copy back to the applicant (admin only).
 * Returns all verifyForensics fields plus provenance (applicant, approvals, downloads).
 * @param {FormData|Object} data - FormData with 'file', or { qr_text: '...' }
 * @returns {Promise<AxiosResponse>}
 */
export const traceForensics = (data) => axios.post('/api/forensics/trace', data, formConfig(data))

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
 * @returns {Promise<AxiosResponse>}
 */
export const buildAnchorBatch = () => axios.post('/api/forensics/anchor/build')

// ──────────────────────────────────────
//  Signing Key
// ──────────────────────────────────────

/**
 * Get the watermark signing key info (kid, algorithm, fingerprint, public key).
 * @returns {Promise<AxiosResponse>}
 */
export const getKeyInfo = () => axios.get('/api/forensics/keyinfo')
