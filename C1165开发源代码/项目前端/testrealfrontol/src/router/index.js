// import { createRouter, createWebHistory } from 'vue-router';
// import { ElMessage } from 'element-plus';
// import { useUserStore } from '@/stores/userStore.js';

// // 导入员工子页面组件
// import EmployeeProfile from '@/views/employee/Employee Profile/employee_profile.vue';
// import EmployeeHelp from '@/views/employee/Employee Help/employee_help.vue';
// import EmployeeAbout from '@/views/employee/Employee About/employee_about.vue';
// import EmployeeDashboard from '@/views/employee/Employee Dashboard/employee_dashboard.vue';

// // 导入管理员仪表板组件
// import AdminDashboard from '@/views/admin/Adm Dashboard/adm_dashboard.vue';

// const routes = [
//   { path: '/', redirect: '/first_home' },
//   { path: '/first_home', component: () => import('@/views/first_home.vue') },
//   { path: '/login', component: () => import('@/views/login.vue') },
//   { path: '/register', component: () => import('@/views/register.vue') },
//   {
//     path: '/admin',
//     name: 'AdminHome',
//     component: () => import('@/views/admin/adm_home.vue'),
//     meta: { requiresAuth: true, roles: ['admin'] },
//     children: [
//       { path: '', name: 'AdminDashboard', component: AdminDashboard },
//       // 员工管理
//       { path: 'employee_management/information_add', name: 'AdminEmployeeInfoAdd', component: () => import('@/views/admin/Employee management/information_add.vue') },
//       { path: 'employee_management/information_list', name: 'AdminEmployeeInfoList', component: () => import('@/views/admin/Employee management/information_list.vue') },
//       { path: 'employee_management/edit/:id', name: 'AdminEditEmployee', component: () => import('@/views/admin/Employee management/EditEmployee.vue') },
//       { path: 'employee_management/account_add', name: 'AdminEmployeeAccountAdd', component: () => import('@/views/admin/Employee management/account_add.vue') },
//       { path: 'employee_management/account_list', name: 'AdminEmployeeAccountList', component: () => import('@/views/admin/Employee management/account_list.vue') },
//       // 审批申请
//       { path: 'approve_application/not_approved', name: 'AdminApproveNotApproved', component: () => import('@/views/admin/Approve Application/not_approved.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
//       { path: 'approve_application/approved', name: 'AdminApproveApproved', component: () => import('@/views/admin/Approve Application/approved.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
//       // 矢量数据水印
//       { path: 'watermark_generation', name: 'VectorWatermarkGeneration', component: () => import('@/views/admin/Watermark Generation/watermark_generation.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm1' } },
//       { path: 'watermark_embedding', name: 'VectorWatermarkEmbedding', component: () => import('@/views/admin/Watermark Embedding/watermark_embedding.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm2' } },
//       { path: 'watermark_extraction', name: 'VectorWatermarkExtraction', component: () => import('@/views/admin/Watermark Extraction/watermark_extraction.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm3' } },
//       // 系统管理
//       { path: 'logs', name: 'AdminLogViewer', component: () => import('@/views/admin/Log Management/LogViewer.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
//       // 数据管理
//       { path: 'data/upload', name: 'AdminDataUpload', component: () => import('@/views/admin/DataManagement/DataUpload.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
//     ]
//   },
//   {
//     path: '/employee',
//     name: 'EmployeeLayout',
//     component: () => import('@/views/employee/employee_home.vue'),
//     meta: { requiresAuth: true, roles: ['employee'] },
//     children: [
//       { path: '', name: 'EmployeeDashboard', component: EmployeeDashboard },
//       { path: 'data_viewing', name: 'EmployeeDataViewing', component: () => import('@/views/employee/Data Viewing/data_viewing.vue') },
//       { path: 'data_download', name: 'EmployeeDataDownload', component: () => import('@/views/employee/Data Download/data_download.vue') },
//       { path: 'data_application', name: 'EmployeeDataApplication', component: () => import('@/views/employee/Data Application/data_application.vue') },
//       { path: 'profile', name: 'EmployeeProfile', component: EmployeeProfile },
//       { path: 'help', name: 'EmployeeHelp', component: EmployeeHelp },
//       { path: 'about', name: 'EmployeeAbout', component: EmployeeAbout }
//     ]
//   },
// ];

// const router = createRouter({
//   history: createWebHistory(),
//   routes
// });

// // =========================================================================
// // 【【【 核心修正点：增强的全局路由守卫 】】】
// // =========================================================================
// router.beforeEach(async (to, from, next) => {
//   // Pinia store 必须在路由守卫内部获取，以确保它是最新的
//   const userStore = useUserStore();

//   // 这是您已有的初始化逻辑，非常好，保持它
//   // 它能确保在刷新页面时，能从sessionStorage恢复登录状态
//   if (!userStore.token) { // 仅在store中无token时才尝试初始化
//     userStore.initializeStore();
//   }

//   // =========================================================================
//   // 【【【 新增逻辑 1/2：登录成功快速通道 】】】
//   // 我们在所有检查的最前面，增加一个“快速通道”。
//   // 如果 userStore 中的 isLoginSuccess 标志为 true，
//   // 说明用户是刚刚通过 login.vue 成功登录的。
//   // 这种情况下，我们无条件放行，并立即重置该标志。
//   if (userStore.isLoginSuccess) {
//     userStore.resetLoginStatus(); // 消耗掉这次的“通行证”
//     return next(); // 立即放行，不再执行下面的任何检查
//   }
//   // =========================================================================

//   // 如果目标路由是公开的（如登录、注册页），也直接放行
//   if (to.path === '/login' || to.path === '/register' || to.path === '/first_home') {
//     return next();
//   }

//   // =========================================================================
//   // 【【【 现有逻辑的增强 】】】
//   // 从这里开始，是您已有的、处理“常规页面跳转”和“页面刷新”的鉴权逻辑。
//   // 我们将使用 store 的 getter 来让代码更清晰。
//   // =========================================================================
//   if (to.meta.requiresAuth) {
//     if (!userStore.isAuthenticated) { // 使用 getter 判断
//       ElMessage.error('未登录或登录已过期，请重新登录。');
//       return next('/login');
//     }
    
//     // 注意: 您代码中的 userStore.checkAuth() 是一个很好的实践，
//     // 用于向后端验证token是否真的有效。这里我们假设它存在并能正常工作。
//     // 如果您还没有实现 checkAuth，可以暂时注释掉下面这个 try...catch 块，
//     // 只保留基础的角色权限检查。
//     try {
//       // 假设 checkAuth() 会返回 true 或 false
//       // const authSuccess = await userStore.checkAuth(); 
//       // if (!authSuccess) {
//       //   ElMessage.error('登录状态异常，请重新登录。');
//       //   return next('/login');
//       // }

//       // 角色权限检查
//       const currentUserRole = userStore.currentUser?.role; // 从 currentUser 中获取角色
//       if (to.meta.roles && !to.meta.roles.includes(currentUserRole)) {
//         ElMessage.error('您没有权限访问该页面。');
//         // 根据角色重定向到各自的主页
//         return next(currentUserRole === 'admin' ? '/admin' : '/employee');
//       }

//       // 特定用户编号检查 (例如 adm1, adm2)
//       const currentUserNumber = userStore.userNumber; // 使用 getter
//       if (to.meta.user_number && to.meta.user_number !== currentUserNumber) {
//         ElMessage.error('您没有权限访问此特定页面。');
//         return next(currentUserRole === 'admin' ? '/admin' : '/login');
//       }
      
//       // 所有检查通过，放行
//       next();

//     } catch (err) {
//       console.error('验证用户状态失败:', err);
//       userStore.clearUserInfo();
//       ElMessage.error('登录状态异常，请重新登录。');
//       return next('/login');
//     }
//   } else {
//     // 如果页面不需要认证，直接放行
//     next();
//   }
// });

// export default router;

import { createRouter, createWebHistory } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useUserStore } from '@/stores/userStore.js';

// 导入员工子页面组件
import EmployeeProfile from '@/views/employee/Employee Profile/employee_profile.vue';
import EmployeeHelp from '@/views/employee/Employee Help/employee_help.vue';
import EmployeeAbout from '@/views/employee/Employee About/employee_about.vue';
import EmployeeDashboard from '@/views/employee/Employee Dashboard/employee_dashboard.vue';

// 导入管理员仪表板组件
import AdminDashboard from '@/views/admin/Adm Dashboard/adm_dashboard.vue';

const routes = [
  { path: '/', redirect: '/first_home' },
  { path: '/first_home', component: () => import('@/views/first_home.vue') },
  { path: '/login', component: () => import('@/views/login.vue') },
  { path: '/register', component: () => import('@/views/register.vue') },
  {
    path: '/admin',
    name: 'AdminHome',
    component: () => import('@/views/admin/adm_home.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
    children: [
      { path: '', name: 'AdminDashboard', component: AdminDashboard },
      // 员工管理
      { path: 'employee_management/information_add', name: 'AdminEmployeeInfoAdd', component: () => import('@/views/admin/Employee management/information_add.vue') },
      { path: 'employee_management/information_list', name: 'AdminEmployeeInfoList', component: () => import('@/views/admin/Employee management/information_list.vue') },
      { path: 'employee_management/edit/:id', name: 'AdminEditEmployee', component: () => import('@/views/admin/Employee management/EditEmployee.vue') },
      { path: 'employee_management/account_add', name: 'AdminEmployeeAccountAdd', component: () => import('@/views/admin/Employee management/account_add.vue') },
      { path: 'employee_management/account_list', name: 'AdminEmployeeAccountList', component: () => import('@/views/admin/Employee management/account_list.vue') },
      // 审批申请
      { path: 'approve_application/not_approved', name: 'AdminApproveNotApproved', component: () => import('@/views/admin/Approve Application/not_approved.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'approve_application/approved', name: 'AdminApproveApproved', component: () => import('@/views/admin/Approve Application/approved.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      // 矢量数据水印
      { path: 'watermark_generation', name: 'VectorWatermarkGeneration', component: () => import('@/views/admin/Watermark Generation/watermark_generation.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm1' } },
      { path: 'watermark_embedding', name: 'VectorWatermarkEmbedding', component: () => import('@/views/admin/Watermark Embedding/watermark_embedding.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm2' } },
      { path: 'watermark_extraction', name: 'VectorWatermarkExtraction', component: () => import('@/views/admin/Watermark Extraction/watermark_extraction.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm3' } },
      // 栅格数据水印
      { path: 'raster_watermark_generation', name: 'RasterWatermarkGeneration', component: () => import('@/views/admin/RasterWatermarkGeneration/raster_watermark_generation.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm1' } },
      { path: 'raster_watermark_embedding', name: 'RasterWatermarkEmbedding', component: () => import('@/views/admin/RasterWatermarkEmbedding/raster_watermark_embedding.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm2' } },
      { path: 'raster_watermark_extraction', name: 'RasterWatermarkExtraction', component: () => import('@/views/admin/RasterWatermarkExtraction/raster_watermark_extraction.vue'), meta: { requiresAuth: true, roles: ['admin'], user_number: 'adm3' } },
      // 系统管理
      { path: 'logs', name: 'AdminLogViewer', component: () => import('@/views/admin/Log Management/LogViewer.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      // 数据管理
      { path: 'data/upload', name: 'AdminDataUpload', component: () => import('@/views/admin/DataManagement/DataUpload.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
    ]
  },
  {
    path: '/employee',
    name: 'EmployeeLayout',
    component: () => import('@/views/employee/employee_home.vue'),
    meta: { requiresAuth: true, roles: ['employee'] },
    children: [
      { path: '', name: 'EmployeeDashboard', component: EmployeeDashboard },
      { path: 'data_viewing', name: 'EmployeeDataViewing', component: () => import('@/views/employee/Data Viewing/data_viewing.vue') },
      { path: 'data_download', name: 'EmployeeDataDownload', component: () => import('@/views/employee/Data Download/data_download.vue') },
      { path: 'data_application', name: 'EmployeeDataApplication', component: () => import('@/views/employee/Data Application/data_application.vue') },
      { path: 'profile', name: 'EmployeeProfile', component: EmployeeProfile },
      { path: 'help', name: 'EmployeeHelp', component: EmployeeHelp },
      { path: 'about', name: 'EmployeeAbout', component: EmployeeAbout }
    ]
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// =========================================================================
// 【【【 核心修正点：增强的全局路由守卫 】】】
// =========================================================================
router.beforeEach(async (to, from, next) => {
  // Pinia store 必须在路由守卫内部获取，以确保它是最新的
  const userStore = useUserStore();

  // 这是您已有的初始化逻辑，非常好，保持它
  // 它能确保在刷新页面时，能从sessionStorage恢复登录状态
  if (!userStore.token) { // 仅在store中无token时才尝试初始化
    userStore.initializeStore();
  }

  // =========================================================================
  // 【【【 新增逻辑 1/2：登录成功快速通道 】】】
  // 我们在所有检查的最前面，增加一个“快速通道”。
  // 如果 userStore 中的 isLoginSuccess 标志为 true，
  // 说明用户是刚刚通过 login.vue 成功登录的。
  // 这种情况下，我们无条件放行，并立即重置该标志。
  if (userStore.isLoginSuccess) {
    userStore.resetLoginStatus(); // 消耗掉这次的“通行证”
    return next(); // 立即放行，不再执行下面的任何检查
  }
  // =========================================================================

  // 如果目标路由是公开的（如登录、注册页），也直接放行
  if (to.path === '/login' || to.path === '/register' || to.path === '/first_home') {
    return next();
  }

  // =========================================================================
  // 【【【 现有逻辑的增强 】】】
  // 从这里开始，是您已有的、处理“常规页面跳转”和“页面刷新”的鉴权逻辑。
  // 我们将使用 store 的 getter 来让代码更清晰。
  // =========================================================================
  if (to.meta.requiresAuth) {
    if (!userStore.isAuthenticated) { // 使用 getter 判断
      ElMessage.error('未登录或登录已过期，请重新登录。');
      return next('/login');
    }
    
    // 注意: 您代码中的 userStore.checkAuth() 是一个很好的实践，
    // 用于向后端验证token是否真的有效。这里我们假设它存在并能正常工作。
    // 如果您还没有实现 checkAuth，可以暂时注释掉下面这个 try...catch 块，
    // 只保留基础的角色权限检查。
    try {
      // 假设 checkAuth() 会返回 true 或 false
      // const authSuccess = await userStore.checkAuth(); 
      // if (!authSuccess) {
      //  ElMessage.error('登录状态异常，请重新登录。');
      //  return next('/login');
      // }

      // 角色权限检查
      const currentUserRole = userStore.currentUser?.role; // 从 currentUser 中获取角色
      if (to.meta.roles && !to.meta.roles.includes(currentUserRole)) {
        ElMessage.error('您没有权限访问该页面。');
        // 根据角色重定向到各自的主页
        return next(currentUserRole === 'admin' ? '/admin' : '/employee');
      }

      // 特定用户编号检查 (例如 adm1, adm2)
      const currentUserNumber = userStore.userNumber; // 使用 getter
      if (to.meta.user_number && to.meta.user_number !== currentUserNumber) {
        ElMessage.error('您没有权限访问此特定页面。');
        return next(currentUserRole === 'admin' ? '/admin' : '/login');
      }
      
      // 所有检查通过，放行
      next();

    } catch (err) {
      console.error('验证用户状态失败:', err);
      userStore.clearUserInfo();
      ElMessage.error('登录状态异常，请重新登录。');
      return next('/login');
    }
  } else {
    // 如果页面不需要认证，直接放行
    next();
  }
});

export default router;
