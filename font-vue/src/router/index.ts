import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const getToken = () => localStorage.getItem('access_token')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/agent-workbench'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', layout: 'blank' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/Register.vue'),
    meta: { title: '注册', layout: 'blank' }
  },
  {
    path: '/training',
    name: 'Training',
    component: () => import('@/views/Training.vue'),
    meta: { title: '知识训练', icon: 'Upload' }
  },
  {
    path: '/data-manage',
    name: 'DataManage',
    component: () => import('@/views/DataManage.vue'),
    meta: { title: '数据管理', icon: 'Document' }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
    meta: { title: '智能问答', icon: 'ChatDotRound' }
  },
  {
    path: '/agent-workbench',
    name: 'AgentWorkbench',
    component: () => import('@/views/AgentWorkbench.vue'),
    meta: { title: 'Agent工作台', icon: 'Cpu' }
  },
  {
    path: '/video-summary',
    name: 'VideoSummary',
    component: () => import('@/views/VideoSummary.vue'),
    meta: { title: '视界拾贝', icon: 'VideoCamera' }
  },
  {
    path: '/financial',
    name: 'Financial',
    meta: { title: '财务核算', icon: 'Money' },
    children: [
      {
        path: 'overtime-stats',
        name: 'OvertimeStats',
        component: () => import('@/views/financialAccouting/OvertimeStats.vue'),
        meta: { title: '加班统计', icon: 'TrendCharts' }
      },
      {
        path: 'overtime-list',
        name: 'OvertimeList',
        component: () => import('@/views/financialAccouting/OvertimeList.vue'),
        meta: { title: '加班记录', icon: 'Document' }
      },
      {
        path: 'attendance-list',
        name: 'AttendanceList',
        component: () => import('@/views/financialAccouting/attendanceList/index.vue'),
        meta: { title: '考勤扣款', icon: 'Warning' }
      },
      {
        path: 'work-time',
        name: 'WorkTimeStats',
        component: () => import('@/views/financialAccouting/workTime/index.vue'),
        meta: { title: '工作时长统计', icon: 'Timer' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  const token = getToken()
  if (to.path === '/login' || to.path === '/register') {
    // 已登录访问登录/注册页，跳转到首页
    if (token) return next('/agent-workbench')
    return next()
  }
  if (!token) {
    return next('/login')
  }
  next()
})

export default router
