import { $, clearChildren, formatTime } from './core.js';

const interactionLabels = {
  qa: '问答',
  checklist: '清单',
  workflow: '工作流',
  precheck: '预审',
};

export function renderInteractionHistory(items) {
  const container = $('#interaction-history');
  clearChildren(container);
  const historyItems = Array.isArray(items) ? items : [];

  if (!historyItems.length) {
    const empty = document.createElement('article');
    empty.className = 'history-card empty';
    empty.textContent = '暂无交互历史。';
    container.appendChild(empty);
    return;
  }

  historyItems.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'history-card';

    const title = document.createElement('strong');
    title.textContent = `${interactionLabels[item.kind] || item.kind || 'unknown'} · ${item.intent || '未识别'}`;
    const meta = document.createElement('span');
    meta.className = 'history-meta';
    meta.textContent = `${formatTime(item.created_at)} · 来源 ${item.source_count || 0} · 覆盖 ${Math.round((item.citation_coverage || 0) * 100)}%`;
    const prompt = document.createElement('div');
    prompt.className = 'history-prompt';
    prompt.textContent = item.prompt || '';
    const preview = document.createElement('div');
    preview.className = 'history-preview';
    preview.textContent = item.answer_preview || '无摘要';

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(prompt);
    card.appendChild(preview);
    container.appendChild(card);
  });
}

export function renderIndexHistory(items, onSelectTask) {
  const container = $('#index-history');
  clearChildren(container);
  const historyItems = Array.isArray(items) ? items : [];

  if (!historyItems.length) {
    const empty = document.createElement('article');
    empty.className = 'history-card empty';
    empty.textContent = '暂无索引历史。';
    container.appendChild(empty);
    return;
  }

  historyItems.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'history-card';
    if (item.task_id) {
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');
      card.setAttribute('aria-label', `${item.state || 'unknown'}，${item.stage || 'unknown'}，任务 ${item.task_id}，查看详情`);
      card.addEventListener('click', () => onSelectTask(item.task_id));
      card.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelectTask(item.task_id);
        }
      });
    }

    const title = document.createElement('strong');
    title.textContent = `${item.state || 'unknown'} · ${item.stage || 'unknown'}${item.task_id ? ` · ${item.task_id}` : ''}`;
    const meta = document.createElement('span');
    meta.className = 'history-meta';
    meta.textContent = `${formatTime(item.recorded_at)} · 文档 ${item.document_count || 0}`;
    const message = document.createElement('div');
    message.className = 'history-prompt';
    message.textContent = item.message || '';
    const detail = document.createElement('div');
    detail.className = 'history-preview';
    detail.textContent = item.error || `开始：${formatTime(item.started_at)}；结束：${formatTime(item.finished_at)}`;

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(message);
    card.appendChild(detail);
    container.appendChild(card);
  });
}
