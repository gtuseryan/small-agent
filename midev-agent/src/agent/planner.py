"""任务规划器 —— 将复杂用户意图拆解为可执行的子任务序列"""


class Planner:
    """简单的任务规划器，将用户意图拆分为步骤序列"""

    @staticmethod
    def decompose(user_query: str) -> list[dict]:
        """
        根据用户查询拆解任务。

        返回示例:
        [
            {"step": 1, "action": "analyze", "target": "文件路径", "reason": "理解现有代码"},
            {"step": 2, "action": "search", "target": "关键词", "reason": "检索相关知识"},
            ...
        ]
        """
        # 基于关键词的简单任务拆解（生产环境可替换为 LLM 驱动）
        steps = []
        query_lower = user_query.lower()

        # 代码审查类任务
        if any(kw in query_lower for kw in ["审查", "review", "检查", "review", "check"]):
            steps.append({
                "step": len(steps) + 1,
                "action": "read_file",
                "target": "{待审查文件}",
                "reason": "读取待审查的代码文件",
            })
            steps.append({
                "step": len(steps) + 1,
                "action": "analyze_code",
                "target": "{待审查文件}",
                "reason": "对代码进行静态分析，识别潜在问题",
            })
            steps.append({
                "step": len(steps) + 1,
                "action": "search_knowledge",
                "target": "相关技术规范和最佳实践",
                "reason": "检索团队编码规范和已知陷阱",
            })

        # 文档生成类任务
        elif any(kw in query_lower for kw in ["文档", "doc", "readme", "api"]):
            steps.append({
                "step": len(steps) + 1,
                "action": "list_directory",
                "target": "{项目目录}",
                "reason": "了解项目整体结构",
            })
            steps.append({
                "step": len(steps) + 1,
                "action": "generate_doc",
                "target": "{目标文件或目录}",
                "reason": "自动生成文档内容",
            })

        # 知识问答类任务
        elif any(kw in query_lower for kw in ["怎么", "如何", "为什么", "什么是", "how", "what", "why"]):
            steps.append({
                "step": len(steps) + 1,
                "action": "search_knowledge",
                "target": user_query,
                "reason": "从知识库检索相关答案",
            })

        # 通用任务 - 默认拆解
        if not steps:
            steps.append({
                "step": 1,
                "action": "analyze",
                "target": user_query,
                "reason": "理解用户意图，选择合适工具",
            })

        return steps

    @staticmethod
    def format_plan(steps: list[dict]) -> str:
        """格式化任务计划为可读文本"""
        lines = ["## 任务执行计划\n"]
        for s in steps:
            lines.append(f"**步骤 {s['step']}**: {s['action']}")
            lines.append(f"  - 目标: {s['target']}")
            lines.append(f"  - 原因: {s['reason']}")
            lines.append("")
        return "\n".join(lines)
