"""
告警规则引擎
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any
from agents.server_monitor_agent.config import ALERT_THRESHOLDS


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警结果"""
    server: str
    metric: str
    current_value: float
    threshold: float
    level: AlertLevel
    message: str


class AlertEngine:
    """告警规则引擎"""
    
    def __init__(self, thresholds: dict = None):
        self.thresholds = thresholds or ALERT_THRESHOLDS
    
    def check(self, server: str, metrics: dict[str, Any]) -> list[Alert]:
        """
        检查指标是否触发告警
        
        Args:
            server: 服务器名称
            metrics: 指标数据
        
        Returns:
            触发的告警列表
        """
        alerts = []
        
        for metric, value in metrics.items():
            if metric not in self.thresholds:
                continue
            
            if value is None:
                continue
            
            threshold_config = self.thresholds[metric]
            
            # 检查 critical
            if value >= threshold_config.get("critical", float('inf')):
                alerts.append(Alert(
                    server=server,
                    metric=metric,
                    current_value=value,
                    threshold=threshold_config["critical"],
                    level=AlertLevel.CRITICAL,
                    message=f"⚠️ 严重告警: {metric} = {value:.1f}%，超过阈值 {threshold_config['critical']}%"
                ))
            # 检查 warning
            elif value >= threshold_config.get("warning", float('inf')):
                alerts.append(Alert(
                    server=server,
                    metric=metric,
                    current_value=value,
                    threshold=threshold_config["warning"],
                    level=AlertLevel.WARNING,
                    message=f"⚡ 警告: {metric} = {value:.1f}%，超过阈值 {threshold_config['warning']}%"
                ))
        
        return alerts
    
    def format_alerts(self, alerts: list[Alert]) -> str:
        """格式化告警信息"""
        if not alerts:
            return "✅ 所有指标正常，无告警"
        
        lines = ["📢 发现以下告警：", ""]
        for alert in alerts:
            lines.append(f"  {alert.message}")
        
        return "\n".join(lines)
