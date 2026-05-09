/**
 * 工作流控制器
 * 负责问答流程的控制和状态管理
 */

import { apiClient } from './api-client.js';
import { $, showToast, legacyState } from './core.js';
import { handleError, validateInput } from './error-handler.js';
import {
  renderCitationAudit,
  renderEvidence,
  renderEvidencePack,
  renderWorkflowSteps,
  setResultVisible,
} from './dashboard.js';
import { renderAnswer } from './markdown.js';
import {
  renderAgentTimeline,
} from './workflow-visualizer.js';

/**
 * 创建工作流控制器
 * @param {Object} options - 配置选项
 * @param {Function} options.loadHistories - 加载历史记录的回调
 * @returns {Object} 控制器对象
 */
export function createWorkflowController({ loadHistories }) {
  function hasMeaningfulEvidencePack(pack) {
    if (!pack) return false;
    return Boolean(
      pack.intent
      || pack.retrieval_strategy
      || pack.ranking_strategy
      || (Array.isArray(pack.query_variants) && pack.query_variants.length > 0)
      || (Array.isArray(pack.scenario_tags) && pack.scenario_tags.length > 0)
      || (Array.isArray(pack.sources) && pack.sources.length > 0)
      || (Array.isArray(pack.key_facts) && pack.key_facts.length > 0)
      || (Array.isArray(pack.risk_flags) && pack.risk_flags.length > 0)
    );
  }

  /**
   * 设置加载状态
   * @param {boolean} loading - 是否加载中
   */
  function setLoading(loading) {
    const loadingPanel = $('#qa-loading');
    const button = $('#submit-question');
    const progressBar = $('#qa-progress-bar');
    const loadingText = $('#qa-loading-text');
    const percent = $('#qa-loading-percent');

    // 清除定时器
    if (legacyState.progressTimer) {
      window.clearInterval(legacyState.progressTimer);
      legacyState.progressTimer = null;
    }
    if (legacyState.resetTimer) {
      window.clearTimeout(legacyState.resetTimer);
      legacyState.resetTimer = null;
    }

    // 更新状态
    legacyState.busy = loading;
    button.disabled = loading;
    button.textContent = loading ? '预审中' : '执行预审';

    // 加载完成
    if (!loading) {
      progressBar.style.width = '100%';
      progressBar.setAttribute('aria-valuenow', '100');
      percent.textContent = '100%';

      legacyState.resetTimer = window.setTimeout(() => {
        loadingPanel.classList.add('hidden');
        progressBar.style.width = '0%';
        progressBar.setAttribute('aria-valuenow', '0');
        loadingText.textContent = '正在核对办理要求...';
        percent.textContent = '0%';
        legacyState.resetTimer = null;
      }, 260);
      return;
    }

    // 开始加载
    let progress = 8;
    loadingPanel.classList.remove('hidden');
    loadingText.textContent = '正在核对办理要求...';
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', String(progress));
    percent.textContent = `${progress}%`;

    // 模拟进度条
    legacyState.progressTimer = window.setInterval(() => {
      progress = Math.min(progress + Math.ceil(Math.random() * 10), 92);
      progressBar.style.width = `${progress}%`;
      progressBar.setAttribute('aria-valuenow', String(progress));
      percent.textContent = `${progress}%`;

      // 根据进度更新提示文本
      if (progress > 62) {
        loadingText.textContent = '正在生成回答结果...';
      } else if (progress > 28) {
        loadingText.textContent = '正在比对已提供材料...';
      }
    }, 520);
  }

  function parseSubmittedMaterials(rawText) {
    return String(rawText || '')
      .split(/\r?\n|[;,；]/)
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 30);
  }

  /**
   * 提交问题
   */
  async function submitQuestion() {
    // 防止重复提交
    if (legacyState.busy) return;

    const questionInput = $('#question-input');
    const materialsInput = $('#materials-input');
    const question = questionInput.value.trim();
    const submittedMaterials = parseSubmittedMaterials(materialsInput?.value || '');

    // 验证输入
    const validation = validateInput(question, {
      required: true,
      minLength: 2,
      maxLength: 500,
    });

    if (!validation.valid) {
      showToast(validation.message, 'error');
      questionInput.focus();
      return;
    }

    setLoading(true);

    try {
      const data = await apiClient.runWorkflow(question, submittedMaterials, '');

      // 渲染结果
      setResultVisible(data.title || '问答结果');
      renderAnswer(data.answer || data.summary || '');
      renderEvidence(data.sources);

      const timelineSection = $('#agent-timeline-section');
      const metricsSection = $('#quality-metrics-section');
      const reflectionSection = $('#reflection-history-section');

      if (data.steps && data.steps.length > 0) {
        if (timelineSection) timelineSection.classList.remove('hidden');
        renderAgentTimeline(data.steps, '#agent-timeline-container');
      } else if (timelineSection) {
        timelineSection.classList.add('hidden');
      }

      if (metricsSection) metricsSection.classList.add('hidden');
      if (reflectionSection) reflectionSection.classList.add('hidden');

      renderEvidencePack(hasMeaningfulEvidencePack(data.evidence_pack) ? data.evidence_pack : null, data.service_context);
      renderCitationAudit(data.citation_audit);
      renderWorkflowSteps(data.steps);

      // 显示工作流详情
      const workflowPanel = $('#workflow-panel');
      if (workflowPanel) {
        workflowPanel.classList.remove('hidden');
      }

      // 刷新历史记录
      await loadHistories();

      // 显示成功提示
      showToast('回答完成', 'success');
    } catch (error) {
      // 统一错误处理
      handleError(error, {
        context: '问答流程',
        showToast: true,
      });
    } finally {
      setLoading(false);
    }
  }

  return {
    submitQuestion,
  };
}
