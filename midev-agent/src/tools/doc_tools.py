"""知识检索和文件操作工具"""

import os
import glob
from .base import BaseTool, ToolResult


class SearchKnowledgeTool(BaseTool):
    """从研发知识库中检索相关技术文档 —— 需要配合 RAG 模块使用"""

    def __init__(self, rag_retriever=None):
        super().__init__()
        self._retriever = rag_retriever

    def set_retriever(self, retriever):
        self._retriever = retriever

    @property
    def name(self) -> str:
        return "search_knowledge"

    @property
    def description(self) -> str:
        return (
            "从研发知识库中检索与查询相关的技术文档、设计决策和历史讨论。"
            "适用于查找技术方案、架构说明、踩坑记录等知识。"
            "返回相关文档片段及其来源。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "查询关键词或自然语言问题",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量，默认 5",
                },
            },
            "required": ["query"],
        }

    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        top_k = kwargs.get("top_k", 5)
        validation = self._validate_params(kwargs, ["query"])
        if validation:
            return ToolResult.fail(validation)

        if not self._retriever:
            return ToolResult.ok(
                f'[模拟检索] 查询: "{query}"\n\n知识库尚未初始化。请先将文档添加到知识库中（使用 index_document 工具），再进行检索。\n\n提示: 运行 `midev-agent index <文件或目录>` 来构建知识库索引。',
                simulated=True,
            )

        try:
            results = self._retriever.query(query, top_k=top_k)
            if not results:
                return ToolResult.ok(f'未找到与 "{query}" 相关的知识文档。', count=0)

            lines = [f'## 检索结果: "{query}"\n']
            for i, r in enumerate(results, 1):
                lines.append(f"### 结果 {i} (相关度: {r.get('score', 'N/A')})")
                lines.append(f"来源: {r.get('source', 'unknown')}")
                lines.append(f"{r.get('content', '')[:500]}\n")

            return ToolResult.ok("\n".join(lines), count=len(results))
        except Exception as e:
            return ToolResult.fail(f"检索失败: {str(e)}")


class IndexDocumentTool(BaseTool):
    """将文档添加到知识库索引中"""

    def __init__(self, rag_indexer=None):
        super().__init__()
        self._indexer = rag_indexer

    def set_indexer(self, indexer):
        self._indexer = indexer

    @property
    def name(self) -> str:
        return "index_document"

    @property
    def description(self) -> str:
        return (
            "将文档或代码文件添加到知识库索引中，使其可被检索。"
            "支持 .md、.txt、.py、.java、.go、.js、.ts 等格式。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要索引的文件或目录路径",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        validation = self._validate_params(kwargs, ["path"])
        if validation:
            return ToolResult.fail(validation)

        if not os.path.exists(path):
            return ToolResult.fail(f"路径不存在: {path}")

        file_count = 0
        if os.path.isfile(path):
            file_count = 1
        elif os.path.isdir(path):
            exts = {".md", ".txt", ".py", ".java", ".go", ".js", ".ts", ".yaml", ".yml"}
            for root, _, files in os.walk(path):
                for f in files:
                    if os.path.splitext(f)[1] in exts and not f.startswith("."):
                        file_count += 1

        if self._indexer:
            try:
                self._indexer.index(path)
                return ToolResult.ok(
                    f"已成功将 {file_count} 个文件添加到知识库索引中。",
                    file_count=file_count,
                )
            except Exception as e:
                return ToolResult.fail(f"索引失败: {str(e)}")
        else:
            return ToolResult.ok(
                f"[模拟索引] 发现 {file_count} 个可索引文件。\n"
                "知识库索引模块尚未初始化，文件未被实际索引。\n"
                "提示: 运行 `midev-agent index <文件或目录>` 来实际构建索引。",
                file_count=file_count,
                simulated=True,
            )


class ReadFileTool(BaseTool):
    """读取本地文件内容"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "读取指定文件的全部内容并返回。适用于查看代码、配置或文档文件。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（绝对或相对路径）",
                },
                "lines": {
                    "type": "integer",
                    "description": "最多读取行数（可选，默认读取全部）",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        max_lines = kwargs.get("lines")
        validation = self._validate_params(kwargs, ["path"])
        if validation:
            return ToolResult.fail(validation)

        if not os.path.isfile(path):
            return ToolResult.fail(f"文件不存在: {path}")

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                if max_lines:
                    content = "".join(f.readline() for _ in range(max_lines))
                else:
                    content = f.read()

            if len(content) > 8000:
                content = content[:8000] + "\n\n... [内容已截断，文件过大]"

            return ToolResult.ok(
                f"## {path}\n\n```\n{content}\n```",
                path=path,
                size=len(content),
            )
        except Exception as e:
            return ToolResult.fail(f"读取文件失败: {str(e)}")


class ListDirectoryTool(BaseTool):
    """列出目录结构"""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "列出指定目录下的文件和子目录。用于了解项目结构。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "目录路径，默认为当前工作目录",
                },
                "pattern": {
                    "type": "string",
                    "description": "文件名匹配模式，如 *.py（可选）",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")
        pattern = kwargs.get("pattern", "*")

        if not os.path.isdir(path):
            return ToolResult.fail(f"目录不存在: {path}")

        try:
            search_path = os.path.join(path, pattern)
            items = sorted(glob.glob(search_path, recursive=False))

            lines = [f"## 目录: {path}\n"]
            dirs = [i for i in items if os.path.isdir(i)]
            files = [i for i in items if os.path.isfile(i)]

            if dirs:
                lines.append("### 子目录")
                for d in dirs[:30]:
                    lines.append(f"- 📁 {os.path.basename(d)}/")
            if files:
                lines.append(f"\n### 文件 ({len(files)} 个)")
                for f in files[:50]:
                    size = os.path.getsize(f)
                    lines.append(f"- 📄 {os.path.basename(f)} ({self._fmt_size(size)})")

            return ToolResult.ok(
                "\n".join(lines),
                dir_count=len(dirs),
                file_count=len(files),
            )
        except Exception as e:
            return ToolResult.fail(f"列出目录失败: {str(e)}")

    @staticmethod
    def _fmt_size(size: int) -> str:
        for unit in ["B", "KB", "MB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}GB"
