.PHONY: help mysql-up mysql-down mysql-restart mysql-logs mysql-status mysql-cli generate-data import-generated-data

MYSQL_COMPOSE_FILE ?= infra/compose/compose.mysql.yml
MYSQL_ENV_FILE ?= .env
MYSQL_COMPOSE = docker compose --env-file $(MYSQL_ENV_FILE) -f $(MYSQL_COMPOSE_FILE)
SCALE ?= small
SEED ?= 42
START_DATE ?= 2026-01-01
END_DATE ?= 2026-03-31
DATA_OUTPUT ?= source/data-generator/output/generated-data.sql

help: ## 显示当前可用命令
	@echo "CommerceAI Platform - Phase 0 Local Data Foundation"
	@echo ""
	@echo "可用命令："
	@echo "  make help           显示此帮助信息"
	@echo "  make mysql-up       启动本地 MySQL"
	@echo "  make mysql-down     停止本地 MySQL（保留数据卷）"
	@echo "  make mysql-restart  重启本地 MySQL"
	@echo "  make mysql-logs     持续查看 MySQL 日志"
	@echo "  make mysql-status   查看 MySQL 容器状态"
	@echo "  make mysql-cli      使用应用账号进入 commerce 数据库"
	@echo "  make generate-data  生成可重复的模拟电商 SQL 数据"
	@echo "  make import-generated-data  将生成的 SQL 导入空的 commerce 数据库"

generate-data: ## 生成模拟电商 SQL 数据；可覆盖 SCALE、SEED、START_DATE、END_DATE、DATA_OUTPUT
	@python3 source/data-generator/generate.py --scale "$(SCALE)" --seed "$(SEED)" --start-date "$(START_DATE)" --end-date "$(END_DATE)" --output "$(DATA_OUTPUT)"

import-generated-data: ## 将 DATA_OUTPUT 导入当前空的 commerce 数据库
	@test -f "$(DATA_OUTPUT)" || { echo "未找到生成文件：$(DATA_OUTPUT)，请先执行 make generate-data"; exit 1; }
	@$(MYSQL_COMPOSE) exec -T mysql sh -c 'MYSQL_PWD="$${MYSQL_PASSWORD}" exec mysql --default-character-set=utf8mb4 --user="$${MYSQL_USER}" "$${MYSQL_DATABASE}"' < "$(DATA_OUTPUT)"
	@echo "已将 $(DATA_OUTPUT) 导入 MySQL。"

mysql-up: ## 启动本地 MySQL
	@$(MYSQL_COMPOSE) up -d

mysql-down: ## 停止本地 MySQL，但保留数据卷
	@$(MYSQL_COMPOSE) down

mysql-restart: ## 重启本地 MySQL
	@$(MYSQL_COMPOSE) restart mysql

mysql-logs: ## 持续查看 MySQL 日志
	@$(MYSQL_COMPOSE) logs -f mysql

mysql-status: ## 查看 MySQL 容器状态
	@$(MYSQL_COMPOSE) ps mysql

mysql-cli: ## 使用应用账号进入 commerce 数据库
	@$(MYSQL_COMPOSE) exec mysql sh -c 'MYSQL_PWD="$${MYSQL_PASSWORD}" exec mysql --default-character-set=utf8mb4 --user="$${MYSQL_USER}" "$${MYSQL_DATABASE}"'
