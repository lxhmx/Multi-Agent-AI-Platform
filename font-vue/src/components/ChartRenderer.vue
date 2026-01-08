<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

interface Props {
  chartType: string
  chartName: string
  option: any
  rawData?: any[]
  totalCount?: number
}

const props = defineProps<Props>()

const chartContainer = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return
  
  // 销毁旧实例
  if (chartInstance) {
    chartInstance.dispose()
  }
  
  // 创建新实例
  chartInstance = echarts.init(chartContainer.value)
  chartInstance.setOption(props.option)
}

// 监听 option 变化
watch(() => props.option, () => {
  nextTick(() => {
    initChart()
  })
}, { deep: true })

// 窗口大小变化时重绘
const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  nextTick(() => {
    initChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<template>
  <div class="chart-renderer">
    <div class="chart-header">
      <el-icon><DataAnalysis /></el-icon>
      <span>{{ chartName }}</span>
      <span v-if="totalCount" class="chart-count">共 {{ totalCount }} 条数据</span>
    </div>
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<style lang="scss" scoped>
.chart-renderer {
  margin-top: 12px;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.chart-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  
  .el-icon {
    font-size: 16px;
  }
  
  .chart-count {
    margin-left: auto;
    font-size: 12px;
    opacity: 0.8;
  }
}

.chart-container {
  width: 100%;
  height: 300px;
  padding: 16px;
}
</style>
