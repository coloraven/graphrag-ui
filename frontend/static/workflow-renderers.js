import { $, clearChildren } from './core.js';

export function setResultVisible(title = '智能处理结果') {
  $('#answer-panel').classList.remove('empty');
  $('#empty-result').classList.add('hidden');
  $('#workflow-details').classList.remove('hidden');
  $('#answer-panel-title').textContent = title;
  $('#answer-text').classList.remove('hidden');
}

export function renderWorkflowSteps(steps) {
  const list = $('#workflow-steps');
  clearChildren(list);

  (Array.isArray(steps) ? steps : []).forEach((step) => {
    const item = document.createElement('article');
    item.className = 'workflow-step';
    const title = document.createElement('strong');
    title.textContent = step.title || step.key || '执行步骤';
    const detail = document.createElement('span');
    detail.textContent = step.detail || '';
    const status = document.createElement('em');
    status.textContent = step.status || 'completed';
    item.appendChild(title);
    item.appendChild(detail);
    item.appendChild(status);
    list.appendChild(item);
  });

  if (!list.childElementCount) {
    const empty = document.createElement('article');
    empty.className = 'workflow-step';
    empty.textContent = '暂无工作流步骤。';
    list.appendChild(empty);
  }
}
