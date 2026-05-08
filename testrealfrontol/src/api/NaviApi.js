/**
 * @module api/NaviApi
 * Navigation API — admin and employee navigation tree/menu
 */
import axios from '@/utils/Axios'

/**
 * Get admin navigation item by ID.
 * @param {number|string} id
 * @returns {Promise<AxiosResponse>}
 */
const getAdmById = (id) => axios.get(`/api/admin/nav/getById?id=${id}`)

/**
 * Get admin navigation items by parent ID.
 * @param {number|string} parent_id
 * @returns {Promise<AxiosResponse>}
 */
const getAdmListByParentId = (parent_id) => axios.get(`/api/admin/nav/getListByParentId?parent_id=${parent_id}`)

/**
 * Get admin navigation subtree by ID.
 * @param {number|string} id
 * @returns {Promise<AxiosResponse>}
 */
const getAdmAllById = (id) => axios.get(`/api/admin/nav/list?id=${id}`)

/**
 * Get full admin navigation tree.
 * @returns {Promise<Array>} Navigation tree array
 */
const getAdmAll = () => {
  return axios.get('/api/admin/nav/tree').then(response => {
    if (response.data.status) {
      return response.data.data
    } else {
      throw new Error(response.data.msg)
    }
  })
}

/**
 * Get employee navigation item by ID.
 * @param {number|string} id
 * @returns {Promise<AxiosResponse>}
 */
const getEmpById = (id) => axios.get(`/api/employee/nav/getById?id=${id}`)

/**
 * Get employee navigation items by parent ID.
 * @param {number|string} parent_id
 * @returns {Promise<AxiosResponse>}
 */
const getEmpListByParentId = (parent_id) => axios.get(`/api/employee/nav/getListByParentId?parent_id=${parent_id}`)

/**
 * Get employee navigation subtree by ID.
 * @param {number|string} id
 * @returns {Promise<AxiosResponse>}
 */
const getEmpAllById = (id) => axios.get(`/api/employee/nav/list?id=${id}`)

/**
 * Get full employee navigation tree.
 * @returns {Promise<Array>} Navigation tree array
 */
const getEmpAll = () => {
  return axios.get('/api/employee/nav/tree').then(response => {
    if (response.data.status) {
      return response.data.data
    } else {
      throw new Error(response.data.msg)
    }
  })
}

export default {
  getAdmById, getAdmListByParentId, getAdmAllById, getAdmAll,
  getEmpById, getEmpListByParentId, getEmpAllById, getEmpAll
}
