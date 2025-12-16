<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Message, Lock, Cpu, Lightning } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const form = ref({
  username: '',
  email: '',
  password: '',
  confirm: ''
})

const doRegister = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (form.value.password !== form.value.confirm) {
    ElMessage.warning('两次密码不一致')
    return
  }
  loading.value = true
  try {
    const res = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: form.value.username,
        password: form.value.password,
        email: form.value.email || undefined
      })
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '注册失败')
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <div class="bg-grid"></div>
    <div class="bg-gradient-1"></div>
    <div class="bg-gradient-2"></div>
    
    <div class="center-container">
      <div class="brand-section">
        <div class="logo-box">
          <el-icon><Cpu /></el-icon>
        </div>
        <div class="brand-title">AI 智能平台</div>
        <div class="brand-subtitle">创建您的数字化账户</div>
      </div>

      <div class="card">
        <el-form class="form" label-position="top" @submit.prevent>
          <el-form-item label="用户名">
            <el-input
              v-model="form.username"
              placeholder="请输入用户名"
              size="large"
            >
              <template #prefix>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="邮箱地址（可选）">
            <el-input
              v-model="form.email"
              placeholder="your@email.com"
              size="large"
            >
              <template #prefix>
                <el-icon><Message /></el-icon>
              </template>
            </el-input>
          </el-form-item>
          
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              placeholder="设置密码"
              show-password
              size="large"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="确认密码">
            <el-input
              v-model="form.confirm"
              placeholder="再次输入密码"
              show-password
              size="large"
            >
              <template #prefix>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-button
            class="submit-btn"
            type="primary"
            size="large"
            round
            :loading="loading"
            @click="doRegister"
          >
            <el-icon class="mr-2"><Lightning /></el-icon>
            立即注册
          </el-button>

          <div class="switch">
            已有账户? <el-link type="primary" :underline="false" @click="router.push('/login')">去登录</el-link>
          </div>
        </el-form>
      </div>
      
      <div class="footer-text">© 2025 AI 智能平台. 智能驱动未来</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.auth-page {
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
}

.brand-section {
  text-align: center;
  margin-bottom: 32px;
}

/* Logo */
.logo-box {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #00B6DE, #961EFB);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  box-shadow: 0 8px 16px rgba(0, 182, 222, 0.25);
  color: #fff;
  font-size: 28px;
  transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
  cursor: pointer;
}

.logo-box:hover {
  transform: scale(1.15) rotate(5deg);
  box-shadow: 0 12px 24px rgba(0, 182, 222, 0.35);
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

/* Card */
.card {
  position: relative;
  width: 100%;
  background: transparent;
  padding: 3px;
  border-radius: 20px;
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(255, 255, 255, 0.6) inset;
  overflow: hidden;
}

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

.card::after {
  content: '';
  position: absolute;
  inset: 2px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  z-index: 0;
  backdrop-filter: blur(12px);
}

/* 确保表单内容在遮罩之上 */
.form {
  position: relative;
  z-index: 1;
  padding: 32px;
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

:deep(.el-input__wrapper.is-focus) {
  background: #fff;
  box-shadow: 0 0 0 1px #3b82f6 inset !important;
}

:deep(.el-input__wrapper.is-focus)::after {
  content: "";
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, #00B6DE, #961EFB, transparent);
  background-size: 200% 100%;
  animation: flow-line 2s linear infinite;
}

:deep(.el-input__inner) {
  color: #1f2937;
  height: 40px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  background: linear-gradient(90deg, #00B6DE, #961EFB);
  border: none;
  font-weight: 600;
  font-size: 15px;
  box-shadow: 0 4px 12px rgba(0, 182, 222, 0.25);
  transition: all 0.3s;
  margin-top: 12px;
  position: relative;
  overflow: hidden;
  z-index: 1;
}

.submit-btn::before {
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

.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(139, 92, 246, 0.35);
}

.submit-btn:hover::before {
  animation: shine 0.75s;
}

.submit-btn:active {
  transform: scale(0.98);
}

.switch {
  margin-top: 24px;
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
