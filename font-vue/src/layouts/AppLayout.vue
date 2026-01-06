<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed, ref, onMounted } from 'vue'

const route = useRoute()
const router = useRouter()
const ready = ref(false)

onMounted(() => {
  requestAnimationFrame(() => {
    ready.value = true
  })
})

const menuItems = [
  { path: '/agent-workbench', title: 'Agent工作台', icon: 'Cpu' },
  { path: '/video-summary', title: '视界拾贝', icon: 'VideoCamera' },
  { path: '/chat', title: '智能问答', icon: 'ChatDotRound' },
  { path: '/training', title: '知识训练', icon: 'Upload' },
  { path: '/data-manage', title: '数据管理', icon: 'Document' }
]

const activeMenu = computed(() => route.path)

const handleMenuSelect = (path: string) => {
  router.push(path)
}

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  router.push('/login')
}
</script>

<template>
  <div class="app-layout" :class="{ 'is-ready': ready }">
    <!-- 背景装饰 -->
    <div class="bg-grid"></div>
    <div class="bg-gradient-1"></div>
    <div class="bg-gradient-2"></div>
    
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-content">
        <!-- Logo -->
        <div class="logo">
          <div class="logo-icon">
            <el-icon :size="24" color="#fff"><Cpu /></el-icon>
          </div>
          <div class="logo-text">
            <span class="title">AI 智能平台</span>
            <span class="subtitle">Text2SQL</span>
          </div>
        </div>
        
        <!-- 导航菜单 -->
        <nav class="nav-menu">
          <div 
            v-for="item in menuItems" 
            :key="item.path"
            class="nav-item"
            :class="{ active: activeMenu === item.path }"
            @click="handleMenuSelect(item.path)"
          >
            <div class="nav-icon">
              <el-icon :size="18"><component :is="item.icon" /></el-icon>
            </div>
            <span class="nav-title">{{ item.title }}</span>
          </div>
        </nav>
        
        <!-- 底部信息 -->
        <div class="sidebar-footer">
          <div class="footer-divider"></div>
          <div class="footer-info">
            <el-icon><InfoFilled /></el-icon>
            <span>v1.0.0</span>
          </div>
        </div>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 顶部栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <span class="page-title">{{ route.meta.title || '控制台' }}</span>
        </div>
        <div class="topbar-right">
          <el-dropdown trigger="click">
            <span class="user-chip">
              <div class="user-avatar">
                <el-icon :size="16"><User /></el-icon>
              </div>
              <span class="user-name">账户</span>
              <el-icon class="arrow-icon"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 页面内容 -->
      <section class="page-body">
        <slot />
      </section>
    </main>
  </div>
</template>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: #f0f4ff;
  position: relative;
  overflow: hidden;
  opacity: 0;
  transition: opacity 0.5s ease;
  
  &.is-ready {
    opacity: 1;
  }
}

/* 背景网格 */
.bg-grid {
  position: fixed;
  inset: 0;
  background-image: 
    linear-gradient(rgba(78, 108, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(78, 108, 255, 0.03) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

/* 背景光晕 */
.bg-gradient-1 {
  position: fixed;
  top: -20%;
  right: -10%;
  width: 50%;
  height: 50%;
  background: radial-gradient(circle, rgba(0, 212, 255, 0.12) 0%, transparent 70%);
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
  animation: float-bg 15s ease-in-out infinite alternate;
}

.bg-gradient-2 {
  position: fixed;
  bottom: -20%;
  left: -10%;
  width: 50%;
  height: 50%;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, transparent 70%);
  filter: blur(60px);
  pointer-events: none;
  z-index: 0;
  animation: float-bg 12s ease-in-out infinite alternate-reverse;
}

/* ========== 侧边栏 ========== */
.sidebar {
  width: 220px;
  position: relative;
  z-index: 10;
  padding: 16px 12px;
  
  .sidebar-content {
    height: 100%;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(20px);
    border-radius: 20px;
    border: 1px solid rgba(255, 255, 255, 0.8);
    box-shadow: 
      0 4px 24px rgba(0, 0, 0, 0.06),
      0 0 0 1px rgba(255, 255, 255, 0.5) inset;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
}

.logo {
  display: flex;
  align-items: center;
  padding: 20px 16px;
  gap: 12px;
  
  .logo-icon {
    width: 44px;
    height: 44px;
    background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 6px 16px rgba(88, 141, 239, 0.35);
    transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
    cursor: pointer;
    
    &:hover {
      transform: scale(1.08) rotate(3deg);
      box-shadow: 0 8px 20px rgba(88, 141, 239, 0.45);
    }
  }
  
  .logo-text {
    display: flex;
    flex-direction: column;
    
    .title {
      font-size: 16px;
      font-weight: 700;
      color: #1f2937;
      letter-spacing: -0.3px;
    }
    
    .subtitle {
      font-size: 11px;
      color: #9ca3af;
      margin-top: 2px;
    }
  }
}

.nav-menu {
  flex: 1;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  
  .nav-icon {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f3f4f6;
    transition: all 0.25s ease;
    
    .el-icon {
      color: #6b7280;
      transition: all 0.25s ease;
    }
  }
  
  .nav-title {
    font-size: 14px;
    font-weight: 500;
    color: #4b5563;
    transition: all 0.25s ease;
  }
  
  &:hover {
    background: rgba(88, 141, 239, 0.06);
    
    .nav-icon {
      background: rgba(88, 141, 239, 0.1);
      
      .el-icon {
        color: #5b8def;
      }
    }
    
    .nav-title {
      color: #1f2937;
    }
  }
  
  &.active {
    background: linear-gradient(90deg, rgba(0, 212, 255, 0.1) 0%, rgba(168, 85, 247, 0.08) 100%);
    
    .nav-icon {
      background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
      box-shadow: 0 4px 12px rgba(88, 141, 239, 0.4);
      
      .el-icon {
        color: #fff;
      }
    }
    
    .nav-title {
      color: #1f2937;
      font-weight: 600;
    }
  }
}

.sidebar-footer {
  padding: 12px 16px 20px;
  
  .footer-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, #e5e7eb 50%, transparent 100%);
    margin-bottom: 12px;
  }
  
  .footer-info {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    font-size: 12px;
    color: #9ca3af;
    
    .el-icon {
      font-size: 14px;
    }
  }
}

/* ========== 主内容区 ========== */
.main-content {
  flex: 1;
  position: relative;
  z-index: 10;
  padding: 16px 16px 16px 0;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ========== 顶部栏 ========== */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 
    0 4px 24px rgba(0, 0, 0, 0.06),
    0 0 0 1px rgba(255, 255, 255, 0.5) inset;
  margin-bottom: 16px;
}

.topbar-left {
  .page-title {
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
    letter-spacing: -0.3px;
  }
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px 6px 6px;
  border-radius: 999px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  cursor: pointer;
  transition: all 0.25s ease;
  
  .user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    
    .el-icon {
      color: #fff;
    }
  }
  
  .user-name {
    font-size: 14px;
    font-weight: 500;
    color: #4b5563;
  }
  
  .arrow-icon {
    font-size: 12px;
    color: #9ca3af;
    transition: transform 0.2s ease;
  }
  
  &:hover {
    background: #fff;
    border-color: #d1d5db;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    
    .arrow-icon {
      transform: translateY(1px);
    }
  }
}

/* ========== 页面内容区 ========== */
.page-body {
  flex: 1;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 
    0 4px 24px rgba(0, 0, 0, 0.06),
    0 0 0 1px rgba(255, 255, 255, 0.5) inset;
  overflow: hidden;
  position: relative;
  min-height: 0;
}

/* 下拉菜单样式 */
:deep(.el-dropdown-menu) {
  min-width: 140px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  
  .el-dropdown-menu__item {
    padding: 10px 16px;
    font-size: 14px;
    
    &:hover {
      background: rgba(88, 141, 239, 0.08);
      color: #5b8def;
    }
  }
}

/* 动画 */
@keyframes float-bg {
  0% { transform: translate(0, 0); }
  100% { transform: translate(20px, 20px); }
}
</style>
