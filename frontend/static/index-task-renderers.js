import { $, formatTime } from './core.js';

export function renderTaskDetail(data) {
  const panel = $('#index-task-detail');
  const status = data || {};
  if (!status.task_id) {
    panel.classList.add('hidden');
    $('#task-detail-title').textContent = '-';
    $('#task-detail-message').textContent = '-';
    return;
  }
  const stateName = {
    idle: '空闲',
    queued: '排队中',
    running: '运行中',
    succeeded: '已完成',
    failed: '失败',
  }[status.state] || '未知';
  $('#task-detail-title').textContent = `${status.task_id} · ${stateName}`;
  $('#task-detail-message').textContent = status.error
    ? `${status.message || '任务失败'}：${status.error}`
    : `${status.message || '无详情'}；阶段 ${status.stage || 'idle'}；开始 ${formatTime(status.started_at)}；结束 ${formatTime(status.finished_at)}`;
  panel.classList.remove('hidden');
}

export function resetTaskStatus() {
  $('#index-task-message').textContent = '索引任务状态加载失败';
  $('#index-task-state').textContent = '失败';
}

export function isIndexTaskActive(data) {
  return ['queued', 'running'].includes(data?.state);
}

export function setLatestTaskStatus(data) {
  const status = data || {};
  if (!status.task_id) {
    $('#metric-last-task').textContent = status.message || '暂无';
    return;
  }
  const stateName = {
    succeeded: '成功',
    failed: '失败',
  }[status.state] || status.state || '未知';
  $('#metric-last-task').textContent = `${stateName} · ${status.task_id}`;
}

export function setIndexTaskStatus(data, state) {
  const status = data || {};
  const stateName = {
    idle: '空闲',
    queued: '排队中',
    running: '运行中',
    succeeded: '已完成',
    failed: '失败',
  }[status.state] || '未知';
  const selectedTaskId = state.get('selectedTaskId');

  $('#index-task-stage').textContent = status.stage || 'idle';
  $('#index-task-message').textContent = status.error
    ? `${status.message || '索引任务失败'}：${status.error}`
    : (status.message || '暂无正在运行的索引任务。');
  if (status.task_id) {
    const queueSuffix = Number.isFinite(status.queue_depth) && status.queue_depth > 0
      ? ` · 队列 ${status.queue_depth}`
      : '';
    $('#index-task-message').textContent += `（任务 ${status.task_id}${queueSuffix}）`;
  }
  $('#index-task-state').textContent = stateName;
  $('#index-task-state').classList.toggle('muted', !isIndexTaskActive(status));

  const button = $('#rebuild-index');
  const active = isIndexTaskActive(status);
  button.disabled = active;
  button.textContent = status.state === 'queued' ? '排队中' : active ? '索引中' : '重建索引';
  if (!selectedTaskId && status.task_id) {
    renderTaskDetail(status);
  }
  if (selectedTaskId && status.task_id === selectedTaskId) {
    renderTaskDetail(status);
  }
}
