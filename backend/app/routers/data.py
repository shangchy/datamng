"""数据路由：日活数据/公积金/账单/预警"""
import csv
import io
import re
import threading
import uuid
from datetime import date, datetime
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import (DailyData, Fund, Bill, Alert, Customer, Channel, Category,
                      Order, SysConfig, Operator, SourceFile, Template, WashName, Platform)
from ..pagination import paginate, ok_page
from ..excel import xlsx_response
from ..utils import fmt_dt
from ..schemas import BatchStopBody, GenerateBody

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
               channel: str = "", biz_date: str = "", page: int = 1, per_page: int = 10):
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
    if biz_date:
        qy = qy.filter(DailyData.biz_date == biz_date)
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


@router.get("/daily-data/export")
def export_daily(db: Session = Depends(get_db), _=Depends(get_current_user),
                 q: str = "", phone: str = "", upstream: str = "", task_id: str = "",
                 task_name: str = "", province: str = "", city: str = "",
                 operator: str = "", platform: str = "", source_file: str = "",
                 customer: str = "", secondary_agent: str = "", channel: str = "",
                 biz_date: str = ""):
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
    if biz_date:
        qy = qy.filter(DailyData.biz_date == biz_date)
    rows = qy.order_by(DailyData.id.desc()).limit(50000).all()
    headers = ["数据日期", "甲方", "任务id", "任务名", "手机号", "姓名", "省", "市", "运营商",
               "一级品类", "二级品类", "平台",
               "一级代理", "二级代理", "渠道", "来源文件名", "创建时间", "更新时间"]
    data = [[str(d.biz_date) if d.biz_date else "", d.upstream or "", d.task_id or "",
             d.task_name or "", d.phone or "", d.name or "", d.province or "", d.city or "",
             d.operator or "", d.cat1 or "", d.cat2 or "", d.platform or "",
             d.customer or "", d.secondary_agent or "",
             d.channel or "", d.source_file or "",
             fmt_dt(d.created_at), fmt_dt(d.updated_at)] for d in rows]
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


def _import_niu_excel(db, content, biz_date, source_file, source_file_id, errors):
    """解析牛的数据 excel（第一行是表头）：任务id/任务名/手机号/省/市/运营商"""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    n = 0
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
    return n


def _import_new_excel(db, content, biz_date, source_file, source_file_id, errors):
    """解析新的数据 excel（第一行是数据，无表头）：手机号/甲方工单号/平台/省/市"""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    n = 0
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
    return n


def _import_one_daily_file(db, fn, content, date_obj, source_file_id, errors):
    """处理单个文件（zip 或 excel），返回导入条数"""
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    if ext not in ("zip", "xlsx", "xls"):
        errors.append(f"{fn}: 仅支持 zip / xlsx / xls 文件")
        return 0
    n = 0
    if ext == "zip":
        import zipfile
        try:
            zf = zipfile.ZipFile(io.BytesIO(content))
            for name in zf.namelist():
                if name.lower().endswith((".xlsx", ".xls")):
                    try:
                        n += _import_niu_excel(db, zf.read(name), date_obj, fn, source_file_id, errors)
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
            n += _import_niu_excel(db, content, date_obj, fn, source_file_id, errors)
        else:
            n += _import_new_excel(db, content, date_obj, fn, source_file_id, errors)
    return n


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
    """统计未匹配到订单的日活数据条数"""
    order_tids = {r[0] for r in db.query(Order.task_id).all() if r[0]}
    total = 0
    for fn, content in file_list:
        for tid in _extract_task_ids(fn, content):
            if tid not in order_tids:
                total += 1
    return total


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

    # 未匹配订单时，弹出提示确认
    if not confirm:
        unmatched = _count_unmatched(db, file_list)
        if unmatched > 0:
            return {"code": 0, "data": {"needs_confirm": True, "unmatched": unmatched},
                    "msg": f"有 {unmatched} 条数据未匹配到订单"}

    imported = 0
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
        imported += _import_one_daily_file(db, fn, content, date_obj, sf.id, errors)
    db.commit()
    return {"code": 0, "data": {"imported": imported, "errors": errors},
            "msg": f"导入 {imported} 条，失败 {len(errors)} 条"}


@router.post("/daily-data/batch-delete")
def batch_delete_daily(body: BatchStopBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(DailyData).filter(DailyData.id.in_(body.ids)).all()
    for r in rows:
        db.delete(r)
    db.commit()
    return {"code": 0, "data": {"deleted": len(rows)}, "msg": f"已删除 {len(rows)} 条"}


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
    """洗名：导出所选日期下，姓名为空且关联订单「是否加名=是」的手机号"""
    from urllib.parse import quote
    from fastapi.responses import Response
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
    text = "\n".join(phones)
    return Response(content=text, media_type="text/plain",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote('洗名-' + date + '.txt')}"})


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
    updated = 0
    for phone, rec in rec_map.items():
        n = db.query(DailyData).filter(DailyData.phone == phone).update({"name": rec["name"]})
        updated += n
    for phone, rec in rec_map.items():
        # 更新洗名库（手机号存在则更新，不存在则插入）
        w = db.query(WashName).filter(WashName.phone == phone).first()
        if w:
            w.name = rec["name"]
            w.province = rec["province"]
            w.city = rec["city"]
            w.operator = rec["operator"]
        else:
            db.add(WashName(phone=phone, name=rec["name"], province=rec["province"],
                            city=rec["city"], operator=rec["operator"]))
    db.commit()
    return {"code": 0, "data": {"updated": updated}, "msg": f"已更新 {updated} 条姓名，洗名库同步更新"}


# ============ 洗名库 ============

@router.get("/wash-names")
def list_wash_names(db: Session = Depends(get_db), _=Depends(get_current_user),
                    q: str = "", phone: str = "", name: str = "",
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


def _fill_distribute_file(tpl_bytes, records):
    """用模版字节 + 日活数据记录（含手机号/省市/运营商/渠道/平台/任务名）生成单个文件"""
    from openpyxl import load_workbook, Workbook
    from openpyxl.styles import Alignment, Border, Side
    from ..tidabiao import _header_field, _cell_value_split
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
        if ws.max_row > header_row:
            ws.delete_rows(header_row + 1, ws.max_row - header_row)
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
            row += 1
    else:
        wb = Workbook()
        ws = wb.active
        ws.append(["手机号"])
        for rec in records:
            ws.append([rec.get("url", "")])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def _fill_bill_file(cust_label, date_str, bill):
    """生成单个代理的账单 excel"""
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
    ws.append(["小组", "手机号数量", "金额(元)"])
    for g, gg in sorted(bill.get("groups", {}).items()):
        ws.append([g, gg["qty"], round(float(gg["amount"]), 2)])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio


def _build_distribute_zip(jobs, bills, date_str, progress_cb):
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
            bio = _fill_bill_file(bill.get("cust_label") or cc, date_str, bill)
            zf.writestr(f"{folder}/账单-{cc}-{date_str}.xlsx", bio.read())
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
        orders_info[d.task_id] = {
            "tpl_code": tpl.code if tpl else "",
            "group_name": order.group_name or "",
            "cust_code": cust.code if cust else "",
            "cust_name": cust.name if cust else "",
            "sec_agent": order.secondary_agent or "",
            "tpl_bytes": bytes(tpl.file_data) if tpl and tpl.file_data else None,
            "price": float(order.price) if order.price is not None else 0,
            "customer_id": order.customer_id,
        }

    if not orders_info:
        raise HTTPException(status_code=404, detail="没有可分发的数据（任务id未关联到订单）")

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
        if not d.task_id or d.task_id not in orders_info:
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
            "province": d.province or "",
            "city": d.city or "",
            "operator": d.operator or "",
            "channel": d.channel or "",
            "platform": d.platform or "",
            "task_name": _task_suffix(d.task_name),
        })

    jobs = list(jobs.values())
    jobs.sort(key=lambda j: j["cust_code"])

    # 6. 计算各代理账单（进货量、销售金额 = 手机号 × 订单单价）
    bills = {}
    for d in rows:
        if not d.task_id or d.task_id not in orders_info:
            continue
        info = orders_info[d.task_id]
        cc = info["cust_code"]
        if cc not in bills:
            label = (f"{cc} {info['cust_name']}".strip() if info["cust_name"] else cc)
            bills[cc] = {"customer_id": info["customer_id"], "cust_label": label,
                         "qty": 0, "sales": 0.0, "groups": {}}
        bills[cc]["qty"] += 1
        bills[cc]["sales"] += info["price"]
        gg = bills[cc]["groups"].setdefault(info["group_name"], {"qty": 0, "amount": 0.0})
        gg["qty"] += 1
        gg["amount"] += info["price"]

    # 7. 保存账单（按客户+日期 upsert）
    for cc, b in bills.items():
        cid = b.get("customer_id")
        if not cid:
            continue
        cust = db.query(Customer).filter(Customer.id == cid).first()
        balance = float(cust.balance) if cust and cust.balance is not None else 0
        existing = db.query(Bill).filter(Bill.customer_id == cid, Bill.biz_date == date_obj).first()
        if existing:
            existing.purchase_qty = b["qty"]
            existing.sales = b["sales"]
            existing.balance = balance
        else:
            db.add(Bill(customer_id=cid, biz_date=date_obj, purchase_qty=b["qty"],
                        sales=b["sales"], balance=balance, profit=0))
    db.commit()

    task_id = uuid.uuid4().hex
    _DISTRIBUTE_TASKS[task_id] = {"total": len(jobs), "done": 0, "status": "running",
                                  "error": "", "buffer": None, "date_str": date_obj.strftime("%m%d")}

    def run():
        try:
            buf = _build_distribute_zip(jobs, bills, date_obj.strftime("%m%d"), lambda done: _DISTRIBUTE_TASKS[task_id].update(done=done))
            _DISTRIBUTE_TASKS[task_id]["buffer"] = buf
            _DISTRIBUTE_TASKS[task_id]["status"] = "done"
        except Exception as e:  # noqa
            _DISTRIBUTE_TASKS[task_id]["status"] = "error"
            _DISTRIBUTE_TASKS[task_id]["error"] = str(e)

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
    rows = qy.order_by(Fund.id.desc()).limit(50000).all()
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
            "balance": float(b.balance) if b.balance is not None else None,
            "profit": float(b.profit) if b.profit is not None else 0,
            "created_at": fmt_dt(b.created_at),
        })
    return ok_page(data, total)


@router.delete("/bills")
def clear_bills(db: Session = Depends(get_db), _=Depends(get_current_user)):
    n = db.query(Bill).count()
    db.query(Bill).delete()
    db.commit()
    return {"code": 0, "data": {"cleared": n}, "msg": f"已清空 {n} 条账单"}


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
        g = o.group_name or "未分组"
        gg = groups.setdefault(g, {"qty": 0, "amount": 0.0})
        gg["qty"] += 1
        gg["amount"] += float(o.price) if o.price is not None else 0
    detail = {
        "id": b.id,
        "customer": (f"{c.code} {c.name}" if c else ""),
        "biz_date": str(b.biz_date),
        "purchase_qty": b.purchase_qty,
        "sales": float(b.sales) if b.sales is not None else 0,
        "balance": float(b.balance) if b.balance is not None else 0,
        "profit": float(b.profit) if b.profit is not None else 0,
        "created_at": fmt_dt(b.created_at),
        "groups": [{"group_name": g, "qty": gg["qty"], "amount": round(float(gg["amount"]), 2)}
                   for g, gg in sorted(groups.items())],
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


@router.get("/alert-config")
def get_alert_config(db: Session = Depends(get_db), _=Depends(get_current_user)):
    cfg = db.query(SysConfig).filter(SysConfig.key == "alert_trigger_time").first()
    return {"code": 0, "data": {"trigger_time": cfg.value if cfg else "00:00"}, "msg": "ok"}


@router.put("/alert-config")
def set_alert_config(body: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    value = (body.get("trigger_time") or "00:00").strip()
    cfg = db.query(SysConfig).filter(SysConfig.key == "alert_trigger_time").first()
    if cfg:
        cfg.value = value
    else:
        db.add(SysConfig(key="alert_trigger_time", value=value))
    db.commit()
    return {"code": 0, "data": None, "msg": "已保存"}


@router.post("/alerts/scan")
def manual_scan(db: Session = Depends(get_db), _=Depends(get_current_user)):
    run_alert_scan(db)
    count = db.query(func.count(Alert.id)).filter(Alert.status == "未处理").scalar() or 0
    return {"code": 0, "data": {"unhandled": int(count)}, "msg": "预警扫描完成"}


@router.get("/distinct")
def distinct_values(db: Session = Depends(get_db), _=Depends(get_current_user),
                    model: str = "", field: str = ""):
    allowed = {
        "daily_data": {"province", "city", "platform", "upstream", "wash_status"},
        "orders": {"province", "city"},
        "fund": {"province", "city", "company_type", "operator", "source_file"},
        "customer": {"wash_mode"},
    }
    if model not in allowed or field not in allowed[model]:
        return {"code": 0, "data": [], "msg": "ok"}
    table = {"daily_data": DailyData, "orders": Order, "fund": Fund, "customer": Customer}[model]
    col = getattr(table, field)
    rows = db.query(col).filter(col.isnot(None), col != "").distinct().order_by(col).all()
    return {"code": 0, "data": [r[0] for r in rows], "msg": "ok"}


def run_alert_scan(db: Session):
    """定时：停单日到达 -> 停单提醒；余额低于预警额度 -> 账单预警"""
    today = date.today()
    # 停单提醒
    for o in db.query(Order).filter(Order.stop_date == today).all():
        if not db.query(Alert).filter(Alert.type == "停单提醒", Alert.task_name == o.task_name,
                                      Alert.trigger_time >= datetime(today.year, today.month, today.day)).first():
            c = db.query(Customer).filter(Customer.id == o.customer_id).first()
            db.add(Alert(level="提醒", type="停单提醒", customer_id=o.customer_id,
                         task_name=o.task_name, content=f"停单日 {today} 已到达，请确认是否停单",
                         trigger_time=datetime.now()))
    # 账单预警
    for c in db.query(Customer).filter(Customer.ctype == "downstream", Customer.status == 1).all():
        if c.warn_amount and c.warn_amount > 0 and (c.balance or 0) < c.warn_amount:
            if not db.query(Alert).filter(Alert.type == "账单预警", Alert.customer_id == c.id,
                                          Alert.status == "未处理").first():
                db.add(Alert(level="预警", type="账单预警", customer_id=c.id,
                             content=f"余额 {c.balance} 已低于预警额度 {c.warn_amount}",
                             trigger_time=datetime.now()))
    db.commit()
