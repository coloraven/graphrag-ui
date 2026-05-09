"""文档管理模块

负责文档上传、扫描、预览等操作
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterable, Iterable
from datetime import datetime
from pathlib import Path

from .paths import AppPaths, SUPPORTED_INPUT_EXTENSIONS
from .preprocess import extract_pdf_text
from .schemas import DocumentItem, DocumentPreviewResponse, DocumentUploadResponse


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
PREVIEW_MAX_CHARS = 4000


def validate_document_name(name: str) -> str:
    """验证文档名称

    Args:
        name: 文档名称

    Returns:
        规范化的文档名称

    Raises:
        ValueError: 文档名称无效或类型不支持
    """
    raw_name = name.strip()
    normalized_name = raw_name.replace("\\", "/")
    path = Path(normalized_name)
    if not raw_name or normalized_name.startswith("/") or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Invalid document name")
    if path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        raise ValueError("Unsupported document type")
    return normalized_name


def build_document_item(path: Path) -> DocumentItem:
    """构建文档项

    Args:
        path: 文档路径

    Returns:
        DocumentItem 对象
    """
    stat = path.stat()
    return DocumentItem(
        name=path.name,
        type=path.suffix.lower().lstrip('.'),
        size=stat.st_size,
        updated_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        indexed=False,
        stale=False,
    )


def scan_input_documents(
    input_dir: Path,
    indexed_names: set[str] | None = None,
    last_indexed_at: datetime | None = None,
) -> list[DocumentItem]:
    """扫描输入目录中的文档

    Args:
        input_dir: 输入目录
        indexed_names: 已索引的文档名称集合
        last_indexed_at: 最后索引时间

    Returns:
        文档项列表
    """
    if not input_dir.exists():
        return []

    known_indexed_names = indexed_names or set()
    items: list[DocumentItem] = []
    for path in sorted(input_dir.rglob("*"), key=lambda item: str(item.relative_to(input_dir)).lower()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
            continue
        item = build_document_item(path)
        item.name = path.relative_to(input_dir).as_posix()
        item.indexed = item.name in known_indexed_names
        item.stale = item.indexed and last_indexed_at is not None and datetime.fromtimestamp(path.stat().st_mtime) > last_indexed_at
        items.append(item)
    return items


def save_uploaded_document(input_dir: Path, filename: str, content: bytes) -> DocumentUploadResponse:
    """保存上传的文档（同步版本）

    Args:
        input_dir: 输入目录
        filename: 文件名
        content: 文件内容

    Returns:
        上传响应
    """
    return _save_uploaded_document_chunks(input_dir, filename, [content])


async def save_uploaded_document_stream(
    input_dir: Path,
    filename: str,
    chunks: AsyncIterable[bytes],
) -> DocumentUploadResponse:
    """保存上传的文档（流式版本）

    Args:
        input_dir: 输入目录
        filename: 文件名
        chunks: 文件内容流

    Returns:
        上传响应
    """
    document_name, target, temp_path, temp_fd = _prepare_upload_paths(input_dir, filename)

    total_size = 0
    try:
        with os.fdopen(temp_fd, "wb") as output_file:
            async for chunk in chunks:
                if not chunk:
                    continue
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise ValueError("Document is too large")
                output_file.write(chunk)
        if total_size == 0:
            raise ValueError("Document content is empty")
        _publish_uploaded_document(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return _build_upload_response(target, document_name)


def _save_uploaded_document_chunks(input_dir: Path, filename: str, chunks: Iterable[bytes]) -> DocumentUploadResponse:
    """保存上传的文档（分块版本）"""
    document_name, target, temp_path, temp_fd = _prepare_upload_paths(input_dir, filename)

    total_size = 0
    try:
        with os.fdopen(temp_fd, "wb") as output_file:
            for chunk in chunks:
                if not chunk:
                    continue
                total_size += len(chunk)
                if total_size > MAX_UPLOAD_BYTES:
                    raise ValueError("Document is too large")
                output_file.write(chunk)
        if total_size == 0:
            raise ValueError("Document content is empty")
        _publish_uploaded_document(temp_path, target)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return _build_upload_response(target, document_name)


def _prepare_upload_paths(input_dir: Path, filename: str) -> tuple[str, Path, Path, int]:
    """准备上传路径"""
    document_name = validate_document_name(filename)
    input_dir.mkdir(parents=True, exist_ok=True)
    target = input_dir / document_name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("Document already exists")
    temp_fd, temp_name = tempfile.mkstemp(
        prefix=f'.{target.name}.',
        suffix='.uploading',
        dir=target.parent,
    )
    return document_name, target, Path(temp_name), temp_fd


def _publish_uploaded_document(temp_path: Path, target: Path) -> None:
    """发布上传的文档"""
    try:
        os.link(temp_path, target)
    except FileExistsError as exc:
        raise FileExistsError("Document already exists") from exc
    finally:
        temp_path.unlink(missing_ok=True)


def _build_upload_response(target: Path, document_name: str) -> DocumentUploadResponse:
    """构建上传响应"""
    item = build_document_item(target)
    item.name = document_name
    return DocumentUploadResponse(
        item=item,
        message="Document uploaded. Rebuild the index before querying it.",
    )


def read_document_preview(input_dir: Path, filename: str, max_chars: int = PREVIEW_MAX_CHARS) -> DocumentPreviewResponse:
    """读取文档预览

    Args:
        input_dir: 输入目录
        filename: 文件名
        max_chars: 最大字符数

    Returns:
        文档预览响应
    """
    document_name = validate_document_name(filename)
    path = input_dir / document_name
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("Document not found")

    if path.suffix.lower() == ".pdf":
        content = extract_pdf_text(path)
    else:
        content = path.read_text(encoding="utf-8")

    normalized_content = content.strip()
    return DocumentPreviewResponse(
        name=document_name,
        type=path.suffix.lower().lstrip('.'),
        size=path.stat().st_size,
        content=normalized_content[:max_chars],
        character_count=len(normalized_content),
        truncated=len(normalized_content) > max_chars,
    )
