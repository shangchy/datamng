"""客户管理路由"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import (Customer, CustomerRecharge, CustomerPrice, Channel,
                      Bill, Order, Url, Category, Alert, SysConfig, Operator)
from ..schemas import CustomerBody, RechargeBody, PriceBody
from ..pagination import paginate, ok_page
from ..utils import fmt_dt

router = APIRouter(prefix="/api/customers", tags=["customers"])


def _recharge_rate(db):
    cfg = db.query(SysConfig).filter(SysConfig.key == "recharge_rate").first()
    try:
        return float(cfg.value) if cfg and cfg.value else 6.7
    except (TypeError, ValueError):
        return 6.7


@router.get("/recharge-rate")
def get_recharge_rate(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return {"code": 0, "data": {"rate": _recharge_rate(db)}, "msg": "ok"}


@router.put("/recharge-rate")
def set_recharge_rate(body: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    try:
        rate = float(body.get("rate"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="汇率无效")
    cfg = db.query(SysConfig).filter(SysConfig.key == "recharge_rate").first()
    if cfg:
        cfg.value = str(rate)
    else:
        db.add(SysConfig(key="recharge_rate", value=str(rate)))
    db.commit()
    return {"code": 0, "data": {"rate": rate}, "msg": "汇率已保存"}


@router.get("")
def list_customers(db: Session = Depends(get_db), _=Depends(get_current_user),
                   q: str = "", code: str = "", name: str = "", ctype: str = "",
                   tg_id: str = "", status: str = "", note: str = "",
                   page: int = 1, per_page: int = 10):
    qy = db.query(Customer)
    if q:
        like = f"%{q}%"
        qy = qy.filter(or_(Customer.code.like(like), Customer.name.like(like),
                           Customer.tg_id.like(like)))
    if code:
        qy = qy.filter(Customer.code.like(f"%{code}%"))
    if name:
        qy = qy.filter(Customer.name.like(f"%{name}%"))
    if ctype:
        qy = qy.filter(Customer.ctype == ctype)
    if tg_id:
        qy = qy.filter(Customer.tg_id.like(f"%{tg_id}%"))
    if status:
        qy = qy.filter(Customer.status == int(status))
    if note:
        qy = qy.filter(Customer.note.like(f"%{note}%"))
    total, rows = paginate(qy, page, per_page)
    alert_customers = {r[0] for r in db.query(Alert.customer_id).filter(Alert.type == "账单预警", Alert.status == "未处理").all() if r[0]}
    data = []
    for c in rows:
        d = _customer_dict(c)
        d["has_alert"] = c.id in alert_customers
        data.append(d)
    return ok_page(data, total)


@router.get("/{cid}")
def customer_detail(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Customer).filter(Customer.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    total_supply = db.query(func.coalesce(func.sum(Order.qty), 0)).filter(Order.customer_id == cid).scalar() or 0
    total_sales = db.query(func.coalesce(func.sum(Bill.sales), 0)).filter(Bill.customer_id == cid).scalar() or 0
    total_profit = db.query(func.coalesce(func.sum(Bill.profit), 0)).filter(Bill.customer_id == cid).scalar() or 0
    d = _customer_dict(c)
    d.update({"total_supply": float(total_supply), "total_sales": float(total_sales), "total_profit": float(total_profit)})
    return {"code": 0, "data": d, "msg": "ok"}


@router.post("")
def create_customer(body: CustomerBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Customer).filter(Customer.code == body.code).first():
        raise HTTPException(status_code=409, detail="客户编号已存在")
    c = Customer(**body.model_dump())
    db.add(c)
    db.commit()
    return {"code": 0, "data": {"id": c.id}, "msg": "ok"}


@router.put("/{cid}")
def update_customer(cid: int, body: CustomerBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Customer).filter(Customer.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    c.updated_at = datetime.now()
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.delete("/{cid}")
def delete_customer(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Customer).filter(Customer.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    if db.query(Order).filter(Order.customer_id == cid).first() or db.query(Bill).filter(Bill.customer_id == cid).first():
        raise HTTPException(status_code=409, detail="存在关联数据，不可删除")
    db.delete(c)
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.get("/{cid}/recharges")
def list_recharges(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(CustomerRecharge).filter(CustomerRecharge.customer_id == cid).order_by(CustomerRecharge.recharge_date.desc()).all()
    return {"code": 0, "data": [{
        "id": r.id, "recharge_date": str(r.recharge_date), "amount_u": float(r.amount_u),
        "amount_rmb": float(r.amount_rmb) if r.amount_rmb else None, "note": r.note,
    } for r in rows], "msg": "ok"}


@router.post("/{cid}/recharges")
def create_recharge(cid: int, body: RechargeBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Customer).filter(Customer.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    rate = _recharge_rate(db)
    if body.amount_rmb is not None:
        rmb = round(float(body.amount_rmb), 2)
        u = round(rmb / rate, 2)
    elif body.amount_u is not None:
        u = round(float(body.amount_u), 2)
        rmb = round(u * rate, 2)
    else:
        raise HTTPException(status_code=422, detail="请填写充值金额（U 或 人民币）")
    db.add(CustomerRecharge(customer_id=cid, recharge_date=body.recharge_date,
                            amount_u=u, amount_rmb=rmb, note=body.note))
    c.balance = (c.balance if c.balance is not None else Decimal("0")) + Decimal(str(rmb))
    # 联动最新账单余额（保持与客户余额一致）
    latest_bill = db.query(Bill).filter(Bill.customer_id == cid).order_by(Bill.biz_date.desc()).first()
    if latest_bill:
        latest_bill.balance = c.balance
    db.query(Alert).filter(Alert.type == "账单预警", Alert.customer_id == cid, Alert.status == "未处理").delete()
    db.commit()
    return {"code": 0, "data": None, "msg": "充值成功"}


@router.put("/{cid}/recharges/{rid}")
def update_recharge(cid: int, rid: int, body: RechargeBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    r = db.query(CustomerRecharge).filter(CustomerRecharge.id == rid,
                                          CustomerRecharge.customer_id == cid).first()
    if not r:
        raise HTTPException(status_code=404, detail="充值记录不存在")
    c = db.query(Customer).filter(Customer.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    rate = _recharge_rate(db)
    if body.amount_rmb is not None:
        rmb = round(float(body.amount_rmb), 2)
        u = round(rmb / rate, 2)
    elif body.amount_u is not None:
        u = round(float(body.amount_u), 2)
        rmb = round(u * rate, 2)
    else:
        raise HTTPException(status_code=422, detail="请填写充值金额（U 或 人民币）")
    old_rmb = float(r.amount_rmb) if r.amount_rmb is not None else 0
    delta = round(rmb - old_rmb, 2)
    r.amount_u = u
    r.amount_rmb = rmb
    r.recharge_date = body.recharge_date
    r.note = body.note
    if delta:
        c.balance = (c.balance if c.balance is not None else Decimal("0")) + Decimal(str(delta))
        latest_bill = db.query(Bill).filter(Bill.customer_id == cid).order_by(Bill.biz_date.desc()).first()
        if latest_bill:
            latest_bill.balance = c.balance
    db.query(Alert).filter(Alert.type == "账单预警", Alert.customer_id == cid, Alert.status == "未处理").delete()
    db.commit()
    return {"code": 0, "data": None, "msg": "充值已更新"}


DPI_OPERATORS = ["移动", "联通", "电信"]


@router.get("/{cid}/prices")
def list_prices(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    channels = db.query(Channel).filter(Channel.status == 1).all()
    operator_ids = {op.name: op.id for op in db.query(Operator).filter(Operator.status == 1).all()}
    prices = {}
    for p in db.query(CustomerPrice).filter(CustomerPrice.customer_id == cid).all():
        prices[(p.channel_id, p.operator_id)] = float(p.price)
    seen = set()
    data = []
    for ch in channels:
        name = (ch.name or "").strip()
        if not name:
            continue
        if "dpi" in name:
            for op_name in DPI_OPERATORS:
                op_id = operator_ids.get(op_name)
                if op_id is None:
                    continue
                label = f"{name}-{op_name}"
                if label in seen:
                    continue
                seen.add(label)
                data.append({"channel_id": ch.id, "operator_id": op_id,
                             "channel": label, "price": prices.get((ch.id, op_id))})
        else:
            if name in seen:
                continue
            seen.add(name)
            data.append({"channel_id": ch.id, "operator_id": None,
                         "channel": name, "price": prices.get((ch.id, None))})
    return {"code": 0, "data": data, "msg": "ok"}


@router.put("/{cid}/prices")
def save_prices(cid: int, body: PriceBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    for item in body.prices:
        ch_id = item.get("channel_id")
        price = item.get("price")
        op_id = item.get("operator_id")
        if ch_id is None or price is None:
            continue
        row = db.query(CustomerPrice).filter(CustomerPrice.customer_id == cid,
                                             CustomerPrice.channel_id == ch_id,
                                             CustomerPrice.operator_id == op_id).first()
        if row:
            row.price = price
        else:
            db.add(CustomerPrice(customer_id=cid, channel_id=ch_id, operator_id=op_id, price=price))
    db.commit()
    return {"code": 0, "data": None, "msg": "单价已保存"}


@router.get("/{cid}/orders")
def customer_orders(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Customer).filter(Customer.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="客户不存在")
    name = c.name or ""
    code = c.code or ""
    conds = [Order.customer_id == cid, Order.upstream_id == cid]
    if name:
        conds.append(Order.secondary_agent == name)
    if code and code != name:
        conds.append(Order.secondary_agent == code)
    rows = db.query(Order).filter(or_(*conds)).order_by(Order.id.desc()).all()
    data = []
    for o in rows:
        ch = db.query(Channel).filter(Channel.id == o.channel_id).first()
        up = db.query(Customer).filter(Customer.id == o.upstream_id).first()
        urls = [u.url for u in o.urls]
        data.append({
            "order_no": o.order_no, "status": o.status, "start_date": str(o.start_date) if o.start_date else None,
            "end_date": str(o.end_date) if o.end_date else None,
            "upstream": (f"{up.code} {up.name}".strip() if up else ""),
            "channel": ch.name if ch else "", "task_name": o.task_name,
            "url": urls[0] + f" 等{len(urls)}个" if len(urls) > 1 else (urls[0] if urls else ""),
            "qty": o.qty,
        })
    return {"code": 0, "data": data, "msg": "ok"}


def _customer_dict(c: Customer):
    return {
        "id": c.id, "code": c.code, "name": c.name, "ctype": c.ctype, "tg_id": c.tg_id,
        "is_accounted": c.is_accounted,
        "balance": float(c.balance) if c.balance is not None else 0,
        "warn_amount": float(c.warn_amount) if c.warn_amount is not None else 0,
        "start_date": str(c.start_date) if c.start_date else None,
        "end_date": str(c.end_date) if c.end_date else None,
        "bill_tpl_id": c.bill_tpl_id,
        "note": c.note, "status": c.status,
        "created_at": fmt_dt(c.created_at),
        "updated_at": fmt_dt(c.updated_at),
    }
