"""数据库自动备份"""
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from .config import DATABASE_URL, BASE_DIR


def _backup_dir() -> Path:
    d = Path(BASE_DIR) / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def backup_database(keep_days=7):
    """执行一次数据库备份，返回备份文件路径"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    d = _backup_dir()
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.split("///", 1)[1]
        src = Path(db_path)
        dest = d / f"backup_{ts}.sqlite3"
        src_conn = sqlite3.connect(str(src))
        try:
            dst_conn = sqlite3.connect(str(dest))
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
        finally:
            src_conn.close()
    else:
        # PostgreSQL：用 pg_dump 导出
        from sqlalchemy.engine.url import make_url
        url = make_url(DATABASE_URL)
        dest = d / f"backup_{ts}.sql"
        cmd = ["pg_dump", "-h", url.host or "127.0.0.1",
               "-p", str(url.port or 5432),
               "-U", url.username or "", "-d", url.database or ""]
        env = os.environ.copy()
        if url.password:
            env["PGPASSWORD"] = url.password
        with open(dest, "wb") as f:
            subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env, check=True)
    cleanup_old_backups(d, keep_days)
    return dest


def cleanup_old_backups(d: Path = None, keep_days: int = 7):
    """仅保留近 N 天的备份文件"""
    d = d or _backup_dir()
    try:
        keep_days = int(keep_days)
    except (TypeError, ValueError):
        keep_days = 7
    cutoff = datetime.now() - timedelta(days=keep_days)
    for f in d.glob("backup_*"):
        try:
            if f.is_file() and f.stat().st_mtime < cutoff.timestamp():
                f.unlink()
        except OSError:
            continue
