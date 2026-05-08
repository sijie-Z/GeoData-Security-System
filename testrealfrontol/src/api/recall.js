/**
 * @module api/recall
 * Recall proposal management — list, create, vote, detail
 */
import axios from '@/utils/Axios'

/**
 * Get paginated list of recall proposals.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @param {string} [params.status] - Filter by status
 * @returns {Promise<AxiosResponse>}
 */
export const getRecallProposals = (params) => axios.get('/api/recall/list', { params })

/**
 * Create a new recall proposal.
 * @param {Object} data
 * @param {number} data.application_id - The application to recall
 * @param {string} data.reason - Reason for recall
 * @returns {Promise<AxiosResponse>}
 */
export const createRecall = (data) => axios.post('/api/recall/create', data)

/**
 * Cast a vote on a recall proposal.
 * @param {number|string} id - Recall proposal ID
 * @param {Object} data
 * @param {string} data.vote - 'approve' | 'reject'
 * @returns {Promise<AxiosResponse>}
 */
export const voteRecall = (id, data) => axios.post(`/api/recall/${id}/vote`, data)

/**
 * Get detailed information about a single recall proposal.
 * @param {number|string} id - Recall proposal ID
 * @returns {Promise<AxiosResponse>}
 */
export const getRecallDetail = (id) => axios.get(`/api/recall/${id}`)
