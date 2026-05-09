"""向量检索器 - 基于 FAISS 的语义相似度检索"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import numpy as np
import pandas as pd

from ..schemas import Citation
from .repository import IndexRepository

if TYPE_CHECKING:
    from ..settings import Settings

logger = logging.getLogger(__name__)


class VectorRetriever:
    """向量检索器 - 使用 Embedding API + FAISS 进行语义相似度检索"""

    def __init__(self, settings: Settings, index_repository: IndexRepository):
        self.settings = settings
        self.index_repository = index_repository
        self.api_base = settings.embedding.api_base
        self.api_key = settings.embedding.api_key
        self.model = settings.embedding.model
        self.cache_path = Path(settings.paths.index_dir) / "embeddings.parquet"
        self.index = None

    async def retrieve(self, query: str, limit: int = 5) -> list[Citation]:
        """执行向量检索

        Args:
            query: 查询文本
            limit: 返回结果数量

        Returns:
            按相似度排序的 Citation 列表
        """
        try:
            # 1. 确保向量索引已构建
            await self._ensure_index()

            text_units = self.index_repository.text_units()
            if self.index is None or len(text_units) == 0:
                logger.warning("Vector index is empty")
                return []

            # 2. 获取查询向量
            query_embeddings = await self._get_embeddings_batch([query])
            if not query_embeddings or len(query_embeddings) == 0:
                logger.warning("Failed to get query embedding")
                return []

            query_embedding = query_embeddings[0]

            # 3. 使用 FAISS 搜索最相似的文档
            query_vector = np.array([query_embedding], dtype=np.float32)
            distances, indices = self.index.search(query_vector, min(limit, len(text_units)))

            # 4. 构建结果
            results = []
            for idx, (distance, doc_idx) in enumerate(zip(distances[0], indices[0]), start=1):
                if doc_idx == -1:  # FAISS 返回 -1 表示无效结果
                    continue

                unit = text_units[doc_idx]
                similarity = float(1 - distance)  # 转换距离为相似度

                citation = Citation(
                    index=idx,
                    source_id=unit.source_id,
                    document_name=unit.document_name,
                    snippet=unit.text[:200] + "..." if len(unit.text) > 200 else unit.text,
                )

                results.append(citation)
                logger.debug(f"Vector match {idx}: {citation.document_name} (similarity: {similarity:.4f})")

            return results

        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            return []

    async def _ensure_index(self) -> None:
        """确保向量索引已构建"""
        text_units = self.index_repository.text_units()

        if not text_units:
            logger.warning("No text units found in index")
            return

        # 缓存元数据文件路径
        cache_meta_path = self.cache_path.with_suffix('.meta.json')

        # 检查缓存元数据是否存在且有效
        if self.cache_path.exists() and cache_meta_path.exists():
            try:
                # 读取元数据
                with open(cache_meta_path, 'r', encoding='utf-8') as f:
                    cache_meta = json.load(f)

                # 快速验证：比对文档数量和版本
                current_count = len(text_units)
                cached_count = cache_meta.get("document_count", 0)

                if cached_count == current_count:
                    # 数量匹配，加载缓存
                    logger.info(f"Loading cached embeddings from {self.cache_path} (meta: {cache_meta})")
                    df = pd.read_parquet(self.cache_path)
                    embeddings = np.vstack(df["embedding"].tolist()).astype(np.float32)
                    self._build_faiss_index(embeddings)
                    return
                else:
                    logger.info(f"Cache outdated: cached={cached_count}, current={current_count}, rebuilding")
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")

        # 重新构建向量索引
        await self._rebuild_index()

    async def _rebuild_index(self) -> None:
        """重新构建向量索引"""
        text_units = self.index_repository.text_units()
        logger.info(f"Building vector index for {len(text_units)} documents")

        # 批量获取文档向量（使用配置的最大长度）
        texts = [unit.text[:self.settings.embedding.max_length] for unit in text_units]
        embeddings = await self._get_embeddings_batch(texts, batch_size=self.settings.embedding.batch_size)

        if not embeddings or len(embeddings) != len(texts):
            logger.error("Failed to get embeddings for all documents")
            return

        # 保存到缓存
        df = pd.DataFrame({
            "source_id": [unit.source_id for unit in text_units],
            "document_name": [unit.document_name for unit in text_units],
            "embedding": embeddings,
        })
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self.cache_path)
        logger.info(f"Saved embeddings cache to {self.cache_path}")

        # 保存缓存元数据
        cache_meta = {
            "version": "v1",
            "document_count": len(text_units),
            "last_updated": datetime.now().isoformat(),
            "embedding_model": self.model,
        }
        cache_meta_path = self.cache_path.with_suffix('.meta.json')
        with open(cache_meta_path, 'w', encoding='utf-8') as f:
            json.dump(cache_meta, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved cache metadata to {cache_meta_path}")

        # 构建 FAISS 索引
        embeddings_array = np.array(embeddings, dtype=np.float32)
        self._build_faiss_index(embeddings_array)

    def _build_faiss_index(self, embeddings: np.ndarray) -> None:
        """构建 FAISS 索引

        Args:
            embeddings: 文档向量矩阵 (N, D)
        """
        import faiss

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product (余弦相似度)

        # 归一化向量（使内积等价于余弦相似度）
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)

        logger.info(f"Built FAISS index with {self.index.ntotal} vectors (dim={dimension})")

    async def _get_embeddings_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """批量调用 Embedding API 获取向量

        Args:
            texts: 输入文本列表
            batch_size: 批次大小

        Returns:
            向量列表
        """
        if not texts:
            return []

        all_embeddings = []

        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await self._get_embedding_api(batch)

            if not batch_embeddings:
                logger.error(f"Failed to get embeddings for batch {i // batch_size + 1}")
                return []

            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _get_embedding_api(self, texts: list[str]) -> list[list[float]] | None:
        """调用 Embedding API（支持批量）

        Args:
            texts: 输入文本列表

        Returns:
            向量列表，失败返回 None
        """
        if not texts:
            return None

        # 过滤空文本
        valid_texts = [text.strip() for text in texts if text.strip()]
        if not valid_texts:
            return None

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_base}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "input": valid_texts,  # 批量输入
                        "encoding_format": "float",
                    },
                )

                if response.status_code != 200:
                    logger.error(f"Embedding API error: {response.status_code} {response.text}")
                    return None

                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings

        except Exception as e:
            logger.error(f"Failed to get embeddings: {e}")
            return None
