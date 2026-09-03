# CommerceAI Platform

CommerceAI Platform 是一个长期学习与实践项目，目标是从商业事件数据出发，逐步搭建一条覆盖数据采集、实时计算、分析建模、语义治理与智能应用的现代数据平台链路。

当前状态：**Phase 0 - Project Bootstrap**

本仓库目前仅完成项目目录、基础文档和开发约定的初始化。除项目骨架外，数据服务、处理任务、分析模型以及 AI 能力均尚未实现。

## 项目目标

- 以可复现的小规模商业数据场景理解端到端数据平台建设过程。
- 逐阶段实践事件生成、数据集成、流处理、实时分析和数据建模。
- 在数据基础稳定后，再探索语义层、元数据、血缘、RAG、Data Agent 与评估治理。
- 保持各阶段边界清晰、可验证，并为架构决策留下记录。

## 最终架构

以下是项目计划逐步演进到的**目标架构**，不代表当前已经实现：

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

更详细的目标架构说明见 [`docs/architecture/overview.md`](docs/architecture/overview.md)。

## 技术栈

计划使用的主要技术如下，具体引入时间以各阶段目标为准：

| 领域 | 计划技术 |
| --- | --- |
| 数据源与事件 | MySQL、Event Generator |
| 数据集成 | Apache NiFi |
| 消息队列 | Apache Kafka |
| 实时计算 | Apache Flink、Flink CDC |
| 实时数仓 | Apache Doris |
| 数据建模 | dbt |
| 数据消费 | Semantic Layer |
| 数据治理 | Metadata、Lineage |
| 智能检索 | RAG、云端 Embedding / LLM API |
| 智能应用 | Data Agent |
| 质量保障 | Evaluation、Governance |
| 本地基础设施 | Docker Desktop、Make |

## Roadmap

| 阶段 | 主题 | 状态 |
| --- | --- | --- |
| Phase 0 | Project Bootstrap：仓库骨架、基础文档与开发约定 | **当前阶段** |
| Phase 1 | Source & Ingestion：MySQL、事件生成与 NiFi 采集 | 未开始 |
| Phase 2 | Event Streaming：Kafka 事件管道 | 未开始 |
| Phase 3 | Stream Processing：Flink CDC 与流处理 | 未开始 |
| Phase 4 | Real-time Warehouse：Apache Doris 与分层数据模型 | 未开始 |
| Phase 5 | Analytics Engineering：dbt 转换、测试与文档 | 未开始 |
| Phase 6 | Semantic Layer：统一指标与业务语义 | 未开始 |
| Phase 7 | Metadata & Lineage：元数据采集与数据血缘 | 未开始 |
| Phase 8 | RAG & Data Agent：检索增强与数据智能体 | 未开始 |
| Phase 9 | Evaluation & Governance：评估、安全与治理 | 未开始 |

## 本地资源限制

开发环境以 macOS、Apple Silicon M4、24GB RAM 和 Docker Desktop 为基准。后续阶段应遵守以下约束：

- Docker 镜像优先选择原生 ARM64 或明确支持多架构的版本。
- 控制容器数量、内存上限和并行度，避免一次启动完整目标架构。
- 每个阶段仅运行当前验证所必需的服务，并按需停止非必要容器。
- 数据集采用适合本地学习和测试的小规模样本，不提交数据库真实数据或运行时卷。
- LLM 与 Embedding 能力后续使用云 API，不在本地运行大模型。
- 密码、Token、API Key 等敏感信息只通过本地环境变量或密钥机制管理，严禁提交到仓库。

## 当前进度

Phase 0 已建立预期的目录结构，并提供 `.gitignore`、`Makefile`、架构概览与 ADR 模板。当前没有可运行的数据服务，也没有实现 Phase 1-9 的功能。

可用命令：

```bash
make help
```

## 项目目录

```text
commerce-ai-platform/
├── infra/                 # 本地基础设施编排与辅助脚本
├── source/                # MySQL 数据源与事件生成器
├── nifi/                  # NiFi 流程定义
├── flink/                 # Flink CDC 与流处理任务
├── doris/                 # Doris 分层 DDL 与数据加载
├── warehouse/dbt/         # dbt 分析工程项目
├── semantic/              # 语义层定义
├── metadata/              # 元数据采集与血缘
├── rag/                   # Embedding、索引与检索
├── agent/                 # Data Agent API、工具与提示词
├── evaluation/            # 评估与治理资产
├── docs/                  # 架构、数据模型、指标与 ADR 文档
└── tests/                 # 跨模块测试
```

各目录现阶段仅作为后续阶段的边界占位，不表示对应能力已经实现。

## 安全约定

严禁提交 `.env`、密码、Token、API Key、私钥、凭据文件、数据库真实数据和本地 Docker 运行时数据。需要共享变量名时，应在后续阶段使用不包含真实值的 `.env.example`。

