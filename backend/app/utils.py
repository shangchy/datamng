"""通用工具"""
import re


def fmt_dt(dt):
    """格式化 datetime 为 YYYY-MM-DD HH:MM:SS（去掉微秒）"""
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def norm_region(v):
    """地区字段统一为 | 分隔（兼容 , ， 、 ｜ | ; ； 换行等分隔符）"""
    if not v:
        return ""
    parts = re.split(r"[|｜,，、;；\n\r]+", str(v))
    return "|".join(p.strip() for p in parts if p.strip())


def client_ip(request) -> str:
    """提取客户端 IP（优先 X-Forwarded-For）"""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""
