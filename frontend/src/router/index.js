import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/assets',
    children: [
      {
        path: 'employees',
        name: 'Employees',
        component: () => import('../views/EmployeeList.vue'),
        meta: { title: '员工管理', requireAdmin: true },
      },
      {
        path: 'assets',
        name: 'Assets',
        component: () => import('../views/AssetList.vue'),
        meta: { title: '资产管理' },
      },
      {
        path: 'asset-logs',
        name: 'AssetLogs',
        component: () => import('../views/AssetLogList.vue'),
        meta: { title: '流转记录', requireAdmin: true },
      },
      {
        path: 'operation-logs',
        name: 'OperationLogs',
        component: () => import('../views/OperationLogList.vue'),
        meta: { title: '操作日志', requireAdmin: true },
      },
      {
        path: 'cloud-files',
        name: 'CloudFiles',
        component: () => import('../views/CloudFiles.vue'),
        meta: { title: '云盘' },
      },
      {
        path: 'knowledge',
        name: 'KnowledgeBase',
        component: () => import('../views/KnowledgeBase.vue'),
        meta: { title: '知识库', requireAdmin: true },
      },
      {
        path: 'ai-config',
        name: 'AIConfig',
        component: () => import('../views/AIConfig.vue'),
        meta: { title: 'AI配置', requireAdmin: true },
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('../views/ChatView.vue'),
        meta: { title: 'AI问答' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const store = useUserStore()
  if (to.path !== '/login' && !store.token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && store.token) {
    return '/'
  }
  if (to.meta.requireAdmin && !store.isAdmin) {
    return '/assets'
  }
  document.title = to.meta.title ? `${to.meta.title} - 企业资产管理系统` : '企业资产管理系统'
  return true
})

export default router
