# AGENTS.md

## 修改后端后必须重启

后端改动（`backend/` 下任何 Python 文件）默认不会热加载，**必须重启 uvicorn 才生效**。改完后执行：

```bash
ps aux | grep uvicorn | grep -v grep | awk '{print $2}' | xargs -r kill
cd backend && nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > logs/uvicorn.log 2>&1 &
```

## 前端改动后需重新构建

前端改动（`frontend/src/`）需重新构建后部署：

```bash
export PATH="/opt/homebrew/bin:$PATH"; cd frontend && npm run build
```
