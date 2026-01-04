"""
SSH 连接管理器
"""

import paramiko
import os
from typing import Optional
from agents.server_monitor_agent.config import MONITOR_SERVERS


class SSHManager:
    """SSH 连接管理器"""
    
    _connections: dict[str, paramiko.SSHClient] = {}
    
    @classmethod
    def get_connection(cls, server_name: str) -> paramiko.SSHClient:
        """获取或创建 SSH 连接，支持多种认证方式"""
        if server_name in cls._connections:
            client = cls._connections[server_name]
            if client.get_transport() and client.get_transport().is_active():
                return client
        
        config = MONITOR_SERVERS.get(server_name)
        if not config:
            raise ValueError(f"服务器 '{server_name}' 不存在")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        auth_type = config.get("auth_type", "key")
        
        connect_kwargs = {
            "hostname": config["host"],
            "port": config.get("port", 22),
            "username": config["username"],
            "timeout": 10,
            "allow_agent": False,
            "look_for_keys": False
        }
        
        if auth_type == "key":
            # 密钥文件认证
            key_path = os.path.expanduser(config["key_path"])
            passphrase = config.get("key_passphrase")
            pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
            connect_kwargs["pkey"] = pkey
            
        elif auth_type == "password":
            # 密码认证
            connect_kwargs["password"] = config["password"]
            
        elif auth_type == "agent":
            # SSH Agent 认证
            connect_kwargs["allow_agent"] = True
            connect_kwargs["look_for_keys"] = True
        
        client.connect(**connect_kwargs)
        cls._connections[server_name] = client
        return client
    
    @classmethod
    def execute(cls, server_name: str, command: str) -> str:
        """执行远程命令"""
        client = cls.get_connection(server_name)
        stdin, stdout, stderr = client.exec_command(command, timeout=30)
        
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        if error and not output:
            return f"错误: {error}"
        return output
    
    @classmethod
    def close_all(cls):
        """关闭所有连接"""
        for client in cls._connections.values():
            try:
                client.close()
            except:
                pass
        cls._connections.clear()


def find_server(query: str) -> Optional[str]:
    """
    根据用户输入匹配服务器名称
    
    Args:
        query: 用户输入
    
    Returns:
        服务器名称或 None
    """
    query = query.lower()
    
    for name, config in MONITOR_SERVERS.items():
        # 匹配名字
        if query in name.lower() or name.lower() in query:
            return name
        
        # 匹配别名
        for alias in config.get("aliases", []):
            if query in alias.lower() or alias.lower() in query:
                return name
    
    return None


def get_server_list() -> str:
    """获取服务器列表描述"""
    lines = []
    for name, config in MONITOR_SERVERS.items():
        aliases = ", ".join(config.get("aliases", []))
        lines.append(f"- {name} ({config['host']}) 别名: {aliases}")
    return "\n".join(lines)
