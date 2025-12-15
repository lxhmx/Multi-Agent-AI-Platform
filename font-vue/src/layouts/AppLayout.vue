<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const router = useRouter()

const menuItems = [
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
  <div class="app-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <!-- 背景装饰 -->
      <div class="sidebar-bg">
        <div class="bg-circle circle-1"></div>
        <div class="bg-circle circle-2"></div>
        <div class="bg-circle circle-3"></div>
      </div>
      
      <div class="sidebar-content">
        <div class="logo">
          <div class="logo-icon">
            <el-icon :size="26" color="#fff"><Connection /></el-icon>
          </div>
          <div class="logo-text">
            <span class="title">智能知识库</span>
            <span class="subtitle">Text2SQL 问答平台</span>
          </div>
        </div>
        
        <nav class="nav-menu">
          <div 
            v-for="item in menuItems" 
            :key="item.path"
            class="nav-item"
            :class="{ active: activeMenu === item.path }"
            @click="handleMenuSelect(item.path)"
          >
            <div class="nav-icon">
              <el-icon><component :is="item.icon" /></el-icon>
            </div>
            <span class="nav-title">{{ item.title }}</span>
            <div class="nav-indicator"></div>
          </div>
        </nav>
        
        <div class="sidebar-footer">
          <div class="footer-divider"></div>
          <div class="footer-info">
            <el-icon><InfoFilled /></el-icon>
            <span>v1.0.0</span>
          </div>
          <div class="footer-copyright">© 2025 智能知识库</div>
        </div>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content">
      <header class="topbar">
        <div class="topbar-left">
          <span class="page-title">{{ route.meta.title || '控制台' }}</span>
        </div>
        <div class="topbar-right">
          <el-dropdown trigger="click">
            <span class="user-chip">
              <el-icon><User /></el-icon>
              <span class="user-name">账户</span>
              <el-icon><ArrowDown /></el-icon>
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
}

.sidebar {
  width: 240px;
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  
  // 背景装饰圆圈
  .sidebar-bg {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
    
    .bg-circle {
      position: absolute;
      border-radius: 50%;
      opacity: 0.08;
      
      &.circle-1 {
        width: 200px;
        height: 200px;
        background: linear-gradient(135deg, #7c3aed 0%, #a855f7 100%);
        top: -60px;
        right: -60px;
        animation: float 8s ease-in-out infinite;
      }
      
      &.circle-2 {
        width: 150px;
        height: 150px;
        background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
        bottom: 20%;
        left: -40px;
        animation: float 10s ease-in-out infinite reverse;
      }
      
      &.circle-3 {
        width: 100px;
        height: 100px;
        background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 100%);
        bottom: -20px;
        right: 20px;
        animation: float 6s ease-in-out infinite;
      }
    }
  }
  
  .sidebar-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  .logo {
    display: flex;
    align-items: center;
    padding: 24px 20px;
    gap: 14px;
    
    .logo-icon {
      width: 48px;
      height: 48px;
      background: linear-gradient(135deg, #7c3aed 0%, #a855f7 50%, #10b981 100%);
      border-radius: 14px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 24px rgba(124, 58, 237, 0.4);
      animation: pulse-glow 3s ease-in-out infinite;
    }
    
    .logo-text {
      display: flex;
      flex-direction: column;
      
      .title {
        font-size: 18px;
        font-weight: 700;
        background: linear-gradient(135deg, #fff 0%, #e0e7ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      
      .subtitle {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
        margin-top: 2px;
        letter-spacing: 0.5px;
      }
    }
  }
  
  .nav-menu {
    flex: 1;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  
  .nav-item {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px 16px;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    overflow: hidden;
    
    .nav-icon {
      width: 38px;
      height: 38px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.08);
      transition: all 0.3s ease;
      
      .el-icon {
        font-size: 18px;
        color: rgba(255, 255, 255, 0.7);
        transition: all 0.3s ease;
      }
    }
    
    .nav-title {
      font-size: 14px;
      font-weight: 500;
      color: rgba(255, 255, 255, 0.7);
      transition: all 0.3s ease;
    }
    
    .nav-indicator {
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 4px;
      height: 0;
      background: linear-gradient(180deg, #7c3aed 0%, #10b981 100%);
      border-radius: 0 4px 4px 0;
      transition: height 0.3s ease;
    }
    
    &:hover {
      background: rgba(255, 255, 255, 0.06);
      
      .nav-icon {
        background: rgba(255, 255, 255, 0.12);
        transform: scale(1.05);
      }
      
      .nav-title {
        color: rgba(255, 255, 255, 0.9);
      }
    }
    
    &.active {
      background: linear-gradient(135deg, rgba(124, 58, 237, 0.25) 0%, rgba(16, 185, 129, 0.15) 100%);
      
      .nav-icon {
        background: linear-gradient(135deg, #7c3aed 0%, #10b981 100%);
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4);
        
        .el-icon {
          color: #fff;
        }
      }
      
      .nav-title {
        color: #fff;
        font-weight: 600;
      }
      
      .nav-indicator {
        height: 24px;
      }
    }
  }
  
  .sidebar-footer {
    padding: 16px 20px 24px;
    
    .footer-divider {
      height: 1px;
      background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.1) 50%, transparent 100%);
      margin-bottom: 16px;
    }
    
    .footer-info {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      font-size: 12px;
      color: rgba(255, 255, 255, 0.4);
      margin-bottom: 8px;
      
      .el-icon {
        font-size: 14px;
      }
    }
    
    .footer-copyright {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.3);
      text-align: center;
    }
  }
}

.main-content {
  flex: 1;
  background: linear-gradient(180deg, #0b1020 0%, #0a0f1e 100%);
  padding: 24px 32px;
  color: #e5e7eb;
  display: flex;
  flex-direction: column;
}

:deep(.el-dropdown-menu) {
  min-width: 140px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
  margin-bottom: 16px;
}

.topbar-left .page-title {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: #f9fafb;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  color: #e5e7eb;
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.08);
  transition: all 0.2s ease;
}

.user-chip:hover {
  border-color: rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.12);
}

.page-body {
  flex: 1;
  margin-top: 4px;
}

/* 关键动画 */
@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0px); }
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 8px 24px rgba(124, 58, 237, 0.4);
  }
  50% {
    box-shadow: 0 8px 32px rgba(124, 58, 237, 0.6), 0 0 48px rgba(16, 185, 129, 0.3);
  }
}
</style>
