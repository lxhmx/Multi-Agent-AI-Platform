<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { Session } from '@/api'

const props = defineProps<{
  sessions: Session[]
  activeSessionId: string
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'select', sessionId: string): void
  (e: 'create'): void
  (e: 'rename', sessionId: string, newTitle: string): void
  (e: 'delete', sessionId: string): void
}>()

// 编辑状态
const editingSessionId = ref<string | null>(null)
const editingTitle = ref('')

// 悬停状态
const hoveringSessionId = ref<string | null>(null)

// 格式化时间
const formatTime = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) {
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } else if (days === 1) {
    return '昨天'
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }
}

// 获取显示标题
const getDisplayTitle = (session: Session) => {
  return session.title || '新对话'
}

// 开始编辑
const startEditing = (session: Session) => {
  editingSessionId.value = session.id
  editingTitle.value = session.title || ''
}

// 保存编辑
const saveEditing = () => {
  if (!editingSessionId.value) return
  
  const trimmedTitle = editingTitle.value.trim()
  if (!trimmedTitle) {
    ElMessage.warning('标题不能为空')
    return
  }
  
  emit('rename', editingSessionId.value, trimmedTitle)
  cancelEditing()
}

// 取消编辑
const cancelEditing = () => {
  editingSessionId.value = null
  editingTitle.value = ''
}

// 处理编辑输入框按键
const handleEditKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter') {
    e.preventDefault()
    saveEditing()
  } else if (e.key === 'Escape') {
    cancelEditing()
  }
}

// 确认删除
const confirmDelete = async (session: Session) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除会话"${getDisplayTitle(session)}"吗？删除后无法恢复。`,
      '删除确认',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    emit('delete', session.id)
  } catch {
    // 用户取消
  }
}

// 选择会话
const selectSession = (sessionId: string) => {
  if (editingSessionId.value === sessionId) return
  emit('select', sessionId)
}
</script>

<template>
  <div class="session-sidebar">
    <!-- 新建会话按钮 -->
    <div class="sidebar-header">
      <button class="new-session-btn" @click="emit('create')" :disabled="loading">
        <el-icon><Plus /></el-icon>
        <span>新对话</span>
      </button>
    </div>
    
    <!-- 会话列表 -->
    <div class="session-list" v-loading="loading">
      <div
        v-for="session in sessions"
        :key="session.id"
        class="session-item"
        :class="{ active: session.id === activeSessionId }"
        @click="selectSession(session.id)"
        @mouseenter="hoveringSessionId = session.id"
        @mouseleave="hoveringSessionId = null"
      >
        <!-- 编辑模式 -->
        <div v-if="editingSessionId === session.id" class="session-edit">
          <input
            v-model="editingTitle"
            class="edit-input"
            @keydown="handleEditKeydown"
            @blur="saveEditing"
            @click.stop
            ref="editInput"
            autofocus
          />
        </div>
        
        <!-- 显示模式 -->
        <template v-else>
          <div class="session-content">
            <div class="session-title">{{ getDisplayTitle(session) }}</div>
            <div class="session-meta">
              <span class="session-time">{{ formatTime(session.updated_at) }}</span>
              <span v-if="session.message_count > 0" class="session-count">
                {{ session.message_count }} 条消息
              </span>
            </div>
          </div>
          
          <!-- 操作按钮 -->
          <div 
            class="session-actions"
            :class="{ visible: hoveringSessionId === session.id }"
            @click.stop
          >
            <el-tooltip content="重命名" placement="top">
              <button class="action-btn" @click="startEditing(session)">
                <el-icon><Edit /></el-icon>
              </button>
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <button class="action-btn delete" @click="confirmDelete(session)">
                <el-icon><Delete /></el-icon>
              </button>
            </el-tooltip>
          </div>
        </template>
      </div>
      
      <!-- 空状态 -->
      <div v-if="!loading && sessions.length === 0" class="empty-state">
        <el-icon :size="32"><ChatDotRound /></el-icon>
        <p>暂无对话记录</p>
        <p class="hint">点击上方按钮开始新对话</p>
      </div>
    </div>
  </div>
</template>


<style lang="scss" scoped>
.session-sidebar {
  width: 280px;
  height: 100%;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.new-session-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  
  &:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(88, 141, 239, 0.35);
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  
  &::-webkit-scrollbar {
    width: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(0, 0, 0, 0.1);
    border-radius: 2px;
  }
}

.session-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  
  &:hover {
    background: rgba(88, 141, 239, 0.06);
  }
  
  &.active {
    background: linear-gradient(90deg, rgba(0, 212, 255, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%);
    
    .session-title {
      color: #5b8def;
      font-weight: 500;
    }
  }
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 14px;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.session-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #999;
}

.session-count {
  &::before {
    content: '·';
    margin-right: 8px;
  }
}

.session-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
  
  &.visible {
    opacity: 1;
  }
}

.action-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: #f5f5f5;
    color: #333;
  }
  
  &.delete:hover {
    background: #fff1f0;
    border-color: #ffccc7;
    color: #ff4d4f;
  }
}

.session-edit {
  flex: 1;
}

.edit-input {
  width: 100%;
  padding: 6px 10px;
  border: 2px solid #5b8def;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  background: #fff;
  
  &:focus {
    box-shadow: 0 0 0 3px rgba(88, 141, 239, 0.15);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #999;
  
  .el-icon {
    margin-bottom: 12px;
    color: #ddd;
  }
  
  p {
    margin: 0;
    font-size: 14px;
  }
  
  .hint {
    font-size: 12px;
    margin-top: 8px;
    color: #bbb;
  }
}
</style>
