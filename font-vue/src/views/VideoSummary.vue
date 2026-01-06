<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { trainManual } from '@/api'

// 步骤定义
const steps = [
  { title: '输入地址', icon: 'VideoCamera' },
  { title: '下载视频', icon: 'Download' },
  { title: 'AI 分析', icon: 'MagicStick' },
  { title: '编辑内容', icon: 'Edit' },
  { title: '完成上传', icon: 'CircleCheck' }
]

// 当前步骤 (0-4)
const currentStep = ref(0)

// 表单数据
const videoUrl = ref('')
const videoTitle = ref('')
const videoAuthor = ref('')
const localVideoPath = ref('')
const videoPlayableUrl = ref('')  // 可直接播放的视频URL
const summaryContent = ref('')
const originalSummary = ref('')

// 状态
const isProcessing = ref(false)
const downloadProgress = ref(0)
const downloadedSize = ref(0)  // 已下载大小（字节）
const totalSize = ref(0)       // 总大小（字节）
const analyzeProgress = ref(0)
const uploadLoading = ref(false)
const errorMessage = ref('')
const hasFailed = ref(false)
const failedStep = ref(0)

// 格式化文件大小
const formatSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// 下载进度显示文本
const downloadProgressText = computed(() => {
  if (totalSize.value > 0) {
    return `${formatSize(downloadedSize.value)} / ${formatSize(totalSize.value)}`
  } else if (downloadedSize.value > 0) {
    return `已下载 ${formatSize(downloadedSize.value)}`
  }
  return ''
})

// 计算属性
const canStartProcess = computed(() => videoUrl.value.trim().length > 0)
const isEdited = computed(() => summaryContent.value !== originalSummary.value)

// 开始处理视频
const startProcess = async () => {
  if (!canStartProcess.value) {
    ElMessage.warning('请输入视频地址')
    return
  }
  
  errorMessage.value = ''
  isProcessing.value = true
  currentStep.value = 1
  downloadProgress.value = 0
  
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch('/api/video-summary/process', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify({ url: videoUrl.value })
    })

    if (!response.ok) {
      throw new Error('请求失败')
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应流')
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
        let eventType = ''
        let eventData = ''
        
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            eventData = line.slice(6)
          }
        }
        
        if (eventType && eventData) {
          handleSSEEvent(eventType, eventData)
        }
      }
    }
  } catch (error: any) {
    console.error('处理视频失败:', error)
    errorMessage.value = error.message || '处理视频时出现错误'
    hasFailed.value = true
    failedStep.value = currentStep.value
    ElMessage.error(errorMessage.value)
  } finally {
    isProcessing.value = false
  }
}

// 处理SSE事件
const handleSSEEvent = (eventType: string, data: string) => {
  try {
    switch (eventType) {
      case 'platform':
        console.log('平台识别:', data)
        break
        
      case 'video_info': {
        const info = JSON.parse(data)
        videoTitle.value = info.title || ''
        videoAuthor.value = info.author || ''
        break
      }
        
      case 'download_start':
        currentStep.value = 1
        downloadProgress.value = 0
        downloadedSize.value = 0
        totalSize.value = 0
        break
        
      case 'download_progress': {
        try {
          const progressData = JSON.parse(data)
          downloadProgress.value = Math.min(progressData.percentage || 0, 99)
          downloadedSize.value = progressData.downloaded || 0
          totalSize.value = progressData.total || 0
        } catch {
          // 兼容旧格式（纯数字）
          downloadProgress.value = Math.min(parseInt(data) || 0, 99)
        }
        break
      }
        
      case 'download_complete': {
        const downloadData = JSON.parse(data)
        localVideoPath.value = downloadData.path || ''
        videoPlayableUrl.value = downloadData.url || ''  // 优先使用返回的可访问URL
        downloadProgress.value = 100
        setTimeout(() => {
          currentStep.value = 2
          analyzeProgress.value = 10
        }, 500)
        break
      }
        
      case 'analyze_start':
        currentStep.value = 2
        analyzeProgress.value = 20
        break
        
      case 'analyze_progress':
        analyzeProgress.value = Math.min(parseInt(data) || 50, 90)
        break
        
      case 'analyze_complete':
        analyzeProgress.value = 100
        break
        
      case 'summary':
        try {
          const binaryStr = atob(data)
          const bytes = Uint8Array.from(binaryStr, c => c.charCodeAt(0))
          const decodedText = new TextDecoder('utf-8').decode(bytes)
          summaryContent.value = decodedText
          originalSummary.value = decodedText
        } catch {
          summaryContent.value = data
          originalSummary.value = data
        }
        setTimeout(() => {
          currentStep.value = 3
        }, 500)
        break
        
      case 'error': {
        const errorData = JSON.parse(data)
        errorMessage.value = errorData.message || '处理失败'
        hasFailed.value = true
        failedStep.value = currentStep.value
        ElMessage.error(errorMessage.value)
        break
      }
        
      case 'done':
        console.log('处理完成')
        break
    }
  } catch (error: any) {
    console.error('处理事件失败:', eventType, error)
    if (eventType === 'error') {
      throw error
    }
  }
}

// 上传到知识库
const uploadToKnowledge = async () => {
  if (!summaryContent.value.trim()) {
    ElMessage.warning('总结内容不能为空')
    return
  }
  
  uploadLoading.value = true
  
  try {
    const title = videoTitle.value || `视频总结_${new Date().toLocaleString()}`
    
    await trainManual({
      type: 'documentation',
      content: summaryContent.value,
      title: title,
      keywords: videoAuthor.value ? `视频,${videoAuthor.value}` : '视频总结',
      tags: '视频总结,AI分析'
    })
    
    ElMessage.success('上传知识库成功！')
    currentStep.value = 4
  } catch (error: any) {
    console.error('上传失败:', error)
    ElMessage.error(error.message || '上传知识库失败')
  } finally {
    uploadLoading.value = false
  }
}

// 返回编辑
const backToEdit = () => {
  currentStep.value = 3
}

// 处理新视频
const startNewVideo = () => {
  currentStep.value = 0
  videoUrl.value = ''
  videoTitle.value = ''
  videoAuthor.value = ''
  localVideoPath.value = ''
  videoPlayableUrl.value = ''
  summaryContent.value = ''
  originalSummary.value = ''
  downloadProgress.value = 0
  downloadedSize.value = 0
  totalSize.value = 0
  analyzeProgress.value = 0
  errorMessage.value = ''
  hasFailed.value = false
  failedStep.value = 0
}

// 重置编辑内容
const resetContent = () => {
  summaryContent.value = originalSummary.value
}

// 获取视频播放URL
const videoPlayUrl = computed(() => {
  // 优先使用后端返回的可直接访问的URL
  if (videoPlayableUrl.value) return videoPlayableUrl.value
  // 降级使用API播放
  if (!localVideoPath.value) return ''
  return `/api/video-summary/play?path=${encodeURIComponent(localVideoPath.value)}`
})
</script>

<template>
  <div class="video-summary-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-icon">
        <el-icon :size="32"><VideoCamera /></el-icon>
      </div>
      <div class="header-text">
        <h1>视界拾贝</h1>
        <p>智能识别视频内容，自动生成知识库文档</p>
      </div>
    </div>

    <!-- 步骤条 -->
    <div class="steps-container">
      <div class="steps-wrapper">
        <div 
          v-for="(step, index) in steps" 
          :key="index"
          class="step-item"
          :class="{ active: currentStep === index, completed: currentStep > index }"
        >
          <div class="step-icon">
            <el-icon v-if="currentStep > index" :size="20"><CircleCheck /></el-icon>
            <el-icon v-else :size="20">
              <VideoCamera v-if="index === 0" />
              <Download v-else-if="index === 1" />
              <MagicStick v-else-if="index === 2" />
              <Edit v-else-if="index === 3" />
              <CircleCheck v-else />
            </el-icon>
          </div>
          <span class="step-title">{{ step.title }}</span>
          <div v-if="index < steps.length - 1" class="step-line" />
        </div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-container">
      <!-- 步骤1: 输入视频地址 -->
      <div v-if="currentStep === 0" class="step-content step-input">
        <div class="input-card">
          <h3>步骤 1: 输入视频地址</h3>
          <div class="form-item">
            <label>视频 URL</label>
            <el-input
              v-model="videoUrl"
              placeholder="https://example.com/video.mp4"
              size="large"
              clearable
              :disabled="isProcessing"
            >
              <template #prefix>
                <el-icon><Link /></el-icon>
              </template>
            </el-input>
            <p class="form-tip">支持抖音、B站、小红书、视频号等平台链接</p>
          </div>
          <el-button
            type="primary"
            size="large"
            class="start-btn"
            :disabled="!canStartProcess"
            :loading="isProcessing"
            @click="startProcess"
          >
            开始处理
          </el-button>
        </div>
      </div>

      <!-- 步骤2: 下载视频 -->
      <div v-if="currentStep === 1" class="step-content step-download">
        <div class="loading-card" :class="{ 'has-error': hasFailed && failedStep === 1 }">
          <div class="loading-animation">
            <el-icon v-if="hasFailed && failedStep === 1" class="error-icon" :size="64"><CircleClose /></el-icon>
            <el-icon v-else class="rotating" :size="64"><Loading /></el-icon>
          </div>
          <h3>{{ hasFailed && failedStep === 1 ? '下载失败' : '正在下载视频...' }}</h3>
          <p class="loading-tip">{{ hasFailed && failedStep === 1 ? errorMessage : (videoTitle || '获取视频信息中') }}</p>
          <template v-if="!(hasFailed && failedStep === 1)">
            <el-progress :percentage="downloadProgress" :stroke-width="8" :show-text="true">
              <template #default="{ percentage }">
                <span class="progress-text">{{ percentage }}%</span>
              </template>
            </el-progress>
            <p v-if="downloadProgressText" class="size-info">{{ downloadProgressText }}</p>
          </template>
          <div v-if="hasFailed && failedStep === 1" class="error-actions">
            <el-button size="large" @click="startNewVideo">
              <el-icon><RefreshRight /></el-icon>
              重新开始
            </el-button>
          </div>
        </div>
      </div>

      <!-- 步骤3: 分析视频 -->
      <div v-if="currentStep === 2" class="step-content step-analyze">
        <div class="loading-card" :class="{ 'has-error': hasFailed && failedStep === 2 }">
          <div class="loading-animation">
            <el-icon v-if="hasFailed && failedStep === 2" class="error-icon" :size="64"><CircleClose /></el-icon>
            <el-icon v-else class="rotating" :size="64"><MagicStick /></el-icon>
          </div>
          <h3>{{ hasFailed && failedStep === 2 ? 'AI 分析失败' : 'AI 正在分析视频内容...' }}</h3>
          <p class="loading-tip">{{ hasFailed && failedStep === 2 ? errorMessage : '使用多模态模型智能识别视频内容' }}</p>
          <el-progress v-if="!(hasFailed && failedStep === 2)" :percentage="analyzeProgress" :stroke-width="8" :show-text="true" />
          <div v-if="hasFailed && failedStep === 2" class="error-actions">
            <el-button size="large" @click="startNewVideo">
              <el-icon><RefreshRight /></el-icon>
              重新开始
            </el-button>
          </div>
        </div>
      </div>

      <!-- 步骤4: 编辑内容 -->
      <div v-if="currentStep === 3" class="step-content step-edit">
        <div class="edit-layout">
          <!-- 左侧：视频播放 -->
          <div class="video-panel">
            <div class="panel-header">
              <el-icon><VideoCamera /></el-icon>
              <span>视频预览</span>
            </div>
            <div class="video-wrapper">
              <video v-if="localVideoPath" :src="videoPlayUrl" controls class="video-player" />
              <div v-else class="video-placeholder">
                <el-icon :size="48"><VideoCamera /></el-icon>
                <p>视频加载中...</p>
              </div>
            </div>
            <div class="video-info" v-if="videoTitle || videoAuthor">
              <p v-if="videoTitle" class="video-title">{{ videoTitle }}</p>
              <p v-if="videoAuthor" class="video-author">作者: {{ videoAuthor }}</p>
            </div>
          </div>

          <!-- 右侧：内容编辑 -->
          <div class="editor-panel">
            <div class="panel-header">
              <el-icon><Edit /></el-icon>
              <span>内容总结</span>
              <div class="header-actions">
                <el-button v-if="isEdited" size="small" @click="resetContent">重置</el-button>
              </div>
            </div>
            <div class="editor-wrapper">
              <el-input
                v-model="summaryContent"
                type="textarea"
                :rows="18"
                placeholder="AI生成的视频总结将显示在这里，您可以自行编辑修改..."
                resize="none"
              />
            </div>
            <div class="editor-footer">
              <span class="char-count">{{ summaryContent.length }} 字</span>
              <el-button type="primary" size="large" :loading="uploadLoading" @click="uploadToKnowledge">
                <el-icon><Upload /></el-icon>
                一键上传知识库
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 步骤5: 上传成功 -->
      <div v-if="currentStep === 4" class="step-content step-success">
        <div class="success-card">
          <div class="success-icon">
            <el-icon :size="80"><CircleCheck /></el-icon>
          </div>
          <h2>上传成功！</h2>
          <p class="success-tip">视频内容已成功添加到知识库</p>
          <div class="success-actions">
            <el-button size="large" @click="backToEdit">
              <el-icon><Back /></el-icon>
              返回编辑
            </el-button>
            <el-button type="primary" size="large" @click="startNewVideo">
              <el-icon><Plus /></el-icon>
              处理新视频
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.video-summary-page {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
  
  .header-icon {
    width: 64px;
    height: 64px;
    border-radius: 16px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    box-shadow: 0 8px 24px rgba(102, 126, 234, 0.3);
  }
  
  .header-text {
    h1 {
      font-size: 24px;
      font-weight: 700;
      color: #1f2937;
      margin: 0 0 4px 0;
    }
    p {
      font-size: 14px;
      color: #6b7280;
      margin: 0;
    }
  }
}

.steps-container {
  margin-bottom: 32px;
  padding: 0 20px;
}

.steps-wrapper {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  gap: 100px;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  
  .step-icon {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #9ca3af;
    transition: all 0.3s ease;
    z-index: 1;
  }
  
  .step-title {
    margin-top: 12px;
    white-space: nowrap;
    font-size: 12px;
    color: #9ca3af;
    transition: color 0.3s ease;
  }
  
  .step-line {
    position: absolute;
    top: 22px;
    left: calc(50% + 30px);
    width: 120px;
    height: 2px;
    background: #e5e7eb;
    transition: background 0.3s ease;
  }
  
  &.active {
    .step-icon {
      background: #2B7FFF;
      color: #fff;
      box-shadow: 0 0 0 0 rgba(43, 127, 255, 0.6);
      animation: breathe 2s ease-in-out infinite;
    }
    .step-title {
      color: #2B7FFF;
      font-weight: 600;
    }
  }
  
  &.completed {
    .step-icon {
      background: #00C950;
      color: #fff;
    }
    .step-title {
      color: #00C950;
    }
    .step-line {
      background: #00C950;
    }
  }
}

.content-container {
  max-width: 1200px;
  margin: 0 auto;
}

.step-input {
  .input-card {
    background: #fff;
    border-radius: 20px;
    padding: 40px;
    max-width: 600px;
    margin: 40px auto;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    
    h3 {
      font-size: 18px;
      font-weight: 600;
      color: #1f2937;
      margin: 0 0 24px 0;
    }
    
    .form-item {
      margin-bottom: 24px;
      label {
        display: block;
        font-size: 14px;
        font-weight: 500;
        color: #374151;
        margin-bottom: 8px;
      }
      .form-tip {
        font-size: 12px;
        color: #9ca3af;
        margin: 8px 0 0 0;
      }
    }
    
    .start-btn {
      width: 100%;
      height: 48px;
      font-size: 16px;
      background: #2B7FFF;
      border: none;
      border-radius: 24px;
      transition: all 0.3s ease;
      
      &:hover:not(:disabled) {
        background: #1a6fe8;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(43, 127, 255, 0.4);
      }
      
      &:disabled {
        background: #d1e3ff;
        color: #9fc5ff;
        cursor: not-allowed;
        box-shadow: none;
      }
    }
  }
}

.step-download,
.step-analyze {
  .loading-card {
    background: #fff;
    border-radius: 20px;
    padding: 60px 40px;
    max-width: 500px;
    margin: 40px auto;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    
    &.has-error {
      border: 2px solid #fee2e2;
      
      .loading-animation {
        color: #ef4444;
      }
      
      h3 {
        color: #ef4444;
      }
      
      .loading-tip {
        color: #f87171;
      }
    }
    
    .loading-animation {
      margin-bottom: 24px;
      color: #667eea;
    }
    
    .error-icon {
      animation: shake 0.5s ease-in-out;
    }
    
    h3 {
      font-size: 20px;
      font-weight: 600;
      color: #1f2937;
      margin: 0 0 8px 0;
    }
    
    .loading-tip {
      font-size: 14px;
      color: #6b7280;
      margin: 0 0 24px 0;
    }
    
    .error-actions {
      margin-top: 24px;
      
      .el-button {
        border-radius: 20px;
      }
    }
    
    :deep(.el-progress) {
      .el-progress-bar__outer {
        background: #e5e7eb;
      }
      .el-progress-bar__inner {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      }
    }
    
    .progress-text {
      font-size: 14px;
      font-weight: 600;
      color: #667eea;
    }
    
    .size-info {
      font-size: 13px;
      color: #6b7280;
      margin: 12px 0 0 0;
      font-family: 'Monaco', 'Menlo', monospace;
    }
  }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%, 60% { transform: translateX(-5px); }
  40%, 80% { transform: translateX(5px); }
}

.rotating {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes breathe {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(43, 127, 255, 0.6);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 20px 4px rgba(43, 127, 255, 0.4);
  }
}

.step-edit {
  .edit-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    @media (max-width: 900px) {
      grid-template-columns: 1fr;
    }
  }
  
  .video-panel,
  .editor-panel {
    background: #fff;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  }
  
  .panel-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 16px 20px;
    border-bottom: 1px solid #f3f4f6;
    font-weight: 600;
    color: #374151;
    .header-actions {
      margin-left: auto;
    }
  }
  
  .video-wrapper {
    aspect-ratio: 16 / 9;
    background: #000;
    .video-player {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
    .video-placeholder {
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #6b7280;
      gap: 12px;
    }
  }
  
  .video-info {
    padding: 16px 20px;
    .video-title {
      font-size: 14px;
      font-weight: 600;
      color: #1f2937;
      margin: 0 0 4px 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .video-author {
      font-size: 12px;
      color: #6b7280;
      margin: 0;
    }
  }
  
  .editor-wrapper {
    padding: 16px 20px;
    :deep(.el-textarea__inner) {
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 14px;
      line-height: 1.8;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      &:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
      }
    }
  }
  
  .editor-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-top: 1px solid #f3f4f6;
    .char-count {
      font-size: 12px;
      color: #9ca3af;
    }
    .el-button--primary {
      background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
      border: none;
    }
  }
}

.step-success {
  .success-card {
    background: #fff;
    border-radius: 20px;
    padding: 60px 40px;
    max-width: 500px;
    margin: 40px auto;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    
    .success-icon {
      color: #00C950;
      margin-bottom: 24px;
    }
    
    h2 {
      font-size: 24px;
      font-weight: 700;
      color: #1f2937;
      margin: 0 0 8px 0;
    }
    
    .success-tip {
      font-size: 14px;
      color: #6b7280;
      margin: 0 0 32px 0;
    }
    
    .success-actions {
      display: flex;
      gap: 16px;
      justify-content: center;
      .el-button--primary {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border: none;
      }
    }
  }
}
</style>
