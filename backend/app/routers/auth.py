"""认证路由"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_permissions
from ..models import SysUser, SysRole
from ..schemas import LoginBody, ChangePasswordBody
from ..security import hash_password, verify_password, create_access_token
from ..models import OperationLog
from ..utils import client_ip
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _log(db, user, module, action, target=""):
    db.add(OperationLog(user_id=user.id if user else None, username=user.username if user else None,
                        module=module, action=action, target=target, created_at=datetime.now()))
    db.commit()


@router.post("/login")
def login(body: LoginBody, request: Request, db: Session = Depends(get_db)):
    user = db.query(SysUser).filter(SysUser.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        db.add(OperationLog(user_id=user.id if user else None, username=body.username,
                            module="auth", action="login_failed", target=body.username,
                            detail="用户名或密码错误", ip=client_ip(request), created_at=datetime.now()))
        db.commit()
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账户已停用")
    user.last_login_at = datetime.now()
    db.add(OperationLog(user_id=user.id, username=user.username, module="auth", action="login",
                        target=user.username, detail="", ip=client_ip(request), created_at=datetime.now()))
    db.commit()
    perms = get_permissions(user, db)
    token = create_access_token(user.username)
    return {"code": 0, "data": {
        "token": token,
        "user": {
            "id": user.id, "username": user.username, "nickname": user.nickname,
            "role": user.role.name if user.role else "", "role_code": user.role.code if user.role else "",
            "permissions": sorted(perms), "must_change_pwd": user.must_change_pwd,
        }
    }, "msg": "ok"}


@router.get("/me")
def me(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    perms = get_permissions(user, db)
    return {"code": 0, "data": {
        "id": user.id, "username": user.username, "nickname": user.nickname,
        "role": user.role.name if user.role else "", "role_code": user.role.code if user.role else "",
        "permissions": sorted(perms), "must_change_pwd": user.must_change_pwd,
    }, "msg": "ok"}


@router.post("/change-password")
def change_password(body: ChangePasswordBody, user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=422, detail="原密码错误")
    user.password_hash = hash_password(body.new_password)
    user.must_change_pwd = False
    db.commit()
    _log(db, user, "auth", "change-password")
    return {"code": 0, "data": None, "msg": "密码已修改"}
