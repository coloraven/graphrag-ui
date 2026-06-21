from __future__ import annotations

import os
from typing import Literal, cast

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .error_handlers import register_error_handlers
from .evaluation import run_evaluation
from .indexing import get_index_status, list_documents, rebuild_index
from .index_tasks import INDEX_TASK_MANAGER
from .logging_config import setup_logging
from .persistence import get_app_state_store
from .schemas import (
    HealthComponent,
    HealthResponse,
    IndexStatusResponse,
    WorkflowRequest,
    WorkflowResponse,
    EvalReport,
)
from .settings import Settings, load_settings
from .workflow import run_workflow


# ============ 健康检查逻辑 ============

def get_health_status(settings: Settings) -> HealthResponse:
    """获取系统健康状态"""
    index_status = get_index_status(settings.paths)

    components = [
        HealthComponent(
            name="index",
            status="pass" if index_status.ready else "warn",
            detail=(
                f"索引已就绪，文档数 {index_status.document_count}"
                if index_status.ready
                else "索引尚未建立或产物不完整"
            ),
        ),
    ]

    overall_status = "ok" if index_status.ready else "warn"

    return HealthResponse(
        status=cast(Literal["ok", "warn", "fail"], overall_status),
        document_count=index_status.document_count,
        index_ready=index_status.ready,
        last_indexed_at=index_status.last_indexed_at,
        active_task_state="idle",
        components=components,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    """创建 FastAPI 应用 - 简化版，直接调用核心函数"""
    app_settings = settings or load_settings()

    # 配置日志
    setup_logging(
        level=app_settings.log_level,
        log_file=app_settings.paths.root / "logs" / "app.log" if hasattr(app_settings.paths, "root") else None,
    )

    # 初始化持久化
    state_store = get_app_state_store(app_settings.paths)
    INDEX_TASK_MANAGER.configure(app_settings.paths)

    app = FastAPI(
        title="RegFlow Precheck Assistant",
        description="GraphRAG-powered registration precheck assistant for enterprise registration and business-scope knowledge bases",
    )

    cors_origins = [
        origin.strip()
        for origin in os.environ.get(
            "CORS_ALLOW_ORIGINS",
            "http://localhost:8012,http://127.0.0.1:8012",
        ).split(",")
        if origin.strip()
    ]

    # 添加 CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册全局错误处理器
    register_error_handlers(app)

    # ============ 健康检查路由 ============
    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return get_health_status(app_settings)

    @app.get("/api/health/index", response_model=IndexStatusResponse)
    async def index_status() -> IndexStatusResponse:
        return get_index_status(app_settings.paths)

    @app.get("/api/index/status", response_model=IndexStatusResponse)
    async def index_status_alias() -> IndexStatusResponse:
        """索引状态（前端兼容端点）"""
        return get_index_status(app_settings.paths)
        return get_index_status(app_settings)

    # ============ 核心工作流路由 ============
    @app.post("/api/workflow/run", response_model=WorkflowResponse)
    async def workflow_run(request: WorkflowRequest) -> WorkflowResponse:
        """统一工作流入口 - 所有功能通过此接口"""
        if request.submitted_materials:
            for idx, material in enumerate(request.submitted_materials):
                if len(material) > 500:
                    raise HTTPException(
                        status_code=400,
                        detail=f"材料项 {idx + 1} 长度超过 500 字符"
                    )

        response = await run_workflow(
            request.task,
            app_settings,
            request.context,
            request.submitted_materials,
        )

        # 记录交互历史
        try:
            state_store.log_interaction(
                kind="workflow",
                prompt=request.task,
                context=request.context,
                intent=response.intent,
                answer=response.answer,
                source_count=len(response.sources),
                citation_coverage=response.citation_audit.citation_coverage,
                status=response.citation_audit.status,
            )
        except Exception:
            pass  # 日志失败不影响业务

        return response

    # ============ 评测路由 ============
    @app.post("/api/eval/run", response_model=EvalReport)
    async def eval_run() -> EvalReport:
        return await run_evaluation(app_settings, run_workflow)

    # ============ 索引管理路由 ============
    @app.post("/api/index/rebuild")
    async def index_rebuild():
        """重建索引"""
        return await rebuild_index(app_settings)

    @app.get("/api/index/task")
    async def current_index_task():
        """获取当前索引任务"""
        return INDEX_TASK_MANAGER.get_current_task()

    @app.get("/api/index/task/latest")
    async def latest_index_task():
        """获取最近的索引任务"""
        return INDEX_TASK_MANAGER.get_latest_task()

    @app.get("/api/index/task/{task_id}")
    async def get_index_task(task_id: str):
        """获取指定索引任务"""
        task = INDEX_TASK_MANAGER.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    # ============ 历史记录路由 ============
    @app.get("/api/history/index-tasks")
    async def index_task_history(limit: int = Query(default=8, ge=1, le=100)):
        """索引任务历史"""
        return INDEX_TASK_MANAGER.list_tasks(limit=limit)

    @app.get("/api/history/interactions")
    async def interaction_history(limit: int = Query(default=8, ge=1, le=100)):
        """交互历史"""
        return state_store.list_interactions(limit=limit)

    # ============ 文档管理路由 ============
    @app.get("/api/documents")
    async def documents():
        """文档列表"""
        return list_documents(app_settings)

    @app.post("/api/documents/upload")
    async def document_upload(
        request: Request,
        filename: str = Query(min_length=1, max_length=180)
    ):
        """文档上传"""
        from .indexing import save_uploaded_document_stream
        try:
            return await save_uploaded_document_stream(
                app_settings.paths.input_dir,
                filename,
                request.stream()
            )
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/documents/preview")
    async def document_preview(filename: str = Query(min_length=1, max_length=180)):
        """文档预览"""
        from .indexing import read_document_preview
        try:
            return read_document_preview(app_settings.paths.input_dir, filename)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    # ============ 前端静态文件 ============
    static_dir = app_settings.paths.root / "frontend" / "static"
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(static_dir)), name="assets")

        @app.get("/", include_in_schema=False)
        async def frontend_index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

    return app
