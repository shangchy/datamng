# 嘟嘟业务数据库 v2 设计（去冗余 · 按现有数据盘点）

> 2026-09-03 护卫设计 · 目标：有价值的数据入库、表结构不冗余、支撑历史统计/报表/对账
> 现状库：`data/dudu.db`（v1.1~v1.3，16 表，daily_records 已 190 万行手机号明细）
> 本文件为**目标设计 + 迁移方案**，不直接改动在跑系统；配套建表脚本 `schema_v2.sql`

---

## 一、现状盘点：现有 16 张表与冗余问题

| 现有表 | 行数 | 作用 | 问题 |
|---|---|---|---|
| daily_records | **190 万** | 手机号级明细 | **最大冗余源**：①每行重复存 agent_name / task_name / channel 文本；②channel 有脏值（`蓝鸟-小程序-526`、None 79 万行）；③统计历史根本不需要手机号级 |
| agents | 16 | 代理规则 | 基本可用，稍补列 |
| agent_accounts | 16 | 代理当前余额 | balance 与 balance_history 最新值重复 → 冗余（保留联系方式等静态属性即可） |
| agent_recharges | 21 | 充值流水 | ✔ 已是账务流水 |
| agent_prices | 105 | 代理单价历史 | ✔ 保留（出货单价随日期变化，必须留历史） |
| agent_balance_history | 0 | 每日余额 | ✔ 账务快照，应每天记账后写入（现在空 = 没在记） |
| daily_dedup | 8 | 去重数 | 是 fact_delivery 可推导的聚合 → v2 合并进交付事实 |
| wash_cost | 8 | 洗名费用 | ✔ 账务事实（含 note 算法），v2 扩展为 fact_wash（补唯一值/未命中列） |
| daily_business | 0 | 每日经营汇总 | **冗余**：ship_qty/ship_amount/profit 全可推导；只留「进货总额手动覆盖」这一个不可推导事实 |
| daily_adjustments | 2 | 每日调价 | ✔ 保留 |
| match_table | 368 | 工单号↔任务名 | 回执反查的缓存，可留可废（权威源=每日回执） |
| upstreams | 2 | 上游客户 | ✔ |
| upstream_files | 6 | 上游文件归档 | ✔ 文件级留痕 |
| import_log | 5 | 导入日志 | ✔ |
| purchase_prices | 8 | 进货单价 | 并入 v2 渠道字典（同一渠道集，一个地方维护） |

**核心结论**：
1. 手机号明细 ≠ 统计源。统计/对账/利润只需要 **「日期 × 代理 × 任务 × 渠道 × 数量」** 汇总级，每天几百行，一年不到 10 万行。
2. 渠道口径散落 4 处（daily_records.channel 文本 / bill.py 行位映射 / purchase_prices / 回执类型），必须收敛为**一张渠道字典**。
3. 金额分两类：**可推导的**（数量×单价）不落库，靠价格历史现算；**外部事实**（BOSS 手动覆盖的进货总额、充值、余额快照、洗名费）落库。

---

## 二、v2 目标结构：字典层 + 事实层（星型）

```
维度表（小、稳定）                    事实表（大、只增）
┌──────────────┐
│ dim_agent    │◄──┐
│ dim_channel  │◄──┼── fact_delivery  每日任务交付（收/去重/交付数量）
│ dim_task     │◄──┘        │
│ dim_upstream │            ├── fact_wash     洗名（唯一/未命中/费用）
└──────────────┘            ├── fact_bill     账单（代理×日期×渠道 qty+单价快照）
                            ├── fact_recharge 充值流水（=现 agent_recharges）
                            ├── fact_balance  每日余额快照（=现 balance_history）
                            └── purchase_override 进货总额手动覆盖（原 daily_business 瘦身）
```

### 字典层

**dim_agent**（现 agents + 补折扣列）
| 列 | 说明 |
|---|---|
| agent_id PK | 660001…880008 |
| agent_name | 财神/知南… |
| wash_mode | 只分/洗名/合并/只加工/跳过 |
| split_by | 地区/平台/平铺/不拆 |
| is_accounted | 是否记账发账单（888888=0） |
| discount / discount_start / discount_end | 结算折扣（660003 九折 8/29~9/13） |

**dim_channel**（★ 全库唯一渠道口径，替代散落映射）
| 列 | 说明 | 示例 |
|---|---|---|
| channel_id PK | | 1 |
| bill_name | 账单口径名 | 106短信劫持 |
| pipe_name | 流水线口径名 | 106 |
| channel_type | 回执类型归并 | 106/小程序/直播间/DPI-白/DPI-灰 |
| isp | 运营商 | 移动/联通/电信（106、小程序为 NULL） |
| upstream_price | 甲方进货单价（成本） | 0.06 |
| sort_no | 账单行位顺序 | 8 |

种子 9 行：106短信劫持(0.06)/小程序(0.05)/直播间(上游单价待确认)/DPI-白 移动(0.04)/DPI-灰 移动(0.05)/DPI-白 电信(0.05)/DPI-灰 电信(0.06)/DPI-白 联通(0.05)/DPI-灰 联通(0.05) —— 单价与 purchase_prices、甲方账单 G 列一致；直播间无上游行（甲方牛无此渠道），单价置 NULL 待 BOSS 确认。

**dim_task**（任务字典：任务名 → 代理、首末在执日期；渠道不落这里，渠道按当天回执判断落事实）
| 列 | 说明 |
|---|---|
| task_id PK | |
| task_name UNIQUE | 660002-内江-中银消金 |
| agent_id FK | 任务名前 6 位 |
| first_seen / last_seen | 在执起止 |
| is_active | 当前是否在执（按最新回执更新） |

**dim_upstream**（= 现 upstreams，不动）

### 事实层

**fact_delivery —— 每日任务级交付流水（v2 核心表，替代手机号明细做一切统计）**
| 列 | 说明 |
|---|---|
| biz_date | YYYY-MM-DD |
| upstream_id FK | 新甲方/牛 |
| agent_id FK | |
| task_id FK | |
| channel_id FK | 当天回执类型+运营商推出 |
| ver | 880008 两版：`v1`(全库去重)/`v2`(平台库去重)；其他代理 `''` |
| qty_received | 上游匹配条数（原始） |
| qty_dedup | 当日去重删除条数 |
| qty_delivered | 交付条数（= received − dedup，洗名代理为洗名前数） |

UNIQUE(biz_date, task_id, ver)。每天约 300~600 行。
**能推导出（全部不另建表）**：渠道总量、各代理各渠道数量（记账用）、888888 渠道统计、去重总数、进货/出货口径数量。

**fact_wash —— 洗名账务**（扩展现 wash_cost）
| 列 | 说明 |
|---|---|
| agent_id, biz_date, ver PK | |
| unique_cnt | 唯一值（去重后条数） |
| miss_cnt | 未命中 |
| fee | 洗名费 = (unique_cnt − miss_cnt) × 0.012，公式由系统算 |
| note | 批次备注 |

**fact_bill —— 账单事实**（权威源 = BOSS 的账单 Excel；每日记账后反读同步或 bill.py 写入时同步）
| 列 | 说明 |
|---|---|
| agent_id, biz_date, channel_id PK | |
| qty | 当天该渠道数量（Excel 里的数，BOSS 手改以 Excel 为准） |
| unit_price | 单价快照（当天生效价） |

出货额 = Σ qty×unit_price（SQL 现算，不落库）；888888 无账单不写本表。

**fact_recharge**（= 现 agent_recharges）、**fact_balance**（= 现 agent_balance_history，记账后写 D5 快照）

**purchase_override**（原 daily_business 瘦身成"只存不可推导项"）
| 列 | 说明 |
|---|---|
| biz_date PK | |
| purchase_amount | 进货总额：BOSS 手动覆盖值（上游真实成本，只有 BOSS 知道） |
| note | |
| ship_amount / profit / wash_cost | **一律不落库**，视图现算 = 出货额 − 进货总额 − Σfact_wash.fee |

---

## 三、利润/经营报表口径（v2 = 视图现算，杜绝双写不一致）

```
进货数据量 purchase_qty = Σ fact_delivery.qty_received（或 upstream_files.row_count 文件口径）
出货数据量 ship_qty     = Σ fact_delivery.qty_delivered
出货总额 ship_amount    = Σ fact_bill.qty × unit_price（880008 按 ver=v2 口径）
进货总额 purchase_amount = purchase_override（手动，唯一外部事实）
洗名费用 wash_fee       = Σ fact_wash.fee（1.2 分/条）
利润 profit             = ship_amount − purchase_amount − wash_fee
余额 balance            = 上期余额 − 本周出货 + 本周充值（D5 权威，直接快照不重算）
```

全部由 SQL/视图产生：一份代码、一个口径，不会再出现 daily_business 里 profit 忘了扣洗名费这类漏算。

---

## 四、手机号明细（daily_records 190 万行）去留

统计/报表/利润 **完全不需要**手机号级，需要的场景只有两个：
1. **去重比对**（880008 全库去重 / 660009 每日去重）——目前用 Excel 去重库，脚本正常，不依赖 DB
2. **回查**"某个手机号历史上给过谁"——低频

建议（三选一，待 BOSS 拍板）：
- **A（推荐）**：统计全走 v2 汇总表；daily_records **冻结不再写入**，历史保留可查。库体积从此每天只长几百行而不是几万行。
- **B**：daily_records 只留近 30 天供回查，更早的归档到独立老库文件 `dudu_legacy.db`（主库瘦身）。
- **C**：彻底删除手机号明细（不推荐，回查能力丢失）。

> 手机号属个人信息，SQLite 明文存在本机可接受（现 Excel 也是明文）；**不要**把这个库同步到任何云盘/网盘。

---

## 五、与现有 16 表映射一览

| v2 | 处理 | 现有表 |
|---|---|---|
| dim_agent | 改造 | agents（加 discount 列） |
| dim_channel | **新建** | 收敛 purchase_prices + bill.py 行位 + 回执类型 |
| dim_task | **新建** | 从回执+流水线生成 |
| dim_upstream | 保留 | upstreams |
| fact_delivery | **新建** | 取代 daily_records/daily_dedup 的统计职能 |
| fact_wash | 改造 | wash_cost（加 unique_cnt/miss_cnt/ver） |
| fact_bill | **新建** | 账单 Excel 反读（含 888888 排除、880008 v2 口径） |
| fact_recharge | 保留 | agent_recharges |
| fact_balance | 启用 | agent_balance_history（开始每天写 D5） |
| purchase_override | 改造 | daily_business（删可推导列，留手动覆盖） |
| 丢弃 | 停用 | daily_records（冻结）/ daily_dedup（并入）/ agent_accounts.balance（取 balance_history 最新） |
| 保留 | 保留 | agent_prices / daily_adjustments / upstream_files / import_log / match_table |

---

## 六、迁移步骤（分期，先不动在跑系统）

1. **本期（只加不改）**：执行 schema_v2.sql（在 dudu.db 里新增 dim_* / fact_* 表，不碰旧表旧代码）→ 现有系统零影响
2. 改 `importer.py`：流水线导入时同时写 fact_delivery（旧 daily_records 写入停掉）
3. 改 `bill.py` / 记账流程：记账后写 fact_bill、fact_balance（D5）
4. 洗名拆分流程补写 fact_wash（现 wash_cost 逻辑已有，扩列即可）
5. 页面统计查询切到 v2 表 + 利润视图；验证 8/30~9/2 数据回放一致后，旧表冻结/归档
6. 880008 脚本缺口补齐后，fact_delivery 天然支持 ver=v1/v2 双版本记账口径

---

## 七、待 BOSS 拍板

1. 手机号明细去留：A 冻结 / B 近30天+老库归档 / C 删除
2. 直播间渠道：上游/甲方无单价行，进货单价怎么算？（或本渠道数据量极少、成本另计）
3. 执行节奏：先只建表（本期），还是连 importer/bill.py 改造一起做？

---

## 八、落地状态与补充（2026-09-05 重构完成）

### 落地状态
- ✅ schema_v2.sql 全部表已建；**历史回填完成**（backfill_v2.py）：8/13~9/3 共 17 个业务日
- ✅ fact_delivery/fact_bill 每日由 importer 导入后自动重建（v2.rebuild_date，幂等）；页面/API 全部改走 v2
- ✅ 对账：9/1~9/3 与 BOSS 利润表逐日逐代理全等（数量/销售额/进货/洗名/利润）
- ✅ 手机号索引（idx_records_phone）已建，196 万行明细查询提速
- ✅ 每日流水线 detail json 增加平台列（item[6]），后续批次自动入库平台

### 规格修正（相对本文档原设计）
1. **fact_delivery 唯一键加 channel_id**：`UNIQUE(biz_date, task_id, channel_id, ver)`——现实里同一任务同一天可跨渠道（如 880008 平台文件白/灰同出、老牛期平台任务多渠道）；原 UNIQUE(biz_date, task_id) 会丢数据。schema_v2.sql 已改，db.py 启动自动迁移旧表。
2. **同任务跨上游合并**：蓝鸟与新甲方同任务同日合并为一行交付流水，upstream_id 取占比多者（上游文件级来量看 upstream_files）。
3. **新增补充表 `bill_adjust`**（代理×日期 让利/补数金额）：口径 = 账单 Excel H19 补数行，amount>0 冲减营业额、<0 加收；660003 九折不落此表（走 dim_agent.discount 折扣系数）。
4. **积压排除表驱动**：v2.REBUILD_EXCLUDE = {日期: [代理]}，如 9/1~9/2 的 660009（利润表口径：未出货不计数量/成本/营收）。
5. **账单期边界**：金额（营业额/进货/洗名/利润）仅 2026-08-30 起（老牛期无账单体系）；老牛期只统计数量/渠道/平台。
6. **上游文件清单重建**：upstream_files 清重复（8/31 ×4）并补齐 8/13~9/3（老日活文件 8/13~8/24 = 交付级文件，与明细一致；8/1~8/12 为旧实例原始转储不入）。
7. **660007/660006 单价 +2 分**：660007 证据显示 9/2 生效（9/1 利润表按旧价）；660006 9/1 起。见 backfill_v2.py PRICE_BUMP。

### 遗留（待 BOSS）
- 手机号明细去留（A 冻结不再写 / B 近30天+老库 / C 删除）仍未拍板：当前继续写入（v2 汇总同步维护，无性能压力）
- 直播间渠道上游单价 NULL（无甲方行），若出该渠道数据需定成本
- 8/30~8/31 无利润表文件：9 折按折扣系数自动算，若当时账单未打折需手工校正
