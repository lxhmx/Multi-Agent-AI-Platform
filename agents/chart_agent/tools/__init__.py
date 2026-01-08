"""
图表智能体工具集
"""

from agents.chart_agent.tools.chart_generator import generate_chart

ALL_TOOLS = [generate_chart]

__all__ = ["ALL_TOOLS", "generate_chart"]
