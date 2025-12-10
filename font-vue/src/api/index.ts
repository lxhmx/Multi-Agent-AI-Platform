import axios from 'axios'
import type { AxiosResponse } from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器
api.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    console.error('API Error:', error)
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

// 智能问答
export const queryQuestion = (question: string): Promise<QueryResult> => {
  return api.post('/query', { question })
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

export default api
