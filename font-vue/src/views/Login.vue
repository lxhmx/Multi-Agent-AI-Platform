<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const form = ref({
  username: '',
  password: ''
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
      body: JSON.stringify(form.value)
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
    <div class="bg-glow"></div>
    <div class="card">
      <div class="brand">
        <div class="brand-icon">T2S</div>
        <div class="brand-text">
          <div class="title">Text2SQL Control</div>
          <div class="subtitle">Secure Access · AI Native</div>
        </div>
      </div>
      <div class="headline">
        <div class="title">登录你的数据智能中枢</div>
        <div class="desc">以零代码方式查询数据，先登录，再体验全链路问答与训练。</div>
      </div>

      <el-form class="form" label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input
            v-model="form.username"
            placeholder="输入用户名"
            size="large"
            clearable
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            placeholder="输入密码"
            show-password
            size="large"
            clearable
          >
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-button
          class="login-btn"
          type="primary"
          size="large"
          round
          :loading="loading"
          @click="doLogin"
        >
          进入控制台
        </el-button>
        <div class="switch">
          还没有账户？
          <el-link type="primary" :underline="false" @click="router.push('/register')">去注册</el-link>
        </div>
      </el-form>

      <div class="footer">
        <div class="tag">JWT Auth</div>
        <div class="tag">FastAPI</div>
        <div class="tag">AI Gateway</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(120% 120% at 50% 20%, #1f2b5a 0%, #0c1224 50%, #05060c 100%);
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
  opacity: 0.4;
}
.bg-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(60% 60% at 20% 20%, rgba(72, 118, 255, 0.25), transparent 40%),
              radial-gradient(50% 50% at 80% 30%, rgba(72, 255, 218, 0.2), transparent 40%),
              radial-gradient(40% 40% at 50% 80%, rgba(255, 140, 72, 0.16), transparent 45%);
  filter: blur(40px);
  opacity: 0.7;
}
.card {
  position: relative;
  width: 420px;
  padding: 32px;
  border-radius: 18px;
  background: rgba(15, 22, 38, 0.72);
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
  background: linear-gradient(135deg, #4e6cff, #36e0f7);
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
:deep(.el-input__inner) {
  color: #e8ecf8;
}
:deep(.el-input__inner::placeholder) {
  color: rgba(232, 236, 248, 0.65);
}
:deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.06);
  border-color: #4e6cff;
  box-shadow: 0 0 0 1px #4e6cff inset, 0 6px 18px rgba(78, 108, 255, 0.28);
}
.login-btn {
  width: 100%;
  margin-top: 12px;
  background: linear-gradient(135deg, #4e6cff, #36e0f7);
  border: none;
  color: #05060c;
  font-weight: 700;
  letter-spacing: 0.5px;
  box-shadow: 0 12px 30px rgba(78, 108, 255, 0.35);
}
.login-btn:hover {
  filter: brightness(1.05);
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
