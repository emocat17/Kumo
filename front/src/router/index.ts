import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'dashboard',
        component: () => import('@/pages/Dashboard.vue')
      },
      {
        path: 'python-versions',
        name: 'python-versions',
        component: () => import('@/pages/python/Versions.vue')
      },
      {
        path: 'python-environments',
        name: 'python-environments',
        component: () => import('@/pages/python/Environments.vue')
      },
      {
        path: 'projects',
        name: 'projects',
        component: () => import('@/pages/project/Projects.vue')
      }
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/pages/NotFound.vue') }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})

