import { createRouter, createWebHistory } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useUserStore } from '@/stores/userStore.js';
import i18n from '@/locales/index.js';

const t = (key) => i18n.global.t(key);

import EmployeeProfile from '@/views/employee/Employee Profile/employee_profile.vue';
import EmployeeHelp from '@/views/employee/Employee Help/employee_help.vue';
import EmployeeAbout from '@/views/employee/Employee About/employee_about.vue';
import EmployeeDashboard from '@/views/employee/Employee Dashboard/employee_dashboard.vue';
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
      { path: 'employee_management/information_add', name: 'AdminEmployeeInfoAdd', component: () => import('@/views/admin/Employee management/information_add.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'employee_management/information_list', name: 'AdminEmployeeInfoList', component: () => import('@/views/admin/Employee management/information_list.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'employee_management/edit/:id', name: 'AdminEditEmployee', component: () => import('@/views/admin/Employee management/EditEmployee.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'approve_application/not_approved', name: 'AdminApproveNotApproved', component: () => import('@/views/admin/Approve Application/not_approved.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRoles: ['adm1'] } },
      { path: 'approve_application/approved', name: 'AdminApproveApproved', component: () => import('@/views/admin/Approve Application/approved.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRoles: ['adm2'] } },
      { path: 'approve_application/dual_channel', name: 'AdminDualChannelApproval', component: () => import('@/views/admin/Approve Application/DualChannelApproval.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRoles: ['adm1', 'adm2', 'adm3'] } },
      { path: 'watermark_generation', name: 'VectorWatermarkGeneration', component: () => import('@/views/admin/WatermarkGeneration/watermark_generation.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRole: 'adm1' } },
      { path: 'watermark_embedding', name: 'VectorWatermarkEmbedding', component: () => import('@/views/admin/Watermark Embedding/watermark_embedding.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRole: 'adm2' } },
      { path: 'watermark_extraction', name: 'VectorWatermarkExtraction', component: () => import('@/views/admin/Watermark Extraction/watermark_extraction.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRole: 'adm3' } },
      { path: 'raster_watermark_generation', name: 'RasterWatermarkGeneration', component: () => import('@/views/admin/RasterWatermarkGeneration/raster_watermark_generation.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRole: 'adm1' } },
      { path: 'raster_watermark_embedding', name: 'RasterWatermarkEmbedding', component: () => import('@/views/admin/RasterWatermarkEmbedding/raster_watermark_embedding.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRole: 'adm2' } },
      { path: 'raster_watermark_extraction', name: 'RasterWatermarkExtraction', component: () => import('@/views/admin/RasterWatermarkExtraction/raster_watermark_extraction.vue'), meta: { requiresAuth: true, roles: ['admin'], adminRole: 'adm3' } },
      { path: 'logs', name: 'AdminLogViewer', component: () => import('@/views/admin/Log Management/LogViewer.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'system/announcements', name: 'AdminSystemAnnouncements', component: () => import('@/views/admin/System Management/SystemAnnouncement.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'system/notifications', name: 'AdminSystemNotifications', component: () => import('@/views/admin/System Management/AdminNotifications.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'system/chat', name: 'AdminChat', component: () => import('@/views/admin/System Management/AdminChat.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'guide', name: 'AdminGuide', component: () => import('@/views/admin/System Management/AdminGuide.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'data/upload', name: 'AdminDataUpload', component: () => import('@/views/admin/DataManagement/DataUpload.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'recall', name: 'AdminRecallList', component: () => import('@/views/admin/RecallManagement/RecallProposalList.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
      { path: 'admin-application', name: 'AdminApplicationVoting', component: () => import('@/views/admin/AdminApplication/VotingPage.vue'), meta: { requiresAuth: true, roles: ['admin'] } },
    ]
  },
  {
    path: '/employee',
    name: 'EmployeeLayout',
    component: () => import('@/views/employee/employee_home.vue'),
    meta: { requiresAuth: true, roles: ['employee'] },
    children: [
      { path: '', name: 'EmployeeDashboard', component: EmployeeDashboard },
      { path: 'data_viewing', name: 'EmployeeDataViewing', component: () => import('@/views/employee/Data Viewing/data_viewing_new.vue') },
      { path: 'data_download', name: 'EmployeeDataDownload', component: () => import('@/views/employee/Data Download/data_download.vue') },
      { path: 'data_application', name: 'EmployeeDataApplication', component: () => import('@/views/employee/Data Application/data_application.vue') },
      { path: 'operation_history', name: 'EmployeeOperationHistory', component: () => import('@/views/employee/Operation History/my_operation_history.vue') },
      { path: 'notifications', name: 'EmployeeNotifications', component: () => import('@/views/employee/My Notifications/my_notifications.vue') },
      { path: 'chat', name: 'EmployeeChat', component: () => import('@/views/employee/Chat/employee_chat.vue') },
      { path: 'apply_admin', name: 'EmployeeApplyAdmin', component: () => import('@/views/employee/AdminApplication/ApplicationForm.vue') },
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

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore();

  if (!userStore.token) {
    userStore.initializeStore();
  }

  if (userStore.isLoginSuccess) {
    userStore.resetLoginStatus();
    return next();
  }

  if (to.path === '/login' || to.path === '/register' || to.path === '/first_home') {
    return next();
  }

  if (to.meta.requiresAuth) {
    if (!userStore.isAuthenticated) {
      ElMessage.error(t('auth.unauthorized'));
      return next('/login');
    }

    try {
      const currentUserRole = userStore.currentUser?.role;
      if (to.meta.roles && !to.meta.roles.includes(currentUserRole)) {
        ElMessage.error(t('auth.noPermission'));
        return next(currentUserRole === 'admin' ? '/admin' : '/employee');
      }

      if (currentUserRole === 'admin' && (to.meta.adminRole || to.meta.adminRoles)) {
        const num = (userStore.userNumber || '').toString().toLowerCase();
        const name = (userStore.userName || '').toString().toLowerCase();
        const adminRole =
          (num === 'admin1' || num === '22200214135' || name === '管理员1') ? 'adm1' :
          (num === 'admin2' || num === '33300214135' || name === '管理员2') ? 'adm2' :
          (num === 'admin3' || num === '44400214135' || name === '管理员3') ? 'adm3' :
          'adm1';
        const allowed = to.meta.adminRole ? [to.meta.adminRole] : (to.meta.adminRoles || []);
        if (allowed.length && !allowed.includes(adminRole)) {
          ElMessage.error(t('auth.noPermissionPage'));
          return next({ name: 'AdminDashboard' });
        }
      }

      next();
    } catch (err) {
      console.error('验证用户状态失败:', err);
      userStore.clearUserInfo();
      ElMessage.error(t('auth.sessionError'));
      return next('/login');
    }
  } else {
    next();
  }
});

export default router;
