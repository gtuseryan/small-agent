#!/usr/bin/env python3
"""
MiDevAgent 快速演示脚本

运行前请确保:
1. 已复制 .env.example 为 .env 并填入真实的 API 密钥
2. 已安装依赖: pip install -r requirements.txt
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.llm import LLMClient
from src.tools import (
    AnalyzeCodeTool, ReviewDiffTool, GenerateDocTool,
    SearchKnowledgeTool, IndexDocumentTool, ReadFileTool, ListDirectoryTool,
    ToolRegistry,
)
from src.rag import VectorStore, Retriever
from src.agent import ReActAgent, MemoryManager


def demo_without_api():
    """无 API 时的演示 —— 展示工具系统独立运行"""
    print("=" * 60)
    print("  MiDevAgent 工具系统演示（无需 LLM API）")
    print("=" * 60)

    # 1. 文件读取工具
    print("\n--- 1. 文件读取工具 ---")
    reader = ReadFileTool()
    current_file = __file__
    result = reader.execute(path=current_file, lines=10)
    print(f"工具: {reader.name}")
    print(f"描述: {reader.description}")
    print(f"结果: {result.content[:300]}...")

    # 2. 目录列表工具
    print("\n--- 2. 目录列表工具 ---")
    lister = ListDirectoryTool()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = lister.execute(path=project_root)
    print(f"工具: {lister.name}")
    print(f"结果:\n{result.content[:500]}")

    # 3. 代码分析工具
    print("\n--- 3. 代码分析工具 ---")
    analyzer = AnalyzeCodeTool()
    # 分析自身
    result = analyzer.execute(file_path=current_file, focus="all")
    print(f"工具: {analyzer.name}")
    print(f"结果:\n{result.content[:500]}")

    # 4. 工具注册中心
    print("\n--- 4. 工具注册中心 ---")
    registry = ToolRegistry()
    registry.register_many([
        AnalyzeCodeTool(), ReviewDiffTool(), GenerateDocTool(),
        ReadFileTool(), ListDirectoryTool(),
    ])
    print(f"已注册工具 ({len(registry.list_tools())} 个):")
    for name in registry.list_tools():
        tool = registry.get(name)
        print(f"  - {name}: {tool.description[:60]}...")

    tools_json = registry.to_openai_tools()
    print(f"\nOpenAI 工具格式: {len(tools_json)} 个工具定义已生成")

    print("\n" + "=" * 60)
    print("  演示完成！所有工具均可独立运行。")
    print("  如需体验完整的 Agent 推理，请配置 .env 中的 API 密钥。")
    print("=" * 60)


def demo_with_api():
    """有 API 时的完整演示"""
    print("=" * 60)
    print("  MiDevAgent 完整演示（需要 LLM API）")
    print("=" * 60)

    # 构建 Agent
    llm = LLMClient()
    vector_store = VectorStore()
    retriever = Retriever(vector_store)

    search_tool = SearchKnowledgeTool(retriever)
    index_tool = IndexDocumentTool(retriever)
    index_tool._indexer = retriever

    registry = ToolRegistry()
    registry.register_many([
        AnalyzeCodeTool(), ReviewDiffTool(), GenerateDocTool(),
        search_tool, index_tool, ReadFileTool(), ListDirectoryTool(),
    ])

    memory = MemoryManager()
    agent = ReActAgent(
        llm_client=llm,
        tool_registry=registry,
        memory=memory,
        max_iterations=8,
        verbose=True,
    )

    # 示例任务
    demos = [
        "请使用 list_directory 工具查看当前项目目录结构，然后告诉我项目的组织方式。",
        "请使用 read_file 读取 main.py 的前20行，然后总结这个文件的功能。",
    ]

    for i, query in enumerate(demos, 1):
        print(f"\n{'=' * 60}")
        print(f"  示例 {i}: {query}")
        print("=" * 60)
        try:
            result = agent.run(query)
            print(f"\n最终输出:\n{result}")
        except Exception as e:
            print(f"执行失败: {e}")
            break


if __name__ == "__main__":
    # 检查是否有 API 密钥
    api_key = os.getenv("LLM_API_KEY")
    if api_key and api_key != "your-api-key-here":
        demo_with_api()
    else:
        print("提示: 未检测到有效的 LLM_API_KEY，运行无 API 演示模式\n")
        demo_without_api()
