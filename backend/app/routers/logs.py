"""日志管理路由（仅 admin）"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_permission
from ..models import OperationLog
from ..pagination import paginate, ok_page
from ..utils import fmt_dt

router = APIRouter(prefix="/api/logs", tags=["logs"])

LOGIN_ACTIONS = {"login", "login_failed"}


@router.get("")
def list_logs(db: Session = Depends(get_db), _=Depends(require_permission("account:view")),
              type: str = "operation", username: str = "", action: str = "",
              start_date: str = "", end_date: str = "",
              page: int = 1, per_page: int = 10):
    q = db.query(OperationLog)
    if type == "login":
        q = q.filter(OperationLog.action.in_(LOGIN_ACTIONS))
    else:
        q = q.filter(OperationLog.action.notin_(LOGIN_ACTIONS))
    if username:
        q = q.filter(OperationLog.username.like(f"%{username}%"))
    if action:
        q = q.filter(OperationLog.action == action)
    if start_date:
        q = q.filter(OperationLog.created_at >= start_date)
    if end_date:
        q = q.filter(OperationLog.created_at <= end_date + " 23:59:59")
    total, rows = paginate(q.order_by(OperationLog.id.desc()), page, per_page)
    data = [{
        "id": r.id, "username": r.username, "module": r.module, "action": r.action,
        "target": r.target, "detail": r.detail, "ip": r.ip,
        "created_at": fmt_dt(r.created_at),
    } for r in rows]
    return ok_page(data, total)
