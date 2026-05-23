# small-agent
小工具
一个采用 ReAct 范式的轻量级智能Agent系统，专为研发场景设计。

核心能力：
- 智能代码审查：自动分析代码逻辑，识别Bug和安全漏洞
- 技术文档生成：根据代码自动生成API文档、模块说明
- 研发知识库问答：基于RAG的私有知识库自然语言检索
- 多工具编排：统一接口调用文件系统、代码分析、知识检索等工具

技术亮点：
- ReAct推理循环（Thought → Action → Observation）
- MCP兼容的工具系统，7个内置工具，支持自定义扩展
- 三层记忆管理（短期/工作/长期）
- ChromaDB + JSON双模式向量存储
- OpenAI兼容API格式，可接入任意兼容模型

快速开始：
pip install -r requirements.txt
cp .env.example .env
python main.py demo
二次更新
单人构建，MIT开源。
项目定位 —— 从1段扩展为4段，逐项拆解三大痛点（审查/文档/检索），每项给出具体场景和数据（"一个MR几百行变更"、"一个中等模块文档写半天"、"新人入职两周才能自行找到答案"）

核心能力 —— 四项每项从一段扩展为完整小节。代码审查展开为四个子维度（逻辑/安全/规范/性能）配具体示例；文档生成列出四类输出（概述/API/配置/变更记录）；知识问答说明"建索引→查"两步流程；工具编排展开为规划/选择/修正/汇总四个子步骤

技术亮点 —— 五项每项从一段扩展为深度分析。ReAct展开为Thought/Action/Observation三个阶段各配具体行为描述；工具系统详述BaseTool/ToolRegistry/ToolResult三层设计；记忆管理补充了三个维度的触发时机和数据格式；双模式存储补充了HNSW算法、SQLite底层的技术细节；API格式补充了Function Calling的完整流程
