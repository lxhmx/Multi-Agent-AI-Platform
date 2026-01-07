<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { uploadFile, trainManual, trainSql, trainDocument } from '@/api'

defineOptions({
  name: 'Training'
})

// 当前模式：upload | manual
const activeMode = ref<'upload' | 'manual'>('upload')

// 文件上传相关
const fileList = ref<any[]>([])
const uploading = ref(false)

// 手动输入 - 训练类型
const trainType = ref<'question-sql' | 'ddl' | 'documentation'>('question-sql')

// Question-SQL 表单
const questionSqlForm = ref({
  question: '',
  sql: ''
})

// DDL 表单（只需要 DDL 内容，Vanna 会自动解析表结构）
const ddlForm = ref({
  content: ''
})

// 文档表单（只需要内容，Vanna 通过向量语义检索）
const docForm = ref({
  content: ''
})

const submitting = ref(false)

// 示例数据
const examples = {
  'question-sql': [
    { question: '查询所有在线设备', sql: "SELECT * FROM devices WHERE status = 'online'" },
    { question: '统计各类型设备数量', sql: 'SELECT device_type, COUNT(*) as count FROM devices GROUP BY device_type' },
    { question: '查询本月新增的设备', sql: "SELECT * FROM devices WHERE MONTH(create_time) = MONTH(CURDATE()) AND YEAR(create_time) = YEAR(CURDATE())" }
  ],
  'ddl': [
    { content: 'CREATE TABLE users (\n  id INT PRIMARY KEY,\n  name VARCHAR(100),\n  email VARCHAR(200)\n)' }
  ],
  'documentation': [
    { content: '设备状态说明：online 表示在线，offline 表示离线，maintenance 表示维护中' }
  ]
}

// 填充示例
const fillExample = (index: number) => {
  if (trainType.value === 'question-sql') {
    const ex = examples['question-sql'][index]
    questionSqlForm.value = { question: ex.question, sql: ex.sql }
  } else if (trainType.value === 'ddl') {
    const ex = examples['ddl'][0]
    ddlForm.value = { content: ex.content }
  } else {
    const ex = examples['documentation'][0]
    docForm.value = { content: ex.content }
  }
}

// 表单是否有效
const isFormValid = computed(() => {
  if (trainType.value === 'question-sql') {
    return questionSqlForm.value.question.trim() && questionSqlForm.value.sql.trim()
  } else if (trainType.value === 'ddl') {
    return ddlForm.value.content.trim()
  } else {
    return docForm.value.content.trim()
  }
})

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
  if (!isFormValid.value) {
    ElMessage.warning('请填写必填项')
    return
  }
  
  submitting.value = true
  try {
    let payload: any = {}
    
    if (trainType.value === 'question-sql') {
      // Question-SQL 对训练
      payload = {
        type: 'sql',
        title: questionSqlForm.value.question,  // question 作为 title
        content: questionSqlForm.value.sql
      }
    } else if (trainType.value === 'ddl') {
      // DDL 训练（只需要内容）
      payload = {
        type: 'ddl',
        content: ddlForm.value.content
      }
    } else {
      // 文档训练（只需要内容，无需标题）
      payload = {
        type: 'documentation',
        content: docForm.value.content
      }
    }
    
    const res = await trainManual(payload)
    if (res.success) {
      ElMessage.success('训练成功！')
      // 重置表单
      if (trainType.value === 'question-sql') {
        questionSqlForm.value = { question: '', sql: '' }
      } else if (trainType.value === 'ddl') {
        ddlForm.value = { content: '' }
      } else {
        docForm.value = { content: '' }
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
        <!-- 训练类型选择卡片 -->
        <div class="train-type-cards">
          <div 
            class="train-type-card"
            :class="{ active: trainType === 'question-sql' }"
            @click="trainType = 'question-sql'"
          >
            <div class="card-icon question-sql">
              <el-icon><ChatLineSquare /></el-icon>
            </div>
            <div class="card-info">
              <span class="card-title">问答对训练</span>
              <span class="card-desc">针对特定业务问题训练 SQL</span>
            </div>
            <el-icon v-if="trainType === 'question-sql'" class="card-check"><Select /></el-icon>
          </div>
          
          <div 
            class="train-type-card"
            :class="{ active: trainType === 'ddl' }"
            @click="trainType = 'ddl'"
          >
            <div class="card-icon ddl">
              <el-icon><Grid /></el-icon>
            </div>
            <div class="card-info">
              <span class="card-title">表结构训练</span>
              <span class="card-desc">训练数据库表的 DDL 定义</span>
            </div>
            <el-icon v-if="trainType === 'ddl'" class="card-check"><Select /></el-icon>
          </div>
          
          <div 
            class="train-type-card"
            :class="{ active: trainType === 'documentation' }"
            @click="trainType = 'documentation'"
          >
            <div class="card-icon doc">
              <el-icon><Document /></el-icon>
            </div>
            <div class="card-info">
              <span class="card-title">业务文档训练</span>
              <span class="card-desc">训练业务术语和规则说明</span>
            </div>
            <el-icon v-if="trainType === 'documentation'" class="card-check"><Select /></el-icon>
          </div>
        </div>
        
        <!-- Question-SQL 表单 -->
        <div v-if="trainType === 'question-sql'" class="form-panel">
          <div class="panel-header">
            <el-icon><ChatLineSquare /></el-icon>
            <span>问答对训练</span>
            <el-tooltip content="让 AI 学习「用户问什么 → 应该生成什么 SQL」" placement="top">
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>
          
          <div class="form-item">
            <label class="form-label">
              <span class="label-icon">Q</span>
              业务问题 <span class="required">*</span>
            </label>
            <el-input
              v-model="questionSqlForm.question"
              placeholder="例如：查询本月销售额最高的前10个产品"
            />
            <div class="form-hint">用自然语言描述用户可能会问的问题</div>
          </div>
          
          <div class="form-item">
            <label class="form-label">
              <span class="label-icon sql">SQL</span>
              对应 SQL <span class="required">*</span>
            </label>
            <el-input
              v-model="questionSqlForm.sql"
              type="textarea"
              :rows="5"
              placeholder="SELECT product_name, SUM(amount) as total FROM sales WHERE MONTH(sale_date) = MONTH(CURDATE()) GROUP BY product_name ORDER BY total DESC LIMIT 10"
            />
            <div class="form-hint">这个问题应该执行的 SQL 语句</div>
          </div>
          
          <!-- 示例快捷填充 -->
          <div class="examples-section">
            <span class="examples-label">快速填充示例：</span>
            <div class="example-tags">
              <span 
                v-for="(ex, idx) in examples['question-sql']" 
                :key="idx"
                class="example-tag"
                @click="fillExample(idx)"
              >
                {{ ex.question }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- DDL 表单 -->
        <div v-else-if="trainType === 'ddl'" class="form-panel">
          <div class="panel-header">
            <el-icon><Grid /></el-icon>
            <span>表结构训练</span>
            <el-tooltip content="DDL 会被解析并存储，帮助 AI 理解数据库表结构" placement="top">
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>
          
          <div class="form-item">
            <label class="form-label">DDL 语句 <span class="required">*</span></label>
            <el-input
              v-model="ddlForm.content"
              type="textarea"
              :rows="10"
              placeholder="CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL COMMENT '用户名',
  email VARCHAR(100) COMMENT '邮箱',
  status ENUM('active', 'inactive') DEFAULT 'active' COMMENT '状态',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 可以一次训练多个表
CREATE TABLE orders (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT COMMENT '用户ID',
  amount DECIMAL(10,2) COMMENT '订单金额'
);"
            />
            <div class="form-hint">
              <el-icon><InfoFilled /></el-icon>
              Vanna 会自动解析表名、字段名、类型和注释，用于生成准确的 SQL
            </div>
          </div>
        </div>
        
        <!-- 文档表单 -->
        <div v-else class="form-panel">
          <div class="panel-header">
            <el-icon><Document /></el-icon>
            <span>业务文档训练</span>
            <el-tooltip content="文档内容会被向量化存储，用户提问时通过语义相似度检索" placement="top">
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>
          
          <div class="form-item">
            <label class="form-label">文档内容 <span class="required">*</span></label>
            <el-input
              v-model="docForm.content"
              type="textarea"
              :rows="10"
              placeholder="设备状态说明：
- status = 'online'：设备在线，正常运行
- status = 'offline'：设备离线，无法连接
- status = 'maintenance'：设备维护中，暂停服务

销售指标定义：
- GMV：成交总额，包含已取消订单
- 实际销售额：已完成订单的金额总和
- 客单价：实际销售额 / 订单数"
            />
            <div class="form-hint">
              <el-icon><InfoFilled /></el-icon>
              文档会被向量化存储，当用户提问时，系统会检索语义相似的文档作为 SQL 生成的上下文
            </div>
          </div>
        </div>
        
        <!-- 提交按钮 -->
        <el-button 
          type="primary" 
          class="submit-btn"
          :loading="submitting"
          :disabled="!isFormValid"
          @click="handleManualSubmit"
        >
          <el-icon><Upload /></el-icon>
          提交训练
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
  background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
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
      background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
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
      color: #5b8def;
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
      background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
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
      border-color: #5b8def;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(88, 141, 239, 0.2);
      
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
      color: #5b8def;
      opacity: 0;
      transform: translateX(-10px);
      transition: all 0.3s;
    }
  }
}

.manual-section {
  // 训练类型选择卡片
  .train-type-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }
  
  .train-type-card {
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
      border-color: #e5e7eb;
      transform: translateY(-2px);
    }
    
    &.active {
      background: #fff;
      border-color: #7c3aed;
      box-shadow: 0 4px 12px rgba(124, 58, 237, 0.15);
      
      .card-title {
        color: #7c3aed;
      }
    }
    
    .card-icon {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      color: #fff;
      flex-shrink: 0;
      
      &.question-sql {
        background: linear-gradient(135deg, #00d4ff 0%, #5b8def 100%);
      }
      
      &.ddl {
        background: linear-gradient(135deg, #5b8def 0%, #a855f7 100%);
      }
      
      &.doc {
        background: linear-gradient(135deg, #a855f7 0%, #c084fc 100%);
      }
    }
    
    .card-info {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-width: 0;
      
      .card-title {
        font-size: 14px;
        font-weight: 600;
        color: #333;
        margin-bottom: 2px;
      }
      
      .card-desc {
        font-size: 12px;
        color: #999;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
    
    .card-check {
      color: #5b8def;
      font-size: 18px;
    }
  }
  
  // 表单面板
  .form-panel {
    background: #fafafa;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
  }
  
  .panel-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
    color: #333;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid #eee;
    
    .el-icon {
      color: #5b8def;
    }
    
    .help-icon {
      color: #999;
      font-size: 14px;
      cursor: help;
      margin-left: auto;
      
      &:hover {
        color: #5b8def;
      }
    }
  }
  
  .form-item {
    margin-bottom: 20px;
    
    .form-label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 500;
      color: #333;
      margin-bottom: 8px;
      
      .label-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 6px;
        background: linear-gradient(135deg, #00d4ff 0%, #5b8def 100%);
        color: #fff;
        font-size: 12px;
        font-weight: 700;
        
        &.sql {
          background: linear-gradient(135deg, #5b8def 0%, #a855f7 100%);
          font-size: 10px;
        }
      }
      
      .required {
        color: #ef4444;
      }
    }
    
    .form-hint {
      font-size: 12px;
      color: #999;
      margin-top: 6px;
    }
  }
  
  // 示例区域
  .examples-section {
    background: #fff;
    border-radius: 8px;
    padding: 12px 16px;
    border: 1px dashed #e5e7eb;
    
    .examples-label {
      font-size: 12px;
      color: #666;
      margin-right: 8px;
    }
    
    .example-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    
    .example-tag {
      display: inline-block;
      padding: 6px 12px;
      background: rgba(88, 141, 239, 0.1);
      color: #5b8def;
      border-radius: 16px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
      
      &:hover {
        background: linear-gradient(90deg, #00d4ff 0%, #a855f7 100%);
        color: #fff;
      }
    }
  }
  
  .submit-btn {
    width: 100%;
    height: 52px;
    font-size: 16px;
    font-weight: 600;
    background: linear-gradient(90deg, #00d4ff 0%, #5b8def 50%, #a855f7 100%);
    border: none;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    box-shadow: 0 8px 24px rgba(88, 141, 239, 0.35);
    transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    
    &:hover:not(:disabled) {
      transform: translateY(-2px) scale(1.02);
      box-shadow: 0 12px 28px rgba(88, 141, 239, 0.5);
    }
    
    &:active:not(:disabled) {
      transform: translateY(0) scale(0.98);
    }
    
    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .manual-section {
    .train-type-cards {
      grid-template-columns: 1fr;
    }
    
    .train-type-card {
      .card-desc {
        display: none;
      }
    }
  }
}
</style>
