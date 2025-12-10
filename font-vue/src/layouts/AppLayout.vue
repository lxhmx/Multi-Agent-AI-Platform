<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const router = useRouter()

const menuItems = [
  { path: '/training', title: '知识训练', icon: 'Upload' },
  { path: '/data-manage', title: '数据管理', icon: 'Document' },
  { path: '/chat', title: '智能问答', icon: 'ChatDotRound' }
]

const activeMenu = computed(() => route.path)

const handleMenuSelect = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <div class="logo-icon">
          <el-icon :size="24" color="#fff"><Connection /></el-icon>
        </div>
        <div class="logo-text">
          <span class="title">智能知识库</span>
          <span class="subtitle">问答平台</span>
        </div>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        class="sidebar-menu"
        @select="handleMenuSelect"
      >
        <el-menu-item 
          v-for="item in menuItems" 
          :key="item.path"
          :index="item.path"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        © 2025 智能知识库平台
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 200px;
  background: #fff;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #f0f0f0;
  
  .logo {
    display: flex;
    align-items: center;
    padding: 20px 16px;
    gap: 12px;
    
    .logo-icon {
      width: 40px;
      height: 40px;
      background: linear-gradient(180deg, #7c3aed 0%, #10b981 100%);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .logo-text {
      display: flex;
      flex-direction: column;
      
      .title {
        font-size: 16px;
        font-weight: 600;
        color: #7c3aed;
      }
      
      .subtitle {
        font-size: 12px;
        color: #999;
      }
    }
  }
  
  .sidebar-menu {
    flex: 1;
    padding: 0 12px;
    
    :deep(.el-menu-item) {
      height: 44px;
      line-height: 44px;
      margin-bottom: 4px;
      border-radius: 8px;
      
      &:hover {
        background: #f5f5f5;
      }
      
      &.is-active {
        background: linear-gradient(135deg, #7c3aed 0%, #10b981 100%) !important;
        color: #fff !important;
        
        .el-icon {
          color: #fff;
        }
      }
    }
  }
  
  .sidebar-footer {
    padding: 16px;
    font-size: 12px;
    color: #999;
    text-align: center;
  }
}

.main-content {
  flex: 1;
  background: #f8f9fc;
  padding: 24px;
  overflow-y: auto;
}
</style>
