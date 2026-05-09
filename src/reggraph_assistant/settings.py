"""配置模块 - 重构版

使用嵌套 Pydantic 模型组织配置，提高可读性和可维护性
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, model_validator

from .paths import AppPaths, resolve_paths


load_dotenv()

# 配置常量
DEFAULT_PORT = 8012
MIN_PORT = 1024
MAX_PORT = 65535
DEFAULT_LLM_MODEL = "deepseek-chat"
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"
DEFAULT_API_BASE = "https://api.deepseek.com/v1"
DEFAULT_EMBEDDING_API_BASE = "https://api.siliconflow.cn/v1"


class LLMConfig(BaseModel):
    """LLM 配置"""
    api_base: str = Field(
        default=DEFAULT_API_BASE,
        description="LLM API 基础 URL",
    )
    api_key: str = Field(
        min_length=1,
        description="LLM API 密钥（必填）",
    )
    model: str = Field(
        default=DEFAULT_LLM_MODEL,
        min_length=1,
        description="LLM 模型名称",
    )

    @field_validator("api_base")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证 URL 格式"""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL 必须以 http:// 或 https:// 开头: {v}")
        return v.rstrip("/")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """验证 API 密钥格式"""
        if v.startswith("__FILL_") or v == "":
            raise ValueError("API 密钥未配置，请在 .env 文件中设置有效的 API 密钥")
        return v


class EmbeddingConfig(BaseModel):
    """Embedding 配置"""
    api_base: str = Field(
        default=DEFAULT_EMBEDDING_API_BASE,
        description="Embedding API 基础 URL",
    )
    api_key: str = Field(
        min_length=1,
        description="Embedding API 密钥（必填）",
    )
    model: str = Field(
        default=DEFAULT_EMBEDDING_MODEL,
        min_length=1,
        description="Embedding 模型名称",
    )
    max_length: int = Field(
        default=512,
        ge=1,
        le=8192,
        description="文本最大长度（字符数）",
    )
    batch_size: int = Field(
        default=32,
        ge=1,
        le=100,
        description="批量调用大小",
    )

    @field_validator("api_base")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证 URL 格式"""
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"URL 必须以 http:// 或 https:// 开头: {v}")
        return v.rstrip("/")

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """验证 API 密钥格式"""
        if v.startswith("__FILL_") or v == "":
            raise ValueError("API 密钥未配置，请在 .env 文件中设置有效的 API 密钥")
        return v


class RetrievalConfig(BaseModel):
    """检索配置"""
    graphrag_limit: int = Field(default=5, ge=1, le=20, description="GraphRAG 检索结果数量")
    bm25_limit: int = Field(default=5, ge=1, le=20, description="BM25 检索结果数量")
    vector_limit: int = Field(default=5, ge=1, le=20, description="向量检索结果数量")
    fusion_limit: int = Field(default=7, ge=1, le=30, description="融合后结果数量")
    timeout: float = Field(default=30.0, ge=5.0, le=120.0, description="检索超时时间（秒）")


class IntentConfig(BaseModel):
    """意图识别配置"""
    policy_hints: list[str] = Field(
        default=["咨询", "答复", "口径", "解释"],
        description="政策答复意图识别关键词",
    )
    checklist_hints: list[str] = Field(
        default=["办理", "材料", "清单", "准备", "许可", "登记"],
        description="材料清单意图识别关键词",
    )


class QualityConfig(BaseModel):
    """质量评估配置"""
    reviewer_weights: dict[str, float] = Field(
        default={
            "coverage": 0.4,
            "length": 0.2,
            "facts": 0.2,
            "risks": 0.2,
        },
        description="Reviewer 质量评分权重",
    )
    critic_weights: dict[str, float] = Field(
        default={
            "relevance": 0.25,
            "completeness": 0.25,
            "accuracy": 0.25,
            "citation": 0.15,
            "expression": 0.10,
        },
        description="Critic 质量评分权重",
    )
    min_citation_coverage: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="最小引用覆盖率阈值",
    )
    quality_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="质量分数阈值",
    )


class Settings(BaseModel):
    """应用配置

    使用嵌套配置模型组织配置项，提高可读性和可维护性
    """

    paths: AppPaths = Field(description="应用路径配置")
    llm: LLMConfig = Field(description="LLM 配置")
    embedding: EmbeddingConfig = Field(description="Embedding 配置")
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig, description="检索配置")
    intent: IntentConfig = Field(default_factory=IntentConfig, description="意图识别配置")
    quality: QualityConfig = Field(default_factory=QualityConfig, description="质量评估配置")
    port: int = Field(
        default=DEFAULT_PORT,
        ge=MIN_PORT,
        le=MAX_PORT,
        description=f"服务端口号（{MIN_PORT}-{MAX_PORT}）",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="日志级别",
    )

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def validate_paths_exist(self) -> Settings:
        """验证关键路径存在"""
        if not self.paths.root.exists():
            raise ValueError(f"根目录不存在: {self.paths.root}")
        return self



def load_settings(
    root_dir: Path | None = None,
    env: Literal["development", "production", "test"] | None = None,
) -> Settings:
    """加载应用配置

    Args:
        root_dir: 应用根目录，默认为当前工作目录
        env: 环境类型（development/production/test），用于加载对应的 .env 文件

    Returns:
        Settings: 验证后的配置对象

    Raises:
        ValueError: 配置验证失败时抛出，包含详细的错误信息
    """
    # 根据环境加载对应的 .env 文件
    if env:
        env_file = f".env.{env}"
        if Path(env_file).exists():
            load_dotenv(env_file, override=True)

    paths = resolve_paths(root_dir)
    api_key = os.environ.get("GRAPHRAG_API_KEY", "")
    embedding_api_key = os.environ.get("GRAPHRAG_API_KEY_EMBEDDING", api_key)

    try:
        return Settings(
            paths=paths,
            llm=LLMConfig(
                api_base=os.environ.get("API_BASE", DEFAULT_API_BASE),
                api_key=api_key,
                model=os.environ.get("GRAPHRAG_LLM_MODEL", DEFAULT_LLM_MODEL),
            ),
            embedding=EmbeddingConfig(
                api_base=os.environ.get("API_BASE_EMBEDDING", DEFAULT_EMBEDDING_API_BASE),
                api_key=embedding_api_key,
                model=os.environ.get("GRAPHRAG_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
                max_length=int(os.environ.get("EMBEDDING_MAX_LENGTH", "512")),
                batch_size=int(os.environ.get("EMBEDDING_BATCH_SIZE", "32")),
            ),
            port=int(os.environ.get("PORT", str(DEFAULT_PORT))),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),  # type: ignore
        )
    except ValueError as e:
        raise ValueError(
            f"配置加载失败: {e}\n"
            "请检查 .env 文件中的配置项是否正确设置。\n"
            "参考 .env.example 文件了解所需的配置项。"
        ) from e
