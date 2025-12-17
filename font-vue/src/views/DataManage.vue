<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTrainingStats, getTrainingActivity, getTrainingFiles, deleteTrainingFiles } from '@/api'
import type { TrainingActivity } from '@/api'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

// 文件记录类型
interface TrainingFile {
  id: number
  file_name: string
  file_path: string
  file_type: string
  train_type: string
  file_size: number
  train_status: string
  train_result?: string
  train_count: number
  upload_date: string
  created_at: string
}

// 统计数据类型
interface Stats {
  total_files: number
  sql_count: number
  doc_count: number
  success_count: number
  failed_count: number
  pending_count: number
  total_train_items: number
  total_file_size: number
  by_type: Record<string, number>
}

// 数据状态
const stats = ref<Stats>({
  total_files: 0,
  sql_count: 0,
  doc_count: 0,
  success_count: 0,
  failed_count: 0,
  pending_count: 0,
  total_train_items: 0,
  total_file_size: 0,
  by_type: {}
})
const activity = ref<TrainingActivity[]>([])
const dataList = ref<TrainingFile[]>([])
const loading = ref(false)
const selectedIds = ref<number[]>([])

// 筛选条件
const filterType = ref('all')
const filterStatus = ref('all')
const searchKeyword = ref('')
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 饼图配置 - 按训练类型
const pieOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
  legend: {
    orient: 'horizontal',
    bottom: 0,
    left: 'center'
  },
  series: [{
    type: 'pie',
    radius: ['40%', '60%'],
    center: ['50%', '40%'],
    avoidLabelOverlap: false,
    label: { show: false },
    data: [
      { value: stats.value.sql_count, name: 'SQL文件', itemStyle: { color: '#5b8def' } },
      { value: stats.value.doc_count, name: '文档文件', itemStyle: { color: '#a855f7' } }
    ]
  }]
}))

// 柱状图配置
const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  xAxis: {
    type: 'category',
    data: activity.value.map(item => item.date.slice(5))
  },
  yAxis: { type: 'value' },
  series: [{
    type: 'bar',
    data: activity.value.map(item => item.count),
    itemStyle: {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: '#00d4ff' },
          { offset: 1, color: '#a855f7' }
        ]
      },
      borderRadius: [4, 4, 0, 0]
    }
  }]
}))

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const [statsRes, activityRes, listRes] = await Promise.all([
      getTrainingStats(),
      getTrainingActivity(7),
      getTrainingFiles({
        page: pagination.value.page,
        page_size: pagination.value.pageSize,
        train_type: filterType.value === 'all' ? undefined : filterType.value,
        train_status: filterStatus.value === 'all' ? undefined : filterStatus.value,
        keyword: searchKeyword.value || undefined
      })
    ])
    
    if (statsRes.success) stats.value = statsRes.stats as unknown as Stats
    if (activityRes.success) activity.value = activityRes.data
    if (listRes.success) {
      dataList.value = listRes.data as TrainingFile[]
      pagination.value.total = listRes.pagination?.total || 0
    }
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.value.page = 1
  loadData()
}

// 筛选类型变化
const handleFilterChange = (type: string) => {
  filterType.value = type
  pagination.value.page = 1
  loadData()
}

// 选择变化
const handleSelectionChange = (rows: TrainingFile[]) => {
  selectedIds.value = rows.map(row => row.id)
}

// 删除
const handleDelete = async (ids: number[]) => {
  try {
    await ElMessageBox.confirm('确定要删除选中的文件记录吗？', '提示', {
      type: 'warning'
    })
    
    const res = await deleteTrainingFiles({ ids }) as any
    if (res.success) {
      ElMessage.success(res.message || '删除成功')
      loadData()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    // 用户取消
  }
}

// 批量删除
const handleBatchDelete = () => {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要删除的记录')
    return
  }
  handleDelete(selectedIds.value)
}

// 获取文件类型标签样式
const getFileTypeTag = (type: string) => {
  const map: Record<string, { text: string; color: string }> = {
    sql: { text: 'SQL', color: '#a855f7' },
    doc: { text: 'DOC', color: '#3b82f6' },
    docx: { text: 'DOCX', color: '#3b82f6' },
    pdf: { text: 'PDF', color: '#ef4444' },
    xls: { text: 'XLS', color: '#10b981' },
    xlsx: { text: 'XLSX', color: '#10b981' },
    csv: { text: 'CSV', color: '#f59e0b' },
    txt: { text: 'TXT', color: '#6b7280' }
  }
  return map[type] || { text: type.toUpperCase(), color: '#999' }
}

// 获取训练状态标签样式
const getStatusTag = (status: string) => {
  const map: Record<string, { text: string; type: string }> = {
    pending: { text: '待训练', type: 'info' },
    training: { text: '训练中', type: 'warning' },
    success: { text: '已完成', type: 'success' },
    failed: { text: '失败', type: 'danger' }
  }
  return map[status] || { text: status, type: 'info' }
}

// 筛选状态变化
const handleStatusChange = (status: string) => {
  filterStatus.value = status
  pagination.value.page = 1
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="data-manage-page">
    <h1 class="page-title">训练数据管理</h1>
    
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stats-card overview">
        <div class="stats-header">
          <el-icon><TrendCharts /></el-icon>
          <span>文件概览</span>
        </div>
        <div class="stats-items">
          <div class="stat-item">
            <div class="stat-icon sql"><el-icon><Document /></el-icon></div>
            <div class="stat-value">{{ stats.sql_count }}</div>
            <div class="stat-label">SQL文件</div>
          </div>
          <div class="stat-item">
            <div class="stat-icon doc"><el-icon><Files /></el-icon></div>
            <div class="stat-value">{{ stats.doc_count }}</div>
            <div class="stat-label">文档文件</div>
          </div>
          <div class="stat-item">
            <div class="stat-icon success"><el-icon><CircleCheck /></el-icon></div>
            <div class="stat-value">{{ stats.success_count }}</div>
            <div class="stat-label">已训练</div>
          </div>
          <div class="stat-item">
            <div class="stat-icon pending"><el-icon><Clock /></el-icon></div>
            <div class="stat-value">{{ stats.pending_count }}</div>
            <div class="stat-label">待训练</div>
          </div>
        </div>
        <div class="stats-total">
          总文件数 <span class="total-value">{{ stats.total_files }}</span>
          <span class="size-info">（{{ formatFileSize(stats.total_file_size) }}）</span>
        </div>
      </div>
      
      <div class="stats-card chart">
        <div class="stats-header">类型分布</div>
        <v-chart :option="pieOption" autoresize style="height: 180px" />
      </div>
    </div>
    
    <!-- 活跃度图表 -->
    <div class="activity-card">
      <div class="card-header">近期训练活跃度</div>
      <v-chart :option="barOption" autoresize style="height: 200px" />
    </div>
    
    <!-- 数据列表 -->
    <div class="list-card">
      <!-- 搜索和筛选 -->
      <div class="list-toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索文件名..."
            style="width: 300px"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          
          <el-button 
            type="danger" 
            :disabled="selectedIds.length === 0"
            @click="handleBatchDelete"
          >
            <el-icon><Delete /></el-icon>
            批量删除
          </el-button>
        </div>
        
        <div class="filter-buttons">
          <el-button 
            :type="filterType === 'all' ? 'primary' : 'default'"
            @click="handleFilterChange('all')"
          >全部</el-button>
          <el-button 
            :type="filterType === 'sql' ? 'primary' : 'default'"
            @click="handleFilterChange('sql')"
          >SQL</el-button>
          <el-button 
            :type="filterType === 'document' ? 'primary' : 'default'"
            @click="handleFilterChange('document')"
          >文档</el-button>
          
          <el-divider direction="vertical" />
          
          <el-button 
            :type="filterStatus === 'all' ? 'primary' : 'default'"
            size="small"
            @click="handleStatusChange('all')"
          >全部状态</el-button>
          <el-button 
            :type="filterStatus === 'pending' ? 'primary' : 'default'"
            size="small"
            @click="handleStatusChange('pending')"
          >待训练</el-button>
          <el-button 
            :type="filterStatus === 'success' ? 'primary' : 'default'"
            size="small"
            @click="handleStatusChange('success')"
          >已完成</el-button>
        </div>
      </div>
      
      <!-- 表格 -->
      <el-table
        :data="dataList"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        style="width: 100%"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="file_name" label="文件名" min-width="200">
          <template #default="{ row }">
            <div class="file-name-cell">
              <el-tag 
                :style="{ 
                  background: getFileTypeTag(row.file_type).color,
                  color: '#fff',
                  border: 'none'
                }"
                size="small"
              >
                {{ getFileTypeTag(row.file_type).text }}
              </el-tag>
              <span class="file-name">{{ row.file_name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="train_type" label="训练类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.train_type === 'sql' ? 'primary' : 'success'" size="small">
              {{ row.train_type === 'sql' ? 'SQL训练' : '文档训练' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="train_status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.train_status).type as any" size="small">
              {{ getStatusTag(row.train_status).text }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="train_count" label="知识条目" width="90">
          <template #default="{ row }">
            {{ row.train_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="upload_date" label="上传日期" width="110">
          <template #default="{ row }">
            {{ row.upload_date || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button 
              type="danger" 
              link 
              @click="handleDelete([row.id])"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @change="loadData"
        />
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.data-manage-page {
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
  margin-bottom: 8px;
  letter-spacing: -0.5px;
}

.page-title {
  margin-bottom: 24px;
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
  
  &:hover {
    box-shadow: 0 8px 30px rgba(88, 141, 239, 0.12);
  }
  
  &.overview {
    flex: 1;
  }
  
  &.chart {
    width: 320px;
  }
  
  .stats-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
    color: #4b5563;
    margin-bottom: 20px;
    
    .el-icon {
      color: #5b8def;
    }
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
        
        &.sql { background: linear-gradient(135deg, rgba(0, 212, 255, 0.15) 0%, rgba(91, 141, 239, 0.15) 100%); color: #5b8def; }
        &.doc { background: linear-gradient(135deg, rgba(91, 141, 239, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%); color: #a855f7; }
        &.success { background: rgba(34, 197, 94, 0.12); color: #22c55e; }
        &.pending { background: rgba(245, 158, 11, 0.12); color: #f59e0b; }
      }
      
      .stat-value {
        font-size: 28px;
        font-weight: 700;
        color: #333;
        line-height: 1.2;
      }
      
      .stat-label {
        font-size: 13px;
        color: #888;
        margin-top: 4px;
      }
    }
  }
  
  .stats-total {
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid #f0f0f0;
    font-size: 14px;
    color: #666;
    display: flex;
    align-items: baseline;
    justify-content: center;
    
    .total-value {
      font-size: 28px;
      font-weight: 700;
      color: #5b8def;
      margin: 0 6px;
    }
    
    .size-info {
      font-size: 13px;
      color: #999;
    }
  }
}

.activity-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(88, 141, 239, 0.08);
  border: 1px solid rgba(88, 141, 239, 0.06);
  transition: all 0.3s ease;
  
  &:hover {
    box-shadow: 0 8px 30px rgba(88, 141, 239, 0.12);
  }
  
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
    
    .toolbar-left {
      display: flex;
      gap: 12px;
      align-items: center;
    }
    
    .filter-buttons {
      display: flex;
      gap: 8px;
      align-items: center;
    }
  }
  
  .file-name-cell {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .file-name {
      color: #333;
      font-size: 13px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  
  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
}
</style>
