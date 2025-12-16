<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, Message, Cpu, Lightning, View, Hide } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const form = ref({
  username: '',
  password: '',
  remember: false
})
const showPassword = ref(false)
const ready = ref(false)

onMounted(() => {
  requestAnimationFrame(() => {
    ready.value = true
  })
})

const doLogin = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: form.value.username,
        password: form.value.password
      })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '登录失败')
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    ElMessage.success('登录成功')
    router.push('/chat')
  } catch (e: any) {
    ElMessage.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="bg-grid"></div>
    <div class="bg-gradient-1"></div>
    <div class="bg-gradient-2"></div>
    
    <div class="center-container" :class="{ 'is-ready': ready }">
      <div class="brand-section fade-drop stagger-1">
        <div class="logo-box">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="brand-title">AI 智能平台</div>
        <div class="brand-subtitle">开启您的数字化未来</div>
      </div>

      <div class="card fade-drop stagger-2">
        <el-form class="form" label-position="top" @submit.prevent>
          <el-form-item label="邮箱地址/用户名" class="fade-drop stagger-3">
            <el-input
              v-model="form.username"
              placeholder="your@email.com"
              size="large"
            >
              <template #prefix>
                <el-icon><Message /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="密码" class="fade-drop stagger-4">
            <el-input
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="••••••••"
              size="large"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
              <template #suffix>
                <el-icon
                  class="toggle-eye"
                  :size="18"
                  @click="showPassword = !showPassword"
                >
                  <component :is="showPassword ? View : Hide" />
                </el-icon>
              </template>
            </el-input>
          </el-form-item>

          <div class="form-actions fade-drop stagger-5">
            <el-checkbox v-model="form.remember" label="记住我" />
            <el-link type="primary" :underline="false">忘记密码?</el-link>
          </div>

          <el-button
            class="login-btn fade-drop stagger-6"
            type="primary"
            size="large"
            round
            :loading="loading"
            @click="doLogin"
          >
            <el-icon class="mr-2"><Lightning /></el-icon>
            登录
          </el-button>

          <div class="divider fade-drop stagger-7">
            <span>或使用其他方式登录</span>
          </div>

          <div class="social-login fade-drop stagger-8">
            <button class="social-btn">G</button>
            <button class="social-btn">G</button>
            <button class="social-btn">M</button>
          </div>

          <div class="switch fade-drop stagger-9">
            还没有账户? <el-link type="primary" :underline="false" @click="router.push('/register')">立即注册</el-link>
          </div>
        </el-form>
      </div>
      
      <div class="footer-text fade-drop stagger-10">© 2025 AI 智能平台. 智能驱动未来</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  position: relative;
  min-height: 100vh;
  background: #f0f4ff;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* 背景网格 */
.bg-grid {
  position: absolute;
  inset: 0;
  background-image: 
    linear-gradient(rgba(78, 108, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(78, 108, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
}

/* 背景光晕 */
.bg-gradient-1 {
  position: absolute;
  top: -10%;
  left: -10%;
  width: 60%;
  height: 60%;
  background: radial-gradient(circle, rgba(162, 184, 255, 0.2) 0%, transparent 70%);
  filter: blur(60px);
  animation: float-bg 15s ease-in-out infinite alternate;
}

.bg-gradient-2 {
  position: absolute;
  bottom: -10%;
  right: -10%;
  width: 60%;
  height: 60%;
  background: radial-gradient(circle, rgba(169, 139, 255, 0.2) 0%, transparent 70%);
  filter: blur(60px);
  animation: float-bg 12s ease-in-out infinite alternate-reverse;
}

.center-container {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 440px;
  opacity: 0;
  transform: translateY(-24px);
  transition: opacity 0.8s ease, transform 0.8s ease;
}

.center-container.is-ready {
  opacity: 1;
  transform: translateY(0);
}

/* */
.brand-section {
  text-align: center;
  margin-bottom: 32px;
}

/* */
.logo-box {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #00C6FB, #7C2BFF);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  box-shadow: 0 8px 16px rgba(0, 198, 251, 0.25);
  color: #fff;
  font-size: 28px;
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
  cursor: pointer;
}

.logo-box:hover {
  transform: scale(1.15) rotate(5deg);
  box-shadow: 0 12px 24px rgba(0, 198, 251, 0.35);
}

.brand-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 8px;
}

.brand-subtitle {
  font-size: 14px;
  color: #6b7280;
}

/* */
.card {
  position: relative;
  width: 100%;
  background: transparent;
  padding: 3px; 
  border-radius: 20px;
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(255, 255, 255, 0.6) inset;
  overflow: hidden;
}

/* */
.card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: conic-gradient(
    transparent, 
    transparent, 
    transparent, 
    transparent,
    transparent,
    transparent,
    #0ea5e9, 
    transparent
  );
  animation: rotate-border 17s linear infinite;
  z-index: 0;
}

/* 内容遮罩层 */
.card::after {
  content: '';
  position: absolute;
  inset: 2px; /* 内部留出2px边框可见 */
  background: rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  z-index: 0;
  backdrop-filter: blur(12px);
}

/* 确保表单内容在遮罩之上 */
.form {
  position: relative;
  z-index: 1;
  padding: 32px; /* 原 card padding 移到这里 */
}

:deep(.el-form-item__label) {
  color: #4b5563;
  font-size: 13px;
  padding-bottom: 4px;
}

:deep(.el-input__wrapper) {
  background: #f9fafb;
  box-shadow: 0 0 0 1px #e5e7eb inset !important;
  border-radius: 12px;
  padding: 4px 11px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

:deep(.el-input__prefix .el-icon) {
  color: #69A4FF;
}

/* 动效：输入框聚焦流光边框 */
/* 使用 box-shadow 模拟渐变边框不太容易，这里用背景色+inset shadow 模拟 */
:deep(.el-input__wrapper.is-focus) {
  background: #fff;
  /* 基础聚焦色 - 使用 Royal Blue */
  box-shadow: 0 0 0 1px #3b82f6 inset !important;
}

/* 添加流动的底部线条 */
:deep(.el-input__wrapper.is-focus)::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  /* 使用指定青紫渐变 */
  background: linear-gradient(90deg, transparent, #00C6FB, #7C2BFF, transparent);
  background-size: 200% 100%;
  animation: flow-line 2s linear infinite;
}

:deep(.el-input__inner) {
  color: #1f2937;
  height: 40px;
}

.toggle-eye {
  cursor: pointer;
  color: #7c2bff;
  transition: color 0.2s ease;
}

.toggle-eye:hover {
  color: #9b6bff;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 8px 0 24px;
}

/* 动效：按钮扫光效果 */
.login-btn {
  width: 100%;
  height: 48px;
  /* 按钮渐变 - 调整为 Cyan 到 Purple */
  background: linear-gradient(90deg, #00C6FB, #7C2BFF);
  border: none;
  font-weight: 600;
  font-size: 15px;
  box-shadow: 0 4px 12px rgba(0, 198, 251, 0.25);
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
  z-index: 1;
}

.login-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.4),
    transparent
  );
  transform: skewX(-20deg);
  transition: none;
  z-index: -1;
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(139, 92, 246, 0.35);
}

/* 按钮 hover 时触发扫光动画 */
.login-btn:hover::before {
  animation: shine 0.75s;
}

.login-btn:active {
  transform: scale(0.98);
}

.divider {
  margin: 24px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    height: 1px;
    background: #e5e7eb;
  }
  
  span {
    position: relative;
    background: #fff; /* Fallback */
    background: rgba(255, 255, 255, 0.95);
    padding: 0 12px;
    font-size: 12px;
    color: #9ca3af;
    z-index: 1; /* 确保遮住线 */
  }
}

.social-login {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 24px;
}

.social-btn {
  width: 80px;
  height: 40px;
  border: 1px solid #e5e7eb;
  background: #fff;
  border-radius: 8px;
  color: #4b5563;
  font-weight: 600;
  font-style: italic;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  overflow: hidden;
  
  &:hover {
    background: #f9fafb;
    border-color: #d1d5db;
    transform: translateY(-2px);
  }
}

.switch {
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}

.footer-text {
  margin-top: 32px;
  font-size: 12px;
  color: #9ca3af;
}

.mr-2 {
  margin-right: 6px;
}

.fade-drop {
  opacity: 0;
  transform: translateY(-16px) scale(0.98);
  transition: opacity 0.6s cubic-bezier(0.22, 1, 0.36, 1), transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

.center-container.is-ready .fade-drop {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.stagger-1 { transition-delay: 0.05s; }
.stagger-2 { transition-delay: 0.10s; }
.stagger-3 { transition-delay: 0.15s; }
.stagger-4 { transition-delay: 0.20s; }
.stagger-5 { transition-delay: 0.25s; }
.stagger-6 { transition-delay: 0.30s; }
.stagger-7 { transition-delay: 0.35s; }
.stagger-8 { transition-delay: 0.40s; }
.stagger-9 { transition-delay: 0.45s; }
.stagger-10 { transition-delay: 0.50s; }

/* 动画关键帧 */
@keyframes rotate-border {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes flow-line {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@keyframes shine {
  0% { left: -100%; }
  100% { left: 200%; }
}

@keyframes float-bg {
  0% { transform: translate(0, 0); }
  100% { transform: translate(20px, 20px); }
}
</style>
