"""ORM 模型（对应 docs/db_design.md）"""
from datetime import datetime

from sqlalchemy import (Integer, Boolean, Column, Date, DateTime, ForeignKey,
                        Integer, LargeBinary, Numeric, SmallInteger, String, Table, Text)
from sqlalchemy.orm import relationship

from .database import Base


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============ 系统：账户与权限 ============

class SysRole(Base):
    __tablename__ = "sys_role"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    is_builtin = Column(Boolean, default=False)
    note = Column(Text)


class SysPermission(Base):
    __tablename__ = "sys_permission"
    id = Column(Integer, primary_key=True)
    code = Column(String(100), nullable=False, unique=True)
    label = Column(String(100), nullable=False)
    module = Column(String(50))


sys_role_permission = Table(
    "sys_role_permission", Base.metadata,
    Column("role_id", Integer, ForeignKey("sys_role.id"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("sys_permission.id"), primary_key=True),
)


class SysUser(Base):
    __tablename__ = "sys_user"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(200), nullable=False)
    nickname = Column(String(50))
    role_id = Column(Integer, ForeignKey("sys_role.id"))
    status = Column(SmallInteger, default=1)
    must_change_pwd = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    role = relationship("SysRole", lazy="joined")


# ============ 主数据：客户 ============

class Customer(Base, TimestampMixin):
    __tablename__ = "customer"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    ctype = Column(String(20), nullable=False)  # upstream / downstream
    tg_id = Column(String(100))
    wash_mode = Column(String(20), default="只分")
    is_accounted = Column(Boolean, default=True)
    discount = Column(Numeric(5, 4), default=1)
    balance = Column(Numeric(14, 2), default=0)
    warn_amount = Column(Numeric(14, 2), default=0)
    start_date = Column(Date)                        # 合作开始日期
    end_date = Column(Date)                          # 合作结束日期
    bill_tpl_id = Column(Integer, ForeignKey("template.id"))   # 账单模版
    note = Column(Text)
    status = Column(SmallInteger, default=1)


class CustomerRecharge(Base):
    __tablename__ = "customer_recharge"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    recharge_date = Column(Date, nullable=False)
    amount_u = Column(Numeric(14, 2), nullable=False)
    amount_rmb = Column(Numeric(14, 2))
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


class CustomerPrice(Base, TimestampMixin):
    __tablename__ = "customer_price"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=False)
    price = Column(Numeric(8, 4), nullable=False)


# ============ 主数据：品类/渠道/运营商 ============

class Category(Base, TimestampMixin):
    __tablename__ = "category"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("category.id"))
    level = Column(SmallInteger, nullable=False)  # 1 一级 / 2 二级
    sort_no = Column(SmallInteger, default=0)
    status = Column(SmallInteger, default=1)


class Channel(Base, TimestampMixin):
    __tablename__ = "channel"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    status = Column(SmallInteger, default=1)


class Operator(Base, TimestampMixin):
    __tablename__ = "operator"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    status = Column(SmallInteger, default=1)


# ============ 主数据：配件/URL ============

class Url(Base, TimestampMixin):
    __tablename__ = "url"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    owner_id = Column(Integer, ForeignKey("customer.id"))
    cat1_id = Column(Integer, ForeignKey("category.id"))
    cat2_id = Column(Integer, ForeignKey("category.id"))
    platform_id = Column(Integer, ForeignKey("platform.id"))
    channel_id = Column(Integer, ForeignKey("channel.id"))
    url = Column(Text, nullable=False)
    level = Column(String(10), default="中")  # 高/中/低
    status = Column(SmallInteger, default=1)


# ============ 主数据：平台（挂在二级品类下） ============

class Platform(Base, TimestampMixin):
    __tablename__ = "platform"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    cat_id = Column(Integer, ForeignKey("category.id"), nullable=False)  # 二级品类
    sort_no = Column(SmallInteger, default=0)
    status = Column(SmallInteger, default=1)


# ============ 业务：订单 ============

class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_no = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey("customer.id"))
    upstream_id = Column(Integer, ForeignKey("customer.id"))
    channel_id = Column(Integer, ForeignKey("channel.id"))
    operator_id = Column(Integer, ForeignKey("operator.id"))
    task_name = Column(String(200))
    task_id = Column(String(100))
    qty = Column(Integer)
    duration = Column(String(50))
    province = Column(String(500))
    city = Column(String(500))
    excl_province = Column(String(500))
    excl_city = Column(String(500))
    age_min = Column(Integer)
    age_max = Column(Integer)
    pv = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    stop_date = Column(Date)
    status = Column(String(20), default="未提")  # 未提/在执/已停/改单
    batch_no = Column(String(50))                # 提单批次（如 20260921-01）
    dup_order_nos = Column(Text)                 # 重复订单编号（多个换行分隔）
    change_fields_json = Column(Text)            # 改单时发生变更的字段（JSON 数组）
    template_id = Column(Integer, ForeignKey("order_template.id"))
    filename_rule = Column(String(200))
    dist_config_json = Column(Text)
    order_date = Column(Date)                     # 提单日
    price = Column(Numeric(10, 4))                # 定价（元/条）
    secondary_agent = Column(String(100))         # 二级代理（自由文本）
    platform = Column(String(100))                # 平台（快照）
    tpl_id = Column(Integer, ForeignKey("template.id"))  # 模版编号（关联模版管理）
    group_name = Column(String(100))              # 分组（文本）
    export_filename = Column(String(200))         # 导出文件名（文本）
    add_name = Column(Boolean, default=False)     # 是否加名 是/否
    urls = relationship("OrderUrl", cascade="all, delete-orphan", backref="order")


# ============ 业务：模版管理（模版文件） ============

class Template(Base, TimestampMixin):
    __tablename__ = "template"
    id = Column(Integer, primary_key=True)
    ttype = Column(String(50))                    # 模版名称
    tpl_type = Column(String(20), default="其他")  # 模版类型：订单/出数/账单/其他
    code = Column(String(100), nullable=False, unique=True)  # 模版编号
    name = Column(String(200), nullable=False)    # 模版文件名
    file_data = Column(LargeBinary)               # 上传的模版文件
    file_type = Column(String(50))                # 文件扩展名/类型
    description = Column(Text)                    # 说明（模版用途/填写注意事项）
    status = Column(SmallInteger, default=1)


class OrderTemplate(Base, TimestampMixin):
    __tablename__ = "order_template"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    party = Column(String(20))                     # 牛 / 新 / 通用
    columns_json = Column(Text)                    # 列定义
    style_json = Column(Text)                      # 版式
    filename_rule = Column(String(200))            # 文件名规则
    match_rule_json = Column(Text)                 # 自动匹配规则
    status = Column(SmallInteger, default=1)


class OrderUrl(Base):
    __tablename__ = "order_url"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    url = Column(Text, nullable=False)
    level = Column(String(10), default="中")
    sort_no = Column(SmallInteger, default=0)


# ============ 业务：提单历史（生成提单表的订单快照，全文本，无关联） ============

class TidabiaoHistory(Base):
    __tablename__ = "tidabiao_history"
    id = Column(Integer, primary_key=True)
    batch_no = Column(String(50))               # 提单批次
    order_id = Column(Integer)                  # 原订单 id（仅记录，不关联）
    order_no = Column(String(50))
    status = Column(String(20))
    order_date = Column(String(50))
    upstream = Column(String(100))
    customer = Column(String(100))
    secondary_agent = Column(String(100))
    channel = Column(String(100))
    operator = Column(String(50))
    task_name = Column(String(200))
    task_id = Column(String(100))
    url = Column(Text)
    qty = Column(String(50))
    duration = Column(String(50))
    age_min = Column(String(50))
    age_max = Column(String(50))
    pv = Column(String(50))
    province = Column(String(500))
    city = Column(String(500))
    excl_province = Column(String(500))
    excl_city = Column(String(500))
    start_date = Column(String(50))
    end_date = Column(String(50))
    price = Column(String(50))
    platform = Column(String(100))
    group_name = Column(String(100))
    tpl_code = Column(String(100))
    add_name = Column(String(10))
    created_at = Column(DateTime, default=datetime.now)


# ============ 业务：日活数据 ============

class DailyData(Base, TimestampMixin):
    __tablename__ = "daily_data"
    id = Column(Integer, primary_key=True)
    biz_date = Column(Date, nullable=False)      # 数据日期
    upstream = Column(String(100))               # 甲方
    task_id = Column(String(100))                # 任务id（工单号）
    task_name = Column(String(200))              # 任务名
    phone = Column(String(20), nullable=False)   # 手机号
    name = Column(String(50))                    # 姓名（洗名后填写）
    province = Column(String(50))                # 省
    city = Column(String(50))                    # 市
    operator = Column(String(50))                # 运营商
    cat1 = Column(String(100))                   # 一级品类（按平台关联品类管理）
    cat2 = Column(String(100))                   # 二级品类（按平台关联品类管理）
    platform = Column(String(100))               # 平台（关联订单）
    customer = Column(String(100))               # 一级代理（关联订单）
    secondary_agent = Column(String(100))        # 二级代理（关联订单）
    channel = Column(String(100))                # 渠道（关联订单）
    source_file = Column(String(500))            # 来源文件名
    source_file_id = Column(Integer)             # 源文件记录 id（用于下载）


# ============ 业务：洗名库（手机号 → 姓名） ============

class WashName(Base, TimestampMixin):
    __tablename__ = "wash_name"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False, unique=True)   # 手机号
    name = Column(String(50))                                 # 姓名
    province = Column(String(50))                             # 省
    city = Column(String(50))                                 # 市
    operator = Column(String(50))                             # 运营商（文件 isp 列）


# ============ 业务：源文件管理（上传的原始数据文件） ============

class SourceFile(Base):
    __tablename__ = "source_file"
    id = Column(Integer, primary_key=True)
    filename = Column(String(500))               # 文件名
    file_data = Column(LargeBinary)              # 文件内容
    file_type = Column(String(20))               # zip / xlsx / xls
    biz_date = Column(String(50))                # 数据日期
    party = Column(String(50))                   # 甲方（牛/新）
    size = Column(Integer)                       # 文件大小（字节）
    created_at = Column(DateTime, default=datetime.now)


# ============ 业务：公积金 ============

class Fund(Base):
    __tablename__ = "fund"
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), nullable=False)
    name = Column(String(50))
    id_card = Column(String(30))
    gender = Column(String(10))
    province = Column(String(50))
    city = Column(String(50))
    company = Column(String(200))
    company_type = Column(String(50))
    base = Column(Numeric(14, 2))
    ratio = Column(String(20))
    monthly = Column(Numeric(14, 2))
    balance = Column(Numeric(14, 2))
    deposit_status = Column(String(20))
    open_date = Column(String(20))
    pay_to = Column(String(20))
    operator = Column(String(20))
    source_file = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)


# ============ 业务：账单 ============

class Bill(Base):
    __tablename__ = "bill"
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False)
    biz_date = Column(Date, nullable=False)
    purchase_qty = Column(Integer, default=0)
    sales = Column(Numeric(14, 2), default=0)
    balance = Column(Numeric(14, 2), default=0)
    profit = Column(Numeric(14, 2), default=0)
    created_at = Column(DateTime, default=datetime.now)


# ============ 业务：预警 ============

class Alert(Base):
    __tablename__ = "alert"
    id = Column(Integer, primary_key=True)
    level = Column(String(10), nullable=False)  # 提醒/预警
    type = Column(String(20), nullable=False)   # 停单提醒/账单预警
    customer_id = Column(Integer, ForeignKey("customer.id"))
    task_name = Column(String(200))
    content = Column(Text)
    trigger_time = Column(DateTime)
    status = Column(String(20), default="未处理")
    created_at = Column(DateTime, default=datetime.now)


# ============ 通用：操作日志 ============

class OperationLog(Base):
    __tablename__ = "operation_log"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    username = Column(String(50))
    module = Column(String(50))
    action = Column(String(50))
    target = Column(String(200))
    detail = Column(Text)
    ip = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)


# ============ 系统配置 ============

class SysConfig(Base):
    __tablename__ = "sys_config"
    key = Column(String(50), primary_key=True)
    value = Column(String(200))
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============ AI 助手 ============

class AiSession(Base):
    __tablename__ = "ai_session"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sys_user.id"))
    title = Column(String(100))
    archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class AiMessage(Base):
    __tablename__ = "ai_message"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("ai_session.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text)
    tool_calls_json = Column(Text)
    model = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)


class AiToolCall(Base):
    __tablename__ = "ai_tool_call"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("ai_session.id"))
    message_id = Column(Integer, ForeignKey("ai_message.id"))
    user_id = Column(Integer)
    tool = Column(String(50), nullable=False)
    args_json = Column(Text)
    risk = Column(String(10), default="read")
    status = Column(String(20), default="ok")
    result_json = Column(Text)
    error = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
