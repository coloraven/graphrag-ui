/**
 * 核心工具模块
 * 提供基础工具函数和全局状态
 *
 * @deprecated 部分功能已迁移到新模块：
 * - DOM 操作 → dom-utils.js
 * - 状态管理 → state-manager.js
 * - 错误处理 → error-handler.js
 */

// 导出新模块的功能（向后兼容）
export { $, $$, clearChildren } from './dom-utils.js';
export { appState as state } from './state-manager.js';

// 保留旧的 state 对象以兼容现有代码
export const legacyState = {
  busy: false,
  progressTimer: null,
  resetTimer: null,
  toastTimer: null,
  indexPollTimer: null,
  selectedTaskId: null,
};

/**
 * 格式化字节大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化后的字符串
 */
export function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/**
 * 格式化时间
 * @param {string|Date} value - 时间值
 * @returns {string} 格式化后的时间字符串
 */
export function formatTime(value) {
  if (!value) return '暂无';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
}

/**
 * URL 编码查询参数
 * @param {string} value - 查询参数值
 * @returns {string} 编码后的字符串
 */
export function encodeQuery(value) {
  return encodeURIComponent(String(value || ''));
}

/**
 * 显示 Toast 提示
 * @param {string} message - 提示消息
 * @param {string} type - 提示类型（'info' | 'error' | 'success' | 'warning'）
 * @param {number} duration - 显示时长（毫秒）
 */
export function showToast(message, type = 'info', duration = 3200) {
  const toast = $('#toast');
  if (!toast) return;

  toast.textContent = message;

  // 移除所有类型类
  toast.classList.remove('error', 'success', 'warning', 'info');

  // 添加当前类型类
  toast.classList.add(type);
  toast.classList.remove('hidden');

  // 清除之前的定时器
  if (legacyState.toastTimer) {
    window.clearTimeout(legacyState.toastTimer);
  }

  // 设置新的定时器
  legacyState.toastTimer = window.setTimeout(() => {
    toast.classList.add('hidden');
    legacyState.toastTimer = null;
  }, duration);
}

/**
 * 读取 JSON 响应
 * @private
 * @param {Response} response - Fetch 响应对象
 * @returns {Promise<Object>} JSON 数据
 */
async function readJsonResponse(response) {
  const text = await response.text();
  if (!text) return {};

  try {
    return JSON.parse(text);
  } catch {
    if (response.ok) throw new Error('服务返回了无法解析的响应');
    return { detail: text };
  }
}

/**
 * 发送 JSON 请求
 * @param {string} url - 请求 URL
 * @param {Object} options - Fetch 选项
 * @returns {Promise<Object>} JSON 响应数据
 * @throws {Error} 请求失败时抛出错误
 */
export async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(data.detail || `请求失败：${response.status}`);
  }

  return data;
}
