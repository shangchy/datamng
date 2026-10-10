@echo off
chcp 65001 >nul
REM ============================================================
REM  LM 订单管理系统 · PostgreSQL 一键安装 + 数据迁移（Windows）
REM ============================================================
REM  步骤：安装 PostgreSQL -> 创建库/用户 -> 改 .env -> 迁移数据
REM  前提：本脚本需放在部署包根目录（与 app/、run.bat 同级）
REM ============================================================

setlocal EnableDelayedExpansion
set PG_USER=lm
set PG_PASSWORD=lm123456
set PG_DB=lm
set PG_HOST=127.0.0.1
set PG_PORT=5432

echo ========== [1/5] 检测 PostgreSQL ==========
where psql >nul 2>nul
if errorlevel 1 (
  echo 未检测到 psql，尝试用 Chocolatey 安装...
  where choco >nul 2>nul
  if errorlevel 1 (
    echo [提示] 未安装 Chocolatey。
    echo 请任选其一安装 PostgreSQL：
    echo   1) 官方安装包：https://www.enterprisedb.com/downloads/postgresql-postgresql-downloads
    echo      安装时设置超级用户 postgres 的密码，并记下端口 5432。
    echo   2) 先装 Chocolatey 再重跑本脚本：https://chocolatey.org/install
    echo 安装完成后，重新运行本脚本即可。
    pause
    exit /b 1
  )
  choco install postgresql -y
  echo PostgreSQL 已安装。如果服务未自动启动，请在「服务」里启动 postgresql-x64-* 后重跑。
)

echo ========== [2/5] 创建用户与数据库 ==========
REM 以超级用户 postgres 身份执行（首次会提示输入 postgres 密码）
psql -U postgres -h %PG_HOST% -p %PG_PORT% -v ON_ERROR_STOP=1 -c "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='%PG_USER%') THEN CREATE ROLE %PG_USER% LOGIN SUPERUSER PASSWORD '%PG_PASSWORD%'; ELSE ALTER ROLE %PG_USER% WITH LOGIN SUPERUSER PASSWORD '%PG_PASSWORD%'; END IF; END \$\$;"
psql -U postgres -h %PG_HOST% -p %PG_PORT% -v ON_ERROR_STOP=1 -c "SELECT 'CREATE DATABASE %PG_DB% OWNER %PG_USER%' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='%PG_DB%')\gexec"

echo ========== [3/5] 更新 .env ==========
set DATABASE_URL=postgresql+psycopg2://%PG_USER%:%PG_PASSWORD%@%PG_HOST%:%PG_PORT%/%PG_DB%
if exist .env (
  copy /Y .env .env.bak >nul
  findstr /B "DATABASE_URL=" .env >nul
  if errorlevel 1 (
    echo DATABASE_URL=%DATABASE_URL%>> .env
  ) else (
    powershell -NoProfile -Command "(Get-Content .env) -replace '^DATABASE_URL=.*', 'DATABASE_URL=%DATABASE_URL%' | Set-Content .env"
  )
) else (
  echo DATABASE_URL=%DATABASE_URL%> .env
)
echo 已写入：%DATABASE_URL%

echo ========== [4/5] 安装依赖并迁移数据 ==========
if exist venv\Scripts\python.exe (
  set PY=venv\Scripts\python.exe
) else (
  set PY=python
)
%PY% -m pip install -q psycopg2-binary
%PY% migrate_sqlite_to_pg.py

echo ========== [5/5] 完成 ==========
echo 数据已迁移到 PostgreSQL。请双击 run.bat 启动系统。
echo （验证无误后可删除旧的 backend\data\lm.db 或 data\lm.db）
pause
endlocal
