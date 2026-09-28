"""分页工具"""


def paginate(query, page: int = 1, per_page: int = 10):
    page = max(1, page)
    per_page = min(max(1, per_page), 500)
    total = query.count()
    rows = query.offset((page - 1) * per_page).limit(per_page).all()
    return total, rows


def ok_page(rows, total):
    return {"code": 0, "data": {"total": total, "rows": rows}, "msg": "ok"}
