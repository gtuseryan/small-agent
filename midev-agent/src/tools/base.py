"""工具系统的抽象基类 —— 参考 MCP 协议设计统一的工具接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: str
    metadata: dict = field(default_factory=dict)
    error: str = ""

    @classmethod
    def ok(cls, content: str, **metadata) -> "ToolResult":
        return cls(success=True, content=content, metadata=metadata)

    @classmethod
    def fail(cls, error: str) -> "ToolResult":
        return cls(success=False, content="", error=error)


class BaseTool(ABC):
    """工具基类 —— 所有工具需继承此类并实现 execute 方法"""

    def __init__(self):
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（供 Agent 理解何时使用）"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """工具参数定义（JSON Schema 格式）"""
        ...

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具逻辑"""
        ...

    def to_openai_tool(self) -> dict:
        """转为 OpenAI 兼容的工具定义"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def _validate_params(self, kwargs: dict, required: list) -> str:
        """校验必填参数"""
        missing = [p for p in required if p not in kwargs or not kwargs[p]]
        if missing:
            return f"缺少必填参数: {', '.join(missing)}"
        return ""
