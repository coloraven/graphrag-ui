import { apiClient } from './api-client.js';
import { showToast, state } from './core.js';
import {
  isIndexTaskActive,
  renderTaskDetail,
  resetTaskStatus,
  setIndexTaskStatus,
  setLatestTaskStatus,
} from './status-renderers.js';

export function createIndexTaskController({ refreshDocuments, refreshStatus, loadHistories }) {
  async function loadLatestTaskStatus() {
    try {
      const data = await apiClient.getLatestIndexTask();
      setLatestTaskStatus(data);
      if (!state.get('selectedTaskId') && data?.task_id) {
        state.set('selectedTaskId', data.task_id);
        renderTaskDetail(data);
      }
    } catch (error) {
      document.querySelector('#metric-last-task').textContent = '加载失败';
      showToast(error.message || '最近索引结果加载失败', 'error');
    }
  }

  async function loadTaskDetail(taskId) {
    if (!taskId) {
      state.set('selectedTaskId', null);
      renderTaskDetail(null);
      return;
    }
    try {
      const data = await apiClient.getIndexTask(taskId);
      state.set('selectedTaskId', taskId);
      renderTaskDetail(data);
    } catch (error) {
      showToast(error.message || '索引任务详情加载失败', 'error');
    }
  }

  async function loadCurrentTaskStatus() {
    try {
      const data = await apiClient.getCurrentIndexTask();
      setIndexTaskStatus(data, state);
      if (isIndexTaskActive(data)) startPolling();
      return data;
    } catch (error) {
      resetTaskStatus();
      showToast(error.message || '索引任务状态加载失败', 'error');
      return null;
    }
  }

  function stopPolling() {
    const indexPollTimer = state.get('indexPollTimer');
    if (!indexPollTimer) return;
    window.clearInterval(indexPollTimer);
    state.set('indexPollTimer', null);
  }

  function startPolling() {
    if (state.get('indexPollTimer')) return;
    const indexPollTimer = window.setInterval(async () => {
      const data = await loadCurrentTaskStatus();
      if (data === null) {
        return;
      }
      if (!isIndexTaskActive(data)) {
        stopPolling();
        await Promise.all([refreshStatus(), loadLatestTaskStatus(), refreshDocuments(), loadHistories()]);
        if (data?.state === 'succeeded') showToast(`索引完成：${data.document_count || 0} 个文档`);
        if (data?.state === 'failed') showToast(data.error || '索引任务失败', 'error');
      }
    }, 1600);
    state.set('indexPollTimer', indexPollTimer);
  }

  async function rebuildIndex() {
    const button = document.querySelector('#rebuild-index');
    button.disabled = true;
    button.textContent = '索引中';
    showToast('索引任务已启动');

    try {
      const data = await apiClient.rebuildIndex();
      setIndexTaskStatus(data, state);
      if (data?.task_id) {
        state.set('selectedTaskId', data.task_id);
        renderTaskDetail(data);
      }
      if (isIndexTaskActive(data)) startPolling();
    } catch (error) {
      showToast(error.message || '索引失败', 'error');
      button.disabled = false;
      button.textContent = '重建索引';
    }
  }

  return {
    loadCurrentTaskStatus,
    loadLatestTaskStatus,
    loadTaskDetail,
    rebuildIndex,
    startPolling,
    stopPolling,
  };
}
