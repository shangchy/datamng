"""给 daily_data 表补充索引（幂等，可重复执行，不影响既有数据）。

用法（Windows 部署目录下，先停止系统）：
    venv\\Scripts\\activate.bat
    python -m app.add_indexes
"""
from sqlalchemy import create_engine, text

from .config import DATABASE_URL

INDEXES = [
    ("idx_daily_data_biz_date", "daily_data", "biz_date"),
    ("idx_daily_data_task_id", "daily_data", "task_id"),
    ("idx_daily_data_phone", "daily_data", "phone"),
]


def main():
    print(f"数据库: {DATABASE_URL}")
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(DATABASE_URL, connect_args=connect_args)
    try:
        with engine.connect() as conn:
            if DATABASE_URL.startswith("sqlite"):
                conn.exec_driver_sql("PRAGMA busy_timeout = 60000")
            for name, table, col in INDEXES:
                sql = f'CREATE INDEX IF NOT EXISTS "{name}" ON "{table}" ("{col}")'
                conn.execute(text(sql))
                print(f"  OK: {name} ({table}.{col})")
            conn.commit()
    finally:
        engine.dispose()
    print("完成，索引已创建（重复执行无副作用）。")


if __name__ == "__main__":
    main()
