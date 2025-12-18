<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getAgentList } from '@/api'
import type { AgentInfo } from '@/api'

const router = useRouter()
const agents = ref<AgentInfo[]>([])
const loading = ref(false)

// 智能体图标映射
const agentIcons: Record<string, string> = {
  data_analyst: 'DataAnalysis',
  default: 'Cpu'
}

// 智能体颜色映射
const agentColors: Record<string, string> = {
  data_analyst: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
  default: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
}

// 加载智能体列表
const loadAgents = async () => {
  loading.value = true
  try {
    const response = await getAgentList()
    agents.value = response.agents
  } catch (error) {
    console.error('加载智能体列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 跳转到对话页面并选择智能体
const startChat = (agentName: string) => {
  router.push({ path: '/chat', query: { agent: agentName } })
}

onMounted(() => {
  loadAgents()
})
</script>

<template>
  <div class="agent-workbench">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-icon">
          <el-icon :size="32"><Cpu /></el-icon>
        </div>
        <div class="header-text">
          <h1 class="header-title">Agent 工作台</h1>
          <p class="header-desc">选择一个智能体开始对话，或查看智能体详情</p>
        </div>
      </div>
    </div>

    <!-- 智能体卡片列表 -->
    <div class="agent-grid" v-loading="loading">
      <!-- 智能模式卡片 -->
      <div class="agent-card auto-mode" @click="startChat('auto')">
        <div class="card-badge">推荐</div>
        <div class="card-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
          <el-icon :size="36"><MagicStick /></el-icon>
        </div>
        <div class="card-content">
          <h3 class="card-title">智能模式</h3>
          <p class="card-desc">自动选择最合适的智能体处理您的问题</p>
        </div>
        <div class="card-footer">
          <span class="card-tag">自动路由</span>
          <el-button type="primary" size="small" round>
            <el-icon><ChatDotRound /></el-icon>
            开始对话
          </el-button>
        </div>
      </div>

      <!-- 具体智能体卡片 -->
      <div 
        v-for="agent in agents" 
        :key="agent.name"
        class="agent-card"
        @click="startChat(agent.name)"
      >
        <div class="card-icon" :style="{ background: agentColors[agent.name] || agentColors.default }">
          <el-icon :size="36">
            <component :is="agentIcons[agent.name] || agentIcons.default" />
          </el-icon>
        </div>
        <div class="card-content">
          <h3 class="card-title">{{ agent.description.split('，')[0] }}</h3>
          <p class="card-desc">{{ agent.description }}</p>
        </div>
        <div class="card-footer">
          <span class="card-tag">{{ agent.name }}</span>
          <el-button type="primary" size="small" round>
            <el-icon><ChatDotRound /></el-icon>
            开始对话
          </el-button>
        </div>
      </div>

      <!-- 敬请期待卡片 -->
      <div class="agent-card placeholder">
        <div class="card-icon placeholder-icon">
          <el-icon :size="36"><Plus /></el-icon>
        </div>
        <div class="card-content">
          <h3 class="card-title">更多智能体</h3>
          <p class="card-desc">更多智能体正在开发中，敬请期待</p>
        </div>
        <div class="card-footer">
          <span class="card-tag">Coming Soon</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.agent-workbench {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

// ========== 页面头部 ==========
.page-header {
  margin-bottom: 32px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 8px 24px rgba(88, 141, 239, 0.3);
}

.header-text {
  .header-title {
    font-size: 24px;
    font-weight: 700;
    color: #1f2937;
    margin: 0 0 4px 0;
  }
  
  .header-desc {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
  }
}

// ========== 智能体卡片网格 ==========
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

.agent-card {
  background: #fff;
  border-radius: 20px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid rgba(0, 0, 0, 0.04);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  position: relative;
  overflow: hidden;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(88, 141, 239, 0.15);
    border-color: rgba(88, 141, 239, 0.2);
  }
  
  &.auto-mode {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
    border-color: rgba(102, 126, 234, 0.2);
  }
  
  &.placeholder {
    cursor: default;
    opacity: 0.6;
    
    &:hover {
      transform: none;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
    }
    
    .placeholder-icon {
      background: #e5e7eb !important;
      border: 2px dashed #ccc;
    }
  }
}

.card-badge {
  position: absolute;
  top: 16px;
  right: 16px;
  padding: 4px 12px;
  background: linear-gradient(90deg, #00d4ff 0%, #a855f7 100%);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  border-radius: 12px;
}

.card-icon {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 20px;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}

.card-content {
  margin-bottom: 20px;
  
  .card-title {
    font-size: 18px;
    font-weight: 600;
    color: #1f2937;
    margin: 0 0 8px 0;
  }
  
  .card-desc {
    font-size: 14px;
    color: #6b7280;
    margin: 0;
    line-height: 1.6;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  
  .card-tag {
    padding: 4px 12px;
    background: #f3f4f6;
    border-radius: 8px;
    font-size: 12px;
    color: #6b7280;
  }
  
  .el-button {
    background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
    border: none;
    
    &:hover {
      opacity: 0.9;
    }
  }
}
</style>
