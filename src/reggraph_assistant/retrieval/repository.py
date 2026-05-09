"""索引仓库 - 统一数据加载和文档映射"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ..settings import Settings


@dataclass(frozen=True)
class TextUnitRecord:
    """文本单元记录"""
    source_id: str
    human_readable_id: str
    document_name: str
    text: str


class IndexRepository:
    """索引仓库 - 统一管理索引数据加载和文档映射

    职责：
    1. 加载 documents.parquet 和 text_units.parquet
    2. 构建文档名称映射（source_id -> document_name）
    3. 提供文本单元列表（供 BM25 和 Vector 使用）
    4. 缓存加载结果，避免重复 I/O
    """

    def __init__(self, index_dir: Path, normalized_dir: Path | None = None) -> None:
        self._index_dir = index_dir
        self._normalized_dir = normalized_dir or index_dir.parent / "normalized"

        # 缓存
        self._document_lookup: dict[str, str] | None = None
        self._text_units: list[TextUnitRecord] | None = None
        self._documents_frame: pd.DataFrame | None = None
        self._text_units_frame: pd.DataFrame | None = None

    def document_lookup(self) -> dict[str, str]:
        """获取文档名称映射（source_id -> document_name）"""
        if self._document_lookup is not None:
            return self._document_lookup

        documents = self._load_documents_frame()
        text_units = self._load_text_units_frame()
        if documents is None or text_units is None:
            self._document_lookup = {}
            return self._document_lookup

        # 加载规范化清单
        from ..preprocess import load_normalized_manifest
        manifest = load_normalized_manifest(self._normalized_dir)

        # 构建文档标题映射
        document_titles: dict[str, str] = {}
        for record in documents.to_dict('records'):
            title = record.get("title")
            raw_title = str(record["id"]) if title is None or pd.isna(title) else str(title)
            display_title = manifest.get(raw_title, raw_title)
            document_titles[str(record["id"])] = display_title
            document_titles[str(record.get("human_readable_id", ""))] = display_title

        # 构建 text_unit -> document 映射
        lookup: dict[str, str] = {}
        for record in text_units.to_dict('records'):
            document_id = str(record.get("document_id") or "")
            document_name = document_titles.get(
                document_id,
                document_titles.get(document_id.removeprefix("D"), "未知来源")
            )
            lookup[str(record["id"])] = document_name
            lookup[str(record.get("human_readable_id", ""))] = document_name

        self._document_lookup = lookup
        return lookup

    def text_units(self) -> list[TextUnitRecord]:
        """获取所有文本单元列表"""
        if self._text_units is not None:
            return self._text_units

        text_units = self._load_text_units_frame()
        if text_units is None or text_units.empty:
            self._text_units = []
            return self._text_units

        lookup = self.document_lookup()
        records: list[TextUnitRecord] = []

        for record in text_units.to_dict('records'):
            text = str(record.get("text") or "").strip()
            if not text:
                continue

            source_id = str(record.get("id") or "")
            records.append(
                TextUnitRecord(
                    source_id=source_id,
                    human_readable_id=str(record.get("human_readable_id", "")),
                    document_name=lookup.get(
                        source_id,
                        lookup.get(source_id.removeprefix("T"), "未知来源")
                    ),
                    text=text,
                )
            )

        self._text_units = records
        return records

    def _load_documents_frame(self) -> pd.DataFrame | None:
        """加载 documents.parquet"""
        if self._documents_frame is not None:
            return self._documents_frame

        documents_path = self._index_dir / "documents.parquet"
        if not documents_path.exists():
            return None

        self._documents_frame = pd.read_parquet(documents_path)
        return self._documents_frame

    def _load_text_units_frame(self) -> pd.DataFrame | None:
        """加载 text_units.parquet"""
        if self._text_units_frame is not None:
            return self._text_units_frame

        text_units_path = self._index_dir / "text_units.parquet"
        if not text_units_path.exists():
            return None

        self._text_units_frame = pd.read_parquet(text_units_path)
        return self._text_units_frame


def load_index_repository(settings: Settings) -> IndexRepository:
    """加载索引仓库（工厂函数）"""
    return IndexRepository(
        index_dir=settings.paths.index_dir,
        normalized_dir=settings.paths.root / "normalized",
    )
