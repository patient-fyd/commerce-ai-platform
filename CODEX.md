# CommerceAI Codex Rules

## 1. Project Purpose

CommerceAI 是一个长期学习型 AI Data Engineering 项目。

最终目标：

```text
MySQL / Event Generator
→ NiFi
→ Kafka
→ Flink
→ Doris
→ dbt
→ Semantic Layer
→ Metadata / Lineage
→ RAG
→ Data Agent
→ Evaluation / Governance
```

项目按照 Phase 0 - Phase 9 逐步实现。

禁止提前实现尚未进入的 Phase。

---

## 2. Learning First

AI 用于提高工程效率，而不是隐藏技术原理。

当实现涉及以下内容时：

- 数据模型
- 表模型
- Flink 状态
- Watermark
- Materialized View
- Metric
- Semantic Model
- RAG
- Agent

必须在实现结果中解释：

1. 它解决什么问题
2. 为什么项目需要它
3. 为什么采用当前方案
4. 是否存在其他方案

不要只输出代码。

---

## 3. Environment Constraints

本项目主要开发环境：

- macOS
- Apple Silicon M4
- 24GB RAM
- Docker Desktop

所有基础设施必须优先考虑：

- ARM64 compatibility
- 低资源占用
- 单节点开发环境
- 服务可以独立启动和关闭

禁止为了模拟生产环境而默认部署多节点集群。

不要默认同时启动所有基础设施组件。

---

## 4. Scope Control

每个任务必须严格遵守当前用户指定的 Scope。

禁止：

- 顺手实现未来 Phase
- 修改无关文件
- 无必要重构
- 无必要增加框架
- 无必要增加基础设施
- 无必要引入新的依赖

如果发现现有架构存在问题：

先报告问题和建议，不要擅自大规模修改。

---

## 5. Dependency Rules

引入新依赖之前必须说明：

- dependency name
- purpose
- why it is needed
- alternatives
- resource / maintenance cost

优先使用简单方案。

不要为了“架构完整”引入当前阶段实际上不需要的组件。

---

## 6. Security

禁止硬编码：

- password
- API key
- token
- credential
- private endpoint

禁止提交：

- `.env`
- 真实数据库数据
- 敏感日志
- 密钥文件

所有配置示例使用：

- `.env.example`
- 或其他 example 配置文件

---

## 7. Data Warehouse Modeling

禁止机械创建 ODS / DWD / DIM / DWS / ADS。

创建事实表时必须说明：

- Business Process
- Grain
- Primary / Unique Key
- Dimensions
- Measures
- Source
- Important Assumptions

创建维度表时必须说明：

- Business Entity
- Grain
- Natural Key
- Surrogate Key（如果使用）
- SCD Strategy（如果需要）

SQL 文件建议在头部保留相应说明。

---

## 8. Metric Rules

定义 Metric 时必须记录：

- Metric Name
- Business Definition
- Formula
- Source Measure
- Time Field
- Supported Dimensions
- Filters
- Null Handling
- Grain
- Example

禁止仅仅写 SQL 而不定义业务口径。

---

## 9. Infrastructure

Docker 服务必须：

- 独立 Compose
- 可以独立启动
- 可以独立关闭
- 有 healthcheck（组件支持时）
- 有持久化方案（需要持久化时）
- 不默认和未来组件绑定

目录：

```text
infra/compose/
```

不同基础设施尽量使用独立 compose 文件。

---

## 10. Code Quality

保持：

- clear naming
- small modules
- minimal abstraction
- explicit configuration
- reproducible execution

不要为了设计模式而设计模式。

---

## 11. Documentation Synchronization

如果实现改变：

- Architecture
- Data Model
- Development Command
- Infrastructure
- Metric
- Public API

必须检查是否需要同步更新：

- `README.md`
- `docs/`

但不要为了小改动机械修改所有文档。

---

## 12. Git

除非用户明确要求：

- 禁止自动执行 `git commit`
- 禁止自动执行 `git push`
- 禁止修改 Git 历史

每个任务完成后推荐一个 Conventional Commit message。

格式优先：

- `feat:`
- `fix:`
- `docs:`
- `test:`
- `refactor:`
- `chore:`

---

## 13. Completion Report

每次工程任务结束后必须报告：

### Files Changed

列出新增和修改文件。

### Design Decisions

说明关键设计决定。

### How to Run

给出运行方法。

### How to Verify

给出验证步骤。

### Resource Impact

如果涉及基础设施，说明大概资源影响。

### Remaining Issues

说明未完成或需要后续验证的内容。

### Suggested Commit

给出推荐 commit message。

---

## 14. Important Principle

项目目标不是堆砌：

```text
NiFi + Kafka + Flink + Doris + dbt + LLM
```

而是理解每一个组件解决的问题，以及它们如何组成完整的数据架构。

当前阶段未使用某项技术时，不要为了最终架构提前引入。
