# -*- coding: utf-8 -*-
"""
===================================
FastAPI 应用工厂模块
===================================

职责：
1. 创建和配置 FastAPI 应用实例
2. 配置 CORS 中间件
3. 注册路由和异常处理器

使用方式：
    from api.app import create_app
    app = create_app()
"""

import mimetypes
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from api.v1 import api_v1_router
from api.middlewares.auth import add_auth_middleware
from api.middlewares.error_handler import add_error_handlers
from api.v1.schemas.common import HealthResponse
from src.services.system_config_service import SystemConfigService


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Initialize and release shared services for the app lifecycle."""
    app.state.system_config_service = SystemConfigService()
    try:
        yield
    finally:
        if hasattr(app.state, "system_config_service"):
            delattr(app.state, "system_config_service")


def create_app(static_dir: Optional[Path] = None) -> FastAPI:
    """
    创建并配置 FastAPI 应用实例

    Args:
        static_dir: 静态文件目录路径（可选，默认为项目根目录下的 static）

    Returns:
        配置完成的 FastAPI 应用实例
    """
    if static_dir is None:
        static_dir = Path(__file__).parent.parent / "static"

    app = FastAPI(
        title="AI News Digest API",
        description=(
            "AI News Digest Service API\n\n"
            "## 功能模块\n"
            "- 系统配置：管理运行时设置\n"
            "- 认证：保护敏感操作\n\n"
            "## 认证方式\n"
            "支持可选的运行时认证"
        ),
        version="2.0.0",
        lifespan=app_lifespan,
    )

    # CORS 配置
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    extra_origins = os.environ.get("CORS_ORIGINS", "")
    if extra_origins:
        allowed_origins.extend([o.strip() for o in extra_origins.split(",") if o.strip()])

    allow_all_origins = os.environ.get("CORS_ALLOW_ALL", "").lower() == "true"
    allow_credentials = not allow_all_origins
    if allow_all_origins:
        allowed_origins = ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    add_auth_middleware(app)

    # 注册路由
    app.include_router(api_v1_router)
    add_error_handlers(app)

    # 根路由
    has_frontend = static_dir.exists() and (static_dir / "index.html").exists()

    if not has_frontend:
        _NO_FRONTEND_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI News Digest API</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{min-height:100vh;display:flex;align-items:center;justify-content:center;
       background:#0a0e17;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,monospace}
  .card{max-width:580px;padding:2.5rem;border:1px solid #1e293b;border-radius:12px;background:#111827}
  h1{font-size:1.25rem;color:#38bdf8;margin-bottom:.75rem}
  p{font-size:.9rem;line-height:1.7;color:#94a3b8}
  a{color:#38bdf8;text-decoration:none}
  a:hover{text-decoration:underline}
  .status{margin-top:1rem;font-size:.8rem;color:#475569}
</style></head><body><div class="card">
<h1>AI News Digest API</h1>
<p>The API is running. Visit <a href="/docs">/docs</a> for interactive API documentation.</p>
<p class="status">API Version 2.0.0 &bull; <a href="/api/health">/api/health</a></p>
</div></body></html>"""

        @app.get("/", include_in_schema=False)
        async def root():
            return HTMLResponse(content=_NO_FRONTEND_HTML)

    @app.get(
        "/api/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="健康检查",
        description="用于负载均衡器或监控系统检查服务状态"
    )
    async def health_check() -> HealthResponse:
        """健康检查接口"""
        return HealthResponse(
            status="ok",
            timestamp=datetime.now().isoformat()
        )

    if has_frontend:
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(request: Request, full_path: str):
            if full_path == "api" or full_path.startswith("api/"):
                return JSONResponse(
                    status_code=404,
                    content={"error": "not_found", "message": f"API endpoint /{full_path} not found"}
                )

            file_path = static_dir / full_path
            if file_path.exists() and file_path.is_file():
                content_type, _ = mimetypes.guess_type(str(file_path))
                return FileResponse(file_path, media_type=content_type)

            return FileResponse(static_dir / "index.html")

    return app


# 默认应用实例（供 uvicorn 直接使用）
app = create_app()
