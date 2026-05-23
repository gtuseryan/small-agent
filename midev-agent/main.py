#!/usr/bin/env python3
"""
MiDevAgent —— 基于小米预训练基础大模型的智能研发协作Agent系统

用法:
  python main.py run "帮我审查 src/tools/code_tools.py 的代码质量"
  python main.py chat "什么是 ReAct Agent 模式？"
  python main.py index ./docs          # 将文档目录加入知识库
  python main.py review "git diff 内容"  # 审查代码变更
  python main.py doc ./src              # 为源码目录生成文档
  python main.py demo                  # 运行交互式演示
"""

import os
import sys
import argparse

from dotenv import load_dotenv
load_dotenv()

from src.llm import LLMClient
from src.tools import (
    AnalyzeCodeTool, ReviewDiffTool, GenerateDocTool,
    SearchKnowledgeTool, IndexDocumentTool, ReadFileTool, ListDirectoryTool,
    ToolRegistry,
)
from src.rag import DocumentLoader, VectorStore, Retriever
from src.agent import ReActAgent, MemoryManager


def build_agent(config_path: str = "config.yaml", verbose: bool = True):
    """构建完整的 Agent 实例（含 RAG 和工具）"""
    # LLM 客户端
    llm = LLMClient(config_path)

    # RAG 模块
    import yaml
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    rag_cfg = config.get("rag", {})
    embed_cfg = config.get("embedding", {})

    # 尝试初始化嵌入客户端
    embedding_client = None
    if embed_cfg.get("api_key"):
        from openai import OpenAI
        try:
            embedding_client = OpenAI(
                api_key=os.path.expandvars(embed_cfg["api_key"]),
                base_url=os.path.expandvars(embed_cfg.get("base_url", "")),
            )
        except Exception:
            pass

    vector_store = VectorStore(
        persist_dir=rag_cfg.get("persist_directory", "./data/chroma_db"),
        collection_name=rag_cfg.get("collection_name", "midev_knowledge"),
        embedding_client=embedding_client,
        embedding_model=os.path.expandvars(embed_cfg.get("model_name", "text-embedding-3-small")),
    )
    retriever = Retriever(
        vector_store,
        chunk_size=rag_cfg.get("chunk_size", 500),
        chunk_overlap=rag_cfg.get("chunk_overlap", 50),
    )

    # 工具注册
    search_tool = SearchKnowledgeTool(retriever)
    index_tool = IndexDocumentTool(retriever)
    # 索引工具使用向量存储的 add 方法
    index_tool._indexer = retriever

    registry = ToolRegistry()
    registry.register_many([
        AnalyzeCodeTool(),
        ReviewDiffTool(),
        GenerateDocTool(),
        search_tool,
        index_tool,
        ReadFileTool(),
        ListDirectoryTool(),
    ])

    # 记忆管理
    memory = MemoryManager()

    # Agent
    agent_cfg = config.get("agent", {})
    agent = ReActAgent(
        llm_client=llm,
        tool_registry=registry,
        memory=memory,
        max_iterations=agent_cfg.get("max_iterations", 10),
        verbose=verbose,
    )

    return agent, retriever


def cmd_run(args):
    """执行 Agent 完整任务"""
    agent, _ = build_agent(verbose=args.verbose)
    result = agent.run(args.query)
    print(result)


def cmd_chat(args):
    """简单对话（无工具调用）"""
    agent, _ = build_agent(verbose=False)
    print("MiDevAgent 对话模式 (输入 /quit 退出)\n")
    while True:
        try:
            query = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break
        if query.lower() in ("/quit", "/exit"):
            print("再见！")
            break
        if not query:
            continue
        response = agent.chat(query)
        print(f"\n{response}\n")


def cmd_index(args):
    """索引文档到知识库"""
    _, retriever = build_agent(verbose=False)
    path = args.path
    if not os.path.exists(path):
        print(f"路径不存在: {path}")
        sys.exit(1)
    count = retriever.index(path)
    print(f"已完成索引: {count} 个文档块已添加到知识库")


def cmd_review(args):
    """代码审查"""
    diff_content = args.diff
    if os.path.isfile(diff_content):
        with open(diff_content, "r", encoding="utf-8") as f:
            diff_content = f.read()

    agent, _ = build_agent(verbose=args.verbose)
    query = f"请审查以下代码变更（git diff），逐行分析潜在问题、安全风险和规范违规：\n\n```diff\n{diff_content}\n```"
    result = agent.run(query)
    print(result)


def cmd_doc(args):
    """生成文档"""
    target = args.target
    agent, _ = build_agent(verbose=args.verbose)
    query = f"请为以下目标生成技术文档（API文档/模块说明）：{target}\n请先使用 list_directory 了解结构，再使用 read_file 读取关键文件，最后生成完整的文档。"
    result = agent.run(query)
    print(result)


def cmd_demo(args):
    """交互式演示"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    console.print(Panel.fit(
        "[bold cyan]MiDevAgent[/bold cyan] —— 基于小米预训练基础大模型的智能研发协作Agent",
        border_style="cyan",
    ))

    table = Table(title="可用命令")
    table.add_column("命令", style="cyan")
    table.add_column("说明")
    table.add_row("审查代码文件", "帮我审查 <文件路径> 的代码质量")
    table.add_row("审查 diff 变更", "帮我审查这段代码变更是否有问题: <diff内容>")
    table.add_row("生成文档", "为 <目录路径> 生成 API 文档")
    table.add_row("技术问答", "如何在项目中实现 <某个功能>？")
    table.add_row("知识检索", "搜索关于 <关键词> 的技术文档")
    table.add_row("/quit", "退出演示")
    console.print(table)
    console.print()

    agent, _ = build_agent(verbose=True)

    while True:
        try:
            query = input("[cyan]MiDevAgent > [/cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n再见！")
            break
        if query.lower() in ("/quit", "/exit"):
            console.print("再见！")
            break
        if not query:
            continue
        try:
            result = agent.run(query)
            console.print(f"\n{result}\n")
        except Exception as e:
            console.print(f"[red]执行出错: {e}[/red]")


def main():
    parser = argparse.ArgumentParser(
        description="MiDevAgent —— 基于小米预训练基础大模型的智能研发协作Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py run "帮我审查 src/tools/code_tools.py 的代码质量"
  python main.py chat
  python main.py index ./docs
  python main.py review "git diff 输出内容或文件路径"
  python main.py doc ./src
  python main.py demo
        """,
    )
    parser.add_argument("--config", default="config.yaml", help="配置文件路径 (默认: config.yaml)")

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run - 执行Agent任务
    p_run = subparsers.add_parser("run", help="执行完整的 Agent 任务")
    p_run.add_argument("query", help="任务描述（自然语言）")
    p_run.add_argument("--verbose", action="store_true", default=True, help="显示详细执行过程")
    p_run.add_argument("--quiet", action="store_true", help="安静模式")

    # chat - 简单对话
    p_chat = subparsers.add_parser("chat", help="进入对话模式")

    # index - 索引文档
    p_index = subparsers.add_parser("index", help="索引文档到知识库")
    p_index.add_argument("path", help="要索引的文件或目录路径")

    # review - 代码审查
    p_review = subparsers.add_parser("review", help="审查代码变更")
    p_review.add_argument("diff", help="git diff 内容或 diff 文件路径")
    p_review.add_argument("--verbose", action="store_true", default=True)

    # doc - 生成文档
    p_doc = subparsers.add_parser("doc", help="生成技术文档")
    p_doc.add_argument("target", help="目标文件或目录")
    p_doc.add_argument("--verbose", action="store_true", default=True)

    # demo - 交互式演示
    subparsers.add_parser("demo", help="进入交互式演示模式")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # 处理 quiet 模式
    if hasattr(args, "quiet") and args.quiet:
        args.verbose = False

    commands = {
        "run": cmd_run,
        "chat": cmd_chat,
        "index": cmd_index,
        "review": cmd_review,
        "doc": cmd_doc,
        "demo": cmd_demo,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
