"""主数据路由：品类/渠道/运营商/配件URL/平台"""
import io
import re

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Category, Channel, Operator, Url, Customer, Platform
from ..schemas import CategoryBody, SimpleBody, UrlBody, PlatformBody
from ..pagination import paginate, ok_page
from ..utils import fmt_dt
from ..regions import PROVINCES, CITIES

router = APIRouter(prefix="/api", tags=["master"])


def _norm_header(h):
    return re.sub(r"\s+", "", str(h)).lower()


def _read_xlsx_rows(content):
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    header, rows = None, []
    for values in ws.iter_rows(values_only=True):
        if header is None:
            header = ["" if v is None else str(v) for v in values]
            continue
        rows.append(values)
    wb.close()
    return header, rows


def _row_map(header, values, field_map):
    idx = {_norm_header(h): i for i, h in enumerate(header)}
    row = {}
    for name, field in field_map.items():
        key = _norm_header(name)
        if key in idx and idx[key] < len(values):
            v = values[idx[key]]
            row[field] = None if v is None else str(v).strip()
    return row


@router.get("/regions")
def list_regions(_=Depends(get_current_user)):
    return {"code": 0, "data": {"provinces": PROVINCES, "cities": CITIES}, "msg": "ok"}


# ============ 品类 ============
@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _=Depends(get_current_user)):
    rows = db.query(Category).order_by(Category.level, Category.sort_no).all()
    parents = [r for r in rows if r.level == 1]
    data = []
    for p in parents:
        children = [{"id": c.id, "name": c.name, "status": c.status}
                    for c in rows if c.parent_id == p.id]
        data.append({"id": p.id, "name": p.name, "status": p.status, "children": children})
    return {"code": 0, "data": data, "msg": "ok"}


@router.post("/categories")
def create_category(body: CategoryBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = Category(name=body.name, parent_id=body.parent_id, level=body.level, sort_no=body.sort_no, status=body.status)
    db.add(c)
    db.commit()
    return {"code": 0, "data": {"id": c.id}, "msg": "ok"}


@router.put("/categories/{cid}")
def update_category(cid: int, body: CategoryBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Category).filter(Category.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="品类不存在")
    c.name, c.status = body.name, body.status
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.delete("/categories/{cid}")
def delete_category(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Category).filter(Category.parent_id == cid).first():
        raise HTTPException(status_code=409, detail="存在子品类，不可删除")
    if db.query(Url).filter((Url.cat1_id == cid) | (Url.cat2_id == cid)).first():
        raise HTTPException(status_code=409, detail="被 URL 引用，不可删除")
    db.query(Category).filter(Category.id == cid).delete()
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


# ============ 渠道 ============
@router.get("/channels")
def list_channels(db: Session = Depends(get_db), _=Depends(get_current_user), name: str = "",
                  page: int = 1, per_page: int = 10):
    q = db.query(Channel)
    if name:
        q = q.filter(Channel.name.like(f"%{name}%"))
    total, rows = paginate(q.order_by(Channel.id), page, per_page)
    return ok_page([{"id": c.id, "name": c.name, "status": c.status} for c in rows], total)


@router.post("/channels")
def create_channel(body: SimpleBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Channel).filter(Channel.name == body.name).first():
        raise HTTPException(status_code=409, detail="渠道名已存在")
    c = Channel(name=body.name, status=body.status)
    db.add(c)
    db.commit()
    return {"code": 0, "data": {"id": c.id}, "msg": "ok"}


@router.put("/channels/{cid}")
def update_channel(cid: int, body: SimpleBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Channel).filter(Channel.id == cid).first()
    if not c:
        raise HTTPException(status_code=404, detail="渠道不存在")
    c.name, c.status = body.name, body.status
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.delete("/channels/{cid}")
def delete_channel(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Url).filter(Url.channel_id == cid).first():
        raise HTTPException(status_code=409, detail="被 URL 引用，不可删除")
    db.query(Channel).filter(Channel.id == cid).delete()
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.get("/channels/{cid}/detail")
def channel_detail(cid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    ch = db.query(Channel).filter(Channel.id == cid).first()
    if not ch:
        raise HTTPException(status_code=404, detail="渠道不存在")
    urls = db.query(Url).filter(Url.channel_id == cid).all()
    url_list = []
    for u in urls:
        cat1 = db.query(Category).filter(Category.id == u.cat1_id).first()
        cat2 = db.query(Category).filter(Category.id == u.cat2_id).first()
        path = " → ".join([x for x in [cat1.name if cat1 else "", cat2.name if cat2 else "", ch.name] if x])
        url_list.append({"url": u.url, "owner": u.owner, "level": u.level, "path": path,
                         "updated_at": fmt_dt(u.updated_at)})
    return {"code": 0, "data": {"name": ch.name, "urls": url_list}, "msg": "ok"}


# ============ 运营商 ============
@router.get("/operators")
def list_operators(db: Session = Depends(get_db), _=Depends(get_current_user), name: str = "",
                   page: int = 1, per_page: int = 10):
    q = db.query(Operator)
    if name:
        q = q.filter(Operator.name.like(f"%{name}%"))
    total, rows = paginate(q.order_by(Operator.id), page, per_page)
    return ok_page([{"id": o.id, "name": o.name, "status": o.status} for o in rows], total)


@router.post("/operators")
def create_operator(body: SimpleBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    if db.query(Operator).filter(Operator.name == body.name).first():
        raise HTTPException(status_code=409, detail="运营商已存在")
    o = Operator(name=body.name, status=body.status)
    db.add(o)
    db.commit()
    return {"code": 0, "data": {"id": o.id}, "msg": "ok"}


@router.put("/operators/{oid}")
def update_operator(oid: int, body: SimpleBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    o = db.query(Operator).filter(Operator.id == oid).first()
    if not o:
        raise HTTPException(status_code=404, detail="运营商不存在")
    o.name, o.status = body.name, body.status
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.delete("/operators/{oid}")
def delete_operator(oid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    db.query(Operator).filter(Operator.id == oid).delete()
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


# ============ 配件/URL ============
@router.get("/urls")
def list_urls(db: Session = Depends(get_db), _=Depends(get_current_user),
              owner: str = "", level: str = "", channel: str = "", url: str = "",
              name: str = "", cat1: str = "", cat2: str = "", platform: str = "",
              page: int = 1, per_page: int = 10):
    q = db.query(Url).order_by(Url.id.desc())
    if owner:
        c = db.query(Customer).filter(or_(Customer.name.like(f"%{owner}%"),
                                          Customer.code.like(f"%{owner}%"))).all()
        q = q.filter(Url.owner_id.in_([x.id for x in c]) if c else [-1])
    if level:
        q = q.filter(Url.level == level)
    if channel:
        ch = db.query(Channel).filter(Channel.name.like(f"%{channel}%")).all()
        q = q.filter(Url.channel_id.in_([c.id for c in ch]) if ch else [-1])
    if url:
        q = q.filter(Url.url.like(f"%{url}%"))
    if name:
        q = q.filter(Url.name.like(f"%{name}%"))
    if cat1:
        cats = db.query(Category).filter(Category.name.like(f"%{cat1}%"), Category.level == 1).all()
        q = q.filter(Url.cat1_id.in_([c.id for c in cats]) if cats else [-1])
    if cat2:
        cats = db.query(Category).filter(Category.name.like(f"%{cat2}%"), Category.level == 2).all()
        q = q.filter(Url.cat2_id.in_([c.id for c in cats]) if cats else [-1])
    if platform:
        plats = db.query(Platform).filter(Platform.name.like(f"%{platform}%")).all()
        q = q.filter(Url.platform_id.in_([p.id for p in plats]) if plats else [-1])
    total, rows = paginate(q, page, per_page)
    data = []
    for u in rows:
        cat1 = db.query(Category).filter(Category.id == u.cat1_id).first()
        cat2 = db.query(Category).filter(Category.id == u.cat2_id).first()
        ch = db.query(Channel).filter(Channel.id == u.channel_id).first()
        owner_c = db.query(Customer).filter(Customer.id == u.owner_id).first()
        plat = db.query(Platform).filter(Platform.id == u.platform_id).first() if u.platform_id else None
        data.append({
            "id": u.id,
            "name": u.name or "",
            "owner": f"{owner_c.code} {owner_c.name}" if owner_c else "",
            "owner_id": u.owner_id,
            "cat1": cat1.name if cat1 else "", "cat2": cat2.name if cat2 else "",
            "cat1_id": u.cat1_id, "cat2_id": u.cat2_id,
            "platform": plat.name if plat else "", "platform_id": u.platform_id,
            "channel": ch.name if ch else "", "url": u.url, "level": u.level,
            "updated_at": fmt_dt(u.updated_at),
        })
    return ok_page(data, total)


@router.post("/urls")
def create_urls(body: UrlBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    created = 0
    cat1_id, cat2_id, platform_id = body.cat1_id, body.cat2_id, body.platform_id
    if platform_id and (not cat1_id or not cat2_id):
        plat = db.query(Platform).filter(Platform.id == platform_id).first()
        if plat:
            cat2_id = plat.cat_id
            cat2 = db.query(Category).filter(Category.id == cat2_id).first()
            cat1_id = cat2.parent_id if cat2 else None
    for u in body.urls:
        db.add(Url(name=u.get("name", body.name or ""), owner_id=body.owner_id, cat1_id=cat1_id,
                   cat2_id=cat2_id, platform_id=platform_id, channel_id=body.channel_id,
                   url=u.get("url", ""), level=u.get("level", "中")))
        created += 1
    db.commit()
    return {"code": 0, "data": {"created": created}, "msg": f"已保存 {created} 个 URL"}


@router.put("/urls/{uid}")
def update_url(uid: int, body: UrlBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    u = db.query(Url).filter(Url.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="URL 不存在")
    if body.urls:
        item = body.urls[0]
        u.url = item.get("url", u.url)
        u.level = item.get("level", u.level)
        if "name" in item:
            u.name = item.get("name") or ""
    u.name = body.name if body.name is not None else u.name
    u.owner_id = body.owner_id
    u.channel_id = body.channel_id
    u.platform_id = body.platform_id
    u.cat1_id = body.cat1_id
    u.cat2_id = body.cat2_id
    if body.platform_id and (not body.cat1_id or not body.cat2_id):
        plat = db.query(Platform).filter(Platform.id == body.platform_id).first()
        if plat:
            u.cat2_id = plat.cat_id
            cat2 = db.query(Category).filter(Category.id == plat.cat_id).first()
            u.cat1_id = cat2.parent_id if cat2 else None
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.delete("/urls")
def clear_urls(db: Session = Depends(get_db), _=Depends(get_current_user)):
    n = db.query(Url).count()
    db.query(Url).delete()
    db.commit()
    return {"code": 0, "data": {"cleared": n}, "msg": f"已清空 {n} 条配件"}


@router.delete("/urls/{uid}")
def delete_url(uid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    db.query(Url).filter(Url.id == uid).delete()
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


# ============ 平台（挂在二级品类下） ============
@router.get("/platforms")
def list_platforms(db: Session = Depends(get_db), _=Depends(get_current_user), cat_id: int = 0):
    q = db.query(Platform)
    if cat_id:
        q = q.filter(Platform.cat_id == cat_id)
    rows = q.order_by(Platform.cat_id, Platform.sort_no, Platform.id).all()
    data = []
    for p in rows:
        cat = db.query(Category).filter(Category.id == p.cat_id).first()
        data.append({"id": p.id, "name": p.name, "cat_id": p.cat_id,
                     "cat_name": cat.name if cat else "", "sort_no": p.sort_no, "status": p.status})
    return {"code": 0, "data": data, "msg": "ok"}


@router.post("/platforms")
def create_platform(body: PlatformBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = Platform(name=body.name, cat_id=body.cat_id, sort_no=body.sort_no, status=body.status)
    db.add(p)
    db.commit()
    return {"code": 0, "data": {"id": p.id}, "msg": "ok"}


@router.put("/platforms/{pid}")
def update_platform(pid: int, body: PlatformBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    p = db.query(Platform).filter(Platform.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="平台不存在")
    p.name, p.cat_id, p.sort_no, p.status = body.name, body.cat_id, body.sort_no, body.status
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.delete("/platforms/{pid}")
def delete_platform(pid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    db.query(Platform).filter(Platform.id == pid).delete()
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


# ============ 导入 ============
@router.post("/categories/import")
async def import_categories(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(get_current_user)):
    content = await file.read()
    header, rows = _read_xlsx_rows(content)
    field_map = {"大品类": "cat1", "小品类": "cat2", "平台": "platform"}
    created_cat = 0
    created_plat = 0
    for values in rows:
        r = _row_map(header, values, field_map)
        cat1_name = r.get("cat1")
        if not cat1_name:
            continue
        cat1 = db.query(Category).filter(Category.name == cat1_name, Category.level == 1).first()
        if not cat1:
            cat1 = Category(name=cat1_name, level=1)
            db.add(cat1)
            db.flush()
            created_cat += 1
        cat2 = None
        if r.get("cat2"):
            cat2 = db.query(Category).filter(Category.name == r["cat2"], Category.level == 2,
                                             Category.parent_id == cat1.id).first()
            if not cat2:
                cat2 = Category(name=r["cat2"], level=2, parent_id=cat1.id)
                db.add(cat2)
                db.flush()
                created_cat += 1
        if r.get("platform") and cat2:
            if not db.query(Platform).filter(Platform.name == r["platform"], Platform.cat_id == cat2.id).first():
                db.add(Platform(name=r["platform"], cat_id=cat2.id))
                created_plat += 1
    db.commit()
    return {"code": 0, "data": {"categories": created_cat, "platforms": created_plat},
            "msg": f"导入品类 {created_cat} 个、平台 {created_plat} 个"}


@router.post("/urls/import")
async def import_urls(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(get_current_user)):
    content = await file.read()
    header, rows = _read_xlsx_rows(content)
    field_map = {"归属方": "owner", "大品类": "cat1", "小品类": "cat2", "平台": "platform",
                 "命名": "name", "渠道": "channel", "url": "url", "等级": "level"}
    n = 0
    for values in rows:
        r = _row_map(header, values, field_map)
        url = r.get("url")
        if not url:
            continue
        channel_id = None
        if r.get("channel"):
            ch = db.query(Channel).filter(Channel.name == r["channel"]).first()
            channel_id = ch.id if ch else None
        platform_id, cat2_id, cat1_id = None, None, None
        if r.get("platform"):
            plat = db.query(Platform).filter(Platform.name == r["platform"]).first()
            if plat:
                platform_id = plat.id
                cat2_id = plat.cat_id
                cat2 = db.query(Category).filter(Category.id == cat2_id).first()
                cat1_id = cat2.parent_id if cat2 else None
        if not cat1_id and r.get("cat1"):
            c1 = db.query(Category).filter(Category.name == r["cat1"], Category.level == 1).first()
            cat1_id = c1.id if c1 else None
        if not cat2_id and r.get("cat2"):
            c2 = db.query(Category).filter(Category.name == r["cat2"], Category.level == 2).first()
            cat2_id = c2.id if c2 else None
        owner_id = None
        if r.get("owner"):
            ow = db.query(Customer).filter(Customer.name == r["owner"]).first()
            owner_id = ow.id if ow else None
        db.add(Url(name=r.get("name") or "", owner_id=owner_id, cat1_id=cat1_id, cat2_id=cat2_id,
                   platform_id=platform_id, channel_id=channel_id, url=url,
                   level=r.get("level") or "中"))
        n += 1
    db.commit()
    return {"code": 0, "data": {"imported": n}, "msg": f"导入 {n} 条配件"}
