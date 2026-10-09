"""Pydantic 请求体"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class LoginBody(BaseModel):
    username: str
    password: str


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


class UserCreate(BaseModel):
    username: str
    nickname: str = ""
    role_id: int
    password: str = "123456"


class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    role_id: Optional[int] = None
    status: Optional[int] = None


class UserSetPasswordBody(BaseModel):
    password: str


class RolePermissionsBody(BaseModel):
    codes: list[str] = []


class CustomerBody(BaseModel):
    code: str
    name: str
    ctype: str = "downstream"
    tg_id: Optional[str] = ""
    is_accounted: bool = True
    warn_amount: float = 0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    bill_tpl_id: Optional[int] = None
    note: Optional[str] = ""
    status: int = 1


class RechargeBody(BaseModel):
    amount_u: Optional[float] = None
    amount_rmb: Optional[float] = None
    recharge_date: date
    note: str = ""


class PriceBody(BaseModel):
    prices: list[dict]  # [{channel_id, price}]


class CategoryBody(BaseModel):
    name: str
    parent_id: Optional[int] = None
    level: int = 1
    sort_no: int = 0
    status: int = 1


class SimpleBody(BaseModel):
    name: str
    status: int = 1


class UrlBody(BaseModel):
    owner_id: Optional[int] = None
    cat1_id: Optional[int] = None
    cat2_id: Optional[int] = None
    platform_id: Optional[int] = None
    channel_id: Optional[int] = None
    name: Optional[str] = ""
    urls: list[dict] = []  # [{url, level}]


class OrderBody(BaseModel):
    customer_id: int
    upstream_id: Optional[int] = None
    channel_id: Optional[int] = None
    operator_id: Optional[int] = None
    task_name: str = ""
    task_id: Optional[str] = ""
    urls: list[dict] = []
    qty: Optional[int] = None
    duration: Optional[str] = ""
    status: str = "未提"
    province: str = ""
    city: str = ""
    excl_province: str = ""
    excl_city: str = ""
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    pv: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    template_id: Optional[int] = None
    filename_rule: Optional[str] = ""
    dist_config: Optional[dict] = None
    order_date: Optional[date] = None
    price: Optional[float] = None
    secondary_agent: Optional[str] = ""
    platform: Optional[str] = ""
    tpl_id: Optional[int] = None
    group_name: Optional[str] = ""
    export_filename: Optional[str] = ""
    add_name: bool = False
    check_collision: bool = False


class BatchGroupBody(BaseModel):
    ids: list[int]
    group_name: str = ""


class TemplateBody(BaseModel):
    ttype: str = ""
    tpl_type: str = "其他"
    code: str = ""
    name: str = ""
    description: str = ""
    status: int = 1


class PlatformBody(BaseModel):
    name: str
    cat_id: int
    sort_no: int = 0
    status: int = 1


class OrderTemplateBody(BaseModel):
    code: str
    name: str
    party: str = ""
    columns: list[dict] = []
    style: dict = {}
    filename_rule: str = ""
    match_rule: dict = {}
    status: int = 1


class OrderDistConfigBody(BaseModel):
    template_id: Optional[int] = None
    filename_rule: Optional[str] = ""
    dist_config: Optional[dict] = None


class StopBody(BaseModel):
    reason: str = ""
    note: str = ""
    order_date: Optional[date] = None


class BatchStopBody(BaseModel):
    ids: list[int]
    reason: str = ""
    note: str = ""
    order_date: Optional[date] = None


class ReopenBody(BaseModel):
    order_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class GenerateBody(BaseModel):
    order_ids: list[int] = []
    date: str = ""  # 更新日期 YYYY-MM-DD，用于文件名
    confirm: bool = False  # 分数据：是否已确认继续（忽略未设定出数模版的订单）


class AlertHandleBody(BaseModel):
    status: str = "已处理"


class ExtractBody(BaseModel):
    filters: dict = {}             # 日活筛选条件
    start_date: str = ""           # 时间段开始
    end_date: str = ""             # 时间段结束
    limit: int = 0                 # 抽取条数
    customer_id: Optional[int] = None  # 给代理
    target_name: str = ""          # 给其他人（自由文本）
    price: float = 0               # 单价（元/条）
    note: str = ""                 # 备注
