# CommerceAI Platform

CommerceAI Platform 是一个长期学习与实践项目，目标是从商业事件数据出发，逐步搭建一条覆盖数据采集、实时计算、分析建模、语义治理与智能应用的现代数据平台链路。

当前状态：**Phase 0 - Local Data Foundation｜Completed**

本仓库已实现第一版 MySQL Source Model、为该模型生成可重复模拟数据的本地 Python 工具，以及可独立运行的单节点 Apache Doris 本地开发环境。数据采集、流处理、Doris 数仓分层模型以及 AI 能力均尚未实现。

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
| Phase 0 | Local Data Foundation：项目骨架、MySQL OLTP 数据源与本地 Doris 基础环境 | **Completed** |
| Phase 1 | Traditional Data Warehouse Modeling | **下一阶段，未开始** |
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

## Phase 0 完成状态

Phase 0 已完成项目骨架与可独立运行的本地数据基础：

- 规范化 OLTP 模型：用户、分类、SPU、SKU、订单、订单明细、支付和退款。
- 可配置随机种子和日期范围、带生成前业务校验的 synthetic SQL 数据生成器。
- Apple Silicon 可用的单节点 MySQL Compose，包含健康检查和持久化卷。
- Apple Silicon 原生单节点 Doris All-In-One Compose，包含健康检查、幂等数据库初始化和持久化卷。
- MySQL 与 Doris 各自独立的启停、状态、日志和数据库终端命令。

源模型设计见 [`docs/data-model/source-model.md`](docs/data-model/source-model.md)。Doris 当前只提供本地运行基础设施和 `commerce_ai` 数据库；ODS、DIM、DWD、DWS、ADS 等正式数仓模型均未创建。下一阶段是 **Phase 1｜Traditional Data Warehouse Modeling**，目前尚未开始。其他数据采集、消息、计算、语义层和 AI 能力也仍未实现。

## Synthetic Data Generator

默认生成 `small` 数据集（约 10,000 张订单），输出目录不会被 Git 跟踪：

```bash
make generate-data
make import-generated-data
```

MySQL 新数据卷只自动创建表结构，不再自动导入 `source/mysql/seed.sql`。`import-generated-data` 应在空的 `commerce` 数据库中执行；重复导入会因主键和唯一键冲突而失败。可通过 `SCALE`、`SEED`、`START_DATE`、`END_DATE` 和 `DATA_OUTPUT` 覆盖参数。完整的场景、导入和验证说明见 [`source/data-generator/README.md`](source/data-generator/README.md)。

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

MySQL 官方镜像只会在数据目录为空的**第一次启动**时执行 `/docker-entrypoint-initdb.d/` 中的脚本。本项目执行：

1. 由 `MYSQL_DATABASE` 创建 `commerce` 数据库（示例配置值）。
2. 执行 `source/mysql/schema.sql`。

`source/mysql/seed.sql` 不再自动执行，避免其固定主键与数据生成器冲突。表结构初始化完成后，通过生成器写入业务数据：

```bash
make generate-data
make import-generated-data
```

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

MySQL 健康且生成数据导入完成后进入客户端，可执行以下数量和关系检查：

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

## Local Doris Development

### 镜像与适用范围

本项目使用 `apache/doris:all-in-one-4.1.3`。这是 Apache Doris 官方提供的 All-In-One 基础镜像，在一个容器内运行单 FE、单 BE 和单副本，适合本地开发与集成测试，不用于生产。选择 4.1.3 是因为它是当前官方 Latest 版本，并且同一 tag 的 OCI image index 同时提供 `linux/arm64` 和 `linux/amd64`；Compose 明确选择 `linux/arm64`，不会在 Apple Silicon 上运行 amd64 模拟镜像。基础 tag 已满足内部表开发需要，因此不使用包含额外 Hudi、Trino 和 MaxCompute 组件的 `-full` tag。详见 [Apache Doris All-In-One 官方说明](https://doris.apache.org/community/developer-guide/all-in-one-image/) 和 [官方版本页](https://doris.apache.org/download/)。

All-In-One 镜像已内置适合 CI / 本地测试的资源参数：FE heap 为 `-Xmx2048m`，BE JNI heap 为 `-Xmx1024m`，BE `mem_limit = 40%`。本项目不通过 `FE_CONFIG_EXTRA` 或 `BE_CONFIG_EXTRA` 重复覆盖这些值，避免容器上限与进程内限制互相冲突。

### 资源建议

在 24GB RAM 的 Mac 上，建议将 Docker Desktop 总内存设为 **10GB**，为 macOS、浏览器、IDE、ChatGPT / Codex 和按需运行的 MySQL 留出空间。Doris 容器默认限制为 **4 CPU / 6GB RAM**；这是容器级硬上限，不改变镜像内部的 FE / BE 内存参数。空闲开发环境无需为了生产建议值提高资源。

如确有需要，可在本地 `.env` 中覆盖 `DORIS_MEMORY_LIMIT` 和 `DORIS_CPUS`，但降低内存时要注意 FE 固定的 2GB heap 及 BE 的额外开销。

### 本地账号

Doris 使用 `root` 用户，并从被 Git 忽略的本地 `.env` 读取 `DORIS_ROOT_PASSWORD`。示例配置让它复用 `MYSQL_ROOT_PASSWORD`，因此只需维护一个本地 root 密码：

```dotenv
DORIS_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
```

首次启动和后续启动都会确保 Doris 密码与该值一致。官方 All-In-One entrypoint 必须从容器内部 `127.0.0.1` 使用 root 完成 BE 注册，因此 Compose 仅为容器内 localhost 启用 `skip_localhost_auth_check`；通过宿主机映射端口连接仍需密码。

### 启动、停止与状态

```bash
make doris-up
make doris-status
make doris-logs
make doris-restart
make doris-down
```

`doris-up` 只启动 Doris，等待内置健康检查确认 FE 和 BE 均已就绪，然后调用 `infra/scripts/init-doris.sh` 幂等执行：

```sql
CREATE DATABASE IF NOT EXISTS commerce_ai;
```

All-In-One 镜像不使用 MySQL 的 `docker-entrypoint-initdb.d` 初始化约定，因此项目使用显式脚本，不模拟不属于该镜像的 entrypoint 行为。`doris-down` 停止并移除容器与 Compose 网络，但保留数据卷。

### 连接与检查

使用容器内置的 MySQL 协议客户端进入 `commerce_ai`：

```bash
make doris-cli
```

也可以从宿主机客户端连接。密码输入本地 `.env` 中的 `DORIS_ROOT_PASSWORD`；本项目将端口仅绑定到 `127.0.0.1`：

```bash
mysql --host=127.0.0.1 --port=9030 --user=root --password commerce_ai
```

FE Web / HTTP 端口为 `8030`，BE HTTP / Stream Load 端口为 `8040`，MySQL 协议查询端口为 `9030`。运行完整检查：

```bash
docker compose --env-file .env -f infra/compose/compose.doris.yml config --quiet
make doris-check
```

该命令检查容器、FE HTTP 接口、BE 注册与 Alive 状态、`commerce_ai` 数据库以及 `SELECT 1`，任一失败都会返回非零退出码。

### 数据持久化与彻底重置

FE metadata 和 BE storage 分别保存在命名卷 `commerce_ai_doris_fe_meta` 与 `commerce_ai_doris_be_storage`。普通停止和重启不会删除这些卷。

> **Warning：以下命令会永久删除本地 Doris metadata 和全部 Doris 数据，无法通过项目恢复。请先确认其中没有需要保留的数据。** Makefile 不提供默认 reset 命令；只有需要从空环境重新验证时，才手工执行：

```bash
docker compose --env-file .env -f infra/compose/compose.doris.yml down -v
make doris-up
```

## Phase 0 Final Verification

`infra/scripts/verify-phase0.sh` 用于重复执行 Phase 0 最终环境验证。运行前需要 MySQL、Doris 和生成 SQL 均已准备好：

```bash
make mysql-up
make doris-up
infra/scripts/verify-phase0.sh
```

脚本执行以下安全检查：

- 创建独立 MySQL 数据库 `commerce_verify`；如果数据库为空，则应用 `source/mysql/schema.sql` 并真实导入 `source/data-generator/output/generated-data.sql`。
- 如果 `commerce_verify` 已有完整验证数据，则跳过重复导入并重新执行数量和业务一致性检查。
- 如果验证库处于未知或不完整的 schema 状态，则返回非零并停止，不会清表或覆盖数据。
- 在 Doris `commerce_ai` 中创建 `_dev_connection_test`，写入并读回 3 行后，只删除本次由脚本创建的临时表。
- 不修改 `commerce`，不删除任何数据库或 Docker volume。

当前 `small` 数据集已在 MySQL 8.4.11 中完成真实导入，结果如下：

| 表 | 行数 |
| --- | ---: |
| `user_info` | 1,000 |
| `sku_info` | 400 |
| `order_info` | 10,000 |
| `order_detail` | 25,955 |
| `payment_info` | 13,939 |
| `refund_info` | 724 |

订单金额、成功支付、单订单成功支付数量、退款关联、退款支付状态和退款预占上限六项一致性检查的违规数均为 0。Doris 临时表写入、查询和清理也已通过。

`commerce_verify` 默认保留，便于后续复验。只有确认验证数据不再需要时才手工删除：

> **Warning：以下命令会永久删除 `commerce_verify` 及其中的验证数据。它不会删除 `commerce`，但执行前仍需确认数据库名。**

```bash
docker compose --env-file .env -f infra/compose/compose.mysql.yml exec -T mysql \
  sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql --user=root --execute="DROP DATABASE commerce_verify;"'
```

Phase 0 至此完成。下一阶段为 **Phase 1｜Traditional Data Warehouse Modeling**；本阶段未提前创建任何正式 ODS、DIM、DWD、DWS 或 ADS 表。

## 项目目录

```text
commerce-ai-platform/
├── infra/                 # 本地基础设施编排与辅助脚本
├── source/                # MySQL 数据源与事件生成器
├── nifi/                  # NiFi 流程定义
├── flink/                 # Flink CDC 与流处理任务
├── doris/                 # 未来 Phase 的 Doris 分层 DDL 与数据加载
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
