"""
服务器监控配置

认证方式 (auth_type):
- "key": 密钥文件认证，需要 key_path，可选 key_passphrase
- "password": 密码认证，需要 password
- "agent": 使用系统 SSH Agent
"""

# 监控的服务器列表
MONITOR_SERVERS = {
    # 示例1: 密钥认证（带密码）
    "lxhAgent": {
        "host": "43.138.0.100",
        "port": 22,
        "username": "ubuntu",
        "auth_type": "key",
        "key_path": "/app/ssh_keys/windows_login1.pem",
        "key_passphrase": "lxh13085951873@",
        "aliases": ["lxh", "agent服务器", "主服务器"]
    },
    
    # 示例2: 密钥认证（无密码）
    # "生产Web服务器": {
    #     "host": "192.168.1.10",
    #     "port": 22,
    #     "username": "deploy",
    #     "auth_type": "key",
    #     "key_path": "~/.ssh/id_rsa",
    #     "aliases": ["web", "prod-web"]
    # },
    
    # 示例3: 密码认证
    # "测试服务器": {
    #     "host": "192.168.1.30",
    #     "port": 22,
    #     "username": "root",
    #     "auth_type": "password",
    #     "password": "your_password",
    #     "aliases": ["test", "测试"]
    # },
    
    # 示例4: SSH Agent 认证
    # "开发服务器": {
    #     "host": "192.168.1.40",
    #     "port": 22,
    #     "username": "dev",
    #     "auth_type": "agent",
    #     "aliases": ["dev", "开发"]
    # },
}

# 告警阈值配置
ALERT_THRESHOLDS = {
    "cpu_percent": {"warning": 80, "critical": 95},
    "memory_percent": {"warning": 85, "critical": 95},
    "disk_percent": {"warning": 80, "critical": 90},
    "load_average_1m": {"warning": 4.0, "critical": 8.0}
}
