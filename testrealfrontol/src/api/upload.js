/**
 * @module api/upload
 * Data upload and management operations
 */
import axios from '@/utils/Axios'

/**
 * Upload SHP data with metadata.
 * @param {FormData} formData - file, data_alias, category, data_introduction
 * @param {Object} [config] - Additional axios config (e.g., onUploadProgress)
 * @returns {Promise<AxiosResponse>}
 */
export const uploadShpData = (formData, config = {}) =>
  axios.post('/api/upload_shp_data', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...config,
  })

/**
 * Upload Raster data with metadata.
 * @param {FormData} formData - file, data_alias, category, data_introduction
 * @param {Object} [config] - Additional axios config (e.g., onUploadProgress)
 * @returns {Promise<AxiosResponse>}
 */
export const uploadRasterData = (formData, config = {}) =>
  axios.post('/api/upload_raster_data', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...config,
  })

/**
 * Get data list (vector or raster) with pagination.
 * @param {string} dataType - 'vector' or 'raster'
 * @param {Object} params - { page, pageSize, keyword }
 * @returns {Promise<AxiosResponse>}
 */
export const getDataList = (dataType, params = {}) =>
  axios.get(`/api/data/${dataType}`, { params })

/**
 * Get single data record detail.
 * @param {string} dataType - 'vector' or 'raster'
 * @param {number} dataId
 * @returns {Promise<AxiosResponse>}
 */
export const getDataDetail = (dataType, dataId) =>
  axios.get(`/api/data/${dataType}/${dataId}`)

/**
 * Update data record metadata.
 * @param {string} dataType - 'vector' or 'raster'
 * @param {number} dataId
 * @param {Object} data - { alias, introduction, data_source }
 * @returns {Promise<AxiosResponse>}
 */
export const updateData = (dataType, dataId, data) =>
  axios.put(`/api/data/${dataType}/${dataId}`, data)

/**
 * Delete a data record.
 * @param {string} dataType - 'vector' or 'raster'
 * @param {number} dataId
 * @returns {Promise<AxiosResponse>}
 */
export const deleteData = (dataType, dataId) =>
  axios.delete(`/api/data/${dataType}/${dataId}/delete`)

/**
 * Manually publish data to GeoServer.
 * @param {Object} data - { data_type, data_id }
 * @returns {Promise<AxiosResponse>}
 */
export const publishToGeoServer = (data) =>
  axios.post('/api/geoserver/publish', data)

/**
 * Check GeoServer connection status.
 * @returns {Promise<AxiosResponse>}
 */
export const getGeoServerStatus = () =>
  axios.get('/api/geoserver/status')
