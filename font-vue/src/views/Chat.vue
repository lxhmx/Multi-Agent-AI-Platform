<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  queryQuestionStream, queryAgentStream,
  getSessions, createSession, getSessionDetail, 
  updateSessionTitle, deleteSession, addMessage
} from '@/api'
import type { QueryResult, Session, SessionMessage } from '@/api'
import SessionSidebar from '@/components/SessionSidebar.vue'

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

// 会话管理状态
const sessions = ref<Session[]>([])
const currentSessionId = ref<string>('')
const sidebarLoading = ref(false)

// 模式切换：false = 普通模式（固定流程），true = Agent 模式（智能决策）
const useAgentMode = ref<boolean>(true)

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

// 加载会话列表
const loadSessions = async () => {
  sidebarLoading.value = true
  try {
    const response = await getSessions()
    sessions.value = response.sessions
  } catch (error) {
    console.error('加载会话列表失败:', error)
  } finally {
    sidebarLoading.value = false
  }
}

// 加载会话详情
const loadSessionDetail = async (sessionId: string) => {
  try {
    const detail = await getSessionDetail(sessionId)
    messages.value = detail.messages.map((m: SessionMessage) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      time: formatTime(new Date(m.created_at))
    }))
    scrollToBottom()
  } catch (error) {
    console.error('加载会话详情失败:', error)
    ElMessage.error('加载会话失败')
  }
}

// 选择会话
const handleSelectSession = async (sessionId: string) => {
  if (sessionId === currentSessionId.value) return
  currentSessionId.value = sessionId
  await loadSessionDetail(sessionId)
}

// 创建新会话
const handleCreateSession = async () => {
  try {
    const session = await createSession()
    sessions.value.unshift(session)
    currentSessionId.value = session.id
    messages.value = [{
      id: Date.now(),
      role: 'assistant',
      content: '您好！我是智能知识库助手。我可以帮您查询数据、生成报表和回答问题。请问有什么可以帮助您的？',
      time: formatTime(new Date())
    }]
  } catch (error) {
    console.error('创建会话失败:', error)
    ElMessage.error('创建会话失败')
  }
}

// 重命名会话
const handleRenameSession = async (sessionId: string, newTitle: string) => {
  try {
    await updateSessionTitle(sessionId, newTitle)
    const session = sessions.value.find(s => s.id === sessionId)
    if (session) {
      session.title = newTitle
    }
    ElMessage.success('重命名成功')
  } catch (error) {
    console.error('重命名失败:', error)
    ElMessage.error('重命名失败')
  }
}

// 删除会话
const handleDeleteSession = async (sessionId: string) => {
  try {
    await deleteSession(sessionId)
    const index = sessions.value.findIndex(s => s.id === sessionId)
    if (index !== -1) {
      sessions.value.splice(index, 1)
    }
    
    // 如果删除的是当前会话，自动创建新会话或切换到其他会话
    if (sessionId === currentSessionId.value) {
      if (sessions.value.length > 0) {
        // 切换到第一个会话
        currentSessionId.value = sessions.value[0].id
        await loadSessionDetail(sessions.value[0].id)
      } else {
        // 没有会话了，创建新会话
        await handleCreateSession()
      }
    }
    
    ElMessage.success('删除成功')
  } catch (error) {
    console.error('删除会话失败:', error)
    ElMessage.error('删除失败')
  }
}

// 初始化
onMounted(async () => {
  await loadSessions()
  
  // 如果有会话，加载第一个；否则创建新会话
  if (sessions.value.length > 0) {
    currentSessionId.value = sessions.value[0].id
    await loadSessionDetail(sessions.value[0].id)
  } else {
    await handleCreateSession()
  }
})


// 发送消息（SSE 流式模式）
const sendMessage = async () => {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  
  // 添加用户消息
  const userMsg: Message = {
    id: Date.now(),
    role: 'user',
    content: text,
    time: formatTime(new Date())
  }
  messages.value.push(userMsg)
  
  // 保存用户消息到会话
  if (currentSessionId.value) {
    try {
      await addMessage(currentSessionId.value, 'user', text)
      // 更新会话列表中的时间
      const session = sessions.value.find(s => s.id === currentSessionId.value)
      if (session) {
        session.updated_at = new Date().toISOString()
        session.message_count++
        // 如果没有标题，用第一条消息作为标题
        if (!session.title) {
          session.title = text.length > 50 ? text.substring(0, 50) : text
        }
      }
    } catch (error) {
      console.error('保存用户消息失败:', error)
    }
  }
  
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
  let fullContent = ''
  
  try {
    if (useAgentMode.value) {
      // Agent 模式：智能决策，自动调用工具
      await queryAgentStream(text, {
        onAnswer: (chunk: string) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.content += chunk
            fullContent += chunk
            scrollToBottom()
          }
        },
        onDone: async () => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.isStreaming = false
          }
          // 保存助手消息到会话
          if (currentSessionId.value && fullContent) {
            try {
              await addMessage(currentSessionId.value, 'assistant', fullContent)
              const session = sessions.value.find(s => s.id === currentSessionId.value)
              if (session) {
                session.message_count++
              }
            } catch (error) {
              console.error('保存助手消息失败:', error)
            }
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
      }, currentSessionId.value)
    } else {
      // 普通模式：固定流程，返回表格数据
      await queryQuestionStream(text, {
        onAnswer: (chunk: string) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.content += chunk
            fullContent += chunk
            scrollToBottom()
          }
        },
        onTable: (table) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.data = { ...msg.data, table, success: true }
            scrollToBottom()
          }
        },
        onDone: async (data) => {
          const msg = messages.value.find(m => m.id === assistantMsgId)
          if (msg) {
            msg.isStreaming = false
            msg.data = { ...msg.data, row_count: data.row_count }
          }
          // 保存助手消息到会话
          if (currentSessionId.value && fullContent) {
            try {
              await addMessage(currentSessionId.value, 'assistant', fullContent)
              const session = sessions.value.find(s => s.id === currentSessionId.value)
              if (session) {
                session.message_count++
              }
            } catch (error) {
              console.error('保存助手消息失败:', error)
            }
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
      }, currentSessionId.value)
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
    <!-- 左侧会话侧边栏 -->
    <SessionSidebar
      :sessions="sessions"
      :active-session-id="currentSessionId"
      :loading="sidebarLoading"
      @select="handleSelectSession"
      @create="handleCreateSession"
      @rename="handleRenameSession"
      @delete="handleDeleteSession"
    />
    
    <!-- 右侧聊天区域 -->
    <div class="chat-area">
      <!-- 消息区域 -->
      <div class="messages-area" ref="chatContainer">
        <!-- 欢迎区域（无消息时显示） -->
        <div v-if="messages.length <= 1" class="welcome-section">
          <div class="welcome-icon">
            <el-icon :size="48"><ChatDotRound /></el-icon>
          </div>
          <h2 class="welcome-title">智能数据助手</h2>
          <p class="welcome-desc">我可以帮您查询数据、分析报表、回答问题</p>
          <div class="quick-actions">
            <div class="quick-item" @click="inputText = '查询所有设备信息'">
              <el-icon><Search /></el-icon>
              <span>查询设备信息</span>
            </div>
            <div class="quick-item" @click="inputText = '统计各类型设备数量'">
              <el-icon><DataAnalysis /></el-icon>
              <span>统计设备数量</span>
            </div>
            <div class="quick-item" @click="inputText = '数据库有哪些表'">
              <el-icon><Grid /></el-icon>
              <span>查看数据库结构</span>
            </div>
          </div>
        </div>
        
        <!-- 消息列表 -->
        <div v-else class="messages-list">
          <div 
            v-for="msg in messages" 
            :key="msg.id" 
            class="message-item"
            :class="msg.role"
          >
            <div class="message-avatar">
              <el-icon v-if="msg.role === 'assistant'" :size="18" color="#fff">
                <ChatDotRound />
              </el-icon>
              <el-icon v-else :size="18" color="#fff">
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
        </div>
      </div>
      
      <!-- 底部输入卡片 -->
      <div class="input-card">
        <div class="input-card-inner">
          <!-- 输入框区域 -->
          <div class="input-row">
            <div class="input-field">
              <el-icon class="input-icon"><EditPen /></el-icon>
              <input
                v-model="inputText"
                type="text"
                placeholder="输入您的问题，按 Enter 发送..."
                :disabled="loading"
                @keydown="handleKeydown"
              />
            </div>
            <button 
              class="send-button"
              :class="{ loading: loading }"
              :disabled="loading || !inputText.trim()"
              @click="sendMessage"
            >
              <el-icon v-if="!loading"><Promotion /></el-icon>
              <el-icon v-else class="is-loading"><Loading /></el-icon>
            </button>
          </div>
          
          <!-- 底部工具栏 -->
          <div class="input-toolbar">
            <div class="mode-toggle" @click="useAgentMode = !useAgentMode">
              <div class="mode-indicator" :class="{ active: useAgentMode }">
                <el-icon><MagicStick /></el-icon>
              </div>
              <span class="mode-text">{{ useAgentMode ? 'Agent 智能模式' : '普通查询模式' }}</span>
              <el-tooltip 
                :content="useAgentMode ? 'AI 自动决定是否需要查询数据库' : '每次都执行数据库查询并返回表格'"
                placement="top"
              >
                <el-icon class="mode-help"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
            <div class="toolbar-hint">
              <el-icon><InfoFilled /></el-icon>
              <span>支持自然语言查询数据</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>


<style lang="scss" scoped>
.chat-page {
  height: 100%;
  display: flex;
  background: transparent;
  overflow: hidden;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  min-width: 0;
  overflow: hidden;
}

// ========== 消息区域 ==========
.messages-area {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 24px 24px 140px;
  
  &::-webkit-scrollbar {
    width: 6px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(88, 141, 239, 0.2);
    border-radius: 3px;
  }
}

// ========== 欢迎区域 ==========
.welcome-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  text-align: center;
  animation: fadeIn 0.6s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.welcome-icon {
  width: 100px;
  height: 100px;
  border-radius: 28px;
  background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  margin-bottom: 24px;
  box-shadow: 0 20px 40px rgba(88, 141, 239, 0.3);
}

.welcome-title {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 12px;
}

.welcome-desc {
  font-size: 15px;
  color: #666;
  margin-bottom: 32px;
}

.quick-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.quick-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #fff;
  border-radius: 12px;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid transparent;
  
  .el-icon {
    color: #5b8def;
  }
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(88, 141, 239, 0.2);
    border-color: rgba(88, 141, 239, 0.3);
  }
}

// ========== 消息列表 ==========
.messages-list {
  max-width: 900px;
  margin: 0 auto;
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  animation: slideIn 0.3s ease;
  
  @keyframes slideIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }
  
  &.user {
    flex-direction: row-reverse;
    
    .message-avatar {
      background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    }
    
    .message-bubble {
      background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
      color: #fff;
      border-radius: 18px 18px 4px 18px;
    }
    
    .message-content {
      align-items: flex-end;
    }
  }
  
  &.assistant {
    .message-avatar {
      background: linear-gradient(90deg, #00d4ff 0%, #a855f7 100%);
    }
    
    .message-bubble {
      background: #fff;
      color: #333;
      border-radius: 18px 18px 18px 4px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
    }
  }
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.message-content {
  display: flex;
  flex-direction: column;
  max-width: 75%;
}

.message-bubble {
  padding: 14px 18px;
  font-size: 14px;
  line-height: 1.7;
  
  &.loading {
    display: flex;
    gap: 6px;
    padding: 18px 24px;
    
    .dot {
      width: 8px;
      height: 8px;
      background: linear-gradient(90deg, #00d4ff 0%, #a855f7 100%);
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
  font-size: 11px;
  color: #aaa;
  margin-top: 6px;
}

// ========== 结果表格 ==========
.result-table {
  margin-top: 12px;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  
  .table-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 14px;
    background: linear-gradient(90deg, rgba(0, 212, 255, 0.08) 0%, rgba(168, 85, 247, 0.08) 100%);
    color: #666;
    font-size: 12px;
    font-weight: 500;
  }
  
  .table-more {
    padding: 10px 14px;
    text-align: center;
    font-size: 12px;
    color: #999;
    background: #fafafa;
  }
}

// ========== 底部输入卡片 ==========
.input-card {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 16px 24px 24px;
  background: linear-gradient(to top, rgba(240, 244, 255, 1) 0%, rgba(240, 244, 255, 0) 100%);
}

.input-card-inner {
  max-width: 800px;
  margin: 0 auto;
  background: #fff;
  border-radius: 20px;
  padding: 16px 20px;
  box-shadow: 
    0 4px 24px rgba(88, 141, 239, 0.15),
    0 8px 48px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(88, 141, 239, 0.1);
}

.input-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.input-field {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  background: #f0f4ff;
  border-radius: 14px;
  border: 2px solid transparent;
  transition: all 0.3s ease;
  
  &:focus-within {
    background: #fff;
    border-color: #5b8def;
    box-shadow: 0 0 0 4px rgba(88, 141, 239, 0.1);
  }
  
  .input-icon {
    color: #999;
    font-size: 18px;
  }
  
  input {
    flex: 1;
    height: 48px;
    border: none;
    background: transparent;
    font-size: 15px;
    color: #333;
    outline: none;
    
    &::placeholder {
      color: #aaa;
    }
    
    &:disabled {
      cursor: not-allowed;
    }
  }
}

.send-button {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  border: none;
  background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
  color: #fff;
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  
  &:hover:not(:disabled) {
    transform: scale(1.05);
    box-shadow: 0 8px 24px rgba(88, 141, 239, 0.4);
  }
  
  &:active:not(:disabled) {
    transform: scale(0.95);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  &.loading {
    background: #e5e7eb;
  }
}

.input-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}

.mode-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
  
  &:hover {
    background: rgba(88, 141, 239, 0.06);
  }
  
  .mode-indicator {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #999;
    transition: all 0.3s ease;
    
    &.active {
      background: linear-gradient(90deg, #00d4ff 0%, #a855f7 100%);
      color: #fff;
    }
  }
  
  .mode-text {
    font-size: 13px;
    color: #666;
    font-weight: 500;
  }
  
  .mode-help {
    color: #bbb;
    font-size: 14px;
    
    &:hover {
      color: #5b8def;
    }
  }
}

.toolbar-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #aaa;
  
  .el-icon {
    font-size: 14px;
  }
}

// ========== 光标闪烁 ==========
.cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: #5b8def;
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
