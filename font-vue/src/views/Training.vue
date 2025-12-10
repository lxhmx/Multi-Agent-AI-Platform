<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFile, trainManual, trainSql, trainDocument } from '@/api'

// 当前模式：upload | manual
const activeMode = ref<'upload' | 'manual'>('upload')

// 文件上传相关
const fileList = ref<any[]>([])
const uploading = ref(false)

// 手动输入相关
const manualForm = ref({
  type: 'sql' as 'sql' | 'ddl' | 'documentation',
  content: '',
  title: '',
  keywords: '',
  tags: ''
})
const submitting = ref(false)

// 处理文件上传
const handleUpload = async (options: any) => {
  const file = options.file
  uploading.value = true
  
  try {
    const res = await uploadFile(file)
    if (res.success) {
      ElMessage.success(`${file.name} 上传成功`)
      fileList.value = []
    } else {
      ElMessage.error(res.message || '上传失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

// 提交手动训练
const handleManualSubmit = async () => {
  if (!manualForm.value.content.trim()) {
    ElMessage.warning('请输入训练内容')
    return
  }
  
  submitting.value = true
  try {
    const res = await trainManual(manualForm.value)
    if (res.success) {
      ElMessage.success('训练数据提交成功')
      // 重置表单
      manualForm.value = {
        type: 'sql',
        content: '',
        title: '',
        keywords: '',
        tags: ''
      }
    } else {
      ElMessage.error(res.message || '提交失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

// 训练按钮状态
const trainingSql = ref(false)
const trainingDoc = ref(false)
const trainingExcel = ref(false)

// 文件类型说明
const fileTypes = [
  { icon: 'Document', title: 'SQL 训练', desc: '.sql', color: '#a855f7', type: 'sql', folder: 'train-sql' },
  { icon: 'Tickets', title: '文档训练', desc: '.doc, .pdf', color: '#f97316', type: 'doc', folder: 'train-document' },
  { icon: 'Grid', title: '表格训练', desc: '.xls, .xlsx', color: '#8b5cf6', type: 'excel', folder: 'train-document' }
]

// 点击训练按钮
const handleTrainClick = async (item: typeof fileTypes[0]) => {
  try {
    await ElMessageBox.confirm(
      `确定要开始训练 "${item.folder}" 文件夹中的数据吗？`,
      '确认训练',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    // 开始训练
    if (item.type === 'sql') {
      trainingSql.value = true
      try {
        const res = await trainSql()
        if (res.success) {
          ElMessage.success(`SQL 训练完成，共训练 ${res.trained_count || 0} 条数据`)
        } else {
          ElMessage.error(res.message || 'SQL 训练失败')
        }
      } finally {
        trainingSql.value = false
      }
    } else if (item.type === 'doc') {
      trainingDoc.value = true
      try {
        const res = await trainDocument()
        if (res.success) {
          ElMessage.success(`文档训练完成，共训练 ${res.trained_count || 0} 条数据`)
        } else {
          ElMessage.error(res.message || '文档训练失败')
        }
      } finally {
        trainingDoc.value = false
      }
    } else if (item.type === 'excel') {
      trainingExcel.value = true
      try {
        const res = await trainDocument()
        if (res.success) {
          ElMessage.success(`表格训练完成，共训练 ${res.trained_count || 0} 条数据`)
        } else {
          ElMessage.error(res.message || '表格训练失败')
        }
      } finally {
        trainingExcel.value = false
      }
    }
  } catch {
    // 用户取消
  }
}

// 获取训练状态
const isTraining = (type: string) => {
  if (type === 'sql') return trainingSql.value
  if (type === 'doc') return trainingDoc.value
  if (type === 'excel') return trainingExcel.value
  return false
}
</script>

<template>
  <div class="training-page">
    <h1 class="page-title">知识训练与上传</h1>
    <p class="page-subtitle">上传训练数据或手动输入知识内容</p>
    
    <div class="content-card">
      <!-- 模式切换 -->
      <div class="mode-tabs">
        <div 
          class="mode-tab" 
          :class="{ active: activeMode === 'upload' }"
          @click="activeMode = 'upload'"
        >
          <el-icon><Upload /></el-icon>
          <span>文件上传</span>
        </div>
        <div 
          class="mode-tab" 
          :class="{ active: activeMode === 'manual' }"
          @click="activeMode = 'manual'"
        >
          <el-icon><Plus /></el-icon>
          <span>手动输入</span>
        </div>
      </div>
      
      <!-- 文件上传模式 -->
      <div v-if="activeMode === 'upload'" class="upload-section">
        <el-upload
          class="upload-dragger"
          drag
          :auto-upload="true"
          :show-file-list="false"
          :http-request="handleUpload"
          accept=".sql,.doc,.docx,.pdf,.xls,.xlsx"
        >
          <div class="upload-content">
            <el-icon class="upload-icon"><Upload /></el-icon>
            <p class="upload-text">拖拽文件到此处，或点击上传</p>
            <p class="upload-hint">支持 .sql, .doc, .docx, .pdf, .xls, .xlsx 格式</p>
            <el-button type="primary" class="upload-btn" :loading="uploading">
              选择文件
            </el-button>
          </div>
        </el-upload>
        
        <!-- 文件类型说明 - 可点击训练 -->
        <div class="file-types">
          <div 
            v-for="item in fileTypes" 
            :key="item.title" 
            class="file-type-card"
            :class="{ loading: isTraining(item.type) }"
            @click="handleTrainClick(item)"
          >
            <div class="file-type-icon" :style="{ background: item.color }">
              <el-icon v-if="!isTraining(item.type)" :size="24" color="#fff">
                <component :is="item.icon" />
              </el-icon>
              <el-icon v-else :size="24" color="#fff" class="is-loading">
                <Loading />
              </el-icon>
            </div>
            <div class="file-type-info">
              <span class="file-type-title">{{ item.title }}</span>
              <span class="file-type-desc">{{ item.desc }}</span>
            </div>
            <el-icon class="train-arrow"><Right /></el-icon>
          </div>
        </div>
      </div>
      
      <!-- 手动输入模式 -->
      <div v-else class="manual-section">
        <div class="form-item">
          <label class="form-label">训练类型</label>
          <div class="type-buttons">
            <el-button 
              :type="manualForm.type === 'sql' ? 'primary' : 'default'"
              @click="manualForm.type = 'sql'"
            >SQL</el-button>
            <el-button 
              :type="manualForm.type === 'ddl' ? 'primary' : 'default'"
              @click="manualForm.type = 'ddl'"
            >DDL</el-button>
            <el-button 
              :type="manualForm.type === 'documentation' ? 'primary' : 'default'"
              @click="manualForm.type = 'documentation'"
            >文档</el-button>
          </div>
        </div>
        
        <div class="form-item">
          <label class="form-label">内容 <span class="required">*</span></label>
          <el-input
            v-model="manualForm.content"
            type="textarea"
            :rows="6"
            placeholder="SELECT * FROM users WHERE status = 'active'"
          />
        </div>
        
        <div class="form-item">
          <label class="form-label">标题</label>
          <el-input
            v-model="manualForm.title"
            placeholder="为这条知识添加标题"
          />
        </div>
        
        <div class="form-item">
          <label class="form-label">关键词</label>
          <el-input
            v-model="manualForm.keywords"
            placeholder="用逗号分隔多个关键词"
          />
        </div>
        
        <div class="form-item">
          <label class="form-label">业务标签</label>
          <el-input
            v-model="manualForm.tags"
            placeholder="用逗号分隔多个标签"
          />
        </div>
        
        <el-button 
          type="primary" 
          class="submit-btn"
          :loading="submitting"
          @click="handleManualSubmit"
        >
          提交训练数据
        </el-button>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.training-page {
  max-width: 900px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #7c3aed;
  margin-bottom: 8px;
}

.page-subtitle {
  font-size: 14px;
  color: #666;
  margin-bottom: 24px;
}

.content-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.mode-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  
  .mode-tab {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 16px;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s;
    border: 2px solid #eee;
    color: #666;
    
    &:hover {
      border-color: #7c3aed;
    }
    
    &.active {
      background: linear-gradient(135deg, #7c3aed 0%, #10b981 100%);
      color: #fff;
      border-color: transparent;
    }
  }
}

.upload-section {
  .upload-dragger {
    width: 100%;
    
    :deep(.el-upload-dragger) {
      border: 2px dashed #ddd;
      border-radius: 12px;
      padding: 40px;
      
      &:hover {
        border-color: #7c3aed;
      }
    }
  }
  
  .upload-content {
    text-align: center;
    
    .upload-icon {
      font-size: 48px;
      color: #7c3aed;
      margin-bottom: 16px;
    }
    
    .upload-text {
      font-size: 16px;
      color: #333;
      margin-bottom: 8px;
    }
    
    .upload-hint {
      font-size: 13px;
      color: #999;
      margin-bottom: 16px;
    }
    
    .upload-btn {
      background: linear-gradient(135deg, #7c3aed 0%, #10b981 100%);
      border: none;
    }
  }
}

.file-types {
  display: flex;
  gap: 16px;
  margin-top: 24px;
  
  .file-type-card {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: #f9f9f9;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    border: 2px solid transparent;
    position: relative;
    
    &:hover {
      background: #fff;
      border-color: #7c3aed;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15);
      
      .train-arrow {
        opacity: 1;
        transform: translateX(0);
      }
    }
    
    &.loading {
      pointer-events: none;
      opacity: 0.7;
    }
    
    .file-type-icon {
      width: 48px;
      height: 48px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: transform 0.3s;
    }
    
    &:hover .file-type-icon {
      transform: scale(1.05);
    }
    
    .file-type-info {
      display: flex;
      flex-direction: column;
      flex: 1;
      
      .file-type-title {
        font-size: 14px;
        font-weight: 500;
        color: #333;
      }
      
      .file-type-desc {
        font-size: 12px;
        color: #999;
      }
    }
    
    .train-arrow {
      color: #7c3aed;
      opacity: 0;
      transform: translateX(-10px);
      transition: all 0.3s;
    }
  }
}

.manual-section {
  .form-item {
    margin-bottom: 20px;
    
    .form-label {
      display: block;
      font-size: 14px;
      font-weight: 500;
      color: #333;
      margin-bottom: 8px;
      
      .required {
        color: #7c3aed;
      }
    }
  }
  
  .type-buttons {
    display: flex;
    gap: 12px;
    
    .el-button {
      min-width: 80px;
    }
  }
  
  .submit-btn {
    width: 100%;
    height: 48px;
    font-size: 16px;
    background: linear-gradient(135deg, #7c3aed 0%, #10b981 100%);
    border: none;
    margin-top: 8px;
  }
}
</style>
