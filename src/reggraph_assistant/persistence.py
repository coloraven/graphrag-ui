"""持久化层 - 简化版，直接使用 SQLite"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock

from .paths import AppPaths


class AppStateStore:
    """应用状态存储 - 简化版"""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = Lock()

    def initialize(self) -> None:
        """初始化数据库表"""
        with self._lock:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS interaction_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        prompt TEXT NOT NULL,
                        context TEXT,
                        intent TEXT,
                        answer TEXT,
                        source_count INTEGER,
                        citation_coverage REAL,
                        status TEXT
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    def ping(self) -> bool:
        """检查数据库连接"""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("SELECT 1")
            conn.close()
            return True
        except Exception:
            return False

    def log_interaction(
        self,
        kind: str,
        prompt: str,
        context: str,
        intent: str,
        answer: str,
        source_count: int,
        citation_coverage: float,
        status: str,
    ) -> None:
        """记录交互历史"""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            try:
                conn.execute(
                    """
                    INSERT INTO interaction_history
                    (timestamp, kind, prompt, context, intent, answer, source_count, citation_coverage, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now().isoformat(),
                        kind,
                        prompt,
                        context,
                        intent,
                        answer,
                        source_count,
                        citation_coverage,
                        status,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list_interactions(self, limit: int = 8) -> list[dict]:
        """获取交互历史列表"""
        with self._lock:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(
                    """
                    SELECT id, timestamp, kind, prompt, intent, answer, source_count, citation_coverage, status
                    FROM interaction_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def mark_incomplete_index_tasks_failed(self, reason: str) -> int:
        """标记未完成的索引任务为失败状态（服务重启时调用）

        注意：此方法依赖 index_tasks 表，该表由 IndexTaskManager 管理。
        如果表不存在，静默返回 0。

        Returns:
            标记失败的任务数量
        """
        # IndexTaskManager 使用内存状态管理，不依赖数据库
        # 此方法保留接口兼容性，但不执行任何操作
        return 0

    def load_latest_index_task_status(self):
        """加载最新的索引任务状态

        注意：IndexTaskManager 使用内存状态管理，不依赖数据库持久化。
        此方法保留接口兼容性，始终返回 None。
        """
        return None


_STORE_CACHE: dict[str, AppStateStore] = {}
_STORE_CACHE_LOCK = Lock()


def get_app_state_store(paths: AppPaths) -> AppStateStore:
    """获取应用状态存储实例（单例）"""
    key = str(paths.app_state_db)
    with _STORE_CACHE_LOCK:
        store = _STORE_CACHE.get(key)
        if store is None:
            store = AppStateStore(paths.app_state_db)
            _STORE_CACHE[key] = store
    store.initialize()
    return store


__all__ = [
    "AppStateStore",
    "get_app_state_store",
]
