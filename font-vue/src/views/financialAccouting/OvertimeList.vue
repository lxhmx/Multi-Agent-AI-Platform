<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Download } from '@element-plus/icons-vue'
import { 
  getOvertimeRecords, 
  getOvertimeStats,
  type OvertimeRecord
} from '@/api'

defineOptions({ name: 'OvertimeList' })

// 数据状态
const loading = ref(false)
const dataList = ref<OvertimeRecord[]>([])
const detailDialogVisible = ref(false)
const currentRecord = ref<OvertimeRecord | null>(null)

// 筛选条件
const selectedMonth = ref('')
const searchKeyword = ref('')
const pagination = ref({ page: 1, pageSize: 20, total: 0 })
const availableMonths = ref<string[]>([])
const sortField = ref('')
const sortOrder = ref('')
const exporting = ref(false)

const formatMoney = (amount: number) => amount ? `¥${amount.toFixed(2)}` : '¥0.00'

const loadData = async () => {
  loading.value = true
  try {
    const [statsRes, listRes] = await Promise.all([
      getOvertimeStats(undefined),
      getOvertimeRecords({ 
        page: pagination.value.page, 
        page_size: pagination.value.pageSize, 
        month: selectedMonth.value || undefined, 
        keyword: searchKeyword.value || undefined,
        sort_field: sortField.value || undefined,
        sort_order: sortOrder.value || undefined
      })
    ])
    if (statsRes.success) {
      availableMonths.value = statsRes.data.months || []
    }
    if (listRes.success) {
      dataList.value = listRes.data
      pagination.value.total = listRes.pagination?.total || 0
    }
  } catch (error) { 
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  }
  finally { loading.value = false }
}

const handleSearch = () => { pagination.value.page = 1; loadData() }
const handleMonthChange = () => { pagination.value.page = 1; loadData() }

const handleSortChange = ({ prop, order }: any) => {
  if (order) {
    sortField.value = prop
    sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
  } else {
    sortField.value = ''
    sortOrder.value = ''
  }
  pagination.value.page = 1
  loadData()
}

const handleExport = async () => {
  exporting.value = true
  try {
    const params = new URLSearchParams()
    if (selectedMonth.value) params.append('month', selectedMonth.value)
    if (searchKeyword.value) params.append('keyword', searchKeyword.value)
    if (sortField.value) params.append('sort_field', sortField.value)
    if (sortOrder.value) params.append('sort_order', sortOrder.value)
    
    const url = `/api/financial/overtime-records/export?${params.toString()}`
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })
    
    if (!response.ok) throw new Error('导出失败')
    
    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = downloadUrl
    a.download = `加班记录_${selectedMonth.value || '全部'}${Date.now()}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(downloadUrl)
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const handleViewDetail = (row: OvertimeRecord) => {
  currentRecord.value = row
  detailDialogVisible.value = true
}

const getLevelColor = (level: string) => {
  if (!level) return '#999'
  const colors: Record<string, string> = { 'P': '#5b8def', 'M': '#a855f7', 'D': '#10b981' }
  return colors[level.charAt(0).toUpperCase()] || '#999'
}

onMounted(() => { loadData() })
</script>

<template>
  <div class="overtime-list-page">
    <h1 class="page-title">加班记录</h1>
    
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
          <el-button type="success" :loading="exporting" @click="handleExport">
            <el-icon><Download /></el-icon>
            导出Excel
          </el-button>
        </div>
      </div>
      
      <el-table :data="dataList" v-loading="loading" @sort-change="handleSortChange" style="width: 100%">
        <el-table-column prop="employee_name" label="姓名" width="100" />
        <el-table-column prop="job_title" label="职务" min-width="150" show-overflow-tooltip />
        <el-table-column prop="job_level" label="职级" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.job_level" :style="{ background: getLevelColor(row.job_level), color: '#fff', border: 'none' }" size="small">{{ row.job_level }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="overtime_hours" label="加班时长(h)" width="110" sortable="custom" />
        <el-table-column prop="overtime_days" label="加班天数" width="100" />
        <el-table-column prop="overtime_rate" label="费用标准" width="100">
          <template #default="{ row }">{{ row.overtime_rate ? `¥${row.overtime_rate}/h` : '-' }}</template>
        </el-table-column>
        <el-table-column prop="overtime_amount" label="加班金额" width="110">
          <template #default="{ row }"><span class="money-text">{{ formatMoney(row.overtime_amount) }}</span></template>
        </el-table-column>
        <el-table-column prop="attendance_month" label="考勤月份" width="100" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <span class="detail-link" @click="handleViewDetail(row)">查看详情</span>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @change="loadData" />
      </div>
    </div>
    
    <!-- 详情弹窗 -->
    <el-dialog 
      v-model="detailDialogVisible" 
      title="加班详情" 
      width="600px" 
      align-center
      append-to-body
      :lock-scroll="true"
      class="detail-dialog"
    >
      <div v-if="currentRecord" class="detail-content">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">姓名：</span>
              <span class="value">{{ currentRecord.employee_name }}</span>
            </div>
            <div class="detail-item">
              <span class="label">职务：</span>
              <span class="value">{{ currentRecord.job_title }}</span>
            </div>
            <div class="detail-item">
              <span class="label">职级：</span>
              <el-tag v-if="currentRecord.job_level" :style="{ background: getLevelColor(currentRecord.job_level), color: '#fff', border: 'none' }" size="small">
                {{ currentRecord.job_level }}
              </el-tag>
              <span v-else class="value">-</span>
            </div>
            <div class="detail-item">
              <span class="label">考勤月份：</span>
              <span class="value">{{ currentRecord.attendance_month }}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-section">
          <h3>加班统计</h3>
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">加班时长：</span>
              <span class="value highlight">{{ currentRecord.overtime_hours }} 小时</span>
            </div>
            <div class="detail-item">
              <span class="label">加班天数：</span>
              <span class="value">{{ currentRecord.overtime_days }} 天</span>
            </div>
            <div class="detail-item">
              <span class="label">费用标准：</span>
              <span class="value">{{ currentRecord.overtime_rate ? `¥${currentRecord.overtime_rate}/小时` : '-' }}</span>
            </div>
            <div class="detail-item">
              <span class="label">加班金额：</span>
              <span class="value money">{{ formatMoney(currentRecord.overtime_amount) }}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-section" v-if="currentRecord.overtime_detail">
          <h3>加班明细</h3>
          <div class="detail-text">{{ currentRecord.overtime_detail }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.overtime-list-page {
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

.list-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(88, 141, 239, 0.08);
  border: 1px solid rgba(88, 141, 239, 0.06);
  
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
  
  .money-text { color: #f59e0b; font-weight: 600; }
  .pagination-wrapper { display: flex; justify-content: flex-end; margin-top: 16px; }
  
  .detail-link {
    color: #5b8def;
    cursor: pointer;
    font-size: 14px;
    transition: color 0.3s;
    
    &:hover {
      color: #4472c4;
      text-decoration: underline;
    }
  }
}

.detail-dialog {
  :deep(.el-overlay) {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
  }
  
  :deep(.el-dialog) {
    border-radius: 16px;
    margin: 0 !important;
    position: relative !important;
  }
  
  :deep(.el-dialog__header) {
    padding: 20px 24px;
    border-bottom: 1px solid #f0f0f0;
  }
  
  :deep(.el-dialog__body) {
    padding: 24px;
    max-height: 70vh;
    overflow-y: auto;
  }
}

.detail-content {
  .detail-section {
    margin-bottom: 24px;
    
    &:last-child {
      margin-bottom: 0;
    }
    
    h3 {
      font-size: 15px;
      font-weight: 600;
      color: #333;
      margin-bottom: 16px;
      padding-left: 12px;
      border-left: 3px solid #5b8def;
    }
    
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
    }
    
    .detail-item {
      display: flex;
      align-items: center;
      
      .label {
        font-size: 14px;
        color: #666;
        min-width: 80px;
      }
      
      .value {
        font-size: 14px;
        color: #333;
        font-weight: 500;
        
        &.highlight {
          color: #5b8def;
          font-weight: 600;
        }
        
        &.money {
          color: #f59e0b;
          font-weight: 600;
        }
      }
    }
    
    .detail-text {
      padding: 12px;
      background: #f8f9fa;
      border-radius: 8px;
      font-size: 14px;
      color: #333;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
}
</style>
