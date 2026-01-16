# Multi-Agent AI Platform - 视界拾贝

<p align="center">
  <b>🌟 基于 FastAPI + Vue3 + LangChain 的多智能体 AI 平台</b>
</p>

<p align="center">
  <a href="https://github.com/your-repo/stars"><img src="https://img.shields.io/github/stars/your-repo?style=social" alt="GitHub stars"></a>
  <a href="http://www.lxhmx.top"><img src="https://img.shields.io/badge/Demo-在线演示-blue" alt="Demo"></a>
  <a href="#license"><img src="https://img.shields.io/badge/License-MIT-green" alt="License"></a>
</p>

集成数据分析、流程图生成、浏览器自动化、视频内容总结、服务器监控、智能图表六大智能体，支持自然语言交互和智能路由。

🔗 **在线演示**: [www.lxhmx.top](http://www.lxhmx.top)

---

## ✨ 核心特性

- **🤖 多智能体架构**：统一的 BaseAgent 框架，支持自动路由和指定调用，新增智能体只需继承基类
- **🌊 SSE 流式响应**：支持 answer/image/chart/image_meta 等多种事件类型，前端实时渲染
- **💬 会话记忆管理**：AgentMemory 支持多轮对话上下文保持，可配置最大轮数
- **🔐 JWT 完整鉴权**：用户注册、登录、Token 刷新，保障 API 安全访问
- **📝 智能路由**：基于关键词匹配和置信度评分，自动分发问题到最合适的智能体

---

## 🤖 智能体介绍

### 1. 数据分析智能体 (Data Analyst)
- 自然语言转 SQL 查询（Text2SQL）
- 基于 Vanna + ChromaDB 的 RAG 能力
- 数据库数据分析与统计
- 设备实时数据查询

### 2. 流程图智能体 (Flowchart)
- 自然语言描述生成流程图
- LLM 生成 mxGraphModel XML 格式
- 集成 draw-image-export 服务渲染图片
- 支持下载 PNG 图片和 .drawio 源文件

### 3. 浏览器自动化智能体 (Browser)
- 基于 Browser-Use + Playwright 的浏览器自动化
- 支持网页导航、数据采集、表单操作
- 预定义技能脚本模式（Skills）
- 通用自然语言指令模式

### 4. 视频总结智能体 (Video Summary)
- 自动识别抖音、B站、小红书、视频号链接
- Playwright 获取视频真实地址并下载
- 调用多模态模型分析视频内容
- 生成结构化的内容摘要

### 5. 服务器监控智能体 (Server Monitor)
- SSH 连接远程服务器
- 监控 CPU、内存、磁盘使用情况
- 检查系统负载和进程状态
- 告警检测和通知

### 6. 智能图表智能体 (Chart Agent)
- 理解用户数据查询需求
- 自动生成 SQL 并执行查询
- 智能选择合适的图表类型
- 返回 ECharts 可视化配置

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue3)                       │
│              Element Plus + ECharts + TypeScript             │
└─────────────────────────────┬───────────────────────────────┘
                              │ SSE Stream
┌─────────────────────────────▼───────────────────────────────┐
│                     API Layer (FastAPI)                      │
│         agent_router.py  │  auth_api.py  │  session_api.py   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    AgentRegistry (路由层)                     │
│          关键词匹配 + 置信度评分 → 智能体分发                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      Agents (智能体层)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │DataAnalyst│ │Flowchart │ │ Browser  │ │  VideoSummary    │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
│  ┌──────────┐ ┌──────────┐                                   │
│  │  Chart   │ │ServerMon │  ← 继承 BaseAgent                 │
│  └──────────┘ └──────────┘                                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      Core Layer (核心层)                      │
│     LLM (Qwen/DeepSeek)  │  Memory  │  Tools (LangChain)     │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    Storage Layer (存储层)                     │
│         MySQL  │  ChromaDB (向量)  │  Redis (会话)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI, LangChain, Vanna |
| 数据库 | MySQL, ChromaDB (向量存储) |
| LLM | Qwen3 / DeepSeek (兼容 OpenAI API) |
| 浏览器自动化 | Browser-Use, Playwright |
| 流程图渲染 | draw-image-export2 |
| 前端框架 | Vue 3 + TypeScript + Vite |
| UI 组件 | Element Plus, ECharts |
| 认证 | JWT (python-jose) |

---

## 📂 项目结构

```
├── agents/                    # 智能体模块
│   ├── base.py               # 智能体基类 (BaseAgent)
│   ├── data_analyst_agent/   # 数据分析智能体
│   ├── flowchart_agent/      # 流程图智能体
│   ├── browser_agent/        # 浏览器自动化智能体
│   ├── video_summary_agent/  # 视频总结智能体
│   ├── server_monitor_agent/ # 服务器监控智能体
│   ├── chart_agent/          # 智能图表智能体
│   └── __init__.py           # AgentRegistry 注册表
├── api/                       # API 路由
│   ├── agent_router.py       # 智能体统一路由 (SSE)
│   ├── auth_api.py           # 认证接口
│   ├── session_api.py        # 会话管理
│   └── ...
├── common/                    # 公共模块
│   ├── langchain_llm.py      # LLM 封装
│   └── security.py           # JWT 认证
├── core/                      # 核心组件
│   ├── llm.py                # LLM 实例管理
│   └── memory.py             # AgentMemory 会话记忆
├── font-vue/                  # 前端源码
├── app.py                     # 启动入口
├── config.py                  # 配置文件
└── requirements.txt
```

---

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

---

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

---

## 📡 API 接口

### 智能体对话（SSE 流式）
```http
POST /api/agent/chat
Content-Type: application/json

{
    "question": "查询今天的销售数据",
    "session_id": "optional-session-id",
    "agent_name": "data_analyst"  // 可选，不填则自动路由
}
```

**SSE 事件类型：**
| 事件 | 说明 |
|------|------|
| `answer` | 文本回答片段 |
| `answer_base64` | Base64 编码文本（含换行符） |
| `image` | Base64 图片数据 |
| `image_meta` | 图片元信息 JSON |
| `chart` | ECharts 图表配置 |
| `done` | 完成信号 |
| `error` | 错误信息 |

### 列出智能体
```http
GET /api/agent/list
```

### 清除会话记忆
```http
POST /api/agent/clear-memory?agent_name=xxx&session_id=xxx
```

---

## 🔐 认证接口

| 接口 | 说明 |
|------|------|
| `POST /auth/login` | 用户登录 |
| `POST /auth/register` | 用户注册 |
| `POST /auth/refresh` | 刷新 Token |
| `GET /auth/me` | 获取当前用户信息 |

---

## 🔧 扩展新智能体

只需继承 `BaseAgent` 并实现抽象方法：

```python
from agents.base import BaseAgent

class MyAgent(BaseAgent):
    name = "my_agent"
    description = "我的自定义智能体"
    
    def get_tools(self):
        return [...]  # LangChain 工具列表
    
    def get_system_prompt(self):
        return "你是一个..."
    
    async def run_stream(self, question, session_id=None):
        # 流式执行逻辑
        yield "回答内容..."
    
    def can_handle(self, question):
        # 返回 0-1 置信度分数
        return 0.5
```

然后在 `agents/__init__.py` 中注册即可。

---

## 📄 License

MIT

---

<p align="center">
  <b>⭐ 如果这个项目对你有帮助，欢迎 Star 支持！</b>
</p>



st_id as stId, water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, tm, id
st_id as stId, pa, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, water_z, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, tm, id
st_id as stId, pa, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, water_z, max_water_z, min_water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, qc_yw1, tm, id
st_id as stId, qc_yw1, max_qc_yw1, min_qc_yw1, tm, id
st_id as stId, qc_yw1, max_qc_yw1, min_qc_yw1, tm, id
st_id as stId, qc_yw1, max_qc_yw1, min_qc_yw1, tm, id
st_id as stId, qc_yw1, max_qc_yw1 min_qc_yw1, tm, id
st_id as stId, moment_flow1, tm, id
st_id as stId, moment_flow1, max_moment_flow1, min_moment_flow1, tm, id
st_id as stId, moment_flow1, max_moment_flow1, min_moment_flow1, tm, id
st_id as stId, moment_flow1, max_moment_flow1, min_moment_flow1, tm, id
st_id as stId, moment_flow1, max_moment_flow1, min_moment_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, qc_yw2, tm, id
st_id as stId, qc_yw2, max_qc_yw2, min_qc_yw2, tm, id
st_id as stId, qc_yw2, max_qc_yw2, min_qc_yw2, tm, id
st_id as stId, qc_yw2, max_qc_yw2, min_qc_yw2, tm, id
st_id as stId, qc_yw2, max_qc_yw2, min_qc_yw2, tm, id
st_id as stId, water_z2, tm, id
st_id as stId, water_z2, max_water_z2, min_water_z2, tm, id
st_id as stId, water_z2, max_water_z2, min_water_z2, tm, id
st_id as stId, water_z2, max_water_z2, min_water_z2, tm, id
st_id as stId, water_z2, max_water_z2, min_water_z2, tm, id
st_id as stId, water_z1, tm, id
st_id as stId, water_z1, max_water_z1, min_water_z1,tm, id
st_id as stId, water_z1, max_water_z1, min_water_z1,tm, id
st_id as stId, water_z1, max_water_z1, min_water_z1,tm, id
st_id as stId, water_z1, max_water_z1, min_water_z1,tm, id
st_id as stId, moment_flow2, tm, id
st_id as stId, moment_flow2, max_moment_flow2, min_moment_flow2, tm, id
st_id as stId, moment_flow2, max_moment_flow2, min_moment_flow2, tm, id
st_id as stId, moment_flow2, max_moment_flow2, min_moment_flow2, tm, id
st_id as stId, moment_flow2, max_moment_flow2, min_moment_flow2, tm, id
st_id as stId, total_flow2, tm, id
st_id as stId, total_flow2, tm, id
st_id as stId, total_flow2, tm, id
st_id as stId, total_flow2, tm, id
st_id as stId, total_flow2, tm, id
st_id as stId, moment_flow1, tm, id
st_id as stId, moment_flow1, max_moment_flow1, min_moment_flow1,tm, id
st_id as stId, moment_flow1, max_moment_flow1, min_moment_flow1,tm, id
st_id as stId, moment_flow1, max_moment_flow1, min_moment_flow1,tm, id
st_id as stId, moment_flow1, max_moment_flow1, min_moment_flow1,tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId, total_flow1, tm, id
st_id as stId,  accum_q, water_z, max_z, min_z, min_q,  max_q,  q, pa, max_pa, min_pa,tm, id
st_id as stId,  accum_q, water_z, max_z, min_z, min_q,  max_q,  q, pa, max_pa, min_pa,tm, id
st_id as stId,  accum_q, water_z, max_z, min_z, min_q,  max_q,  q, pa, max_pa, min_pa,tm, id
st_id as stId,  accum_q, water_z, max_z, min_z, min_q,  max_q,  q, pa, max_pa, min_pa, tm, id
st_id as stId,  accum_q, water_z, max_z, min_z, min_q,  max_q,  q, pa, max_pa, min_pa, tm, id
st_id as stId, q, tm, id
st_id as stId, water_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, water_z, max_z, min_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, water_z, max_z, min_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, water_z, max_z, min_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, q, max_q, min_q, tm, id
st_id as stId, water_z, max_z, min_z, tm, id
st_id as stId, accum_q, tm, id
st_id as stId, pa, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, pa, max_pa, min_pa, tm, id
st_id as stId, u_temperature, tm, id
st_id as stId, u_temperature, max_u_temperature, min_u_temperature, tm, id
st_id as stId, u_temperature, max_u_temperature, min_u_temperature, tm, id
st_id as stId, u_temperature, max_u_temperature, min_u_temperature, tm, id
st_id as stId, u_temperature, max_u_temperature, min_u_temperature, tm, id
st_id as stId, v_temperature, tm, id
st_id as stId, v_temperature, max_v_temperature, min_v_temperature, tm, id
st_id as stId, v_temperature, max_v_temperature, min_v_temperature, tm, id
st_id as stId, v_temperature, max_v_temperature, min_v_temperature, tm, id
st_id as stId, v_temperature, max_v_temperature, min_v_temperature, tm, id
st_id as stId, w_temperature, tm, id
st_id as stId, w_temperature, max_w_temperature, min_w_temperature, tm, id
st_id as stId, w_temperature, max_w_temperature, min_w_temperature, tm, id
st_id as stId, w_temperature, max_w_temperature, min_w_temperature, tm, id
st_id as stId, w_temperature, max_w_temperature, min_w_temperature, tm, id
st_id as stId, left_temperature, tm, id
st_id as stId, left_temperature, max_left_temperature, min_left_temperature, tm, id
st_id as stId, left_temperature, max_left_temperature, min_left_temperature, tm, id
st_id as stId, left_temperature, max_left_temperature, min_left_temperature, tm, id
st_id as stId, left_temperature, max_left_temperature, min_left_temperature, tm, id
st_id as stId, right_temperature, tm, id
st_id as stId, right_temperature, max_right_temperature, min_right_temperature, tm, id
st_id as stId, right_temperature, max_right_temperature, min_right_temperature, tm, id
st_id as stId, right_temperature, max_right_temperature, min_right_temperature, tm, id
st_id as stId, right_temperature, max_right_temperature, min_right_temperature, tm, id
st_id as stId, water_z, accum_q, q, v, tm, id