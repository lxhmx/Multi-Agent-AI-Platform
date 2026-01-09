<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import { 
  uploadAttendance, 
  getOvertimeStats, 
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

// 获取上个月的月份字符串 (YYYY-MM)
const getLastMonth = () => {
  const now = new Date()
  const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const year = lastMonth.getFullYear()
  const month = String(lastMonth.getMonth() + 1).padStart(2, '0')
  return `${year}-${month}`
}

// 统计数据
const availableMonths = ref<string[]>([])
const monthlyStats = ref<{month: string, hours: number}[]>([])
const levelStats = ref<LevelStats[]>([])
const topEmployees = ref<TopEmployee[]>([])
const selectedMonth = ref('')

// 各月加班总时长柱状图
const monthlyBarOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].name}<br/>加班: ${params[0].value}小时` },
  grid: { left: 50, right: 20, top: 20, bottom: 40 },
  xAxis: { 
    type: 'category', 
    data: monthlyStats.value.map(item => item.month),
    axisLabel: { rotate: 30 }
  },
  yAxis: { type: 'value', name: '小时' },
  series: [{ 
    type: 'bar', 
    data: monthlyStats.value.map(item => item.hours),
    itemStyle: { 
      color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: '#5b8def' }, { offset: 1, color: '#00d4ff' }] },
      borderRadius: [4, 4, 0, 0]
    }
  }]
}))

// 职级加班时长饼图
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

// 人员排行榜柱状图
const barOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].name}<br/>加班: ${params[0].value}小时` },
  grid: { left: 80, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'value' },
  yAxis: { type: 'category', data: topEmployees.value.map(item => item.employee_name).reverse(), axisLabel: { width: 60, overflow: 'truncate' } },
  series: [{ type: 'bar', data: topEmployees.value.map(item => item.overtime_hours).reverse(),
    itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#00d4ff' }, { offset: 1, color: '#a855f7' }] }, borderRadius: [0, 4, 4, 0] }
  }]
}))

// 加载各月汇总数据（不受月份筛选影响）
const loadMonthlyStats = async () => {
  try {
    const res = await getOvertimeStats(undefined)
    if (res.success) {
      availableMonths.value = res.data.months || []
      // 计算各月加班总时长
      const monthsData: {month: string, hours: number}[] = []
      for (const month of availableMonths.value) {
        const monthRes = await getOvertimeStats(month)
        if (monthRes.success && monthRes.data.stats) {
          monthsData.push({ month, hours: monthRes.data.stats.total_hours || 0 })
        }
      }
      // 按月份升序排列
      monthlyStats.value = monthsData.sort((a, b) => a.month.localeCompare(b.month))
    }
  } catch (error) { console.error('加载月度统计失败:', error) }
}

// 加载筛选月份的数据（职级时长、人员排行榜）
const loadFilteredStats = async () => {
  loading.value = true
  try {
    const res = await getOvertimeStats(selectedMonth.value || undefined)
    if (res.success) {
      levelStats.value = res.data.level_stats || []
      topEmployees.value = res.data.top_employees || []
    }
  } catch (error) { console.error('加载统计数据失败:', error) }
  finally { loading.value = false }
}

const handleMonthChange = () => { loadFilteredStats() }

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
      loadMonthlyStats()
      loadFilteredStats()
    } else { ElMessage.error(res.message || '上传失败') }
  } catch (error: any) { 
    uploadDialogVisible.value = false
    ElMessage.error(error.response?.data?.detail || '上传失败') 
  }
  finally { uploading.value = false }
}

onMounted(async () => {
  await loadMonthlyStats()
  // 自动选择上个月或最新月份
  if (availableMonths.value.length > 0) {
    const lastMonth = getLastMonth()
    selectedMonth.value = availableMonths.value.includes(lastMonth) 
      ? lastMonth 
      : availableMonths.value[0]
  }
  await loadFilteredStats()
})
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

    <!-- 各月加班总时长图表 -->
    <div class="stats-card monthly-chart">
      <div class="stats-header">各月加班总时长</div>
      <VChart v-if="monthlyStats.length" :option="monthlyBarOption" autoresize style="height: 220px" />
      <div v-else class="no-data">暂无数据</div>
    </div>

    <!-- 月份筛选 -->
    <div class="filter-bar">
      <span class="filter-label">按月筛选：</span>
      <el-select v-model="selectedMonth" placeholder="全部月份" clearable style="width: 160px" @change="handleMonthChange">
        <el-option v-for="month in availableMonths" :key="month" :label="month" :value="month" />
      </el-select>
    </div>

    <!-- 职级时长 + 人员排行榜 -->
    <div class="stats-row">
      <div class="stats-card chart">
        <div class="stats-header">职级加班时长</div>
        <VChart v-if="levelStats.length" :option="pieOption" autoresize style="height: 220px" />
        <div v-else class="no-data">暂无数据</div>
      </div>
      <div class="stats-card top-chart">
        <div class="stats-header">加班时长 TOP 10</div>
        <VChart v-if="topEmployees.length" :option="barOption" autoresize style="height: 220px" />
        <div v-else class="no-data">暂无数据</div>
      </div>
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
  display: flex;
  align-items: center;
  gap: 8px;
  
  .filter-label {
    font-size: 14px;
    color: #666;
  }
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
  margin-bottom: 20px;
  
  &:hover { box-shadow: 0 8px 30px rgba(88, 141, 239, 0.12); }
  &.monthly-chart { width: 100%; }
  &.chart { width: 320px; flex-shrink: 0; }
  &.top-chart { flex: 1; }
  
  .stats-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 16px;
    
    &::before {
      content: '';
      width: 4px;
      height: 16px;
      background: linear-gradient(180deg, #00d4ff 0%, #a855f7 100%);
      border-radius: 2px;
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
