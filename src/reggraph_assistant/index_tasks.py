from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import logging
from threading import Condition, Thread
from typing import Literal
from uuid import uuid4

from .indexing import IndexBuildError, rebuild_index
from .paths import AppPaths
from .persistence import AppStateStore, get_app_state_store
from .schemas import IndexTaskStatusResponse
from .settings import Settings


logger = logging.getLogger(__name__)


IndexTaskState = Literal["idle", "queued", "running", "succeeded", "failed"]


@dataclass
class IndexTaskRecord:
    task_id: str | None = None
    state: IndexTaskState = "idle"
    stage: str = "idle"
    message: str = "暂无正在运行的索引任务"
    queue_depth: int = 0
    document_count: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None

    def to_response(self) -> IndexTaskStatusResponse:
        return IndexTaskStatusResponse(
            task_id=self.task_id,
            state=self.state,
            stage=self.stage,
            message=self.message,
            queue_depth=self.queue_depth,
            document_count=self.document_count,
            started_at=self.started_at,
            finished_at=self.finished_at,
            error=self.error,
        )


@dataclass(frozen=True)
class PendingIndexTask:
    task_id: str
    settings: Settings
    started_at: str


class IndexTaskManager:
    def __init__(self) -> None:
        self._condition = Condition()
        self._record = IndexTaskRecord()
        self._queue: deque[PendingIndexTask] = deque()
        self._worker: Thread | None = None
        self._store: AppStateStore | None = None
        self._configured_db_path: str | None = None

    def configure(self, paths: AppPaths) -> None:
        store = get_app_state_store(paths)
        db_key = str(paths.app_state_db)
        with self._condition:
            if self._configured_db_path == db_key:
                return
            if self._configured_db_path is not None and (self._record.state in {"queued", "running"} or self._queue):
                raise RuntimeError("Index task manager is busy with another workspace")
            self._store = store
            self._configured_db_path = db_key
            recovered = store.mark_incomplete_index_tasks_failed("服务重启导致索引任务中断")
            latest = store.load_latest_index_task_status()
            if latest is not None:
                self._record = IndexTaskRecord(
                    task_id=latest.task_id,
                    state=latest.state,
                    stage=latest.stage,
                    message=latest.message,
                    queue_depth=0,
                    document_count=latest.document_count,
                    started_at=latest.started_at,
                    finished_at=latest.finished_at,
                    error=latest.error,
                )
            elif recovered:
                self._record = IndexTaskRecord(
                    state="failed",
                    stage="failed",
                    message="服务重启后已标记未完成索引任务",
                    finished_at=datetime.now().isoformat(),
                    error="服务重启导致索引任务中断",
                )
            self._ensure_worker_locked()

    def get_status(self) -> IndexTaskStatusResponse:
        with self._condition:
            return self._record.to_response()

    def get_latest_completed_status(self) -> IndexTaskStatusResponse:
        with self._condition:
            if self._store is None:
                return IndexTaskStatusResponse(state="idle", stage="idle", message="暂无已完成索引任务")
            latest = self._store.load_latest_completed_index_task_status()
            if latest is not None:
                return latest
            if self._record.state in {"succeeded", "failed"}:
                return self._record.to_response()
            return IndexTaskStatusResponse(state="idle", stage="idle", message="暂无已完成索引任务")

    def get_task_status(self, task_id: str) -> IndexTaskStatusResponse | None:
        with self._condition:
            if self._record.task_id == task_id:
                return self._record.to_response()
            if self._store is None:
                return None
            return self._store.load_index_task_status_by_task_id(task_id)

    def start(self, settings: Settings) -> IndexTaskStatusResponse:
        self.configure(settings.paths)
        with self._condition:
            task_id = self._generate_task_id()
            pending = PendingIndexTask(
                task_id=task_id,
                settings=settings,
                started_at=datetime.now().isoformat(),
            )
            self._queue.append(pending)
            queue_depth = len(self._queue)
            queued_record = IndexTaskRecord(
                task_id=task_id,
                state="queued",
                stage="queued",
                message="索引任务已进入队列",
                queue_depth=queue_depth,
                started_at=pending.started_at,
            )
            self._persist_record_locked(queued_record)
            if self._record.state not in {"running", "queued"}:
                self._record = queued_record
            else:
                self._record.queue_depth = len(self._queue)
                self._persist_record_locked(self._record)
            self._ensure_worker_locked()
            self._condition.notify()
            return queued_record.to_response()

    def _generate_task_id(self) -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]

    def _ensure_worker_locked(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = Thread(target=self._run_worker, name="index-task-worker", daemon=True)
        self._worker.start()

    def _persist_record_locked(self, record: IndexTaskRecord) -> None:
        if self._store is None:
            return
        self._store.log_index_task_snapshot(record.to_response())

    def _set_record(self, record: IndexTaskRecord) -> None:
        with self._condition:
            self._record = record
            self._persist_record_locked(record)

    def _complete_task(self, record: IndexTaskRecord) -> None:
        with self._condition:
            self._persist_record_locked(record)
            if self._queue:
                next_pending = self._queue[0]
                queued_record = IndexTaskRecord(
                    task_id=next_pending.task_id,
                    state="queued",
                    stage="queued",
                    message="索引任务排队中，等待前序任务完成",
                    queue_depth=len(self._queue),
                    started_at=next_pending.started_at,
                )
                self._record = queued_record
                self._persist_record_locked(queued_record)
            else:
                self._record = record

    def _run_worker(self) -> None:
        while True:
            with self._condition:
                while not self._queue:
                    self._condition.wait()
                pending = self._queue.popleft()
                running_record = IndexTaskRecord(
                    task_id=pending.task_id,
                    state="running",
                    stage="starting",
                    message="索引任务正在启动",
                    queue_depth=len(self._queue),
                    started_at=pending.started_at,
                )
                self._record = running_record
                self._persist_record_locked(running_record)

            def report(stage: str, message: str) -> None:
                self._set_record(
                    IndexTaskRecord(
                        task_id=pending.task_id,
                        state="running",
                        stage=stage,
                        message=message,
                        queue_depth=self._queued_count(),
                        started_at=pending.started_at,
                    )
                )

            try:
                result = rebuild_index(pending.settings, progress_callback=report)
            except IndexBuildError as exc:
                logger.error(f"Index build failed: {exc}")
                self._complete_task(
                    IndexTaskRecord(
                        task_id=pending.task_id,
                        state="failed",
                        stage="failed",
                        message="索引构建失败",
                        queue_depth=self._queued_count(),
                        started_at=pending.started_at,
                        finished_at=datetime.now().isoformat(),
                        error=str(exc),
                    )
                )
                continue
            except Exception as exc:
                logger.exception("Unexpected error during index task")
                self._complete_task(
                    IndexTaskRecord(
                        task_id=pending.task_id,
                        state="failed",
                        stage="failed",
                        message="索引任务失败（未预期错误）",
                        queue_depth=self._queued_count(),
                        started_at=pending.started_at,
                        finished_at=datetime.now().isoformat(),
                        error=str(exc),
                    )
                )
                continue

            self._complete_task(
                IndexTaskRecord(
                    task_id=pending.task_id,
                    state="succeeded",
                    stage="completed",
                    message="索引任务完成",
                    queue_depth=self._queued_count(),
                    document_count=result.document_count,
                    started_at=pending.started_at,
                    finished_at=datetime.now().isoformat(),
                )
            )

    def _queued_count(self) -> int:
        with self._condition:
            return len(self._queue)


INDEX_TASK_MANAGER = IndexTaskManager()
