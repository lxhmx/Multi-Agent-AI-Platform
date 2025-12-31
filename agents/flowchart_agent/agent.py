"""
流程图智能体 V2

使用 LLM 生成 mxGraphModel XML，然后调用 export 服务转换为图片。
不再依赖 MCP Server 和浏览器扩展。
"""

import re
import base64
import logging
import uuid
from typing import AsyncGenerator, Optional

from agents.base import BaseAgent
from agents.flowchart_agent.prompts import SYSTEM_PROMPT, ROUTING_KEYWORDS
from agents.flowchart_agent.exporter import get_exporter, ExportError
from core.llm import get_llm

logger = logging.getLogger(__name__)


class FlowchartAgent(BaseAgent):
    """
    流程图智能体 V2
    
    工作流程：
    1. 接收用户的自然语言描述
    2. 调用 LLM 生成 mxGraphModel XML
    3. 调用 export 服务将 XML 转换为图片
    4. 通过 SSE 返回图片给前端
    """
    
    name = "flowchart"
    description = "流程图智能体，可以根据自然语言描述生成流程图"
    
    def __init__(self):
        self._llm = None
    
    def _get_llm(self):
        """获取 LLM 实例（懒加载）"""
        if self._llm is None:
            self._llm = get_llm(streaming=False)
        return self._llm
    
    def get_tools(self):
        """返回工具列表（当前实现不使用工具）"""
        return []
    
    def get_system_prompt(self) -> str:
        """返回系统提示词"""
        return SYSTEM_PROMPT
    
    def run(self, question: str, session_id: Optional[str] = None) -> str:
        """同步执行（不推荐，请使用 run_stream）"""
        import asyncio
        result = []
        async def collect():
            async for chunk in self.run_stream(question, session_id):
                result.append(chunk)
        asyncio.run(collect())
        return "".join(result)
    
    async def run_stream(
        self,
        question: str,
        session_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式执行智能体
        
        Yields:
            str: 文本片段或特殊标记
            - 普通文本: 直接显示
            - [IMAGE:base64data]: 图片数据
            - [IMAGE_META:json]: 图片元信息
        """
        try:
            # Step 1: 告知用户正在生成
            yield "正在为您生成流程图，请稍候...\n\n"
            
            # Step 2: 调用 LLM 生成 XML
            logger.info(f"[FlowchartAgent] 开始生成 XML: {question[:50]}...")
            xml_content = await self._generate_xml(question)
            
            if not xml_content:
                yield "抱歉，无法生成流程图。请尝试更详细地描述您需要的流程。"
                return
            
            logger.info(f"[FlowchartAgent] XML 生成成功，长度: {len(xml_content)}")
            
            # Step 3: 调用 export 服务生成图片
            yield "XML 结构已生成，正在渲染图片...\n\n"
            
            try:
                exporter = get_exporter()
                image_bytes = await exporter.export_to_image(
                    xml=xml_content,
                    format="png",
                    scale=1.5
                )
                
                # Step 4: 编码图片并返回
                image_base64 = base64.b64encode(image_bytes).decode('ascii')
                diagram_id = str(uuid.uuid4())[:8]
                
                # 提取标题（从问题中）
                title = self._extract_title(question)
                
                # 发送图片数据（使用特殊标记）
                yield f"[IMAGE:{image_base64}]"
                
                # 发送元信息
                import json
                meta = {
                    "diagram_id": diagram_id,
                    "title": title,
                    "format": "png",
                    "xml": xml_content
                }
                yield f"[IMAGE_META:{json.dumps(meta, ensure_ascii=False)}]"
                
                yield f"\n\n✅ 流程图已生成完成！您可以下载图片或 .drawio 文件进行编辑。"
                
            except ExportError as e:
                logger.error(f"[FlowchartAgent] 导出失败: {e}")
                yield f"\n\n⚠️ 图片渲染失败: {e}\n\n"
                yield "以下是生成的 XML 结构，您可以复制到 draw.io 中打开：\n\n"
                yield f"```xml\n{xml_content}\n```"
                
        except Exception as e:
            logger.error(f"[FlowchartAgent] 异常: {e}", exc_info=True)
            yield f"抱歉，生成流程图时出现错误: {e}"
    
    async def _generate_xml(self, question: str) -> Optional[str]:
        """
        调用 LLM 生成 mxGraphModel XML
        
        Returns:
            str: XML 内容，失败返回 None
        """
        llm = self._get_llm()
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ]
        
        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # 提取 XML（可能被包裹在 markdown 代码块中）
            xml_content = self._extract_xml(content)
            
            if xml_content and self._validate_xml(xml_content):
                return xml_content
            
            logger.warning(f"[FlowchartAgent] XML 验证失败，原始内容: {content[:500]}")
            return None
            
        except Exception as e:
            logger.error(f"[FlowchartAgent] LLM 调用失败: {e}")
            return None
    
    def _extract_xml(self, content: str) -> Optional[str]:
        """从 LLM 响应中提取 XML"""
        # 尝试从 markdown 代码块中提取
        code_block_pattern = r'```(?:xml)?\s*([\s\S]*?)```'
        matches = re.findall(code_block_pattern, content)
        
        for match in matches:
            if '<mxGraphModel>' in match:
                return match.strip()
        
        # 直接查找 mxGraphModel 标签
        xml_pattern = r'<mxGraphModel[\s\S]*?</mxGraphModel>'
        match = re.search(xml_pattern, content)
        
        if match:
            return match.group(0)
        
        return None
    
    def _validate_xml(self, xml: str) -> bool:
        """验证 XML 基本结构"""
        required_elements = [
            '<mxGraphModel>',
            '</mxGraphModel>',
            '<root>',
            '</root>',
            '<mxCell id="0"',
            '<mxCell id="1"'
        ]
        
        for element in required_elements:
            if element not in xml:
                logger.warning(f"[FlowchartAgent] XML 缺少必要元素: {element}")
                return False
        
        return True
    
    def _extract_title(self, question: str) -> str:
        """从问题中提取图表标题"""
        # 移除常见的前缀词
        prefixes = [
            "画一个", "帮我画", "生成一个", "创建一个",
            "画", "绘制", "生成", "创建"
        ]
        
        title = question
        for prefix in prefixes:
            if title.startswith(prefix):
                title = title[len(prefix):]
                break
        
        # 清理并截断
        title = title.strip()
        if len(title) > 30:
            title = title[:30] + "..."
        
        return title or "流程图"
    
    def can_handle(self, question: str) -> float:
        """判断是否适合处理该问题"""
        question_lower = question.lower()
        matched = sum(1 for k in ROUTING_KEYWORDS if k in question_lower)
        
        if matched == 0:
            return 0.3
        
        return min(0.6 + (matched * 0.1), 1.0)
    
    def clear_memory(self, session_id: str) -> None:
        """清除会话记忆（当前实现无状态）"""
        pass
