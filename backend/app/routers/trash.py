"""垃圾箱：查看/恢复/彻底删除被软删除的数据（仅管理员）"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import (Order, OrderUrl, Alert, Bill, Customer, Product, ProductSale,
                      Channel, Operator, Platform, Category)

router = APIRouter(prefix="/api/trash", tags=["trash"])


def _cust_label(db, cid):
    c = db.query(Customer).filter(Customer.id == cid).first()
    return f"{c.code} {c.name}" if c else (str(cid) if cid else "")


def _label(db, t, o):
    if t == "order":
        return f"{o.order_no}　{o.task_name or ''}".strip()
    if t == "bill":
        return f"{_cust_label(db, o.customer_id)} · {o.biz_date.strftime('%Y-%m-%d') if o.biz_date else ''}"
    if t == "customer":
        return f"{o.code} {o.name}"
    if t == "product":
        return o.name or ""
    if t == "product_sale":
        prod = db.query(Product).filter(Product.id == o.product_id).first()
        return f"{_cust_label(db, o.customer_id)} · {prod.name if prod else ''} · {o.sale_date.strftime('%Y-%m-%d') if o.sale_date else ''}"
    return o.name or ""


_TYPES = [
    ("order", "订单", Order),
    ("bill", "账单", Bill),
    ("customer", "客户", Customer),
    ("product", "产品", Product),
    ("product_sale", "产品销售", ProductSale),
    ("channel", "渠道", Channel),
    ("operator", "运营商", Operator),
    ("platform", "平台", Platform),
    ("category", "品类", Category),
]


def cleanup_expired_trash(db: Session, retention_days: int):
    """彻底删除垃圾箱中已超过保留天数的数据，返回 (清除数, 跳过数)"""
    cutoff = datetime.now() - timedelta(days=max(0, retention_days))
    purged = 0
    skipped = 0
    for t, _, model in _TYPES:
        rows = db.query(model).filter(model.deleted_at.isnot(None), model.deleted_at <= cutoff).all()
        for obj in rows:
            try:
                if t == "order":
                    db.query(OrderUrl).filter(OrderUrl.order_id == obj.id).delete()
                    db.query(Alert).filter(Alert.order_id == obj.id).delete()
                db.delete(obj)
                db.commit()
                purged += 1
            except IntegrityError:
                db.rollback()
                skipped += 1
            except Exception:  # noqa
                db.rollback()
                skipped += 1
    return purged, skipped


@router.get("")
def list_trash(db: Session = Depends(get_db), _=Depends(require_admin)):
    data = []
    for t, tlabel, model in _TYPES:
        rows = db.query(model).filter(model.deleted_at.isnot(None)).order_by(model.deleted_at.desc()).all()
        items = [{"id": r.id, "label": _label(db, t, r),
                  "deleted_at": r.deleted_at.strftime("%Y-%m-%d %H:%M:%S") if r.deleted_at else ""}
                 for r in rows]
        if items:
            data.append({"type": t, "type_label": tlabel, "count": len(items), "items": items})
    return {"code": 0, "data": data, "msg": "ok"}


@router.post("/restore")
def restore_trash(body: dict, db: Session = Depends(get_db), _=Depends(require_admin)):
    t = body.get("type")
    rid = body.get("id")
    model = next((m for tt, _, m in _TYPES if tt == t), None)
    if model is None:
        raise HTTPException(status_code=422, detail="未知数据类型")
    obj = db.query(model).filter(model.id == rid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="记录不存在")

    try:
        if t == "bill":
            if obj.customer_id:
                cust = db.query(Customer).filter(Customer.id == obj.customer_id).first()
                if cust is not None:
                    cust.balance = round(float(cust.balance or 0) - float(obj.sales or 0), 2)
            obj.deleted_at = None
        elif t == "product_sale":
            obj.deleted_at = None
            db.flush()
            from .products import _sync_customer_bill
            _sync_customer_bill(db, obj.customer_id, obj.sale_date, "")
        else:
            obj.deleted_at = None
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="恢复失败：存在同编号/同名数据冲突")
    return {"code": 0, "data": None, "msg": "已恢复"}


@router.delete("/{t}/{rid}")
def permanent_delete(t: str, rid: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    model = next((m for tt, _, m in _TYPES if tt == t), None)
    if model is None:
        raise HTTPException(status_code=422, detail="未知数据类型")
    obj = db.query(model).filter(model.id == rid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="记录不存在")

    if t == "order":
        db.query(OrderUrl).filter(OrderUrl.order_id == rid).delete()
        db.query(Alert).filter(Alert.order_id == rid).delete()
        db.delete(obj)
    elif t == "customer":
        from sqlalchemy import or_
        if (db.query(Order).filter(or_(Order.customer_id == rid, Order.upstream_id == rid)).first()
                or db.query(Bill).filter(Bill.customer_id == rid).first()
                or db.query(ProductSale).filter(ProductSale.customer_id == rid).first()):
            raise HTTPException(status_code=409, detail="客户仍有关联订单/账单/产品销售，无法彻底删除")
        db.delete(obj)
    else:
        db.delete(obj)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="存在关联数据引用，无法彻底删除")
    return {"code": 0, "data": None, "msg": "已彻底删除"}
