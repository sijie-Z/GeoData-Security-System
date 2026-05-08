/**
 * @module api/data
 * Data viewing, SHP data list, raster data, map search, geocoding
 */
import axios from '@/utils/Axios'

/**
 * Get data record by ID.
 * @param {number|string} id
 * @returns {Promise<AxiosResponse>}
 */
export const getDataById = (id) => axios.get(`/api/data_viewing/getById?id=${id}`)

/**
 * Get paginated data list.
 * @param {number} page
 * @param {number} pageSize
 * @returns {Promise<AxiosResponse>}
 */
export const getPageList = (page, pageSize) =>
  axios.get(`/api/data_viewing/pageList?page=${page}&pageSize=${pageSize}`)

/**
 * General data viewing with filters.
 * @param {Object} params - Query parameters
 * @returns {Promise<AxiosResponse>}
 */
export const dataViewing = (params) => axios.get('/api/data_viewing', { params })

/**
 * Vector data viewing with filters.
 * @param {Object} params - Query parameters
 * @returns {Promise<AxiosResponse>}
 */
export const vectorDataViewing = (params) => axios.get('/api/vector_data_viewing', { params })

/**
 * Raster data viewing with filters.
 * @param {Object} params - Query parameters
 * @returns {Promise<AxiosResponse>}
 */
export const rasterDataViewing = (params) => axios.get('/api/raster_data_viewing', { params })

/**
 * Search map data.
 * @param {Object} params
 * @param {string} params.keyword - Search keyword
 * @returns {Promise<AxiosResponse>}
 */
export const mapSearch = (params) => axios.get('/api/map/search', { params })

/**
 * Geocoding search by keyword.
 * @param {Object} params
 * @param {string} params.keyword - Location keyword
 * @returns {Promise<AxiosResponse>}
 */
export const geocodingSearch = (params) => axios.get('/api/geocoding/search', { params })
