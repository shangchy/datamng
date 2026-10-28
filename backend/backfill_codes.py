"""一次性脚本：为品类(二级)与平台补编号，并补建 code 字段（幂等，可重复执行）。

用于生产环境部署时同步本次表结构变更 + 自动为二级品类/平台设定编号。

用法（在 backend 目录下运行）：
    python backfill_codes.py
"""
from sqlalchemy import inspect, text

from app.database import SessionLocal, engine
from app.models import Category, Platform


def ensure_columns():
    """确保 category / platform 表存在 code 字段（幂等）"""
    insp = inspect(engine)
    table_names = set(insp.get_table_names())
    with engine.begin() as conn:
        if "category" in table_names:
            cat_cols = {c["name"] for c in insp.get_columns("category")}
            if "code" not in cat_cols:
                conn.execute(text("ALTER TABLE category ADD COLUMN code VARCHAR(50)"))
                print("已添加 category.code 字段")
        if "platform" in table_names:
            plat_cols = {c["name"] for c in insp.get_columns("platform")}
            if "code" not in plat_cols:
                conn.execute(text("ALTER TABLE platform ADD COLUMN code VARCHAR(10)"))
                print("已添加 platform.code 字段")


def backfill(db):
    from pypinyin import pinyin, Style
    # 二级品类编号：拼音首字母连写，重复则追加数字后缀
    used = set()
    for c in db.query(Category).filter(Category.level == 2).order_by(Category.id).all():
        if c.code:
            used.add(c.code)
            continue
        base = "".join((p[0] if p else "") for p in pinyin(c.name or "", style=Style.FIRST_LETTER)).lower()
        code = base or f"c{c.id}"
        n = 2
        while code in used:
            code = f"{base}{n}"
            n += 1
        c.code = code
        used.add(code)
    # 平台编号：4 位数字，全局唯一
    plat_used = {p.code for p in db.query(Platform).filter(Platform.code.isnot(None), Platform.code != "").all()}
    for p in db.query(Platform).filter((Platform.code.is_(None)) | (Platform.code == "")).order_by(Platform.id).all():
        code = ""
        for num in range(1, 10000):
            c = f"{num:04d}"
            if c not in plat_used:
                code = c
                plat_used.add(c)
                break
        p.code = code or None
    db.commit()


def main():
    ensure_columns()
    db = SessionLocal()
    try:
        backfill(db)
        cat2_total = db.query(Category).filter(Category.level == 2).count()
        cat2_coded = db.query(Category).filter(Category.level == 2, Category.code.isnot(None), Category.code != "").count()
        plat_total = db.query(Platform).count()
        plat_coded = db.query(Platform).filter(Platform.code.isnot(None), Platform.code != "").count()
        print(f"二级品类 {cat2_coded}/{cat2_total} 已设编号")
        print(f"平台 {plat_coded}/{plat_total} 已设编号")
    finally:
        db.close()


if __name__ == "__main__":
    main()
