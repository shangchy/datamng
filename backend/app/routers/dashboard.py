"""工作台统计路由"""
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Order, Bill, Customer, Alert, DailyData, Category, Fund, Channel, Notification

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db), _=Depends(get_current_user)):
    order_count = db.query(func.count(Order.id)).filter(Order.status == "在执").scalar() or 0
    daily_total = db.query(func.count(DailyData.id)).scalar() or 0
    fund_total = db.query(func.count(Fund.id)).scalar() or 0
    delivery_total = db.query(func.coalesce(func.sum(Order.qty), 0)).scalar() or 0
    profit_total = db.query(func.coalesce(func.sum(Bill.profit), 0)).scalar() or 0
    alert_count = db.query(func.count(Alert.id)).filter(Alert.status == "未处理").scalar() or 0
    return {"code": 0, "data": {
        "order_count": order_count, "daily_total": daily_total, "fund_total": fund_total,
        "delivery_total": int(delivery_total), "profit_total": float(profit_total),
        "alert_count": alert_count,
    }, "msg": "ok"}


@router.get("/rank")
def rank(db: Session = Depends(get_db), _=Depends(get_current_user)):
    sales_sub = (db.query(Bill.customer_id, func.coalesce(func.sum(Bill.sales), 0).label("sales"))
                 .group_by(Bill.customer_id).subquery())
    rows = (db.query(Customer.id, Customer.code, Customer.name, Customer.balance,
                     func.coalesce(func.sum(Order.qty), 0), func.coalesce(sales_sub.c.sales, 0))
            .outerjoin(Order, Order.customer_id == Customer.id)
            .outerjoin(sales_sub, sales_sub.c.customer_id == Customer.id)
            .filter(Customer.ctype == "downstream")
            .group_by(Customer.id, sales_sub.c.sales)
            .order_by(func.coalesce(sales_sub.c.sales, 0).desc()).limit(10).all())
    data = []
    for cid, code, name, balance, qty, sales in rows:
        data.append({
            "id": cid, "code": code, "name": name,
            "qty": int(qty or 0), "sales": float(sales or 0),
            "balance": float(balance) if balance is not None else 0,
        })
    return {"code": 0, "data": data, "msg": "ok"}


@router.get("/alerts-count")
def alerts_count(db: Session = Depends(get_db), _=Depends(get_current_user)):
    stop = db.query(func.count(Alert.id)).filter(Alert.type == "停单提醒", Alert.status == "未处理").scalar() or 0
    bill = db.query(func.count(Alert.id)).filter(Alert.type == "账单预警", Alert.status == "未处理").scalar() or 0
    return {"code": 0, "data": {"stop": int(stop), "bill": int(bill)}, "msg": "ok"}


@router.get("/notifications")
def notifications(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Notification).order_by(Notification.notify_time.desc()).all()
    return {"code": 0, "data": [{
        "id": n.id, "content": n.content, "order_no": n.order_no or "",
        "task_id": n.task_id or "", "order_id": n.order_id,
        "notify_time": n.notify_time.strftime("%Y-%m-%d %H:%M:%S") if n.notify_time else "",
    } for n in rows], "msg": "ok"}


@router.get("/trend")
def trend(db: Session = Depends(get_db), _=Depends(get_current_user),
          start: str = "", end: str = ""):
    end_d = datetime.strptime(end, "%Y-%m-%d").date() if end else date.today()
    start_d = datetime.strptime(start, "%Y-%m-%d").date() if start else (end_d - timedelta(days=6))
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    dates = []
    d = start_d
    while d <= end_d:
        dates.append(d)
        d += timedelta(days=1)
    data = []
    for dd in dates:
        in_qty = db.query(func.count(DailyData.id)).filter(DailyData.biz_date == dd).scalar() or 0
        out_qty = db.query(func.coalesce(func.sum(Bill.purchase_qty), 0)).filter(Bill.biz_date == dd).scalar() or 0
        sales = db.query(func.coalesce(func.sum(Bill.sales), 0)).filter(Bill.biz_date == dd).scalar() or 0
        profit = db.query(func.coalesce(func.sum(Bill.profit), 0)).filter(Bill.biz_date == dd).scalar() or 0
        data.append({"date": dd.strftime("%m-%d"), "in_qty": int(in_qty), "out_qty": int(out_qty),
                     "sales": float(sales), "profit": float(profit)})
    return {"code": 0, "data": data, "msg": "ok"}


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
