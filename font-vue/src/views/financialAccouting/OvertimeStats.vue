<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Upload, TrendCharts, User, Clock, Money } from '@element-plus/icons-vue'
import { 
  uploadAttendance, 
  getOvertimeStats, 
  type OvertimeStats,
  type LevelStats,
  type TopEmployee
} from '@/api'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

defineOptions({ name: 'OvertimeStats' })

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

// 数据状态
const loading = ref(false)
const uploading = ref(false)
const uploadDialogVisible = ref(false)
const uploadFileName = ref('')

// 统计数据
const stats = ref<OvertimeStats>({
  total_employees: 0, overtime_employees: 0, total_hours: 0,
  total_days: 0, total_amount: 0, avg_hours: 0
})
const availableMonths = ref<string[]>([])
const levelStats = ref<LevelStats[]>([])
const topEmployees = ref<TopEmployee[]>([])
const selectedMonth = ref('')

const formatMoney = (amount: number) => amount ? `¥${amount.toFixed(2)}` : '¥0.00'

const pieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}小时 ({d}%)' },
  legend: { orient: 'horizontal', bottom: 0, left: 'center' },
  series: [{
    type: 'pie', radius: ['40%', '60%'], center: ['50%', '40%'],
    avoidLabelOverlap: false, label: { show: false },
    data: levelStats.value.map((item, index) => ({
      value: item.total_hours || 0, name: item.job_level || '未知',
      itemStyle: { color: ['#5b8def', '#a855f7', '#10b981', '#f59e0b', '#ef4444'][index % 5] }
    }))
  }]
}))

const barOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].name}<br/>加班: ${params[0].value}小时` },
  grid: { left: 80, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: topEmployees.value.map(item => item.employee_name).reverse(), axisLabel: { width: 60, overflow: 'truncate' } },
  series: [{ type: 'bar', data: topEmployees.value.map(item => item.overtime_hours).reverse(),
    itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#00d4ff' }, { offset: 1, color: '#a855f7' }] }, borderRadius: [0, 4, 4, 0] }
  }]
}))

const loadStats = async () => {
  loading.value = true
  try {
    const res = await getOvertimeStats(selectedMonth.value || undefined)
    if (res.success) {
      stats.value = res.data.stats || {}
      availableMonths.value = res.data.months || []
      levelStats.value = res.data.level_stats || []
      topEmployees.value = res.data.top_employees || []
    }
  } catch (error) { console.error('加载统计数据失败:', error) }
  finally { loading.value = false }
}

const handleMonthChange = () => { loadStats() }

const handleUpload = async (options: any) => {
  const file = options.file
  if (!file) return
  
  uploadFileName.value = file.name
  uploadDialogVisible.value = true
  uploading.value = true
  
  try {
    const res = await uploadAttendance(file, undefined) as any
    uploadDialogVisible.value = false
    if (res.success) {
      ElMessage.success(`处理完成: ${res.data.total_employees}人, 加班${res.data.overtime_employees}人, 共${res.data.total_hours}小时`)
      loadStats()
    } else { ElMessage.error(res.message || '上传失败') }
  } catch (error: any) { 
    uploadDialogVisible.value = false
    ElMessage.error(error.response?.data?.detail || '上传失败') 
  }
  finally { uploading.value = false }
}

onMounted(() => { loadStats() })
</script>

<template>
  <div class="overtime-stats-page">
    <h1 class="page-title">加班统计</h1>
    
    <!-- 上传区域 -->
    <div class="upload-card">
      <div class="upload-header">
        <el-icon><Upload /></el-icon>
        <span>上传考勤表</span>
      </div>
      <div class="upload-content">
        <el-upload :auto-upload="true" :show-file-list="false" :http-request="handleUpload" accept=".xls,.xlsx">
          <el-button type="primary" :loading="uploading">
            <el-icon><Upload /></el-icon>
            选择考勤Excel文件
          </el-button>
        </el-upload>
        <span class="upload-tip">支持 .xls, .xlsx 格式，上传后自动计算加班数据</span>
      </div>
    </div>
    
    <!-- 上传加载弹框 -->
    <el-dialog 
      v-model="uploadDialogVisible" 
      :show-close="false" 
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      width="400px"
      class="upload-loading-dialog"
    >
      <div class="upload-loading-content">
        <div class="loading-spinner">
          <div class="spinner"></div>
        </div>
        <div class="loading-text">正在导入考勤数据...</div>
        <div class="loading-file">{{ uploadFileName }}</div>
        <div class="loading-tip">数据量较大时可能需要等待几秒钟，请勿关闭页面</div>
      </div>
    </el-dialog>

    <!-- 月份筛选 -->
    <div class="filter-bar">
      <el-select v-model="selectedMonth" placeholder="全部月份" clearable style="width: 160px" @change="handleMonthChange">
        <el-option v-for="month in availableMonths" :key="month" :label="month" :value="month" />
      </el-select>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stats-card overview">
        <div class="stats-header">
          <el-icon><TrendCharts /></el-icon>
          <span>加班概览</span>
        </div>
        <div class="stats-items">
          <div class="stat-item">
            <div class="stat-icon users"><el-icon><User /></el-icon></div>
            <div class="stat-value">{{ stats.total_employees || 0 }}</div>
            <div class="stat-label">总人数</div>
          </div>
          <div class="stat-item">
            <div class="stat-icon overtime"><el-icon><Clock /></el-icon></div>
            <div class="stat-value">{{ stats.overtime_employees || 0 }}</div>
            <div class="stat-label">加班人数</div>
          </div>
          <div class="stat-item">
            <div class="stat-icon hours"><el-icon><Clock /></el-icon></div>
            <div class="stat-value">{{ stats.total_hours || 0 }}</div>
            <div class="stat-label">总加班时长(h)</div>
          </div>
          <div class="stat-item">
            <div class="stat-icon money"><el-icon><Money /></el-icon></div>
            <div class="stat-value">{{ formatMoney(stats.total_amount || 0) }}</div>
            <div class="stat-label">加班总金额</div>
          </div>
        </div>
      </div>
      <div class="stats-card chart">
        <div class="stats-header">职级分布</div>
        <VChart v-if="levelStats.length" :option="pieOption" autoresize style="height: 180px" />
        <div v-else class="no-data">暂无数据</div>
      </div>
    </div>
    
    <!-- TOP10图表 -->
    <div class="activity-card" v-if="topEmployees.length">
      <div class="card-header">加班时长 TOP 10</div>
      <VChart :option="barOption" autoresize style="height: 280px" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.overtime-stats-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 24px;
}

.upload-card {
  background: #fff;
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(88, 141, 239, 0.08);
  border: 1px solid rgba(88, 141, 239, 0.06);
  
  .upload-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 16px;
    .el-icon { color: #5b8def; }
  }
  
  .upload-content {
    display: flex;
    align-items: center;
    gap: 12px;
    .upload-tip { font-size: 13px; color: #999; margin-left: 8px; }
  }
}

.filter-bar {
  margin-bottom: 20px;
}

.stats-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.stats-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(88, 141, 239, 0.08);
  border: 1px solid rgba(88, 141, 239, 0.06);
  transition: all 0.3s ease;
  
  &:hover { box-shadow: 0 8px 30px rgba(88, 141, 239, 0.12); }
  &.overview { flex: 1; }
  &.chart { width: 320px; }
  
  .stats-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 20px;
    .el-icon { color: #5b8def; }
  }
  
  .stats-items {
    display: flex;
    justify-content: space-around;
    
    .stat-item {
      text-align: center;
      flex: 1;
      padding: 8px;
      
      .stat-icon {
        width: 44px;
        height: 44px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 10px;
        font-size: 20px;
        
        &.users { background: rgba(91, 141, 239, 0.12); color: #5b8def; }
        &.overtime { background: rgba(168, 85, 247, 0.12); color: #a855f7; }
        &.hours { background: rgba(34, 197, 94, 0.12); color: #22c55e; }
        &.money { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
      }
      
      .stat-value { font-size: 24px; font-weight: 700; color: #333; line-height: 1.2; }
      .stat-label { font-size: 13px; color: #888; margin-top: 4px; }
    }
  }
  
  .no-data {
    height: 180px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #999;
    font-size: 14px;
  }
}

.activity-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(88, 141, 239, 0.08);
  border: 1px solid rgba(88, 141, 239, 0.06);
  
  .card-header {
    font-size: 15px;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 8px;
    
    &::before {
      content: '';
      width: 4px;
      height: 16px;
      background: linear-gradient(180deg, #00d4ff 0%, #a855f7 100%);
      border-radius: 2px;
    }
  }
}

.upload-loading-dialog {
  :deep(.el-dialog) {
    border-radius: 16px;
    overflow: hidden;
  }
  
  :deep(.el-dialog__header) {
    display: none;
  }
  
  :deep(.el-dialog__body) {
    padding: 40px 30px;
  }
}

.upload-loading-content {
  text-align: center;
  
  .loading-spinner {
    display: flex;
    justify-content: center;
    margin-bottom: 24px;
    
    .spinner {
      width: 50px;
      height: 50px;
      border: 4px solid rgba(91, 141, 239, 0.2);
      border-top-color: #5b8def;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
  }
  
  .loading-text {
    font-size: 18px;
    font-weight: 600;
    color: #333;
    margin-bottom: 8px;
  }
  
  .loading-file {
    font-size: 14px;
    color: #5b8def;
    margin-bottom: 16px;
    word-break: break-all;
  }
  
  .loading-tip {
    font-size: 13px;
    color: #999;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
