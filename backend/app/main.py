"""FastAPI 入口"""
import logging
import threading
import time
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from .config import CORS_ORIGINS
from .database import Base, engine, SessionLocal
from .routers import auth, users, customers, orders, master, data, dashboard, ai, order_templates, templates, logs
from .seed import seed


def _setup_file_logging():
    """日志写入文件，每天一个文件（logs/app-YYYY-MM-DD.log），保留 365 天"""
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = TimedRotatingFileHandler(
        str(log_dir / "app.log"),
        when="midnight",
        interval=1,
        backupCount=365,
        encoding="utf-8",
    )
    handler.suffix = "%Y-%m-%d"
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    handler.setLevel(logging.INFO)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(h, TimedRotatingFileHandler) for h in root.handlers):
        root.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        lg.propagate = False
        if not any(isinstance(h, TimedRotatingFileHandler) for h in lg.handlers):
            lg.addHandler(handler)


_setup_file_logging()

Base.metadata.create_all(bind=engine)


def _migrate_schema():
    """幂等增量迁移（兼容 PostgreSQL / SQLite，create_all 不会给已有表加列）"""
    try:
        from sqlalchemy import inspect as sa_inspect
        insp = sa_inspect(engine)
        order_cols = {c["name"] for c in insp.get_columns("orders")}
        url_cols = {c["name"] for c in insp.get_columns("url")}
        tpl_cols = {c["name"] for c in insp.get_columns("template")}
        daily_cols = {c["name"] for c in insp.get_columns("daily_data")} if "daily_data" in insp.get_table_names() else set()
        wash_cols = {c["name"] for c in insp.get_columns("wash_name")} if "wash_name" in insp.get_table_names() else set()
        cust_cols = {c["name"] for c in insp.get_columns("customer")} if "customer" in insp.get_table_names() else set()
        th_cols = {c["name"] for c in insp.get_columns("tidabiao_history")} if "tidabiao_history" in insp.get_table_names() else set()
        with engine.begin() as conn:
            for col, ddl in [
                ("task_id", "VARCHAR(100)"),
                ("duration", "VARCHAR(50)"),
                ("template_id", "INTEGER"),
                ("filename_rule", "VARCHAR(200)"),
                ("dist_config_json", "TEXT"),
                ("order_date", "DATE"),
                ("price", "NUMERIC(10, 4)"),
                ("secondary_agent", "VARCHAR(100)"),
                ("platform", "VARCHAR(100)"),
                ("tpl_id", "INTEGER"),
                ("group_name", "VARCHAR(100)"),
                ("export_filename", "VARCHAR(200)"),
                ("add_name", "BOOLEAN"),
                ("check_collision", "BOOLEAN"),
                ("batch_no", "VARCHAR(50)"),
                ("operator_id", "INTEGER"),
                ("dup_order_nos", "TEXT"),
                ("change_fields_json", "TEXT"),
            ]:
                if col not in order_cols:
                    conn.execute(text(f"ALTER TABLE orders ADD COLUMN {col} {ddl}"))
            if "name" not in url_cols:
                conn.execute(text("ALTER TABLE url ADD COLUMN name VARCHAR(200)"))
            if "platform_id" not in url_cols:
                conn.execute(text("ALTER TABLE url ADD COLUMN platform_id INTEGER"))
            if "description" not in tpl_cols:
                conn.execute(text("ALTER TABLE template ADD COLUMN description TEXT"))
            if "tpl_type" not in tpl_cols:
                conn.execute(text("ALTER TABLE template ADD COLUMN tpl_type VARCHAR(20)"))
            for col, ddl in [
                ("task_id", "VARCHAR(100)"),
                ("operator", "VARCHAR(50)"),
                ("source_file", "VARCHAR(500)"),
                ("updated_at", "TIMESTAMP"),
                ("customer", "VARCHAR(100)"),
                ("secondary_agent", "VARCHAR(100)"),
                ("channel", "VARCHAR(100)"),
                ("source_file_id", "INTEGER"),
                ("name", "VARCHAR(50)"),
                ("cat1", "VARCHAR(100)"),
                ("cat2", "VARCHAR(100)"),
            ]:
                if col not in daily_cols:
                    conn.execute(text(f"ALTER TABLE daily_data ADD COLUMN {col} {ddl}"))
            for col, ddl in [
                ("name", "VARCHAR(50)"),
                ("province", "VARCHAR(50)"),
                ("city", "VARCHAR(50)"),
                ("operator", "VARCHAR(50)"),
            ]:
                if col not in wash_cols:
                    conn.execute(text(f"ALTER TABLE wash_name ADD COLUMN {col} {ddl}"))
            for col, ddl in [
                ("start_date", "DATE"),
                ("end_date", "DATE"),
                ("bill_tpl_id", "INTEGER"),
            ]:
                if col not in cust_cols:
                    conn.execute(text(f"ALTER TABLE customer ADD COLUMN {col} {ddl}"))
            for col, ddl in [
                ("check_collision", "VARCHAR(10)"),
            ]:
                if col not in th_cols:
                    conn.execute(text(f"ALTER TABLE tidabiao_history ADD COLUMN {col} {ddl}"))
            # 去掉过严的唯一索引：同一任务可有多条不同 URL 的订单，重复判定交给「验重」逻辑（url+地区+运营商）
            conn.execute(text("DROP INDEX IF EXISTS uq_order_up_date_task"))
            conn.execute(text("DROP INDEX IF EXISTS uq_order_active_task"))
    except Exception as e:  # noqa
        print(f"[migrate] 跳过: {e}")


def _ensure_indexes():
    """给大表补关键索引（幂等，启动时自动创建，避免全表扫描）"""
    indexes = [
        ("idx_daily_data_phone", "daily_data", "phone"),
        ("idx_daily_data_biz_date", "daily_data", "biz_date"),
        ("idx_daily_data_task_id", "daily_data", "task_id"),
    ]
    try:
        with engine.begin() as conn:
            for name, table, col in indexes:
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{name}" ON "{table}" ("{col}")'))
    except Exception as e:  # noqa
        print(f"[indexes] 跳过: {e}")


def _backfill_tpl_types():
    """给已有模版回填模版类型（订单/出数/账单/其他）"""
    try:
        from .models import Template
        db = SessionLocal()
        try:
            for t in db.query(Template).filter((Template.tpl_type.is_(None)) | (Template.tpl_type == "")).all():
                name = f"{t.ttype or ''} {t.code or ''}"
                if "出数" in name:
                    t.tpl_type = "出数"
                elif "账单" in name:
                    t.tpl_type = "账单"
                elif any(k in name for k in ("提单", "改单", "停单", "导入导出", "订单")):
                    t.tpl_type = "订单"
                else:
                    t.tpl_type = "其他"
            db.commit()
        finally:
            db.close()
    except Exception as e:  # noqa
        print(f"[backfill tpl_type] 跳过: {e}")


def _migrate_mb019_collision():
    """给 MB-019 模版在「是否加名」后插入「是否撞库」列并重建下拉框（幂等）"""
    try:
        import io as _io
        import openpyxl
        from openpyxl.utils import get_column_letter
        from openpyxl.worksheet.datavalidation import DataValidation
        from .models import Template
        db = SessionLocal()
        try:
            t = db.query(Template).filter(Template.code == "MB-019").first()
            if not t or not t.file_data:
                return
            wb = openpyxl.load_workbook(_io.BytesIO(bytes(t.file_data)))
            ws = wb.active
            headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
            if any(h is not None and "是否撞库" in str(h) for h in headers):
                return
            add_name_col = next((c for c, h in enumerate(headers, 1) if h is not None and "是否加名" in str(h)), None)
            if add_name_col is None:
                return
            ws.insert_cols(add_name_col + 1)
            ws.cell(row=1, column=add_name_col + 1, value="是否撞库")
            from openpyxl.styles import Alignment
            ws.cell(row=1, column=add_name_col + 1).alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[get_column_letter(add_name_col + 1)].width = 13
            # 重建下拉框（insert_cols 不会自动平移数据验证范围）
            ws.data_validations.dataValidation.clear()
            dropdowns = {
                "状态": "未提,在执,改单,待停,已停",
                "甲方": "新,牛",
                "是否加名": "是,否",
                "是否撞库": "是,否",
                "渠道": "106,小程序,直播间,dpi-白,dpi-灰",
                "运营商": "移动,电信,联通",
            }
            new_headers = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
            for c, h in enumerate(new_headers, 1):
                if not h:
                    continue
                hs = str(h).replace("\n", "").strip()
                for label, formula in dropdowns.items():
                    if hs == label:
                        dv = DataValidation(type="list", formula1=f'"{formula}"', allow_blank=True)
                        ws.add_data_validation(dv)
                        dv.add(f"{get_column_letter(c)}2:{get_column_letter(c)}1001")
                        break
            bio = _io.BytesIO()
            wb.save(bio)
            t.file_data = bio.getvalue()
            db.commit()
        finally:
            db.close()
    except Exception as e:  # noqa
        print(f"[migrate mb019 collision] 跳过: {e}")


def _dedup_channels():
    """合并重复渠道名（含首尾空格差异；保留最小 id，重定向订单/URL/客户单价引用，删除重复渠道）"""
    try:
        from .models import Channel, Order, Url, CustomerPrice
        db = SessionLocal()
        try:
            groups = {}
            for ch in db.query(Channel).order_by(Channel.id).all():
                key = (ch.name or "").strip()
                groups.setdefault(key, []).append(ch)
            for key, rows in groups.items():
                if len(rows) <= 1:
                    continue
                keep = rows[0]
                for dup in rows[1:]:
                    db.query(Order).filter(Order.channel_id == dup.id).update(
                        {"channel_id": keep.id}, synchronize_session=False)
                    db.query(Url).filter(Url.channel_id == dup.id).update(
                        {"channel_id": keep.id}, synchronize_session=False)
                    for cp in db.query(CustomerPrice).filter(CustomerPrice.channel_id == dup.id).all():
                        existing = db.query(CustomerPrice).filter(
                            CustomerPrice.customer_id == cp.customer_id,
                            CustomerPrice.channel_id == keep.id).first()
                        if existing:
                            existing.price = cp.price
                            db.delete(cp)
                        else:
                            cp.channel_id = keep.id
                    db.delete(dup)
            # 清理客户单价重复（同客户+同渠道）
            cgroups = {}
            for cp in db.query(CustomerPrice).order_by(CustomerPrice.id).all():
                cgroups.setdefault((cp.customer_id, cp.channel_id), []).append(cp)
            for k, rows in cgroups.items():
                if len(rows) <= 1:
                    continue
                for dup in rows[:-1]:
                    db.delete(dup)
            db.commit()
        finally:
            db.close()
    except Exception as e:  # noqa
        print(f"[dedup channels] 跳过: {e}")


_migrate_schema()
_ensure_indexes()
_backfill_tpl_types()
_migrate_mb019_collision()
_dedup_channels()

app = FastAPI(title="LM订单管理系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(customers.router)
app.include_router(orders.router)
app.include_router(master.router)
app.include_router(data.router)
app.include_router(dashboard.router)
app.include_router(ai.router)
app.include_router(order_templates.router)
app.include_router(templates.router)
app.include_router(logs.router)


def _scheduler_loop():
    """按配置的触发时间每天执行一次预警扫描"""
    from .routers.data import run_alert_scan
    from .models import SysConfig
    while True:
        # 读取触发时间（默认 00:00）
        try:
            db = SessionLocal()
            cfg = db.query(SysConfig).filter(SysConfig.key == "alert_trigger_time").first()
            trigger = cfg.value if cfg else "00:00"
            db.close()
        except Exception:  # noqa
            trigger = "00:00"
        try:
            hh, mm = [int(x) for x in trigger.split(":")]
        except Exception:  # noqa
            hh, mm = 0, 0
        now = datetime.now()
        next_run = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        time.sleep((next_run - now).total_seconds())
        try:
            db = SessionLocal()
            run_alert_scan(db)
            db.close()
            print(f"[scheduler] 预警扫描完成（触发时间 {trigger}）")
        except Exception as e:  # noqa
            print(f"[scheduler] 执行异常: {e}")
        time.sleep(60)  # 防止重复触发


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code, "data": None, "msg": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logging.getLogger("uvicorn.error").error("未处理异常", exc_info=exc)
    return JSONResponse(status_code=500, content={"code": 500, "data": None, "msg": "服务器内部错误，详情见日志"})


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    threading.Thread(target=_scheduler_loop, daemon=True).start()


@app.get("/healthz")
def healthz():
    return {"code": 0, "data": "ok", "msg": "ok"}


# ============ 静态文件服务（前端打包产物，SPA） ============
_FRONTEND_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "static",                       # 部署包: backend/static
    Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",     # 源码仓库: frontend/dist
]
FRONTEND_DIR = next((p for p in _FRONTEND_CANDIDATES if (p / "index.html").exists()), None)

if FRONTEND_DIR is not None:
    _assets = FRONTEND_DIR / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{filename:path}", include_in_schema=False)
    async def _spa(filename: str):
        if filename.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        root = FRONTEND_DIR.resolve()
        target = (FRONTEND_DIR / filename).resolve()
        if target.is_file() and str(target).startswith(str(root)):
            return FileResponse(str(target))
        return FileResponse(str(FRONTEND_DIR / "index.html"), headers={"Cache-Control": "no-store"})
