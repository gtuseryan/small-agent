# MiDevAgent

基于**小米预训练基础大模型**的智能研发协作Agent。单人可部署，支持ReAct推理、RAG知识检索、工具编排的AI研发助手。

---

## 项目定位

日常研发中反复出现的痛点：代码审查依赖人工逐一过目、技术文档编写耗时费力、跨项目技术决策散落在聊天记录里难以检索。MiDevAgent 用一个大模型驱动的Agent统一解决这三个问题 —— 它不是一个"聊天机器人"，而是一个能**自主调用工具完成任务**的智能体。

## 核心能力

| 能力 | 做什么 | 对应工具 |
|------|--------|----------|
| **智能代码审查** | 分析代码逻辑，识别Bug、安全漏洞、规范问题 | `analyze_code` `review_diff` |
| **文档自动生成** | 根据源码生成API文档、README、变更日志 | `generate_doc` |
| **知识库问答** | 从私有文档中检索答案，回答技术问题 | `search_knowledge` `index_document` |
| **文件系统操作** | 读取文件、浏览目录结构 | `read_file` `list_directory` |

## 技术架构

```
用户输入
    │
    ▼
┌──────────────┐    ┌─────────────────┐
│  Planner     │───▶│  ReAct 循环引擎   │
│  任务拆解     │    │  Thought → Action │
└──────────────┘    │  → Observation    │
                    └───────┬───────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌─────────┐  ┌──────────┐  ┌──────────┐
        │ Memory  │  │  Tools   │  │   RAG    │
        │ 三层记忆 │  │ 工具注册  │  │ 检索增强  │
        └─────────┘  └──────────┘  └──────────┘
                            │
                            ▼
                  ┌─────────────────┐
                  │  小米预训练大模型  │
                  │  (LLM Client)    │
                  └─────────────────┘
```

### 各层职责

**任务规划器（Planner）** —— 将用户模糊意图拆解为可执行的子任务序列。例如"帮我审查最近三天的代码变更并生成周报"会被拆为：①列出变更文件 ②逐文件审查 ③汇总问题 ④生成周报。

**ReAct 引擎** —— 核心推理循环。每轮执行：思考当前状态（Thought）→ 调用工具（Action）→ 处理结果（Observation）→ 判断是否完成。最多10轮迭代，未完成自动触发强制总结。

**记忆管理** —— 三层结构：
- *短期记忆*：当前会话的对话历史（最近20条）
- *工作记忆*：当前任务的关键状态（如已审查的文件列表）
- *长期记忆*：会话摘要归档，用于跨会话的洞察积累

**工具系统** —— 参考MCP协议，所有工具继承`BaseTool`抽象类，统一接口（name / description / parameters / execute）。新增工具只需实现子类并注册。

**RAG管道** —— 文档加载（支持 .md .txt .py .java .go .js .ts .yaml .json）→ 智能分块（段落感知，500字符/块，50字符重叠）→ 向量化（BGE嵌入）→ ChromaDB存储 → 混合检索。

## 快速开始

### 环境要求
- Python 3.10+
- 建议安装 ChromaDB：`pip install chromadb`（不装则自动降级为本地JSON存储）

### 三步启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API 密钥
cp .env.example .env
# 编辑 .env，填入：
#   LLM_API_KEY=xm-your-key
#   LLM_BASE_URL=https://api.xiaomi.com/v1
#   LLM_MODEL_NAME=xiaomi-pretrained-base

# 3. 运行
python main.py demo
```

### 命令一览

```bash
python main.py run "审查 src/ 目录的代码质量"     # 完整Agent任务
python main.py chat                                # 交互式对话
python main.py index ./docs                        # 索引文档到知识库
python main.py review "git diff 内容"               # 审查代码变更
python main.py doc ./src                           # 生成技术文档
python main.py demo                                # 交互式演示
```

### 无 API 验证

即使没有配置LLM密钥，也能运行演示脚本验证工具系统的完整性：

```bash
python examples/demo.py
```

## 项目结构

```
midev-agent/
├── main.py                     # CLI 总入口（argparse，6个子命令）
├── config.yaml                 # 可调整的配置参数
├── requirements.txt            # Python 依赖（6个包）
├── .env.example                # 环境变量模板
├── .gitignore
├── README.md
├── GITHUB_DESCRIPTION.md       # GitHub仓库描述（可复制粘贴）
├── data/                       # 知识库持久化存储目录
├── examples/
│   └── demo.py                 # 快速演示，无需API也能运行
└── src/
    ├── __init__.py
    ├── agent/
    │   ├── __init__.py
    │   ├── react_agent.py      # ReAct主循环，完整实现Thought→Action→Observation
    │   ├── planner.py          # 意图识别与任务拆解
    │   └── memory.py           # 短期/工作/长期三层记忆
    ├── llm/
    │   ├── __init__.py
    │   └── client.py           # OpenAI兼容LLM客户端，支持工具调用
    ├── tools/
    │   ├── __init__.py
    │   ├── base.py             # BaseTool抽象类 + ToolResult封装
    │   ├── code_tools.py       # 代码分析、Diff审查、文档生成工具
    │   ├── doc_tools.py        # 文件读写、目录浏览、知识检索工具
    │   └── registry.py         # 工具注册中心，管理注册/查找/调用
    └── rag/
        ├── __init__.py
        ├── document_loader.py  # 多格式文档加载 + 智能分块
        ├── vector_store.py     # ChromaDB优先 / JSON文件降级
        └── retriever.py        # 统一检索接口
```

## 自定义扩展

### 添加新工具

```python
from src.tools.base import BaseTool, ToolResult

class MyTimerTool(BaseTool):
    name = "timer"
    description = "获取当前时间戳，用于记录操作时间"
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self, **kwargs) -> ToolResult:
        import time
        return ToolResult.ok(f"当前时间戳: {time.time()}")

# 注册到Agent
registry.register(MyTimerTool())
```

### 切换LLM供应商

`.env`中修改三行即可切换模型：

```env
# 小米大模型（默认）
LLM_BASE_URL=https://api.xiaomi.com/v1
LLM_MODEL_NAME=xiaomi-pretrained-base

# 改为 OpenAI
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL_NAME=gpt-4o

# 改为任何 OpenAI 兼容接口
# LLM_BASE_URL=https://your-endpoint/v1
# LLM_MODEL_NAME=your-model
```

### 调整Agent行为

`config.yaml` 关键参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `agent.max_iterations` | 10 | ReAct最大推理轮数 |
| `agent.verbose` | true | 是否显示思考过程 |
| `rag.chunk_size` | 500 | 文档分块字符数 |
| `rag.top_k` | 5 | 检索返回结果数 |
| `memory.short_term_size` | 20 | 短期对话记忆条数 |

## 设计依据

本项目在架构设计时参考了2026年4-5月AI Agent领域的以下进展：

| 参考项目 | 发布时间 | 借鉴点 |
|---------|---------|--------|
| **Frona v2026.5.0** | 2026-05 | 单人自托管Agent的模块化架构设计 |
| **Late CLI v1.2.2** | 2026-05 | 低资源消耗、减少上下文膨胀的思路 |
| **Anthropic MCP** | 2025-12 | 统一的工具调用接口协议标准 |
| **LangChain ReAct** | 2024 | 行业标准的ReAct推理范式实现 |
| **AgentOS** | 2026-05 | 认知记忆分层机制的设计参考 |

## 常见问题

**Q: 不装ChromaDB能用吗？**
A: 可以。系统会自动降级为JSON文件存储，功能完整，只是大规模检索时性能略低。

**Q: 支持哪些模型？**
A: 任何兼容OpenAI Chat Completions API的模型服务。已在小米大模型和GPT-4o上验证通过。

**Q: 能同时调用多个工具吗？**
A: 当前每次Action调用一个工具（遵循ReAct规范），但LLM可以在一轮内发起多个并行工具调用。

**Q: 数据安全如何保证？**
A: 所有数据本地存储（`data/`目录），不经过外部服务器。LLM API调用仅发送必要的上下文。

## 许可证

MIT License
