# Multi-Agent AI Platform

基于 **FastAPI + Vue3** 的多智能体 AI 平台，集成数据分析、流程图生成、浏览器自动化三大智能体，支持自然语言交互和智能路由。

## ✨ 核心特性

- **多智能体架构**：统一的智能体框架，支持自动路由和指定调用
- **流式响应**：基于 SSE 的实时流式输出
- **会话记忆**：支持多轮对话上下文管理
- **JWT 鉴权**：完整的用户认证体系

## 🤖 智能体介绍

### 1. 数据分析智能体 (Data Analyst)
- 自然语言转 SQL 查询
- 数据库数据分析与统计
- 设备实时数据查询
- 基于 Vanna + ChromaDB 的 RAG 能力

### 2. 流程图智能体 (Flowchart)
- 自然语言描述生成流程图
- 输出 mxGraphModel XML 格式
- 集成 draw-image-export 服务渲染图片
- 支持下载 PNG 图片和 .drawio 源文件

### 3. 浏览器自动化智能体 (Browser)
- 基于 Browser-Use 的浏览器自动化
- 支持网页导航、数据采集、表单操作
- 预定义技能脚本模式
- 通用自然语言指令模式

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI, LangChain, Vanna |
| 数据库 | MySQL, ChromaDB |
| LLM | DeepSeek / Qwen (兼容 OpenAI API) |
| 浏览器自动化 | Browser-Use, Playwright |
| 流程图渲染 | draw-image-export2 |
| 前端 | Vue 3 + TypeScript + Vite |
| UI | Element Plus, ECharts |

## 📂 项目结构

```
├── agents/                    # 智能体模块
│   ├── base.py               # 智能体基类
│   ├── data_analyst_agent/   # 数据分析智能体
│   ├── flowchart_agent/      # 流程图智能体
│   └── browser_agent/        # 浏览器自动化智能体
├── api/                       # API 路由
│   ├── agent_router.py       # 智能体统一路由
│   ├── auth_api.py           # 认证接口
│   └── ...
├── common/                    # 公共模块
├── core/                      # 核心组件 (LLM, Memory)
├── font-vue/                  # 前端源码
├── app.py                     # 启动入口
├── config.py                  # 配置文件
└── requirements.txt
```

## ⚙️ 配置

复制 `config_template.py` 为 `config.py` 并填写：

```python
# 数据库配置
DB_CONFIG = {
    'user': 'your_username',
    'password': 'your_password',
    'host': 'localhost',
    'database': 'your_database',
}

# LLM API 配置
API_KEY = "your_api_key"
VANNA_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# JWT 密钥
SECRET_KEY = "your_secret_key"

# 流程图导出服务
EXPORT_SERVER_URL = "http://localhost:8000"
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt

# 浏览器自动化需要额外安装
pip install browser-use playwright
playwright install chromium
```

### 2. 初始化数据库

```bash
mysql -u root -p < database/init_tables.sql
```

### 3. 启动流程图导出服务（可选）

```bash
git clone https://github.com/jgraph/draw-image-export2.git
cd draw-image-export2
npm install
npm start
```

### 4. 启动后端

```bash
python app.py
```

### 5. 启动前端

```bash
cd font-vue
npm install
npm run dev
```

## 📡 API 接口

### 智能体对话
```
POST /api/agent/chat
Content-Type: application/json

{
    "question": "查询今天的销售数据",
    "session_id": "optional-session-id",
    "agent_name": "data_analyst"  // 可选，不填则自动路由
}
```

### 列出智能体
```
GET /api/agent/list
```

### 清除会话记忆
```
POST /api/agent/clear-memory?agent_name=xxx&session_id=xxx
```

## 🔐 认证

- `POST /auth/login` - 登录
- `POST /auth/register` - 注册
- `POST /auth/refresh` - 刷新令牌
- `GET /auth/me` - 获取当前用户

## 📄 License

MIT
