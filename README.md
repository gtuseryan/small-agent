# midev-agent
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

单人构建，MIT开源。
