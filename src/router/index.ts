import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      redirect: '/map'
    },
    {
      path: '/map',
      name: 'Map',
      component: () => import('@/views/MapView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/gallery',
      name: 'Gallery',
      component: () => import('@/views/GalleryView.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/map')
  } else {
    next()
  }
})

export default router
