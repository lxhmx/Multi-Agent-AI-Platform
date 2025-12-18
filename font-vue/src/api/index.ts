import axios from 'axios'
import type { AxiosResponse } from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：附加 Authorization 头
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    console.error('API Error:', error)
    // 401 未授权，跳转到登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// 类型定义
export interface ApiResponse<T = any> {
  success: boolean
  message?: string
  data?: T
}

export interface TrainingStats {
  total: number
  sql_count: number
  ddl_count: number
  doc_count: number
}

export interface TrainingDataItem {
  id: string
  training_data_type: string
  question?: string
  content?: string
  created_at?: string
  tags?: string[]
}

export interface TrainingActivity {
  date: string
  count: number
}

export interface QueryResult {
  success: boolean
  question: string
  answer: string
  sql: string
  table?: {
    columns: Array<{ field: string; title: string }>
    rows: any[]
    total: number
  }
  chart?: any
  row_count: number
  message?: string
}

// API 方法

// 上传文件
export const uploadFile = (file: File, trainType?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  if (trainType) {
    formData.append('train_type', trainType)
  }
  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 手动训练
export const trainManual = (data: {
  type: 'sql' | 'ddl' | 'documentation'
  content: string
  title?: string
  keywords?: string
  tags?: string
}) => {
  return api.post('/train-manual', data)
}

// ==================== 数据管理接口 ====================

// 获取训练统计
export const getTrainingStats = (): Promise<{ success: boolean; stats: TrainingStats }> => {
  return api.get('/data-manage/stats')
}

// 获取训练活跃度
export const getTrainingActivity = (days = 7): Promise<{ success: boolean; data: TrainingActivity[] }> => {
  return api.get('/data-manage/activity', { params: { days } })
}

// 获取训练文件列表
export const getTrainingFiles = (params: {
  page?: number
  page_size?: number
  train_type?: string
  file_type?: string
  train_status?: string
  keyword?: string
}): Promise<{
  success: boolean
  data: any[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}> => {
  return api.get('/data-manage/files', { params })
}

// 删除训练文件记录
export const deleteTrainingFiles = (data: {
  ids?: number[]
  delete_all?: boolean
}) => {
  return api.delete('/data-manage/files', { data })
}

// 智能问答（普通模式）
export const queryQuestion = (question: string): Promise<QueryResult> => {
  return api.post('/query', { question })
}

// 智能问答（SSE 流式模式）
export interface StreamCallbacks {
  onAnswer?: (chunk: string) => void
  onTable?: (table: QueryResult['table']) => void
  onDone?: (data: { row_count: number }) => void
  onError?: (message: string) => void
}

export const queryQuestionStream = async (
  question: string,
  callbacks: StreamCallbacks,
  sessionId?: string  // 可选的会话 ID，用于启用记忆功能
): Promise<void> => {
  const response = await fetch('/api/query-stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, session_id: sessionId }),
  })

  if (!response.ok) {
    callbacks.onError?.('请求失败')
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    callbacks.onError?.('无法读取响应流')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''
  let currentData = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    
    // 解析 SSE 事件（按双换行分割事件块）
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const lines = part.split('\n')
      currentEvent = ''
      currentData = ''
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          currentData = line.slice(6)
        }
      }
      
      // 处理完整的事件
      if (currentEvent && currentData !== '') {
        if (currentEvent === 'answer') {
          callbacks.onAnswer?.(currentData)
        } else if (currentEvent === 'table') {
          try {
            // Base64 解码（支持 UTF-8 中文）
            const binaryStr = atob(currentData)
            const bytes = Uint8Array.from(binaryStr, c => c.charCodeAt(0))
            const jsonStr = new TextDecoder('utf-8').decode(bytes)
            const tableData = JSON.parse(jsonStr)
            console.log('[SSE] 收到表格数据:', tableData)
            callbacks.onTable?.(tableData)
          } catch (e) {
            console.error('解析表格数据失败:', e, currentData)
          }
        } else if (currentEvent === 'done') {
          try {
            const doneData = JSON.parse(currentData)
            console.log('[SSE] 完成:', doneData)
            callbacks.onDone?.(doneData)
          } catch (e) {
            console.error('解析完成数据失败:', e)
          }
        } else if (currentEvent === 'error') {
          try {
            const errorData = JSON.parse(currentData)
            callbacks.onError?.(errorData.message)
          } catch (e) {
            callbacks.onError?.(currentData)
          }
        }
      }
    }
  }
}

// Agent 模式问答（SSE 流式，自动决定是否查询数据库）
export interface AgentStreamCallbacks {
  onAnswer?: (chunk: string) => void
  onDone?: () => void
  onError?: (message: string) => void
}

export const queryAgentStream = async (
  question: string,
  callbacks: AgentStreamCallbacks,
  sessionId?: string
): Promise<void> => {
  const response = await fetch('/api/query-agent', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, session_id: sessionId }),
  })

  if (!response.ok) {
    callbacks.onError?.('请求失败')
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    callbacks.onError?.('无法读取响应流')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const lines = part.split('\n')
      let currentEvent = ''
      let currentData = ''
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          currentData = line.slice(6)
        }
      }
      
      if (currentEvent && currentData !== '') {
        if (currentEvent === 'answer') {
          callbacks.onAnswer?.(currentData)
        } else if (currentEvent === 'done') {
          callbacks.onDone?.()
        } else if (currentEvent === 'error') {
          try {
            const errorData = JSON.parse(currentData)
            callbacks.onError?.(errorData.message)
          } catch (e) {
            callbacks.onError?.(currentData)
          }
        }
      }
    }
  }
}

// 训练结果类型
export interface TrainResult {
  success: boolean
  message?: string
  trained_count?: number
  skipped_count?: number
  error_count?: number
}

// 训练 SQL 文件
export const trainSql = (): Promise<TrainResult> => {
  return api.post('/train-sql')
}

// 训练文档
export const trainDocument = (docTypes?: string[]): Promise<TrainResult> => {
  return api.post('/train-document', { doc_types: docTypes })
}

// ==================== 智能体接口 ====================

export interface AgentInfo {
  name: string
  description: string
}

// 获取智能体列表
export const getAgentList = (): Promise<{ agents: AgentInfo[] }> => {
  return api.get('/agent/list')
}

// 智能体对话（SSE 流式，支持指定智能体或自动路由）
export const queryAgentChatStream = async (
  question: string,
  callbacks: AgentStreamCallbacks & { onAgentUsed?: (agentName: string) => void },
  sessionId?: string,
  agentName?: string  // 可选，不传则自动路由
): Promise<void> => {
  const token = localStorage.getItem('access_token')
  const response = await fetch('/api/agent/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify({ 
      question, 
      session_id: sessionId,
      agent_name: agentName || null  // null 表示自动路由
    }),
  })

  if (!response.ok) {
    callbacks.onError?.('请求失败')
    return
  }

  const reader = response.body?.getReader()
  if (!reader) {
    callbacks.onError?.('无法读取响应流')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const part of parts) {
      const lines = part.split('\n')
      let currentEvent = ''
      let currentData = ''
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          currentData = line.slice(6)
        }
      }
      
      if (currentEvent && currentData !== '') {
        if (currentEvent === 'answer') {
          callbacks.onAnswer?.(currentData)
        } else if (currentEvent === 'done') {
          try {
            const doneData = JSON.parse(currentData)
            callbacks.onAgentUsed?.(doneData.agent)
          } catch (e) {}
          callbacks.onDone?.()
        } else if (currentEvent === 'error') {
          try {
            const errorData = JSON.parse(currentData)
            callbacks.onError?.(errorData.message)
          } catch (e) {
            callbacks.onError?.(currentData)
          }
        }
      }
    }
  }
}

// ==================== 会话管理接口 ====================

export interface Session {
  id: string
  title: string | null
  created_at: string
  updated_at: string
  message_count: number
}

export interface SessionMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface SessionDetail extends Session {
  messages: SessionMessage[]
}

export interface SessionListResponse {
  sessions: Session[]
  total: number
  page: number
  page_size: number
}

// 获取会话列表
export const getSessions = (page = 1, pageSize = 20): Promise<SessionListResponse> => {
  return api.get('/sessions', { params: { page, page_size: pageSize } })
}

// 创建新会话
export const createSession = (title?: string): Promise<Session> => {
  return api.post('/sessions', { title })
}

// 获取会话详情
export const getSessionDetail = (id: string): Promise<SessionDetail> => {
  return api.get(`/sessions/${id}`)
}

// 更新会话标题
export const updateSessionTitle = (id: string, title: string): Promise<Session> => {
  return api.put(`/sessions/${id}`, { title })
}

// 删除会话
export const deleteSession = (id: string): Promise<void> => {
  return api.delete(`/sessions/${id}`)
}

// 添加消息到会话
export const addMessage = (sessionId: string, role: 'user' | 'assistant', content: string): Promise<SessionMessage> => {
  return api.post(`/sessions/${sessionId}/messages`, { role, content })
}

export default api
