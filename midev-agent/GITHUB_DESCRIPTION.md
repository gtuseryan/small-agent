# small-agent

基于**小米预训练基础大模型**的轻量级智能研发协作Agent。采用ReAct推理范式，深度集成RAG检索增强生成与MCP兼容工具系统，单人可部署、零额外基础设施依赖、支持自定义扩展的AI研发助手。

---

## 项目定位

研发团队每天都在重复三件低效的事：

**代码审查** —— 一个MR动辄几百行变更，审查者要从逻辑正确性、安全漏洞、代码规范、性能隐患四个维度逐一过目。遇到不熟悉的模块还得先花时间理解上下文，一轮审查下来半小时起步。更麻烦的是，审查标准因人而异，同一个问题A说行B说不行。

**文档编写** —— 功能上线后才补文档是常态。API文档要列出所有接口的参数类型、返回值结构、异常码定义；README要讲清楚模块职责、依赖关系、配置参数。这些工作技术含量不高但极其耗时，一个中等模块的文档往往要写半天。

**知识检索** —— "这个设计当时为什么选A方案不选B？""上次那个线上问题的根因是什么？""谁之前做过类似的支付对接？"这些答案散落在飞书群聊、Confluence文档、Gitlab Issue和某次会议的口头讨论里。新人入职至少需要两周才能自行找到答案。

small-agent 用一个LLM驱动的智能体统一解决这三个问题。它的核心区别在于：不是被动等待你提问，而是**主动调用工具**去读取代码、检索文档、分析逻辑，像一个有经验的研发同事一样多步推理，最终交付可落地的结果。

---

## 核心能力

### 智能代码审查

Agent首先调用 `list_directory` 了解项目结构，然后通过 `read_file` 逐文件读取源码。对于每个文件，它从四个维度进行分析：

- **逻辑正确性** —— 追踪数据流和控制流，检查边界条件处理、空值判断、异常捕获是否完备。例如识别出"在调用 `dict.get(key)` 后未判空就直接访问嵌套属性"这类隐蔽Bug。
- **安全漏洞** —— 扫描SQL注入风险点（字符串拼接构造查询）、XSS隐患（未转义的用户输入直接渲染）、敏感信息硬编码（密钥、Token、密码明文写在代码里）。
- **代码规范** —— 检查命名一致性、函数长度、圈复杂度、重复代码块。例如发现同一个工具函数在三个文件里各写了一份，建议抽取到公共模块。
- **性能隐患** —— 标记循环内的数据库查询、未设超时的网络请求、可缓存却重复计算的操作。

审查结果通过 `review_diff` 工具输出结构化报告，每条问题标注文件路径、行号范围、严重程度和建议修改方案，直接粘贴到Gitlab MR评论区即可。

### 技术文档自动生成

调用 `generate_doc` 工具后，Agent遍历指定目录下所有源文件，提取模块结构、公共函数签名、类继承关系和配置项定义。生成的文档包含：

- **模块概述** —— 该目录负责什么功能，在整体架构中的位置，上下游依赖关系。
- **API参考** —— 每个公开函数的参数列表（名称、类型、是否必填、默认值）、返回值类型、可能抛出的异常、使用示例代码。
- **配置说明** —— 读取config文件枚举所有配置项、默认值、取值范围、修改后的影响范围。
- **变更记录** —— 基于git log提取最近提交，按feat/fix/refactor分类汇总为CHANGELOG。

输出格式支持Markdown（发布到Confluence/飞书文档）和纯文本（嵌入代码注释），且Agent会在文档中标注"此为自动生成，请人工复核"的提醒。

### 研发知识库智能问答

这是RAG管道的核心应用场景。使用方式分两步：

**第一步，建立索引。** 将团队已有的技术文档（.md .txt .yaml .json）、代码文件（.py .java .go .js .ts）、甚至飞书文档导出PDF，统一放入 `docs/` 目录，执行 `python main.py index ./docs`。Agent会将文档进行段落感知分块（500字符/块，50字符重叠避免切断上下文），向量化后存入ChromaDB。

**第二步，自然语言查询。** 后续研发过程中遇到任何疑问，直接通过 `search_knowledge` 工具提问，例如"支付模块的超时重试机制是怎么设计的？"。Agent会将问题向量化，在知识库中做BM25关键词匹配 + 稠密向量语义检索，对候选片段重排序，最后结合检索结果和LLM推理生成带引用的答案。

与普通全文搜索的关键区别：你不需要知道"关键词"是什么，用自然语言描述问题即可。且答案不仅返回匹配段落，还会综合多份文档的信息进行归纳总结，每条结论附带源文档链接，可一键溯源。

### 多工具自主编排

这是Agent区别于普通ChatBot的本质特征。当你提出一个复杂需求时，Agent不会直接猜测回答，而是：

1. **任务规划**（Planner模块）—— 将复杂意图拆解为子任务序列。例如"帮我审查最近三天变更的代码并生成周报"被拆为：获取变更文件列表 → 逐文件代码审查 → 汇总问题 → 检索本周相关技术决策 → 生成周报。
2. **工具选择** —— Agent根据每步子任务的特征，从注册的7个工具中自主选择最合适的。它知道"读文件"用 `read_file`，"查历史决策"用 `search_knowledge`，"生成周报"用 `generate_doc`。
3. **多轮修正** —— 工具返回结果不理想时，Agent会换参数重试或换工具。例如 `read_file` 返回了文件但内容不够，它会调整行号范围再次读取。
4. **结果汇总** —— 收集到足够信息后，Agent将多轮结果整合为一份完整输出，而非零散的信息片段。

整个过程你只需给出初始任务描述，Agent自主完成思考、执行、纠错、交付的全链路。

---

## 技术亮点

### ReAct推理循环

ReAct（Reasoning + Acting）是2023年由Yao等人提出的Agent范式，经两年多工业验证已成为最主流的选择。small-agent的 `react_agent.py` 严格实现了其核心循环：

**Thought（思考阶段）** —— Agent收到任务后，分析当前已知信息和未知信息。例如收到"审查代码"任务，它首先思考：我需要知道项目有哪些文件、每个文件的功能、最近变更了哪些内容——这些信息目前都没有，需要调用工具获取。

**Action（行动阶段）** —— 根据思考结论，从工具列表中选择最合适的一个并构造调用参数。Agent不想当然地乱选，而是根据每个工具的描述（description字段）判断其适用场景。例如 `list_directory` 描述说"列出目录下所有文件"，正好满足"了解项目结构"的需求。

**Observation（观察阶段）** —— 工具返回结果后，Agent分析：这些信息够了吗？有没有矛盾之处？需要继续深入吗？如果 `read_file` 返回的代码引用了另一个模块，Agent会主动去读那个模块，形成递归深入的分析链。

整个循环最多10轮，防止Agent陷入死循环。达到上限后自动触发强制总结，基于已收集信息给出当前最优回答，并标注"信息可能不完整"。

### MCP兼容工具系统

Anthropic于2025年底开源MCP（Model Context Protocol）后，迅速成为Agent工具接口的事实标准。small-agent没有直接引入MCP SDK（太重），而是参考其核心设计理念，自研了一套轻量而兼容的抽象层：

**BaseTool抽象类** —— 统一了四个基础接口。`name` 是工具的唯一标识；`description` 用自然语言告诉LLM这个工具做什么、何时使用；`parameters` 用JSON Schema定义参数类型和必填项；`execute` 是实际执行逻辑。任何新工具只需覆写这四个属性/方法。

**ToolRegistry注册中心** —— 所有工具注册到一个字典中，Agent通过名称查找工具。同时提供 `to_openai_tools()` 方法，将所有已注册工具一次性转换为OpenAI Function Calling格式的工具定义列表，直接传给LLM。

**ToolResult统一封装** —— 每个工具的执行结果统一包装为 `success` + `content` + `metadata` 三元组。成功时 `content` 是人类可读的结果文本，失败时 `error` 字段记录异常信息。Agent根据 `success` 字段决定是否换工具重试。

内置的7个工具覆盖了研发Agent的核心场景：`analyze_code`（代码逻辑分析）、`review_diff`（Git Diff审查）、`generate_doc`（文档生成）、`search_knowledge`（RAG检索）、`index_document`（文档索引）、`read_file`（文件读取）、`list_directory`（目录浏览）。

### 三层记忆管理

受AgentOS项目（2026年5月发布，LongMemEval-S得分85.6%）的认知记忆分层理念启发，small-agent实现了三层记忆架构：

**短期记忆（Short-term Memory）** —— 本质是对话历史的滑动窗口，保留最近20条消息（user/assistant/tool）。这是LLM能直接"看到"的上下文。20条的限制既保证了足够的推理依据，又避免了上下文膨胀导致Token成本飙升。

**工作记忆（Working Memory）** —— 存储当前任务的关键状态信息，是一个键值对字典。例如Agent审查了5个文件后，工作记忆里记录 `{"reviewed_files": ["a.py", "b.py", "c.py"], "found_issues": 3, "current_status": "正在分析d.py"}`。这些信息不塞入对话历史（省Token），但在每轮推理前会以"当前任务状态"的形式注入System Prompt。

**长期记忆（Long-term Memory）** —— 每次会话结束后，Agent自动生成摘要（用户请求、执行的工具、最终结论），以文本形式归档。下次新会话启动时，可以从长期记忆中检索相关历史洞察。例如上周审查过一个支付模块的Bug，本周新任务涉及支付模块时，Agent会回顾那次审查的经验。

### ChromaDB + JSON双模式存储

RAG管道的向量存储采用了渐进式架构：

**生产模式（ChromaDB）** —— 安装 `chromadb` 后，所有文档向量持久化存储在 `data/chroma_db/` 目录。ChromaDB是一个专为LLM应用设计的开源向量数据库，支持基于HNSW算法的近似最近邻搜索，十万级文档检索延迟在毫秒级。数据以SQLite格式存储，无需部署独立的数据库服务。

**降级模式（JSON文件）** —— 未安装ChromaDB时，系统自动切换为 `data/vectors.json` 文件存储。向量以NumPy数组序列化后存入JSON，检索时加载全部向量到内存做暴力余弦相似度计算。在千级文档规模下性能差异不明显，但免去了安装任何额外依赖的麻烦。

两种模式的切换对上层完全透明，`retriever.py` 通过 `VectorStore` 的统一接口屏蔽了底层差异。

### OpenAI兼容API格式

LLM客户端（`src/llm/client.py`）基于OpenAI Chat Completions API标准实现，这意味着只要模型服务支持 `/v1/chat/completions` 端点，无需任何代码改动即可接入。修改 `.env` 中两行配置即可切换：

- `LLM_BASE_URL` —— API服务地址，支持小米大模型、OpenAI、DeepSeek、vLLM本地部署、Ollama本地模型等。
- `LLM_MODEL_NAME` —— 具体模型标识，如 `xiaomi-pretrained-base` 或 `gpt-4o` 或 `deepseek-chat`。

客户端还支持 Function Calling（工具调用的底层协议），Agent注册的工具会自动转为OpenAI格式的tools定义传给LLM，LLM返回的tool_calls再由Agent解析并分发到对应的工具执行。

---

## 技术架构

```
                        用户输入
                           │
                           ▼
              ┌─────────────────────────┐
              │       Planner           │
              │  意图识别 → 子任务拆解     │
              │  "审查代码并生成周报"      │
              │       拆为4个子任务       │
              └───────────┬─────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │     ReAct 循环引擎       │
              │                         │
              │  ┌─── Thought ────────┐  │
              │  │ 分析状态，决定下一步  │  │
              │  └──────┬────────────┘  │
              │         │               │
              │  ┌──────▼────────────┐  │
              │  │   Action          │  │
              │  │  调用合适工具       │  │
              │  └──────┬────────────┘  │
              │         │               │
              │  ┌──────▼────────────┐  │
              │  │   Observation     │  │
              │  │  处理工具返回结果   │  │
              │  └──────┬────────────┘  │
              │         │               │
              │    未完成？回Thought      │
              │    已完成？→ Final       │
              └───┬──────┬──────┬───────┘
                  │      │      │
      ┌───────────┘      │      └───────────┐
      ▼                  ▼                  ▼
┌───────────┐    ┌─────────────┐    ┌─────────────┐
│  Memory   │    │   Tools     │    │     RAG     │
│           │    │             │    │             │
│ 短期(对话) │    │ 7个内置工具  │    │ 文档分块     │
│ 工作(状态) │    │ 统一注册中心  │    │ 向量嵌入     │
│ 长期(摘要) │    │ 自动转为     │    │ ChromaDB    │
│           │    │ FuncCall格式  │    │ 混合检索     │
└───────────┘    └──────┬──────┘    └─────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │   LLM Client        │
              │   OpenAI兼容格式     │
              │   小米预训练大模型    │
              │   或任意兼容模型      │
              └─────────────────────┘
```

**数据流转说明：**

1. 用户输入 → Planner拆解为子任务序列
2. 每个子任务 → ReAct引擎启动循环：Thought分析状态 → Action选择工具 → Observation处理结果
3. 工具执行过程中 → 从Memory获取当前任务状态，将关键发现写回工作记忆
4. RAG检索时 → 从ChromaDB/JSON读取向量，返回Top-K匹配文档片段
5. 所有LLM调用 → 通过统一的LLM Client发出，自动附带工具定义
6. 子任务全部完成 → Agent整合所有Observation，生成最终回答

---

## 项目结构

```
small-agent/
│
├── main.py                          # CLI总入口，argparse定义6个子命令
│                                    #  run: 执行完整Agent任务
│                                    #  chat: 交互式多轮对话
│                                    #  index: 索引文档到知识库
│                                    #  review: 审查Git代码变更
│                                    #  doc: 为源码目录生成技术文档
│                                    #  demo: 交互式功能演示
│
├── config.yaml                      # YAML格式配置文件
│                                    #  可调整Agent最大迭代轮数、文档分块大小
│                                    #  RAG检索Top-K、终端输出详细程度
│
├── requirements.txt                 # 6个Python依赖
│                                    #  openai / chromadb / rich / pyyaml / python-dotenv / numpy
│
├── .env.example                     # 环境变量模板，复制为.env后填入真实密钥
│                                    #  支持LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME
│
├── .gitignore                       # 排除__pycache__、.env、chroma_db/
│
├── data/                            # 运行时数据目录（自动创建）
│   ├── chroma_db/                   #   ChromaDB持久化向量文件（生产模式）
│   └── vectors.json                 #   JSON格式向量备份（降级模式）
│
├── examples/
│   └── demo.py                      # 零依赖演示脚本，无需API密钥
│                                    #  展示所有工具的独立运行效果
│
└── src/
    │
    ├── agent/                       # Agent核心引擎
    │   ├── react_agent.py           #   ReAct主循环实现
    │   │                            #   构建系统Prompt → 调用LLM → 解析tool_calls
    │   │                            #   → 分发工具执行 → 注入Observation → 判停
    │   │                            #   支持max_iterations上限保护
    │   │
    │   ├── planner.py               #   任务规划器
    │   │                            #   基于LLM做意图识别，输出子任务序列
    │   │                            #   每个子任务含目标描述和推荐工具类型
    │   │
    │   └── memory.py                #   三层记忆管理器
    │                                #   短期记忆：deque(maxlen=20) 滑动窗口
    │                                #   工作记忆：dict存储当前任务状态
    │                                #   长期记忆：list存储历史会话摘要
    │
    ├── llm/                         # LLM统一接入层
    │   └── client.py                #   OpenAI兼容Chat Client
    │                                #   封装chat()方法，支持tools参数
    │                                #   通过.env读取api_key/base_url/model_name
    │
    ├── tools/                       # 工具系统
    │   ├── base.py                  #   BaseTool抽象类：name/description/parameters/execute
    │   │                            #   ToolResult数据类：success/content/metadata/error
    │   │                            #   to_openai_tool()：转为Function Calling格式
    │   │
    │   ├── code_tools.py            #   代码类工具
    │   │                            #   AnalyzeCodeTool：解析文件结构，识别逻辑问题
    │   │                            #   ReviewDiffTool：解析Diff内容，生成审查意见
    │   │                            #   GenerateDocTool：遍历源码，输出API文档
    │   │
    │   ├── doc_tools.py             #   文档与文件类工具
    │   │                            #   ReadFileTool：按行号范围读取文件
    │   │                            #   ListDirectoryTool：列出目录树结构
    │   │                            #   SearchKnowledgeTool：RAG知识库检索
    │   │                            #   IndexDocumentTool：文档索引到向量库
    │   │
    │   └── registry.py              #   工具注册中心
    │                                #   register()：注册单个工具实例
    │                                #   call()：按名称调用工具
    │                                #   to_openai_tools()：导出全量工具定义
    │
    └── rag/                         # RAG检索增强生成管道
        ├── document_loader.py       #   多格式文档加载器
        │                            #   支持：.md .txt .py .java .go .js .ts .yaml .json
        │                            #   智能分块：段落感知，500字符/块，50字符重叠
        │
        ├── vector_store.py          #   向量存储抽象层
        │                            #   生产模式：ChromaDB持久化，HNSW索引
        │                            #   降级模式：JSON文件 + 暴力余弦相似度
        │                            #   嵌入模型：BGE-large-v1.5（中文优化）
        │
        └── retriever.py             #   统一检索接口
                                     #   index()：索引文件或目录
                                     #   query()：语义检索 + 关键词混合搜索
```

---

## 快速开始

### 前置要求

- Python 3.10 或更高版本
- 可访问的小米预训练基础大模型 API 端点（或任意 OpenAI 兼容模型服务）
- 可选：安装 ChromaDB 获得更好的检索性能（`pip install chromadb`）

### 第一次运行（3步）

**第一步：克隆并安装依赖**

```bash
git clone <your-repo-url> small-agent
cd small-agent
pip install -r requirements.txt
```

如果安装 ChromaDB 遇到问题（某些系统需要额外编译工具），可以先不装，系统会自动降级为 JSON 存储模式：

```bash
pip install openai rich pyyaml python-dotenv numpy
```

**第二步：配置API密钥**

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的API密钥：

```env
LLM_API_KEY=xm-your-actual-api-key
LLM_BASE_URL=https://api.xiaomi.com/v1
LLM_MODEL_NAME=xiaomi-pretrained-base
```

**第三步：运行演示**

```bash
python main.py demo
```

你会看到Agent启动、加载工具、注册到注册中心，然后进入交互模式。首次使用建议先试试这几个命令：

```bash
# 简单对话 —— 不需要工具调用，直接和模型对话
python main.py chat

# 索引项目文档 —— 把代码和文档喂给知识库
python main.py index ./src

# 查询知识库 —— 检索刚才索引的内容
python main.py run "src/tools 目录下有哪些工具？每个工具的作用是什么？"

# 审查代码 —— 让Agent分析某个文件的代码质量
python main.py run "审查 src/tools/registry.py，检查代码规范和潜在问题"

# 生成文档 —— 为某个模块自动生成API文档
python main.py doc ./src/tools

# 审查Git变更 —— 审查最近一次提交的代码变更
python main.py review "$(git diff HEAD~1)"
```

### 无API密钥也能先体验

如果暂时没有API密钥，可以运行独立演示脚本查看所有工具的效果：

```bash
python examples/demo.py
```

这个脚本会逐个展示7个工具的输入输出，帮你理解每个工具的功能和参数格式，不需要任何网络请求。

---

## 配置详解

`config.yaml` 中每个参数的含义和调优建议：

**agent.max_iterations**（默认10）
ReAct循环的最大轮数。简单的代码审查任务通常3-5轮完成，复杂的多文件分析可能需要7-8轮。如果经常触发"达到最大轮数"的警告，可以适当增加。不建议设太大（>20），否则Token消耗会显著增加。

**agent.verbose**（默认true）
设为true时，终端会显示Agent的完整思考过程：每轮的Thought内容、选择的Action、工具返回的Observation。这对于调试和理解Agent行为非常有帮助。生产环境如果觉得输出太多，可以设为false关闭。

**rag.chunk_size**（默认500）
文档分块时的字符数。500字符大约是一段代码的平均长度（一个中等复杂度的函数），也是一段技术文档的自然段落大小。如果发现检索结果经常包含不相关的上下文，可以调小；如果检索结果太碎片化，可以调大。

**rag.chunk_overlap**（默认50）
相邻两个文档块之间的重叠字符数。50字符的重叠确保不会因为分块边界恰好切断一句完整的话而导致上下文断裂。增大这个值会生成更多的文档块。

**rag.top_k**（默认5）
每次检索返回的最相关文档片段数量。太少可能遗漏关键信息，太多会增加LLM上下文的噪音和Token消耗。建议在3-8之间调整。

**memory.short_term_size**（默认20）
短期记忆保留的最近消息条数。20条大约能覆盖3-4轮完整的ReAct交互。如果任务特别复杂需要更多上下文，可以增大，但注意每增加一条消息都可能增加数百到数千Token的API调用成本。

---

## 设计参考

本项目在架构设计阶段系统调研了2026年4-5月AI Agent领域的代表性开源项目，以下是借鉴关系的详细说明：

**Frona v2026.5.0**（2026年5月发布，Rust引擎，BSL许可证）
fronalabs推出的单人自托管Agent平台，支持Docker Compose一键部署，内置Cedar策略语言实现沙箱隔离。small-agent借鉴了两个关键设计：一是工具系统的模块化架构——Frona将每个工具封装为独立模块，通过统一接口接入Agent，small-agent的BaseTool + ToolRegistry即源于此；二是LLM多供应商切换机制——Frona支持通过配置文件在不同模型间切换而不改代码，small-agent将其简化为修改.env两行的方案。

**Late CLI v1.2.2**（2026年5月1日发布，Go语言，MIT许可证）
mlhher开发的极低资源AI编码Agent，仅需5GB VRAM即可运行，纯Go编译为单一静态二进制。small-agent特别借鉴了其"避免上下文膨胀"的设计理念：Late CLI通过精确匹配Diff和子Agent编排来减少Token消耗。small-agent将此理念转化为三层记忆管理——不在每轮对话中都塞入完整历史，而是通过工作记忆提取关键状态信息，显著降低了传给LLM的上下文体积。

**Anthropic MCP 协议**（2025年12月开源）
Model Context Protocol定义了LLM与外部工具和数据源之间的标准通信接口。small-agent没有直接引入MCP SDK（Python SDK较重，不符合本项目的轻量定位），而是深入研究了其协议规范，自研了一套理念兼容的轻量抽象层。BaseTool的四个核心接口（name / description / parameters / execute）直接对应MCP中Tool定义的四个基础字段，to_openai_tools()方法则实现了向OpenAI Function Calling格式的自动转换。

**LangChain ReAct**（2024年，Python，MIT许可证）
LangChain是最早将ReAct范式工程化实现的框架之一。small-agent的react_agent.py参考了其核心循环逻辑，但做了两个简化：去掉了LangChain复杂的AgentExecutor多层封装，改为一个扁平化的while循环（更易理解和调试）；去掉了对LangChain依赖链的绑定，改用原生的OpenAI SDK直接调用，减少了项目中第三方依赖的数量。

**AgentOS**（2026年5月发布，TypeScript运行时，Apache 2.0许可证）
framers推出的Agent运行时，最大的亮点是实现了一套8层认知记忆系统（含HEXACO人格模型），在LongMemEval-S基准测试中取得了85.6%的SOTA得分。small-agent受其"认知记忆分层"理念启发，但做了大幅简化——从8层精简为3层（短期/工作/长期），去掉了人格模型等学术化设计，聚焦于实际研发场景中最需要的记忆类型。

---

## 自定义扩展

### 添加新工具

small-agent的工具系统遵循"定义-注册-使用"三步走。以下是添加一个"执行Shell命令"工具的完整示例：

```python
import subprocess
from src.tools.base import BaseTool, ToolResult

class ShellTool(BaseTool):
    @property
    def name(self) -> str:
        return "run_shell"

    @property
    def description(self) -> str:
        return "执行一条Shell命令并返回标准输出。用于运行测试、查看系统信息、操作文件等。注意：不要执行危险的命令（如rm -rf）。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的Shell命令，例如 'ls -la' 或 'python --version'",
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "命令超时时间（秒），默认30秒",
                    "default": 30,
                },
            },
            "required": ["command"],
        }

    def execute(self, command: str, timeout_seconds: int = 30, **kwargs) -> ToolResult:
        validation = self._validate_params({"command": command}, ["command"])
        if validation:
            return ToolResult.fail(validation)

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout_seconds, cwd=".",
            )
            output = result.stdout or result.stderr
            return ToolResult.ok(
                output[:2000],  # 截断过长的输出
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ToolResult.fail(f"命令超时（{timeout_seconds}秒）: {command}")
        except Exception as e:
            return ToolResult.fail(f"命令执行异常: {str(e)}")


# 注册到Agent（在 main.py 中添加这两行）
from src.tools.registry import ToolRegistry
registry = ToolRegistry()
registry.register(ShellTool())
# 之后Agent就可以自主决定何时执行 Shell 命令了
```

### 切换LLM供应商

不需要修改任何Python代码，只需调整 `.env` 文件中的两行配置：

```env
# ===== 方案一：小米预训练基础大模型（默认） =====
LLM_API_KEY=xm-your-actual-api-key
LLM_BASE_URL=https://api.xiaomi.com/v1
LLM_MODEL_NAME=xiaomi-pretrained-base

# ===== 方案二：OpenAI GPT-4o =====
# LLM_API_KEY=sk-your-openai-api-key
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_MODEL_NAME=gpt-4o

# ===== 方案三：DeepSeek =====
# LLM_API_KEY=your-deepseek-api-key
# LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_MODEL_NAME=deepseek-chat

# ===== 方案四：本地 vLLM 部署 =====
# LLM_API_KEY=not-needed
# LLM_BASE_URL=http://localhost:8000/v1
# LLM_MODEL_NAME=Qwen2.5-7B-Instruct

# ===== 方案五：本地 Ollama =====
# LLM_API_KEY=not-needed
# LLM_BASE_URL=http://localhost:11434/v1
# LLM_MODEL_NAME=qwen2.5:7b
```

切换后重新运行 `python main.py demo` 即可验证新模型是否正常工作。


---

## 常见问题

**Q: 不装ChromaDB可以用吗？**
A: 完全可用。系统检测到ChromaDB未安装时，自动降级为本地JSON文件存储（`data/vectors.json`）。功能和检索精度不变，区别仅在于：ChromaDB使用HNSW近似搜索，十万级文档在毫秒级返回；JSON模式需要加载全量向量到内存做暴力计算，千级以内文档性能差异不明显。建议开发调试阶段用JSON模式（零额外安装），正式使用再装ChromaDB。

**Q: 支持哪些LLM？**
A: 任何兼容OpenAI Chat Completions API（`/v1/chat/completions`端点）的模型服务都可以接入。已验证可用的包括：小米预训练基础大模型、OpenAI GPT-4o/GPT-4o-mini、DeepSeek V3、vLLM部署的开源模型、Ollama本地模型。核心要求是模型支持Function Calling（工具调用），否则Agent无法自动选择工具。

**Q: Agent一次任务能调用多个工具吗？**
A: 可以，分两种方式。串行方式：每轮Action调用一个工具，Observation返回后进入下一轮，这是ReAct的标准模式。并行方式：如果模型支持并行Function Calling（如GPT-4o），LLM可以在单轮返回多个tool_calls，Agent会依次执行所有调用再统一处理Observation。

**Q: 数据安全吗？保存在哪里？**
A: 所有数据（知识库索引、向量文件、会话记录）都在本地 `data/` 目录下，不出你的机器。LLM API调用仅发送当前任务必要的上下文（系统Prompt + 对话历史 + 工具调用结果），不会上传你的整个知识库。对保密性要求极高的场景，建议使用本地部署的模型方案（vLLM或Ollama），这样所有数据完全离线。

**Q: 和GitHub Copilot、Cursor这类AI编程工具有什么区别？**
A: GitHub Copilot和Cursor是IDE内嵌的代码补全工具，擅长"在光标处生成下一行代码"。small-agent定位不同：它是一个自主Agent，你给它一个任务目标（"审查这个模块的安全性"），它会自己读取文件、分析逻辑、检索相关知识、生成完整报告。它不替代Copilot，而是互补——Copilot帮你写代码，small-agent帮你审查、记录和检索。

**Q: 生产环境部署有什么要求？**
A: 最小部署：一台有Python 3.10+的机器，1核CPU，512MB内存即可运行（JSON存储模式）。推荐部署：2核CPU，2GB内存，安装ChromaDB以获得更好的检索性能。无需数据库、消息队列等基础设施。多人使用场景建议对 `data/` 目录做定期备份。


---

## 技术栈

Python 3.10+ · OpenAI SDK · ChromaDB · Rich（终端美化） · PyYAML · python-dotenv · NumPy

---

## 许可证

MIT License
