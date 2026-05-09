/**
 * Workflow Visualizer - Agent执行流程可视化
 * 展示Multi-Agent工作流的执行过程和时间线
 */

import { $, clearChildren } from './core.js';

/**
 * Agent图标映射
 */
const AGENT_ICONS = {
  planner: '📋',
  retriever: '🔍',
  generator: '✍️',
  reviewer: '👁️',
  critic: '⚖️',
  reflection: '🔄',
};

/**
 * Agent名称映射
 */
const AGENT_NAMES = {
  planner: 'Planner',
  retriever: 'Retriever',
  generator: 'Generator',
  reviewer: 'Reviewer',
  critic: 'Critic',
  reflection: 'Reflection',
};

/**
 * 渲染Agent执行时间线
 * @param {Array} steps - 工作流步骤数组
 * @param {string} containerId - 容器元素ID
 */
function resolveContainerSelector(containerId) {
  return containerId.startsWith('#') ? containerId : `#${containerId}`;
}

export function renderAgentTimeline(steps, containerId = 'agent-timeline') {
  const container = $(resolveContainerSelector(containerId));
  if (!container) return;

  clearChildren(container);

  // 创建时间线容器
  const timeline = document.createElement('div');
  timeline.className = 'agent-timeline';

  if (!steps || steps.length === 0) {
    const emptyState = document.createElement('div');
    emptyState.className = 'empty-state';
    emptyState.textContent = '暂无执行步骤';
    timeline.appendChild(emptyState);
    container.appendChild(timeline);
    return;
  }

  // 渲染每个步骤
  steps.forEach((step, index) => {
    const stepElement = createAgentStep(step, index);
    timeline.appendChild(stepElement);
  });

  container.appendChild(timeline);
}

/**
 * 创建单个Agent步骤元素
 * @param {Object} step - 步骤数据
 * @param {number} index - 步骤索引
 * @returns {HTMLElement}
 */
function createAgentStep(step, index) {
  const stepDiv = document.createElement('div');
  stepDiv.className = 'agent-step';

  // 根据状态添加类名
  if (step.status === 'completed') {
    stepDiv.classList.add('completed');
  } else if (step.status === 'running') {
    stepDiv.classList.add('running');
  }

  // 提取agent类型
  const agentType = extractAgentType(step.key || step.title || '');

  // 图标
  const icon = document.createElement('div');
  icon.className = 'step-icon';
  icon.textContent = AGENT_ICONS[agentType] || '🤖';

  // 信息区域
  const info = document.createElement('div');
  info.className = 'step-info';

  const title = document.createElement('strong');
  title.textContent = AGENT_NAMES[agentType] || step.title || `步骤 ${index + 1}`;

  const detail = document.createElement('span');
  detail.textContent = step.detail || step.message || '';

  info.appendChild(title);
  if (detail.textContent) {
    info.appendChild(detail);
  }

  // 时长（如果有）
  if (step.duration) {
    const duration = document.createElement('span');
    duration.className = 'step-duration';
    duration.textContent = formatDuration(step.duration);
    stepDiv.appendChild(icon);
    stepDiv.appendChild(info);
    stepDiv.appendChild(duration);
  } else {
    stepDiv.appendChild(icon);
    stepDiv.appendChild(info);
  }

  return stepDiv;
}

/**
 * 从步骤key中提取agent类型
 * @param {string} key - 步骤key
 * @returns {string}
 */
function extractAgentType(key) {
  const lowerKey = key.toLowerCase();
  if (lowerKey.includes('planner')) return 'planner';
  if (lowerKey.includes('retriever') || lowerKey.includes('retrieve')) return 'retriever';
  if (lowerKey.includes('generator') || lowerKey.includes('generate')) return 'generator';
  if (lowerKey.includes('reviewer') || lowerKey.includes('review')) return 'reviewer';
  if (lowerKey.includes('critic')) return 'critic';
  if (lowerKey.includes('reflection')) return 'reflection';
  return 'unknown';
}

/**
 * 格式化时长
 * @param {number} ms - 毫秒数
 * @returns {string}
 */
function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/**
 * 渲染质量指标
 * @param {Object} metrics - 质量指标数据
 * @param {string} containerId - 容器元素ID
 */
export function renderQualityMetrics(metrics, containerId = 'quality-metrics') {
  const container = $(resolveContainerSelector(containerId));
  if (!container) return;

  clearChildren(container);

  const metricsDiv = document.createElement('div');
  metricsDiv.className = 'quality-metrics';

  // 定义指标
  const metricsList = [
    {
      label: '引用覆盖率',
      value: metrics.citation_coverage || 0,
      key: 'citation_coverage'
    },
    {
      label: '质量评分',
      value: metrics.quality_score || 0,
      key: 'quality_score'
    },
    {
      label: '相关性',
      value: metrics.relevance || 0,
      key: 'relevance'
    },
    {
      label: '完整性',
      value: metrics.completeness || 0,
      key: 'completeness'
    }
  ];

  metricsList.forEach(metric => {
    if (metric.value !== undefined && metric.value !== null) {
      const metricElement = createMetricBar(metric.label, metric.value);
      metricsDiv.appendChild(metricElement);
    }
  });

  container.appendChild(metricsDiv);
}

/**
 * 创建指标条
 * @param {string} label - 指标标签
 * @param {number} value - 指标值（0-1）
 * @returns {HTMLElement}
 */
function createMetricBar(label, value) {
  const metric = document.createElement('div');
  metric.className = 'metric';

  const labelSpan = document.createElement('div');
  labelSpan.className = 'metric-label';
  labelSpan.textContent = label;

  const bar = document.createElement('div');
  bar.className = 'metric-bar';

  const fill = document.createElement('div');
  fill.className = 'metric-fill';
  const percentage = Math.round(value * 100);
  fill.style.width = `${percentage}%`;

  bar.appendChild(fill);

  const valueSpan = document.createElement('div');
  valueSpan.className = 'metric-value';
  valueSpan.textContent = `${percentage}%`;

  metric.appendChild(labelSpan);
  metric.appendChild(bar);
  metric.appendChild(valueSpan);

  return metric;
}

/**
 * 渲染Reflection迭代历史
 * @param {Array} iterations - 迭代历史数组
 * @param {string} containerId - 容器元素ID
 */
export function renderReflectionHistory(iterations, containerId = 'reflection-history') {
  const container = $(resolveContainerSelector(containerId));
  if (!container) return;

  clearChildren(container);

  if (!iterations || iterations.length === 0) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');

  const historyDiv = document.createElement('div');
  historyDiv.className = 'reflection-history';

  const title = document.createElement('h4');
  title.textContent = 'Reflection Loop 迭代历史';
  title.style.marginBottom = 'var(--space-4)';
  historyDiv.appendChild(title);

  iterations.forEach((iteration, index) => {
    const iterElement = createIterationElement(iteration, index + 1);
    historyDiv.appendChild(iterElement);
  });

  container.appendChild(historyDiv);
}

/**
 * 创建迭代元素
 * @param {Object} iteration - 迭代数据
 * @param {number} number - 迭代次数
 * @returns {HTMLElement}
 */
function createIterationElement(iteration, number) {
  const div = document.createElement('div');
  div.className = 'iteration';

  const badge = document.createElement('span');
  badge.className = 'iteration-badge';
  badge.textContent = `第${number}次`;

  const score = document.createElement('span');
  score.className = 'quality-score';
  score.textContent = iteration.score ? iteration.score.toFixed(2) : '0.00';

  const status = document.createElement('span');
  status.className = 'status';

  const threshold = iteration.threshold || 0.8;
  const isAcceptable = iteration.score >= threshold;

  status.textContent = isAcceptable ? '✅ 达标' : '❌ 未达标';
  status.style.color = isAcceptable ? 'var(--success-500)' : 'var(--error-500)';

  div.appendChild(badge);
  div.appendChild(score);
  div.appendChild(status);

  // 如果有改进建议，添加提示
  if (iteration.suggestions && iteration.suggestions.length > 0) {
    const suggestions = document.createElement('div');
    suggestions.style.marginTop = 'var(--space-2)';
    suggestions.style.fontSize = '13px';
    suggestions.style.color = 'var(--text-secondary)';
    suggestions.textContent = `改进建议: ${iteration.suggestions.join(', ')}`;
    div.appendChild(suggestions);
  }

  return div;
}

/**
 * 更新工作流可视化
 * @param {Object} workflowData - 工作流数据
 */
export function updateWorkflowVisualization(workflowData) {
  // 渲染Agent时间线
  if (workflowData.steps) {
    renderAgentTimeline(workflowData.steps, '#agent-timeline-container');
  }

  // 渲染质量指标
  const metrics = {
    citation_coverage: workflowData.citation_audit?.citation_coverage,
    quality_score: workflowData.quality_score,
    relevance: workflowData.dimension_scores?.relevance,
    completeness: workflowData.dimension_scores?.completeness,
  };
  renderQualityMetrics(metrics, 'quality-metrics-container');

  // 渲染Reflection历史
  if (workflowData.reflection_iterations) {
    renderReflectionHistory(workflowData.reflection_iterations, 'reflection-history-container');
  }
}
