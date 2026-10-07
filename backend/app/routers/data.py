"""数据路由：日活数据/公积金/账单/预警"""
import csv
import io
import re
import threading
import uuid
from datetime import date, datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, insert, or_, update, bindparam
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..deps import get_current_user, require_admin
from ..models import (DailyData, Fund, Bill, Alert, Customer, Channel, Category,
                      Order, SysConfig, Operator, SourceFile, Template, WashName, Platform,
                      CustomerRecharge, CustomerPrice)
from ..pagination import paginate, ok_page
from ..excel import xlsx_response
from ..utils import fmt_dt
from ..schemas import BatchStopBody, GenerateBody, ExtractBody

router = APIRouter(prefix="/api", tags=["data"])

_DISTRIBUTE_TASKS = {}

FUND_HEADER_MAP = {
    "手机号": "phone", "姓名": "name", "身份证号": "id_card", "性别": "gender",
    "省份": "province", "地市": "city", "单位名称": "company", "单位性质": "company_type",
    "缴存基数": "base", "缴存比例": "ratio", "月缴存额": "monthly", "账户余额": "balance",
    "缴存状态": "deposit_status", "开户日期": "open_date", "缴至年月": "pay_to",
    "运营商": "operator", "来源文件": "source_file",
}


# ============ 日活数据 ============
@router.get("/daily-data")
def list_daily(db: Session = Depends(get_db), _=Depends(get_current_user),
               q: str = "", phone: str = "", upstream: str = "", task_id: str = "",
               task_name: str = "", province: str = "", city: str = "",
               operator: str = "", cat1: str = "", cat2: str = "", platform: str = "",
                source_file: str = "", customer: str = "", secondary_agent: str = "",
                channel: str = "", biz_date: str = "", name: str = "",
                start_date: str = "", end_date: str = "",
                page: int = 1, per_page: int = 10):
    qy = db.query(DailyData)
    if q:
        like = f"%{q}%"
        qy = qy.filter(or_(DailyData.phone.like(like), DailyData.task_name.like(like),
                           DailyData.upstream.like(like), DailyData.task_id.like(like)))
    if phone:
        qy = qy.filter(DailyData.phone.like(f"%{phone}%"))
    if upstream:
        qy = qy.filter(DailyData.upstream.like(f"%{upstream}%"))
    if task_id:
        qy = qy.filter(DailyData.task_id.like(f"%{task_id}%"))
    if task_name:
        qy = qy.filter(DailyData.task_name.like(f"%{task_name}%"))
    if province:
        provs = [p for p in province.split(",") if p.strip()]
        if provs:
            qy = qy.filter(or_(*[DailyData.province.like(f"%{p}%") for p in provs]))
    if city:
        cities = [c for c in city.split(",") if c.strip()]
        if cities:
            qy = qy.filter(or_(*[DailyData.city.like(f"%{c}%") for c in cities]))
    if operator:
        qy = qy.filter(DailyData.operator.like(f"%{operator}%"))
    if cat1:
        qy = qy.filter(DailyData.cat1.like(f"%{cat1}%"))
    if cat2:
        qy = qy.filter(DailyData.cat2.like(f"%{cat2}%"))
    if platform:
        qy = qy.filter(DailyData.platform.like(f"%{platform}%"))
    if source_file:
        qy = qy.filter(DailyData.source_file.like(f"%{source_file}%"))
    if customer:
        qy = qy.filter(DailyData.customer.like(f"%{customer}%"))
    if secondary_agent:
        qy = qy.filter(DailyData.secondary_agent.like(f"%{secondary_agent}%"))
    if channel:
        qy = qy.filter(DailyData.channel.like(f"%{channel}%"))
    if name:
        qy = qy.filter(DailyData.name.like(f"%{name}%"))
    if biz_date:
        qy = qy.filter(DailyData.biz_date == biz_date)
    if start_date:
        sd = _parse_biz_date(start_date)
        if sd:
            qy = qy.filter(DailyData.biz_date >= sd)
    if end_date:
        ed = _parse_biz_date(end_date)
        if ed:
            qy = qy.filter(DailyData.biz_date <= ed)
    total, rows = paginate(qy.order_by(DailyData.id.desc()), page, per_page)
    return ok_page([_daily_dict(d) for d in rows], total)


def _daily_dict(d: DailyData):
    return {
        "id": d.id, "biz_date": str(d.biz_date) if d.biz_date else None,
        "upstream": d.upstream or "", "task_id": d.task_id or "",
        "task_name": d.task_name or "", "phone": d.phone or "",
        "name": d.name or "",
        "province": d.province or "", "city": d.city or "",
        "operator": d.operator or "",
        "cat1": d.cat1 or "", "cat2": d.cat2 or "",
        "platform": d.platform or "",
        "customer": d.customer or "", "secondary_agent": d.secondary_agent or "",
        "channel": d.channel or "", "source_file": d.source_file or "",
        "source_file_id": d.source_file_id,
        "created_at": fmt_dt(d.created_at), "updated_at": fmt_dt(d.updated_at),
    }


DAILY_EXPORT_COLS = [
    ("biz_date", "数据日期", lambda d: str(d.biz_date) if d.biz_date else ""),
    ("upstream", "甲方", lambda d: d.upstream or ""),
    ("task_id", "任务id", lambda d: d.task_id or ""),
    ("task_name", "任务名", lambda d: d.task_name or ""),
    ("phone", "手机号", lambda d: d.phone or ""),
    ("name", "姓名", lambda d: d.name or ""),
    ("province", "省", lambda d: d.province or ""),
    ("city", "市", lambda d: d.city or ""),
    ("operator", "运营商", lambda d: d.operator or ""),
    ("cat1", "一级品类", lambda d: d.cat1 or ""),
    ("cat2", "二级品类", lambda d: d.cat2 or ""),
    ("platform", "平台", lambda d: d.platform or ""),
    ("customer", "一级代理", lambda d: d.customer or ""),
    ("secondary_agent", "二级代理", lambda d: d.secondary_agent or ""),
    ("channel", "渠道", lambda d: d.channel or ""),
    ("source_file", "来源文件名", lambda d: d.source_file or ""),
    ("created_at", "创建时间", lambda d: fmt_dt(d.created_at)),
    ("updated_at", "更新时间", lambda d: fmt_dt(d.updated_at)),
]


@router.get("/daily-data/export")
def export_daily(db: Session = Depends(get_db), _=Depends(get_current_user),
                 q: str = "", phone: str = "", upstream: str = "", task_id: str = "",
                 task_name: str = "", province: str = "", city: str = "",
                 operator: str = "", cat1: str = "", cat2: str = "", platform: str = "",
                 source_file: str = "", customer: str = "", secondary_agent: str = "",
                 channel: str = "", biz_date: str = "", name: str = "", cols: str = ""):
    qy = db.query(DailyData)
    if q:
        like = f"%{q}%"
        qy = qy.filter(or_(DailyData.phone.like(like), DailyData.task_name.like(like),
                           DailyData.upstream.like(like), DailyData.task_id.like(like)))
    if phone:
        qy = qy.filter(DailyData.phone.like(f"%{phone}%"))
    if upstream:
        qy = qy.filter(DailyData.upstream.like(f"%{upstream}%"))
    if task_id:
        qy = qy.filter(DailyData.task_id.like(f"%{task_id}%"))
    if task_name:
        qy = qy.filter(DailyData.task_name.like(f"%{task_name}%"))
    if province:
        provs = [p for p in province.split(",") if p.strip()]
        if provs:
            qy = qy.filter(or_(*[DailyData.province.like(f"%{p}%") for p in provs]))
    if city:
        cities = [c for c in city.split(",") if c.strip()]
        if cities:
            qy = qy.filter(or_(*[DailyData.city.like(f"%{c}%") for c in cities]))
    if operator:
        qy = qy.filter(DailyData.operator.like(f"%{operator}%"))
    if cat1:
        qy = qy.filter(DailyData.cat1.like(f"%{cat1}%"))
    if cat2:
        qy = qy.filter(DailyData.cat2.like(f"%{cat2}%"))
    if platform:
        qy = qy.filter(DailyData.platform.like(f"%{platform}%"))
    if source_file:
        qy = qy.filter(DailyData.source_file.like(f"%{source_file}%"))
    if customer:
        qy = qy.filter(DailyData.customer.like(f"%{customer}%"))
    if secondary_agent:
        qy = qy.filter(DailyData.secondary_agent.like(f"%{secondary_agent}%"))
    if channel:
        qy = qy.filter(DailyData.channel.like(f"%{channel}%"))
    if name:
        qy = qy.filter(DailyData.name.like(f"%{name}%"))
    if biz_date:
        qy = qy.filter(DailyData.biz_date == biz_date)
    rows = qy.order_by(DailyData.id.desc()).all()
    selected = [c for c in (cols or "").split(",") if c.strip()]
    spec = [(k, l, fn) for (k, l, fn) in DAILY_EXPORT_COLS if not selected or k in selected]
    headers = [l for _, l, _ in spec]
    data = [[fn(d) for _, _, fn in spec] for d in rows]
    return xlsx_response(headers, data, "日活数据.xlsx", "日活数据")


def _parse_biz_date(v):
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _order_info_by_task_id(db, task_id):
    """按工单号关联订单，返回 甲方/任务名/运营商/一级代理/二级代理/渠道/平台"""
    if not task_id:
        return {}
    o = db.query(Order).filter(Order.task_id == task_id).first()
    if not o:
        return {}
    up = db.query(Customer).filter(Customer.id == o.upstream_id).first()
    cust = db.query(Customer).filter(Customer.id == o.customer_id).first()
    op = db.query(Operator).filter(Operator.id == o.operator_id).first()
    ch = db.query(Channel).filter(Channel.id == o.channel_id).first()
    return {
        "upstream": up.name if up else "",
        "task_name": o.task_name or "",
        "operator": op.name if op else "",
        "customer": (f"{cust.code} {cust.name}" if cust else ""),
        "secondary_agent": o.secondary_agent or "",
        "channel": ch.name if ch else "",
        "platform": o.platform or "",
    }


def _wash_name_by_phone(db, phone):
    """按手机号从洗名库取姓名"""
    if not phone:
        return ""
    w = db.query(WashName).filter(WashName.phone == phone).first()
    return w.name if w and w.name else ""


def _cat_by_platform(db, platform_name):
    """按平台名称关联品类管理，返回 (一级品类, 二级品类)"""
    if not platform_name:
        return "", ""
    p = db.query(Platform).filter(Platform.name == platform_name).first()
    if not p:
        return "", ""
    cat2 = db.query(Category).filter(Category.id == p.cat_id).first()
    if not cat2:
        return "", ""
    cat1 = db.query(Category).filter(Category.id == cat2.parent_id).first()
    return (cat1.name if cat1 else ""), (cat2.name or "")


def _is_header_row(values):
    """第一行是否为表头：含「任务id/手机号/运营商」等文字则视为表头"""
    if not values:
        return False
    joined = "".join(str(v) for v in values if v is not None).lower()
    return any(k in joined for k in ("任务id", "任务名", "手机号", "运营商", "省", "市"))


def _import_niu_excel(db, content, biz_date, source_file, source_file_id, errors, seen):
    """解析牛的数据 excel（第一行是表头）：任务id/任务名/手机号/省/市/运营商"""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    n = 0
    deduped = 0
    header = None
    for values in ws.iter_rows(values_only=True):
        if header is None:
            header = [str(v).strip() if v is not None else "" for v in values]
            continue
        if not any((str(v) if v is not None else "").strip() for v in values):
            continue
        def col(*names):
            for i, h in enumerate(header):
                hn = re.sub(r"\s+", "", h).lower()
                for nm in names:
                    if re.sub(r"\s+", "", nm).lower() in hn:
                        return i
            return -1
        tid = col("任务id")
        tnm = col("任务名")
        pn = col("手机号")
        prov = col("省")
        cty = col("市")
        op = col("运营商")
        task_id = str(values[tid]).strip() if tid >= 0 and tid < len(values) and values[tid] is not None else ""
        task_name = str(values[tnm]).strip() if tnm >= 0 and tnm < len(values) and values[tnm] is not None else ""
        phone = str(values[pn]).strip() if pn >= 0 and pn < len(values) and values[pn] is not None else ""
        province = str(values[prov]).strip() if prov >= 0 and prov < len(values) and values[prov] is not None else ""
        city = str(values[cty]).strip() if cty >= 0 and cty < len(values) and values[cty] is not None else ""
        operator = str(values[op]).strip() if op >= 0 and op < len(values) and values[op] is not None else ""
        if not phone:
            continue
        key = (task_id, phone)
        if key in seen:
            deduped += 1
            continue
        seen.add(key)
        info = _order_info_by_task_id(db, task_id)
        cat1, cat2 = _cat_by_platform(db, info.get("platform") or "")
        db.add(DailyData(
            biz_date=biz_date,
            upstream=info.get("upstream") or "",
            task_id=task_id,
            task_name=task_name or info.get("task_name") or "",
            phone=phone,
            name=_wash_name_by_phone(db, phone),
            province=province,
            city=city,
            operator=operator or info.get("operator") or "",
            cat1=cat1,
            cat2=cat2,
            platform=info.get("platform") or "",
            customer=info.get("customer") or "",
            secondary_agent=info.get("secondary_agent") or "",
            channel=info.get("channel") or "",
            source_file=source_file,
            source_file_id=source_file_id,
        ))
        n += 1
    wb.close()
    return n, deduped


def _import_new_excel(db, content, biz_date, source_file, source_file_id, errors, seen):
    """解析新的数据 excel（第一行是数据，无表头）：手机号/甲方工单号/平台/省/市"""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    n = 0
    deduped = 0
    for values in ws.iter_rows(values_only=True):
        if not any((str(v) if v is not None else "").strip() for v in values):
            continue
        vals = [str(v).strip() if v is not None else "" for v in values]
        phone = vals[0] if len(vals) > 0 else ""
        task_id = vals[1] if len(vals) > 1 else ""
        province = vals[3] if len(vals) > 3 else ""
        city = vals[4] if len(vals) > 4 else ""
        if not phone:
            continue
        key = (task_id, phone)
        if key in seen:
            deduped += 1
            continue
        seen.add(key)
        info = _order_info_by_task_id(db, task_id)
        cat1, cat2 = _cat_by_platform(db, info.get("platform") or "")
        db.add(DailyData(
            biz_date=biz_date,
            upstream=info.get("upstream") or "",
            task_id=task_id,
            task_name=info.get("task_name") or "",
            phone=phone,
            name=_wash_name_by_phone(db, phone),
            province=province,
            city=city,
            operator=info.get("operator") or "",
            cat1=cat1,
            cat2=cat2,
            platform=info.get("platform") or "",
            customer=info.get("customer") or "",
            secondary_agent=info.get("secondary_agent") or "",
            channel=info.get("channel") or "",
            source_file=source_file,
            source_file_id=source_file_id,
        ))
        n += 1
    wb.close()
    return n, deduped


def _import_one_daily_file(db, fn, content, date_obj, source_file_id, errors, seen):
    """处理单个文件（zip 或 excel），返回 (导入条数, 去重条数)"""
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    if ext not in ("zip", "xlsx", "xls"):
        errors.append(f"{fn}: 仅支持 zip / xlsx / xls 文件")
        return 0, 0
    n = 0
    deduped = 0
    if ext == "zip":
        import zipfile
        try:
            zf = zipfile.ZipFile(io.BytesIO(content))
            for name in zf.namelist():
                if name.lower().endswith((".xlsx", ".xls")):
                    try:
                        nn, dd = _import_niu_excel(db, zf.read(name), date_obj, fn, source_file_id, errors, seen)
                        n += nn
                        deduped += dd
                    except Exception as e:  # noqa
                        errors.append(f"{name}: {e}")
            zf.close()
        except Exception as e:  # noqa
            errors.append(f"{fn}: 解压失败 {e}")
    else:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        first = None
        for values in ws.iter_rows(values_only=True):
            first = values
            break
        wb.close()
        if _is_header_row(first):
            nn, dd = _import_niu_excel(db, content, date_obj, fn, source_file_id, errors, seen)
        else:
            nn, dd = _import_new_excel(db, content, date_obj, fn, source_file_id, errors, seen)
        n += nn
        deduped += dd
    return n, deduped


def _extract_task_ids_from_excel(content):
    """解析 excel，返回所有（有手机号行的）任务id列表（可能含空串）"""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    tids = []
    header = None
    header_mode = False
    tid_i = phone_i = -1

    def find_idx(names):
        for i, h in enumerate(header or []):
            hn = re.sub(r"\s+", "", h).lower()
            for nm in names:
                if re.sub(r"\s+", "", nm).lower() in hn:
                    return i
        return -1

    for values in ws.iter_rows(values_only=True):
        if header is None:
            header = [str(v).strip() if v is not None else "" for v in values]
            if _is_header_row(values):
                header_mode = True
                tid_i = find_idx(["任务id"])
                phone_i = find_idx(["手机号"])
                continue  # 表头，跳过
        if not any((str(v) if v is not None else "").strip() for v in values):
            continue
        vals = [str(v).strip() if v is not None else "" for v in values]
        if header_mode:
            phone = vals[phone_i] if phone_i >= 0 and phone_i < len(vals) else ""
            tid = vals[tid_i] if tid_i >= 0 and tid_i < len(vals) else ""
        else:
            phone = vals[0] if len(vals) > 0 else ""
            tid = vals[1] if len(vals) > 1 else ""
        if phone:
            tids.append(tid)
    wb.close()
    return tids


def _extract_task_ids(fn, content):
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    tids = []
    if ext == "zip":
        import zipfile
        zf = zipfile.ZipFile(io.BytesIO(content))
        for name in zf.namelist():
            if name.lower().endswith((".xlsx", ".xls")):
                tids += _extract_task_ids_from_excel(zf.read(name))
        zf.close()
    elif ext in ("xlsx", "xls"):
        tids += _extract_task_ids_from_excel(content)
    return tids


def _count_unmatched(db, file_list):
    """统计未匹配到订单的日活数据条数，返回 (条数, 未匹配工单明细列表)"""
    order_tids = {r[0] for r in db.query(Order.task_id).all() if r[0]}
    total = 0
    unmatched_tids = set()
    for fn, content in file_list:
        for tid in _extract_task_ids(fn, content):
            if tid not in order_tids:
                total += 1
                if tid:
                    unmatched_tids.add(tid)
    items = [{"task_id": tid, "task_name": "", "channel": ""} for tid in sorted(unmatched_tids)]
    return total, items


def _count_stopped_abnormal(db, file_list, date_obj):
    """统计关联到已停订单、且数据日期 >= 订单更新日期+2 的异常数据，返回 (条数, 工单明细列表)"""
    stopped = {o.task_id: o for o in db.query(Order).filter(Order.status == "已停").all() if o.task_id}
    chans = {c.id: c.name for c in db.query(Channel).all()}
    total = 0
    tids = set()
    for fn, content in file_list:
        for tid in _extract_task_ids(fn, content):
            o = stopped.get(tid)
            if o and o.order_date and date_obj >= o.order_date + timedelta(days=2):
                total += 1
                tids.add(tid)
    items = []
    for tid in sorted(tids):
        o = stopped.get(tid)
        items.append({"task_id": tid, "task_name": (o.task_name or "") if o else "",
                      "channel": chans.get(o.channel_id, "") if o else ""})
    return total, items


def _count_inactive_orders(db, date_obj):
    """统计在执订单中，数据日期 >= 订单更新日期+2 但当天无数据的工单（明细列表）"""
    has_data = {r[0] for r in db.query(DailyData.task_id).filter(DailyData.biz_date == date_obj).all() if r[0]}
    chans = {c.id: c.name for c in db.query(Channel).all()}
    items = []
    for o in db.query(Order).filter(Order.status == "在执").all():
        if o.task_id and o.order_date and date_obj >= o.order_date + timedelta(days=2) and o.task_id not in has_data:
            items.append({"task_id": o.task_id, "task_name": o.task_name or "",
                          "channel": chans.get(o.channel_id, "")})
    items.sort(key=lambda x: x["task_id"])
    return items


@router.post("/daily-data/import")
async def import_daily(files: List[UploadFile] = File(...), biz_date: str = Form(""),
                       confirm: bool = Form(False), db: Session = Depends(get_db), _=Depends(get_current_user)):
    date_obj = _parse_biz_date(biz_date)
    if not date_obj:
        raise HTTPException(status_code=422, detail="请选择数据日期")

    # 读取所有文件
    file_list = []
    for file in files:
        fn = file.filename or ""
        content = await file.read()
        if content:
            file_list.append((fn, content))

    # 未匹配订单 或 已停订单异常数据时，弹出提示确认
    if not confirm:
        unmatched, unmatched_items = _count_unmatched(db, file_list)
        stopped_abnormal, stopped_items = _count_stopped_abnormal(db, file_list, date_obj)
        if unmatched > 0 or stopped_abnormal > 0:
            return {"code": 0, "data": {"needs_confirm": True, "unmatched": unmatched, "unmatched_items": unmatched_items,
                                        "stopped_abnormal": stopped_abnormal, "stopped_items": stopped_items},
                    "msg": f"有 {unmatched} 条数据未匹配到订单，{stopped_abnormal} 条关联到已停订单"}

    # 当天已有 (任务id, 手机号)，用于同任务内去重
    seen = {(r.task_id, r.phone) for r in db.query(DailyData).filter(DailyData.biz_date == date_obj).all()}

    imported = 0
    deduped = 0
    errors = []
    for fn, content in file_list:
        ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
        if ext not in ("zip", "xlsx", "xls"):
            errors.append(f"{fn}: 仅支持 zip / xlsx / xls 文件")
            continue
        # 上传到源文件管理表
        sf = SourceFile(filename=fn, file_data=content, file_type=ext,
                        biz_date=date_obj.strftime("%Y-%m-%d"), size=len(content))
        db.add(sf)
        db.flush()
        n, dd = _import_one_daily_file(db, fn, content, date_obj, sf.id, errors, seen)
        imported += n
        deduped += dd
    db.commit()
    inactive_items = _count_inactive_orders(db, date_obj)
    return {"code": 0, "data": {"imported": imported, "deduped": deduped, "errors": errors, "inactive_items": inactive_items},
            "msg": f"导入 {imported} 条，去重 {deduped} 条，失败 {len(errors)} 条"}


# ============ 日活数据：LM 结构 CSV 原样导入 ============
_CSV_FIELD_ALIASES = {
    "数据日期": "biz_date", "日期": "biz_date", "biz_date": "biz_date",
    "甲方": "upstream", "upstream": "upstream",
    "任务id": "task_id", "任务ID": "task_id", "工单号": "task_id", "task_id": "task_id",
    "任务名": "task_name", "task_name": "task_name",
    "手机号": "phone", "联系方式": "phone", "phone": "phone",
    "姓名": "name", "name": "name",
    "省": "province", "省份": "province", "province": "province",
    "市": "city", "城市": "city", "city": "city",
    "运营商": "operator", "operator": "operator",
    "一级品类": "cat1", "cat1": "cat1",
    "二级品类": "cat2", "cat2": "cat2",
    "平台": "platform", "platform": "platform",
    "一级代理": "customer", "customer": "customer",
    "二级代理": "secondary_agent", "secondary_agent": "secondary_agent",
    "渠道": "channel", "channel": "channel",
    "来源文件名": "source_file", "source_file": "source_file",
}


def _norm_csv_header(h):
    return re.sub(r"[\s\u3000]+", "", str(h or "")).strip().lstrip("\ufeff")


def _import_daily_csv_stream(db, fh, filename, default_date, stats):
    """流式解析 LM 结构 CSV，按行原样写入 daily_data。

    规则：不关联订单、不查洗名库、不做品类映射（原样入库）；
    按（数据日期+任务id+手机号）去重（含库内已有行，可重复导入不重复计数）。
    """
    import csv as _csv
    reader = _csv.reader(fh)
    header = next(reader, None)
    if header is None:
        return
    idx = {}
    for i, h in enumerate(header):
        key = _CSV_FIELD_ALIASES.get(_norm_csv_header(h))
        if key and key not in idx:
            idx[key] = i
    if "phone" not in idx:
        stats["errors"].append(f"{filename}: 缺少「手机号」列")
        return

    batch = []
    now = datetime.now()
    for values in reader:
        if not any((str(v).strip() if v is not None else "") for v in values):
            continue

        def g(field):
            i = idx.get(field)
            if i is None or i >= len(values):
                return ""
            v = values[i]
            return "" if v is None else str(v).strip()

        phone = g("phone")
        if not phone:
            continue
        d = _parse_biz_date(g("biz_date")) or default_date
        if not d:
            stats["skipped"] += 1
            continue
        ds = str(d)
        # 首次遇到某日期时，把库里该日期已有行按去重键载入
        if ds not in stats["loaded_dates"]:
            stats["loaded_dates"].add(ds)
            for tid, ph, pf, cu, ch, tn in db.query(
                    DailyData.task_id, DailyData.phone, DailyData.platform,
                    DailyData.customer, DailyData.channel, DailyData.task_name).filter(
                    DailyData.biz_date == d).all():
                stats["seen"].add((ds, tid or "", ph or "", pf or "", cu or "", ch or "", tn or ""))

        task_id = g("task_id")
        # 去重键：任务id 为空时（历史日活文件），用平台/一级代理/渠道/任务名 补充区分，避免误吞同日同号的不同行
        key = (ds, task_id, phone, g("platform"), g("customer"), g("channel"), g("task_name"))
        if key in stats["seen"]:
            stats["deduped"] += 1
            continue
        stats["seen"].add(key)
        batch.append({
            "biz_date": d, "upstream": g("upstream"), "task_id": task_id,
            "task_name": g("task_name"), "phone": phone, "name": g("name"),
            "province": g("province"), "city": g("city"), "operator": g("operator"),
            "cat1": g("cat1"), "cat2": g("cat2"), "platform": g("platform"),
            "customer": g("customer"), "secondary_agent": g("secondary_agent"),
            "channel": g("channel"), "source_file": g("source_file") or filename,
            "source_file_id": None, "created_at": now, "updated_at": now,
        })
        if len(batch) >= 5000:
            db.execute(insert(DailyData), batch)
            db.commit()
            stats["imported"] += len(batch)
            batch.clear()
    if batch:
        db.execute(insert(DailyData), batch)
        db.commit()
        stats["imported"] += len(batch)
        batch.clear()


@router.post("/daily-data/import-csv")
async def import_daily_csv(files: List[UploadFile] = File(...), biz_date: str = Form(""),
                           db: Session = Depends(get_db), _=Depends(require_admin)):
    """原样导入 LM 结构 CSV（表头：数据日期/甲方/任务id/任务名/手机号/姓名/省/市/运营商/…）。

    与 /daily-data/import 的区别：不做订单关联、不查洗名库，字段按 CSV 原样入库。
    数据日期以每行的「数据日期」为准，缺省用表单 biz_date 兜底。
    """
    default_date = _parse_biz_date(biz_date)
    stats = {"imported": 0, "deduped": 0, "skipped": 0, "errors": [],
             "seen": set(), "loaded_dates": set()}
    seen_files = 0
    for file in files:
        fn = file.filename or ""
        if not fn.lower().endswith(".csv"):
            stats["errors"].append(f"{fn}: 仅支持 csv 文件")
            continue
        seen_files += 1
        try:
            raw = await file.read()
            text = io.StringIO(raw.decode("utf-8-sig", errors="ignore"))
            _import_daily_csv_stream(db, text, fn, default_date, stats)
            text.close()
            del raw
        except Exception as e:  # noqa
            stats["errors"].append(f"{fn}: {e}")
    if seen_files == 0 and not stats["errors"]:
        raise HTTPException(status_code=422, detail="请选择 csv 文件")
    return {"code": 0, "data": {"imported": stats["imported"], "deduped": stats["deduped"],
                                 "skipped": stats["skipped"], "errors": stats["errors"]},
            "msg": f"CSV 原样导入 {stats['imported']} 条，去重 {stats['deduped']} 条，跳过 {stats['skipped']} 条"}


@router.post("/daily-data/batch-delete")
def batch_delete_daily(body: BatchStopBody, db: Session = Depends(get_db), _=Depends(require_admin)):
    rows = db.query(DailyData).filter(DailyData.id.in_(body.ids)).all()
    for r in rows:
        db.delete(r)
    db.commit()
    return {"code": 0, "data": {"deleted": len(rows)}, "msg": f"已删除 {len(rows)} 条"}


@router.post("/daily-data/delete-by-date")
def delete_daily_by_date(body: GenerateBody, db: Session = Depends(get_db), _=Depends(require_admin)):
    d = _parse_biz_date(body.date)
    if not d:
        raise HTTPException(status_code=422, detail="请选择数据日期")
    n = db.query(DailyData).filter(DailyData.biz_date == d).count()
    db.query(DailyData).filter(DailyData.biz_date == d).delete()
    db.commit()
    return {"code": 0, "data": {"deleted": n}, "msg": f"已删除 {body.date} 的 {n} 条日活数据"}


@router.post("/daily-data/backfill-category")
def backfill_daily_category(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """按平台重新补充缺失的一级/二级品类（品类管理补全平台映射后使用）"""
    missing_cond = or_(DailyData.cat1.is_(None), DailyData.cat1 == "",
                       DailyData.cat2.is_(None), DailyData.cat2 == "")
    platforms = sorted({p for p, in db.query(DailyData.platform).filter(
        DailyData.platform.isnot(None), DailyData.platform != "", missing_cond).distinct().all()})
    updated = 0
    for p in platforms:
        cat1, cat2 = _cat_by_platform(db, p)
        if not cat1 and not cat2:
            continue
        n1 = n2 = 0
        if cat1:
            n1 = db.query(DailyData).filter(DailyData.platform == p,
                                            or_(DailyData.cat1.is_(None), DailyData.cat1 == "")).update(
                {"cat1": cat1}, synchronize_session=False)
        if cat2:
            n2 = db.query(DailyData).filter(DailyData.platform == p,
                                            or_(DailyData.cat2.is_(None), DailyData.cat2 == "")).update(
                {"cat2": cat2}, synchronize_session=False)
        updated += max(n1, n2)
    db.commit()
    return {"code": 0, "data": {"updated": updated}, "msg": f"已补充 {updated} 条品类信息"}


@router.delete("/daily-data")
def clear_daily(db: Session = Depends(get_db), _=Depends(get_current_user)):
    n = db.query(DailyData).count()
    db.query(DailyData).delete()
    db.commit()
    return {"code": 0, "data": {"cleared": n}, "msg": f"已清空 {n} 条日活数据"}


def _phone_str(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


@router.get("/daily-data/wash-export")
def wash_export(date: str = "", db: Session = Depends(get_db), _=Depends(get_current_user)):
    """洗名：导出所选日期下，姓名为空且关联订单「是否加名=是」的手机号（Excel）"""
    date_obj = _parse_biz_date(date)
    if not date_obj:
        raise HTTPException(status_code=422, detail="请选择数据日期")
    add_name_tids = [o.task_id for o in db.query(Order).filter(Order.add_name.is_(True)).all() if o.task_id]
    qy = db.query(DailyData).filter(
        DailyData.biz_date == date_obj,
        or_(DailyData.name.is_(None), DailyData.name == ""),
    )
    if add_name_tids:
        qy = qy.filter(DailyData.task_id.in_(add_name_tids))
    else:
        qy = qy.filter(DailyData.id < 0)
    rows = qy.order_by(DailyData.id).all()
    phones = [r.phone for r in rows if r.phone]
    return xlsx_response(["手机号", "姓名"], [[p, ""] for p in phones], f"洗名-{date}.xlsx", "洗名")


@router.get("/daily-data/wash-stats")
def wash_stats(date: str = "", db: Session = Depends(get_db), _=Depends(get_current_user)):
    """洗名导出统计：一共要导出、已匹配洗名库、需要去小逸洗名"""
    date_obj = _parse_biz_date(date)
    if not date_obj:
        raise HTTPException(status_code=422, detail="请选择数据日期")
    add_name_tids = [o.task_id for o in db.query(Order).filter(Order.add_name.is_(True)).all() if o.task_id]
    qy = db.query(DailyData).filter(DailyData.biz_date == date_obj)
    if add_name_tids:
        qy = qy.filter(DailyData.task_id.in_(add_name_tids))
    else:
        qy = qy.filter(DailyData.id < 0)
    total = qy.count()
    matched = qy.filter(DailyData.name.isnot(None), DailyData.name != "").count()
    need_wash = total - matched
    return {"code": 0, "data": {"total": total, "matched": matched, "need_wash": need_wash}, "msg": "ok"}


def _check_daily_result(db, date_obj):
    """工单检查：统计所有在执工单在所选日期的数据量（按数据量降序）"""
    orders = db.query(Order).filter(Order.status == "在执").all()
    counts = {}
    for tid, cnt in db.query(DailyData.task_id, func.count(DailyData.id)) \
            .filter(DailyData.biz_date == date_obj, DailyData.task_id.isnot(None)) \
            .group_by(DailyData.task_id).all():
        counts[tid] = int(cnt)
    result = []
    for o in orders:
        result.append({
            "task_id": o.task_id or "",
            "task_name": o.task_name or "",
            "order_no": o.order_no or "",
            "count": counts.get(o.task_id, 0),
        })
    result.sort(key=lambda x: (-x["count"], x["task_id"]))
    return result


@router.get("/daily-data/check")
def check_daily(date: str = "", db: Session = Depends(get_db), _=Depends(get_current_user)):
    """工单检查：统计所有在执工单在所选日期的数据量（按数据量降序）"""
    date_obj = _parse_biz_date(date)
    if not date_obj:
        raise HTTPException(status_code=422, detail="请选择数据日期")
    return {"code": 0, "data": _check_daily_result(db, date_obj), "msg": "ok"}


@router.get("/daily-data/check-export")
def check_export(date: str = "", db: Session = Depends(get_db), _=Depends(get_current_user)):
    """工单检查结果导出（Excel）"""
    date_obj = _parse_biz_date(date)
    if not date_obj:
        raise HTTPException(status_code=422, detail="请选择数据日期")
    result = _check_daily_result(db, date_obj)
    headers = ["工单号", "任务名", "订单编号", "数据量"]
    rows = [[r["task_id"], r["task_name"], r["order_no"], r["count"]] for r in result]
    return xlsx_response(headers, rows, f"工单检查-{date}.xlsx", "工单检查")


def _parse_wash_file(fn, content):
    """解析洗名文件，返回 [(phone, name, province, city, operator)]"""
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    rows = []
    if ext in ("xlsx", "xls"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        header = None
        for values in ws.iter_rows(values_only=True):
            if header is None:
                header = [str(v).strip() if v is not None else "" for v in values]
                continue
            if not any((str(v) if v is not None else "").strip() for v in values):
                continue
            def col(*names):
                for i, h in enumerate(header):
                    hn = re.sub(r"\s+", "", h).lower()
                    for nm in names:
                        if re.sub(r"\s+", "", nm).lower() in hn:
                            return i
                return -1
            pi = col("phone", "手机号")
            ni = col("name", "姓名")
            pri = col("province", "省")
            ci = col("city", "市")
            ii = col("isp", "运营商")
            phone = _phone_str(values[pi]) if pi >= 0 and pi < len(values) else ""
            name = str(values[ni]).strip() if ni >= 0 and ni < len(values) and values[ni] is not None else ""
            province = str(values[pri]).strip() if pri >= 0 and pri < len(values) and values[pri] is not None else ""
            city = str(values[ci]).strip() if ci >= 0 and ci < len(values) and values[ci] is not None else ""
            operator = str(values[ii]).strip() if ii >= 0 and ii < len(values) and values[ii] is not None else ""
            if phone:
                rows.append((phone, name, province, city, operator))
        wb.close()
    elif ext == "csv":
        import csv as csv_mod
        text = content.decode("utf-8-sig", errors="ignore")
        reader = csv_mod.reader(io.StringIO(text))
        header = None
        for line in reader:
            if header is None:
                header = [str(v).strip() for v in line]
                continue
            if not any(v.strip() for v in line):
                continue
            def col(*names):
                for i, h in enumerate(header):
                    hn = re.sub(r"\s+", "", h).lower()
                    for nm in names:
                        if re.sub(r"\s+", "", nm).lower() in hn:
                            return i
                return -1
            pi = col("phone", "手机号")
            ni = col("name", "姓名")
            pri = col("province", "省")
            ci = col("city", "市")
            ii = col("isp", "运营商")
            phone = _phone_str(line[pi]) if pi >= 0 and pi < len(line) else ""
            name = line[ni].strip() if ni >= 0 and ni < len(line) else ""
            province = line[pri].strip() if pri >= 0 and pri < len(line) else ""
            city = line[ci].strip() if ci >= 0 and ci < len(line) else ""
            operator = line[ii].strip() if ii >= 0 and ii < len(line) else ""
            if phone:
                rows.append((phone, name, province, city, operator))
    return rows


@router.post("/daily-data/import-wash")
async def import_wash(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(get_current_user)):
    """导入洗名：按手机号更新姓名，同时更新到洗名库（手机号存在则更新，不存在则插入）"""
    fn = file.filename or ""
    content = await file.read()
    if not content:
        raise HTTPException(status_code=422, detail="文件为空")
    rows = _parse_wash_file(fn, content)
    rec_map = {}
    for phone, name, province, city, operator in rows:
        rec_map[phone] = {"name": name, "province": province, "city": city, "operator": operator}
    phones = list(rec_map.keys())
    if phones:
        # 批量更新日活数据姓名（按手机号，走 phone 索引）
        stmt = (update(DailyData.__table__)
                .where(DailyData.__table__.c.phone == bindparam("ph"))
                .values(name=bindparam("nm")))
        db.execute(stmt, [{"ph": p, "nm": rec_map[p]["name"]} for p in phones])
    for phone in phones:
        rec = rec_map[phone]
        # 更新洗名库（手机号存在则更新，不存在且有名则插入；无姓名不插入，避免清空已有姓名）
        w = db.query(WashName).filter(WashName.phone == phone).first()
        if w:
            if rec["name"]:
                w.name = rec["name"]
            if rec["province"]:
                w.province = rec["province"]
            if rec["city"]:
                w.city = rec["city"]
            if rec["operator"]:
                w.operator = rec["operator"]
        elif rec["name"]:
            db.add(WashName(phone=phone, name=rec["name"], province=rec["province"],
                            city=rec["city"], operator=rec["operator"]))
    db.commit()
    return {"code": 0, "data": {"updated": len(phones)}, "msg": f"已更新 {len(phones)} 个手机号的姓名，洗名库同步更新"}


# ============ 洗名库 ============

@router.get("/wash-names")
def list_wash_names(db: Session = Depends(get_db), _=Depends(get_current_user),
                    q: str = "", phone: str = "", name: str = "", name_empty: str = "",
                    province: str = "", city: str = "", operator: str = "",
                    page: int = 1, per_page: int = 10):
    qy = db.query(WashName)
    if q:
        like = f"%{q}%"
        qy = qy.filter(or_(WashName.phone.like(like), WashName.name.like(like)))
    if phone:
        qy = qy.filter(WashName.phone.like(f"%{phone}%"))
    if name:
        qy = qy.filter(WashName.name.like(f"%{name}%"))
    if name_empty in ("1", "true", "yes", "on"):
        qy = qy.filter(or_(WashName.name.is_(None), WashName.name == ""))
    if province:
        provs = [p for p in province.split(",") if p.strip()]
        if provs:
            qy = qy.filter(or_(*[WashName.province.like(f"%{p}%") for p in provs]))
    if city:
        cities = [c for c in city.split(",") if c.strip()]
        if cities:
            qy = qy.filter(or_(*[WashName.city.like(f"%{c}%") for c in cities]))
    if operator:
        qy = qy.filter(WashName.operator.like(f"%{operator}%"))
    total, rows = paginate(qy.order_by(WashName.id.desc()), page, per_page)
    data = [{
        "id": w.id, "phone": w.phone or "", "name": w.name or "",
        "province": w.province or "", "city": w.city or "", "operator": w.operator or "",
        "created_at": fmt_dt(w.created_at), "updated_at": fmt_dt(w.updated_at),
    } for w in rows]
    return ok_page(data, total)


def _map_wash_row(header, values):
    row = {}
    for i, h in enumerate(header):
        if i >= len(values):
            continue
        hn = re.sub(r"\s+", "", str(h))
        v = values[i]
        sv = None if v is None else str(v).strip()
        if not sv:
            continue
        if "手机号" in hn:
            row["phone"] = sv
        elif "姓名" in hn:
            row["name"] = sv
        elif "省" in hn:
            row["province"] = sv
        elif "市" in hn:
            row["city"] = sv
        elif "运营商" in hn:
            row["operator"] = sv
    return row


def _parse_wash_csv(content):
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        return []
    return [_map_wash_row(header, values) for values in reader]


def _parse_wash_xlsx(content):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = []
    header = None
    for values in ws.iter_rows(values_only=True):
        if header is None:
            header = values
            continue
        rows.append(_map_wash_row(header, values))
    wb.close()
    return rows


@router.post("/wash-names/import")
async def import_wash_names(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(get_current_user)):
    fn = file.filename or ""
    content = await file.read()
    if fn.lower().endswith(".csv"):
        rows = _parse_wash_csv(content)
    elif fn.lower().endswith((".xlsx", ".xls")):
        rows = _parse_wash_xlsx(content)
    else:
        raise HTTPException(status_code=422, detail="仅支持 csv / xlsx 文件")
    imported = 0
    updated = 0
    for r in rows:
        phone = r.get("phone")
        if not phone:
            continue
        w = db.query(WashName).filter(WashName.phone == phone).first()
        if w:
            if r.get("name"):
                w.name = r["name"]
            if r.get("province"):
                w.province = r["province"]
            if r.get("city"):
                w.city = r["city"]
            if r.get("operator"):
                w.operator = r["operator"]
            updated += 1
        else:
            if not r.get("name"):
                continue
            db.add(WashName(phone=phone, name=r.get("name"), province=r.get("province"),
                            city=r.get("city"), operator=r.get("operator")))
            imported += 1
    db.commit()
    return {"code": 0, "data": {"imported": imported, "updated": updated},
            "msg": f"导入 {imported} 条，更新 {updated} 条"}


@router.post("/wash-names/batch-delete")
def batch_delete_wash_names(body: BatchStopBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(WashName).filter(WashName.id.in_(body.ids)).all()
    for r in rows:
        db.delete(r)
    db.commit()
    return {"code": 0, "data": {"deleted": len(rows)}, "msg": f"已删除 {len(rows)} 条洗名数据"}


@router.delete("/wash-names")
def clear_wash_names(db: Session = Depends(get_db), _=Depends(get_current_user)):
    n = db.query(WashName).count()
    db.query(WashName).delete()
    db.commit()
    return {"code": 0, "data": {"cleared": n}, "msg": f"已清空 {n} 条洗名库数据"}


def _task_suffix(task_name):
    """任务名只保留尾缀（最后一个 - 之后的内容）"""
    tn = (task_name or "").strip()
    return tn.rsplit("-", 1)[-1] if "-" in tn else tn


def _strip_task_prefix(task_name, city, province):
    """去掉任务名中的「代理编号+代理名+地区」前缀，返回实际任务名"""
    tn = (task_name or "").strip()
    parts = [p for p in tn.split("-") if p.strip()]
    if not parts:
        return tn
    idx = 1 if parts[0].isdigit() else 0
    region = (city or "").strip() or (province or "").strip()
    if region:
        for i in range(idx, len(parts)):
            if parts[i] == region:
                idx = i + 1
                break
    return "-".join(parts[idx:]) if idx < len(parts) else tn


def _pinyin_key(s):
    """把中文转成拼音（用于排序）"""
    try:
        from pypinyin import lazy_pinyin
        return "".join(lazy_pinyin(str(s or "")))
    except Exception:  # noqa
        return str(s or "")


def _fill_distribute_file(tpl_bytes, records):
    """用模版字节 + 日活数据记录（含手机号/省市/运营商/渠道/平台/任务名）生成单个文件；
    若存在「是否撞库」的记录，则在末尾追加「近期申请记录」列（该类记录填历史，无历史填「无」，其余为空）。"""
    from openpyxl import load_workbook, Workbook
    from openpyxl.styles import Alignment, Border, Side, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from ..tidabiao import _header_field, _cell_value_split
    has_collision = any(rec.get("check_collision") for rec in records)
    green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    if tpl_bytes:
        wb = load_workbook(io.BytesIO(tpl_bytes))
        ws = wb.active
        thin = Side(style="thin", color="000000")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        header_row = 1
        headers = [c.value for c in ws[header_row]]
        if all(h is None or str(h).strip() == "" for h in headers):
            header_row = 2
            headers = [c.value for c in ws[header_row]]
        colmap = [(j, _header_field(h) if h else None) for j, h in enumerate(headers, 1)]
        hist_col = len(headers) + 1
        if ws.max_row > header_row:
            ws.delete_rows(header_row + 1, ws.max_row - header_row)
        if has_collision:
            max_w = sum(2 if ord(ch) > 127 else 1 for ch in "近期申请记录")
            for rec in records:
                for line in (rec.get("history") or []):
                    max_w = max(max_w, sum(2 if ord(ch) > 127 else 1 for ch in str(line)))
            hc = ws.cell(row=header_row, column=hist_col, value="近期申请记录")
            hc.alignment = center
            hc.border = border
            hc.font = Font(bold=True)
            hc.fill = green
            ws.column_dimensions[get_column_letter(hist_col)].width = min(max_w + 2, 60)
        row = header_row + 1
        for rec in records:
            for j, m in colmap:
                if not m:
                    continue
                kind, key = m
                value = _cell_value_split(kind, key, rec, rec.get("url", ""))
                cell = ws.cell(row=row, column=j, value=value)
                cell.alignment = center
                cell.border = border
            if has_collision:
                hist = "\n".join(rec.get("history") or [])
                hcell = ws.cell(row=row, column=hist_col, value=hist)
                hcell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                hcell.border = border
            row += 1
    else:
        wb = Workbook()
        ws = wb.active
        ws.append(["手机号"] + (["近期申请记录"] if has_collision else []))
        for rec in records:
            ws.append([rec.get("url", "")] + (["\n".join(rec.get("history") or [])] if has_collision else []))
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def _fill_bill_file(cust_label, date_str, bill, tpl_bytes=None):
    """生成单个代理的账单 excel；配置了账单模版则按模版填充，否则用默认格式"""
    if tpl_bytes:
        return _fill_bill_file_from_template(tpl_bytes, cust_label, date_str, bill)
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "账单"
    qty = bill["qty"]
    sales = round(float(bill["sales"]), 2)
    unit = round(sales / qty, 4) if qty else 0
    rows = [
        ["代理", cust_label],
        ["业务日期", date_str],
        ["进货量", qty],
        ["单价(元/条)", unit],
        ["销售金额(元)", sales],
    ]
    for r in rows:
        ws.append(r)
    ws.append([])
    ws.append(["任务名", "手机号数量", "金额(元)"])
    for g, gg in sorted(bill.get("groups", {}).items(),
                        key=lambda kv: _pinyin_key(kv[1].get("task_name") or kv[0])):
        ws.append([gg.get("task_name") or g, gg["qty"], round(float(gg["amount"]), 2)])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def _copy_cell_style(src, dst):
    """把源单元格的字体/边框/填充/对齐/数字格式复制到目标单元格"""
    import copy as _copy
    if src.has_style:
        dst.font = _copy.copy(src.font)
        dst.border = _copy.copy(src.border)
        dst.fill = _copy.copy(src.fill)
        dst.number_format = src.number_format
        dst.protection = _copy.copy(src.protection)
        dst.alignment = _copy.copy(src.alignment)


def _fill_bill_file_from_template(tpl_bytes, cust_label, date_str, bill):
    """按账单模版结构填充：
    汇总区（客户/业务日期/进货量/销售金额/余额）填右侧值单元格；
    明细表（任务名/数量/单价/是否洗名/金额）按表头定位列并填充数据行，
    当模版空白行数不足时自动插行并复制样式，不影响整体版式。
    """
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(tpl_bytes))
    ws = wb.active

    qty = bill["qty"]
    sales = round(float(bill["sales"]), 2)
    balance = bill.get("balance")
    groups = sorted(bill.get("groups", {}).items(),
                    key=lambda kv: _pinyin_key(kv[1].get("task_name") or kv[0]))

    # ---- 1. 汇总区：标签 -> 右侧值单元格 ----
    def _summary_field(s):
        if s in ("客户", "客户名称", "代理", "代理名称", "客户名"):
            return "客户"
        if "日期" in s:
            return "日期"
        if "进货" in s:
            return "进货量"
        if "销售" in s:
            return "销售金额"
        if "余额" in s:
            return "余额"
        return None

    summary_vals = {
        "客户": cust_label,
        "日期": date_str,
        "进货量": qty,
        "销售金额": sales,
        "余额": (round(float(balance), 2) if balance is not None else ""),
    }
    # 值单元格：标签右侧的第一个合并区间左上角（如 E 列），无合并则用相邻列
    merged_by_row = {}
    for rng in ws.merged_cells.ranges:
        if rng.min_col > 1:
            merged_by_row.setdefault(rng.min_row, rng.min_col)
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is None:
                continue
            field = _summary_field(str(cell.value).strip())
            if field:
                target_col = merged_by_row.get(cell.row, cell.column + 1)
                ws.cell(row=cell.row, column=target_col, value=summary_vals[field])

    # ---- 2. 明细表：定位表头行与各列 ----
    header_row = None
    cols = {}
    for row in ws.iter_rows():
        rowvals = {}
        for cell in row:
            if cell.value is not None:
                rowvals[cell.column] = str(cell.value).strip()
        has_task = any(("任务" in v or "小组" in v) for v in rowvals.values())
        has_qty = any("数量" in v for v in rowvals.values())
        has_amount = any("金额" in v for v in rowvals.values())
        if has_task and has_qty and has_amount:
            header_row = row[0].row
            for col, v in rowvals.items():
                if "任务" in v or "小组" in v:
                    cols["task"] = col
                elif "工单" in v or "任务id" in v or "订单编号" in v or "订单号" in v:
                    cols["task_id"] = col
                elif "类型" in v or "渠道" in v:
                    cols["channel"] = col
                elif "运营商" in v:
                    cols["operator"] = col
                elif "单价" in v or "价格" in v:
                    cols["price"] = col
                elif "洗名" in v or "加名" in v:
                    cols["name"] = col
                elif "数量" in v:
                    cols["qty"] = col
                elif "金额" in v:
                    cols["amount"] = col
            break

    if header_row is None:
        return _fill_bill_file(cust_label, date_str, bill, None)

    # 找合计行（表头下方第一个含「合计/总计」的行）
    total_row = None
    for r in range(header_row + 1, ws.max_row + 2):
        for c in range(1, ws.max_column + 2):
            v = ws.cell(row=r, column=c).value
            if v is not None and ("合计" in str(v) or "总计" in str(v)):
                total_row = r
                break
        if total_row:
            break

    data_start = header_row + 1
    data_end = (total_row - 1) if total_row else ws.max_row
    n_blank = max(0, data_end - data_start + 1)
    n_groups = len(groups)

    # 空白行不足时自动插行（插在合计行之前，或末尾）
    if n_groups > n_blank:
        insert_at = total_row if total_row else (data_end + 1)
        ws.insert_rows(insert_at, amount=n_groups - n_blank)

    # 参考样式行：优先第一条数据行（空白行自带边框样式），否则用表头行
    ref_row = data_start if n_blank >= 1 else header_row
    ref_cols = [c for c in cols.values() if c is not None]

    # 斑马纹：识别模版已有数据行中「填充行」的奇偶性与填充样式，用于还原新插入行的斑马纹
    import copy as _copy
    striped_fill = None
    striped_parity = None
    for i in range(n_blank):
        c = ws.cell(row=data_start + i, column=ref_cols[0])
        if c.fill and c.fill.patternType == 'solid':
            striped_fill = _copy.copy(c.fill)
            striped_parity = i % 2
            break

    for i, (g, gg) in enumerate(groups):
        r = data_start + i
        if "task" in cols:
            ws.cell(row=r, column=cols["task"], value=(gg.get("task_name") or g))
        if "task_id" in cols:
            ws.cell(row=r, column=cols["task_id"], value=(gg.get("order_no") or g))
        if "channel" in cols:
            ws.cell(row=r, column=cols["channel"], value=(gg.get("channel") or ""))
        if "operator" in cols:
            ws.cell(row=r, column=cols["operator"], value=(gg.get("operator") or ""))
        if "qty" in cols:
            ws.cell(row=r, column=cols["qty"], value=gg["qty"])
        if "price" in cols:
            ws.cell(row=r, column=cols["price"], value=(gg.get("unit") or 0))
        if "name" in cols:
            ws.cell(row=r, column=cols["name"], value=("是" if gg.get("add_name") else "否"))
        if "amount" in cols:
            ws.cell(row=r, column=cols["amount"], value=round(float(gg["amount"]), 2))
        # 仅对「新插入」的行复制样式（原有空白行保留模版本来的样式）
        if i >= n_blank:
            for c in ref_cols:
                _copy_cell_style(ws.cell(row=ref_row, column=c), ws.cell(row=r, column=c))
            # 还原斑马纹：与模版填充行同奇偶的新行补上填充色
            if striped_fill is not None and (i % 2) == striped_parity:
                for c in ref_cols:
                    ws.cell(row=r, column=c).fill = _copy.copy(striped_fill)

    # 修正合计行的 SUM 公式范围（openpyxl 插行不会自动调整公式范围）
    if n_groups > n_blank and total_row:
        from openpyxl.utils import get_column_letter
        new_total_row = total_row + (n_groups - n_blank)
        end_row = data_start + n_groups - 1
        for c in range(1, ws.max_column + 1):
            cell = ws.cell(row=new_total_row, column=c)
            if cell.value is not None and "SUM(" in str(cell.value):
                letter = get_column_letter(c)
                cell.value = f"=SUM({letter}{data_start}:{letter}{end_row})"

    # 任务名 / 订单编号列宽度自适应内容（中文按 2 个字符宽度计）
    from openpyxl.utils import get_column_letter as _gcl
    for key, attr in [("task", "task_name"), ("task_id", "order_no")]:
        if key not in cols:
            continue
        max_w = 0
        for i, (g, gg) in enumerate(groups):
            val = str(gg.get(attr) or g)
            w = sum(2 if ord(ch) > 127 else 1 for ch in val)
            max_w = max(max_w, w)
        if max_w > 0:
            ws.column_dimensions[_gcl(cols[key])].width = min(max_w + 2, 60)

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def _attach_history(db, jobs, date_obj):
    """给「是否撞库=是」的记录补充「近期申请记录」：手机号在日活历史中（早于本次数据日期）最近三次出现的日期+平台"""
    phones = set()
    for job in jobs:
        for rec in job["records"]:
            if rec.get("check_collision") and rec.get("url"):
                phones.add(rec["url"])
    phones = sorted(phones)
    history_map = {}
    CHUNK = 500
    for i in range(0, len(phones), CHUNK):
        chunk = phones[i:i + CHUNK]
        rows = db.query(DailyData.phone, DailyData.biz_date, DailyData.platform).filter(
            DailyData.phone.in_(chunk), DailyData.biz_date < date_obj
        ).order_by(DailyData.phone, DailyData.biz_date.desc()).all()
        for phone, bd, pf in rows:
            lst = history_map.setdefault(phone, [])
            if any(x[0] == bd for x in lst):
                continue
            if len(lst) < 3:
                lst.append((bd, pf or ""))
    for job in jobs:
        for rec in job["records"]:
            if not rec.get("check_collision"):
                continue
            lst = history_map.get(rec.get("url"), [])
            rec["history"] = [f"{bd.strftime('%Y%m%d')} {pf or '未知'}" for bd, pf in lst] or ["无"]


def _build_distribute_zip(jobs, bills, date_str, progress_cb, bill_tpls=None):
    import zipfile
    buf = io.BytesIO()
    used_names = set()
    folder_totals = {}
    for job in jobs:
        folder_totals[job["cust_code"]] = folder_totals.get(job["cust_code"], 0) + len(job["records"])
    folder_of = {cc: f"{cc}-{folder_totals[cc]}" for cc in folder_totals}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, job in enumerate(jobs):
            parts = [date_str, job["cust_code"]]
            if job["sec_agent"]:
                parts.append(job["sec_agent"])
            if job["group_name"]:
                parts.append(job["group_name"])
            parts.append(str(len(job["records"])))
            base = "-".join(parts)
            filename = base + ".xlsx"
            n = 1
            while filename in used_names:
                n += 1
                filename = f"{base}-{n}.xlsx"
            used_names.add(filename)
            folder = folder_of[job["cust_code"]]
            bio = _fill_distribute_file(job["tpl_bytes"], job["records"])
            zf.writestr(f"{folder}/{filename}", bio.read())
            if progress_cb:
                progress_cb(i + 1)
        # 各代理账单 excel
        for cc, bill in bills.items():
            folder = folder_of.get(cc)
            if not folder:
                continue
            tpl = (bill_tpls or {}).get(cc)
            bio = _fill_bill_file(bill.get("cust_label") or cc, date_str, bill, tpl)
            bal = float(bill.get("balance") or 0)
            sign = "正" if bal >= 0 else "负"
            abs_bal = round(abs(bal), 2)
            filename = f"账单-{date_str}（余额{sign}{abs_bal}）.xlsx"
            zf.writestr(f"{folder}/{filename}", bio.read())
    buf.seek(0)
    return buf


@router.post("/daily-data/distribute")
def distribute_daily(body: GenerateBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """分数据：按小组名分组，用出数模版生成文件，按一级代理建文件夹"""

    if not body.date:
        raise HTTPException(status_code=422, detail="请选择数据日期")
    try:
        date_obj = datetime.strptime(body.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="日期格式错误")

    rows = db.query(DailyData).filter(DailyData.biz_date == date_obj).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"数据日期 {body.date} 没有可分发的数据")

    # 1. 先把分数据对象（日活数据）全部与订单数据关联（按任务id）
    orders_info = {}
    for d in rows:
        if not d.task_id or d.task_id in orders_info:
            continue
        order = db.query(Order).filter(Order.task_id == d.task_id).first()
        if not order:
            continue
        cust = db.query(Customer).filter(Customer.id == order.customer_id).first()
        tpl = db.query(Template).filter(Template.id == order.tpl_id).first() if order.tpl_id else None
        ch = db.query(Channel).filter(Channel.id == order.channel_id).first()
        op = db.query(Operator).filter(Operator.id == order.operator_id).first()
        # 上游单价（成本）：客户管理里「上游」客户按渠道（dpi 渠道再按运营商）设定的单价
        up_price = 0.0
        if order.upstream_id and order.channel_id:
            up_q = db.query(CustomerPrice).filter(CustomerPrice.customer_id == order.upstream_id,
                                                  CustomerPrice.channel_id == order.channel_id)
            up_cp = up_q.filter(CustomerPrice.operator_id == order.operator_id).first()
            if not up_cp:
                up_cp = up_q.filter(CustomerPrice.operator_id.is_(None)).first()
            if up_cp:
                up_price = float(up_cp.price)
        orders_info[d.task_id] = {
            "tpl_code": tpl.code if tpl else "",
            "group_name": order.group_name or "",
            "task_name": order.task_name or "",
            "order_no": order.order_no or "",
            "stop_date": order.stop_date,
            "city": order.city or "",
            "province": order.province or "",
            "channel": ch.name if ch else "",
            "operator": op.name if op else "",
            "cust_code": cust.code if cust else "",
            "cust_name": cust.name if cust else "",
            "sec_agent": order.secondary_agent or "",
            "tpl_bytes": bytes(tpl.file_data) if tpl and tpl.file_data else None,
            "price": float(order.price) if order.price is not None else 0,
            "customer_id": order.customer_id,
            "add_name": bool(order.add_name),
            "check_collision": bool(order.check_collision),
            "upstream_price": up_price,
        }

    if not orders_info:
        raise HTTPException(status_code=404, detail="没有可分发的数据（任务id未关联到订单）")

    # 停单(t+2)之后仍在出数的数据：不分发、不记账
    stopped_tids = {tid for tid, info in orders_info.items()
                    if info.get("stop_date") and date_obj > info["stop_date"] + timedelta(days=2)}

    # 2. 校验：小组名/一级代理 不能为空
    for tid, info in orders_info.items():
        if not info["group_name"]:
            raise HTTPException(status_code=400, detail=f"订单「{tid}」的小组名为空，无法分数据")
        if not info["cust_code"]:
            raise HTTPException(status_code=400, detail=f"订单「{tid}」的一级代理为空，无法分数据")

    # 3. 按小组聚合，校验出数模版/一级代理/二级代理一致性
    group_meta = {}
    for tid, info in orders_info.items():
        g = info["group_name"]
        m = group_meta.setdefault(g, {"tpl": set(), "cust": set(), "sec": set(), "set_tid": None})
        m["tpl"].add(info["tpl_code"])
        m["cust"].add(info["cust_code"])
        m["sec"].add(info["sec_agent"])
        if info["tpl_code"] and m["set_tid"] is None:
            m["set_tid"] = tid

    soft_issues = []
    for g, m in group_meta.items():
        set_tpls = {t for t in m["tpl"] if t}
        if len(set_tpls) > 1:
            raise HTTPException(status_code=400, detail=f"小组「{g}」对应多个出数模版：{'、'.join(sorted(set_tpls))}")
        if not set_tpls:
            raise HTTPException(status_code=400, detail=f"小组「{g}」的出数模版为空，无法分数据")
        if len(m["cust"]) > 1:
            raise HTTPException(status_code=400, detail=f"小组「{g}」对应多个一级代理：{'、'.join(sorted(m['cust']))}")
        if len(m["sec"]) > 1:
            raise HTTPException(status_code=400, detail=f"小组「{g}」对应多个二级代理：{'、'.join(sorted(m['sec']))}")
        if "" in m["tpl"]:
            unset_count = sum(1 for info in orders_info.values() if info["group_name"] == g and not info["tpl_code"])
            soft_issues.append({"group_name": g, "tpl_code": sorted(set_tpls)[0], "unset_count": unset_count})

    # 4. 有未设定出数模版的订单时，提示是否继续
    if soft_issues and not body.confirm:
        detail = "、".join(f"「{s['group_name']}」{s['unset_count']}个订单未设定出数模版" for s in soft_issues)
        return {"code": 0, "data": {"needs_confirm": True, "issues": soft_issues},
                "msg": f"以下小组存在未设定出数模版的订单：{detail}"}

    # 5. 按小组名分组（同一小组的数据合并到一个文件，使用小组已设定的出数模版）
    jobs = {}
    for d in rows:
        if not d.task_id or d.task_id not in orders_info or d.task_id in stopped_tids:
            continue
        info = orders_info[d.task_id]
        g = info["group_name"]
        if g not in jobs:
            src = orders_info[group_meta[g]["set_tid"]]
            jobs[g] = {
                "records": [],
                "cust_code": src["cust_code"],
                "sec_agent": src["sec_agent"],
                "group_name": g,
                "tpl_bytes": src["tpl_bytes"],
            }
        jobs[g]["records"].append({
            "url": d.phone or "",
            "name": d.name or "",
            "province": d.province or "",
            "city": d.city or "",
            "operator": d.operator or "",
            "channel": d.channel or "",
            "platform": d.platform or "",
            "task_name": d.task_name or "",
            "task_id": d.task_id or "",
            "check_collision": info["check_collision"],
        })

    jobs = list(jobs.values())
    jobs.sort(key=lambda j: j["cust_code"])

    # 6. 计算各代理账单（进货量、销售金额 = 手机号 × 订单单价）
    bills = {}
    for d in rows:
        if not d.task_id or d.task_id not in orders_info or d.task_id in stopped_tids:
            continue
        info = orders_info[d.task_id]
        cc = info["cust_code"]
        if cc not in bills:
            label = (f"{cc} {info['cust_name']}".strip() if info["cust_name"] else cc)
            cust = db.query(Customer).filter(Customer.id == info["customer_id"]).first()
            bills[cc] = {"customer_id": info["customer_id"], "cust_label": label,
                         "qty": 0, "sales": 0.0, "cost": 0.0,
                         "balance": float(cust.balance) if cust and cust.balance is not None else 0,
                         "groups": {}}
        bills[cc]["qty"] += 1
        eff_price = info["price"] + (0.01 if info["add_name"] else 0)
        bills[cc]["sales"] += eff_price
        bills[cc]["cost"] += info["upstream_price"]
        gg = bills[cc]["groups"].setdefault(d.task_id,
                                            {"task_name": info["task_name"] or info["group_name"],
                                             "order_no": info["order_no"],
                                             "channel": info["channel"], "operator": info["operator"],
                                             "qty": 0, "amount": 0.0, "unit": info["price"], "add_name": info["add_name"]})
        gg["qty"] += 1
        gg["amount"] += eff_price

    # 7. 保存账单（按客户+日期 upsert；余额 = 客户余额 - 销售金额），并同步客户余额
    for cc, b in bills.items():
        cid = b.get("customer_id")
        if not cid:
            continue
        cust = db.query(Customer).filter(Customer.id == cid).first()
        existing = db.query(Bill).filter(Bill.customer_id == cid, Bill.biz_date == date_obj).first()
        balance = float(cust.balance) if cust and cust.balance is not None else 0
        # 重复分发时：把上次已扣的销售金额加回来，恢复到扣减前的基础余额，避免重复扣减
        if existing and existing.sales is not None:
            balance = round(balance + float(existing.sales), 2)
        bill_balance = round(balance - float(b["sales"]), 2)
        b["balance"] = bill_balance
        profit = round(float(b["sales"]) - float(b["cost"]), 2)
        if existing:
            existing.purchase_qty = b["qty"]
            existing.sales = b["sales"]
            existing.balance = bill_balance
            existing.profit = profit
        else:
            db.add(Bill(customer_id=cid, biz_date=date_obj, purchase_qty=b["qty"],
                        sales=b["sales"], balance=bill_balance, profit=profit))
        if cust is not None:
            cust.balance = bill_balance
    db.commit()

    # 7.5 各代理账单模版（客户配置了账单模版则按模版生成）
    bill_tpls = {}
    for cc, b in bills.items():
        cid = b.get("customer_id")
        if not cid:
            continue
        cust = db.query(Customer).filter(Customer.id == cid).first()
        if cust and cust.bill_tpl_id:
            tpl = db.query(Template).filter(Template.id == cust.bill_tpl_id).first()
            if tpl and tpl.file_data:
                bill_tpls[cc] = bytes(tpl.file_data)

    task_id = uuid.uuid4().hex
    _DISTRIBUTE_TASKS[task_id] = {"total": len(jobs), "done": 0, "status": "running",
                                  "error": "", "buffer": None, "date_str": date_obj.strftime("%m%d")}

    def run():
        db2 = SessionLocal()
        try:
            _attach_history(db2, jobs, date_obj)
            buf = _build_distribute_zip(jobs, bills, date_obj.strftime("%m%d"),
                                        lambda done: _DISTRIBUTE_TASKS[task_id].update(done=done),
                                        bill_tpls)
            _DISTRIBUTE_TASKS[task_id]["buffer"] = buf
            _DISTRIBUTE_TASKS[task_id]["status"] = "done"
        except Exception as e:  # noqa
            _DISTRIBUTE_TASKS[task_id]["status"] = "error"
            _DISTRIBUTE_TASKS[task_id]["error"] = str(e)
        finally:
            db2.close()

    threading.Thread(target=run, daemon=True).start()
    return {"code": 0, "data": {"task_id": task_id, "total": len(jobs)}, "msg": "分数据任务已启动"}


@router.get("/daily-data/distribute/progress/{task_id}")
def distribute_progress(task_id: str, _=Depends(get_current_user)):
    t = _DISTRIBUTE_TASKS.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "data": {"total": t["total"], "done": t["done"], "status": t["status"], "error": t["error"]}, "msg": "ok"}


@router.get("/daily-data/distribute/download/{task_id}")
def distribute_download(task_id: str, _=Depends(get_current_user)):
    from urllib.parse import quote
    from fastapi.responses import Response
    t = _DISTRIBUTE_TASKS.get(task_id)
    if not t or t["status"] != "done" or not t["buffer"]:
        raise HTTPException(status_code=404, detail="任务未完成或不存在")
    buf = t["buffer"]
    buf.seek(0)
    date_str = t.get("date_str", "")
    return Response(content=buf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote('分数据-' + date_str + '.zip')}"})


# ============ 源文件管理 ============
@router.get("/source-files")
def list_source_files(db: Session = Depends(get_db), _=Depends(get_current_user),
                      q: str = "", biz_date: str = "", page: int = 1, per_page: int = 10):
    qy = db.query(SourceFile)
    if q:
        qy = qy.filter(SourceFile.filename.like(f"%{q}%"))
    if biz_date:
        qy = qy.filter(SourceFile.biz_date == biz_date)
    total, rows = paginate(qy.order_by(SourceFile.id.desc()), page, per_page)
    data = [{"id": s.id, "filename": s.filename, "file_type": s.file_type,
             "biz_date": s.biz_date, "party": s.party, "size": s.size,
             "created_at": fmt_dt(s.created_at)} for s in rows]
    return ok_page(data, total)


@router.get("/source-files/{sid}/download")
def download_source_file(sid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    from urllib.parse import quote
    from fastapi.responses import Response
    s = db.query(SourceFile).filter(SourceFile.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="文件不存在")
    media = "application/zip" if s.file_type == "zip" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(content=bytes(s.file_data), media_type=media,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(s.filename)}"})


@router.delete("/source-files/{sid}")
def delete_source_file(sid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    s = db.query(SourceFile).filter(SourceFile.id == sid).first()
    if not s:
        raise HTTPException(status_code=404, detail="文件不存在")
    db.delete(s)
    db.commit()
    return {"code": 0, "data": None, "msg": "已删除"}


# ============ 公积金 ============
@router.get("/fund")
def list_fund(db: Session = Depends(get_db), _=Depends(get_current_user),
              q: str = "", phone: str = "", name: str = "", id_card: str = "", gender: str = "",
              province: str = "", city: str = "", company: str = "", company_type: str = "",
              deposit_status: str = "", operator: str = "", source_file: str = "",
              page: int = 1, per_page: int = 10):
    qy = db.query(Fund)
    if q:
        like = f"%{q}%"
        qy = qy.filter(or_(Fund.phone.like(like), Fund.name.like(like),
                           Fund.company.like(like), Fund.province.like(like), Fund.id_card.like(like)))
    if phone:
        qy = qy.filter(Fund.phone.like(f"%{phone}%"))
    if name:
        qy = qy.filter(Fund.name.like(f"%{name}%"))
    if id_card:
        qy = qy.filter(Fund.id_card.like(f"%{id_card}%"))
    if gender:
        qy = qy.filter(Fund.gender == gender)
    if province:
        qy = qy.filter(Fund.province.like(f"%{province}%"))
    if city:
        qy = qy.filter(Fund.city.like(f"%{city}%"))
    if company:
        qy = qy.filter(Fund.company.like(f"%{company}%"))
    if company_type:
        qy = qy.filter(Fund.company_type.like(f"%{company_type}%"))
    if deposit_status:
        qy = qy.filter(Fund.deposit_status == deposit_status)
    if operator:
        qy = qy.filter(Fund.operator == operator)
    if source_file:
        qy = qy.filter(Fund.source_file.like(f"%{source_file}%"))
    total, rows = paginate(qy.order_by(Fund.id.desc()), page, per_page)
    return ok_page([_fund_dict(f) for f in rows], total)


@router.delete("/fund/{fid}")
def delete_fund(fid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    db.query(Fund).filter(Fund.id == fid).delete()
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.post("/fund/import")
async def import_fund(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(get_current_user)):
    fn = file.filename or ""
    content = await file.read()
    if fn.lower().endswith(".csv"):
        rows = _parse_fund_csv(content)
    elif fn.lower().endswith((".xlsx", ".xls")):
        rows = _parse_fund_xlsx(content)
    else:
        raise HTTPException(status_code=422, detail="仅支持 csv / xlsx 文件")
    n = 0
    for r in rows:
        phone = r.get("phone")
        if not phone:
            continue
        db.add(Fund(
            phone=phone, name=r.get("name"), id_card=r.get("id_card"), gender=r.get("gender"),
            province=r.get("province"), city=r.get("city"), company=r.get("company"),
            company_type=r.get("company_type"),
            base=_num(r.get("base")), ratio=r.get("ratio"), monthly=_num(r.get("monthly")),
            balance=_num(r.get("balance")), deposit_status=r.get("deposit_status"),
            open_date=r.get("open_date"), pay_to=r.get("pay_to"), operator=r.get("operator"),
            source_file=r.get("source_file") or fn))
        n += 1
    db.commit()
    return {"code": 0, "data": {"imported": n}, "msg": f"导入 {n} 条"}


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _map_row(header, values):
    idx = {str(h).strip(): i for i, h in enumerate(header)}
    row = {}
    for name, field in FUND_HEADER_MAP.items():
        if name in idx and idx[name] < len(values):
            v = values[idx[name]]
            row[field] = None if v is None else str(v).strip()
    return row


def _parse_fund_csv(content):
    text = content.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        return []
    return [_map_row(header, values) for values in reader]


def _parse_fund_xlsx(content):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows = []
    header = None
    for values in ws.iter_rows(values_only=True):
        if header is None:
            header = values
            continue
        rows.append(_map_row(header, values))
    wb.close()
    return rows


def _fund_dict(f: Fund):
    return {
        "id": f.id, "phone": f.phone, "name": f.name, "id_card": f.id_card, "gender": f.gender,
        "province": f.province, "city": f.city, "company": f.company, "company_type": f.company_type,
        "base": float(f.base) if f.base is not None else None, "ratio": f.ratio,
        "monthly": float(f.monthly) if f.monthly is not None else None,
        "balance": float(f.balance) if f.balance is not None else None,
        "deposit_status": f.deposit_status, "open_date": f.open_date, "pay_to": f.pay_to,
        "operator": f.operator, "source_file": f.source_file,
    }


@router.get("/fund/export")
def export_fund(db: Session = Depends(get_db), _=Depends(get_current_user),
                q: str = "", phone: str = "", name: str = "", gender: str = "",
                province: str = "", city: str = "", company: str = "",
                deposit_status: str = ""):
    qy = db.query(Fund)
    if q:
        like = f"%{q}%"
        qy = qy.filter(or_(Fund.phone.like(like), Fund.name.like(like),
                           Fund.company.like(like), Fund.province.like(like)))
    if phone:
        qy = qy.filter(Fund.phone.like(f"%{phone}%"))
    if name:
        qy = qy.filter(Fund.name.like(f"%{name}%"))
    if gender:
        qy = qy.filter(Fund.gender == gender)
    if province:
        qy = qy.filter(Fund.province.like(f"%{province}%"))
    if city:
        qy = qy.filter(Fund.city.like(f"%{city}%"))
    if company:
        qy = qy.filter(Fund.company.like(f"%{company}%"))
    if deposit_status:
        qy = qy.filter(Fund.deposit_status == deposit_status)
    rows = qy.order_by(Fund.id.desc()).all()
    headers = ["手机号", "姓名", "身份证号", "性别", "省份", "地市", "单位名称", "单位性质",
               "缴存基数", "缴存比例", "月缴存额", "账户余额", "缴存状态", "开户日期",
               "缴至年月", "运营商", "来源文件"]
    data = [[f.phone, f.name, f.id_card, f.gender, f.province, f.city, f.company, f.company_type,
             float(f.base) if f.base is not None else None, f.ratio,
             float(f.monthly) if f.monthly is not None else None,
             float(f.balance) if f.balance is not None else None,
             f.deposit_status, f.open_date, f.pay_to, f.operator, f.source_file] for f in rows]
    return xlsx_response(headers, data, "公积金.xlsx", "公积金")


# ============ 账单 ============
@router.get("/bills")
def list_bills(db: Session = Depends(get_db), _=Depends(get_current_user),
               q: str = "", customer: str = "", customer_id: int = 0,
               start_date: str = "", end_date: str = "",
               page: int = 1, per_page: int = 10):
    qy = db.query(Bill).outerjoin(Customer, Bill.customer_id == Customer.id)
    if q:
        qy = qy.filter(or_(Customer.name.like(f"%{q}%"), Customer.code.like(f"%{q}%")))
    if customer:
        qy = qy.filter(Customer.code.like(f"%{customer}%"))
    if customer_id:
        qy = qy.filter(Bill.customer_id == customer_id)
    if start_date:
        qy = qy.filter(Bill.biz_date >= start_date)
    if end_date:
        qy = qy.filter(Bill.biz_date <= end_date)
    total, rows = paginate(qy.order_by(Bill.biz_date.desc()), page, per_page)
    data = []
    for b in rows:
        c = db.query(Customer).filter(Customer.id == b.customer_id).first()
        data.append({
            "id": b.id, "customer": f"{c.code} {c.name}" if c else "", "customer_id": b.customer_id,
            "biz_date": str(b.biz_date), "purchase_qty": b.purchase_qty,
            "sales": float(b.sales) if b.sales is not None else 0,
            "balance": float(c.balance) if c and c.balance is not None else None,
            "profit": float(b.profit) if b.profit is not None else 0,
            "created_at": fmt_dt(b.created_at),
        })
    return ok_page(data, total)


@router.post("/bills/batch-delete")
def batch_delete_bills(body: BatchStopBody, db: Session = Depends(get_db), _=Depends(require_admin)):
    rows = db.query(Bill).filter(Bill.id.in_(body.ids)).all()
    for r in rows:
        db.delete(r)
    db.commit()
    return {"code": 0, "data": {"deleted": len(rows)}, "msg": f"已删除 {len(rows)} 条账单"}


@router.delete("/bills")
def clear_bills(db: Session = Depends(get_db), _=Depends(get_current_user)):
    n = db.query(Bill).count()
    db.query(Bill).delete()
    db.commit()
    return {"code": 0, "data": {"cleared": n}, "msg": f"已清空 {n} 条账单"}


@router.post("/bills/import")
async def import_bills(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(get_current_user)):
    """导入账单：读取「余额总览」sheet，按编号匹配客户，更新客户余额与账单
    （销售金额=本周出货金额，余额=整体所剩余额；文件名需含日期，如 账单-2026-09-29.xlsx）"""
    fn = file.filename or ""
    content = await file.read()
    if not fn.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=422, detail="仅支持 xlsx / xls 文件")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", fn)
    if not m:
        raise HTTPException(status_code=422, detail="文件名需包含日期，如 账单-2026-09-29.xlsx")
    try:
        biz_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        raise HTTPException(status_code=422, detail="文件名日期无效")

    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = None
    for name in wb.sheetnames:
        if "总览" in name or "汇总" in name:
            ws = wb[name]
            break
    if ws is None:
        ws = wb.active

    header_row = None
    code_col = sales_col = balance_col = None
    for r in range(1, ws.max_row + 1):
        rowvals = {}
        for c in range(1, ws.max_column + 1):
            v = ws.cell(row=r, column=c).value
            if v is not None:
                rowvals[c] = str(v).strip()
        if any("编号" in v for v in rowvals.values()) and any("名称" in v for v in rowvals.values()):
            header_row = r
            for c, v in rowvals.items():
                if "编号" in v:
                    code_col = c
                elif "出货" in v:
                    sales_col = c
                elif "余额" in v and "上月" not in v:
                    balance_col = c
            break

    if header_row is None or code_col is None:
        raise HTTPException(status_code=422, detail="未找到账单汇总表头（需含「编号」「名称」列）")

    updated = 0
    errors = []
    for r in range(header_row + 1, ws.max_row + 1):
        code = str(ws.cell(row=r, column=code_col).value or "").strip() if code_col else ""
        if not code:
            continue
        cust = db.query(Customer).filter(Customer.code == code).first()
        if not cust:
            name = code.replace("甲方", "").strip()
            cust = db.query(Customer).filter(Customer.name == name).first() if name else None
        if not cust:
            errors.append(f"{code}: 客户不存在")
            continue
        sales = _num(ws.cell(row=r, column=sales_col).value) if sales_col else None
        balance = _num(ws.cell(row=r, column=balance_col).value) if balance_col else None
        if sales is None and balance is None:
            errors.append(f"{code}: 出货金额/余额为空（请在 Excel 中打开并保存后再导入，以缓存公式结果）")
            continue
        if balance is not None:
            cust.balance = balance
        bill = db.query(Bill).filter(Bill.customer_id == cust.id, Bill.biz_date == biz_date).first()
        if bill:
            if sales is not None:
                bill.sales = sales
            if balance is not None:
                bill.balance = balance
        else:
            db.add(Bill(customer_id=cust.id, biz_date=biz_date, purchase_qty=0,
                        sales=(sales if sales is not None else 0),
                        balance=(balance if balance is not None else 0), profit=0))
        updated += 1
    db.commit()
    return {"code": 0, "data": {"updated": updated, "errors": errors},
            "msg": f"已更新 {updated} 个客户账单，失败 {len(errors)} 个"}


@router.get("/bills/export")
def export_bills(db: Session = Depends(get_db), _=Depends(get_current_user),
                 start_date: str = "", end_date: str = "", customer_id: int = 0):
    """按日期期间导出账单明细（含充值记录和余额）；customer_id=0 导出全部代理"""
    from urllib.parse import quote
    from fastapi.responses import Response
    import openpyxl

    cust_map = {c.id: c for c in db.query(Customer).all()}

    qy = db.query(Bill).order_by(Bill.biz_date, Bill.customer_id)
    if customer_id:
        qy = qy.filter(Bill.customer_id == customer_id)
    if start_date:
        qy = qy.filter(Bill.biz_date >= start_date)
    if end_date:
        qy = qy.filter(Bill.biz_date <= end_date)
    bills = qy.all()

    rqy = db.query(CustomerRecharge).order_by(CustomerRecharge.recharge_date, CustomerRecharge.customer_id)
    if customer_id:
        rqy = rqy.filter(CustomerRecharge.customer_id == customer_id)
    if start_date:
        rqy = rqy.filter(CustomerRecharge.recharge_date >= start_date)
    if end_date:
        rqy = rqy.filter(CustomerRecharge.recharge_date <= end_date)
    recharges = rqy.all()

    wb = openpyxl.Workbook()
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
    from openpyxl.utils import get_column_letter

    title_font = Font(bold=True, size=14)
    header_font = Font(bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="4472C4")
    zebra_fill = PatternFill("solid", fgColor="F2F6FC")
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center")
    right = Alignment(horizontal="right", vertical="center")
    money_fmt = '#,##0.00'

    # ---- 账单明细 ----
    ws1 = wb.active
    ws1.title = "账单明细"
    headers = ["客户编号", "客户名称", "业务日期", "进货量", "销售金额(元)", "余额(元)"]
    widths = [12, 16, 12, 10, 14, 14]
    period = f"{start_date or '...'} ~ {end_date or '...'}"
    ws1.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    tc = ws1.cell(row=1, column=1, value=f"账单明细（{period}）")
    tc.font = title_font
    tc.alignment = center
    ws1.row_dimensions[1].height = 26
    for j, h in enumerate(headers, 1):
        c = ws1.cell(row=2, column=j, value=h)
        c.font = header_font
        c.fill = header_fill
        c.border = border
        c.alignment = center
        ws1.column_dimensions[get_column_letter(j)].width = widths[j - 1]
    ws1.row_dimensions[2].height = 20
    r = 3
    for b in bills:
        c = cust_map.get(b.customer_id)
        row = [
            c.code if c else "", c.name if c else "",
            str(b.biz_date) if b.biz_date else "",
            b.purchase_qty if b.purchase_qty is not None else 0,
            float(b.sales) if b.sales is not None else 0,
            float(b.balance) if b.balance is not None else 0,
        ]
        for j, v in enumerate(row, 1):
            cell = ws1.cell(row=r, column=j, value=v)
            cell.border = border
            cell.alignment = right if j in (4, 5, 6) else center
            if j in (5, 6):
                cell.number_format = money_fmt
            if r % 2 == 0:
                cell.fill = zebra_fill
        r += 1

    # ---- 充值记录 ----
    ws2 = wb.create_sheet("充值记录")
    headers2 = ["客户编号", "客户名称", "充值日期", "充值金额(U)", "折算人民币(元)", "备注"]
    widths2 = [12, 16, 12, 14, 16, 24]
    ws2.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers2))
    tc2 = ws2.cell(row=1, column=1, value=f"充值记录（{period}）")
    tc2.font = title_font
    tc2.alignment = center
    ws2.row_dimensions[1].height = 26
    for j, h in enumerate(headers2, 1):
        c = ws2.cell(row=2, column=j, value=h)
        c.font = header_font
        c.fill = header_fill
        c.border = border
        c.alignment = center
        ws2.column_dimensions[get_column_letter(j)].width = widths2[j - 1]
    ws2.row_dimensions[2].height = 20
    r = 3
    for rec in recharges:
        c = cust_map.get(rec.customer_id)
        row = [
            c.code if c else "", c.name if c else "",
            str(rec.recharge_date) if rec.recharge_date else "",
            float(rec.amount_u) if rec.amount_u is not None else 0,
            float(rec.amount_rmb) if rec.amount_rmb is not None else 0,
            rec.note or "",
        ]
        for j, v in enumerate(row, 1):
            cell = ws2.cell(row=r, column=j, value=v)
            cell.border = border
            cell.alignment = right if j in (4, 5) else center
            if j in (4, 5):
                cell.number_format = money_fmt
            if r % 2 == 0:
                cell.fill = zebra_fill
        r += 1

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    period = f"{start_date or '起'}-{end_date or '止'}"
    filename = f"账单明细-{period}.xlsx"
    return Response(content=bio.getvalue(),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


@router.get("/bills/{bid}")
def bill_detail(bid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    b = db.query(Bill).filter(Bill.id == bid).first()
    if not b:
        raise HTTPException(status_code=404, detail="账单不存在")
    c = db.query(Customer).filter(Customer.id == b.customer_id).first()
    rows = (db.query(DailyData, Order)
            .join(Order, DailyData.task_id == Order.task_id)
            .filter(DailyData.biz_date == b.biz_date, Order.customer_id == b.customer_id)
            .all())
    groups = {}
    for d, o in rows:
        ch = db.query(Channel).filter(Channel.id == o.channel_id).first()
        op = db.query(Operator).filter(Operator.id == o.operator_id).first()
        task_label = o.task_name or o.group_name or "未分组"
        gg = groups.setdefault(o.task_id or "", {
            "task_name": task_label,
            "order_no": o.order_no or "",
            "channel": ch.name if ch else "",
            "operator": op.name if op else "",
            "qty": 0, "amount": 0.0,
        })
        gg["qty"] += 1
        eff_price = (float(o.price) if o.price is not None else 0) + (0.01 if o.add_name else 0)
        gg["amount"] += eff_price
    detail = {
        "id": b.id,
        "customer": (f"{c.code} {c.name}" if c else ""),
        "biz_date": str(b.biz_date),
        "purchase_qty": b.purchase_qty,
        "sales": float(b.sales) if b.sales is not None else 0,
        "balance": float(c.balance) if c and c.balance is not None else 0,
        "profit": float(b.profit) if b.profit is not None else 0,
        "created_at": fmt_dt(b.created_at),
        "groups": [{"task_name": gg["task_name"], "task_id": g, "order_no": gg["order_no"],
                    "channel": gg["channel"], "operator": gg["operator"], "qty": gg["qty"],
                    "amount": round(float(gg["amount"]), 2)}
                   for g, gg in sorted(groups.items(), key=lambda kv: _pinyin_key(kv[1]["task_name"]))],
    }
    return {"code": 0, "data": detail, "msg": "ok"}


# ============ 预警 ============
@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), _=Depends(get_current_user),
                q: str = "", level: str = "", type: str = "", status: str = "未处理",
                page: int = 1, per_page: int = 10):
    qy = db.query(Alert).outerjoin(Customer, Alert.customer_id == Customer.id)
    if q:
        like = f"%{q}%"
        qy = qy.filter(or_(Alert.content.like(like), Alert.task_name.like(like),
                           Customer.name.like(like)))
    if level:
        qy = qy.filter(Alert.level == level)
    if type:
        qy = qy.filter(Alert.type == type)
    if status:
        qy = qy.filter(Alert.status == status)
    total, rows = paginate(qy.order_by(Alert.id.desc()), page, per_page)
    data = []
    for a in rows:
        c = db.query(Customer).filter(Customer.id == a.customer_id).first()
        data.append({
            "id": a.id, "type": a.type, "customer_id": a.customer_id,
            "customer_name": f"{c.code} {c.name}" if c else "", "task_name": a.task_name,
            "order_no": a.order_no or "", "order_id": a.order_id,
            "content": a.content, "time": fmt_dt(a.trigger_time),
            "status": a.status,
        })
    return ok_page(data, total)


@router.put("/alerts/{aid}")
def handle_alert(aid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    a = db.query(Alert).filter(Alert.id == aid).first()
    if not a:
        raise HTTPException(status_code=404, detail="预警不存在")
    a.status = "已处理"
    db.commit()
    return {"code": 0, "data": None, "msg": "已处理"}


def _alert_days(db):
    cfg = db.query(SysConfig).filter(SysConfig.key == "alert_days").first()
    try:
        return int(cfg.value) if cfg and cfg.value else 0
    except (TypeError, ValueError):
        return 0


@router.get("/alert-config")
def get_alert_config(db: Session = Depends(get_db), _=Depends(get_current_user)):
    cfg = db.query(SysConfig).filter(SysConfig.key == "alert_trigger_time").first()
    return {"code": 0, "data": {"trigger_time": cfg.value if cfg else "00:00",
                                "alert_days": _alert_days(db)}, "msg": "ok"}


@router.put("/alert-config")
def set_alert_config(body: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    value = (body.get("trigger_time") or "00:00").strip()
    cfg = db.query(SysConfig).filter(SysConfig.key == "alert_trigger_time").first()
    if cfg:
        cfg.value = value
    else:
        db.add(SysConfig(key="alert_trigger_time", value=value))
    if "alert_days" in body:
        try:
            days = int(body.get("alert_days"))
        except (TypeError, ValueError):
            days = 0
        dc = db.query(SysConfig).filter(SysConfig.key == "alert_days").first()
        if dc:
            dc.value = str(days)
        else:
            db.add(SysConfig(key="alert_days", value=str(days)))
    db.commit()
    return {"code": 0, "data": None, "msg": "已保存"}


@router.post("/alerts/scan")
def manual_scan(db: Session = Depends(get_db), _=Depends(get_current_user)):
    run_alert_scan(db)
    count = db.query(func.count(Alert.id)).filter(Alert.status == "未处理").scalar() or 0
    return {"code": 0, "data": {"unhandled": int(count)}, "msg": "预警扫描完成"}


@router.get("/daily-data/filter-options")
def daily_filter_options(db: Session = Depends(get_db), _=Depends(get_current_user)):
    """日活数据筛选级联选项：品类（一级→二级→平台）、一级代理→二级代理/渠道"""
    # 一级品类 → 二级品类
    cat1 = []
    cat2_map = {}
    for c in db.query(Category).filter(Category.level == 1).order_by(Category.id).all():
        cat1.append(c.name)
        children = db.query(Category).filter(Category.level == 2, Category.parent_id == c.id).order_by(Category.id).all()
        cat2_map[c.name] = [x.name for x in children]
    # 二级品类 → 平台
    platform_map = {}
    for p in db.query(Platform).order_by(Platform.id).all():
        c2 = db.query(Category).filter(Category.id == p.cat_id).first()
        if c2:
            platform_map.setdefault(c2.name, []).append(p.name)
    # 一级代理 → 二级代理 / 渠道（customer 存储为「编号 名称」，用编号作为级联键）
    agent_map = {}
    channel_map = {}
    for cu, sa in db.query(DailyData.customer, DailyData.secondary_agent).filter(
            DailyData.customer.isnot(None), DailyData.customer != "",
            DailyData.secondary_agent.isnot(None), DailyData.secondary_agent != "").distinct().all():
        agent_map.setdefault(cu.split()[0], []).append(sa)
    for cu, ch in db.query(DailyData.customer, DailyData.channel).filter(
            DailyData.customer.isnot(None), DailyData.customer != "",
            DailyData.channel.isnot(None), DailyData.channel != "").distinct().all():
        channel_map.setdefault(cu.split()[0], []).append(ch)
    for k in agent_map:
        agent_map[k] = sorted(set(agent_map[k]))
    for k in channel_map:
        channel_map[k] = sorted(set(channel_map[k]))
    return {"code": 0, "data": {
        "cat1": cat1, "cat2_map": cat2_map, "platform_map": platform_map,
        "agent_map": agent_map, "channel_map": channel_map,
    }, "msg": "ok"}


@router.get("/distinct")
def distinct_values(db: Session = Depends(get_db), _=Depends(get_current_user),
                    model: str = "", field: str = ""):
    allowed = {
        "daily_data": {"province", "city", "platform", "upstream", "wash_status"},
        "orders": {"province", "city"},
        "fund": {"province", "city", "company_type", "operator", "source_file"},
    }
    if model not in allowed or field not in allowed[model]:
        return {"code": 0, "data": [], "msg": "ok"}
    table = {"daily_data": DailyData, "orders": Order, "fund": Fund, "customer": Customer}[model]
    col = getattr(table, field)
    rows = db.query(col).filter(col.isnot(None), col != "").distinct().order_by(col).all()
    return {"code": 0, "data": [r[0] for r in rows], "msg": "ok"}


def _apply_daily_filters(qy, f):
    f = f or {}
    if f.get("q"):
        like = f"%{f['q']}%"
        qy = qy.filter(or_(DailyData.phone.like(like), DailyData.task_name.like(like),
                           DailyData.upstream.like(like), DailyData.task_id.like(like)))
    if f.get("phone"):
        qy = qy.filter(DailyData.phone.like(f"%{f['phone']}%"))
    if f.get("upstream"):
        qy = qy.filter(DailyData.upstream.like(f"%{f['upstream']}%"))
    if f.get("task_id"):
        qy = qy.filter(DailyData.task_id.like(f"%{f['task_id']}%"))
    if f.get("task_name"):
        qy = qy.filter(DailyData.task_name.like(f"%{f['task_name']}%"))
    if f.get("province"):
        provs = [p for p in f["province"].split(",") if p.strip()]
        if provs:
            qy = qy.filter(or_(*[DailyData.province.like(f"%{p}%") for p in provs]))
    if f.get("city"):
        cities = [c for c in f["city"].split(",") if c.strip()]
        if cities:
            qy = qy.filter(or_(*[DailyData.city.like(f"%{c}%") for c in cities]))
    if f.get("operator"):
        qy = qy.filter(DailyData.operator.like(f"%{f['operator']}%"))
    if f.get("cat1"):
        qy = qy.filter(DailyData.cat1.like(f"%{f['cat1']}%"))
    if f.get("cat2"):
        qy = qy.filter(DailyData.cat2.like(f"%{f['cat2']}%"))
    if f.get("platform"):
        qy = qy.filter(DailyData.platform.like(f"%{f['platform']}%"))
    if f.get("customer"):
        qy = qy.filter(DailyData.customer.like(f"%{f['customer']}%"))
    if f.get("secondary_agent"):
        qy = qy.filter(DailyData.secondary_agent.like(f"%{f['secondary_agent']}%"))
    if f.get("channel"):
        qy = qy.filter(DailyData.channel.like(f"%{f['channel']}%"))
    if f.get("source_file"):
        qy = qy.filter(DailyData.source_file.like(f"%{f['source_file']}%"))
    if f.get("name"):
        qy = qy.filter(DailyData.name.like(f"%{f['name']}%"))
    if f.get("biz_date"):
        qy = qy.filter(DailyData.biz_date == f["biz_date"])
    return qy


@router.post("/daily-data/extract")
def extract_daily(body: ExtractBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    """单独抽取：按条件/时间段抽取日活数据，生成数据文件与账单文件，并单独记一笔账单"""
    from urllib.parse import quote
    from fastapi.responses import Response
    import zipfile
    import openpyxl

    qy = _apply_daily_filters(db.query(DailyData), body.filters)
    if body.start_date:
        sd = _parse_biz_date(body.start_date)
        if sd:
            qy = qy.filter(DailyData.biz_date >= sd)
    if body.end_date:
        ed = _parse_biz_date(body.end_date)
        if ed:
            qy = qy.filter(DailyData.biz_date <= ed)
    rows = qy.order_by(DailyData.id.desc()).all()
    if body.limit and body.limit > 0:
        rows = rows[:body.limit]
    if not rows:
        raise HTTPException(status_code=404, detail="没有符合条件的数据")

    qty = len(rows)
    price = float(body.price or 0)
    sales = round(price * qty, 2)

    cust = db.query(Customer).filter(Customer.id == body.customer_id).first() if body.customer_id else None
    target_label = (f"{cust.code} {cust.name}" if cust else (body.target_name or "其他人"))

    balance = 0
    if cust is not None:
        balance = round((float(cust.balance) if cust.balance is not None else 0) - sales, 2)
        cust.balance = balance
    db.add(Bill(customer_id=body.customer_id, biz_date=date.today(),
                purchase_qty=qty, sales=sales, balance=balance,
                profit=sales, bill_type="单独抽取",
                target_name=(body.target_name or None) if not cust else None))
    db.commit()

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        dwb = openpyxl.Workbook()
        dws = dwb.active
        dws.title = "抽取数据"
        dheaders = ["数据日期", "甲方", "任务id", "任务名", "手机号", "姓名", "省", "市", "运营商", "渠道", "平台"]
        dws.append(dheaders)
        for d in rows:
            dws.append([str(d.biz_date) if d.biz_date else "", d.upstream or "", d.task_id or "",
                        d.task_name or "", d.phone or "", d.name or "", d.province or "", d.city or "",
                        d.operator or "", d.channel or "", d.platform or ""])
        dbio = io.BytesIO()
        dwb.save(dbio)
        zf.writestr("抽取数据.xlsx", dbio.getvalue())

        bwb = openpyxl.Workbook()
        bws = bwb.active
        bws.title = "账单"
        bws.append(["收款对象", target_label])
        bws.append(["日期", date.today().strftime("%Y-%m-%d")])
        bws.append(["进货量", qty])
        bws.append(["单价(元/条)", price])
        bws.append(["销售金额(元)", sales])
        bws.append(["利润(元)", sales])
        if body.note:
            bws.append(["备注", body.note])
        bbio = io.BytesIO()
        bwb.save(bbio)
        zf.writestr("账单.xlsx", bbio.getvalue())

    bio.seek(0)
    filename = f"单独抽取-{date.today().strftime('%Y%m%d')}.zip"
    return Response(content=bio.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})


def run_alert_scan(db: Session):
    """定时：停单日临近（按预警天数）-> 停单提醒；余额低于预警额度 -> 账单预警"""
    today = date.today()
    # 停单提醒（预警天数内到期的订单）
    alert_days = _alert_days(db)
    target = today + timedelta(days=alert_days)
    for o in db.query(Order).filter(Order.stop_date.isnot(None),
                                    Order.stop_date >= today,
                                    Order.stop_date <= target).all():
        if not db.query(Alert).filter(Alert.type == "停单提醒", Alert.task_name == o.task_name,
                                      Alert.trigger_time >= datetime(today.year, today.month, today.day)).first():
            db.add(Alert(level="提醒", type="停单提醒", customer_id=o.customer_id,
                         task_name=o.task_name, order_no=o.order_no, order_id=o.id,
                         content=f"停单日 {o.stop_date} 已到达，请确认是否停单",
                         trigger_time=datetime.now()))
    # 在执/待停订单截止时间过期提醒（类型：停单提醒）
    for o in db.query(Order).filter(Order.status.in_(["在执", "待停"]),
                                    Order.end_date.isnot(None),
                                    Order.end_date <= today).all():
        if not db.query(Alert).filter(Alert.type == "停单提醒", Alert.task_name == o.task_name,
                                      Alert.trigger_time >= datetime(today.year, today.month, today.day)).first():
            db.add(Alert(level="提醒", type="停单提醒", customer_id=o.customer_id,
                         task_name=o.task_name, order_no=o.order_no, order_id=o.id,
                         content=f"截止时间 {o.end_date} 已过期（{o.task_name or o.order_no}），请确认是否处理",
                         trigger_time=datetime.now()))
    # 账单预警
    for c in db.query(Customer).filter(Customer.ctype == "downstream", Customer.status == 1).all():
        if c.warn_amount and (c.balance or 0) < c.warn_amount:
            if not db.query(Alert).filter(Alert.type == "账单预警", Alert.customer_id == c.id,
                                          Alert.status == "未处理").first():
                db.add(Alert(level="预警", type="账单预警", customer_id=c.id,
                             content=f"余额 {c.balance} 已低于预警额度 {c.warn_amount}",
                             trigger_time=datetime.now()))
    # 自动标记已解决的预警（订单已处理/余额已补足）
    for a in db.query(Alert).filter(Alert.status == "未处理").all():
        if a.type == "停单提醒":
            o = None
            if a.order_no:
                o = db.query(Order).filter(Order.order_no == a.order_no).first()
            if not o and a.task_name:
                o = db.query(Order).filter(Order.task_name == a.task_name).first()
            if not o:
                a.status = "已处理"
            elif o.status not in ("在执", "待停"):
                a.status = "已处理"
            elif (a.content or "").startswith("截止时间") and o.end_date and o.end_date > today:
                a.status = "已处理"
        elif a.type == "账单预警":
            c = db.query(Customer).filter(Customer.id == a.customer_id).first()
            if not c or not c.warn_amount or (c.balance or 0) >= c.warn_amount:
                a.status = "已处理"
    db.commit()
