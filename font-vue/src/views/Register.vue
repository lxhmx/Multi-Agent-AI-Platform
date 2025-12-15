<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

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
    <div class="bg-glow"></div>
    <div class="card">
      <div class="brand">
        <div class="brand-icon">T2S</div>
        <div class="brand-text">
          <div class="title">Create Access</div>
          <div class="subtitle">注册你的数据智能中枢账户</div>
        </div>
      </div>

      <div class="headline">
        <div class="title">欢迎加入 Text2SQL Control</div>
        <div class="desc">创建账户后即可体验登录、问答、训练和数据管理的全链路。</div>
      </div>

      <el-form class="form" label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            placeholder="输入用户名"
            size="large"
            clearable
          >
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="邮箱（可选）">
          <el-input
            v-model="form.email"
            placeholder="用于找回或通知"
            size="large"
            clearable
          >
            <template #prefix><el-icon><Message /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="输入密码"
            show-password
            size="large"
            clearable
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="form.confirm"
            type="password"
            placeholder="再次输入密码"
            show-password
            size="large"
            clearable
          >
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button
          class="primary-btn"
          type="primary"
          size="large"
          round
          :loading="loading"
          @click="doRegister"
        >
          创建账户
        </el-button>
        <div class="switch">
          已有账户？
          <el-link type="primary" :underline="false" @click="router.push('/login')">去登录</el-link>
        </div>
      </el-form>

      <div class="footer">
        <div class="tag">Secure · JWT</div>
        <div class="tag">FastAPI</div>
        <div class="tag">AI Ready</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.auth-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(120% 120% at 50% 20%, #172037 0%, #0b0f1f 50%, #05060c 100%);
  color: #e8ecf8;
  overflow: hidden;
}
.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px);
  background-size: 24px 24px;
  opacity: 0.35;
}
.bg-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(60% 60% at 20% 20%, rgba(80, 140, 255, 0.25), transparent 40%),
              radial-gradient(50% 50% at 80% 30%, rgba(56, 255, 214, 0.2), transparent 40%),
              radial-gradient(40% 40% at 50% 80%, rgba(255, 166, 74, 0.16), transparent 45%);
  filter: blur(40px);
  opacity: 0.7;
}
.card {
  position: relative;
  width: 440px;
  padding: 32px;
  border-radius: 18px;
  background: rgba(12, 17, 32, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  z-index: 1;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
}
.brand-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, #46c9ff, #4c6bff);
  display: grid;
  place-items: center;
  font-weight: 700;
  color: #05060c;
  letter-spacing: 0.5px;
}
.brand-text .title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.3px;
}
.brand-text .subtitle {
  font-size: 12px;
  color: #9fb4ff;
}
.headline .title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 6px;
}
.headline .desc {
  font-size: 13px;
  color: #c5cee0;
  line-height: 1.5;
  margin-bottom: 16px;
}
.form {
  margin-top: 12px;
}
.el-form-item__label {
  color: #cfd9ff;
  font-weight: 600;
  letter-spacing: 0.2px;
}
:deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
}
.primary-btn {
  width: 100%;
  margin-top: 4px;
  background: linear-gradient(135deg, #4e6cff, #38e0ff);
  border: none;
  color: #05060c;
  font-weight: 700;
  letter-spacing: 0.5px;
  box-shadow: 0 12px 30px rgba(78, 108, 255, 0.35);
}
.primary-btn:hover {
  filter: brightness(1.05);
}
.switch {
  margin-top: 12px;
  color: #cfd9ff;
  font-size: 13px;
  text-align: center;
}
.footer {
  display: flex;
  gap: 8px;
  margin-top: 18px;
  flex-wrap: wrap;
}
.tag {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #cdd6f4;
  font-size: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
