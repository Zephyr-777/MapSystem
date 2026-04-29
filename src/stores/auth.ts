import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type LoginRequest, type RegisterRequest } from '@/api/auth'
import router from '@/router'

type UserRole = 'admin' | 'researcher' | 'guest'

function normalizeRole(rawRole?: string): UserRole {
  const role = (rawRole || '').toLowerCase()
  if (role === 'admin' || role === 'administrator') return 'admin'
  if (role === 'researcher') return 'researcher'
  return 'guest'
}

export const useAuthStore = defineStore('auth', () => {
  const isAuthenticated = ref(false)
  const user = ref<{ id: number; username: string; email?: string; role?: string } | null>(null)
  const token = ref<string | null>(localStorage.getItem('token'))
  const role = computed<UserRole>(() => normalizeRole(user.value?.role))

  // 初始化时检查 token
  if (token.value) {
    isAuthenticated.value = true
    // 可以从 token 中解析用户信息，或调用 API 获取
    const userStr = localStorage.getItem('user')
    if (userStr) {
      user.value = JSON.parse(userStr)
    }
  }

  async function login(data: LoginRequest) {
    try {
      const response = await authApi.login(data)
      token.value = response.token
      user.value = response.user
      isAuthenticated.value = true
      
      // 保存到 localStorage
      localStorage.setItem('token', response.token)
      localStorage.setItem('user', JSON.stringify(response.user))
      
      return { success: true }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.detail || error.response?.data?.message || '登录失败，请检查用户名和密码'
      }
    }
  }

  async function register(data: RegisterRequest) {
    try {
      const response = await authApi.register(data)
      token.value = response.token
      user.value = response.user
      isAuthenticated.value = true
      
      // 保存到 localStorage
      localStorage.setItem('token', response.token)
      localStorage.setItem('user', JSON.stringify(response.user))
      
      return { success: true }
    } catch (error: any) {
      return {
        success: false,
        message: error.response?.data?.detail || error.response?.data?.message || '注册失败，请重试'
      }
    }
  }

  function logout() {
    isAuthenticated.value = false
    user.value = null
    token.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
  }

  function setRole(role: string) {
    if (user.value) {
      user.value = { ...user.value, role };
      localStorage.setItem('user', JSON.stringify(user.value));
    }
  }

  function hasRole(expected: UserRole) {
    return role.value === expected
  }

  function hasAnyRole(expectedRoles: UserRole[]) {
    return expectedRoles.includes(role.value)
  }

  const canManageUsers = computed(() => role.value === 'admin')
  const canExportData = computed(() => hasAnyRole(['admin', 'researcher']))

  return {
    isAuthenticated: computed(() => isAuthenticated.value),
    user: computed(() => user.value),
    token: computed(() => token.value),
    role,
    canManageUsers,
    canExportData,
    hasRole,
    hasAnyRole,
    login,
    register,
    logout,
    setRole
  }
})
