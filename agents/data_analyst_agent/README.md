# 数据分析智能体 (Data Analyst Agent)

## 概述

数据分析智能体负责处理与数据库查询、数据分析相关的任务。它可以：

- 将自然语言问题转换为 SQL 查询
- 执行数据库查询并返回结果
- 获取设备实时监测数据
- 查看数据库表结构

## 目录结构

```
data_analyst/
├── __init__.py          # 模块入口
├── agent.py             # 智能体主类
├── prompts.py           # 系统提示词和路由关键词
├── README.md            # 本文档
└── tools/               # 工具集
    ├── __init__.py
    ├── text2sql_tool.py     # Text2SQL 查询工具
    ├── schema_tool.py       # 数据库结构查询工具
    └── equipment_tool.py    # 设备实时数据查询工具
```

## 工具说明

### 1. text2sql_query

将用户的自然语言问题转换为 SQL 并执行查询。

**适用场景：**
- 查询数据列表
- 统计数量
- 数据分析

**示例问题：**
- "查询所有设备"
- "统计本月用水量"
- "查找名称包含'水'的设备"

### 2. get_database_schema

获取数据库的表结构信息。

**适用场景：**
- 了解数据库有哪些表
- 查看表字段结构

### 3. get_equipment_property

获取中水数易设备的实时监测数据。

**适用场景：**
- 查询设备实时流量
- 获取闸门当前开度
- 查看设备在线状态

## 使用方式

```python
from agents import AgentRegistry

# 获取智能体
agent = AgentRegistry.get("data_analyst")

# 同步调用
result = agent.run("查询所有设备数量")

# 流式调用
async for chunk in agent.run_stream("统计本月数据"):
    print(chunk, end="")
```

## 扩展指南

### 添加新工具

1. 在 `tools/` 目录下创建新的工具文件
2. 使用 `@tool` 装饰器定义工具函数
3. 在 `tools/__init__.py` 中导出并添加到 `ALL_TOOLS`

### 修改提示词

编辑 `prompts.py` 中的 `SYSTEM_PROMPT` 来调整智能体的行为。

### 调整路由权重

修改 `prompts.py` 中的 `ROUTING_KEYWORDS` 或重写 `agent.py` 中的 `can_handle` 方法。
