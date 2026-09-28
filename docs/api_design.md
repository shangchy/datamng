# LM订单管理系统 · API 设计文档

> 依据原型（docs/prototype.html）与数据库设计（docs/db_design.md）整理。
> 技术栈：FastAPI；统一 REST 风格；鉴权 JWT（Bearer）。

---

## 1. 通用约定

### 1.1 请求/响应
- 统一响应：`{ code, data, msg }`；`code=0` 成功，非 0 失败。
- 列表分页参数：`page`（默认 1）、`per_page`（默认 50，最大 200）。
- 列表返回：`{ code:0, data:{ total, rows }, msg:'ok' }`。

### 1.2 鉴权与权限
- 除 `/api/auth/login` 外，均需 `Authorization: Bearer <token>`。
- 权限点：`模块:动作`，如 `account:view`、`account:edit`、`order:view`、`order:edit`。
- 账户维护接口（`/api/users`、`/api/roles`、`/api/permissions`）仅超级管理员（拥有 `account:*`）可访问；后端对每个接口校验权限，前端隐藏菜单为第二道防线。

### 1.3 错误码
| code | 含义 |
|---|---|
| 0 | 成功 |
| 401 | 未登录/凭证失效 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 参数/校验错误 |
| 409 | 唯一约束冲突 |
| 500 | 服务异常 |

---

## 2. 认证 API

### 2.1 登录
- `POST /api/auth/login`
- 入参：`{ username, password }`
- 处理逻辑：
  1. 查询 `sys_user` by username；不存在或密码（bcrypt）不匹配 → 401「用户名或密码错误」。
  2. 状态停用 → 403「账户已停用」。
  3. 登录失败计数，连续 5 次锁定 15 分钟。
  4. 成功：更新 `last_login_at`，返回 JWT + 用户信息 + `must_change_pwd` 标志。
- 响应：`{ code:0, data:{ token, user:{ id, username, nickname, role, permissions, must_change_pwd } } }`

### 2.2 退出
- `POST /api/auth/logout`
- 处理逻辑：使当前 token 失效（黑名单/短期有效期），记录操作日志。

### 2.3 当前用户
- `GET /api/auth/me`
- 响应：当前用户信息 + 角色 + 权限点列表（供前端渲染菜单）。

### 2.4 修改密码
- `POST /api/auth/change-password`
- 入参：`{ old_password, new_password }`
- 处理逻辑：校验旧密码；新密码强度校验；更新 `password_hash`，置 `must_change_pwd=false`。

---

## 3. 账户管理 API（仅 admin）

| 接口 | 方法 | 处理逻辑 |
|---|---|---|
| `/api/users` | GET | 分页查询账户，联角色；支持按用户名/状态筛选 |
| `/api/users` | POST | 校验用户名唯一；bcrypt 加密初始密码；`must_change_pwd=true`；记录日志 |
| `/api/users/{id}` | PUT | 更新昵称/角色/状态；记录日志 |
| `/api/users/{id}/reset-password` | POST | 重置密码为初始值，`must_change_pwd=true` |
| `/api/users/{id}/status` | PUT | 启停用账户；停用后该用户不可登录 |
| `/api/roles` | GET/POST | 角色列表/新增 |
| `/api/permissions` | GET | 权限点字典（供角色勾选） |

---

## 4. 客户 API

### 4.1 列表/详情
- `GET /api/customers?page=&per_page=&code=&name=&ctype=&status=`
- 处理逻辑：按筛选条件分页；返回客户列表（含余额、预警额度等）。

- `GET /api/customers/{id}`（详情）
- 处理逻辑：返回客户基本信息 + 聚合指标（总供货量、总销售额、总利润）：
  - 总供货量 = `SUM(daily_data 该客户作为上游? )`（按口径：下游客户总供货量=其名下供货记录）
  - 总销售额 = `SUM(bill.sales)`，总利润 = `SUM(bill.profit)`。

### 4.2 新增/编辑/删除
- `POST /api/customers`：校验 `code` 唯一；写 `customer`；记录日志。
- `PUT /api/customers/{id}`：更新可编辑字段；`updated_at=now()`；记录日志。
- `DELETE /api/customers/{id}`：若存在关联订单/账单/充值则返回 409「存在关联数据，不可删除」；否则删除。

### 4.3 充值
- `GET /api/customers/{id}/recharges`：充值记录列表（倒序）。
- `POST /api/customers/{id}/recharges`：入参 `{ amount_u, amount_rmb, recharge_date, note }`；事务内写 `customer_recharge` 并累加 `customer.balance`；记录日志。

### 4.4 单价管理
- `GET /api/customers/{id}/prices`：返回渠道列表（渠道名 + 隶属关系）+ 该客户单价。
- `PUT /api/customers/{id}/prices`：入参 `{ prices:[{channel_id, price}] }`；批量 upsert `customer_price`（按 `(customer_id, channel_id)` 唯一）。

### 4.5 客户订单记录
- `GET /api/customers/{id}/orders`：该客户名下订单（对齐订单管理关键字段），供客户详情「订单记录」tab。

---

## 5. 品类 / 渠道 / 运营商 API

### 5.1 品类
- `GET /api/categories`：返回树形（一级含 children 二级）。
- `POST /api/categories`：入参 `{ name, parent_id?, level }`；一级 `parent_id=null, level=1`；二级 `parent_id=一级id, level=2`；校验父子关系。
- `PUT /api/categories/{id}`：改名/状态；`updated_at`。
- `DELETE /api/categories/{id}`：有子品类（level=1）或被 URL 引用 → 409；否则删除。

### 5.2 渠道
- `GET /api/channels`：列表（渠道名、状态）。
- `POST /api/channels`：校验名称唯一。
- `PUT /api/channels/{id}`、`DELETE /api/channels/{id}`：删除时被 `url`/`order`/`customer_price` 引用 → 409。

### 5.3 渠道详情（订单页点渠道）
- `GET /api/channels/{id}/detail`
- 处理逻辑：返回渠道隶属关系（一级品类 → 二级品类 → 渠道）+ 该渠道下 URL 列表（归属方/URL/等级/更新时间）。

### 5.4 运营商
- `GET /api/operators`、`POST`、`PUT /{id}`、`DELETE /{id}`：标准 CRUD，名称唯一。

---

## 6. 配件/URL API

- `GET /api/urls?owner=&cat1_id=&cat2_id=&channel_id=&level=&url=`：分页筛选。
- `POST /api/urls`：入参 `{ owner, cat1_id, cat2_id, channel_id, urls:[{url, level}] }`；**一次可录入多个 URL**，循环写入 `url` 表（每条 `level` 高/中/低）；校验归属方合法。
- `PUT /api/urls/{id}`：编辑单条 URL 及其等级。
- `DELETE /api/urls/{id}`：删除（确认）。

---

## 7. 订单 API

### 7.1 列表/详情
- `GET /api/orders?page=&per_page=&status=&order_no=&upstream=&customer_id=&channel_id=&task_name=&province=&...`
  - 处理逻辑：支持全字段组合筛选（前端查询条件 = 列表字段）；状态、渠道等生成下拉选项（distinct）。
- `GET /api/orders/{id}`：订单详情（含多 URL 列表、地区四字段）。

### 7.2 新建/改单
- `POST /api/orders`
- `PUT /api/orders/{id}`
- 入参：`{ customer_id, upstream, channel_id, task_name, urls:[{url,level}], qty, province, city, excl_province, excl_city, age_min, age_max, pv, start_date, end_date }`
- 处理逻辑：
  1. 校验必填（下游/上游/渠道/任务名/数量）。
  2. **地区规则校验**：province 与 city 互斥；province=全国 时允许 excl_province；province=单省 时允许 excl_city；多值以 `｜` 分隔。
  3. 新建：生成订单号（DD+日期+序号），`status='已提交'`，`created_at/updated_at=now()`。
  4. 改单：更新可编辑字段，`status` 重置为 `'已提交'`，`updated_at=now()`。
  5. 写入 `order_url`（多 URL）。
  6. 记录操作日志。

### 7.3 停单
- `POST /api/orders/{id}/stop`
- 入参：`{ reason, note }`
- 处理逻辑：`status='已停单'`、`stop_date=today`、`updated_at=now()`；写操作日志。

### 7.4 状态自动流转（定时任务）
- 每天扫描 `order`：`start_date`（业务日期）距今 +2 天且 `status='已提交'` → 更新为 `'在执中'`。

### 7.5 导出 / 导入 / 模版
- `GET /api/orders/export?<筛选条件>`：按当前条件导出 Excel（列=列表列）。
- `GET /api/orders/template`：下载空白模版（含表头列）。
- `POST /api/orders/import`：上传 Excel 批量导入，逐行校验后写库；返回成功/失败行明细。

---

## 8. 日活数据 API

- `GET /api/daily-data?page=&per_page=&cat1_id=&cat2_id=&platform=&channel_id=&phone=&customer_id=&...`
  - 处理逻辑：全字段组合筛选（含省份/地市/排除省/排除市），手机号支持精确/模糊。
- `GET /api/daily-data/export`：按条件导出 Excel。

---

## 9. 公积金 API

- `GET /api/fund?page=&per_page=&phone=&name=&gender=&province=&city=&company=&deposit_status=&...`
- `POST /api/fund`、`PUT /api/fund/{id}`、`DELETE /api/fund/{id}`：标准 CRUD。
- `POST /api/fund/import`：上传 Excel；按 `(phone, source_file)` 唯一幂等去重；返回导入条数。
- `GET /api/fund/export`：按条件导出 Excel。

---

## 10. 账单 API

- `GET /api/bills?customer_id=&start_date=&end_date=`
- 处理逻辑：按客户 + 业务日期区间返回每日账单（进货量/销售金额/余额/利润/创建日期）；客户名关联客户表（前端点击客户名查客户详情）。

---

## 11. 预警 API

- `GET /api/alerts?type=&status=&customer_id=`：预警列表。
- `PUT /api/alerts/{id}`：入参 `{ status:'已处理' }`；标记处理。
- 定时任务：
  - 停单提醒：`order` 中 `stop_date` 到达当日 → 生成 `alert(level=提醒, type=停单提醒, customer_id, task_name, content='停单日 XX 已到达...')`。
  - 账单预警：`customer.balance < warn_amount` → 生成 `alert(level=预警, type=账单预警)`。

---

## 12. 工作台 API

- `GET /api/dashboard/summary`：返回指标卡数据（今日交付量/上游订单量/上游数据量/下游订单量/营业额/待处理预警）。
- `GET /api/dashboard/trend?granularity=day|week|month&start=&end=`：趋势数据（上游/下游数据量、订单量、利润）。
- `GET /api/dashboard/rank?period=`：下游客户业务量排名。

---

## 13. 权限矩阵

| 模块 | 权限点 | admin | 运营(lemon) |
|---|---|---|---|
| 订单 | order:view/edit/stop/import/export | ✅ | ✅ |
| 日活/公积金 | data:view/import/export | ✅ | ✅ |
| 客户 | customer:view/edit/recharge | ✅ | ✅ |
| 配件/品类/渠道/运营商 | master:view/edit | ✅ | ✅ |
| 账单 | bill:view | ✅ | ✅ |
| 预警 | alert:view/handle | ✅ | ✅ |
| 账户 | account:view/edit | ✅ | ❌ |

---

## 14. 与数据库表映射速查

| 页面/接口 | 主要表 |
|---|---|
| 账户管理 | sys_user / sys_role / sys_permission / sys_role_permission |
| 客户管理 | customer / customer_recharge / customer_price |
| 品类/渠道/运营商 | category / channel / operator |
| 配件管理 | url |
| 订单管理 | order / order_url |
| 日活数据 | daily_data |
| 公积金 | fund |
| 账单 | bill |
| 预警 | alert |
| 操作日志 | operation_log |
