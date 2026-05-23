"""ReAct Agent 核心引擎 —— 思考(Thought) → 行动(Action) → 观察(Observation) 循环"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from ..llm import LLMClient
from ..tools.registry import ToolRegistry
from .memory import MemoryManager
from .planner import Planner

console = Console()


class ReActAgent:
    """
    ReAct (Reasoning + Acting) Agent 实现。

    核心循环:
    1. Thought (思考): 分析当前状态，决定下一步
    2. Action (行动): 调用工具或生成回复
    3. Observation (观察): 处理工具返回结果
    4. Reflection (反思): 判断任务是否完成，是否继续

    参考文献:
    - Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models", 2023
    - Anthropic MCP Protocol Specification
    """

    REACT_SYSTEM_PROMPT = """你是一个基于小米预训练基础大模型的智能研发协作Agent（MiDevAgent）。

## 核心能力
- 代码分析：理解代码逻辑、发现Bug、提出优化建议
- 文档生成：自动生成API文档、README、变更日志
- 知识检索：从研发知识库检索技术文档和历史决策

## ReAct 工作模式
你需要严格按照以下格式进行思考和行动：

Thought: [对当前状态的分析，决定下一步要做什么]
Action: [要执行的操作，可以是工具调用名称]
Action Input: [传递给工具的JSON格式参数]

每次工具调用后，你将收到 Observation 反馈。基于观察结果继续思考。

当任务完成时，输出以下格式：
Thought: 任务已完成
Final Answer: [最终的回答或报告]

## 重要规则
1. 每次只执行一个 Action
2. 遇到不确定的信息，使用工具检索，不要猜测
3. 代码建议需具体指出位置和修改方案
4. 文档生成需格式规范、内容完整
5. 如果工具执行失败，尝试其他方法或向用户说明
{available_tools}
"""

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        memory: MemoryManager = None,
        max_iterations: int = 10,
        verbose: bool = True,
    ):
        self.llm = llm_client
        self.tools = tool_registry
        self.memory = memory or MemoryManager()
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.planner = Planner()

    def run(self, user_query: str) -> str:
        """执行 Agent 主循环，返回最终答案"""
        self.memory.clear_working()

        # 第一步：任务拆解
        steps = self.planner.decompose(user_query)
        plan_text = self.planner.format_plan(steps)

        if self.verbose:
            console.print(Panel(plan_text, title="任务计划", border_style="blue"))

        # 构建系统消息
        system_msg = self._build_system_prompt()

        # 构建初始消息
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"## 用户请求\n{user_query}\n\n## 执行计划\n{plan_text}\n\n请开始执行。"},
        ]

        self.memory.add_message("user", user_query)

        # ReAct 循环
        for iteration in range(1, self.max_iterations + 1):
            if self.verbose:
                console.print(f"\n[bold yellow]═══ 第 {iteration}/{self.max_iterations} 轮 ═══[/bold yellow]")

            # 调用 LLM
            response = self.llm.chat(
                messages=messages,
                tools=self.tools.to_openai_tools(),
            )

            # 检查是否是工具调用
            if response.get("tool_calls"):
                for tc in response["tool_calls"]:
                    tool_name = tc["name"]
                    try:
                        tool_args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                    except json.JSONDecodeError:
                        tool_args = {}

                    if self.verbose:
                        console.print(f"[cyan]🔧 Action: {tool_name}[/cyan]")
                        console.print(f"[dim]   参数: {json.dumps(tool_args, ensure_ascii=False)}[/dim]")

                    # 执行工具
                    result = self.tools.call(tool_name, **tool_args)

                    if self.verbose:
                        status = "✅" if result.success else "❌"
                        preview = result.content[:300].replace("\n", " ")
                        console.print(f"[dim]   {status} {preview}...[/dim]" if len(result.content) > 300 else f"[dim]   {status} {preview}[/dim]")

                    # 将工具调用和结果加入消息历史
                    messages.append({
                        "role": "assistant",
                        "content": response.get("content") or "",
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {"name": tool_name, "arguments": json.dumps(tool_args, ensure_ascii=False)},
                            }
                        ],
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": f"成功:\n{result.content}" if result.success else f"失败: {result.error}",
                    })

                    self.memory.add_message("tool", result.content[:200], tool=tool_name)
                    self.memory.set_working(f"last_tool_{tool_name}", result.content[:300])

            else:
                # 无工具调用：Agent 给出了最终回答
                final_answer = response["content"]
                self.memory.add_message("assistant", final_answer)

                if self.verbose:
                    console.print(Panel(
                        Markdown(final_answer),
                        title="最终回答",
                        border_style="green",
                    ))

                # 记录长期记忆
                summary = self.memory.summarize_session()
                self.memory.add_insight(summary)

                return final_answer

            # 轮次结束，添加上下文提示
            if iteration < self.max_iterations:
                messages.append({
                    "role": "system",
                    "content": (
                        f"工具调用已完成（第 {iteration}/{self.max_iterations} 轮）。"
                        "请继续思考，选择下一步 Action 或给出 Final Answer。"
                    ),
                })

        # 达到最大迭代次数，强制总结
        if self.verbose:
            console.print(f"\n[bold red]已达最大迭代次数 {self.max_iterations}，正在强制总结...[/bold red]")

        messages.append({
            "role": "user",
            "content": "已达到最大执行轮数。请基于已获取的信息给出你的最终回答（Final Answer）。",
        })
        final = self.llm.chat(messages=messages)
        return final["content"]

    def chat(self, user_query: str) -> str:
        """简化的对话接口（不使用工具的单轮对话）"""
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_query},
        ]
        response = self.llm.chat(messages=messages)
        return response["content"]

    def _build_system_prompt(self) -> str:
        tools_desc = self.tools.describe_all()
        working_state = self.memory.get_working_state()

        prompt = self.REACT_SYSTEM_PROMPT.format(available_tools=tools_desc)
        if working_state:
            prompt += f"\n\n{working_state}"

        return prompt
