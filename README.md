# CommerceAI Platform

CommerceAI Platform 是一个长期学习与实践项目，目标是从商业事件数据出发，逐步搭建一条覆盖数据采集、实时计算、分析建模、语义治理与智能应用的现代数据平台链路。

当前状态：**Phase 0 - Local Data Foundation**

本仓库已实现第一版 MySQL Source Model，用于模拟用户、商品、订单、支付和退款的 OLTP 业务数据。数据采集、流处理、分析数仓以及 AI 能力均尚未实现。

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
| Phase 0 | Local Data Foundation：项目骨架与 MySQL OLTP 数据源 | **当前阶段（MySQL Source Model 已实现）** |
| Phase 1 | Source & Ingestion：事件生成与 NiFi 采集 | 未开始 |
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

Phase 0 已建立项目骨架，并实现可独立运行的本地 MySQL 8.4 数据源：

- 规范化 OLTP 模型：用户、分类、SPU、SKU、订单、订单明细、支付和退款。
- 少量人工可读的关系验证数据。
- Apple Silicon 可用的单节点 MySQL Compose，包含健康检查和持久化卷。
- 启停、状态、日志和数据库终端命令。

源模型设计见 [`docs/data-model/source-model.md`](docs/data-model/source-model.md)。Phase 1-9 的数据采集、消息、计算、数仓、语义层和 AI 能力仍未实现。

## Local MySQL Development

### 准备配置

仓库只提交示例配置。先创建被 Git 忽略的本地 `.env`，并替换其中的示例密码：

```bash
cp .env.example .env
```

### 启动与停止

```bash
make mysql-up
make mysql-status
make mysql-logs
make mysql-restart
make mysql-down
```

`mysql-down` 会停止并移除容器和 Compose 网络，但保留 MySQL 命名卷，后续启动会继续使用已有数据。

### 连接

使用容器内置客户端和 `.env` 中的应用账号连接：

```bash
make mysql-cli
```

也可以从宿主机客户端连接，端口和凭据以本地 `.env` 为准：

```bash
mysql --host=127.0.0.1 --port=3306 --user=commerce_app --password commerce
```

### 首次初始化行为

MySQL 官方镜像只会在数据目录为空的**第一次启动**时执行 `/docker-entrypoint-initdb.d/` 中的脚本。本项目按顺序执行：

1. 由 `MYSQL_DATABASE` 创建 `commerce` 数据库（示例配置值）。
2. 执行 `source/mysql/schema.sql`。
3. 执行 `source/mysql/seed.sql`。

修改 SQL 文件后，仅执行 `make mysql-restart` 不会重新初始化已有数据库。如需从头验证初始化，可在确认本地数据可丢弃后执行以下命令删除 Compose 数据卷，再重新启动：

```bash
docker compose --env-file .env -f infra/compose/compose.mysql.yml down -v
make mysql-up
```

### 验证

先检查 Compose 最终配置：

```bash
docker compose --env-file .env -f infra/compose/compose.mysql.yml config
```

MySQL 健康后进入客户端，可执行以下关系检查：

种子数据的预期数量为 8 个用户、8 个 SKU、12 张订单、16 条订单明细、13 次支付尝试和 5 次退款请求。

```sql
SELECT COUNT(*) AS user_count FROM user_info;
SELECT COUNT(*) AS sku_count FROM sku_info;
SELECT COUNT(*) AS order_count FROM order_info;

SELECT o.order_no, d.sku_name_snapshot, d.quantity, d.line_amount
FROM order_info AS o
JOIN order_detail AS d ON d.order_id = o.order_id
ORDER BY o.order_id, d.order_detail_id;

SELECT o.order_no, p.payment_attempt_no, p.payment_status, p.payment_amount
FROM order_info AS o
JOIN payment_info AS p ON p.order_id = o.order_id
ORDER BY o.order_id, p.payment_attempt_no;

SELECT r.refund_no, o.order_no, d.sku_name_snapshot, r.refund_status, r.refund_amount
FROM refund_info AS r
JOIN order_info AS o ON o.order_id = r.order_id
JOIN order_detail AS d ON d.order_detail_id = r.order_detail_id
ORDER BY r.refund_id;
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

严禁提交 `.env`、密码、Token、API Key、私钥、凭据文件、数据库真实数据和本地 Docker 运行时数据。需要共享变量名时，使用只包含示例值的 `.env.example`。
