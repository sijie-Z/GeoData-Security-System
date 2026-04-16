// import { defineStore } from 'pinia';

// export const useUserStore = defineStore('user', {
//   state: () => ({
//     currentUser: null,
//     token: null,
//     refreshToken: null,
//     permissions: [],
//     user_number: null,
//     user_name: null  // 添加这一行
//   }),
//   actions: {
//     setUserInfo(userData) {
//       this.currentUser = userData;
//       this.token = userData.token;
//       this.refreshToken = userData.refreshToken;
//       this.permissions = userData.permissions;
//       this.user_number = userData.user_number;
//       this.user_name = userData.user_name;  // 添加这一行
//       sessionStorage.setItem('currentUser', JSON.stringify(userData));
//       sessionStorage.setItem('token', userData.token);
//       sessionStorage.setItem('refreshToken', userData.refreshToken);
//     },

//     clearUserInfo() {
//       this.currentUser = null;
//       this.token = null;
//       this.refreshToken = null;
//       this.permissions = [];
//       this.user_number = null;
//       this.user_name = null;  // 添加这一行
//       sessionStorage.removeItem('currentUser');
//       sessionStorage.removeItem('token');
//       sessionStorage.removeItem('refreshToken');
//     },

//     initializeStore() {
//       const storedUser = sessionStorage.getItem('currentUser');
//       if (storedUser) {
//         const userData = JSON.parse(storedUser);
//         this.setUserInfo(userData);
//       }
//     },

//     hasPermission(permission) {
//       return this.permissions.includes(permission);
//     }
//   },
//   getters: {
//     userNumber: (state) => state.user_number || '',
//     userName: (state) => state.user_name || ''  // 添加这一行
//   }
// });



import { defineStore } from 'pinia';

export const useUserStore = defineStore('user', {
  state: () => ({
    currentUser: null,
    token: null,
    refreshToken: null,
    permissions: [],
    user_number: null,
    user_name: null,
    
    // =========================================================================
    // 【【【 核心修正点 1/3：新增状态标志 】】】
    // 这个标志将作为同步的“通行证”，用于在登录成功后的瞬间通知路由守卫。
    // 它不是持久化的，只在单次登录流程中有效。
    isLoginSuccess: false,
    // =========================================================================
  }),

  actions: {
    setUserInfo(userData) {
      this.currentUser = userData;
      this.token = userData.token;
      this.refreshToken = userData.refreshToken;
      this.permissions = userData.permissions;
      this.user_number = userData.user_number;
      this.user_name = userData.user_name;

      // 在更新所有持久化信息的同时，设置我们的“通行证”
      this.isLoginSuccess = true; // <--- 关键！

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
      
      // =========================================================================
      // 【【【 核心修正点 2/3：重置状态标志 】】】
      // 登出时，务必重置“通行证”
      this.isLoginSuccess = false;
      // =========================================================================

      sessionStorage.removeItem('currentUser');
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('refreshToken');
    },

    initializeStore() {
      const storedUser = sessionStorage.getItem('currentUser');
      if (storedUser) {
        try { // 增加一个try...catch以防JSON解析失败
            const userData = JSON.parse(storedUser);
            // 注意：这里我们不直接调用setUserInfo，因为它会错误地设置isLoginSuccess标志
            // 我们只恢复持久化数据
            this.currentUser = userData;
            this.token = userData.token;
            this.refreshToken = userData.refreshToken;
            this.permissions = userData.permissions;
            this.user_number = userData.user_number;
            this.user_name = userData.user_name;
        } catch (error) {
            console.error("Failed to parse user data from sessionStorage:", error);
            this.clearUserInfo(); // 如果解析失败，清空所有信息
        }
      }
    },
    
    // =========================================================================
    // 【【【 核心修正点 3/3：新增一个Action来重置标志 】】】
    // 路由守卫在放行后，会调用这个action来销毁“通行证”，
    // 确保它只在登录跳转时生效一次。
    resetLoginStatus() {
      this.isLoginSuccess = false;
    },
    // =========================================================================

    hasPermission(permission) {
      // 确保在检查权限前，permissions数组一定存在
      return this.permissions && this.permissions.includes(permission);
    }
  },

  getters: {
    // 增加一个 isAuthenticated 的 getter，方便路由守卫使用
    isAuthenticated: (state) => !!state.token,
    userNumber: (state) => state.user_number || '',
    userName: (state) => state.user_name || ''
  }
});