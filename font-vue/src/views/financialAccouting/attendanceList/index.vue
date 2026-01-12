<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Upload, Search } from '@element-plus/icons-vue'
import { 
  uploadAttendanceDeduction, 
  getDeductionRecords, 
  getDeductionStats,
  exportDeductionRecords,
  type DeductionRecord
} from '@/api'

defineOptions({ name: 'AttendanceList' })

// 数据状态
const loading = ref(false)
const uploading = ref(false)
const dataList = ref<DeductionRecord[]>([])
const uploadDialogVisible = ref(false)
const uploadFileName = ref('')

// 获取上个月的月份字符串
const getLastMonth = () => {
  const now = new Date()
  const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const year = lastMonth.getFullYear()
  const month = String(lastMonth.getMonth() + 1).padStart(2, '0')
  return `${year}-${month}`
}

// 筛选条件
const availableMonths = ref<string[]>([])
const selectedMonth = ref(getLastMonth())  // 默认上个月
const searchKeyword = ref('')
const pagination = ref({ page: 1, pageSize: 20, total: 0 })

const formatMoney = (amount: number) => amount ? `¥${Number(amount).toFixed(2)}` : '¥0.00'

const loadData = async () => {
  loading.value = true
  try {
    const [statsRes, listRes] = await Promise.all([
      getDeductionStats(selectedMonth.value || undefined),
      getDeductionRecords({ page: pagination.value.page, page_size: pagination.value.pageSize, month: selectedMonth.value || undefined, keyword: searchKeyword.value || undefined })
    ])
    if (statsRes.success) {
      availableMonths.value = statsRes.data.months || []
      // 如果默认月份不在可用月份列表中，且列表不为空，则选择第一个可用月份
      if (availableMonths.value.length > 0 && !availableMonths.value.includes(selectedMonth.value)) {
        selectedMonth.value = availableMonths.value[0]
        // 重新加载数据
        loading.value = false
        return loadData()
      }
    }
    if (listRes.success) {
      dataList.value = listRes.data
      pagination.value.total = listRes.pagination?.total || 0
    }
  } catch (error) { console.error('加载数据失败:', error) }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.value.page = 1; loadData() }
const handleMonthChange = () => { pagination.value.page = 1; loadData() }

const handleUpload = async (options: any) => {
  const file = options.file
  if (!file) return
  
  uploadFileName.value = file.name
  uploadDialogVisible.value = true
  uploading.value = true
  
  try {
    const res = await uploadAttendanceDeduction(file) as any
    uploadDialogVisible.value = false
    if (res.success) {
      ElMessage.success(`处理完成: ${res.data.total_employees}人, 扣款${res.data.deduction_employees}人, 共¥${res.data.total_deduction}`)
      loadData()
    } else { ElMessage.error(res.message || '上传失败') }
  } catch (error: any) { 
    uploadDialogVisible.value = false
    ElMessage.error(error.response?.data?.detail || '上传失败') 
  }
  finally { uploading.value = false }
}

const handleExport = async () => {
  try {
    await exportDeductionRecords(selectedMonth.value || undefined, searchKeyword.value || undefined)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const getLevelColor = (level: string) => {
  if (!level) return '#999'
  const colors: Record<string, string> = { 'P': '#5b8def', 'M': '#a855f7', 'D': '#10b981', '实习': '#f59e0b' }
  return colors[level] || '#999'
}

onMounted(() => { loadData() })
</script>

<template>
  <div class="attendance-page">
    <h1 class="page-title">员工考勤扣款管理</h1>
    
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
        <span class="upload-tip">支持 .xls, .xlsx 格式，上传后自动计算扣款数据</span>
      </div>
    </div>
    
    <!-- 上传加载弹框 -->
    <el-dialog v-model="uploadDialogVisible" :show-close="false" :close-on-click-modal="false" :close-on-press-escape="false" width="400px" class="upload-loading-dialog">
      <div class="upload-loading-content">
        <div class="loading-spinner"><div class="spinner"></div></div>
        <div class="loading-text">正在计算考勤扣款...</div>
        <div class="loading-file">{{ uploadFileName }}</div>
        <div class="loading-tip">数据量较大时可能需要等待几秒钟，请勿关闭页面</div>
      </div>
    </el-dialog>
    
    <!-- 数据列表 -->
    <div class="list-card">
      <div class="list-toolbar">
        <div class="toolbar-left">
          <el-select v-model="selectedMonth" placeholder="全部月份" clearable style="width: 140px" @change="handleMonthChange">
            <el-option v-for="month in availableMonths" :key="month" :label="month" :value="month" />
          </el-select>
          <el-input v-model="searchKeyword" placeholder="搜索姓名/职务..." style="width: 200px" @keyup.enter="handleSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
          <el-button @click="handleSearch">搜索</el-button>
        </div>
        <div class="toolbar-right">
          <el-button type="success" @click="handleExport">导出Excel</el-button>
        </div>
      </div>
      
      <el-table :data="dataList" v-loading="loading" style="width: 100%">
        <el-table-column prop="employee_name" label="姓名" width="100" />
        <el-table-column prop="job_title" label="职务" min-width="120" show-overflow-tooltip />
        <el-table-column prop="level_type" label="职级" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.level_type" :style="{ background: getLevelColor(row.level_type), color: '#fff', border: 'none' }" size="small">{{ row.level_type }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_late_count" label="总迟到" width="80" sortable />
        <el-table-column prop="late_within_10_count" label="10分内" width="80" />
        <el-table-column prop="late_over_10_count" label="超10分" width="80" />
        <el-table-column prop="late_over_60_count" label="超1小时" width="80" />
        <el-table-column prop="morning_missing_count" label="早缺卡" width="80" />
        <el-table-column prop="evening_missing_count" label="晚缺卡" width="80" />
        <el-table-column prop="early_leave_count" label="早退" width="70" />
        <el-table-column prop="total_deduction" label="扣款金额" width="100">
          <template #default="{ row }"><span class="money-text">{{ formatMoney(row.total_deduction) }}</span></template>
        </el-table-column>
        <el-table-column prop="attendance_month" label="考勤月份" width="100" />
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @change="loadData" />
      </div>
    </div>
  </div>
</template>


<style lang="scss" scoped>
.attendance-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-title {
  font-size: 26px;
  font-weight: 700;
  background: linear-gradient(90deg, #ef4444 0%, #f59e0b 50%, #10b981 100%);
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
  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.06);
  
  .upload-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 16px;
    .el-icon { color: #ef4444; }
  }
  
  .upload-content {
    display: flex;
    align-items: center;
    gap: 12px;
    .upload-tip { font-size: 13px; color: #999; margin-left: 8px; }
  }
}

.list-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.06);
  
  .list-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
    
    .toolbar-left { display: flex; gap: 12px; align-items: center; }
    .toolbar-right { display: flex; gap: 12px; align-items: center; }
  }
  
  .money-text { color: #ef4444; font-weight: 600; }
  .pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
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
      border: 4px solid rgba(239, 68, 68, 0.2);
      border-top-color: #ef4444;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }
  }
  
  .loading-text { font-size: 18px; font-weight: 600; color: #333; margin-bottom: 8px; }
  .loading-file { font-size: 14px; color: #ef4444; margin-bottom: 16px; word-break: break-all; }
  .loading-tip { font-size: 13px; color: #999; }
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
