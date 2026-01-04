"""
服务器监控工具集
"""

from agents.server_monitor_agent.tools.metrics import (
    get_server_metrics,
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage,
    get_system_load,
    get_process_list,
    check_alerts,
    list_servers
)

ALL_TOOLS = [
    get_server_metrics,
    get_cpu_usage,
    get_memory_usage,
    get_disk_usage,
    get_system_load,
    get_process_list,
    check_alerts,
    list_servers
]
