import axios from 'axios';
import { useUserStore } from '@/stores/userStore';
import router from '@/router';
import { ElMessage } from 'element-plus';

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — inject JWT token
axiosInstance.interceptors.request.use(
  (config) => {
    const userStore = useUserStore();
    const token = userStore.token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — handle 401 with automatic token refresh
axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Attempt token refresh on 401 (once)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const userStore = useUserStore();

      try {
        const { data } = await axiosInstance.post('/api/refresh-token', {
          refresh_token: userStore.refreshToken,
        });

        userStore.setUserInfo({
          ...userStore.currentUser,
          token: data.access_token,
          refreshToken: data.refresh_token,
        });

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return axiosInstance.request(originalRequest);
      } catch (refreshError) {
        userStore.clearUserInfo();
        ElMessage.error('登录已过期，请重新登录');
        router.push('/login');
        return Promise.reject(refreshError);
      }
    }

    // Handle other errors
    if (error.response) {
      const { status, data } = error.response;
      const msg = data?.msg || data?.message;

      switch (status) {
        case 403:
          ElMessage.error(msg || '没有权限访问');
          break;
        case 404:
          ElMessage.error(msg || '请求的资源不存在');
          break;
        case 429:
          ElMessage.error(msg || '请求过于频繁，请稍后重试');
          break;
        case 500:
          ElMessage.error(msg || '服务器错误，请稍后重试');
          break;
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接');
    }

    return Promise.reject(error);
  }
);

// Convenience methods
const get = (url, params = {}) => {
  return axiosInstance.get(url, { params }).then((response) => response.data);
};

const post = (url, data = null, config = {}) => {
  return axiosInstance.post(url, data, config).then((response) => response.data);
};

export default axiosInstance;
export { axiosInstance as axios, get, post };
