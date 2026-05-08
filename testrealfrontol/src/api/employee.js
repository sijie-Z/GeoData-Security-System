/**
 * @module api/employee
 * Employee operations — profile, applications, notifications, operation history, dashboard
 */
import axios from '@/utils/Axios'

// ──────────────────────────────────────
//  Dashboard
// ──────────────────────────────────────

/**
 * Get employee dashboard statistics and charts data.
 * @returns {Promise<AxiosResponse>}
 */
export const getDashboard = () => axios.get('/api/employee/dashboard')

// ──────────────────────────────────────
//  Applications
// ──────────────────────────────────────

/**
 * Get current employee's applications (paginated).
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @param {string} [params.userNumber]
 * @returns {Promise<AxiosResponse>}
 */
export const getMyApplications = (params) => axios.get('/api/get_applications', { params })

/**
 * Get current employee's approved applications.
 * @param {Object} [params]
 * @returns {Promise<AxiosResponse>}
 */
export const getApprovedApplications = (params) => axios.get('/api/get_approved_applications', { params })

/**
 * Submit a new data application.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const submitApplication = (data) => axios.post('/api/submit_application', data)

/**
 * Withdraw (cancel) a pending application.
 * @param {number|string} applicationId
 * @returns {Promise<AxiosResponse>}
 */
export const withdrawApplication = (applicationId) =>
  axios.put(`/api/applications/${applicationId}/withdraw`)

// ──────────────────────────────────────
//  Profile
// ──────────────────────────────────────

/**
 * Get current employee's profile.
 * @returns {Promise<AxiosResponse>}
 */
export const getProfile = () => axios.get('/api/employee/profile')

/**
 * Update current employee's profile (FormData for photo upload).
 * @param {FormData} formData
 * @returns {Promise<AxiosResponse>}
 */
export const updateProfile = (formData) => axios.put('/api/employee/profile', formData)

/**
 * Change current employee's password.
 * @param {Object} data - { oldPassword, newPassword }
 * @returns {Promise<AxiosResponse>}
 */
export const changePassword = (data) => axios.put('/api/employee/password', data)

/**
 * Get employee photo as blob.
 * @param {string} employeeNumber
 * @param {Object} [config] - Additional axios config (e.g., responseType)
 * @returns {Promise<AxiosResponse>}
 */
export const getPhoto = (employeeNumber, config = {}) =>
  axios.get(`/api/employee/photo/${employeeNumber}`, config)

// ──────────────────────────────────────
//  Notifications
// ──────────────────────────────────────

/**
 * Get paginated notifications for the current employee.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @param {boolean} [params.unread_only]
 * @returns {Promise<AxiosResponse>}
 */
export const getNotifications = (params) => axios.get('/api/employee/notifications', { params })

/**
 * Mark a notification as read.
 * @param {number|string} id - Notification ID
 * @returns {Promise<AxiosResponse>}
 */
export const markNotificationRead = (id) => axios.post(`/api/employee/notifications/${id}/read`)

// ──────────────────────────────────────
//  Operation History / Logs
// ──────────────────────────────────────

/**
 * Get current employee's operation logs (paginated).
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getMyLogs = (params) => axios.get('/api/employee/my-logs', { params })

// ──────────────────────────────────────
//  Downloads
// ──────────────────────────────────────

/**
 * Download approved data as ZIP (blob response).
 * @param {Object} data
 * @returns {Promise<AxiosResponse>} Blob response with content-disposition header
 */
export const downloadFile = (data) => axios.post('/api/download/emp_download_zip', data, { responseType: 'blob' })

/**
 * Request a download token for an application.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const requestDownloadToken = (data) => axios.post('/api/download/request-token', data)

/**
 * Record a file download event.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const recordDownloadFile = (data) => axios.post('/api/record_download_file', data)
