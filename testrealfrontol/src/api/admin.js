/**
 * @module api/admin
 * Admin operations — dashboard, employee CRUD, approval flows, logs,
 * announcements, admin application management
 */
import axios from '@/utils/Axios'

// ──────────────────────────────────────
//  Dashboard
// ──────────────────────────────────────

/**
 * Get admin dashboard statistics.
 * @returns {Promise<AxiosResponse>}
 */
export const getDashboard = () => axios.get('/api/admin/dashboard')

// ──────────────────────────────────────
//  Employee CRUD
// ──────────────────────────────────────

/**
 * Get paginated employee list.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getEmployeeList = (params) => axios.get('/api/adm/get_emp_info_list', { params })

/**
 * Add a new employee.
 * @param {FormData} formData
 * @returns {Promise<AxiosResponse>}
 */
export const addEmployee = (formData) => axios.post('/api/adm/add_employee', formData)

/**
 * Update an employee by number.
 * @param {string} number - Employee number
 * @param {FormData} formData
 * @returns {Promise<AxiosResponse>}
 */
export const updateEmployee = (number, formData) => axios.put(`/api/employee/${number}`, formData)

/**
 * Delete an employee by number.
 * @param {string} number - Employee number
 * @returns {Promise<AxiosResponse>}
 */
export const deleteEmployee = (number) => axios.delete(`/api/admin/employee/${number}`)

// ──────────────────────────────────────
//  Application Approval Flow
// ──────────────────────────────────────

/**
 * Get applications for a given approval stage.
 * @param {string} stage - e.g. 'adm1', 'adm2'
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getApplications = (stage, params) => axios.get(`/api/${stage}_get_applications`, { params })

/**
 * Approve an application at a given stage.
 * @param {string} stage - e.g. 'adm1', 'adm2'
 * @param {Object} data - { id, user_name, user_number }
 * @returns {Promise<AxiosResponse>}
 */
export const approveApplication = (stage, data) => axios.post(`/api/${stage}_pass`, data)

/**
 * Reject an application at a given stage.
 * @param {string} stage - e.g. 'adm1', 'adm2'
 * @param {Object} data - { id, user_name, user_number, fail_reason }
 * @returns {Promise<AxiosResponse>}
 */
export const rejectApplication = (stage, data) => axios.post(`/api/${stage}_fail`, data)

/**
 * Batch review multiple applications.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const batchReview = (data) => axios.post('/api/admin/batch_review', data)

/**
 * Get approved applications (admin2 level).
 * @param {Object} [params]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getApprovedApplications = (params) => axios.get('/api/adm2_get_approved', { params })

/**
 * Re-review a previously approved application.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const reReview = (data) => axios.post('/api/admin/re_review', data)

/**
 * Additional review at stage 3.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const additionalReview = (data) => axios.post('/api/adm3_additional_review', data)

// ──────────────────────────────────────
//  Admin Application Management
// ──────────────────────────────────────

/**
 * Get paginated list of admin applications.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getAdminApplicationList = (params) => axios.get('/api/admin-application/list', { params })

/**
 * Get admin application detail by ID.
 * @param {number|string} id
 * @returns {Promise<AxiosResponse>}
 */
export const getAdminApplicationDetail = (id) => axios.get(`/api/admin-application/${id}`)

/**
 * Vote on an admin application.
 * @param {number|string} id
 * @param {Object} data - { approve, comment }
 * @returns {Promise<AxiosResponse>}
 */
export const voteAdminApplication = (id, data) => axios.post(`/api/admin-application/${id}/vote`, data)

/**
 * Check eligibility for admin application.
 * @returns {Promise<AxiosResponse>}
 */
export const checkAdminApplicationEligibility = () => axios.get('/api/admin-application/eligibility')

/**
 * Get current user's admin applications.
 * @returns {Promise<AxiosResponse>}
 */
export const getMyAdminApplications = () => axios.get('/api/admin-application/my')

/**
 * Submit an admin application.
 * @param {Object} data - { reason }
 * @returns {Promise<AxiosResponse>}
 */
export const submitAdminApplication = (data) => axios.post('/api/admin-application/submit', data)

// ──────────────────────────────────────
//  System Logs
// ──────────────────────────────────────

/**
 * Get paginated system logs.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getSystemLogs = (params) => axios.get('/api/admin/logs', { params })

// ──────────────────────────────────────
//  Announcements
// ──────────────────────────────────────

/**
 * Get paginated announcements.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getAnnouncements = (params) => axios.get('/api/announcements', { params })

/**
 * Create a new announcement.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const createAnnouncement = (data) => axios.post('/api/admin/announcements', data)

/**
 * Update an announcement.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const updateAnnouncement = (data) => axios.put('/api/admin/announcements', data)

/**
 * Delete an announcement by ID.
 * @param {number|string} id
 * @returns {Promise<AxiosResponse>}
 */
export const deleteAnnouncement = (id) => axios.delete('/api/admin/announcements', { params: { id } })

// ──────────────────────────────────────
//  Notifications
// ──────────────────────────────────────

/**
 * Send a notification to a user.
 * @param {Object} data
 * @returns {Promise<AxiosResponse>}
 */
export const sendNotification = (data) => axios.post('/api/admin/send-notification', data)

// ──────────────────────────────────────
//  Application Fetching (by channel)
// ──────────────────────────────────────

/**
 * Get SHP (vector) applications for first review.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getShpApplications = (params) => axios.get('/api/adm1_get_shp_applications', { params })

/**
 * Get raster applications for first review.
 * @param {Object} [params]
 * @param {number} [params.page]
 * @param {number} [params.pageSize]
 * @returns {Promise<AxiosResponse>}
 */
export const getRasterApplications = (params) => axios.get('/api/adm1_get_raster_applications', { params })

// ──────────────────────────────────────
//  User Management
// ──────────────────────────────────────

/**
 * Get all users (employees and admins) for chat contact selection.
 * @returns {Promise<AxiosResponse>}
 */
export const getAdminUsers = () => axios.get('/api/admin/users')

/**
 * Get single employee details by number.
 * @param {string} number - Employee number
 * @returns {Promise<AxiosResponse>}
 */
export const getEmployeeDetails = (number) => axios.get(`/api/employee/details/${number}`)

/**
 * Create a new user account.
 * @param {Object} data
 * @param {string} data.employee_number
 * @param {string} data.username
 * @param {string} data.password
 * @param {string} data.role
 * @returns {Promise<AxiosResponse>}
 */
export const createAccount = (data) => axios.post('/api/account/create', data)

/**
 * Export batch review failures as CSV (blob response).
 * @param {Object} data
 * @param {Array} data.failed
 * @returns {Promise<AxiosResponse>} Blob response
 */
export const batchReviewFailedExport = (data) => axios.post('/api/admin/batch_review_failed_export', data, { responseType: 'blob' })

/**
 * Get employee info for admin notification targeting.
 * @returns {Promise<AxiosResponse>}
 */
export const getEmployeeInfo = () => axios.get('/api/admin/get_employee_info')
