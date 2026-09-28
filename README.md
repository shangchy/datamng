# LM 订单管理系统

订单/日活数据/分数据/账单一体化管理系统。前后端分离，后端 FastAPI + SQLAlchemy（PostgreSQL / SQLite），前端 React + Vite。

## 技术栈
- 后端：Python 3.9+ / FastAPI / SQLAlchemy / Pydantic
- 前端：React 18 / Vite
- 数据库：PostgreSQL（开发）/ SQLite（Windows 部署，内置免安装）

## 目录结构
```
├── backend/              # 后端 FastAPI
│   ├── app/              # 应用代码
│   │   ├── main.py       # 入口 + 迁移 + 日志
│   │   ├── models.py     # ORM 模型（表结构）
│   │   ├── tidabiao.py   # 提单表生成
│   │   ├── routers/      # 各业务路由（订单/客户/数据/账单等）
│   │   └── ai/           # AI 助手（DeepSeek）
│   └── requirements.txt
├── frontend/             # 前端 React
│   ├── src/
│   │   ├── pages/        # 页面（订单/客户/日活/账单等）
│   │   └── components/   # 组件
│   └── vite.config.js
├── schema.sql            # 表结构（PostgreSQL DDL，由 models.py 生成）
└── docs/                 # 设计文档
```

## 表结构
- ORM 定义：`backend/app/models.py`
- SQL DDL：`schema.sql`（PostgreSQL）
- 设计文档：`docs/db_design.md`、`docs/SCHEMA_V2.md`

## 启动
```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端（开发）
cd frontend
npm install
npm run dev
```

数据库默认 PostgreSQL（`DATABASE_URL`），可通过环境变量 `.env` 覆盖为 SQLite（`sqlite:///./data/lm.db`）。

## 主要功能
- 订单管理：订单 CRUD / 导入导出 / 提单表生成 / 提单确认 / 停单 / 验重
- 日活数据：导入（按工单号关联订单、洗名库自动补姓名、平台自动关联品类）/ 分数据（按小组分组生成 Excel 打包）/ 洗名
- 洗名库：手机号→姓名/省/市/运营商 维护
- 账单管理：分数据自动生成各代理账单 + 明细
- 基础数据：品类/渠道/运营商/模版/URL 等
- AI 助手：DeepSeek 集成

## 默认账号
admin / Lemon123#
