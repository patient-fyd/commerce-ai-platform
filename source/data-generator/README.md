# CommerceAI Data Generator

这个生成器为 Phase 0 的 MySQL OLTP 模型提供稳定、可重复的虚构电商数据，供后续的数据采集、建模、指标和流处理练习使用。它只依赖 Python 3 标准库，生成 SQL 文件，不直接连接数据库。

## 数据范围与业务场景

`small` 是当前唯一实现的规模：约 1,000 个用户、20 个分类、150 个 SPU、400 个 SKU、10,000 张订单和 20,000–30,000 条订单明细。支付与退款数量由订单状态和业务概率决定。

生成器覆盖：

- 待支付、已支付、已完成和已取消订单。
- 首次支付成功、失败后成功、多次失败、待处理和关闭的支付尝试。
- WECHAT、ALIPAY、BANK_CARD 三种支付渠道，且每次尝试支付完整订单金额。
- 无退款、全额退款、部分退款、同一明细多次部分退款，以及待处理、成功、失败和取消退款。
- 热门 SKU、高活跃用户、分类热度差异、周末权重和非均匀支付渠道。

所有用户资料都明显标记为 synthetic，例如 `user000001@example.test`、`Synthetic User 000001` 和以 `000` 开头的无效模拟号码，不使用真实个人数据。

## 可重复性

相同的 `--seed`、`--scale`、`--start-date` 和 `--end-date` 会生成逐字节相同的 SQL。生成摘要会输出 SHA-256，便于比较两次结果。当前只接受 `small`；`medium` 和 `large` 留待确有学习需求时实现。

## 生成

从仓库根目录运行：

```bash
python3 source/data-generator/generate.py \
  --scale small \
  --seed 42 \
  --start-date 2026-01-01 \
  --end-date 2026-03-31 \
  --output source/data-generator/output/generated-data.sql
```

或使用 Make：

```bash
make generate-data
make generate-data SCALE=small SEED=42 START_DATE=2026-01-01 END_DATE=2026-03-31
```

查看全部参数：

```bash
python3 source/data-generator/generate.py --help
```

`output/` 已被 Git 忽略。生成器先在内存中完成业务校验，再原子替换目标文件；校验或写入失败时不会留下半成品目标 SQL。

## 导入 MySQL

SQL 使用显式主键以保证结果可重复，因此必须导入已经执行 `source/mysql/schema.sql` 且没有现有业务数据的 `commerce` 数据库。MySQL Compose 在新数据卷第一次启动时只初始化 schema，不自动执行 `source/mysql/seed.sql`。

```bash
make mysql-up
make generate-data
make import-generated-data
```

`import-generated-data` 使用 `.env` 中的数据库名和应用账号，将 `DATA_OUTPUT` 导入当前数据库。它不会自动清表；重复导入会因主键和唯一键冲突而失败。如果数据库已有数据，需要明确确认数据可以丢弃后删除 Compose 数据卷并重新初始化。

## 校验

每次生成都会在写文件前检查：

- 订单金额等于明细金额之和，明细金额等于单价乘数量。
- 支付引用正确订单、尝试序号连续、每单最多一笔成功支付，且每次支付尝试金额等于订单金额。
- 退款的订单、明细和成功支付属于同一订单。
- 待处理与成功退款的累计预占数量和金额不超过原订单明细。
- 下单、支付、退款和对应终态时间顺序正确。
- 所有指定订单、支付、退款状态、渠道和关键重试/部分退款场景均存在。

成功时命令输出 `verification: passed`。导入后可额外执行：

```sql
SELECT o.order_id
FROM order_info AS o
JOIN (
    SELECT order_id, SUM(line_amount) AS detail_amount
    FROM order_detail
    GROUP BY order_id
) AS d ON d.order_id = o.order_id
WHERE o.order_amount <> d.detail_amount;

SELECT order_id
FROM payment_info
WHERE payment_status = 20
GROUP BY order_id
HAVING COUNT(*) > 1;

SELECT d.order_detail_id
FROM order_detail AS d
JOIN refund_info AS r ON r.order_detail_id = d.order_detail_id
WHERE r.refund_status IN (10, 20)
GROUP BY d.order_detail_id, d.quantity, d.line_amount
HAVING SUM(r.refund_quantity) > d.quantity
    OR SUM(r.refund_amount) > d.line_amount;
```

三个查询都应返回空结果。

## 本地资源预期

`small` 面向 Mac M4 / 24GB RAM 的本地开发。它是单进程、无并发实现；10,000 张订单只需数秒和几十 MB 级内存，输出 SQL 通常为数 MB。数据规模刻意保持在适合反复生成、导入和查询的范围内。
