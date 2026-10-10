#!/usr/bin/env python3
"""
LM 订单管理系统 · SQLite -> PostgreSQL 数据迁移脚本

用法（在 backend/ 目录下运行）：
    python migrate_sqlite_to_pg.py

可通过环境变量覆盖连接串：
    SRC_DB_URL  源库（SQLite），默认 sqlite:///./data/lm.db
    DST_DB_URL  目标库（PostgreSQL），默认 postgresql+psycopg2://lm:lm123456@127.0.0.1:5432/lm

说明：
    1. 先在目标 PostgreSQL 按 models.py 建好表结构（create_all）。
    2. 按外键依赖拓扑排序后逐表复制数据（保留自增 id）。
    3. 迁移完成后重置各表自增序列（否则新插入会主键冲突）。

注意事项：
    - 迁移前请备份源 SQLite 文件。
    - 源库表结构会通过 SQLAlchemy 反射自动读取，兼容不同版本。
"""
import os
import sys
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from sqlalchemy import create_engine, MetaData, Table, select, text

SRC_DB_URL = os.getenv("SRC_DB_URL", "sqlite:///./data/lm.db")
DST_DB_URL = os.getenv("DST_DB_URL", "postgresql+psycopg2://lm:lm123456@127.0.0.1:5432/lm")


def _topo_order(tables):
    """按外键依赖做拓扑排序，被依赖的表先插入"""
    deps = defaultdict(set)
    for name, table in tables.items():
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            if parent != name and parent in tables:
                deps[name].add(parent)
    ordered = []
    visiting = set()
    done = set()

    def visit(n):
        if n in done:
            return
        if n in visiting:
            return  # 自引用/环，跳过（category.parent_id 自引用）
        visiting.add(n)
        for p in sorted(deps[n]):
            visit(p)
        visiting.discard(n)
        done.add(n)
        ordered.append(n)

    for n in sorted(tables.keys()):
        visit(n)
    return ordered


def _reset_sequences(conn):
    """重置各表自增序列，避免迁移后新插入主键冲突"""
    rows = conn.execute(text("""
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE column_default LIKE 'nextval%'
          AND table_schema = 'public'
    """)).fetchall()
    for table_name, column_name in rows:
        conn.execute(text(
            f'SELECT setval(pg_get_serial_sequence(\'{table_name}\', \'{column_name}\'), '
            f'COALESCE((SELECT MAX("{column_name}") FROM "{table_name}"), 1), true)'
        ))
    print(f"[序列] 已重置 {len(rows)} 个自增序列")


def main():
    src = create_engine(SRC_DB_URL)
    dst = create_engine(DST_DB_URL)

    # 1. 目标库建表
    from app.models import Base
    Base.metadata.create_all(dst)
    print("[结构] 目标库建表完成")

    # 2. 反射源库（SQLite）表结构
    src_meta = MetaData()
    src_meta.reflect(bind=src)
    src_tables = {k: v for k, v in src_meta.tables.items() if not k.startswith("sqlite_")}
    print(f"[源库] 共 {len(src_tables)} 张表")

    # 3. 按拓扑顺序复制数据
    order = _topo_order(src_tables)
    total = 0
    with dst.begin() as conn:
        # 若当前用户是 superuser，则额外禁用外键约束（双保险）
        is_super = conn.execute(text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user")).scalar()
        if is_super:
            conn.execute(text("SET session_replication_role = 'replica'"))
        else:
            print("[提示] 当前用户非 SUPERUSER，将仅依赖外键拓扑顺序插入")

        for name in order:
            t = src_tables[name]
            with src.connect() as sc:
                rows = sc.execute(select(t)).fetchall()
            if not rows:
                continue
            cols = [c.name for c in t.columns]
            data = [dict(zip(cols, row)) for row in rows]
            dst_t = Table(name, MetaData(), autoload_with=dst)
            conn.execute(dst_t.insert(), data)
            total += len(data)
            print(f"  {name}: {len(data)} 行")

        if is_super:
            conn.execute(text("SET session_replication_role = 'origin'"))

        _reset_sequences(conn)

    print(f"\n迁移完成，共 {total} 行")


if __name__ == "__main__":
    main()
