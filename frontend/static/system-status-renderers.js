import { $, clearChildren, formatTime } from './core.js';

export function setMetricStatus(data) {
  $('#metric-ready').textContent = data.ready ? '已就绪' : '未建立';
  $('#metric-count').textContent = String(data.document_count || 0);
  $('#metric-time').textContent = formatTime(data.last_indexed_at);
}

export function setHealthStatus(data) {
  const statusLabel = {
    ok: '健康',
    warn: '需关注',
    fail: '异常',
  }[data?.status] || '未知';
  $('#metric-health').textContent = statusLabel;
  renderHealthComponents(Array.isArray(data?.components) ? data.components : []);
}

export function resetHealthStatus() {
  $('#metric-health').textContent = '异常';
  renderHealthComponents([]);
}

function renderHealthComponents(components) {
  const container = $('#health-components');
  clearChildren(container);

  components.forEach((component) => {
    const item = document.createElement('span');
    item.className = `health-chip ${component.status || 'warn'}`;
    item.textContent = `${component.name}：${component.detail || ''}`;
    container.appendChild(item);
  });
}
