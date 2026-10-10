#!/usr/bin/env bash
# ============================================================
# LM 订单管理系统 · PostgreSQL 版并行服务（Linux / macOS）
# 原服务（SQLite）：端口 8000；本服务（PostgreSQL）：端口 8001
# 用法：先迁移数据，再运行本脚本验证。
# ============================================================
set -e
cd "$(dirname "$0")/backend"

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://lm:lm123456@127.0.0.1:5432/lm}"
export PORT="${PORT:-8001}"

if [ -f ".venv/bin/python" ]; then
  PY=".venv/bin/python"
else
  PY="python"
fi

echo "启动 PostgreSQL 版服务（并行验证）"
echo "访问地址: http://127.0.0.1:$PORT"
echo "数据库: PostgreSQL"
echo
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
