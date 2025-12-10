<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { queryQuestionStream, queryAgentStream } from '@/api'
import type { QueryResult } from '@/api'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  time: string
  data?: Partial<QueryResult>
  isStreaming?: boolean
}

const messages = ref<Message[]>([])
const inputText = ref('')
const loading = ref(false)
const chatContainer = ref<HTMLElement>()

// 会话 ID（用于记忆功能，页面加载时生成唯一 ID）
const sessionId = ref<string>(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)

// 模式切换：false = 普通模式（固定流程），true = Agent 模式（智能决策）
const useAgentMode = ref<boolean>(true)

// 初始化欢迎消息
onMounted(() => {
  messages.value.push({
    id: Date.now(),
    role: 'assistant',
    content: '您好！我是智能知识库助手。我可以帮您查询数据、生成报表和回答问题。请问有什么可以帮助您的？',
    time: formatTime(new Date())
  })
})

// 格式化时间
const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

// 滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// 发送消息（SSE 流式模式）
const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  
  // 添加用户消息
  messages.value.push({
    id: Date.now(),
    role: 'user',
    content: text,
    time: formatTime(new Date())
  })
  
  inputText.value = ''
  scrollToBottom()
  
  // 创建助手消息占位符（用于流式更新）
  const assistantMsgId = Date.now() + 1
  const assistantMsg: Message = {
    id: assistantMsgId,
    role: 'assistant',
    content: '',
    time: formatTime(new Date()),
    isStreaming: true,
    data: {}
  }
  messages.value.push(assistantMsg)
  
  // 发送 SSE 请求
  loading.value = true
  try {
    if (useAgentMode.value) {
      // Agent 模式：智能决策，自动调用工具
      await queryAgentStream(text, {
        onAnswer: (chunk: string) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.content += chunk
            scrollToBottom()
          }
        },
        onDone: () => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.isStreaming = false
          }
          loading.value = false
          scrollToBottom()
        },
        onError: (message: string) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.content = message || '抱歉，我无法理解您的问题'
            msg.isStreaming = false
          }
          loading.value = false
          scrollToBottom()
        }
      }, sessionId.value)
    } else {
      // 普通模式：固定流程，返回表格数据
      await queryQuestionStream(text, {
        onAnswer: (chunk: string) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.content += chunk
            scrollToBottom()
          }
        },
        onTable: (table) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.data = { ...msg.data, table, success: true }
            console.log('[Chat] 更新表格数据:', table)
            scrollToBottom()
          }
        },
        onDone: (data) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.isStreaming = false
            msg.data = { ...msg.data, row_count: data.row_count }
          }
          loading.value = false
          scrollToBottom()
        },
        onError: (message: string) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.content = message || '抱歉，我无法理解您的问题'
            msg.isStreaming = false
          }
          loading.value = false
          scrollToBottom()
        }
      }, sessionId.value)
    }
  } catch (error: any) {
    const msg = messages.value.find(m => m.id === assistantMsgId)
    if (msg) {
      msg.content = '抱歉，服务暂时不可用，请稍后重试。'
      msg.isStreaming = false
    }
    ElMessage.error('请求失败')
    loading.value = false
    scrollToBottom()
  }
}

// 处理回车发送
const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}
</script>

<template>
  <div class="chat-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">智能问答</h1>
        <p class="page-subtitle">与知识库进行对话式交互</p>
      </div>
      <div class="mode-switch">
        <span class="mode-label">{{ useAgentMode ? 'Agent 模式' : '普通模式' }}</span>
        <el-switch 
          v-model="useAgentMode" 
          active-text="智能"
          inactive-text="普通"
          :active-color="'#7c3aed'"
        />
        <el-tooltip 
          :content="useAgentMode ? 'Agent 模式：AI 自动决定是否查询数据库' : '普通模式：固定流程，每次都查询数据库并返回表格'"
          placement="bottom"
        >
          <el-icon class="mode-help"><QuestionFilled /></el-icon>
        </el-tooltip>
      </div>
    </div>
    
    <div class="chat-container">
      <!-- 消息列表 -->
      <div class="messages-wrapper" ref="chatContainer">
        <div 
          v-for="msg in messages" 
          :key="msg.id" 
          class="message-item"
          :class="msg.role"
        >
          <div class="message-avatar">
            <el-icon v-if="msg.role === 'assistant'" :size="20" color="#fff">
              <ChatDotRound />
            </el-icon>
            <el-icon v-else :size="20" color="#fff">
              <User />
            </el-icon>
          </div>
          
          <div class="message-content">
            <div class="message-bubble" :class="{ streaming: msg.isStreaming }">
              {{ msg.content }}<span v-if="msg.isStreaming" class="cursor">|</span>
            </div>
            
            <!-- 如果有查询结果，显示表格 -->
            <div v-if="msg.data?.table?.rows && msg.data.table.rows.length > 0" class="result-table">
              <div class="table-header">
                <el-icon><Grid /></el-icon>
                <span>查询结果 ({{ msg.data.table.total || msg.data.row_count || msg.data.table.rows.length }} 条)</span>
              </div>
              <el-table 
                :data="msg.data.table.rows.slice(0, 10)" 
                size="small"
                max-height="300"
                stripe
              >
                <el-table-column 
                  v-for="col in msg.data.table.columns" 
                  :key="col.field"
                  :prop="col.field"
                  :label="col.title"
                  min-width="120"
                  show-overflow-tooltip
                />
              </el-table>
              <div v-if="msg.data.table.total > 10 || msg.data.table.rows.length > 10" class="table-more">
                显示前 10 条，共 {{ msg.data.table.total || msg.data.table.rows.length }} 条数据
              </div>
            </div>
            
            <div class="message-time">{{ msg.time }}</div>
          </div>
        </div>
        
        <!-- 加载中 -->
        <div v-if="loading" class="message-item assistant">
          <div class="message-avatar">
            <el-icon :size="20" color="#fff"><ChatDotRound /></el-icon>
          </div>
          <div class="message-content">
            <div class="message-bubble loading">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入区域 -->
      <div class="input-wrapper">
        <el-input
          v-model="inputText"
          placeholder="输入您的问题... (按 Enter 发送)"
          :disabled="loading"
          @keydown="handleKeydown"
        />
        <el-button 
          type="primary" 
          class="send-btn"
          :loading="loading"
          @click="sendMessage"
        >
          <el-icon><Promotion /></el-icon>
          发送
        </el-button>
      </div>
      
      <div class="input-hint">
        提示：尝试问 "显示销售数据图表" 或 "查询员工业绩数据"
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.chat-page {
  height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #7c3aed;
  margin-bottom: 8px;
}

.page-subtitle {
  font-size: 14px;
  color: #666;
  margin-bottom: 0;
}

.mode-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f5f3ff;
  border-radius: 20px;
  
  .mode-label {
    font-size: 13px;
    font-weight: 500;
    color: #7c3aed;
  }
  
  .mode-help {
    color: #999;
    cursor: help;
    font-size: 16px;
    
    &:hover {
      color: #7c3aed;
    }
  }
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.messages-wrapper {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background: linear-gradient(180deg, #f5f3ff 0%, #fff 100%);
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  
  &.user {
    flex-direction: row-reverse;
    
    .message-avatar {
      background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    }
    
    .message-bubble {
      background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
      color: #fff;
    }
    
    .message-content {
      align-items: flex-end;
    }
  }
  
  &.assistant {
    .message-avatar {
      background: linear-gradient(135deg, #7c3aed 0%, #10b981 100%);
    }
    
    .message-bubble {
      background: #fff;
      color: #333;
      border: 1px solid #f0f0f0;
    }
  }
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

.message-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  
  &.loading {
    display: flex;
    gap: 4px;
    padding: 16px 20px;
    
    .dot {
      width: 8px;
      height: 8px;
      background: #7c3aed;
      border-radius: 50%;
      animation: bounce 1.4s infinite ease-in-out both;
      
      &:nth-child(1) { animation-delay: -0.32s; }
      &:nth-child(2) { animation-delay: -0.16s; }
    }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.sql-block {
  margin-top: 12px;
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  
  .sql-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: #2d2d2d;
    color: #999;
    font-size: 12px;
  }
  
  .sql-code {
    padding: 12px;
    margin: 0;
    color: #9cdcfe;
    font-family: 'Consolas', monospace;
    font-size: 13px;
    overflow-x: auto;
  }
}

.result-table {
  margin-top: 12px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
  
  .table-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 12px;
    background: #f9f9f9;
    color: #666;
    font-size: 12px;
  }
  
  .table-more {
    padding: 8px 12px;
    text-align: center;
    font-size: 12px;
    color: #999;
    background: #f9f9f9;
  }
}

.input-wrapper {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  
  .el-input {
    flex: 1;
    
    :deep(.el-input__wrapper) {
      border-radius: 24px;
      padding: 8px 20px;
    }
  }
  
  .send-btn {
    height: 44px;
    padding: 0 24px;
    border-radius: 22px;
    background: linear-gradient(135deg, #7c3aed 0%, #10b981 100%);
    border: none;
  }
}

.input-hint {
  padding: 0 24px 16px;
  font-size: 12px;
  color: #999;
  text-align: center;
}

// 流式输出光标闪烁效果
.cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: #7c3aed;
  font-weight: bold;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.message-bubble.streaming {
  min-height: 20px;
}
</style>
