"""
Vanna 实例管理模块
提供统一的 Vanna 实例获取接口
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import API_KEY, VANNA_MODEL, VANNA_API_BASE
from vanna.legacy.chromadb import ChromaDB_VectorStore
from vanna.legacy.base import VannaBase
from openai import OpenAI

# ========== 多租户配置 ==========
# 默认租户 ID（测试阶段使用）
DEFAULT_TENANT_ID = "136023"


class DeepSeekChat(VannaBase):
    """DeepSeek LLM 集成类"""
    
    def __init__(self, config=None):
        VannaBase.__init__(self, config=config)
        if config is None:
            raise ValueError("config must be provided with api_key and model")
        if "api_key" not in config:
            raise ValueError("config must contain api_key")
        if "model" not in config:
            raise ValueError("config must contain model")
        
        api_key = config["api_key"]
        model = config["model"]
        base_url = config.get("base_url", "https://api.deepseek.com/v1")
        
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def system_message(self, message: str) -> dict:
        return {"role": "system", "content": message}
    
    def user_message(self, message: str) -> dict:
        return {"role": "user", "content": message}
    
    def assistant_message(self, message: str) -> dict:
        return {"role": "assistant", "content": message}
    
    def submit_prompt(self, prompt, **kwargs) -> str:
        chat_response = self.client.chat.completions.create(
            model=self.model,
            messages=prompt,
        )
        return chat_response.choices[0].message.content


class MyVanna(ChromaDB_VectorStore, DeepSeekChat):
    """自定义 Vanna 类，结合 ChromaDB 向量存储和 DeepSeek LLM"""
    
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        DeepSeekChat.__init__(self, config=config)
        self.tenant_id = config.get('tenant_id', DEFAULT_TENANT_ID) if config else DEFAULT_TENANT_ID
    
    def generate_sql(self, question: str, **kwargs) -> str:
        """
        重写 generate_sql 方法，自动添加租户 ID 过滤条件
        """
        # 调用父类方法生成原始 SQL
        sql = super().generate_sql(question, **kwargs)
        
        if sql:
            # 添加租户 ID 过滤条件
            sql = self._add_tenant_filter(sql)
        
        return sql
    
    def _add_tenant_filter(self, sql: str) -> str:
        """
        为 SQL 添加租户 ID 过滤条件
        """
        import re
        
        if not sql or not self.tenant_id:
            return sql
        
        sql_upper = sql.upper().strip()
        
        # 只处理 SELECT 语句
        if not sql_upper.startswith('SELECT'):
            return sql
        
        tenant_condition = f"tenant_id = '{self.tenant_id}'"
        
        # 检查是否已经包含 tenant_id 条件
        if 'TENANT_ID' in sql_upper:
            return sql
        
        # 查找 WHERE 子句的位置
        where_match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)
        
        if where_match:
            # 已有 WHERE 子句，在 WHERE 后添加 tenant_id 条件
            where_pos = where_match.end()
            sql = sql[:where_pos] + f" {tenant_condition} AND" + sql[where_pos:]
        else:
            # 没有 WHERE 子句，需要添加
            # 查找 GROUP BY, ORDER BY, LIMIT, HAVING 等子句的位置
            clause_match = re.search(r'\b(GROUP\s+BY|ORDER\s+BY|LIMIT|HAVING|UNION|;)\b', sql, re.IGNORECASE)
            
            if clause_match:
                # 在这些子句之前插入 WHERE
                insert_pos = clause_match.start()
                sql = sql[:insert_pos] + f" WHERE {tenant_condition} " + sql[insert_pos:]
            else:
                # 没有其他子句，直接在末尾添加
                sql = sql.rstrip(';').strip() + f" WHERE {tenant_condition}"
        
        return sql


# 全局 Vanna 实例
_vn = None


def get_vanna_instance():
    """获取或创建 Vanna 实例（单例模式）"""
    global _vn
    if _vn is None:
        # 使用 Path 处理路径
        db_data_path = Path(__file__).parent.parent / 'dbData'
        db_data_path.mkdir(exist_ok=True)
        
        _vn = MyVanna(config={
            'api_key': API_KEY,
            'model': VANNA_MODEL,
            'base_url': VANNA_API_BASE,
            'path': str(db_data_path),
            'tenant_id': DEFAULT_TENANT_ID
        })
    return _vn
