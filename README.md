# Text2SQL 自助式数据报表开发平台

这是一个基于 **Vanna** 和 **DeepSeek** 大模型的智能 Text-to-SQL 数据报表开发平台。用户可以通过自然语言提问，系统自动生成 SQL 语句并查询数据库，最终以图表或表格形式展示结果。

## 🚀 项目特色

- **智能问答 (Text-to-SQL)**: 集成 DeepSeek-V3 大模型，支持复杂的自然语言转 SQL 查询。
- **多模态训练**:
  - **SQL 训练**: 支持上传历史 SQL 记录进行训练。
  - **文档训练**: 支持 PDF, Excel, TXT 等格式的业务文档（数据字典、业务逻辑）训练。
  - **手动训练**: 支持手动录入问答对进行精确干预。
- **向量增强 (RAG)**: 使用 ChromaDB 本地向量数据库存储知识库，通过 RAG 技术提高生成准确率。
- **多租户支持**: 内置多租户数据隔离机制，确保查询安全性。
- **可视化大屏**: 前端基于 Vue3 + ECharts，提供直观的数据展示和管理界面。

## 🛠️ 技术栈

### 后端 (Backend)
- **核心框架**: Python, Flask
- **Text2SQL 引擎**: [Vanna](https://github.com/vanna-ai/vanna)
- **大模型**: DeepSeek-V3 (兼容 OpenAI 接口)
- **向量数据库**: ChromaDB (本地持久化)
- **数据库**: MySQL
- **依赖管理**: `requirements.txt`

### 前端 (Frontend)
- **框架**: Vue 3 + TypeScript + Vite
- **UI 组件库**: Element Plus
- **图表库**: ECharts, Vue-ECharts
- **状态管理**: Pinia
- **网络请求**: Axios

## 📂 目录结构

```
.
├── api/                 # API 接口模块
│   ├── ask_api.py       # 问答相关接口
│   ├── train_sql_api.py # SQL 训练接口
│   ├── train_document_api.py # 文档训练接口
│   └── ...
├── common/              # 公共工具模块
│   ├── vanna_instance.py # Vanna 实例与 DeepSeek 集成
│   └── conn_mysql.py     # 数据库连接池
├── database/            # 数据库初始化脚本
│   └── init_tables.sql
├── dbData/              # ChromaDB 向量数据存储目录
├── font-vue/            # Vue3 前端项目源码
├── train-document/      # 训练文档上传目录
├── train-sql/           # SQL 训练文件目录
├── app.py               # 后端启动入口
├── config.py            # 项目配置文件
├── requirements.txt     # Python 依赖清单
└── README.md            # 项目说明文档
```

## 🔧 快速开始

### 1. 环境准备
- Python 3.8+
- Node.js 16+
- MySQL 8.0+

### 2. 后端部署

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置数据库与 API**
   修改 `config.py` 文件：
   ```python
   # 数据库配置
   DB_CONFIG = {
       'user': 'your_user',
       'password': 'your_password',
       'host': 'your_host',
       'database': 'your_database',
       ...
   }

   # DeepSeek API 配置
   API_KEY = "your_deepseek_api_key"
   ```

3. **初始化数据库**
   在 MySQL 中执行 `database/init_tables.sql` 脚本，创建必要的业务表。

4. **启动服务**
   ```bash
   python app.py
   ```
   后端服务默认运行在 `http://localhost:5000`。

### 3. 前端部署

1. **进入前端目录**
   ```bash
   cd font-vue
   ```

2. **安装依赖**
   ```bash
   npm install
   ```

3. **启动开发服务器**
   ```bash
   npm run dev
   ```
   前端页面默认运行在 `http://localhost:5173` (具体端口视 Vite 配置而定)。

## 📖 API 接口说明

后端提供了一系列 RESTful API，主要包含：

- **POST /api/query**: 提交自然语言问题，返回 SQL 及查询结果。
- **POST /api/train-sql**: 上传 SQL 文件进行训练。
- **POST /api/train-document**: 上传文档进行知识库构建。
- **POST /api/train-manual**: 手动录入 Q&A 对。
- **GET /api/data-manage/stats**: 获取训练数据统计信息。

## ⚠️ 注意事项

- 请确保 `config.py` 中的 API Key 有效且额度充足。
- 首次运行时，系统会自动在 `dbData/` 目录下创建向量数据库文件，请勿随意删除该目录下的文件，否则会导致训练数据丢失。
- 默认开启了多租户过滤（`tenant_id`），在 `common/vanna_instance.py` 中配置。

## 📄 License

[MIT License](LICENSE)
