#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${ENV_FILE:-${PROJECT_ROOT}/.env}"
MYSQL_COMPOSE_FILE="${MYSQL_COMPOSE_FILE:-${PROJECT_ROOT}/infra/compose/compose.mysql.yml}"
DORIS_COMPOSE_FILE="${DORIS_COMPOSE_FILE:-${PROJECT_ROOT}/infra/compose/compose.doris.yml}"
SCHEMA_FILE="${SCHEMA_FILE:-${PROJECT_ROOT}/source/mysql/schema.sql}"
DATA_FILE="${DATA_FILE:-${PROJECT_ROOT}/source/data-generator/output/generated-data.sql}"
VERIFY_DATABASE="commerce_verify"
DORIS_DATABASE="commerce_ai"
DORIS_TABLE="_dev_connection_test"

MYSQL_COMPOSE=(docker compose --project-directory "${PROJECT_ROOT}" --env-file "${ENV_FILE}" -f "${MYSQL_COMPOSE_FILE}")
DORIS_COMPOSE=(docker compose --project-directory "${PROJECT_ROOT}" --env-file "${ENV_FILE}" -f "${DORIS_COMPOSE_FILE}")
DORIS_TABLE_CREATED=false

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

mysql_root() {
  "${MYSQL_COMPOSE[@]}" exec -T mysql sh -c '
    MYSQL_PWD="${MYSQL_ROOT_PASSWORD}" exec mysql \
      --default-character-set=utf8mb4 \
      --user=root \
      "$@"
  ' sh "$@"
}

mysql_value() {
  mysql_root --batch --skip-column-names "${VERIFY_DATABASE}" --execute="$1" | tr -d '\r'
}

doris_root() {
  "${DORIS_COMPOSE[@]}" exec -T doris bash -c '
    MYSQL_PWD="${DORIS_ROOT_PASSWORD}" exec mysql \
      --host=127.0.0.1 \
      --port=9030 \
      --user=root \
      "$@"
  ' bash "$@"
}

doris_value() {
  doris_root --batch --skip-column-names --execute="$1" | tr -d '\r'
}

cleanup_doris_table() {
  if [[ "${DORIS_TABLE_CREATED}" == true ]]; then
    echo "[CLEANUP] 删除本次创建的 Doris 临时表 ${DORIS_DATABASE}.${DORIS_TABLE}..."
    if doris_root --execute="DROP TABLE ${DORIS_DATABASE}.${DORIS_TABLE};"; then
      DORIS_TABLE_CREATED=false
      echo "          OK - Doris 临时表已删除"
    else
      echo "[WARN] Doris 临时表清理失败，请手工检查 ${DORIS_DATABASE}.${DORIS_TABLE}。" >&2
    fi
  fi
}

assert_zero() {
  local label="$1"
  local query="$2"
  local violations
  violations="$(mysql_value "${query}")" || fail "${label} 查询执行失败。"
  if [[ "${violations}" != "0" ]]; then
    fail "${label}：发现 ${violations} 条违规记录。"
  fi
  printf "       OK - %-42s violations=%s\n" "${label}" "${violations}"
}

trap cleanup_doris_table EXIT

echo "============================================================"
echo " CommerceAI Phase 0 Final Verification"
echo "============================================================"

[[ -f "${ENV_FILE}" ]] || fail "缺少本地环境文件：${ENV_FILE}"
[[ -f "${SCHEMA_FILE}" ]] || fail "缺少 MySQL schema：${SCHEMA_FILE}"
[[ -f "${DATA_FILE}" ]] || fail "缺少生成 SQL：${DATA_FILE}"

mysql_container_id="$("${MYSQL_COMPOSE[@]}" ps --status running --quiet mysql)"
[[ -n "${mysql_container_id}" ]] || fail "MySQL 容器未运行，请先执行 make mysql-up。"

doris_container_id="$("${DORIS_COMPOSE[@]}" ps --status running --quiet doris)"
[[ -n "${doris_container_id}" ]] || fail "Doris 容器未运行，请先执行 make doris-up。"

echo "[MYSQL] 准备独立验证数据库 ${VERIFY_DATABASE}..."
mysql_root --execute="CREATE DATABASE IF NOT EXISTS ${VERIFY_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"

table_count="$(mysql_value "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '${VERIFY_DATABASE}';")"
expected_table_count="$(mysql_value "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '${VERIFY_DATABASE}' AND TABLE_NAME IN ('user_info', 'category_info', 'spu_info', 'sku_info', 'order_info', 'order_detail', 'payment_info', 'refund_info');")"

if [[ "${table_count}" == "0" ]]; then
  echo "        应用 source/mysql/schema.sql..."
  mysql_root "${VERIFY_DATABASE}" < "${SCHEMA_FILE}"
  table_count="$(mysql_value "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = '${VERIFY_DATABASE}';")"
  expected_table_count="${table_count}"
fi

[[ "${table_count}" == "8" && "${expected_table_count}" == "8" ]] \
  || fail "${VERIFY_DATABASE} 不是预期的 8 张空/已验证源表；为保护现有数据，停止执行。"

total_source_rows="$(mysql_value 'SELECT
  (SELECT COUNT(*) FROM user_info) +
  (SELECT COUNT(*) FROM category_info) +
  (SELECT COUNT(*) FROM spu_info) +
  (SELECT COUNT(*) FROM sku_info) +
  (SELECT COUNT(*) FROM order_info) +
  (SELECT COUNT(*) FROM order_detail) +
  (SELECT COUNT(*) FROM payment_info) +
  (SELECT COUNT(*) FROM refund_info);')"

if [[ "${total_source_rows}" == "0" ]]; then
  echo "        导入 source/data-generator/output/generated-data.sql..."
  mysql_root "${VERIFY_DATABASE}" < "${DATA_FILE}"
  echo "        OK - synthetic SQL 已真实导入 MySQL 8.4"
else
  echo "        INFO - ${VERIFY_DATABASE} 已有数据，跳过重复导入并重新执行全部验证"
fi

echo "[MYSQL] 实际行数："
mysql_root --table "${VERIFY_DATABASE}" --execute='
  SELECT "user_info" AS table_name, COUNT(*) AS row_count FROM user_info
  UNION ALL SELECT "sku_info", COUNT(*) FROM sku_info
  UNION ALL SELECT "order_info", COUNT(*) FROM order_info
  UNION ALL SELECT "order_detail", COUNT(*) FROM order_detail
  UNION ALL SELECT "payment_info", COUNT(*) FROM payment_info
  UNION ALL SELECT "refund_info", COUNT(*) FROM refund_info;'

echo "[MYSQL] 业务一致性："
assert_zero "order_amount = SUM(order_detail.line_amount)" '
  SELECT COUNT(*) FROM (
    SELECT o.order_id
    FROM order_info AS o
    LEFT JOIN order_detail AS d ON d.order_id = o.order_id
    GROUP BY o.order_id, o.order_amount
    HAVING COUNT(d.order_detail_id) = 0 OR o.order_amount <> SUM(d.line_amount)
  ) AS violations;'

assert_zero "成功支付金额 = order_amount" '
  SELECT COUNT(*)
  FROM payment_info AS p
  JOIN order_info AS o ON o.order_id = p.order_id
  WHERE p.payment_status = 20
    AND p.payment_amount <> o.order_amount;'

assert_zero "同一订单最多一笔成功支付" '
  SELECT COUNT(*) FROM (
    SELECT order_id
    FROM payment_info
    WHERE payment_status = 20
    GROUP BY order_id
    HAVING COUNT(*) > 1
  ) AS violations;'

assert_zero "refund 的 order/detail/payment 属于同一订单" '
  SELECT COUNT(*)
  FROM refund_info AS r
  LEFT JOIN order_detail AS d ON d.order_detail_id = r.order_detail_id
  LEFT JOIN payment_info AS p ON p.payment_id = r.payment_id
  WHERE d.order_detail_id IS NULL
     OR p.payment_id IS NULL
     OR d.order_id <> r.order_id
     OR p.order_id <> r.order_id;'

assert_zero "refund payment 必须成功" '
  SELECT COUNT(*)
  FROM refund_info AS r
  LEFT JOIN payment_info AS p ON p.payment_id = r.payment_id
  WHERE p.payment_id IS NULL OR p.payment_status <> 20;'

assert_zero "reserved refund 不超过明细数量/金额" '
  SELECT COUNT(*) FROM (
    SELECT d.order_detail_id
    FROM order_detail AS d
    JOIN refund_info AS r ON r.order_detail_id = d.order_detail_id
    WHERE r.refund_status IN (10, 20)
    GROUP BY d.order_detail_id, d.quantity, d.line_amount
    HAVING SUM(r.refund_quantity) > d.quantity
        OR SUM(r.refund_amount) > d.line_amount
  ) AS violations;'

echo "[DORIS] 创建临时连通性表 ${DORIS_DATABASE}.${DORIS_TABLE}..."
existing_doris_table="$(doris_value "SHOW TABLES FROM ${DORIS_DATABASE} LIKE '${DORIS_TABLE}';")"
[[ -z "${existing_doris_table}" ]] \
  || fail "Doris 临时表 ${DORIS_DATABASE}.${DORIS_TABLE} 已存在；为避免误删，停止执行。"

doris_root --execute="
  CREATE TABLE ${DORIS_DATABASE}.${DORIS_TABLE} (
    id INT,
    name VARCHAR(64),
    created_at DATETIME
  )
  DUPLICATE KEY(id)
  DISTRIBUTED BY HASH(id) BUCKETS 1
  PROPERTIES ('replication_num' = '1');"
DORIS_TABLE_CREATED=true

doris_root --execute="
  INSERT INTO ${DORIS_DATABASE}.${DORIS_TABLE} VALUES
    (1, 'mysql-source-ready', NOW()),
    (2, 'doris-write-ready', NOW()),
    (3, 'phase0-verified', NOW());"

doris_row_count="$(doris_value "SELECT COUNT(*) FROM ${DORIS_DATABASE}.${DORIS_TABLE};")"
[[ "${doris_row_count}" == "3" ]] || fail "Doris 临时表期望 3 行，实际为 ${doris_row_count}。"
echo "        OK - Doris 写入成功，查询返回 ${doris_row_count} 行"
doris_root --table --execute="SELECT id, name, created_at FROM ${DORIS_DATABASE}.${DORIS_TABLE} ORDER BY id;"

cleanup_doris_table
remaining_doris_table="$(doris_value "SHOW TABLES FROM ${DORIS_DATABASE} LIKE '${DORIS_TABLE}';")"
[[ -z "${remaining_doris_table}" ]] || fail "Doris 临时表清理后仍然存在。"

echo "============================================================"
echo " PASS - Phase 0 最终环境验证全部通过"
echo " INFO - MySQL ${VERIFY_DATABASE} 已保留，不会自动删除"
echo "============================================================"
