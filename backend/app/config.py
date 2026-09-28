"""应用配置"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# 数据库：默认 PostgreSQL（可用 DATABASE_URL 覆盖为 SQLite 等）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://lm:lm123456@127.0.0.1:5432/lm",
)

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "lm-order-system-dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

# DeepSeek（AI 助手）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
