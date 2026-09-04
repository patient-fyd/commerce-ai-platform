#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${DORIS_COMPOSE_FILE:-${PROJECT_ROOT}/infra/compose/compose.doris.yml}"
ENV_FILE="${DORIS_ENV_FILE:-${PROJECT_ROOT}/.env}"
TIMEOUT_SECONDS="${DORIS_INIT_TIMEOUT_SECONDS:-180}"

compose() {
  docker compose --project-directory "${PROJECT_ROOT}" --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

container_id="$(compose ps --status running --quiet doris)"
if [[ -z "${container_id}" ]]; then
  echo "[ERROR] Doris 容器未运行，请先执行 make doris-up。" >&2
  exit 1
fi

echo "[WAIT] 等待 Doris FE 与 BE 就绪（最长 ${TIMEOUT_SECONDS} 秒）..."
deadline=$((SECONDS + TIMEOUT_SECONDS))
while (( SECONDS < deadline )); do
  health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_id}")"
  case "${health_status}" in
    healthy)
      break
      ;;
    unhealthy)
      echo "[ERROR] Doris 健康检查失败，请执行 make doris-logs 查看日志。" >&2
      exit 1
      ;;
  esac
  sleep 2
done

health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "${container_id}")"
if [[ "${health_status}" != "healthy" ]]; then
  echo "[ERROR] Doris 未在 ${TIMEOUT_SECONDS} 秒内就绪，当前状态：${health_status}。" >&2
  exit 1
fi

echo "[INIT] 确保 Doris root 密码与本地 .env 一致..."
compose exec -T doris bash -c '
  set -euo pipefail
  : "${DORIS_ROOT_PASSWORD:?DORIS_ROOT_PASSWORD is required}"

  password_sha1="$(printf "%s" "${DORIS_ROOT_PASSWORD}" | sha1sum)"
  password_sha1="${password_sha1%% *}"
  password_sha1_bytes="$(printf "%s" "${password_sha1}" | sed "s/../\\\\x&/g")"
  password_hash="$(printf "%b" "${password_sha1_bytes}" | sha1sum)"
  password_hash="*${password_hash%% *}"
  password_hash="${password_hash^^}"

  printf "SET PASSWORD FOR root = %b%s%b;\n" "\047" "${password_hash}" "\047" \
    | mysql --host=127.0.0.1 --port=9030 --user=root
'

echo "[INIT] 幂等创建 Doris 数据库 commerce_ai..."
compose exec -T doris bash -c '
  MYSQL_PWD="${DORIS_ROOT_PASSWORD}" exec mysql \
    --host=127.0.0.1 \
    --port=9030 \
    --user=root \
    --execute="CREATE DATABASE IF NOT EXISTS commerce_ai;"
'

echo "[OK] Doris root 密码已配置，commerce_ai 数据库已存在。"
