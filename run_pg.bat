@echo off
chcp 65001 >nul
cd /d %~dp0
REM ============================================================
REM  LM 订单管理系统 · PostgreSQL 版并行服务（不影响原 SQLite 服务）
REM  原服务：run.bat，端口 8000，SQLite
REM  本服务：run_pg.bat，端口 8001，PostgreSQL（环境变量覆盖 DATABASE_URL）
REM  用法：先迁移数据，再运行本脚本验证，验证无误后再切换。
REM ============================================================

set DATABASE_URL=postgresql+psycopg2://lm:lm123456@127.0.0.1:5432/lm
set PORT=8001

REM 首次运行创建虚拟环境
if not exist venv (
  echo 正在创建虚拟环境，请稍候...
  python -m venv venv
)
call venv\Scripts\activate.bat

echo 正在检查依赖...
python -m pip install -q -r requirements.txt

echo.
echo 启动 PostgreSQL 版服务（并行验证）
echo 访问地址: http://127.0.0.1:%PORT%
echo 数据库: PostgreSQL（lm 库）
echo 按 Ctrl+C 停止
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%
pause
