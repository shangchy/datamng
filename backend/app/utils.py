"""通用工具"""


def fmt_dt(dt):
    """格式化 datetime 为 YYYY-MM-DD HH:MM:SS（去掉微秒）"""
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def client_ip(request) -> str:
    """提取客户端 IP（优先 X-Forwarded-For）"""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""
