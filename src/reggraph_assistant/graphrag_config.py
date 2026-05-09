"""GraphRAG 配置管理模块

负责 GraphRAG 项目初始化和配置管理
"""
from __future__ import annotations

import yaml

from .paths import AppPaths
from .settings import Settings


COMMUNITY_REPORT_PROMPT_SUFFIX = "\n\nOutput a single raw JSON object only. Do not wrap the JSON in markdown code fences. Do not add any prose before or after the JSON."


def _ensure_prompt_constraints(paths: AppPaths) -> None:
    """确保 prompt 包含必要的约束

    Args:
        paths: 应用路径配置
    """
    prompt_path = paths.graphrag_project_dir / "prompts" / "community_report_graph.txt"
    if not prompt_path.exists():
        return
    prompt_text = prompt_path.read_text(encoding="utf-8")
    if COMMUNITY_REPORT_PROMPT_SUFFIX in prompt_text:
        return
    prompt_path.write_text(prompt_text.rstrip() + COMMUNITY_REPORT_PROMPT_SUFFIX + "\n", encoding="utf-8")


def ensure_graphrag_project(paths: AppPaths, settings: Settings) -> None:
    """确保 GraphRAG 项目已初始化并配置正确

    Args:
        paths: 应用路径配置
        settings: 应用配置
    """
    from graphrag.cli.initialize import initialize_project_at

    settings_path = paths.graphrag_project_dir / "settings.yaml"
    if not settings_path.exists():
        initialize_project_at(
            path=paths.graphrag_project_dir,
            force=True,
            model=settings.llm.model,
            embedding_model=settings.embedding.model,
        )

    config = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    completion_model = config["completion_models"]["default_completion_model"]
    embedding_model = config["embedding_models"]["default_embedding_model"]
    completion_model["api_base"] = "${GRAPHRAG_API_BASE}"
    embedding_model["model_provider"] = "hosted_vllm"
    embedding_model["api_base"] = "${GRAPHRAG_API_BASE_EMBEDDING}"
    embedding_model["api_key"] = "${GRAPHRAG_API_KEY_EMBEDDING}"
    config["input"]["file_pattern"] = r".*\.(md)$$"
    settings_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    env_path = paths.graphrag_project_dir / ".env"
    if env_path.exists():
        env_path.unlink()

    _ensure_prompt_constraints(paths)


def persist_vector_size(paths: AppPaths, vector_size: int) -> None:
    """持久化向量维度配置

    Args:
        paths: 应用路径配置
        vector_size: 向量维度
    """
    settings_path = paths.graphrag_project_dir / "settings.yaml"
    if not settings_path.exists():
        return

    config = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    vector_store = config.get("vector_store")
    if not isinstance(vector_store, dict):
        return

    vector_store["vector_size"] = vector_size
    index_schema = vector_store.get("index_schema")
    if isinstance(index_schema, dict):
        for schema in index_schema.values():
            if isinstance(schema, dict):
                schema["vector_size"] = vector_size

    settings_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
