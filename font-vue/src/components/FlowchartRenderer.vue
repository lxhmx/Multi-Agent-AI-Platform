<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { ZoomOut, ZoomIn, FullScreen, Download } from '@element-plus/icons-vue'

const props = defineProps<{
  svgContent: string
  diagramId: string
  title?: string
}>()

const emit = defineEmits<{
  (e: 'download', format: string): void
}>()

// 缩放状态
const scale = ref(1)
const containerRef = ref<HTMLElement>()
const svgContainerRef = ref<HTMLElement>()

// 缩放范围
const MIN_SCALE = 0.25
const MAX_SCALE = 3
const SCALE_STEP = 0.25

// 计算缩放百分比显示
const scalePercent = computed(() => Math.round(scale.value * 100))

// 放大
const zoomIn = () => {
  if (scale.value < MAX_SCALE) {
    scale.value = Math.min(scale.value + SCALE_STEP, MAX_SCALE)
  }
}

// 缩小
const zoomOut = () => {
  if (scale.value > MIN_SCALE) {
    scale.value = Math.max(scale.value - SCALE_STEP, MIN_SCALE)
  }
}

// 重置缩放
const resetZoom = () => {
  scale.value = 1
}

// 适应容器
const fitToContainer = () => {
  if (!containerRef.value || !svgContainerRef.value) return
  
  const container = containerRef.value
  const svgEl = svgContainerRef.value.querySelector('svg')
  if (!svgEl) return
  
  const containerWidth = container.clientWidth - 40
  const containerHeight = container.clientHeight - 40
  const svgWidth = svgEl.clientWidth || 800
  const svgHeight = svgEl.clientHeight || 600
  
  const scaleX = containerWidth / svgWidth
  const scaleY = containerHeight / svgHeight
  scale.value = Math.min(scaleX, scaleY, 1)
}

// 生成下载文件名
const generateFilename = (format: string): string => {
  if (props.title && props.title.trim()) {
    // 清理标题中的非法字符
    const sanitized = props.title
      .trim()
      .replace(/[<>:"/\\|?*]/g, '_')
      .replace(/\s+/g, '_')
      .substring(0, 50)
    return `${sanitized}.${format}`
  }
  // 使用时间戳
  const timestamp = new Date().toISOString().slice(0, 10).replace(/-/g, '')
  return `flowchart_${timestamp}.${format}`
}

// 下载 SVG
const downloadSvg = () => {
  if (!props.svgContent) {
    ElMessage.warning('没有可下载的内容')
    return
  }
  
  try {
    const filename = generateFilename('svg')
    const blob = new Blob([props.svgContent], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
    ElMessage.success('下载成功')
    emit('download', 'svg')
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败，请重试')
  }
}
</script>


<template>
  <div class="flowchart-renderer" ref="containerRef">
    <!-- 工具栏 -->
    <div class="flowchart-toolbar">
      <div class="toolbar-left">
        <span class="diagram-title" v-if="title">{{ title }}</span>
        <span class="diagram-id" v-else>图表 #{{ diagramId.slice(0, 8) }}</span>
      </div>
      
      <div class="toolbar-center">
        <el-tooltip content="缩小" placement="top">
          <button class="toolbar-btn" @click="zoomOut" :disabled="scale <= MIN_SCALE">
            <el-icon><ZoomOut /></el-icon>
          </button>
        </el-tooltip>
        
        <span class="zoom-level" @click="resetZoom">{{ scalePercent }}%</span>
        
        <el-tooltip content="放大" placement="top">
          <button class="toolbar-btn" @click="zoomIn" :disabled="scale >= MAX_SCALE">
            <el-icon><ZoomIn /></el-icon>
          </button>
        </el-tooltip>
        
        <el-tooltip content="适应窗口" placement="top">
          <button class="toolbar-btn" @click="fitToContainer">
            <el-icon><FullScreen /></el-icon>
          </button>
        </el-tooltip>
      </div>
      
      <div class="toolbar-right">
        <el-tooltip content="下载 SVG" placement="top">
          <button class="toolbar-btn download-btn" @click="downloadSvg">
            <el-icon><Download /></el-icon>
            <span>下载</span>
          </button>
        </el-tooltip>
      </div>
    </div>
    
    <!-- SVG 内容区域 -->
    <div class="flowchart-content">
      <div 
        class="svg-container" 
        ref="svgContainerRef"
        :style="{ transform: `scale(${scale})` }"
        v-html="svgContent"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.flowchart-renderer {
  display: flex;
  flex-direction: column;
  background: #fafbfc;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e8e8e8;
  margin-top: 12px;
}

.flowchart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  gap: 12px;
}

.toolbar-left {
  flex: 1;
  min-width: 0;
}

.diagram-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.diagram-id {
  font-size: 12px;
  color: #999;
  font-family: monospace;
}

.toolbar-center {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 10px;
  background: #f5f5f5;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  color: #666;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover:not(:disabled) {
    background: #e8e8e8;
    color: #333;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .el-icon {
    font-size: 16px;
  }
}

.download-btn {
  background: linear-gradient(135deg, #5b8def 0%, #a855f7 100%);
  border: none;
  color: #fff;
  
  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #4a7de0 0%, #9645e8 100%);
    color: #fff;
    box-shadow: 0 4px 12px rgba(88, 141, 239, 0.3);
  }
}

.zoom-level {
  min-width: 50px;
  text-align: center;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  
  &:hover {
    background: #f0f0f0;
  }
}

.flowchart-content {
  flex: 1;
  min-height: 300px;
  max-height: 500px;
  overflow: auto;
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(88, 141, 239, 0.2);
    border-radius: 4px;
  }
  
  &::-webkit-scrollbar-track {
    background: transparent;
  }
}

.svg-container {
  transform-origin: center center;
  transition: transform 0.2s ease;
  
  :deep(svg) {
    max-width: 100%;
    height: auto;
    display: block;
  }
}
</style>
