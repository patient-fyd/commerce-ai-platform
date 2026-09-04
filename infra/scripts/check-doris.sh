#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${DORIS_COMPOSE_FILE:-${PROJECT_ROOT}/infra/compose/compose.doris.yml}"
ENV_FILE="${DORIS_ENV_FILE:-${PROJECT_ROOT}/.env}"

compose() {
  docker compose --project-directory "${PROJECT_ROOT}" --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

sql_value() {
  compose exec -T doris bash -c '
    MYSQL_PWD="${DORIS_ROOT_PASSWORD}" exec mysql \
      --batch \
      --skip-column-names \
      --host=127.0.0.1 \
      --port=9030 \
      --user=root \
      --execute="${1}"
  ' bash "$1" 2>/dev/null | tr -d '\r'
}

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

echo "========================================"
echo " CommerceAI Doris Local Check"
echo "========================================"

echo "[1/5] 检查 Docker 容器..."
container_id="$(compose ps --status running --quiet doris)"
[[ -n "${container_id}" ]] || fail "Doris 容器未运行。"
container_name="$(docker inspect --format '{{.Name}}' "${container_id}" | sed 's#^/##')"
echo "       OK - ${container_name} 正在运行"

echo "[2/5] 检查 Doris FE HTTP 接口..."
fe_endpoint="$(compose port doris 8030)" || fail "无法读取 FE HTTP 端口映射。"
[[ -n "${fe_endpoint}" ]] || fail "FE HTTP 端口未映射到宿主机。"
health_response="$(curl --fail --silent --show-error --max-time 5 \
  "http://${fe_endpoint}/api/health")" || fail "FE HTTP 接口不可访问。"
[[ -n "${health_response}" ]] || fail "FE HTTP 接口返回空响应。"
echo "       OK - http://${fe_endpoint}/api/health"

echo "[3/5] 检查 BE 注册与 Alive 状态..."
backend_count="$(sql_value 'SELECT COUNT(*) FROM backends();')" \
  || fail "无法查询 BE 列表。"
alive_backend_count="$(sql_value 'SELECT COUNT(*) FROM backends() WHERE Alive = 1;')" \
  || fail "无法查询 BE Alive 状态。"
[[ "${backend_count}" == "1" ]] || fail "期望注册 1 个 BE，实际为 ${backend_count}。"
[[ "${alive_backend_count}" == "1" ]] || fail "已注册 BE 未处于 Alive 状态。"
echo "       OK - 1 个 BE 已注册且 Alive"

echo "[4/5] 检查 commerce_ai 数据库..."
database_name="$(sql_value "SHOW DATABASES LIKE 'commerce_ai';")" \
  || fail "无法查询数据库列表。"
[[ "${database_name}" == "commerce_ai" ]] || fail "commerce_ai 数据库不存在。"
echo "       OK - commerce_ai 存在"

echo "[5/5] 执行 SELECT 1..."
select_result="$(sql_value 'SELECT 1;')" || fail "SELECT 1 执行失败。"
[[ "${select_result}" == "1" ]] || fail "SELECT 1 返回异常结果：${select_result}"
echo "       OK - SELECT 1 返回 1"

echo "========================================"
echo " PASS - Doris 基础环境检查全部通过"
echo "========================================"
