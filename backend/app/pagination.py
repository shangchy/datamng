"""分页工具"""
from sqlalchemy import func


def paginate(query, page: int = 1, per_page: int = 10):
    page = max(1, page)
    per_page = min(max(1, per_page), 10000)
    offset = (page - 1) * per_page
    # 用直接 SELECT count(*) 代替 ORM query.count()，避免 count(subquery) 的子查询开销（大表尤其明显）
    count_stmt = query.statement.with_only_columns(func.count()).order_by(None)
    # with_only_columns 会丢掉"单表且无 where/join"的隐式 from，需手动补回，否则 count 结果错误
    if not count_stmt.get_final_froms():
        for f in query.statement.get_final_froms():
            count_stmt = count_stmt.select_from(f)
    total = query.session.execute(count_stmt).scalar() or 0
    rows = query.offset(offset).limit(per_page).all()
    return total, rows


def ok_page(rows, total):
    return {"code": 0, "data": {"total": total, "rows": rows}, "msg": "ok"}
