from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


SUPPORTED_INPUT_EXTENSIONS = (".txt", ".md", ".pdf")
NORMALIZED_PREFIX = "__normalized__"
NORMALIZED_SUFFIX = ".md"
NORMALIZED_MANIFEST = "normalized_manifest.json"


class AppPaths(BaseModel):
    """应用路径配置"""

    root: Path = Field(description="应用根目录")
    input_dir: Path = Field(description="输入文档目录")
    workspace_dir: Path = Field(description="工作空间目录")
    normalized_dir: Path = Field(description="标准化文档目录")
    graphrag_project_dir: Path = Field(description="GraphRAG 项目目录")
    index_dir: Path = Field(description="索引目录")
    app_state_db: Path = Field(description="应用状态数据库路径")

    model_config = {"frozen": True}


def resolve_paths(root: Path | None = None) -> AppPaths:
    """解析应用路径配置

    Args:
        root: 应用根目录，默认为当前工作目录

    Returns:
        AppPaths 配置对象

    Raises:
        ValueError: 当根目录不存在或不是目录时
    """
    resolved_root = (root or Path.cwd()).resolve()

    # 安全检查：确保路径存在且是目录
    if not resolved_root.exists():
        raise ValueError(f"Root directory does not exist: {resolved_root}")
    if not resolved_root.is_dir():
        raise ValueError(f"Root path is not a directory: {resolved_root}")

    workspace_dir = resolved_root / "workspace"
    return AppPaths(
        root=resolved_root,
        input_dir=resolved_root / "input",
        workspace_dir=workspace_dir,
        normalized_dir=workspace_dir / "normalized",
        graphrag_project_dir=workspace_dir / "graphrag_project",
        index_dir=workspace_dir / "index",
        app_state_db=workspace_dir / "app_state.sqlite3",
    )
