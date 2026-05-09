"""索引管理模块（对外接口）

提供统一的索引管理接口，协调文档管理、索引构建等子模块
"""
from __future__ import annotations

from .document_manager import (
    read_document_preview,
    save_uploaded_document,
    save_uploaded_document_stream,
    scan_input_documents,
)
from .index_builder import (
    STATUS_FILE,
    IndexBuildError,
    get_index_status,
    load_indexed_document_names,
    load_last_indexed_at,
    rebuild_index,
    run_graphrag_index,
)
from .paths import AppPaths
from .schemas import DocumentItem


def list_documents(paths: AppPaths) -> list[DocumentItem]:
    """列出所有文档

    Args:
        paths: 应用路径配置

    Returns:
        文档列表
    """
    indexed_names = load_indexed_document_names(paths)
    return scan_input_documents(
        paths.input_dir,
        indexed_names=indexed_names,
        last_indexed_at=load_last_indexed_at(paths),
    )


# 导出所有公共接口
__all__ = [
    # 文档管理
    "read_document_preview",
    "save_uploaded_document",
    "save_uploaded_document_stream",
    "scan_input_documents",
    "list_documents",
    # 索引构建
    "STATUS_FILE",
    "IndexBuildError",
    "get_index_status",
    "load_indexed_document_names",
    "load_last_indexed_at",
    "rebuild_index",
    "run_graphrag_index",
]
