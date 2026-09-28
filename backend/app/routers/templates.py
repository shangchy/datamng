"""模版管理路由：模版文件（模版类型/模版编号 + 文件上传下载预览）"""
import io
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Template
from ..schemas import TemplateBody
from ..utils import fmt_dt

router = APIRouter(prefix="/api/templates", tags=["templates"])


def _next_code(db):
    max_n = 0
    for (code,) in db.query(Template.code).all():
        m = re.match(r"^MB-(\d+)$", code or "")
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"MB-{max_n + 1:03d}"


def _dump(t: Template) -> dict:
    return {
        "id": t.id, "ttype": t.ttype or "", "code": t.code,
        "name": t.name or "", "file_name": t.name or "",
        "file_type": t.file_type or "",
        "has_file": bool(t.file_data),
        "description": t.description or "",
        "status": t.status,
        "created_at": fmt_dt(t.created_at), "updated_at": fmt_dt(t.updated_at),
    }


@router.get("")
def list_templates(db: Session = Depends(get_db), _=Depends(get_current_user),
                   q: str = ""):
    query = db.query(Template)
    if q:
        like = f"%{q}%"
        query = query.filter((Template.ttype.like(like)) | (Template.code.like(like)) | (Template.name.like(like)))
    rows = query.order_by(Template.id).all()
    return {"code": 0, "data": [_dump(t) for t in rows], "msg": "ok"}


@router.post("")
def create_template(body: TemplateBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    code = (body.code or "").strip() or _next_code(db)
    if db.query(Template).filter(Template.code == code).first():
        raise HTTPException(status_code=409, detail="模版编号已存在")
    t = Template(ttype=body.ttype, code=code, name="", description=body.description or "", status=body.status)
    db.add(t)
    db.commit()
    return {"code": 0, "data": {"id": t.id, "code": code}, "msg": "已创建"}


@router.put("/{tid}")
def update_template(tid: int, body: TemplateBody, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Template).filter(Template.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="模版不存在")
    t.ttype = body.ttype
    t.description = body.description or ""
    t.status = body.status
    db.commit()
    return {"code": 0, "data": None, "msg": "已保存"}


@router.delete("/{tid}")
def delete_template(tid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Template).filter(Template.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="模版不存在")
    db.delete(t)
    db.commit()
    return {"code": 0, "data": None, "msg": "已删除"}


@router.post("/{tid}/upload")
async def upload_template(tid: int, file: UploadFile = File(...),
                          db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Template).filter(Template.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="模版不存在")
    content = await file.read()
    fn = file.filename or ""
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    t.file_data = content
    t.file_type = ext
    if fn:
        t.name = fn
    db.commit()
    return {"code": 0, "data": {"filename": fn}, "msg": "模版文件已上传"}


@router.delete("/{tid}/file")
def delete_template_file(tid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Template).filter(Template.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="模版不存在")
    t.file_data = None
    t.file_type = ""
    t.name = ""
    db.commit()
    return {"code": 0, "data": None, "msg": "模版文件已删除"}


@router.get("/{tid}/preview")
def preview_template(tid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Template).filter(Template.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="模版不存在")
    if not t.file_data:
        raise HTTPException(status_code=404, detail="该模版未上传文件")
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(bytes(t.file_data)), data_only=True)
    sheets = []
    for ws in wb.worksheets:
        rows = []
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            rows.append(["" if v is None else str(v) for v in row])
            if i >= 49:
                rows.append(["…（仅预览前 50 行）"])
                break
        sheets.append({"name": ws.title, "rows": rows})
    wb.close()
    return {"code": 0, "data": {"filename": t.name or t.code, "sheets": sheets}, "msg": "ok"}


@router.get("/{tid}/download")
def download_template(tid: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    t = db.query(Template).filter(Template.id == tid).first()
    if not t:
        raise HTTPException(status_code=404, detail="模版不存在")
    if not t.file_data:
        raise HTTPException(status_code=404, detail="该模版未上传文件")
    ext = t.file_type or "xlsx"
    filename = t.name or t.code
    if "." not in filename:
        filename = f"{filename}.{ext}"
    media = {
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xls": "application/vnd.ms-excel",
    }.get(ext, "application/octet-stream")
    return Response(content=bytes(t.file_data), media_type=media,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})
