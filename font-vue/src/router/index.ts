import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/training'
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
