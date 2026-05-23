"""记忆管理 —— 短期上下文 + 长期向量记忆 + 工作状态维护"""

from collections import deque


class MemoryManager:
    """管理 Agent 的多层记忆系统"""

    def __init__(self, short_term_size: int = 20, working_size: int = 5):
        self._short_term: deque[dict] = deque(maxlen=short_term_size)
        self._working: dict = {}  # 当前任务的关键状态
        self._long_term: list[dict] = []  # 长期记忆（摘要列表）
        self._session_summary: str = ""

    # ---- 短期记忆 ----
    def add_message(self, role: str, content: str, **meta):
        """添加一条对话消息到短期记忆"""
        msg = {"role": role, "content": content, "meta": meta}
        self._short_term.append(msg)

    def get_messages(self) -> list[dict]:
        """获取当前对话历史（给 LLM 的 messages 格式）"""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self._short_term
        ]

    def get_last(self, n: int = 1) -> list[dict]:
        """获取最近 n 条消息"""
        return list(self._short_term)[-n:]

    # ---- 工作记忆 ----
    def set_working(self, key: str, value):
        """设置工作记忆中的键值"""
        self._working[key] = value

    def get_working(self, key: str, default=None):
        """获取工作记忆中的值"""
        return self._working.get(key, default)

    def clear_working(self):
        """清空工作记忆"""
        self._working.clear()

    def get_working_state(self) -> str:
        """获取工作记忆的文本摘要"""
        if not self._working:
            return ""
        lines = ["## 当前任务状态"]
        for k, v in self._working.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    # ---- 长期记忆 ----
    def add_insight(self, insight: str):
        """添加一条长期记忆洞察"""
        self._long_term.append({
            "insight": insight,
            "id": len(self._long_term),
        })

    def get_insights(self, limit: int = 10) -> list[str]:
        """获取最近的长期记忆"""
        return [m["insight"] for m in self._long_term[-limit:]]

    # ---- 会话摘要 ----
    def summarize_session(self) -> str:
        """生成当前会话的简要摘要"""
        if not self._short_term:
            return ""
        user_msgs = [m["content"] for m in self._short_term if m["role"] == "user"]
        tool_calls = [m for m in self._short_term if m["role"] == "tool"]

        parts = []
        if user_msgs:
            parts.append(f"用户请求: {user_msgs[-1][:200]}")
        if tool_calls:
            parts.append(f"工具调用: {len(tool_calls)} 次")
        if self._working:
            parts.append(f"工作状态: {list(self._working.keys())}")

        return " | ".join(parts)

    def clear(self):
        """清空所有记忆"""
        self._short_term.clear()
        self._working.clear()
        self._long_term.clear()
