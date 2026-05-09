import { $, clearChildren } from './core.js';

function isSafeHref(href) {
  try {
    const url = new URL(href, window.location.origin);
    return ['http:', 'https:'].includes(url.protocol);
  } catch {
    return false;
  }
}

function appendInlineMarkdown(container, text) {
  const source = String(text || '');
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(([^)\s]+)\)|\[\d+\])/g;
  let cursor = 0;

  source.replace(pattern, (match, _token, href, offset) => {
    if (offset > cursor) container.appendChild(document.createTextNode(source.slice(cursor, offset)));

    if (match.startsWith('**') && match.endsWith('**')) {
      const strong = document.createElement('strong');
      strong.textContent = match.slice(2, -2);
      container.appendChild(strong);
    } else if (match.startsWith('`') && match.endsWith('`')) {
      const code = document.createElement('code');
      code.textContent = match.slice(1, -1);
      container.appendChild(code);
    } else if (/^\[\d+\]$/.test(match)) {
      const citation = document.createElement('button');
      citation.type = 'button';
      citation.className = 'citation-ref';
      citation.dataset.citationIndex = match.slice(1, -1);
      citation.textContent = `依据 ${match.slice(1, -1)}`;
      citation.title = `定位到来源片段 ${match.slice(1, -1)}`;
      container.appendChild(citation);
    } else {
      const linkMatch = match.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/);
      if (linkMatch && isSafeHref(linkMatch[2])) {
        const link = document.createElement('a');
        link.href = linkMatch[2];
        link.textContent = linkMatch[1];
        link.target = '_blank';
        link.rel = 'noreferrer';
        container.appendChild(link);
      } else {
        container.appendChild(document.createTextNode(match));
      }
    }

    cursor = offset + match.length;
    return match;
  });

  if (cursor < source.length) container.appendChild(document.createTextNode(source.slice(cursor)));
}

function getIndentLevel(line) {
  const match = line.match(/^(\s*)/);
  return match ? match[1].length : 0;
}

function isListLine(line) {
  return /^\s*(?:[-*•]|\d+[.)、]|[（(]\d+[)）]|[一二三四五六七八九十]+、)\s+/.test(line);
}

function isTaskListLine(line) {
  return /^\s*[-*•]\s+\[([ xX])\]\s+/.test(line);
}

function isOrderedListLine(line) {
  return /^\s*(?:\d+[.)、]|[（(]\d+[)）]|[一二三四五六七八九十]+、)\s+/.test(line);
}

function stripListMarker(line) {
  return line.replace(/^\s*(?:[-*•]|\d+[.)、]|[（(]\d+[)）]|[一二三四五六七八九十]+、)\s+/, '');
}

function stripTaskListMarker(line) {
  const match = line.match(/^\s*[-*•]\s+\[([ xX])\]\s+(.*)$/);
  if (!match) return { checked: false, content: line };
  return {
    checked: match[1].toLowerCase() === 'x',
    content: match[2],
  };
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function parseTableRow(line) {
  return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
}

function appendParagraph(container, lines) {
  const paragraph = document.createElement('p');
  lines.forEach((line, index) => {
    if (index > 0) paragraph.appendChild(document.createElement('br'));
    appendInlineMarkdown(paragraph, line);
  });
  container.appendChild(paragraph);
}

function appendList(container, lines) {
  if (!lines.length) return;

  // 构建嵌套列表结构
  const root = { children: [], indent: -1 };
  const stack = [root];

  lines.forEach((line) => {
    const indent = getIndentLevel(line);
    const isTask = isTaskListLine(line);
    const isOrdered = !isTask && isOrderedListLine(line);

    let content, checked;
    if (isTask) {
      const taskData = stripTaskListMarker(line);
      content = taskData.content;
      checked = taskData.checked;
    } else {
      content = stripListMarker(line);
      checked = null;
    }

    // 找到正确的父节点
    while (stack.length > 1 && stack[stack.length - 1].indent >= indent) {
      stack.pop();
    }

    const parent = stack[stack.length - 1];
    const node = {
      content,
      indent,
      isOrdered,
      isTask,
      checked,
      children: [],
      element: null,
    };

    parent.children.push(node);
    stack.push(node);
  });

  // 递归渲染列表
  function renderListNode(node, parentElement) {
    if (node.children.length === 0) return;

    // 按类型分组子节点
    const groups = [];
    let currentGroup = null;

    node.children.forEach((child) => {
      const groupKey = child.isTask ? 'task' : (child.isOrdered ? 'ordered' : 'unordered');
      if (!currentGroup || currentGroup.type !== groupKey) {
        currentGroup = { type: groupKey, items: [] };
        groups.push(currentGroup);
      }
      currentGroup.items.push(child);
    });

    // 渲染每个分组
    groups.forEach((group) => {
      const list = document.createElement(group.type === 'ordered' ? 'ol' : 'ul');
      if (group.type === 'task') {
        list.className = 'task-list';
      }

      group.items.forEach((item) => {
        const li = document.createElement('li');

        if (item.isTask) {
          // 任务列表项
          const checkbox = document.createElement('input');
          checkbox.type = 'checkbox';
          checkbox.checked = item.checked;
          checkbox.disabled = true;
          checkbox.className = 'task-checkbox';

          const label = document.createElement('label');
          appendInlineMarkdown(label, item.content);

          li.appendChild(checkbox);
          li.appendChild(document.createTextNode(' '));
          li.appendChild(label);
          li.className = 'task-item';
        } else {
          // 普通列表项
          appendInlineMarkdown(li, item.content);
        }

        list.appendChild(li);

        // 递归渲染子列表
        if (item.children.length > 0) {
          renderListNode(item, li);
        }
      });

      parentElement.appendChild(list);
    });
  }

  renderListNode(root, container);
}

function appendCodeBlock(container, lines, language = '') {
  const pre = document.createElement('pre');
  const code = document.createElement('code');
  if (language) code.dataset.language = language;
  code.textContent = lines.join('\n');
  pre.appendChild(code);
  container.appendChild(pre);
}

function appendBlockquote(container, lines) {
  const quote = document.createElement('blockquote');
  appendParagraph(quote, lines.map((line) => line.replace(/^\s*>\s?/, '')));
  container.appendChild(quote);
}

function appendTable(container, lines) {
  const headers = parseTableRow(lines[0]);
  const bodyRows = lines.slice(2).map(parseTableRow);
  const wrapper = document.createElement('div');
  wrapper.className = 'markdown-table-wrap';
  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');

  headers.forEach((header) => {
    const cell = document.createElement('th');
    appendInlineMarkdown(cell, header);
    headRow.appendChild(cell);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  if (bodyRows.length) {
    const tbody = document.createElement('tbody');
    bodyRows.forEach((row) => {
      const bodyRow = document.createElement('tr');
      headers.forEach((_, index) => {
        const cell = document.createElement('td');
        appendInlineMarkdown(cell, row[index] || '');
        bodyRow.appendChild(cell);
      });
      tbody.appendChild(bodyRow);
    });
    table.appendChild(tbody);
  }

  wrapper.appendChild(table);
  container.appendChild(wrapper);
}

function isBlockStart(line, nextLine = '') {
  return (
    /^#{1,6}\s+/.test(line)
    || /^```\w*\s*$/.test(line)
    || /^\s*>\s?/.test(line)
    || isListLine(line)
    || (line.includes('|') && isTableSeparator(nextLine))
    || /^\s*---+\s*$/.test(line)
  );
}

export function renderAnswer(answer) {
  const container = $('#answer-text');
  clearChildren(container);

  const lines = String(answer || '').replace(/\r\n/g, '\n').split('\n');
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trimEnd();
    const nextLine = lines[index + 1] || '';

    if (!line.trim()) {
      index += 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = Math.min(headingMatch[1].length, 6);
      const heading = document.createElement(`h${level}`);
      appendInlineMarkdown(heading, headingMatch[2].trim());
      container.appendChild(heading);
      index += 1;
      continue;
    }

    const fenceMatch = line.match(/^```(\w*)\s*$/);
    if (fenceMatch) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !/^```\s*$/.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      appendCodeBlock(container, codeLines, fenceMatch[1]);
      index += index < lines.length ? 1 : 0;
      continue;
    }

    if (line.includes('|') && isTableSeparator(nextLine)) {
      const tableLines = [line, nextLine];
      index += 2;
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        tableLines.push(lines[index]);
        index += 1;
      }
      appendTable(container, tableLines);
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quoteLines = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        quoteLines.push(lines[index]);
        index += 1;
      }
      appendBlockquote(container, quoteLines);
      continue;
    }

    if (isListLine(line)) {
      const listLines = [];
      const ordered = isOrderedListLine(line);
      while (index < lines.length && isListLine(lines[index]) && isOrderedListLine(lines[index]) === ordered) {
        listLines.push(lines[index]);
        index += 1;
      }
      appendList(container, listLines);
      continue;
    }

    if (/^\s*---+\s*$/.test(line)) {
      container.appendChild(document.createElement('hr'));
      index += 1;
      continue;
    }

    const paragraphLines = [];
    while (index < lines.length && lines[index].trim()) {
      const current = lines[index].trimEnd();
      if (paragraphLines.length && isBlockStart(current, lines[index + 1] || '')) break;
      paragraphLines.push(current);
      index += 1;
    }
    appendParagraph(container, paragraphLines);
  }
}
