"""索引构建模块

负责 GraphRAG 索引的构建和发布
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pd
import yaml
from graphrag.api import build_index
from graphrag.callbacks.noop_workflow_callbacks import NoopWorkflowCallbacks
from graphrag.config.enums import IndexingMethod
from graphrag.config.load_config import load_config
from graphrag.index.validate_config import validate_config_names

from .env_utils import build_env_overrides, isolated_graphrag_env
from .graphrag_config import ensure_graphrag_project, persist_vector_size
from .paths import AppPaths
from .preprocess import load_normalized_manifest, normalize_documents
from .schemas import RebuildIndexResponse, IndexStatusResponse
from .settings import Settings


logger = logging.getLogger(__name__)

STATUS_FILE = "status.yaml"
ProgressCallback = Callable[[str, str], None]


class IndexBuildError(Exception):
    """索引构建失败异常"""
    pass


def _notify(progress_callback: ProgressCallback | None, stage: str, message: str) -> None:
    """通知进度回调

    Args:
        progress_callback: 进度回调函数
        stage: 当前阶段
        message: 进度消息
    """
    if progress_callback is not None:
        progress_callback(stage, message)


def run_graphrag_index(settings: Settings) -> None:
    """运行 GraphRAG 索引构建

    Args:
        settings: 应用配置

    Raises:
        IndexBuildError: 索引构建失败时抛出
    """
    with isolated_graphrag_env(build_env_overrides(settings)):
        try:
            config = load_config(root_dir=settings.paths.graphrag_project_dir)
            validate_config_names(config)
        except Exception as e:
            logger.exception("Failed to load or validate GraphRAG config")
            raise IndexBuildError("GraphRAG configuration error") from e

        try:
            persist_vector_size(settings.paths, config.vector_store.vector_size)
        except Exception as e:
            logger.warning(f"Failed to persist vector size: {e}")

        try:
            outputs = asyncio.run(
                build_index(
                    config=config,
                    method=IndexingMethod.Standard,
                    is_update_run=False,
                    callbacks=[NoopWorkflowCallbacks()],
                    verbose=False,
                )
            )
        except Exception as e:
            logger.exception("GraphRAG index build failed")
            raise IndexBuildError("Failed to build GraphRAG index") from e

    if any(output.error is not None for output in outputs):
        errors = [str(output.error) for output in outputs if output.error is not None]
        error_msg = "GraphRAG indexing failed: " + "; ".join(errors)
        logger.error(error_msg)
        raise IndexBuildError(error_msg)


def sync_normalized_to_graphrag_input(paths: AppPaths) -> None:
    """同步归一化文档到 GraphRAG 输入目录

    Args:
        paths: 应用路径配置
    """
    input_dir = paths.graphrag_project_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for child in list(input_dir.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
            continue
        child.unlink()

    for source in sorted(paths.normalized_dir.glob("*.md"), key=lambda item: item.name.lower()):
        if source.is_file():
            shutil.copy2(source, input_dir / source.name)


def _publish_index(paths: AppPaths, document_count: int) -> None:
    """发布索引到生产目录

    Args:
        paths: 应用路径配置
        document_count: 文档数量
    """
    output_dir = paths.graphrag_project_dir / "output"
    if not output_dir.exists():
        raise IndexBuildError(f"GraphRAG output directory not found: {output_dir}")

    publish_dir = paths.workspace_dir / "index_next"
    backup_dir = paths.workspace_dir / "index_previous"
    if publish_dir.exists():
        shutil.rmtree(publish_dir)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    shutil.copytree(output_dir, publish_dir)
    status_path = publish_dir / STATUS_FILE
    status_path.write_text(
        yaml.safe_dump(
            {
                "document_count": document_count,
                "last_indexed_at": datetime.now().isoformat(),
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    try:
        if paths.index_dir.exists():
            paths.index_dir.replace(backup_dir)
        publish_dir.replace(paths.index_dir)
    except Exception:
        if backup_dir.exists() and not paths.index_dir.exists():
            backup_dir.replace(paths.index_dir)
        raise
    finally:
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        if publish_dir.exists():
            shutil.rmtree(publish_dir)


def rebuild_index(settings: Settings, progress_callback: ProgressCallback | None = None) -> RebuildIndexResponse:
    """重建 GraphRAG 索引

    Args:
        settings: 应用配置
        progress_callback: 进度回调函数

    Returns:
        索引重建响应

    Raises:
        IndexBuildError: 索引构建失败时抛出
    """
    paths = settings.paths
    try:
        _notify(progress_callback, "preparing", "正在准备索引目录")
        paths.input_dir.mkdir(parents=True, exist_ok=True)
        paths.workspace_dir.mkdir(parents=True, exist_ok=True)

        _notify(progress_callback, "project", "正在检查 GraphRAG 项目配置")
        ensure_graphrag_project(paths, settings)

        _notify(progress_callback, "normalizing", "正在解析并归一化知识文档")
        normalized = normalize_documents(paths.input_dir, paths.normalized_dir)

        if not normalized:
            logger.warning("No documents to index")
            return RebuildIndexResponse(success=False, document_count=0, error="No documents found in input directory")

        _notify(progress_callback, "syncing", "正在同步归一化文档到 GraphRAG 输入目录")
        sync_normalized_to_graphrag_input(paths)

        _notify(progress_callback, "building", "正在构建 GraphRAG 图谱与向量索引")
        run_graphrag_index(settings)

        _notify(progress_callback, "publishing", "正在发布最新索引产物")
        _publish_index(paths, len(normalized))

        _notify(progress_callback, "completed", "索引构建完成")
        return RebuildIndexResponse(success=True, document_count=len(normalized))

    except IndexBuildError:
        # 已经是 IndexBuildError，直接重新抛出
        _notify(progress_callback, "failed", "索引构建失败")
        raise
    except Exception as e:
        # 其他异常，包装为 IndexBuildError
        logger.error(f"Unexpected error during index rebuild: {e}")
        _notify(progress_callback, "failed", f"索引构建失败: {e}")
        raise IndexBuildError(f"Failed to rebuild index: {e}") from e


def load_indexed_document_names(paths: AppPaths) -> set[str]:
    """加载已索引的文档名称

    Args:
        paths: 应用路径配置

    Returns:
        已索引的文档名称集合
    """
    documents_path = paths.index_dir / "documents.parquet"
    if not documents_path.exists():
        return set()
    df = pd.read_parquet(documents_path)
    titles = df.get("title")
    if titles is None:
        return set()
    manifest = load_normalized_manifest(paths.normalized_dir)
    indexed_names: set[str] = set()
    for title in titles.tolist():
        if title is None or pd.isna(title):
            continue
        raw_title = str(title)
        indexed_names.add(manifest.get(raw_title, raw_title))
    return indexed_names


def get_index_status(paths: AppPaths) -> IndexStatusResponse:
    """获取索引状态

    Args:
        paths: 应用路径配置

    Returns:
        索引状态响应
    """
    status_path = paths.index_dir / STATUS_FILE
    if not status_path.exists():
        return IndexStatusResponse(ready=False, document_count=0, last_indexed_at=None)

    data = yaml.safe_load(status_path.read_text(encoding="utf-8")) or {}
    return IndexStatusResponse(
        ready=(paths.index_dir / "text_units.parquet").exists(),
        document_count=int(data.get("document_count", 0)),
        last_indexed_at=data.get("last_indexed_at"),
    )


def load_last_indexed_at(paths: AppPaths) -> datetime | None:
    """加载最后索引时间

    Args:
        paths: 应用路径配置

    Returns:
        最后索引时间，如果不存在则返回 None
    """
    status = get_index_status(paths)
    if not status.last_indexed_at:
        return None
    try:
        return datetime.fromisoformat(status.last_indexed_at)
    except ValueError:
        return None
