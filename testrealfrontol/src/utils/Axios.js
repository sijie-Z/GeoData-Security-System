import axios from 'axios'
import { useUserStore } from '@/stores/userStore'
import router from '@/router'
import { ElMessage } from 'element-plus'
import i18n from '@/locales/index.js'

const t = (key) => i18n.global.t(key)

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Refresh token lock — prevents multiple simultaneous refresh attempts
let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token)
    }
  })
  failedQueue = []
}

// Request interceptor — inject JWT token
axiosInstance.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    const token = userStore.token
    if (token && !config.url.includes('/api/login') && !config.url.includes('/api/refresh-token')) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor — handle 401 with automatic token refresh
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // Attempt token refresh on 401 (once)
    if (error.response?.status === 401 && !originalRequest._retry
        && !originalRequest.url.includes('/api/refresh-token')
        && !originalRequest.url.includes('/api/login')) {

      if (isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return axiosInstance.request(originalRequest)
        }).catch(err => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true
      const userStore = useUserStore()

      try {
        const { data } = await axiosInstance.post('/api/refresh-token', {
          refresh_token: userStore.refreshToken,
        })

        userStore.setUserInfo({
          ...userStore.currentUser,
          token: data.access_token,
          refreshToken: data.refresh_token,
        })

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        processQueue(null, data.access_token)
        return axiosInstance.request(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        userStore.clearUserInfo()
        ElMessage.error(t('auth.tokenExpired'))
        router.push('/login')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    // Handle other errors
    if (error.response) {
      const { status, data } = error.response
      const msg = data?.msg || data?.message

      switch (status) {
        case 403:
          ElMessage.error(msg || t('auth.noPermissionAccess'))
          break
        case 404:
          ElMessage.error(msg || t('auth.resourceNotFound'))
          break
        case 429:
          ElMessage.error(msg || t('auth.tooManyRequests'))
          break
        case 500:
          ElMessage.error(msg || t('auth.serverError'))
          break
      }
    } else if (error.request) {
      ElMessage.error(t('auth.networkError'))
    }

    return Promise.reject(error)
  }
)

// Convenience methods
const get = (url, params = {}) => {
  return axiosInstance.get(url, { params }).then((response) => response.data)
}

const post = (url, data = null, config = {}) => {
  return axiosInstance.post(url, data, config).then((response) => response.data)
}

export default axiosInstance
export { axiosInstance as axios, get, post }
