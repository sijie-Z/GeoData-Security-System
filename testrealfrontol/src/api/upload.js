/**
 * @module api/upload
 * Data upload operations — SHP file upload
 */
import axios from '@/utils/Axios'

/**
 * Upload SHP data with metadata.
 * @param {FormData} formData - file, data_alias, category, data_introduction
 * @param {Object} [config] - Additional axios config (e.g., onUploadProgress, headers)
 * @returns {Promise<AxiosResponse>}
 */
export const uploadShpData = (formData, config = {}) =>
  axios.post('/api/upload_shp_data', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    ...config,
  })
