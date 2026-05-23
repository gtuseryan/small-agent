"""LLM 客户端模块 —— 兼容小米预训练基础大模型 API（OpenAI 兼容格式）"""

import os
import yaml
from openai import OpenAI


class LLMClient:
    """统一 LLM 调用客户端，支持小米大模型及任意 OpenAI 兼容 API"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        llm_cfg = self.config["llm"]

        self.client = OpenAI(
            api_key=os.path.expandvars(llm_cfg["api_key"]),
            base_url=os.path.expandvars(llm_cfg["base_url"]),
        )
        self.model_name = os.path.expandvars(llm_cfg["model_name"])
        self.default_temperature = llm_cfg.get("temperature", 0.1)
        self.default_max_tokens = llm_cfg.get("max_tokens", 4096)

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def chat(
        self,
        messages: list[dict],
        temperature: float = None,
        max_tokens: int = None,
        tools: list[dict] = None,
    ) -> dict:
        """发送对话请求，支持工具调用"""
        kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature or self.default_temperature,
            "max_tokens": max_tokens or self.default_max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    def chat_stream(self, messages: list[dict], **kwargs):
        """流式对话请求"""
        kwargs.setdefault("model", self.model_name)
        kwargs.setdefault("temperature", self.default_temperature)
        kwargs.setdefault("max_tokens", self.default_max_tokens)

        stream = self.client.chat.completions.create(
            **kwargs, messages=messages, stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _parse_response(self, response) -> dict:
        """将 OpenAI 响应解析为统一格式"""
        choice = response.choices[0]
        result = {
            "role": choice.message.role,
            "content": choice.message.content or "",
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
        }

        if choice.message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
                for tc in choice.message.tool_calls
            ]

        return result
