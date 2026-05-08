/**
 * @module api/auth
 * Authentication API — login, register, token refresh
 */
import axios from '@/utils/Axios'

/**
 * Authenticate a user with username, password, and role.
 * @param {Object} payload
 * @param {string} payload.username
 * @param {string} payload.password
 * @param {string} payload.role - 'admin' | 'employee'
 * @returns {Promise<AxiosResponse>} Response containing access_token, refresh_token, user info
 */
export const login = (payload) => axios.post('/api/login', payload)

/**
 * Register a new user (FormData supports avatar upload).
 * @param {FormData} formData - name, employeeId, idNumber, phone, password, confirmPassword, avatar
 * @returns {Promise<AxiosResponse>}
 */
export const register = (formData) => axios.post('/api/register', formData)

/**
 * Refresh the JWT access token.
 * @param {Object} data
 * @param {string} data.refresh_token
 * @returns {Promise<AxiosResponse>} Response containing new access_token and refresh_token
 */
export const refreshToken = (data) => axios.post('/api/refresh-token', data)
