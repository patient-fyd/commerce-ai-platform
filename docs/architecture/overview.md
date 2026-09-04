# CommerceAI 目标架构概览

## 文档范围

本文描述 CommerceAI Platform 计划逐阶段建设的目标架构，用于指导后续设计和学习路径。当前项目处于 **Phase 0 - Local Data Foundation**；目标链路中仅 MySQL 数据源、Synthetic Data Generator 和 Doris 本地基础环境已经实现，组件存在不代表组件间链路已打通。

## 目标数据链路

```text
MySQL / Event Generator
        ↓
       NiFi
        ↓
       Kafka
        ↓
       Flink
        ↓
   Apache Doris
        ↓
        dbt
        ↓
 Semantic Layer
        ↓
 Metadata / Lineage
        ↓
        RAG
        ↓
    Data Agent
        ↓
Evaluation / Governance
```

## 组件职责

- **MySQL / Event Generator**：提供业务状态数据和可控的商业事件样本。
- **NiFi**：负责数据采集、基础路由与数据流编排。
- **Kafka**：作为事件流的持久化缓冲和上下游解耦层。
- **Flink**：承担 CDC 接入、实时清洗、转换和流式计算。
- **Apache Doris**：承载面向分析的实时数仓和分层数据模型。
- **dbt**：管理分析转换、模型依赖、数据测试与文档。
- **Semantic Layer**：统一业务实体、指标定义和查询语义。
- **Metadata / Lineage**：采集技术与业务元数据，追踪数据流向和模型依赖。
- **RAG**：在受控知识范围内完成向量化、索引和检索增强。
- **Data Agent**：基于授权工具与语义上下文辅助数据分析。
- **Evaluation / Governance**：覆盖质量评估、安全边界、权限、审计与治理策略。

## 设计约束

- 面向 Apple Silicon 优先采用 ARM64 或多架构 Docker 镜像。
- 适配 24GB RAM 的本地环境，按阶段、按需启动最小服务集合。
- 使用小规模合成或脱敏数据，不将数据库真实数据写入版本库。
- 后续 LLM 和 Embedding 使用云 API，不在本地部署大模型。
- 每个阶段先明确契约和验收标准，再引入所需组件，避免提前增加复杂度。

## 当前实现边界

Phase 0 当前已经实现：

- 单节点 MySQL 8.4 本地数据源及其 OLTP schema。
- 生成可重复小规模电商 SQL 数据的 Synthetic Data Generator。
- Apple Silicon 原生的 Apache Doris All-In-One 本地环境：单 FE、单 BE、单副本、持久化存储，以及空的 `commerce_ai` 数据库。

MySQL、Generator 和 Doris 目前可以各自独立运行，但尚未形成自动采集或流式数据链路。NiFi、Kafka、Flink、Doris 数仓分层模型、dbt、Semantic Layer、Metadata / Lineage、RAG、Data Agent、Evaluation / Governance 均未实现，留待各自 Phase。
