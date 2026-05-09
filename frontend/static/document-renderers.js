import { $, clearChildren, formatBytes, formatTime } from './core.js';

export function renderDocumentRows(items, previewDocument) {
  const tbody = $('#document-table');
  clearChildren(tbody);

  if (!items.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 6;
    cell.textContent = 'input 目录暂无可用资料。支持 txt、md、pdf。';
    row.appendChild(cell);
    tbody.appendChild(row);
    return;
  }

  items.forEach((item) => {
    const row = document.createElement('tr');
    const indexLabel = item.stale ? '需重建' : item.indexed ? '已索引' : '未索引';
    const values = [item.name, item.type, formatBytes(item.size), formatTime(item.updated_at), indexLabel];

    values.forEach((value, index) => {
      const cell = document.createElement('td');
      if (index === 4) {
        const badge = document.createElement('span');
        badge.className = `status-badge${item.stale ? ' warning' : item.indexed ? '' : ' muted'}`;
        badge.textContent = value;
        cell.appendChild(badge);
      } else {
        cell.textContent = value;
      }
      row.appendChild(cell);
    });

    const actionCell = document.createElement('td');
    const previewButton = document.createElement('button');
    previewButton.type = 'button';
    previewButton.className = 'table-action';
    previewButton.textContent = '预览';
    previewButton.addEventListener('click', () => previewDocument(item.name));
    actionCell.appendChild(previewButton);
    row.appendChild(actionCell);
    tbody.appendChild(row);
  });
}
