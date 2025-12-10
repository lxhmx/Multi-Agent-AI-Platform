# 智能知识库问答平台 - 前端

基于 Vue 3 + TypeScript + Element Plus 构建的智能知识库问答平台前端。

## 技术栈

- **Vue 3** - 渐进式 JavaScript 框架
- **TypeScript** - 类型安全的 JavaScript 超集
- **Vite** - 下一代前端构建工具
- **Element Plus** - Vue 3 组件库
- **Vue Router** - 官方路由管理器
- **Pinia** - Vue 状态管理
- **ECharts** - 数据可视化图表库
- **Axios** - HTTP 客户端

## 功能模块

### 1. 知识训练与上传
- 文件上传：支持 .sql, .doc, .docx, .pdf, .xls, .xlsx 格式
- 手动输入：支持 SQL、DDL、文档三种类型
- 自动训练：上传后自动进行模型训练

### 2. 数据管理
- 数据统计：展示 SQL、DDL、文档数量分布
- 活跃度图表：展示近期训练活跃度
- 数据列表：分页展示、搜索、筛选、删除

### 3. 智能问答
- 对话式交互界面
- 自然语言查询数据库
- 展示生成的 SQL 和查询结果
- 支持数据表格展示

## 快速开始

### 安装依赖

```bash
cd font-vue
npm install
```

### 启动开发服务器

```bash
npm run dev
```

前端将在 http://localhost:3000 启动，并自动代理 API 请求到后端 http://localhost:5000

### 构建生产版本

```bash
npm run build
```

## 项目结构

```
font-vue/
├── src/
│   ├── api/           # API 接口封装
│   ├── layouts/       # 布局组件
│   ├── router/        # 路由配置
│   ├── styles/        # 全局样式
│   ├── views/         # 页面组件
│   │   ├── Training.vue    # 知识训练页面
│   │   ├── DataManage.vue  # 数据管理页面
│   │   └── Chat.vue        # 智能问答页面
│   ├── App.vue        # 根组件
│   └── main.ts        # 入口文件
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── openapi.yaml       # API 规范文档
```

## API 接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/upload` | POST | 文件上传 |
| `/api/train-manual` | POST | 手动输入训练 |
| `/api/training-stats` | GET | 获取训练统计 |
| `/api/training-activity` | GET | 获取训练活跃度 |
| `/api/training-data` | GET | 获取训练数据列表 |
| `/api/training-data` | DELETE | 删除训练数据 |
| `/api/query` | POST | 智能问答查询 |

## 文件存储规则

上传的文件按日期存储：
- SQL 文件: `train-sql/2025-12-09/filename.sql`
- 文档文件: `train-document/2025-12-09/filename.pdf`

## 配合后端使用

1. 启动后端服务：
```bash
cd ..
python app.py
```

2. 启动前端开发服务器：
```bash
cd font-vue
npm run dev
```

3. 访问 http://localhost:3000
