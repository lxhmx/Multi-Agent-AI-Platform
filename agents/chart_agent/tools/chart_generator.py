"""
图表生成工具
整合 SQL 生成、执行、图表选择和数据映射
"""

import json
import copy
from decimal import Decimal
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional
from neo4j import GraphDatabase
from openai import OpenAI
from langchain_core.tools import tool

import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import API_KEY, VANNA_MODEL, VANNA_API_BASE, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from database.mysql_client import MySQLClient


def convert_to_serializable(obj):
    """将不可序列化的类型转换为可序列化类型"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj


class Neo4jSQLGenerator:
    """基于 Neo4j 图谱的 SQL 生成器"""
    
    def __init__(self, 
                 neo4j_uri=NEO4J_URI,
                 neo4j_user=NEO4J_USER,
                 neo4j_password=NEO4J_PASSWORD):
        
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri, auth=(neo4j_user, neo4j_password)
        )
        self.llm_client = OpenAI(api_key=API_KEY, base_url=VANNA_API_BASE)
        self.model = VANNA_MODEL
        
    def close(self):
        self.neo4j_driver.close()
        
    def search_relevant_tables(self, keywords: List[str]) -> List[Dict]:
        """根据关键词搜索相关表"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                UNWIND $keywords AS keyword
                MATCH (t:Table)
                WHERE toLower(t.name) CONTAINS toLower(keyword)
                   OR toLower(t.comment) CONTAINS toLower(keyword)
                WITH DISTINCT t
                OPTIONAL MATCH (c:Column)-[:BELONGS_TO]->(t)
                WITH t, collect({
                    name: c.name, 
                    type: c.data_type, 
                    comment: c.comment,
                    is_pk: c.is_pk
                }) AS columns
                RETURN t.name AS table_name, t.comment AS table_comment, columns
            """, keywords=keywords)
            return [dict(r) for r in result]
    
    def search_by_column(self, keywords: List[str]) -> List[Dict]:
        """根据字段名/注释搜索相关表"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                UNWIND $keywords AS keyword
                MATCH (c:Column)-[:BELONGS_TO]->(t:Table)
                WHERE toLower(c.name) CONTAINS toLower(keyword)
                   OR toLower(c.comment) CONTAINS toLower(keyword)
                WITH DISTINCT t
                OPTIONAL MATCH (col:Column)-[:BELONGS_TO]->(t)
                WITH t, collect({
                    name: col.name, 
                    type: col.data_type, 
                    comment: col.comment,
                    is_pk: col.is_pk
                }) AS columns
                RETURN t.name AS table_name, t.comment AS table_comment, columns
            """, keywords=keywords)
            return [dict(r) for r in result]
            
    def get_join_path(self, table1: str, table2: str) -> Optional[Dict]:
        """获取两表之间的 JOIN 路径"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH path = shortestPath(
                    (t1:Table {name: $t1})-[:JOINS_WITH*1..4]-(t2:Table {name: $t2})
                )
                WITH path, [n IN nodes(path) | n.name] AS tables
                UNWIND range(0, size(tables)-2) AS i
                WITH path, tables, i
                MATCH (ta:Table {name: tables[i]})-[r:JOINS_WITH]-(tb:Table {name: tables[i+1]})
                WITH tables, collect(DISTINCT {
                    from_table: tables[i], 
                    to_table: tables[i+1], 
                    join_columns: r.join_columns
                }) AS joins
                RETURN tables, joins
                LIMIT 1
            """, t1=table1, t2=table2)
            
            record = result.single()
            if record:
                return {'tables': record['tables'], 'joins': record['joins']}
            return None

    def get_table_schema(self, table_name: str) -> Dict:
        """获取表的完整 schema"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (t:Table {name: $name})
                OPTIONAL MATCH (c:Column)-[:BELONGS_TO]->(t)
                OPTIONAL MATCH (c)-[fk:FK_TO]->(target:Column)-[:BELONGS_TO]->(tt:Table)
                WITH t, c, tt, target
                ORDER BY c.is_pk DESC, c.name
                WITH t, collect({
                    name: c.name,
                    type: c.column_type,
                    comment: c.comment,
                    is_pk: c.is_pk,
                    fk_table: tt.name,
                    fk_column: target.name
                }) AS columns
                RETURN t.name AS table_name, t.comment AS table_comment, columns
            """, name=table_name)
            
            record = result.single()
            if record:
                return dict(record)
            return None
    
    def extract_keywords(self, question: str) -> List[str]:
        """从问题中提取关键词"""
        prompt = f"""从以下问题中提取用于数据库查询的关键词（表名、字段名、业务术语）。
只返回关键词列表，用逗号分隔，不要其他内容。

问题：{question}

关键词："""
        
        response = self.llm_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        keywords = response.choices[0].message.content.strip()
        return [k.strip() for k in keywords.split(',') if k.strip()]
    
    def build_context(self, tables: List[Dict], joins: List[Dict] = None) -> str:
        """构建给 LLM 的上下文"""
        context_parts = ["### 数据库表结构\n"]
        
        for table in tables:
            table_name = table['table_name']
            table_comment = table.get('table_comment', '')
            columns = table.get('columns', [])
            
            context_parts.append(f"\n表名: {table_name}")
            if table_comment:
                context_parts.append(f"说明: {table_comment}")
            context_parts.append("字段:")
            
            for col in columns:
                col_desc = f"  - {col['name']} ({col['type']})"
                if col.get('is_pk'):
                    col_desc += " [主键]"
                if col.get('comment'):
                    col_desc += f" -- {col['comment']}"
                if col.get('fk_table'):
                    col_desc += f" -> {col['fk_table']}.{col['fk_column']}"
                context_parts.append(col_desc)
        
        if joins:
            context_parts.append("\n### 表关联关系")
            for join in joins:
                join_cols = join.get('join_columns', [])
                if join_cols:
                    context_parts.append(
                        f"  {join['from_table']} JOIN {join['to_table']} ON {join_cols[0]}"
                    )
        
        return "\n".join(context_parts)

    def generate_sql(self, question: str, additional_tables: List[str] = None) -> Dict:
        """根据用户问题生成 SQL"""
        keywords = self.extract_keywords(question)
        
        tables_by_name = self.search_relevant_tables(keywords)
        tables_by_column = self.search_by_column(keywords)
        
        all_tables = {t['table_name']: t for t in tables_by_name}
        for t in tables_by_column:
            if t['table_name'] not in all_tables:
                all_tables[t['table_name']] = t
        
        if additional_tables:
            for table_name in additional_tables:
                if table_name not in all_tables:
                    schema = self.get_table_schema(table_name)
                    if schema:
                        all_tables[table_name] = schema
        
        tables = list(all_tables.values())
        
        if not tables:
            return {
                'sql': None,
                'tables_used': [],
                'explanation': '未找到相关的表'
            }
        
        table_names = [t['table_name'] for t in tables]
        all_joins = []
        
        if len(table_names) > 1:
            for i, t1 in enumerate(table_names):
                for t2 in table_names[i+1:]:
                    path = self.get_join_path(t1, t2)
                    if path and path.get('joins'):
                        all_joins.extend(path['joins'])
        
        context = self.build_context(tables, all_joins)
        
        prompt = f"""{context}

### 用户问题
{question}

### 要求
1. 根据上面的表结构和关联关系，生成正确的 MySQL SQL 查询语句
2. 使用合适的 JOIN 连接相关表
3. 字段名和表名使用反引号包裹
4. 只返回 SQL 语句，不要其他解释

### SQL
"""
        
        response = self.llm_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        sql = response.choices[0].message.content.strip()
        if sql.startswith('```'):
            sql = sql.split('\n', 1)[1] if '\n' in sql else sql[3:]
        if sql.endswith('```'):
            sql = sql.rsplit('```', 1)[0]
        sql = sql.strip()
        
        return {
            'sql': sql,
            'tables_used': table_names,
            'joins': all_joins
        }


class ChartTemplateManager:
    """图表模板管理器"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.index = self._load_index()
        self.llm_client = OpenAI(api_key=API_KEY, base_url=VANNA_API_BASE)
        self.model = VANNA_MODEL
    
    def _load_index(self) -> Dict:
        """加载模板索引"""
        index_path = self.templates_dir / "index.json"
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_template(self, chart_type: str) -> Dict:
        """加载指定类型的图表模板"""
        template_path = self.templates_dir / f"{chart_type}.json"
        if not template_path.exists():
            raise ValueError(f"模板不存在: {chart_type}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_data_type(self, data: List[Dict], columns: List[str]) -> str:
        """分析数据类型"""
        if not data:
            return "empty"
        
        # 单值
        if len(data) == 1 and len(columns) <= 2:
            return "single_value"
        
        # 检查是否有时间列
        time_keywords = ['date', 'time', '日期', '时间', 'month', 'year', 'day']
        for col in columns:
            if any(k in col.lower() for k in time_keywords):
                return "time_series"
        
        # 分类数据
        return "category_value"
    
    def select_chart_type(self, question: str, data_type: str) -> str:
        """使用 LLM 选择合适的图表类型"""
        available_types = list(self.index['templates'].keys())
        
        # 构建图表描述
        type_descriptions = []
        for t, info in self.index['templates'].items():
            type_descriptions.append(f"- {t}: {info['description']}，适用于{', '.join(info['scenarios'])}")
        
        prompt = f"""根据以下信息，选择最合适的图表类型。

用户问题：{question}
数据类型：{data_type}

可选图表类型：
{chr(10).join(type_descriptions)}

只返回图表类型名称（如 gauge、pie、bar、line、bar_horizontal），不要其他内容。
"""
        
        response = self.llm_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        
        chart_type = response.choices[0].message.content.strip().lower()
        
        # 验证返回的类型是否有效
        if chart_type not in available_types:
            # 根据数据类型选择默认图表
            type_mapping = {
                "single_value": "gauge",
                "time_series": "line",
                "category_value": "bar"
            }
            chart_type = type_mapping.get(data_type, "bar")
        
        return chart_type
    
    def map_data_to_option(self, template: Dict, data: List[Dict], 
                           columns: List[str], question: str) -> Dict:
        """将数据映射到 EChart option"""
        option = copy.deepcopy(template['option'])
        chart_type = template['type']
        
        if chart_type == "gauge":
            return self._map_gauge(option, data, columns, question)
        elif chart_type == "pie":
            return self._map_pie(option, data, columns, question)
        elif chart_type == "bar":
            return self._map_bar(option, data, columns, question)
        elif chart_type == "line":
            return self._map_line(option, data, columns, question)
        elif chart_type == "bar_horizontal":
            return self._map_bar_horizontal(option, data, columns, question)
        
        return option
    
    def _map_gauge(self, option: Dict, data: List[Dict], 
                   columns: List[str], question: str) -> Dict:
        """映射仪表盘数据"""
        if data:
            row = data[0]
            # 取第一个数值列
            value = None
            for col in columns:
                v = row.get(col)
                if isinstance(v, (int, float)):
                    value = v
                    break
            
            if value is not None:
                # 如果值大于1且小于等于100，认为是百分比
                # 如果值小于等于1，转换为百分比
                if value <= 1:
                    value = round(value * 100, 2)
                
                option['series'][0]['data'][0]['value'] = value
                option['series'][0]['data'][0]['name'] = self._extract_label(question)
                option['series'][0]['name'] = self._extract_label(question)
        
        return option
    
    def _map_pie(self, option: Dict, data: List[Dict], 
                 columns: List[str], question: str) -> Dict:
        """映射饼图数据"""
        if len(columns) >= 2:
            name_col = columns[0]
            value_col = columns[1]
            
            pie_data = []
            legend_data = []
            
            for row in data:
                name = str(row.get(name_col, ''))
                value = row.get(value_col, 0)
                pie_data.append({"name": name, "value": value})
                legend_data.append(name)
            
            option['series'][0]['data'] = pie_data
            option['series'][0]['name'] = self._extract_label(question)
            option['legend']['data'] = legend_data
        
        return option
    
    def _map_bar(self, option: Dict, data: List[Dict], 
                 columns: List[str], question: str) -> Dict:
        """映射柱状图数据"""
        if len(columns) >= 2:
            x_col = columns[0]
            y_col = columns[1]
            
            x_data = [str(row.get(x_col, '')) for row in data]
            y_data = [row.get(y_col, 0) for row in data]
            
            option['xAxis']['data'] = x_data
            option['series'][0]['data'] = y_data
            option['series'][0]['name'] = self._extract_label(question)
        
        return option
    
    def _map_line(self, option: Dict, data: List[Dict], 
                  columns: List[str], question: str) -> Dict:
        """映射折线图数据"""
        if len(columns) >= 2:
            x_col = columns[0]
            y_col = columns[1]
            
            x_data = [str(row.get(x_col, '')) for row in data]
            y_data = [row.get(y_col, 0) for row in data]
            
            option['xAxis']['data'] = x_data
            option['series'][0]['data'] = y_data
            option['series'][0]['name'] = self._extract_label(question)
        
        return option
    
    def _map_bar_horizontal(self, option: Dict, data: List[Dict], 
                            columns: List[str], question: str) -> Dict:
        """映射横向柱状图数据"""
        if len(columns) >= 2:
            name_col = columns[0]
            value_col = columns[1]
            
            y_data = [str(row.get(name_col, '')) for row in data]
            x_data = [row.get(value_col, 0) for row in data]
            
            option['yAxis']['data'] = y_data
            option['series'][0]['data'] = x_data
            option['series'][0]['name'] = self._extract_label(question)
        
        return option
    
    def _extract_label(self, question: str) -> str:
        """从问题中提取标签"""
        # 简单提取，可以用 LLM 优化
        keywords = ['在线率', '完成率', '数量', '统计', '分布', '趋势', '排名', '占比']
        for k in keywords:
            if k in question:
                return k
        return "数据"


@tool
def generate_chart(question: str) -> str:
    """
    根据用户问题生成可视化图表。
    
    这个工具会：
    1. 分析问题，生成对应的 SQL 查询
    2. 执行 SQL 获取数据
    3. 根据数据特征选择合适的图表类型
    4. 将数据映射到 EChart option
    
    Args:
        question: 用户的自然语言问题，如"闸门的在线率是多少"
    
    Returns:
        str: 包含特殊标记的字符串，格式为 [CHART:json_data] 或错误信息
    """
    sql_generator = None
    mysql_client = None
    
    try:
        # 1. 生成 SQL
        print(f"[ChartGenerator] 开始处理问题: {question}")
        sql_generator = Neo4jSQLGenerator()
        sql_result = sql_generator.generate_sql(question)
        
        if not sql_result.get('sql'):
            print(f"[ChartGenerator] SQL 生成失败: {sql_result}")
            return f"无法生成查询：{sql_result.get('explanation', '未找到相关数据表')}"
        
        sql = sql_result['sql']
        print(f"[ChartGenerator] 生成的 SQL: {sql}")
        
        # 2. 执行 SQL
        mysql_client = MySQLClient()
        data, columns = mysql_client.execute_query_with_columns(sql)
        # 转换 Decimal 等不可序列化类型
        data = convert_to_serializable(data)
        print(f"[ChartGenerator] 查询结果: {len(data)} 条数据, 列: {columns}")
        
        if not data:
            return "查询成功但没有数据"
        
        # 3. 选择图表类型
        template_manager = ChartTemplateManager()
        data_type = template_manager.analyze_data_type(data, columns)
        chart_type = template_manager.select_chart_type(question, data_type)
        print(f"[ChartGenerator] 数据类型: {data_type}, 图表类型: {chart_type}")
        
        # 4. 加载模板并映射数据
        template = template_manager.load_template(chart_type)
        option = template_manager.map_data_to_option(template, data, columns, question)
        print(f"[ChartGenerator] 图表 option 生成完成")
        
        # 5. 返回特殊标记格式，供 agent 识别并发送 SSE 事件
        chart_data = {
            "chart_type": chart_type,
            "chart_name": template['name'],
            "option": option,
            "raw_data": data[:10],  # 只返回前10条原始数据
            "total_count": len(data)
        }
        
        result = f"[CHART:{json.dumps(chart_data, ensure_ascii=False)}]"
        print(f"[ChartGenerator] 返回结果长度: {len(result)}")
        return result
        
    except Exception as e:
        import traceback
        print(f"[ChartGenerator] 异常: {traceback.format_exc()}")
        return f"生成图表失败: {str(e)}"
    
    finally:
        if sql_generator:
            sql_generator.close()
        if mysql_client:
            mysql_client.close()
