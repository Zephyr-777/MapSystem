<template>
  <div class="auth-container">
    <div class="auth-background"></div>
    <div class="auth-box glass-morphism">
      <div class="auth-header">
        <h1 class="auth-title">GeoMap</h1>
        <p class="auth-subtitle">探索地质数据的无限可能</p>
      </div>
      
      <form @submit.prevent="handleLogin" class="auth-form">
        <div class="form-group">
          <input
            id="username"
            v-model="formData.username"
            type="text"
            placeholder="用户名"
            required
            :disabled="loading"
            class="apple-input"
          />
        </div>
        
        <div class="form-group">
          <input
            id="password"
            v-model="formData.password"
            type="password"
            placeholder="密码"
            required
            :disabled="loading"
            class="apple-input"
          />
        </div>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <button type="submit" class="apple-btn primary-btn" :disabled="loading">
          <span v-if="!loading">登录</span>
          <span v-else>登录中...</span>
        </button>
      </form>

      <div class="auth-footer">
        <p>
          还没有账户？
          <router-link to="/register" class="auth-link">立即注册</router-link>
        </p>
        <div class="chatgpt-hint">
          Protected by GeoMap Secure Auth
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const errorMessage = ref('')

const formData = ref({
  username: '',
  password: ''
})

const handleLogin = async () => {
  errorMessage.value = ''
  loading.value = true

  try {
    const result = await authStore.login({
      username: formData.value.username,
      password: formData.value.password
    })

    if (result.success) {
      router.push('/')
    } else {
      errorMessage.value = result.message || '登录失败，请检查用户名和密码'
    }
  } catch (error) {
    errorMessage.value = '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-container {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  overflow: hidden;
}

/* 动态渐变背景 */
.auth-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%);
  filter: blur(8px);
  z-index: -1;
  background-size: 200% 200%;
  animation: gradientBG 15s ease infinite;
}

@keyframes gradientBG {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.auth-box {
  width: 100%;
  max-width: 400px;
  padding: 40px;
  border-radius: 24px;
  text-align: center;
}

/* 玻璃质感核心类 */
.glass-morphism {
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
}

.auth-header {
  margin-bottom: 30px;
}

.auth-title {
  font-size: 28px;
  font-weight: 700;
  color: #1d1d1f;
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.auth-subtitle {
  color: #86868b;
  font-size: 15px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  text-align: left;
}

/* Apple 风格输入框 */
.apple-input {
  width: 100%;
  padding: 16px;
  border-radius: 12px;
  border: none;
  background: rgba(0, 0, 0, 0.05);
  font-size: 16px;
  color: #1d1d1f;
  transition: all 0.3s ease;
  outline: none;
}

.apple-input:focus {
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 0 0 4px rgba(0, 113, 227, 0.15);
}

.apple-input::placeholder {
  color: #86868b;
}

.error-message {
  color: #ff3b30;
  font-size: 14px;
  background: rgba(255, 59, 48, 0.1);
  padding: 10px;
  border-radius: 8px;
}

/* Apple 风格按钮 */
.apple-btn {
  width: 100%;
  padding: 16px;
  border-radius: 12px;
  border: none;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.primary-btn {
  background: #0071E3;
  color: white;
}

.primary-btn:hover {
  background: #0077ED;
  box-shadow: 0 4px 12px rgba(0, 113, 227, 0.3);
}

.primary-btn:active {
  transform: scale(0.96);
}

.primary-btn:disabled {
  background: #99c7ff;
  cursor: not-allowed;
  transform: none;
}

.auth-footer {
  margin-top: 24px;
  font-size: 14px;
  color: #86868b;
}

.auth-link {
  color: #0071E3;
  text-decoration: none;
  font-weight: 500;
}

.auth-link:hover {
  text-decoration: underline;
}

.chatgpt-hint {
  margin-top: 40px;
  font-size: 12px;
  color: #86868b;
  opacity: 0.6;
}
</style>
