"""AI 助手 · 指标语义层（只读口径函数）

每个指标 = 一个只读 SQL 口径函数，模型只负责把自然语言翻译成 {指标 + 参数}，
数字永远由这里计算，杜绝幻觉。返回统一结构供前端渲染表格卡。
"""
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_

from ..models import (Alert, Bill, Channel, Customer, CustomerRecharge,
                      DailyData, Fund, Order, WashName)


def _mask_phone(p):
    if p is None:
        return ""
    p = str(p)
    if len(p) >= 7:
        return p[:3] + "****" + p[-4:]
    return p[:3] + "****"


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _latest_biz_date(db):
    d = db.query(func.max(Bill.biz_date)).scalar()
    return d


def _fmt(v, nd=2):
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return round(float(v), nd)
    return v


def _table(title, columns, rows, caliber, source):
    return {"type": "table", "title": title, "columns": columns,
            "rows": rows, "caliber": caliber, "source": source}


# ---------------- 指标实现 ----------------

def overview_today(db, date=None):
    d = _parse_date(date) or _latest_biz_date(db) or date.today()
    sales = db.query(func.sum(Bill.sales)).filter(Bill.biz_date == d).scalar() or 0
    profit = db.query(func.sum(Bill.profit)).filter(Bill.biz_date == d).scalar() or 0
    qty = db.query(func.sum(Bill.purchase_qty)).filter(Bill.biz_date == d).scalar() or 0
    active = db.query(func.count(Order.id)).filter(Order.status == "在执").scalar() or 0
    alerts = db.query(func.count(Alert.id)).filter(Alert.status == "未处理").scalar() or 0
    rows = [
        {"指标": "营业额(元)", "数值": _fmt(sales)},
        {"指标": "利润(元)", "数值": _fmt(profit)},
        {"指标": "进货量", "数值": int(qty or 0)},
        {"指标": "在执订单数", "数值": int(active)},
        {"指标": "待处理预警", "数值": int(alerts)},
    ]
    return _table(f"经营概览 · {d}", ["指标", "数值"], rows,
                  "营业额/利润/进货量 = 当日 bill 表汇总；在执订单 = orders 状态为在执；预警 = alert 未处理", "bill/orders/alert")


def sales_trend(db, start_date=None, end_date=None, days=7):
    if start_date and end_date:
        s, e = _parse_date(start_date), _parse_date(end_date)
    else:
        e = _latest_biz_date(db) or date.today()
        s = e - timedelta(days=max(1, int(days or 7)) - 1)
    rows = (db.query(Bill.biz_date, func.sum(Bill.sales), func.sum(Bill.profit), func.sum(Bill.purchase_qty))
            .filter(Bill.biz_date >= s, Bill.biz_date <= e)
            .group_by(Bill.biz_date).order_by(Bill.biz_date).all())
    data = [{"日期": str(r[0]), "营业额": _fmt(r[1]), "利润": _fmt(r[2]), "进货量": int(r[3] or 0)} for r in rows]
    return _table(f"经营趋势 · {s} ~ {e}", ["日期", "营业额", "利润", "进货量"], data,
                  "按 bill.biz_date 聚合的营业额/利润/进货量", "bill")


def customer_rank(db, start_date=None, end_date=None, days=7, limit=10):
    if start_date and end_date:
        s, e = _parse_date(start_date), _parse_date(end_date)
    else:
        e = _latest_biz_date(db) or date.today()
        s = e - timedelta(days=max(1, int(days or 7)) - 1)
    rows = (db.query(Customer.name, func.sum(Bill.sales), func.sum(Bill.profit), func.sum(Bill.purchase_qty))
            .join(Bill, Bill.customer_id == Customer.id)
            .filter(Bill.biz_date >= s, Bill.biz_date <= e)
            .group_by(Customer.id, Customer.name)
            .order_by(func.sum(Bill.sales).desc()).limit(int(limit or 10)).all())
    data = [{"客户": r[0] or "", "营业额": _fmt(r[1]), "利润": _fmt(r[2]), "进货量": int(r[3] or 0)} for r in rows]
    return _table(f"代理排行 · {s} ~ {e}", ["客户", "营业额", "利润", "进货量"], data,
                  "按 bill.customer_id 聚合，按营业额降序", "bill/customer")


def customer_balance(db):
    rows = db.query(Customer.code, Customer.name, Customer.balance, Customer.warn_amount).filter(
        Customer.ctype == "downstream").order_by(Customer.balance.desc()).all()
    data = [{"编号": r[0], "客户": r[1], "余额": _fmt(r[2]), "预警额度": _fmt(r[3])} for r in rows]
    return _table("客户余额", ["编号", "客户", "余额", "预警额度"], data,
                  "下游客户当前余额与预警额度", "customer")


def low_balance(db):
    rows = (db.query(Customer.code, Customer.name, Customer.balance, Customer.warn_amount)
            .filter(Customer.ctype == "downstream", Customer.warn_amount > 0,
                    Customer.balance < Customer.warn_amount).all())
    data = [{"编号": r[0], "客户": r[1], "余额": _fmt(r[2]), "预警额度": _fmt(r[3])} for r in rows]
    return _table("低余额客户（欠款预警）", ["编号", "客户", "余额", "预警额度"], data,
                  "余额 < 预警额度 的下游客户", "customer")


def active_orders(db, limit=50):
    rows = (db.query(Order.order_no, Order.task_name, Customer.name, Channel.name, Order.qty, Order.province)
            .outerjoin(Customer, Order.customer_id == Customer.id)
            .outerjoin(Channel, Order.channel_id == Channel.id)
            .filter(Order.status == "在执")
            .order_by(Order.id.desc()).limit(int(limit or 50)).all())
    data = [{"订单号": r[0], "任务名": r[1] or "", "下游": r[2] or "", "渠道": r[3] or "", "数量": r[4], "地区": r[5] or ""} for r in rows]
    return _table("在执订单", ["订单号", "任务名", "下游", "渠道", "数量", "地区"], data,
                  "orders.status=在执", "orders")


def stop_alerts(db):
    rows = (db.query(Alert.task_name, Customer.name, Alert.content, Alert.trigger_time)
            .outerjoin(Customer, Alert.customer_id == Customer.id)
            .filter(Alert.type == "停单提醒", Alert.status == "未处理").all())
    data = [{"任务": r[0] or "", "客户": r[1] or "", "内容": r[2] or "", "触发时间": str(r[3])} for r in rows]
    return _table("停单提醒（未处理）", ["任务", "客户", "内容", "触发时间"], data,
                  "alert.type=停单提醒 且 status=未处理", "alert")


def bill_alerts(db):
    rows = (db.query(Customer.name, Customer.balance, Customer.warn_amount, Alert.content)
            .join(Alert, Alert.customer_id == Customer.id)
            .filter(Alert.type == "账单预警", Alert.status == "未处理").all())
    data = [{"客户": r[0] or "", "余额": _fmt(r[1]), "预警额度": _fmt(r[2]), "内容": r[3] or ""} for r in rows]
    return _table("账单预警（未处理）", ["客户", "余额", "预警额度", "内容"], data,
                  "alert.type=账单预警 且 status=未处理", "alert/customer")


def channel_qty(db, date=None):
    d = _parse_date(date) or _latest_biz_date(db) or date.today()
    rows = (db.query(Channel.name, func.count(DailyData.id))
            .join(Channel, DailyData.channel_id == Channel.id)
            .filter(DailyData.biz_date == d)
            .group_by(Channel.name).order_by(func.count(DailyData.id).desc()).all())
    data = [{"渠道": r[0] or "", "数量": int(r[1])} for r in rows]
    return _table(f"渠道数量 · {d}", ["渠道", "数量"], data,
                  "按 daily_data.channel_id 统计当日明细数量", "daily_data/channel")


def recharge_records(db, limit=50):
    rows = (db.query(Customer.name, CustomerRecharge.recharge_date, CustomerRecharge.amount_u, CustomerRecharge.amount_rmb)
            .join(Customer, CustomerRecharge.customer_id == Customer.id)
            .order_by(CustomerRecharge.id.desc()).limit(int(limit or 50)).all())
    data = [{"客户": r[0] or "", "日期": str(r[1]), "充值(U)": _fmt(r[2]), "折算RMB": _fmt(r[3])} for r in rows]
    return _table("充值记录", ["客户", "日期", "充值(U)", "折算RMB"], data,
                  "customer_recharge 最近记录", "customer_recharge")


def phone_lookup(db, phone=None):
    if not phone:
        return _table("手机号查询", ["字段", "值"], [], "请输入要查询的手机号", "-")
    d_rows = (db.query(DailyData.phone, DailyData.name, DailyData.upstream, DailyData.task_name,
                       Channel.name, DailyData.province, DailyData.city, DailyData.wash_status, DailyData.biz_date)
              .outerjoin(Channel, DailyData.channel_id == Channel.id)
              .filter(DailyData.phone == phone).order_by(DailyData.id.desc()).limit(50).all())
    data = [{"来源": "日活", "姓名": r[1] or "", "上游": r[2] or "", "任务": r[3] or "",
             "渠道": r[4] or "", "省市": f"{r[5] or ''}{r[6] or ''}", "洗名状态": r[7] or "", "日期": str(r[8])} for r in d_rows]
    f_rows = db.query(Fund).filter(Fund.phone == phone).limit(20).all()
    for f in f_rows:
        data.append({"来源": "公积金", "姓名": f.name or "", "上游": "", "任务": "",
                     "渠道": f.company or "", "省市": f"{f.province or ''}{f.city or ''}",
                     "洗名状态": f.deposit_status or "", "日期": f.open_date or ""})
    return _table(f"手机号 {_mask_phone(phone)} 全历史", ["来源", "姓名", "上游", "任务", "渠道", "省市", "洗名状态", "日期"], data,
                  "跨 daily_data 与 fund 检索，手机号已脱敏", "daily_data/fund")


def order_list(db, status=None, limit=50):
    q = (db.query(Order.order_no, Order.task_name, Customer.name, Channel.name, Order.qty, Order.status)
         .outerjoin(Customer, Order.customer_id == Customer.id)
         .outerjoin(Channel, Order.channel_id == Channel.id))
    if status:
        q = q.filter(Order.status == status)
    rows = q.order_by(Order.id.desc()).limit(int(limit or 50)).all()
    data = [{"订单号": r[0], "任务名": r[1] or "", "下游": r[2] or "", "渠道": r[3] or "", "数量": r[4], "状态": r[5]} for r in rows]
    return _table("订单列表", ["订单号", "任务名", "下游", "渠道", "数量", "状态"], data,
                  "orders 列表", "orders")


def daily_data_query(db, date=None, customer=None, channel=None, phone=None, limit=50):
    q = db.query(DailyData.biz_date, DailyData.upstream, DailyData.task_name, DailyData.phone,
                 DailyData.name, DailyData.province, DailyData.city, DailyData.customer,
                 DailyData.channel, DailyData.platform)
    d = _parse_date(date)
    if d:
        q = q.filter(DailyData.biz_date == d)
    if customer:
        q = q.filter(DailyData.customer.like(f"%{customer}%"))
    if channel:
        q = q.filter(DailyData.channel == channel)
    if phone:
        q = q.filter(DailyData.phone == phone)
    total = q.count()
    rows = q.order_by(DailyData.id.desc()).limit(int(limit or 50)).all()
    data = [{"日期": str(r[0]), "甲方": r[1] or "", "任务": r[2] or "", "手机号": _mask_phone(r[3]),
             "姓名": r[4] or "", "省市": f"{r[5] or ''}{r[6] or ''}", "代理": r[7] or "",
             "渠道": r[8] or "", "平台": r[9] or ""} for r in rows]
    return _table(f"日活数据明细（共 {total} 条，展示 {len(data)} 条）",
                  ["日期", "甲方", "任务", "手机号", "姓名", "省市", "代理", "渠道", "平台"], data,
                  "daily_data 明细，手机号已脱敏", "daily_data")


def wash_name_lookup(db, phone=None, name=None):
    q = db.query(WashName.phone, WashName.name, WashName.province, WashName.city, WashName.operator)
    if phone:
        q = q.filter(WashName.phone == phone)
    if name:
        q = q.filter(WashName.name.like(f"%{name}%"))
    rows = q.order_by(WashName.id.desc()).limit(50).all()
    data = [{"手机号": _mask_phone(r[0]), "姓名": r[1] or "", "省": r[2] or "", "市": r[3] or "",
             "运营商": r[4] or ""} for r in rows]
    return _table("洗名库查询", ["手机号", "姓名", "省", "市", "运营商"], data,
                  "wash_name 洗名库，手机号已脱敏", "wash_name")


def bill_detail(db, customer=None, date=None, start_date=None, end_date=None, limit=50):
    q = (db.query(Customer.code, Customer.name, Bill.biz_date, Bill.purchase_qty, Bill.sales, Bill.balance)
         .join(Bill, Bill.customer_id == Customer.id))
    if customer:
        q = q.filter(or_(Customer.code.like(f"%{customer}%"), Customer.name.like(f"%{customer}%")))
    d = _parse_date(date)
    if d:
        q = q.filter(Bill.biz_date == d)
    s = _parse_date(start_date)
    if s:
        q = q.filter(Bill.biz_date >= s)
    e = _parse_date(end_date)
    if e:
        q = q.filter(Bill.biz_date <= e)
    rows = q.order_by(Bill.biz_date.desc()).limit(int(limit or 50)).all()
    data = [{"编号": r[0], "客户": r[1], "日期": str(r[2]), "进货量": r[3] or 0,
             "销售": _fmt(r[4]), "余额": _fmt(r[5])} for r in rows]
    return _table("账单明细", ["编号", "客户", "日期", "进货量", "销售", "余额"], data,
                  "bill 明细，余额为该日滚动余额", "bill/customer")


def work_order_check(db, date=None):
    d = _parse_date(date) or _latest_biz_date(db) or date.today()
    counts = dict(db.query(DailyData.task_id, func.count(DailyData.id))
                  .filter(DailyData.biz_date == d, DailyData.task_id.isnot(None))
                  .group_by(DailyData.task_id).all())
    rows = (db.query(Order.task_id, Order.task_name, Customer.name, Channel.name)
            .outerjoin(Customer, Order.customer_id == Customer.id)
            .outerjoin(Channel, Order.channel_id == Channel.id)
            .filter(Order.status == "在执").all())
    data = [{"工单号": r[0] or "", "任务名": r[1] or "", "代理": r[2] or "",
             "渠道": r[3] or "", "数据量": counts.get(r[0], 0)} for r in rows]
    data.sort(key=lambda x: x["数据量"])
    return _table(f"工单检查 · {d}（按数据量升序，找少出/未出）",
                  ["工单号", "任务名", "代理", "渠道", "数据量"], data,
                  "在执工单在所选日期的 daily_data 数据量，升序", "orders/daily_data")


def category_stats(db, date=None):
    d = _parse_date(date) or _latest_biz_date(db) or date.today()
    rows = (db.query(DailyData.cat1, DailyData.cat2, DailyData.platform, func.count(DailyData.id))
            .filter(DailyData.biz_date == d)
            .group_by(DailyData.cat1, DailyData.cat2, DailyData.platform)
            .order_by(func.count(DailyData.id).desc()).all())
    data = [{"一级品类": r[0] or "", "二级品类": r[1] or "", "平台": r[2] or "", "数量": int(r[3])} for r in rows]
    return _table(f"品类/平台分布 · {d}", ["一级品类", "二级品类", "平台", "数量"], data,
                  "按 daily_data 的 cat1/cat2/platform 统计当日数量", "daily_data")


# ---------------- 工具注册表（供 LLM function-calling） ----------------

IMPL = {
    "overview_today": overview_today,
    "sales_trend": sales_trend,
    "customer_rank": customer_rank,
    "customer_balance": customer_balance,
    "low_balance": low_balance,
    "active_orders": active_orders,
    "stop_alerts": stop_alerts,
    "bill_alerts": bill_alerts,
    "channel_qty": channel_qty,
    "recharge_records": recharge_records,
    "phone_lookup": phone_lookup,
    "order_list": order_list,
    "daily_data_query": daily_data_query,
    "wash_name_lookup": wash_name_lookup,
    "bill_detail": bill_detail,
    "work_order_check": work_order_check,
    "category_stats": category_stats,
}

TOOLS = [
    {"type": "function", "function": {
        "name": "overview_today", "description": "某日经营概览：营业额、利润、进货量、在执订单数、待处理预警数。用于「今天/昨天经营怎么样」类问题。",
        "parameters": {"type": "object", "properties": {"date": {"type": "string", "description": "日期 YYYY-MM-DD，缺省用最近有数据的日期"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "sales_trend", "description": "营业额/利润/进货量趋势。用于「最近N天趋势」类问题。",
        "parameters": {"type": "object", "properties": {
            "start_date": {"type": "string"}, "end_date": {"type": "string"},
            "days": {"type": "integer", "description": "缺省范围天数，默认7"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "customer_rank", "description": "代理排行（按营业额/利润排序）。用于「哪个代理赚最多」类问题。",
        "parameters": {"type": "object", "properties": {
            "start_date": {"type": "string"}, "end_date": {"type": "string"},
            "days": {"type": "integer"}, "limit": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "customer_balance", "description": "所有下游客户当前余额与预警额度。用于「客户余额」类问题。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "low_balance", "description": "低余额/欠款客户（余额低于预警额度）。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "active_orders", "description": "当前在执订单列表。",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "stop_alerts", "description": "未处理的停单提醒。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "bill_alerts", "description": "未处理的账单预警（余额低于预警额度）。",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "channel_qty", "description": "某日各渠道数量分布。",
        "parameters": {"type": "object", "properties": {"date": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "recharge_records", "description": "客户充值记录。",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "phone_lookup", "description": "按手机号跨库查询全历史（日活+公积金）。用于「138...这条是谁的」类问题。",
        "parameters": {"type": "object", "properties": {"phone": {"type": "string", "description": "手机号"}}, "required": ["phone"]}}},
    {"type": "function", "function": {
        "name": "order_list", "description": "订单列表，可按状态过滤。",
        "parameters": {"type": "object", "properties": {"status": {"type": "string"}, "limit": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "daily_data_query", "description": "日活数据明细查询。可按日期、代理、渠道、手机号过滤，返回明细条数及样例。用于「某天某代理出了多少条」类问题。",
        "parameters": {"type": "object", "properties": {
            "date": {"type": "string", "description": "日期 YYYY-MM-DD"},
            "customer": {"type": "string", "description": "一级代理编号或名称"},
            "channel": {"type": "string", "description": "渠道名"},
            "phone": {"type": "string", "description": "手机号"},
            "limit": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "wash_name_lookup", "description": "洗名库查询。按手机号或姓名查洗名记录。用于「某某手机号洗名了没」类问题。",
        "parameters": {"type": "object", "properties": {
            "phone": {"type": "string", "description": "手机号"}, "name": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "bill_detail", "description": "账单明细查询。按客户、日期或日期区间查进货量/销售/余额（余额为每日滚动余额）。",
        "parameters": {"type": "object", "properties": {
            "customer": {"type": "string", "description": "客户编号或名称"},
            "date": {"type": "string"}, "start_date": {"type": "string"}, "end_date": {"type": "string"},
            "limit": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "work_order_check", "description": "工单检查：所有在执工单在所选日期的数据量（升序，找少出/未出的工单）。",
        "parameters": {"type": "object", "properties": {"date": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "category_stats", "description": "品类/平台分布：按一级品类、二级品类、平台统计某日数据量。",
        "parameters": {"type": "object", "properties": {"date": {"type": "string"}}, "required": []}}},
]


def run_tool(db, name: str, args: dict) -> dict:
    fn = IMPL.get(name)
    if not fn:
        return _table(name, ["错误"], [], f"未知工具 {name}", "-")
    try:
        return fn(db, **args)
    except Exception as e:  # noqa
        return _table(name, ["错误"], [], f"查询失败：{e}", "-")
