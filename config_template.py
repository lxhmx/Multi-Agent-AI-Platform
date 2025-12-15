"""
配置文件模板
请复制此文件为 config.py 并填入实际配置
"""

# 数据库配置
DB_CONFIG = {
    'user': 'your_username',
    'password': 'your_password',
    'host': 'localhost',
    'port': 3306,
    'database': 'your_database',
    'charset': 'utf8mb4'
}

# 鉴权配置
SECRET_KEY = "please_change_me_to_random_string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

# DeepSeek API配置
API_KEY = "your_api_key_here"

# Vanna配置
VANNA_MODEL = "deepseek-v3"
VANNA_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
