/**
 * @module api/data_viewing_api
 * @deprecated Use {@link module:api/data} instead for all data viewing operations.
 * Kept for backward compatibility.
 */
import axios from '@/utils/Axios'

/**
 * Get data record by ID.
 * @param {number|string} id
 * @returns {Promise<AxiosResponse>}
 */
const getById = (id) => axios.get(`/api/data_viewing/getById?id=${id}`)

/**
 * Get paginated data list.
 * @param {number} page
 * @param {number} pageSize
 * @returns {Promise<AxiosResponse>}
 */
const pageList = (page, pageSize) => axios.get(`/api/data_viewing/pageList?page=${page}&pageSize=${pageSize}`)

export default { getById, pageList }
