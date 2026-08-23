"""agent_hive —— 首脑统筹的 LangGraph 编排程序。

首脑（本程序）只做三件事：定架构、分包派发、验收集成；
编码/测试/评审/调研四个角色专家各司其职；
架构方案与批次表两个关口需要人工审批（LangGraph interrupt）。
契约与提示词与 ~/.dsh/skills/agent-hive/contracts.md 保持一致。
"""
