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
export interface AgentDoneData {
  success: boolean
  message?: string
  agent?: string
  user_id?: number
}

export interface ImageData {
  imageData: string  // data:image/png;base64,xxx 格式
  format: string
}

export interface ImageMeta {
  diagram_id: string
  title: string
  format: string
  xml: string  // 原始 XML，可用于下载 .drawio 文件
}

export interface ChartData {
  chart_type: string
  chart_name: string
  option: any  // EChart option 对象
  raw_data: any[]
  total_count: number
}

export interface AgentStreamCallbacks {
  onAnswer?: (chunk: string) => void
  onFlowchart?: (data: { svgContent: string; diagramId: string; title: string }) => void
  onImage?: (data: ImageData) => void
  onImageMeta?: (meta: ImageMeta) => void
  onChart?: (data: ChartData) => void
  onDone?: (data?: AgentDoneData) => void
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
  
  try {
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
    let receivedDone = false

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
          } else if (currentEvent === 'answer_base64') {
            // Base64 解码（支持 UTF-8 中文和换行符）
            try {
              const binaryStr = atob(currentData)
              const bytes = Uint8Array.from(binaryStr, c => c.charCodeAt(0))
              const decodedText = new TextDecoder('utf-8').decode(bytes)
              callbacks.onAnswer?.(decodedText)
            } catch (e) {
              console.error('解码 answer_base64 失败:', e)
              callbacks.onAnswer?.(currentData)
            }
          } else if (currentEvent === 'flowchart') {
            try {
              // Base64 解码（支持 UTF-8 中文）- 旧版兼容
              const binaryStr = atob(currentData)
              const bytes = Uint8Array.from(binaryStr, c => c.charCodeAt(0))
              const jsonStr = new TextDecoder('utf-8').decode(bytes)
              const flowchartData = JSON.parse(jsonStr)
              console.log('[SSE] 收到流程图数据:', flowchartData)
              callbacks.onFlowchart?.({
                svgContent: flowchartData.svg_content,
                diagramId: flowchartData.diagram_id,
                title: flowchartData.title || ''
              })
            } catch (e) {
              console.error('解析流程图数据失败:', e, currentData)
            }
          } else if (currentEvent === 'image') {
            // 图片数据（Base64 PNG）
            console.log('[SSE] 收到图片数据，大小:', currentData.length)
            callbacks.onImage?.({
              imageData: `data:image/png;base64,${currentData}`,
              format: 'png'
            })
          } else if (currentEvent === 'image_meta') {
            // 图片元信息（Base64 编码的 JSON）
            try {
              const binaryStr = atob(currentData)
              const bytes = Uint8Array.from(binaryStr, c => c.charCodeAt(0))
              const jsonStr = new TextDecoder('utf-8').decode(bytes)
              const meta = JSON.parse(jsonStr)
              console.log('[SSE] 收到图片元信息:', meta)
              callbacks.onImageMeta?.(meta)
            } catch (e) {
              console.error('解析图片元信息失败:', e)
            }
          } else if (currentEvent === 'chart') {
            // 图表数据（Base64 编码的 JSON）
            try {
              const binaryStr = atob(currentData)
              const bytes = Uint8Array.from(binaryStr, c => c.charCodeAt(0))
              const jsonStr = new TextDecoder('utf-8').decode(bytes)
              const chartData = JSON.parse(jsonStr)
              console.log('[SSE] 收到图表数据:', chartData)
              callbacks.onChart?.(chartData)
            } catch (e) {
              console.error('解析图表数据失败:', e)
            }
          } else if (currentEvent === 'done') {
            receivedDone = true
            try {
              const doneData = JSON.parse(currentData)
              console.log('[SSE] 任务完成:', doneData)
              callbacks.onAgentUsed?.(doneData.agent)
              // 传递完整的 done 数据，包含 success 和 message
              callbacks.onDone?.(doneData)
            } catch (e) {
              callbacks.onDone?.()
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
    
    // 如果流结束但没有收到 done 事件，也要调用 onDone
    if (!receivedDone) {
      console.log('[SSE] 流结束但未收到 done 事件，自动完成')
      callbacks.onDone?.()
    }
  } catch (error) {
    console.error('[SSE] 连接错误:', error)
    callbacks.onError?.('连接中断，请重试')
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

// ==================== 财务加班管理接口 ====================

export interface OvertimeRecord {
  id: number
  employee_name: string
  job_title: string
  job_level: string
  overtime_hours: number
  overtime_minutes: number
  overtime_days: number
  overtime_rate: number
  overtime_amount: number
  overtime_detail: string
  attendance_month: string
  created_at: string
  updated_at: string
}

export interface OvertimeStats {
  total_employees: number
  overtime_employees: number
  total_hours: number
  total_days: number
  total_amount: number
  avg_hours: number
}

export interface LevelStats {
  job_level: string
  count: number
  total_hours: number
  total_amount: number
}

export interface TopEmployee {
  employee_name: string
  job_title: string
  job_level: string
  overtime_hours: number
  overtime_amount: number
}

export interface OvertimeStatsResponse {
  success: boolean
  data: {
    stats: OvertimeStats
    months: string[]
    level_stats: LevelStats[]
    top_employees: TopEmployee[]
  }
}

// 上传考勤表
export const uploadAttendance = (file: File, month?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  if (month) {
    formData.append('month', month)
  }
  return api.post('/financial/upload-attendance', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 获取加班记录列表
export const getOvertimeRecords = (params: {
  page?: number
  page_size?: number
  month?: string
  keyword?: string
  sort_field?: string
  sort_order?: string
}): Promise<{
  success: boolean
  data: OvertimeRecord[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}> => {
  return api.get('/financial/overtime-records', { params })
}

// 获取加班统计数据
export const getOvertimeStats = (month?: string): Promise<OvertimeStatsResponse> => {
  return api.get('/financial/overtime-stats', { params: { month } })
}

// 删除加班记录
export const deleteOvertimeRecords = (params: {
  ids?: number[]
  month?: string
}) => {
  return api.delete('/financial/overtime-records', { params })
}

// ==================== 考勤扣款管理接口 ====================

export interface DeductionRecord {
  id: number
  employee_name: string
  job_title: string
  job_level: string
  level_type: string
  total_late_count: number
  late_within_10_count: number
  late_over_10_count: number
  late_over_60_count: number
  morning_missing_count: number
  evening_missing_count: number
  early_leave_count: number
  total_deduction: number
  attendance_month: string
  created_at: string
  updated_at: string
}

export interface DeductionStats {
  total_employees: number
  deduction_employees: number
  total_late_count: number
  late_within_10_count: number
  late_over_10_count: number
  late_over_60_count: number
  morning_missing_count: number
  evening_missing_count: number
  early_leave_count: number
  total_deduction: number
}

export interface LevelDeductionStats {
  level_type: string
  count: number
  total_late: number
  total_deduction: number
}

export interface TopDeductionEmployee {
  employee_name: string
  job_title: string
  level_type: string
  total_late_count: number
  total_deduction: number
}

export interface DeductionStatsResponse {
  success: boolean
  data: {
    stats: DeductionStats
    months: string[]
    level_stats: LevelDeductionStats[]
    top_employees: TopDeductionEmployee[]
  }
}

// 上传考勤表计算扣款
export const uploadAttendanceDeduction = (file: File, month?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  if (month) {
    formData.append('month', month)
  }
  return api.post('/financial/attendance/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 获取考勤扣款记录列表
export const getDeductionRecords = (params: {
  page?: number
  page_size?: number
  month?: string
  keyword?: string
  sort_field?: string
  sort_order?: string
}): Promise<{
  success: boolean
  data: DeductionRecord[]
  pagination: {
    page: number
    page_size: number
    total: number
    total_pages: number
  }
}> => {
  return api.get('/financial/attendance/records', { params })
}

// 获取考勤扣款统计数据
export const getDeductionStats = (month?: string): Promise<DeductionStatsResponse> => {
  return api.get('/financial/attendance/stats', { params: { month } })
}

// 删除考勤扣款记录
export const deleteDeductionRecords = (params: {
  ids?: number[]
  month?: string
}) => {
  return api.delete('/financial/attendance/records', { params })
}

// 导出考勤扣款记录
export const exportDeductionRecords = async (month?: string, keyword?: string) => {
  const params = new URLSearchParams()
  if (month) params.append('month', month)
  if (keyword) params.append('keyword', keyword)
  
  const response = await fetch(`/api/financial/attendance/export?${params.toString()}`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`
    }
  })
  
  if (!response.ok) throw new Error('导出失败')
  
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `attendance_deduction_${month || 'all'}_${Date.now()}.xlsx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

export default api
