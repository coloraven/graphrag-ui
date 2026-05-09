import { $, clearChildren } from './core.js';

export function renderEvidence(items) {
  const list = $('#evidence-list');
  const panel = $('#evidence-section');
  const rawSources = Array.isArray(items) ? items : [];
  const sources = rawSources.filter((source) => String(source?.snippet || '').trim());
  clearChildren(list);

  if (!sources.length) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');

  sources.forEach((source) => {
    const snippet = String(source?.snippet || '').trim();

    const card = document.createElement('article');
    card.className = 'evidence-card';
    const rawIndex = source?.index;
    const citationIndex = Number.isFinite(rawIndex)
      ? rawIndex
      : rawSources.indexOf(source) + 1;
    card.dataset.citationIndex = String(citationIndex);

    const title = document.createElement('strong');
    title.textContent = `依据 ${citationIndex} · ${source?.document_name || '未知文档'}`;
    const meta = document.createElement('span');
    meta.className = 'evidence-meta';
    meta.textContent = source?.source_id ? `知识片段编号：${source.source_id}` : '知识片段编号：未返回';
    const body = document.createElement('div');
    body.textContent = snippet;

    card.appendChild(title);
    card.appendChild(meta);
    card.appendChild(body);
    list.appendChild(card);
  });
}

export function renderCitationAudit(audit) {
  const panel = $('#citation-audit-panel');
  const summary = $('#citation-audit-summary');
  const warnings = $('#citation-audit-warnings');
  clearChildren(summary);
  clearChildren(warnings);

  if (!audit) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');
  panel.dataset.status = audit.status || 'fail';
  const statusName = {
    pass: '通过',
    warn: '需复核',
    fail: '未通过',
  }[audit.status] || '未知';
  const citedLabels = (audit.cited_indices || []).map((index) => `依据 ${index}`).join('、') || '无';
  const items = [
    `检查结果：${statusName}`,
    `来源片段：${audit.source_count || 0}`,
    `来源覆盖：${Math.round((audit.citation_coverage || 0) * 100)}%`,
    `已对应：${citedLabels}`,
  ];

  items.forEach((value) => {
    const item = document.createElement('span');
    item.textContent = value;
    summary.appendChild(item);
  });

  (Array.isArray(audit.warnings) ? audit.warnings : []).forEach((warning) => {
    const item = document.createElement('div');
    item.textContent = warning;
    warnings.appendChild(item);
  });
}

export function renderEvidencePack(pack, serviceContext) {
  const panel = $('#evidence-pack-panel');
  const summary = $('#evidence-pack-summary');
  const facts = $('#evidence-pack-facts');
  const risks = $('#evidence-pack-risks');
  clearChildren(summary);
  clearChildren(facts);
  clearChildren(risks);

  if (!pack) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');
  const slots = serviceContext?.slots || {};
  const slotText = Object.keys(slots).length
    ? Object.entries(slots).map(([key, value]) => `${key}:${value}`).join('、')
    : '无';
  const summaryItems = [
    `客服任务：${serviceContext?.task_type || '未识别'}`,
    `业务范围：${serviceContext?.in_scope === false ? '越界' : '范围内'}`,
    `槽位：${slotText}`,
    `任务类型：${pack.intent || '未识别'}`,
    `检索策略：${pack.retrieval_strategy || '未返回'}`,
    `排序策略：${pack.ranking_strategy || '未返回'}`,
    `情形标签：${(pack.scenario_tags || []).join('、') || '无'}`,
    `查询变体：${(pack.query_variants || []).join('；') || '无'}`,
  ];
  summaryItems.forEach((value) => {
    const item = document.createElement('span');
    item.textContent = value;
    summary.appendChild(item);
  });

  (Array.isArray(pack.key_facts) ? pack.key_facts : []).forEach((fact) => {
    const item = document.createElement('article');
    const title = document.createElement('strong');
    const detail = document.createElement('span');
    title.textContent = fact.title || '关键依据';
    detail.textContent = fact.detail || '';
    item.appendChild(title);
    item.appendChild(detail);
    facts.appendChild(item);
  });

  (Array.isArray(pack.risk_flags) ? pack.risk_flags : []).forEach((risk) => {
    const item = document.createElement('article');
    item.dataset.level = risk.level || 'info';
    const title = document.createElement('strong');
    const detail = document.createElement('span');
    title.textContent = risk.level === 'warning' ? '需复核' : '提示';
    detail.textContent = risk.message || '';
    item.appendChild(title);
    item.appendChild(detail);
    risks.appendChild(item);
  });
}
