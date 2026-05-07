import axios from 'axios';
import { useUserStore } from '@/stores/userStore';
import router from '@/router';

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 5000
});

const get = (url, data = {}) => {
    return axiosInstance.get(url, { params: data }).then(response => response.data)
}

const post = (url, data = null, config = {}) => {
    return axiosInstance.post(url, data, config).then(response => response.data)
}


axiosInstance.interceptors.request.use(config => {
  const userStore = useUserStore();
  const token = userStore.token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => {
  return Promise.reject(error);
});

axiosInstance.interceptors.response.use(
  response => response,
  async error => {
    const originalRequest = error.config;
    if (error.response && error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const userStore = useUserStore();

      try {
        const { data } = await axiosInstance.post('/api/refresh-token', {
          refresh_token: userStore.refreshToken
        });
        userStore.setUserInfo({
          ...userStore.currentUser,
          token: data.access_token,
          refreshToken: data.refresh_token
        });
        axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`;
        return axiosInstance.request(originalRequest);
      } catch (refreshError) {
        userStore.clearUserInfo();
        router.push('/login');
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);


export default axiosInstance;
export { axiosInstance as axios,get, post };





