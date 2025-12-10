# Vanna Text2SQL API 服务

## 快速开始

### 启动统一服务（推荐）

```bash
python app.py
```

服务将在 **http://localhost:5000** 启动，包含所有功能接口。

## 项目结构

```
个人练习/
├── app.py                    # 统一启动入口 ⭐推荐
├── api/
│   ├── train_sql_api.py      # SQL 训练路由
│   ├── train_document_api.py # 文档训练路由
│   ├── ask_api.py            # 问答路由
│   └── README.md             # 本文档
├── common/
│   ├── __init__.py
│   ├── vanna_instance.py     # Vanna 实例管理
│   └── conn_mysql.py         # MySQL 连接
├── train-sql/                # 训练用的 SQL 文件
│   └── create_sql.sql
├── train-document/           # 训练用的文档文件
│   ├── doc/                  # Word/TXT 文档
│   ├── pdf/                  # PDF 文档
│   └── excel/                # Excel 文档
├── dbData/                   # ChromaDB 向量数据
├── config.py                 # 配置文件
└── requirements.txt          # 依赖包
```

## API 接口说明

### 统一服务 (app.py) - 推荐 ⭐

**端口**: 5000

**启动命令**:
```bash
python app.py
```

**所有接口**:

#### 训练接口
- `POST /api/train-sql` - 训练 SQL 文件
- `POST /api/train-document` - 训练文档文件
- `GET /api/training-data` - 获取训练数据统计

#### 查询接口
- `POST /api/query` - 自然语言查询

#### 其他
- `GET /api/health` - 健康检查

**支持的文档格式**:
- Word: `.doc`, `.docx`
- 文本: `.txt`
- PDF: `.pdf`
- Excel: `.xlsx`, `.xls`, `.csv`

## 使用流程

### 步骤 1: 准备训练数据

**SQL 文件** - 在 `train-sql/` 文件夹中放置：
- DDL 文件（CREATE TABLE 等）
- 示例查询（SELECT 语句）
- 文档说明（以 `--` 开头）

**文档文件** - 在 `train-document/` 文件夹中放置：
- `doc/` - Word 文档、TXT 文本
- `pdf/` - PDF 文档
- `excel/` - Excel 表格

### 步骤 2: 启动服务

```bash
python app.py
```

### 步骤 3: 训练模型

```bash
# 训练 SQL
curl -X POST http://localhost:5000/api/train-sql

# 训练文档
curl -X POST http://localhost:5000/api/train-document

# 查看训练数据
curl http://localhost:5000/api/training-data
```

### 步骤 4: 提问查询

```bash
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "查询所有闸门设备"}'
```

## 返回格式

```json
{
    "success": true,
    "question": "查询所有闸门设备",
    "answer": "系统中共有15个闸门设备...",
    "sql": "SELECT * FROM att_irrd_i_st_base WHERE tenant_id = '136023'",
    "table": {
        "columns": [...],
        "rows": [...],
        "total": 15
    },
    "chart": {
        "type": "plotly",
        "config": "..."
    },
    "row_count": 15
}
```

## 多租户支持

系统自动为所有 SQL 查询添加租户 ID 过滤：
- 默认租户 ID: `136023`
- 配置位置: `common/vanna_instance.py` 中的 `DEFAULT_TENANT_ID`

## 注意事项

1. **推荐使用 `app.py` 统一启动**，所有功能集成在一个端口 (5000)
2. 接口代码分别在 `api/` 目录下的三个文件中，保持清晰的模块划分
3. 训练接口只需要在数据更新时调用
4. 服务可以长期运行，处理用户查询
5. 所有接口共享同一个 Vanna 实例和向量数据库
6. 如需独立部署，可直接运行各个 API 文件：
   - `python api/train_sql_api.py` (端口 5000)
   - `python api/train_document_api.py` (端口 5002)
   - `python api/ask_api.py` (端口 5001)
