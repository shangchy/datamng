"""AI 助手路由：SSE 聊天 + 会话管理"""
import json
import traceback
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AiMessage, AiSession, AiToolCall, SysUser
from ..ai.agent import available, chat_stream
from ..ai.metrics import TOOLS

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatBody(BaseModel):
    session_id: int = 0
    message: str = ""


def _sse(data: dict) -> str:
    return "data: " + json.dumps(data, ensure_ascii=False, default=str) + "\n\n"


@router.post("/chat")
def chat(body: ChatBody, db: Session = Depends(get_db), user: SysUser = Depends(get_current_user)):
    msg_text = (body.message or "").strip()
    if not msg_text:
        raise HTTPException(status_code=422, detail="消息不能为空")

    user_id = user.id

    session = None
    if body.session_id:
        session = db.query(AiSession).filter(AiSession.id == body.session_id, AiSession.user_id == user_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
    if session is None:
        session = AiSession(user_id=user_id, title=msg_text[:20])
        db.add(session)
        db.flush()
    session_id = session.id

    db.add(AiMessage(session_id=session_id, role="user", content=msg_text))
    db.commit()

    history_rows = (db.query(AiMessage)
                    .filter(AiMessage.session_id == session_id)
                    .order_by(AiMessage.id).limit(40).all())
    history = [{"role": m.role, "content": m.content} for m in history_rows
               if m.role in ("user", "assistant") and m.content]

    def gen():
        summary_parts = []
        tool_name = None
        tool_args = None
        try:
            for ev in chat_stream(db, history, msg_text):
                t = ev.get("type")
                if t == "token":
                    summary_parts.append(ev.get("data", ""))
                    yield _sse({"type": "token", "data": ev.get("data", "")})
                elif t == "text":
                    summary_parts.append(ev.get("data", ""))
                    yield _sse({"type": "text", "data": ev.get("data", "")})
                elif t == "card":
                    yield _sse({"type": "card", "data": ev.get("data")})
                elif t == "tool":
                    tool_name = ev["data"].get("tool")
                    tool_args = ev["data"].get("args")
                elif t == "error":
                    yield _sse({"type": "error", "data": ev.get("data")})
                elif t == "done":
                    summary = "".join(summary_parts).strip()
                    assistant = AiMessage(session_id=session_id, role="assistant", content=summary)
                    db.add(assistant)
                    db.flush()
                    if tool_name:
                        db.add(AiToolCall(session_id=session_id, message_id=assistant.id,
                                          user_id=user_id, tool=tool_name,
                                          args_json=json.dumps(tool_args, ensure_ascii=False, default=str),
                                          risk="read", status="ok"))
                    db.execute(update(AiSession).where(AiSession.id == session_id)
                               .values(updated_at=datetime.now()))
                    db.commit()
                    yield _sse({"type": "done", "data": {"session_id": session_id}})
        except Exception as e:  # noqa
            traceback.print_exc()
            yield _sse({"type": "error", "data": f"服务异常：{e}"})
            yield _sse({"type": "done", "data": {"session_id": session_id}})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/sessions")
def list_sessions(db: Session = Depends(get_db), user: SysUser = Depends(get_current_user)):
    rows = (db.query(AiSession).filter(AiSession.user_id == user.id, AiSession.archived == False)  # noqa
            .order_by(AiSession.updated_at.desc()).all())
    data = [{"id": s.id, "title": s.title, "created_at": str(s.created_at), "updated_at": str(s.updated_at)} for s in rows]
    return {"code": 0, "data": data, "msg": "ok"}


@router.get("/sessions/{sid}/messages")
def session_messages(sid: int, db: Session = Depends(get_db), user: SysUser = Depends(get_current_user)):
    session = db.query(AiSession).filter(AiSession.id == sid, AiSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    rows = db.query(AiMessage).filter(AiMessage.session_id == sid).order_by(AiMessage.id).all()
    data = [{"role": m.role, "content": m.content, "tool_calls": m.tool_calls_json, "created_at": str(m.created_at)} for m in rows]
    return {"code": 0, "data": data, "msg": "ok"}


@router.delete("/sessions/{sid}")
def delete_session(sid: int, db: Session = Depends(get_db), user: SysUser = Depends(get_current_user)):
    session = db.query(AiSession).filter(AiSession.id == sid, AiSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.query(AiToolCall).filter(AiToolCall.session_id == sid).delete()
    db.query(AiMessage).filter(AiMessage.session_id == sid).delete()
    db.delete(session)
    db.commit()
    return {"code": 0, "data": None, "msg": "已删除"}


@router.get("/tools")
def tools(_=Depends(get_current_user)):
    data = [{"name": t["function"]["name"], "description": t["function"]["description"]} for t in TOOLS]
    return {"code": 0, "data": {"available": available(), "tools": data}, "msg": "ok"}
