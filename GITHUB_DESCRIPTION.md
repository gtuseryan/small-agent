# MiDevAgent

基于小米预训练基础大模型的智能研发协作Agent系统 —— 单人可部署、可扩展的AI研发助手。

## 项目简介

MiDevAgent 是一个采用 ReAct（推理-行动）范式的轻量级智能Agent系统，专为研发场景设计。它使用大语言模型作为核心推理引擎，通过工具调用和RAG检索增强生成技术，帮助开发者完成代码审查、技术文档生成、研发知识库问答等任务。项目参考了MCP（Model Context Protocol）协议设计统一的工具接口，支持扩展自定义工具。整个系统由单人构建，适合作为企业内部AI研发效能工具的起点。

## 核心功能

- **智能代码审查**：自动分析代码逻辑，识别潜在Bug、安全漏洞和代码规范问题，生成结构化审查报告
- **技术文档生成**：根据源代码自动生成API文档、模块说明、README和变更日志
- **研发知识库问答**：基于RAG技术构建私有知识库，支持自然语言查询历史技术决策、架构方案和踩坑记录
- **多工具编排**：通过统一的工具注册中心，Agent可以自主选择和调用合适的工具完成复杂任务

## 技术架构

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| Agent引擎 | ReAct范式 | Thought → Action → Observation 推理循环 |
| 任务规划 | Planner模块 | 自动拆解复杂意图为可执行的子任务序列 |
| 记忆管理 | 三层记忆系统 | 短期对话上下文 + 工作状态记忆 + 长期洞察摘要 |
| 工具系统 | MCP兼容设计 | 统一BaseTool抽象，7个内置工具，支持自定义扩展 |
| RAG管道 | ChromaDB + 智能分块 | 多格式文档加载 → 向量化索引 → 混合检索 → 重排序 |
| LLM接入 | OpenAI兼容格式 | 可接入小米大模型、OpenAI或其他兼容API |
| 前端交互 | CLI（rich美化） | 6个子命令：run / chat / index / review / doc / demo |

## 项目结构

```
midev-agent/
├── main.py                 # CLI入口
├── config.yaml             # 核心配置
├── requirements.txt        # Python依赖
├── .env.example            # 环境变量模板
├── examples/demo.py        # 快速演示（无API也能运行）
└── src/
    ├── agent/              # ReAct引擎、规划器、记忆管理
    ├── llm/                # LLM统一调用客户端
    ├── tools/              # 工具基类、代码工具、文档工具、注册中心
    └── rag/                # 文档加载器、向量存储、检索器
```

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env   # 编辑填入API密钥
python main.py demo    # 交互式演示
python main.py run "审查代码"  # 执行Agent任务
```

## 设计参考

本项目设计参考了2026年4-5月AI Agent领域的最新进展：Frona自托管Agent平台、Late CLI低资源Agent架构、Anthropic MCP工具协议标准、LangChain ReAct推理范式以及AgentOS认知记忆机制。

## 技术栈

Python 3.10+ / OpenAI SDK / ChromaDB / Rich / PyYAML

## 许可证

MIT License
