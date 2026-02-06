from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # <--- 新增
from api.routes import router
from api.oil_routes import router as oil_router
import os

def create_app():
    app = FastAPI(title="ABB Signal Analysis Platform")

    # 1. 允许跨域
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. 注册 API 路由
    app.include_router(router)
    app.include_router(oil_router, tags=["Oil Well"])
    
    # 3. 挂载静态文件 (前端网页)
    # 确保 static 目录存在，否则启动会报错
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
        
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app

app = create_app()