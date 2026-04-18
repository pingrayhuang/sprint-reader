"""
PythonAnywhere WSGI entry point.

在 PythonAnywhere Web tab → WSGI configuration file 填入本檔的完整路徑：
    /home/<username>/sprint-reader/pythonanywhere_wsgi.py

Source code 目錄：
    /home/<username>/sprint-reader

Working directory（讓 DB 路徑能正確解析）：
    /home/<username>/sprint-reader
"""
import sys
import os

# 把專案根目錄加入 Python path，讓 `from app.main import app` 能找到
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 先初始化 DB（PythonAnywhere 不走 uvicorn startup event）
from app.db import init_migrations
init_migrations()

# 把 FastAPI ASGI app 包成 WSGI
from a2wsgi import ASGIMiddleware
from app.main import app as fastapi_app

application = ASGIMiddleware(fastapi_app)
