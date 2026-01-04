"""
服务器指标采集工具
"""

import re
from langchain_core.tools import tool
from agents.server_monitor_agent.ssh_manager import SSHManager, find_server, get_server_list
from agents.server_monitor_agent.alert_engine import AlertEngine
from agents.server_monitor_agent.config import MONITOR_SERVERS


@tool
def list_servers() -> str:
    """列出所有可监控的服务器"""
    return f"可监控的服务器：\n{get_server_list()}"


@tool
def get_server_metrics(server_name: str) -> str:
    """
    获取服务器的综合监控指标，包括 CPU、内存、磁盘、负载
    
    Args:
        server_name: 服务器名称，如 "lxhAgent"
    """
    # 尝试匹配服务器名
    matched = find_server(server_name)
    if not matched:
        return f"未找到服务器 '{server_name}'，可用服务器：\n{get_server_list()}"
    
    try:
        results = []
        results.append(f"📊 服务器 [{matched}] 监控信息\n")
        
        # CPU
        cpu_output = SSHManager.execute(matched, "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
        cpu_percent = float(cpu_output.strip()) if cpu_output.strip() else 0
        results.append(f"🔹 CPU 使用率: {cpu_percent:.1f}%")
        
        # 内存
        mem_output = SSHManager.execute(matched, "free -m | grep Mem")
        mem_parts = mem_output.split()
        if len(mem_parts) >= 3:
            total = int(mem_parts[1])
            used = int(mem_parts[2])
            mem_percent = (used / total) * 100 if total > 0 else 0
            results.append(f"🔹 内存使用: {used}MB / {total}MB ({mem_percent:.1f}%)")
        
        # 磁盘
        disk_output = SSHManager.execute(matched, "df -h / | tail -1")
        disk_parts = disk_output.split()
        if len(disk_parts) >= 5:
            results.append(f"🔹 磁盘使用: {disk_parts[2]} / {disk_parts[1]} ({disk_parts[4]})")
        
        # 负载
        load_output = SSHManager.execute(matched, "uptime | awk -F'load average:' '{print $2}'")
        results.append(f"🔹 系统负载: {load_output.strip()}")
        
        # 检查告警
        metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": mem_percent if 'mem_percent' in dir() else 0,
        }
        engine = AlertEngine()
        alerts = engine.check(matched, metrics)
        if alerts:
            results.append("\n" + engine.format_alerts(alerts))
        else:
            results.append("\n✅ 所有指标正常")
        
        return "\n".join(results)
        
    except Exception as e:
        return f"获取服务器信息失败: {str(e)}"


@tool
def get_cpu_usage(server_name: str) -> str:
    """
    获取服务器 CPU 使用率详情
    
    Args:
        server_name: 服务器名称
    """
    matched = find_server(server_name)
    if not matched:
        return f"未找到服务器 '{server_name}'"
    
    try:
        output = SSHManager.execute(matched, "top -bn1 | head -5")
        return f"📊 [{matched}] CPU 信息:\n{output}"
    except Exception as e:
        return f"获取 CPU 信息失败: {str(e)}"


@tool
def get_memory_usage(server_name: str) -> str:
    """
    获取服务器内存使用详情
    
    Args:
        server_name: 服务器名称
    """
    matched = find_server(server_name)
    if not matched:
        return f"未找到服务器 '{server_name}'"
    
    try:
        output = SSHManager.execute(matched, "free -h")
        return f"📊 [{matched}] 内存信息:\n{output}"
    except Exception as e:
        return f"获取内存信息失败: {str(e)}"


@tool
def get_disk_usage(server_name: str) -> str:
    """
    获取服务器磁盘使用详情
    
    Args:
        server_name: 服务器名称
    """
    matched = find_server(server_name)
    if not matched:
        return f"未找到服务器 '{server_name}'"
    
    try:
        output = SSHManager.execute(matched, "df -h")
        return f"📊 [{matched}] 磁盘信息:\n{output}"
    except Exception as e:
        return f"获取磁盘信息失败: {str(e)}"


@tool
def get_system_load(server_name: str) -> str:
    """
    获取服务器系统负载和运行时间
    
    Args:
        server_name: 服务器名称
    """
    matched = find_server(server_name)
    if not matched:
        return f"未找到服务器 '{server_name}'"
    
    try:
        output = SSHManager.execute(matched, "uptime")
        return f"📊 [{matched}] 系统负载:\n{output}"
    except Exception as e:
        return f"获取系统负载失败: {str(e)}"


@tool
def get_process_list(server_name: str, top_n: int = 10) -> str:
    """
    获取服务器占用资源最多的进程
    
    Args:
        server_name: 服务器名称
        top_n: 显示前 N 个进程，默认 10
    """
    matched = find_server(server_name)
    if not matched:
        return f"未找到服务器 '{server_name}'"
    
    try:
        output = SSHManager.execute(matched, f"ps aux --sort=-%mem | head -{top_n + 1}")
        return f"📊 [{matched}] 资源占用 Top {top_n} 进程:\n{output}"
    except Exception as e:
        return f"获取进程列表失败: {str(e)}"


@tool
def check_alerts(server_name: str = "all") -> str:
    """
    检查服务器告警状态
    
    Args:
        server_name: 服务器名称，"all" 表示检查所有服务器
    """
    servers_to_check = []
    
    if server_name.lower() == "all":
        servers_to_check = list(MONITOR_SERVERS.keys())
    else:
        matched = find_server(server_name)
        if not matched:
            return f"未找到服务器 '{server_name}'"
        servers_to_check = [matched]
    
    engine = AlertEngine()
    all_alerts = []
    results = ["📢 告警检查报告\n"]
    
    for server in servers_to_check:
        try:
            # 采集指标
            cpu_output = SSHManager.execute(server, "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'")
            cpu_percent = float(cpu_output.strip()) if cpu_output.strip() else 0
            
            mem_output = SSHManager.execute(server, "free | grep Mem | awk '{print $3/$2 * 100}'")
            mem_percent = float(mem_output.strip()) if mem_output.strip() else 0
            
            disk_output = SSHManager.execute(server, "df / | tail -1 | awk '{print $5}' | tr -d '%'")
            disk_percent = float(disk_output.strip()) if disk_output.strip() else 0
            
            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": mem_percent,
                "disk_percent": disk_percent
            }
            
            alerts = engine.check(server, metrics)
            all_alerts.extend(alerts)
            
            if alerts:
                results.append(f"\n🔴 [{server}]")
                for alert in alerts:
                    results.append(f"  {alert.message}")
            else:
                results.append(f"🟢 [{server}] 正常")
                
        except Exception as e:
            results.append(f"🔴 [{server}] 检查失败: {str(e)}")
    
    if not all_alerts:
        results.append("\n✅ 所有服务器运行正常，无告警")
    
    return "\n".join(results)
