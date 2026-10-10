#!/usr/bin/env bash
# ============================================================
# LM 订单管理系统 · PostgreSQL 一键安装 + 数据迁移（Linux / macOS）
# ============================================================
# 用途：把生产环境从 SQLite 切换到 PostgreSQL。
# 步骤：安装 PostgreSQL -> 创建库/用户 -> 改 .env -> 迁移数据 -> 重启提示
# 用法：bash deploy_postgres.sh
# ============================================================
set -e

# ---- 可配置项 ----
PG_USER="lm"
PG_PASSWORD="lm123456"
PG_DB="lm"
PG_HOST="127.0.0.1"
PG_PORT="5432"
PG_SUPER_USER="postgres"          # 安装后默认存在的超级用户

# 脚本所在目录（仓库根目录）
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
ENV_FILE="$BACKEND/.env"

echo "========== [1/5] 检测 PostgreSQL =========="
if command -v psql >/dev/null 2>&1; then
  echo "已检测到 psql，跳过安装。"
else
  echo "未检测到 psql，开始安装 PostgreSQL ..."
  if command -v brew >/dev/null 2>&1; then
    brew install postgresql@16
    brew services start postgresql@16
    export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y postgresql postgresql-contrib
    sudo service postgresql start
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y postgresql-server
    sudo postgresql-setup --initdb
    sudo systemctl start postgresql
  else
    echo "[错误] 无法识别包管理器，请手动安装 PostgreSQL 后重新运行本脚本。" >&2
    exit 1
  fi
fi

echo "========== [2/5] 创建用户与数据库 =========="
# 以超级用户身份创建业务用户（SUPERUSER 用于数据迁移时禁用外键）
sudo -u "$PG_SUPER_USER" psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$PG_USER') THEN
    CREATE ROLE $PG_USER LOGIN SUPERUSER PASSWORD '$PG_PASSWORD';
  ELSE
    ALTER ROLE $PG_USER WITH LOGIN SUPERUSER PASSWORD '$PG_PASSWORD';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE $PG_DB OWNER $PG_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$PG_DB')\gexec
SQL

echo "========== [3/5] 更新 .env 数据库连接 =========="
DATABASE_URL="postgresql+psycopg2://$PG_USER:$PG_PASSWORD@$PG_HOST:$PG_PORT/$PG_DB"
if [ -f "$ENV_FILE" ]; then
  # 备份旧 .env 并替换 DATABASE_URL
  cp "$ENV_FILE" "$ENV_FILE.bak-$(date +%Y%m%d%H%M%S)"
  if grep -q "^DATABASE_URL=" "$ENV_FILE"; then
    sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$DATABASE_URL|" "$ENV_FILE"
  else
    echo "DATABASE_URL=$DATABASE_URL" >> "$ENV_FILE"
  fi
else
  echo "DATABASE_URL=$DATABASE_URL" > "$ENV_FILE"
fi
echo "已写入：$DATABASE_URL"

echo "========== [4/5] 安装依赖并迁移数据 =========="
cd "$BACKEND"
# 确保 psycopg2 驱动存在
if [ -f ".venv/bin/pip" ]; then
  .venv/bin/pip install -q psycopg2-binary 2>/dev/null || true
  .venv/bin/python migrate_sqlite_to_pg.py
else
  pip install -q psycopg2-binary 2>/dev/null || true
  python migrate_sqlite_to_pg.py
fi

echo "========== [5/5] 完成 =========="
echo "数据已迁移到 PostgreSQL。请重启后端服务："
echo "  cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "（验证无误后可删除旧 SQLite 文件 backend/data/lm.db）"
