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

MYSQL_HOST = DB_CONFIG['host']
MYSQL_PORT = DB_CONFIG['port']
MYSQL_USER = DB_CONFIG['user']
MYSQL_PASSWORD = DB_CONFIG['password']
MYSQL_DATABASE = DB_CONFIG['database']


# 鉴权配置
SECRET_KEY = "please_change_me_to_random_string"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
REFRESH_TOKEN_EXPIRE_DAYS = 7

# DeepSeek API配置
API_KEY = "your_api_key_here"

# Vanna配置
VANNA_MODEL = "deepseek-v3"
VANNA_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 流程图导出服务配置（draw-image-export2）
# 部署方式: git clone https://github.com/jgraph/draw-image-export2.git && npm install && npm start
EXPORT_SERVER_URL = "http://localhost:8000"

# MCP 服务器配置（已弃用，保留兼容）
MCP_SERVERS = {
    "mcpServers": {
        "drawio": {
            "command": "npx",
            "args": ["-y", "drawio-mcp-server"],
            "timeout": 60
        }
    }
}