<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import api from '@/api'

defineOptions({ name: 'WorkTimeStats' })

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

// 数据状态
const loading = ref(false)
const uploading = ref(false)
const uploadDialogVisible = ref(false)
const uploadFileName = ref('')

// 筛选条件
const selectedEmployee = ref('')
const selectedMonth = ref('')
const selectedCompany = ref('')

// 统计数据
const employees = ref<string[]>([])
const months = ref<string[]>([])
const companies = ref<string[]>([])
const workTypeStats = ref<{name: string, value: number}[]>([])
const employeeTimeStats = ref<{name: string, value: number}[]>([])
const companyStats = ref<{name: string, value: number}[]>([])
const employeeTypeStats = ref<{employee_name: string, work_type: string, minutes: number}[]>([])
const summaryStats = ref({ totalHours: 0, totalRecords: 0, avgHoursPerDay: 0 })

// 颜色配置
const colors = ['#5b8def', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

// 日报类型时间占比饼图
const workTypePieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}小时 ({d}%)' },
  legend: { orient: 'vertical', right: 10, top: 'center', type: 'scroll' },
  series: [{
    type: 'pie', radius: ['35%', '55%'], center: ['35%', '50%'],
    avoidLabelOverlap: true,
    label: { show: true, formatter: '{b}\n{d}%', fontSize: 11 },
    labelLine: { show: true },
    data: workTypeStats.value.slice(0, 15).map((item, index) => ({
      value: Math.round(item.value / 60 * 10) / 10,
      name: item.name,
      itemStyle: { color: colors[index % colors.length] }
    }))
  }]
}))

// 各人员工作时长柱状图
const employeeBarOption = computed(() => ({
  tooltip: { trigger: 'axis', formatter: (params: any) => `${params[0].name}<br/>工作时长: ${params[0].value}小时` },
  grid: { left: 80, right: 20, top: 20, bottom: 30 },
  xAxis: { type: 'value', name: '小时' },
  yAxis: { 
    type: 'category', 
    data: employeeTimeStats.value.map(item => item.name).reverse(),
    axisLabel: { width: 60, overflow: 'truncate' }
  },
  series: [{
    type: 'bar',
    data: employeeTimeStats.value.map(item => Math.round(item.value / 60 * 10) / 10).reverse(),
    itemStyle: {
      color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#00d4ff' }, { offset: 1, color: '#a855f7' }] },
      borderRadius: [0, 4, 4, 0]
    },
    label: { show: true, position: 'right', formatter: '{c}h', fontSize: 11 }
  }]
}))

// 公司主体工作时长饼图
const companyPieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c}小时 ({d}%)' },
  legend: { orient: 'horizontal', bottom: 0, left: 'center' },
  series: [{
    type: 'pie', radius: ['20%', '40%'], center: ['50%', '50%'],
    avoidLabelOverlap: true,
    label: { 
      show: true, 
      formatter: '{b}\n{d}%', 
      fontSize: 10,
      alignTo: 'labelLine',
      distanceToLabelLine: 5
    },
    labelLine: { 
      show: true,
      length: 20,
      length2: 15
    },
    data: companyStats.value
      .filter(item => item.name !== '多公司')
      .map((item, index) => ({
        value: Math.round(item.value / 60 * 10) / 10,
        name: item.name,
        itemStyle: { color: colors[index % colors.length] }
      }))
  }]
}))

// 各人员工作类型分布堆叠柱状图
const employeeTypeBarOption = computed(() => {
  // 获取所有人员和工作类型
  const employeeSet = new Set<string>()
  const typeSet = new Set<string>()
  employeeTypeStats.value.forEach(item => {
    employeeSet.add(item.employee_name)
    typeSet.add(item.work_type)
  })
  const employeeList = Array.from(employeeSet)
  const typeList = Array.from(typeSet).slice(0, 10) // 取前10种类型
  
  // 构建每种工作类型的数据系列
  const series = typeList.map((type, index) => {
    const data = employeeList.map(emp => {
      const record = employeeTypeStats.value.find(r => r.employee_name === emp && r.work_type === type)
      return record ? Math.round(record.minutes / 60 * 10) / 10 : 0
    })
    return {
      name: type,
      type: 'bar',
      stack: 'total',
      data,
      itemStyle: { color: colors[index % colors.length] }
    }
  })
  
  return {
    tooltip: { 
      trigger: 'axis', 
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        let result = `${params[0].name}<br/>`
        params.forEach((p: any) => {
          if (p.value > 0) result += `${p.marker}${p.seriesName}: ${p.value}h<br/>`
        })
        return result
      }
    },
    legend: { type: 'scroll', bottom: 0, left: 'center' },
    grid: { left: 60, right: 20, top: 40, bottom: 60 },
    xAxis: { type: 'category', data: employeeList, axisLabel: { rotate: 30, fontSize: 11 } },
    yAxis: { type: 'value', name: '小时' },
    series
  }
})

// 加载统计数据
const loadStats = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (selectedEmployee.value) params.employee = selectedEmployee.value
    if (selectedMonth.value) params.month = selectedMonth.value
    if (selectedCompany.value) params.company = selectedCompany.value
    
    const res = await api.get('/work-time/stats', { params }) as any
    if (res.success) {
      const data = res.data
      employees.value = data.employees || []
      months.value = data.months || []
      companies.value = data.companies || []
      workTypeStats.value = data.work_type_stats || []
      employeeTimeStats.value = data.employee_time_stats || []
      companyStats.value = data.company_stats || []
      employeeTypeStats.value = data.employee_type_stats || []
      summaryStats.value = data.summary || { totalHours: 0, totalRecords: 0, avgHoursPerDay: 0 }
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

// 上传Excel文件
const handleUpload = async (options: any) => {
  const file = options.file
  if (!file) return
  
  uploadFileName.value = file.name
  uploadDialogVisible.value = true
  uploading.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', file)
    
    const res = await api.post('/work-time/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }) as any
    
    uploadDialogVisible.value = false
    if (res.success) {
      ElMessage.success(`导入成功: ${res.data.total_records}条记录`)
      loadStats()
    } else {
      ElMessage.error(res.message || '上传失败')
    }
  } catch (error: any) {
    uploadDialogVisible.value = false
    ElMessage.error(error.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

const handleFilterChange = () => {
  loadStats()
}

onMounted(() => {
  loadStats()
})
</script>

<template>
  <div class="work-time-page">
    <h1 class="page-title">工作时长统计</h1>
    
    <!-- 上传区域 -->
    <div class="upload-card">
      <div class="upload-header">
        <el-icon><Upload /></el-icon>
        <span>上传工作时长记录表</span>
      </div>
      <div class="upload-content">
        <el-upload :auto-upload="true" :show-file-list="false" :http-request="handleUpload" accept=".xls,.xlsx">
          <el-button type="primary" :loading="uploading">
            <el-icon><Upload /></el-icon>
            选择Excel文件
          </el-button>
        </el-upload>
        <span class="upload-tip">支持 .xls, .xlsx 格式，上传后自动统计工作时长数据</span>
      </div>
    </div>

    <!-- 上传加载弹框 -->
    <el-dialog v-model="uploadDialogVisible" :show-close="false" :close-on-click-modal="false" :close-on-press-escape="false" width="400px" class="upload-loading-dialog">
      <div class="upload-loading-content">
        <div class="loading-spinner"><div class="spinner"></div></div>
        <div class="loading-text">正在导入工作时长数据...</div>
        <div class="loading-file">{{ uploadFileName }}</div>
        <div class="loading-tip">数据量较大时可能需要等待几秒钟，请勿关闭页面</div>
      </div>
    </el-dialog>

    <!-- 汇总卡片 -->
    <div class="summary-row">
      <div class="summary-card">
        <div class="summary-value">{{ Math.round(summaryStats.totalHours / 60 * 10) / 10 }}</div>
        <div class="summary-label">总工作时长(小时)</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ summaryStats.totalRecords }}</div>
        <div class="summary-label">总记录数</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ employees.length }}</div>
        <div class="summary-label">人员数量</div>
      </div>
      <div class="summary-card">
        <div class="summary-value">{{ Math.round(summaryStats.avgHoursPerDay * 10) / 10 }}</div>
        <div class="summary-label">日均工作时长(小时)</div>
      </div>
    </div>

    <!-- 筛选条件 -->
    <div class="filter-bar">
      <span class="filter-label">筛选条件：</span>
      <el-select v-model="selectedEmployee" placeholder="全部人员" clearable style="width: 120px" @change="handleFilterChange">
        <el-option v-for="emp in employees" :key="emp" :label="emp" :value="emp" />
      </el-select>
      <el-select v-model="selectedMonth" placeholder="全部月份" clearable style="width: 140px" @change="handleFilterChange">
        <el-option v-for="month in months" :key="month" :label="month" :value="month" />
      </el-select>
      <el-select v-model="selectedCompany" placeholder="全部公司" clearable style="width: 140px" @change="handleFilterChange">
        <el-option v-for="company in companies" :key="company" :label="company" :value="company" />
      </el-select>
    </div>

    <!-- 图表区域 -->
    <div class="charts-container">
      <!-- 日报类型时间占比 -->
      <div class="stats-card chart-large">
        <div class="stats-header">日报类型时间占比</div>
        <VChart v-if="workTypeStats.length" :option="workTypePieOption" autoresize style="height: 320px" />
        <div v-else class="no-data">暂无数据</div>
      </div>

      <!-- 各人员工作时长排行 -->
      <div class="stats-card chart-large">
        <div class="stats-header">各人员工作时长排行</div>
        <VChart v-if="employeeTimeStats.length" :option="employeeBarOption" autoresize style="height: 320px" />
        <div v-else class="no-data">暂无数据</div>
      </div>
    </div>

    <div class="charts-container">
      <!-- 公司主体工作时长分布 -->
      <div class="stats-card chart-medium">
        <div class="stats-header">公司主体工作时长分布</div>
        <VChart v-if="companyStats.length" :option="companyPieOption" autoresize style="height: 320px" />
        <div v-else class="no-data">暂无数据</div>
      </div>

      <!-- 各人员工作类型分布 -->
      <div class="stats-card chart-wide">
        <div class="stats-header">各人员工作类型分布</div>
        <VChart v-if="employeeTypeStats.length" :option="employeeTypeBarOption" autoresize style="height: 280px" />
        <div v-else class="no-data">暂无数据</div>
      </div>
    </div>
  </div>
</template>


<style lang="scss" scoped>
.work-time-page {
  max-width: 1400px;
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

.summary-row {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.summary-card {
  flex: 1;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  color: #fff;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);
  
  &:nth-child(2) { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); box-shadow: 0 4px 20px rgba(240, 147, 251, 0.3); }
  &:nth-child(3) { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); box-shadow: 0 4px 20px rgba(79, 172, 254, 0.3); }
  &:nth-child(4) { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); box-shadow: 0 4px 20px rgba(67, 233, 123, 0.3); }
  
  .summary-value {
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 8px;
  }
  
  .summary-label {
    font-size: 14px;
    opacity: 0.9;
  }
}

.filter-bar {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  
  .filter-label {
    font-size: 14px;
    color: #666;
    font-weight: 500;
  }
}

.charts-container {
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
  
  &.chart-large { flex: 1; min-width: 0; }
  &.chart-medium { width: 380px; flex-shrink: 0; }
  &.chart-wide { flex: 1; min-width: 0; }
  
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
    height: 200px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #999;
    font-size: 14px;
  }
}

.upload-loading-dialog {
  :deep(.el-dialog) { border-radius: 16px; overflow: hidden; }
  :deep(.el-dialog__header) { display: none; }
  :deep(.el-dialog__body) { padding: 40px 30px; }
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
  
  .loading-text { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 8px; }
  .loading-file { font-size: 14px; color: #5b8def; margin-bottom: 16px; word-break: break-all; }
  .loading-tip { font-size: 13px; color: #999; }
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1200px) {
  .charts-container { flex-direction: column; }
  .stats-card.chart-medium { width: 100%; }
  .summary-row { flex-wrap: wrap; }
  .summary-card { min-width: calc(50% - 10px); }
}
</style>
