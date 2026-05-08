/**
 * @module api/watermark
 * Watermark operations — QR generation, embedding, extraction, preview,
 * batch operations, verification records, raster watermark, CRMark
 */
import axios from '@/utils/Axios'

// ──────────────────────────────────────
//  Watermark Generation
// ──────────────────────────────────────

/**
 * Generate a vector watermark for an application.
 * @param {Object} data - Application info for watermark generation
 * @returns {Promise<AxiosResponse>}
 */
export const generateWatermark = (data) => axios.post('/api/generate_watermark', data)

/**
 * Generate a raster watermark for an application.
 * @param {Object} data - Application info for raster watermark generation
 * @returns {Promise<AxiosResponse>}
 */
export const generateRasterWatermark = (data) => axios.post('/api/generate_raster_watermark', data)

/**
 * Get applications eligible for watermark generation (admin1 stage, vector).
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getApplicationsGenerateWatermark = (params) =>
  axios.get('/api/adm1_get_applications_generate_watermark', { params })

/**
 * Get applications eligible for raster watermark generation (admin1 stage).
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getRasterApplicationsGenerateWatermark = (params) =>
  axios.get('/api/adm1_get_raster_applications_generate_watermark', { params })

// ──────────────────────────────────────
//  Watermark Embedding
// ──────────────────────────────────────

/**
 * Get applications ready for watermark embedding (admin2 stage).
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getEmbeddingApplications = (params) =>
  axios.get('/api/adm2_embedding_watermark_applications', { params })

/**
 * Embed a vector watermark into data (returns ZIP blob).
 * @param {Object} data
 * @param {number} data.application_id
 * @param {string} data.data_id
 * @param {string} data.applicant_user_number
 * @param {string} data.embed_person
 * @param {string} data.applicant
 * @returns {Promise<AxiosResponse>} Blob response with content-disposition header
 */
export const embedWatermark = (data) => axios.post('/api/embedding_watermark', data, { responseType: 'blob' })

/**
 * Dispatch raster watermark embedding.
 * @param {Object} data
 * @param {number} data.application_id
 * @param {string} data.algorithm - 'lsb' | 'dwt' | 'histogram'
 * @returns {Promise<AxiosResponse>}
 */
export const embedDispatch = (data) => axios.post('/api/admin/embed_dispatch', data)

/**
 * Preview watermark embedding capacity for an application.
 * @param {Object} data
 * @param {number} data.application_id
 * @returns {Promise<AxiosResponse>}
 */
export const previewWatermark = (data) => axios.post('/api/watermark/preview', data)

// ──────────────────────────────────────
//  Watermark Extraction
// ──────────────────────────────────────

/**
 * Extract a watermark from uploaded vector data (multipart upload via el-upload).
 * Note: The extraction upload uses the URL `/api/vector/extract` directly
 * with the el-upload component. This function is provided for programmatic use.
 * @param {FormData} data - ZIP file + application_id
 * @returns {Promise<AxiosResponse>}
 */
export const extractWatermark = (data) => axios.post('/api/vector/extract', data)

// ──────────────────────────────────────
//  QR Code
// ──────────────────────────────────────

/**
 * Get QR code data for an application.
 * @param {number|string} id - Application ID
 * @returns {Promise<AxiosResponse>}
 */
export const getApplicationQRCode = (id) => axios.get(`/api/application/${id}/qrcode`)

/**
 * Get QR code image for an application (blob).
 * @param {number|string} id - Application ID
 * @returns {Promise<AxiosResponse>} Blob response
 */
export const getApplicationQRImage = (id) =>
  axios.get(`/api/application/${id}/qrcode-image`, { responseType: 'blob' })

// ──────────────────────────────────────
//  SHP / Raster Applications
// ──────────────────────────────────────

/**
 * Get SHP applications for watermark processing.
 * @param {Object} [params]
 * @returns {Promise<AxiosResponse>}
 */
export const getShpApplications = (params) => axios.get('/api/adm1_get_shp_applications', { params })

/**
 * Get raster applications for watermark processing.
 * @param {Object} [params]
 * @returns {Promise<AxiosResponse>}
 */
export const getRasterApplications = (params) => axios.get('/api/adm1_get_raster_applications', { params })

// ──────────────────────────────────────
//  Raster Watermark (CRMark)
// ──────────────────────────────────────

/**
 * Preview a raster file.
 * @param {Object} data - { file_path } or { application_id }
 * @returns {Promise<AxiosResponse>}
 */
export const previewRaster = (data) => axios.post('/api/raster/preview', data)

/**
 * Embed watermark using CRMark algorithm.
 * @param {Object} data
 * @param {number} data.application_id
 * @returns {Promise<AxiosResponse>}
 */
export const crmarkEmbed = (data) => axios.post('/api/crmark/embed', data)

/**
 * Recover original image from stego image (blob response).
 * @param {Object} data
 * @param {string} data.stego_path
 * @param {string} data.wm_map_path
 * @returns {Promise<AxiosResponse>} Blob response
 */
export const crmarkRecover = (data) => axios.post('/api/crmark/recover', data, { responseType: 'blob' })

/**
 * Decode watermark from stego image (blob response).
 * @param {Object} data
 * @param {string} data.stego_path
 * @param {string} data.wm_map_path
 * @param {string} data.wm_meta_path
 * @returns {Promise<AxiosResponse>} Blob response
 */
export const crmarkDecode = (data) => axios.post('/api/crmark/decode', data, { responseType: 'blob' })

// ──────────────────────────────────────
//  Verification Records
// ──────────────────────────────────────

/**
 * Get paginated watermark verification records.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getVerificationRecords = (params) =>
  axios.get('/api/watermark/verification_records', { params })
