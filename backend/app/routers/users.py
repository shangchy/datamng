"""账户管理路由（仅 admin）"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_permission
from ..models import SysUser, SysRole, SysPermission, sys_role_permission
from ..schemas import UserCreate, UserUpdate, UserSetPasswordBody, RolePermissionsBody, RoleCreate, RoleUpdate
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
        "created_at": fmt_dt(u.created_at), "created_by": u.created_by or "",
        "updated_at": fmt_dt(u.updated_at), "updated_by": u.updated_by or "",
    } for u in rows], total)


@router.post("/users")
def create_user(body: UserCreate, db: Session = Depends(get_db), user=Depends(require_permission("account:edit"))):
    if db.query(SysUser).filter(SysUser.username == body.username).first():
        raise HTTPException(status_code=409, detail="用户名已存在")
    label = (user.nickname or user.username) if user else ""
    u = SysUser(username=body.username, nickname=body.nickname, role_id=body.role_id,
                password_hash=hash_password(body.password), must_change_pwd=True,
                created_by=label, updated_by=label)
    db.add(u)
    db.commit()
    return {"code": 0, "data": {"id": u.id}, "msg": "ok"}


@router.put("/users/{uid}")
def update_user(uid: int, body: UserUpdate, db: Session = Depends(get_db), user=Depends(require_permission("account:edit"))):
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.nickname is not None:
        u.nickname = body.nickname
    if body.role_id is not None:
        u.role_id = body.role_id
    if body.status is not None:
        u.status = body.status
    u.updated_by = (user.nickname or user.username) if user else ""
    db.commit()
    return {"code": 0, "data": None, "msg": "ok"}


@router.post("/users/{uid}/reset-password")
def reset_password(uid: int, db: Session = Depends(get_db), user=Depends(require_permission("account:edit"))):
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.password_hash = hash_password("123456")
    u.must_change_pwd = True
    u.updated_by = (user.nickname or user.username) if user else ""
    db.commit()
    return {"code": 0, "data": None, "msg": "密码已重置"}


@router.post("/users/{uid}/set-password")
def set_password(uid: int, body: UserSetPasswordBody, db: Session = Depends(get_db), user=Depends(require_permission("account:edit"))):
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=422, detail="密码长度至少 6 位")
    u.password_hash = hash_password(body.password)
    u.must_change_pwd = False
    u.updated_by = (user.nickname or user.username) if user else ""
    db.commit()
    return {"code": 0, "data": None, "msg": "密码已修改"}


@router.delete("/users/{uid}")
def delete_user(uid: int, db: Session = Depends(get_db), _=Depends(require_permission("account:edit"))):
    u = db.query(SysUser).filter(SysUser.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.username == "admin":
        raise HTTPException(status_code=400, detail="超级管理员不可删除")
    db.delete(u)
    db.commit()
    return {"code": 0, "data": None, "msg": "已删除"}


@router.get("/roles")
def list_roles(db: Session = Depends(get_db), _=Depends(require_permission("account:view"))):
    rows = db.query(SysRole).all()
    return {"code": 0, "data": [{"id": r.id, "name": r.name, "code": r.code} for r in rows], "msg": "ok"}


@router.post("/roles")
def create_role(body: RoleCreate, db: Session = Depends(get_db), _=Depends(require_permission("account:edit"))):
    name = (body.name or "").strip()
    code = (body.code or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="角色名称不能为空")
    if not code:
        raise HTTPException(status_code=422, detail="角色编码不能为空")
    if db.query(SysRole).filter(SysRole.code == code).first():
        raise HTTPException(status_code=409, detail="角色编码已存在")
    r = SysRole(name=name, code=code, note=(body.note or "").strip(), is_builtin=False)
    db.add(r)
    db.commit()
    return {"code": 0, "data": {"id": r.id}, "msg": "角色已创建"}


@router.put("/roles/{rid}")
def update_role(rid: int, body: RoleUpdate, db: Session = Depends(get_db), _=Depends(require_permission("account:edit"))):
    r = db.query(SysRole).filter(SysRole.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="角色不存在")
    if r.code == "admin":
        raise HTTPException(status_code=400, detail="超级管理员角色不可修改")
    if body.name is not None:
        name = (body.name or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="角色名称不能为空")
        r.name = name
    if body.note is not None:
        r.note = (body.note or "").strip()
    db.commit()
    return {"code": 0, "data": None, "msg": "角色已更新"}


@router.delete("/roles/{rid}")
def delete_role(rid: int, db: Session = Depends(get_db), _=Depends(require_permission("account:edit"))):
    r = db.query(SysRole).filter(SysRole.id == rid).first()
    if not r:
        raise HTTPException(status_code=404, detail="角色不存在")
    if r.code == "admin":
        raise HTTPException(status_code=400, detail="超级管理员角色不可删除")
    if db.query(SysUser).filter(SysUser.role_id == rid).count() > 0:
        raise HTTPException(status_code=400, detail="该角色下仍有账户，请先调整这些账户的角色")
    db.execute(sys_role_permission.delete().where(sys_role_permission.c.role_id == rid))
    db.delete(r)
    db.commit()
    return {"code": 0, "data": None, "msg": "角色已删除"}


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
