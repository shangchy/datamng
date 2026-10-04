"""依赖注入：当前用户、权限校验"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import SysUser, SysRole, sys_role_permission, SysPermission
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> SysUser:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    user = db.query(SysUser).filter(SysUser.username == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已停用")
    return user


def get_permissions(user: SysUser, db: Session) -> set[str]:
    if not user.role_id:
        return set()
    role = db.query(SysRole).filter(SysRole.id == user.role_id).first()
    if not role:
        return set()
    if role.code == "admin":
        return {"*"}
    rows = db.query(SysPermission.code).join(
        sys_role_permission, sys_role_permission.c.permission_id == SysPermission.id
    ).filter(sys_role_permission.c.role_id == role.id).all()
    return {r[0] for r in rows}


def require_admin(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)) -> SysUser:
    """仅系统管理员（role.code == 'admin'，其权限集为 {'*'}）"""
    if "*" in get_permissions(user, db):
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅系统管理员可操作")


def require_permission(perm: str):
    def checker(user: SysUser = Depends(get_current_user), db: Session = Depends(get_db)):
        perms = get_permissions(user, db)
        if "*" in perms or perm in perms:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    return checker
