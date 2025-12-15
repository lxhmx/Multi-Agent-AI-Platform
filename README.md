# Text2SQL 自助式数据库训练与问答平台

基于 **FastAPI + Vue3** 的 Text-to-SQL 系统，集成 DeepSeek/Vanna 能力，提供问答、训练、数据管理的全链路体验，并内置 JWT 登录鉴权。

## 🚀 主要特性
- **登录鉴权**：OAuth2 Password Flow + JWT（访问/刷新令牌），所有接口需登录，默认可用注册/登录页面。
- **智能问答 (Text-to-SQL)**：自然语言转 SQL，支持流式 Agent 模式。
- **多源训练**：SQL 文件、业务文档、手动问答对。
- **数据管理**：训练数据统计、文件列表、删除等。
- **前端体验**：Vue3 + Element Plus 科技风登录/注册页与控制台。

## 🛠️ 技术栈
- 后端：FastAPI、MySQL、python-jose、bcrypt
- 模型/RAG：Vanna、ChromaDB
- 前端：Vue 3 + TypeScript + Vite、Element Plus、ECharts

## 📂 目录结构（简要）
```
api/                 # 后端路由：auth_api.py, ask_api.py, train_api.py, data_manage_api.py, upload_api.py ...
common/              # 依赖、鉴权、DB、工具等
database/init_tables.sql  # 初始化表（users、训练文件记录等）
font-vue/            # 前端源码（Login.vue / Register.vue 等）
app.py               # FastAPI 启动入口
config.py            # 运行配置（DB、鉴权等）- 需手动创建/填写
requirements.txt     # Python 依赖
```

## ⚙️ 配置
`config.py` 示例关键项（参考 `config_template.py`）：
```python
DB_CONFIG = {
    "user": "...",
    "password": "...",
    "host": "...",
    "database": "...",
    "port": 3306,
}

# 鉴权
SECRET_KEY = "replace_with_strong_random"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
```

## 🔧 快速开始
1) 安装依赖
```bash
pip install -r requirements.txt
```
2) 初始化数据库  
在 MySQL 中执行 `database/init_tables.sql` 创建表（users、训练文件记录等）。
3) 启动后端（默认 http://localhost:5000）
```bash
python app.py
```
4) 前端启动（开发模式，端口 3000）
```bash
cd font-vue
npm install
npm run dev
```
Vite 已代理 `/api` 与 `/auth` 到 `http://localhost:5000`。

## 🔑 鉴权与接口
- 前端登录/注册页面：`/login`、`/register`
- 登录成功后本地存储 `access_token` & `refresh_token`，路由守卫自动校验。
- 后端主要接口：
  - `POST /auth/login`、`POST /auth/register`、`POST /auth/refresh`、`GET /auth/me`
  - `POST /api/query`、`POST /api/query-stream`、`POST /api/query-agent`
  - `POST /api/train-sql`、`POST /api/train-document`、`POST /api/train-manual`、`POST /api/upload`
  - `GET /api/data-manage/stats`、`GET /api/data-manage/activity`、`GET /api/data-manage/files`、`DELETE /api/data-manage/files`
  - `GET /api/health`

## ⚠️ 注意
- 需自行在 `config.py` 填写数据库/模型配置及 `SECRET_KEY`。
- 如果需要预置账户，可在执行 `init_tables.sql` 后手动 `INSERT` 一条 bcrypt 哈希的用户记录，再使用登录。
- `.gitignore` 已忽略本地配置与缓存，避免泄露敏感信息。

## 📄 License
MIT
