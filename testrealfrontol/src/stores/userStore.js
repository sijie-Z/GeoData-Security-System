import { defineStore } from 'pinia';

export const useUserStore = defineStore('user', {
  state: () => ({
    currentUser: null,
    token: null,
    refreshToken: null,
    permissions: [],
    user_number: null,
    user_name: null,
    admin_sub_role: null,
    isLoginSuccess: false,
  }),

  actions: {
    setUserInfo(userData) {
      this.currentUser = userData;
      this.token = userData.token;
      this.refreshToken = userData.refreshToken;
      this.permissions = userData.permissions;
      this.user_number = userData.user_number;
      this.user_name = userData.user_name;
      this.admin_sub_role = userData.admin_sub_role || null;
      this.isLoginSuccess = true;

      sessionStorage.setItem('currentUser', JSON.stringify(userData));
      sessionStorage.setItem('token', userData.token);
      sessionStorage.setItem('refreshToken', userData.refreshToken);
    },

    clearUserInfo() {
      this.currentUser = null;
      this.token = null;
      this.refreshToken = null;
      this.permissions = [];
      this.user_number = null;
      this.user_name = null;
      this.admin_sub_role = null;
      this.isLoginSuccess = false;

      sessionStorage.removeItem('currentUser');
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('refreshToken');
    },

    initializeStore() {
      const storedUser = sessionStorage.getItem('currentUser');
      if (storedUser) {
        try {
          const userData = JSON.parse(storedUser);
          this.currentUser = userData;
          this.token = userData.token;
          this.refreshToken = userData.refreshToken;
          this.permissions = userData.permissions;
          this.user_number = userData.user_number;
          this.user_name = userData.user_name;
          this.admin_sub_role = userData.admin_sub_role || null;
        } catch (error) {
          console.error('Failed to parse user data from sessionStorage:', error);
          this.clearUserInfo();
        }
      }
    },

    resetLoginStatus() {
      this.isLoginSuccess = false;
    },

    hasPermission(permission) {
      return this.permissions && this.permissions.includes(permission);
    }
  },

  getters: {
    isAuthenticated: (state) => !!state.token,
    userNumber: (state) => state.user_number || '',
    userName: (state) => state.user_name || '',
    adminSubRole: (state) => state.admin_sub_role || ''
  }
});
