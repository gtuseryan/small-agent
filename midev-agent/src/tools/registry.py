"""工具注册中心 —— 管理所有可用工具的注册、查找和调用"""

from typing import Type
from .base import BaseTool, ToolResult


class ToolRegistry:
    """工具注册中心，管理所有工具的生命周期"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册一个工具实例"""
        self._tools[tool.name] = tool

    def register_many(self, tools: list[BaseTool]) -> None:
        """批量注册工具"""
        for t in tools:
            self.register(t)

    def get(self, name: str) -> BaseTool | None:
        """按名称获取工具"""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """列出所有已注册的工具名称"""
        return list(self._tools.keys())

    def call(self, name: str, **kwargs) -> ToolResult:
        """调用指定工具并返回结果"""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult.fail(f"未知工具: {name}。可用工具: {', '.join(self.list_tools())}")
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult.fail(f"工具 {name} 执行异常: {str(e)}")

    def to_openai_tools(self) -> list[dict]:
        """将所有工具转为 OpenAI 兼容格式"""
        return [t.to_openai_tool() for t in self._tools.values()]

    def describe_all(self) -> str:
        """生成所有工具的描述文本（供 system prompt 使用）"""
        lines = ["## 可用工具\n"]
        for name, tool in self._tools.items():
            lines.append(f"- **{name}**: {tool.description}")
        return "\n".join(lines)
