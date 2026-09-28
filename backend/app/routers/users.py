"""账户管理路由（仅 admin）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_permission
from ..models import SysUser, SysRole, SysPermission, sys_role_permission
from ..schemas import UserCreate, UserUpdate, UserSetPasswordBody, RolePermissionsBody
from ..security import hash_password
from ..pagination import paginate, ok_page
from ..utils import fmt_dt

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), _=Depends(require_permission("account:view")),
               page: int = 1, per_page: int = 10):
    q = db.query(SysUser).order_by(SysUser.id)
    total, rows = paginate(q, page, per_page)
    return ok_page([{
        "id": u.id, "username": u.username, "nickname": u.nickname,
        "role_id": u.role_id, "role": u.role.name if u.role else "",
        "status": u.status, "last_login_at": fmt_dt(u.last_login_at),
    } for u in rows], total)


@router.post("/users")
def create_user(body: UserCreate, db: Session = Depends(get_db), _=Depends(require_permission("account:edit"))):
    if db.query(SysUser).filter(SysUser.username == body.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")
    u = SysUser(username=body.username, nickname=body.nickname, role_id=body.role_id,
                password_hash=hash_password(body.password), must_change_pwd=True)
    db.add(u)
    db.commit()
    return {"code": 0, "data": {"id": u.id}, "msg": "ok"}


@router.put("/users/{uid}")
def update_user(uid: int, body: UserUpdate, db: Session = Depends(get_db), _=Depends(require_permission("account:edit"))):
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.nickname is not None:
        u.nickname = body.nickname
    if body.role_id is not None:
        u.role_id = body.role_id
    if body.status is not None:
        u.status = body.status
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.post("/users/{uid}/reset-password")
def reset_password(uid: int, db: Session = Depends(get_db), _=Depends(require_permission("account:edit"))):
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.password_hash = hash_password("123456")
    u.must_change_pwd = True
    db.commit()
    return {"code": 0, "data": None, "msg": "密码已重置"}


@router.post("/users/{uid}/set-password")
def set_password(uid: int, body: UserSetPasswordBody, db: Session = Depends(get_db), _=Depends(require_permission("account:edit"))):
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=422, detail="密码长度至少 6 位")
    u.password_hash = hash_password(body.password)
    u.must_change_pwd = False
    db.commit()
    return {"code": 0, "data": None, "msg": "密码已修改"}


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _=Depends(require_permission("account:view"))):
    rows = db.query(SysRole).all()
    return {"code": 0, "data": [{"id": r.id, "name": r.name, "code": r.code} for r in rows], "msg": "ok"}


@router.get("/roles/{rid}/permissions")
def role_permissions(rid: int, db: Session = Depends(get_db), _=Depends(require_permission("account:view"))):
    role = db.query(SysRole).filter(SysRole.id == rid).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    codes = db.query(SysPermission.code).join(
        sys_role_permission, sys_role_permission.c.permission_id == SysPermission.id
    ).filter(sys_role_permission.c.role_id == rid).all()
    return {"code": 0, "data": {"codes": [c[0] for c in codes]}, "msg": "ok"}


@router.put("/roles/{rid}/permissions")
def set_role_permissions(rid: int, body: RolePermissionsBody, db: Session = Depends(get_db),
                         _=Depends(require_permission("account:edit"))):
    role = db.query(SysRole).filter(SysRole.id == rid).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    db.execute(sys_role_permission.delete().where(sys_role_permission.c.role_id == rid))
    for code in body.codes:
        p = db.query(SysPermission).filter(SysPermission.code == code).first()
        if p:
            db.execute(sys_role_permission.insert().values(role_id=rid, permission_id=p.id))
    db.commit()
    return {"code": 0, "data": None, "msg": "权限已保存"}


@router.get("/permissions")
def list_permissions(db: Session = Depends(get_db), _=Depends(require_permission("account:view"))):
    rows = db.query(SysPermission).all()
    return {"code": 0, "data": [{"id": p.id, "code": p.code, "label": p.label, "module": p.module} for p in rows], "msg": "ok"}
