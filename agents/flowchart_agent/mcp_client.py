"""
MCP Client for Draw.io integration

通过 MCP 协议与 Draw.io MCP Server 通信，实现流程图生成。
Draw.io MCP Server 通过 WebSocket 连接浏览器中的 Draw.io 扩展。

工作流程：
1. Python 后端启动 drawio-mcp-server 进程
2. drawio-mcp-server 监听 WebSocket 端口 3333
3. 用户在浏览器中打开 Draw.io 并安装扩展
4. 扩展连接到 MCP 服务器
5. Python 通过 stdio 与 MCP 服务器通信，控制 Draw.io

Requirements: 5.4
"""

import asyncio
import json
import logging
import subprocess
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

from config import MCP_SERVERS

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPResponse:
    """MCP 响应"""
    success: bool
    data: Any = None
    error: Optional[str] = None


class MCPClient:
    """
    MCP 客户端
    
    通过 stdio 与 MCP 服务器进程通信，使用 JSON-RPC 2.0 协议。
    """
    
    def __init__(self, server_name: str = "drawio"):
        """
        初始化 MCP 客户端
        
        Args:
            server_name: MCP 服务器名称，对应 config.py 中的配置
        """
        self.server_name = server_name
        self.config = MCP_SERVERS.get("mcpServers", {}).get(server_name, {})
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._tools: List[MCPTool] = []
        self._initialized = False
    
    @property
    def command(self) -> str:
        """获取启动命令"""
        return self.config.get("command", "")
    
    @property
    def args(self) -> List[str]:
        """获取命令参数"""
        return self.config.get("args", [])
    
    @property
    def timeout(self) -> int:
        """获取超时时间"""
        return self.config.get("timeout", 60)
    
    def _next_request_id(self) -> int:
        """生成下一个请求 ID"""
        self._request_id += 1
        return self._request_id
    
    async def start(self) -> bool:
        """
        启动 MCP 服务器进程
        
        Returns:
            bool: 是否启动成功
        """
        if not self.command:
            logger.error(f"[MCPClient] 未找到服务器 '{self.server_name}' 的配置")
            return False
        
        try:
            # Windows 使用 shell=True 时，cmd 应该是字符串
            cmd_parts = [self.command] + self.args
            cmd_str = " ".join(cmd_parts)
            
            print(f"[MCPClient] 启动 MCP 服务器: {cmd_str}")
            logger.info(f"[MCPClient] 启动 MCP 服务器: {cmd_str}")
            
            self.process = subprocess.Popen(
                cmd_str,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                encoding='utf-8',  # 强制使用 UTF-8 编码
                errors='replace',  # 遇到无法解码的字符时替换
                bufsize=0,  # 无缓冲，立即读写
                shell=True  # Windows 需要 shell=True 来找到全局命令
            )
            
            # 等待进程启动并读取初始输出
            await asyncio.sleep(1.0)
            
            if self.process.poll() is not None:
                output = self.process.stdout.read() if self.process.stdout else ""
                print(f"[MCPClient] 服务器启动失败，输出: {output}")
                logger.error(f"[MCPClient] 服务器启动失败: {output}")
                return False
            
            print("[MCPClient] MCP 服务器进程已启动")
            logger.info("[MCPClient] MCP 服务器已启动")
            return True
            
        except FileNotFoundError:
            logger.error(f"[MCPClient] 找不到命令: {self.command}")
            return False
        except Exception as e:
            logger.error(f"[MCPClient] 启动服务器异常: {e}")
            return False
    
    async def stop(self) -> None:
        """停止 MCP 服务器进程"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            finally:
                self.process = None
                self._initialized = False
            logger.info("[MCPClient] MCP 服务器已停止")
    
    async def _send_request(self, method: str, params: Optional[Dict] = None) -> MCPResponse:
        """
        发送 JSON-RPC 请求
        
        Args:
            method: RPC 方法名
            params: 请求参数
        
        Returns:
            MCPResponse: 响应结果
        """
        if not self.process or self.process.poll() is not None:
            print(f"[MCPClient] 错误: MCP 服务器未运行")
            return MCPResponse(success=False, error="MCP 服务器未运行")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": method,
        }
        if params:
            request["params"] = params
        
        # 获取工具名称用于日志
        tool_name = params.get("name", method) if params else method
        
        try:
            # 发送请求
            request_line = json.dumps(request) + "\n"
            print(f"[MCPClient] 发送请求: {request_line.strip()[:200]}...")
            self.process.stdin.write(request_line)
            self.process.stdin.flush()
            print(f"[MCPClient] 请求已发送，等待响应...")
            
            # 读取响应（带超时）- 尝试逐字符读取直到遇到换行
            loop = asyncio.get_event_loop()
            print(f"[MCPClient] 开始读取响应 (超时: {self.timeout}秒)...")
            
            # 使用 readline 读取一行
            def read_line():
                """读取一行，处理可能的多行输出"""
                line = self.process.stdout.readline()
                # 跳过空行和非 JSON 行
                while line and not line.strip().startswith('{'):
                    print(f"[MCPClient] 跳过非 JSON 行: {line.strip()[:100]}")
                    line = self.process.stdout.readline()
                return line
            
            response_line = await asyncio.wait_for(
                loop.run_in_executor(None, read_line),
                timeout=self.timeout
            )
            
            print(f"[MCPClient] 收到响应: {response_line[:500] if response_line else '(空)'}")
            
            if not response_line:
                # 检查 stderr
                stderr_output = ""
                try:
                    # 非阻塞读取 stderr
                    import threading
                    def read_stderr():
                        nonlocal stderr_output
                        stderr_output = self.process.stderr.read(1000) if self.process.stderr else ""
                    t = threading.Thread(target=read_stderr)
                    t.start()
                    t.join(timeout=0.5)
                except:
                    pass
                print(f"[MCPClient] stderr: {stderr_output}")
                return MCPResponse(success=False, error=f"服务器无响应, stderr: {stderr_output}")
            
            response = json.loads(response_line)
            print(f"[MCPClient] 解析响应成功: {str(response)[:200]}...")
            
            if "error" in response:
                error = response["error"]
                error_msg = error.get("message", str(error))
                return MCPResponse(success=False, error=error_msg)
            
            return MCPResponse(success=True, data=response.get("result"))
            
        except asyncio.TimeoutError:
            print(f"[MCPClient] 请求超时: {tool_name} (超时时间: {self.timeout}秒)")
            # 检查进程是否还活着
            poll_result = self.process.poll()
            print(f"[MCPClient] 进程状态: {'运行中' if poll_result is None else f'已退出({poll_result})'}")
            return MCPResponse(success=False, error=f"请求超时: {tool_name}")
        except json.JSONDecodeError as e:
            print(f"[MCPClient] JSON 解析错误: {e}, 原始数据: {response_line[:200] if response_line else '(空)'}")
            return MCPResponse(success=False, error=f"JSON 解析错误: {e}")
        except Exception as e:
            print(f"[MCPClient] 请求异常: {type(e).__name__}: {e}")
            return MCPResponse(success=False, error=f"请求异常: {e}")

    async def initialize(self) -> MCPResponse:
        """
        初始化 MCP 连接
        
        发送 initialize 请求，建立与服务器的协议握手。
        
        Returns:
            MCPResponse: 包含服务器能力信息
        """
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {}
            },
            "clientInfo": {
                "name": "flowchart-agent",
                "version": "1.0.0"
            }
        }
        
        response = await self._send_request("initialize", params)
        
        if response.success:
            self._initialized = True
            # 发送 initialized 通知
            await self._send_notification("notifications/initialized")
            logger.info(f"[MCPClient] 初始化成功: {response.data}")
        
        return response
    
    async def _send_notification(self, method: str, params: Optional[Dict] = None) -> None:
        """
        发送 JSON-RPC 通知（无需响应）
        
        Args:
            method: 通知方法名
            params: 通知参数
        """
        if not self.process or self.process.poll() is not None:
            return
        
        notification = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params:
            notification["params"] = params
        
        try:
            notification_line = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_line)
            self.process.stdin.flush()
        except Exception as e:
            logger.warning(f"[MCPClient] 发送通知失败: {e}")
    
    async def list_tools(self) -> MCPResponse:
        """
        获取 MCP 服务器提供的所有工具列表
        
        Returns:
            MCPResponse: 包含工具列表
            - data.tools: List[Dict] 工具定义列表
        """
        response = await self._send_request("tools/list")
        
        if response.success and response.data:
            tools_data = response.data.get("tools", [])
            self._tools = [
                MCPTool(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {})
                )
                for t in tools_data
            ]
            logger.info(f"[MCPClient] 获取到 {len(self._tools)} 个工具")
        
        return response
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict] = None) -> MCPResponse:
        """
        调用 MCP 工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            MCPResponse: 工具执行结果
        """
        params = {
            "name": tool_name,
            "arguments": arguments or {}
        }
        
        print(f"[MCPClient] 开始调用工具: {tool_name}")
        print(f"[MCPClient] 参数: {json.dumps(arguments or {}, ensure_ascii=False)}")
        
        response = await self._send_request("tools/call", params)
        
        if response.success:
            print(f"[MCPClient] 工具 {tool_name} 调用成功")
            logger.info(f"[MCPClient] 工具调用成功: {tool_name}")
        else:
            print(f"[MCPClient] 工具 {tool_name} 调用失败: {response.error}")
            logger.error(f"[MCPClient] 工具调用失败: {tool_name} - {response.error}")
        
        return response
    
    def call_tool_sync(self, tool_name: str, arguments: Optional[Dict] = None) -> MCPResponse:
        """
        同步调用 MCP 工具（用于 LangChain 工具函数）
        
        直接使用 subprocess 的 stdin/stdout 进行同步通信，
        不依赖 asyncio 事件循环。
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            MCPResponse: 工具执行结果
        """
        if not self.process or self.process.poll() is not None:
            print(f"[MCPClient] 错误: MCP 服务器未运行")
            return MCPResponse(success=False, error="MCP 服务器未运行")
        
        params = {
            "name": tool_name,
            "arguments": arguments or {}
        }
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/call",
            "params": params
        }
        
        print(f"[MCPClient] 同步调用工具: {tool_name}")
        print(f"[MCPClient] 参数: {json.dumps(arguments or {}, ensure_ascii=False)}")
        
        try:
            # 发送请求
            request_line = json.dumps(request) + "\n"
            self.process.stdin.write(request_line)
            self.process.stdin.flush()
            
            # 同步读取响应
            import threading
            response_line = None
            read_error = None
            
            def read_response():
                nonlocal response_line, read_error
                try:
                    line = self.process.stdout.readline()
                    # 跳过非 JSON 行
                    while line and not line.strip().startswith('{'):
                        print(f"[MCPClient] 跳过非 JSON 行: {line.strip()[:100]}")
                        line = self.process.stdout.readline()
                    response_line = line
                except Exception as e:
                    read_error = str(e)
            
            # 使用线程读取，带超时
            reader_thread = threading.Thread(target=read_response)
            reader_thread.start()
            reader_thread.join(timeout=self.timeout)
            
            if reader_thread.is_alive():
                print(f"[MCPClient] 同步调用超时: {tool_name}")
                return MCPResponse(success=False, error=f"请求超时: {tool_name}")
            
            if read_error:
                return MCPResponse(success=False, error=f"读取响应失败: {read_error}")
            
            if not response_line:
                return MCPResponse(success=False, error="服务器无响应")
            
            response = json.loads(response_line)
            
            if "error" in response:
                error = response["error"]
                error_msg = error.get("message", str(error))
                print(f"[MCPClient] 工具 {tool_name} 调用失败: {error_msg}")
                return MCPResponse(success=False, error=error_msg)
            
            print(f"[MCPClient] 工具 {tool_name} 同步调用成功")
            return MCPResponse(success=True, data=response.get("result"))
            
        except json.JSONDecodeError as e:
            print(f"[MCPClient] JSON 解析错误: {e}")
            return MCPResponse(success=False, error=f"JSON 解析错误: {e}")
        except Exception as e:
            print(f"[MCPClient] 同步调用异常: {type(e).__name__}: {e}")
            return MCPResponse(success=False, error=f"调用异常: {e}")
    
    @property
    def tools(self) -> List[MCPTool]:
        """获取已缓存的工具列表"""
        return self._tools
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """
        根据名称获取工具定义
        
        Args:
            name: 工具名称
        
        Returns:
            MCPTool: 工具定义，未找到返回 None
        """
        for tool in self._tools:
            if tool.name == name:
                return tool
        return None
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        await self.initialize()
        await self.list_tools()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()


# 全局单例
_mcp_client: Optional[MCPClient] = None


async def get_mcp_client() -> MCPClient:
    """
    获取 MCP 客户端单例
    
    Returns:
        MCPClient: MCP 客户端实例
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


def get_mcp_client_sync() -> Optional[MCPClient]:
    """
    同步获取 MCP 客户端单例
    
    注意：只有在 app.py 启动时已初始化客户端后才能使用
    
    Returns:
        MCPClient: MCP 客户端实例，如果未初始化则返回 None
    """
    return _mcp_client


async def discover_mcp_tools() -> List[Dict[str, Any]]:
    """
    发现 MCP 服务器提供的所有工具
    
    这是一个便捷函数，用于快速获取可用工具列表。
    
    Returns:
        List[Dict]: 工具信息列表，每个工具包含:
            - name: 工具名称
            - description: 工具描述
            - input_schema: 输入参数 schema
    
    Example:
        >>> tools = await discover_mcp_tools()
        >>> for tool in tools:
        ...     print(f"{tool['name']}: {tool['description']}")
    """
    client = MCPClient()
    tools_info = []
    
    try:
        if await client.start():
            response = await client.initialize()
            if response.success:
                response = await client.list_tools()
                if response.success:
                    tools_info = [
                        {
                            "name": t.name,
                            "description": t.description,
                            "input_schema": t.input_schema
                        }
                        for t in client.tools
                    ]
    finally:
        await client.stop()
    
    return tools_info


# 测试代码
if __name__ == "__main__":
    async def main():
        print("=== MCP 工具发现 ===\n")
        
        tools = await discover_mcp_tools()
        
        if not tools:
            print("未发现任何工具，请确保:")
            print("1. 已安装 drawio-mcp-server: npm install -g drawio-mcp-server")
            print("2. config.py 中的 MCP_SERVERS 配置正确")
            return
        
        print(f"发现 {len(tools)} 个工具:\n")
        for tool in tools:
            print(f"工具名称: {tool['name']}")
            print(f"描述: {tool['description']}")
            print(f"参数 Schema: {json.dumps(tool['input_schema'], indent=2, ensure_ascii=False)}")
            print("-" * 50)
    
    asyncio.run(main())
