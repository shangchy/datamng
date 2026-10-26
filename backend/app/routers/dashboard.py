"""工作台统计路由"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import (Order, Bill, Customer, Alert, DailyData,
                      Notification, ProductSale, DailyBill, SysConfig, CustomerRecharge)
from ..pagination import paginate, ok_page

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _get_usdt_rate(db):
    cfg = db.query(SysConfig).filter(SysConfig.key == "usdt_rate").first()
    try:
        return float(cfg.value) if cfg and cfg.value else 7.0
    except (TypeError, ValueError):
        return 7.0


def _net_bill_balance(db):
    """账单余额 = -(代理余额合计 - 甲方余额) = 甲方余额 - 代理余额合计"""
    down = db.query(func.coalesce(func.sum(Customer.balance), 0)).filter(Customer.ctype == "downstream").scalar() or 0
    up = db.query(func.coalesce(func.sum(Customer.balance), 0)).filter(Customer.ctype == "upstream").scalar() or 0
    return round(float(up) - float(down), 2)


def _bill_balance_at(db, d):
    """重建某日账单余额 = 甲方余额 - 代理余额合计(截至当日)
    代理余额合计(截至当日) = 当前下游余额 - 当日之后充值 + 当日之后销售
    （销售减少余额、充值增加余额；甲方余额无历史，取当前值）"""
    down = db.query(func.coalesce(func.sum(Customer.balance), 0)).filter(Customer.ctype == "downstream").scalar() or 0
    up = db.query(func.coalesce(func.sum(Customer.balance), 0)).filter(Customer.ctype == "upstream").scalar() or 0
    recharge_after = db.query(func.coalesce(func.sum(CustomerRecharge.amount_rmb), 0)).filter(
        CustomerRecharge.recharge_date > d).scalar() or 0
    sales_after = db.query(func.coalesce(func.sum(Bill.sales), 0)).filter(Bill.biz_date > d).scalar() or 0
    down_at_d = float(down) - float(recharge_after) + float(sales_after)
    return round(float(up) - down_at_d, 2)


def snapshot_daily_bill(db, d=None):
    """为指定日期（默认今天）写入/更新当日账单余额快照，返回快照值"""
    d = d or date.today()
    bal = _net_bill_balance(db)
    rec = db.query(DailyBill).filter(DailyBill.biz_date == d).first()
    if rec:
        rec.bill_balance = bal
    else:
        db.add(DailyBill(biz_date=d, bill_balance=bal))
    db.commit()
    return bal


def _daily_bill_balance(db, d):
    """某日账单余额：今天实时计算，历史优先取快照，无快照则重建并回填"""
    if d == date.today():
        return _net_bill_balance(db)
    rec = db.query(DailyBill).filter(DailyBill.biz_date == d).first()
    if rec and rec.bill_balance is not None:
        return float(rec.bill_balance)
    bal = _bill_balance_at(db, d)
    if rec:
        rec.bill_balance = bal
    else:
        db.add(DailyBill(biz_date=d, bill_balance=bal))
    db.commit()
    return bal


@router.get("/summary")
def summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    order_count = db.query(func.count(Order.id)).filter(Order.status == "在执").scalar() or 0
    daily_total = db.query(func.count(DailyData.id)).scalar() or 0
    delivery_total = db.query(func.coalesce(func.sum(Order.qty), 0)).scalar() or 0
    down_balance = db.query(func.coalesce(func.sum(Customer.balance), 0)).filter(Customer.ctype == "downstream").scalar() or 0
    up_balance = db.query(func.coalesce(func.sum(Customer.balance), 0)).filter(Customer.ctype == "upstream").scalar() or 0
    bill_balance = round(float(up_balance) - float(down_balance), 2)
    wallet = db.query(DailyBill).filter(DailyBill.biz_date == date.today()).first()
    wallet_balance = float(wallet.wallet_balance) if wallet and wallet.wallet_balance is not None else 0
    rate = _get_usdt_rate(db)
    total_balance = round(bill_balance + wallet_balance * rate, 2)
    month_start = date.today().replace(day=1)
    bill_profit = db.query(func.coalesce(func.sum(Bill.profit), 0)).filter(Bill.biz_date >= month_start).scalar() or 0
    ps_profit = db.query(func.coalesce(func.sum(ProductSale.profit), 0)).filter(ProductSale.sale_date >= month_start).scalar() or 0
    month_profit = round(float(bill_profit) + float(ps_profit), 2)
    return {"code": 0, "data": {
        "order_count": order_count, "daily_total": daily_total,
        "delivery_total": int(delivery_total),
        "bill_balance": bill_balance,
        "total_balance": total_balance,
        "month_profit": month_profit,
    }, "msg": "ok"}


@router.get("/rank")
def rank(db: Session = Depends(get_db), _=Depends(get_current_user)):
    bill_sub = (db.query(Bill.customer_id,
                         func.coalesce(func.sum(Bill.sales), 0).label("sales"),
                         func.coalesce(func.sum(Bill.profit), 0).label("profit"))
                .group_by(Bill.customer_id).subquery())
    rows = (db.query(Customer.id, Customer.code, Customer.name, Customer.balance,
                     func.coalesce(func.sum(Order.qty), 0),
                     func.coalesce(bill_sub.c.sales, 0), func.coalesce(bill_sub.c.profit, 0))
            .outerjoin(Order, Order.customer_id == Customer.id)
            .outerjoin(bill_sub, bill_sub.c.customer_id == Customer.id)
            .filter(Customer.ctype == "downstream")
            .group_by(Customer.id, bill_sub.c.sales, bill_sub.c.profit)
            .order_by(func.coalesce(bill_sub.c.sales, 0).desc()).limit(10).all())
    data = []
    for cid, code, name, balance, qty, sales, profit in rows:
        data.append({
            "id": cid, "code": code, "name": name,
            "qty": int(qty or 0), "sales": float(sales or 0),
            "profit": float(profit or 0),
            "balance": float(balance) if balance is not None else 0,
        })
    return {"code": 0, "data": data, "msg": "ok"}


@router.get("/alerts-count")
def alerts_count(db: Session = Depends(get_db), _=Depends(get_current_user)):
    stop = db.query(func.count(Alert.id)).filter(Alert.type == "停单提醒", Alert.status == "未处理").scalar() or 0
    bill = db.query(func.count(Alert.id)).filter(Alert.type == "账单预警", Alert.status == "未处理").scalar() or 0
    return {"code": 0, "data": {"stop": int(stop), "bill": int(bill)}, "msg": "ok"}


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), _=Depends(get_current_user),
                  page: int = 1, per_page: int = 500):
    qy = db.query(Notification).order_by(Notification.notify_time.desc(), Notification.id.desc())
    total, rows = paginate(qy, page, per_page)
    return ok_page([{
        "id": n.id, "content": n.content, "order_no": n.order_no or "",
        "task_id": n.task_id or "", "order_id": n.order_id,
        "notify_time": n.notify_time.strftime("%Y-%m-%d %H:%M:%S") if n.notify_time else "",
    } for n in rows], total)


@router.get("/trend")
def trend(db: Session = Depends(get_db), _=Depends(get_current_user),
          start: str = "", end: str = ""):
    end_d = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
    start_d = datetime.strptime(start, "%Y-%m-%d").date() if start else (end_d - timedelta(days=6))
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    rate = _get_usdt_rate(db)
    dates = []
    d = start_d
    while d <= end_d:
        dates.append(d)
        d += timedelta(days=1)
    data = []
    for dd in dates:
        in_qty = db.query(func.count(DailyData.id)).filter(DailyData.biz_date == dd).scalar() or 0
        out_qty = db.query(func.coalesce(func.sum(Bill.purchase_qty), 0)).filter(Bill.biz_date == dd).scalar() or 0
        bill_profit = db.query(func.coalesce(func.sum(Bill.profit), 0)).filter(Bill.biz_date == dd).scalar() or 0
        ps_profit = db.query(func.coalesce(func.sum(ProductSale.profit), 0)).filter(ProductSale.sale_date == dd).scalar() or 0
        profit = round(float(bill_profit) + float(ps_profit), 2)
        bill_balance = _daily_bill_balance(db, dd)
        rec = db.query(DailyBill).filter(DailyBill.biz_date == dd).first()
        wallet_balance = float(rec.wallet_balance) if rec and rec.wallet_balance is not None else 0
        total_balance = round(bill_balance + wallet_balance * rate, 2) if bill_balance is not None else None
        data.append({"date": dd.strftime("%m-%d"), "in_qty": int(in_qty), "out_qty": int(out_qty),
                     "profit": profit, "total_balance": total_balance})
    return {"code": 0, "data": data, "msg": "ok"}


@router.get("/daily-bills")
def daily_bills(db: Session = Depends(get_db), _=Depends(get_current_user),
                start: str = "", end: str = ""):
    end_d = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
    start_d = datetime.strptime(start, "%Y-%m-%d").date() if start else (end_d - timedelta(days=29))
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    today = date.today()
    if start_d <= today <= end_d:
        snapshot_daily_bill(db, today)
    rate = _get_usdt_rate(db)
    data = []
    d = end_d
    while d >= start_d:
        rec = db.query(DailyBill).filter(DailyBill.biz_date == d).first()
        bill_profit = db.query(func.coalesce(func.sum(Bill.profit), 0)).filter(Bill.biz_date == d).scalar() or 0
        ps_profit = db.query(func.coalesce(func.sum(ProductSale.profit), 0)).filter(ProductSale.sale_date == d).scalar() or 0
        profit = round(float(bill_profit) + float(ps_profit), 2)
        bill_balance = _daily_bill_balance(db, d)
        wallet_balance = float(rec.wallet_balance) if rec and rec.wallet_balance is not None else None
        total_balance = round(bill_balance + (wallet_balance or 0) * rate, 2) if bill_balance is not None else None
        data.append({
            "date": d.strftime("%Y-%m-%d"),
            "profit": profit,
            "bill_balance": bill_balance,
            "wallet_balance": wallet_balance,
            "total_balance": total_balance,
        })
        d -= timedelta(days=1)
    return {"code": 0, "data": data, "msg": "ok"}


@router.put("/daily-bills/wallet")
def set_daily_bill_wallet(body: dict, db: Session = Depends(get_db), _=Depends(get_current_user)):
    date_str = body.get("date")
    if not date_str:
        raise HTTPException(status_code=422, detail="请选择日期")
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="日期格式错误")
    value = body.get("wallet_balance")
    wb = None
    if value not in (None, ""):
        try:
            wb = float(value)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="钱包余额格式错误")
    rec = db.query(DailyBill).filter(DailyBill.biz_date == d).first()
    if rec:
        rec.wallet_balance = wb
    else:
        db.add(DailyBill(biz_date=d, wallet_balance=wb))
    db.commit()
    return {"code": 0, "data": None, "msg": "已保存"}


@router.get("/category-pie")
def category_pie(db: Session = Depends(get_db), _=Depends(get_current_user),
                 start: str = "", end: str = ""):
    end_d = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
    start_d = datetime.strptime(start, "%Y-%m-%d").date() if start else (end_d - timedelta(days=6))
    rows = (db.query(DailyData.cat1, func.count(DailyData.id))
            .filter(DailyData.biz_date >= start_d, DailyData.biz_date <= end_d,
                    DailyData.cat1.isnot(None), DailyData.cat1 != "")
            .group_by(DailyData.cat1).all())
    return {"code": 0, "data": [{"name": r[0], "value": int(r[1])} for r in rows], "msg": "ok"}


@router.get("/category2-pie")
def category2_pie(db: Session = Depends(get_db), _=Depends(get_current_user),
                  start: str = "", end: str = ""):
    end_d = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
    start_d = datetime.strptime(start, "%Y-%m-%d").date() if start else (end_d - timedelta(days=6))
    rows = (db.query(DailyData.cat2, func.count(DailyData.id))
            .filter(DailyData.biz_date >= start_d, DailyData.biz_date <= end_d,
                    DailyData.cat2.isnot(None), DailyData.cat2 != "")
            .group_by(DailyData.cat2).all())
    return {"code": 0, "data": [{"name": r[0], "value": int(r[1])} for r in rows], "msg": "ok"}


@router.get("/channel-pie")
def channel_pie(db: Session = Depends(get_db), _=Depends(get_current_user),
                start: str = "", end: str = ""):
    end_d = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
    start_d = datetime.strptime(start, "%Y-%m-%d").date() if start else (end_d - timedelta(days=6))
    rows = (db.query(DailyData.channel, func.count(DailyData.id))
            .filter(DailyData.biz_date >= start_d, DailyData.biz_date <= end_d,
                    DailyData.channel.isnot(None), DailyData.channel != "")
            .group_by(DailyData.channel).all())
    return {"code": 0, "data": [{"name": r[0], "value": int(r[1])} for r in rows], "msg": "ok"}
