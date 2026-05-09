/**
 * 加载状态组件
 * 提供统一的加载指示器、骨架屏、进度条
 */

import { $, createElement, clearChildren, addClass, removeClass } from './dom-utils.js';

/**
 * 创建加载指示器
 * @param {Object} options - 配置选项
 * @param {string} options.size - 大小（'small' | 'medium' | 'large'）
 * @param {string} options.text - 加载文本
 * @returns {Element} 加载指示器元素
 */
export function createLoadingSpinner(options = {}) {
  const { size = 'medium', text = '加载中...' } = options;

  const sizeMap = {
    small: '16px',
    medium: '24px',
    large: '32px',
  };

  const spinner = createElement('div', {
    className: 'loading-spinner',
    attributes: {
      role: 'status',
      'aria-label': text,
    },
  });

  spinner.style.width = sizeMap[size];
  spinner.style.height = sizeMap[size];

  if (text) {
    const container = createElement('div', {
      className: 'loading-container',
      children: [
        spinner,
        createElement('span', {
          className: 'loading-text',
          textContent: text,
        }),
      ],
    });
    return container;
  }

  return spinner;
}

/**
 * 显示全局加载遮罩
 * @param {string} text - 加载文本
 */
export function showGlobalLoading(text = '处理中...') {
  let overlay = $('#global-loading-overlay');

  if (!overlay) {
    overlay = createElement('div', {
      attributes: {
        id: 'global-loading-overlay',
        role: 'dialog',
        'aria-modal': 'true',
        'aria-label': text,
      },
    });

    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9998;
      backdrop-filter: blur(4px);
    `;

    document.body.appendChild(overlay);
  }

  clearChildren(overlay);
  overlay.appendChild(createLoadingSpinner({ size: 'large', text }));
  removeClass(overlay, 'hidden');
}

/**
 * 隐藏全局加载遮罩
 */
export function hideGlobalLoading() {
  const overlay = $('#global-loading-overlay');
  if (overlay) {
    addClass(overlay, 'hidden');
  }
}

/**
 * 创建骨架屏
 * @param {Object} options - 配置选项
 * @param {number} options.lines - 行数
 * @param {boolean} options.hasTitle - 是否包含标题
 * @param {boolean} options.hasAvatar - 是否包含头像
 * @returns {Element} 骨架屏元素
 */
export function createSkeleton(options = {}) {
  const {
    lines = 3,
    hasTitle = false,
    hasAvatar = false,
  } = options;

  const container = createElement('div', {
    className: 'skeleton-container',
    attributes: {
      'aria-busy': 'true',
      'aria-label': '加载中',
    },
  });

  // 头像
  if (hasAvatar) {
    const avatar = createElement('div', {
      className: 'skeleton skeleton-avatar',
    });
    avatar.style.cssText = 'width: 48px; height: 48px; border-radius: 50%; margin-bottom: 12px;';
    container.appendChild(avatar);
  }

  // 标题
  if (hasTitle) {
    container.appendChild(createElement('div', {
      className: 'skeleton skeleton-title',
    }));
  }

  // 文本行
  for (let i = 0; i < lines; i++) {
    const line = createElement('div', {
      className: 'skeleton skeleton-text',
    });

    // 最后一行宽度随机
    if (i === lines - 1) {
      line.style.width = `${60 + Math.random() * 30}%`;
    }

    container.appendChild(line);
  }

  return container;
}

/**
 * 显示骨架屏
 * @param {string} selector - 容器选择器
 * @param {Object} options - 骨架屏选项
 */
export function showSkeleton(selector, options = {}) {
  const container = $(selector);
  if (!container) return;

  clearChildren(container);
  container.appendChild(createSkeleton(options));
}

/**
 * 隐藏骨架屏
 * @param {string} selector - 容器选择器
 */
export function hideSkeleton(selector) {
  const container = $(selector);
  if (!container) return;

  const skeleton = container.querySelector('.skeleton-container');
  if (skeleton) {
    skeleton.remove();
  }
}

/**
 * 创建进度条
 * @param {Object} options - 配置选项
 * @param {number} options.value - 当前值（0-100）
 * @param {string} options.label - 标签文本
 * @param {boolean} options.showPercentage - 是否显示百分比
 * @returns {Element} 进度条元素
 */
export function createProgressBar(options = {}) {
  const {
    value = 0,
    label = '',
    showPercentage = true,
  } = options;

  const container = createElement('div', {
    className: 'progress-container',
  });

  // 标签和百分比
  if (label || showPercentage) {
    const header = createElement('div', {
      className: 'progress-header',
      children: [
        label ? createElement('span', { textContent: label }) : null,
        showPercentage ? createElement('span', { textContent: `${value}%` }) : null,
      ].filter(Boolean),
    });
    header.style.cssText = 'display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;';
    container.appendChild(header);
  }

  // 进度条轨道
  const track = createElement('div', {
    className: 'progress-track',
    attributes: {
      role: 'progressbar',
      'aria-valuenow': String(value),
      'aria-valuemin': '0',
      'aria-valuemax': '100',
    },
  });

  // 进度条填充
  const bar = createElement('div', {
    className: 'progress-bar',
  });
  bar.style.width = `${value}%`;

  track.appendChild(bar);
  container.appendChild(track);

  return container;
}

/**
 * 更新进度条
 * @param {Element} progressBar - 进度条元素
 * @param {number} value - 新的进度值（0-100）
 */
export function updateProgressBar(progressBar, value) {
  if (!progressBar) return;

  const bar = progressBar.querySelector('.progress-bar');
  const percentage = progressBar.querySelector('.progress-header span:last-child');
  const track = progressBar.querySelector('.progress-track');

  if (bar) {
    bar.style.width = `${value}%`;
  }

  if (percentage) {
    percentage.textContent = `${value}%`;
  }

  if (track) {
    track.setAttribute('aria-valuenow', String(value));
  }
}

/**
 * 创建空状态组件
 * @param {Object} options - 配置选项
 * @param {string} options.icon - 图标（emoji 或 SVG）
 * @param {string} options.title - 标题
 * @param {string} options.message - 消息
 * @param {string} options.actionText - 操作按钮文本
 * @param {Function} options.onAction - 操作按钮回调
 * @returns {Element} 空状态元素
 */
export function createEmptyState(options = {}) {
  const {
    icon = '📭',
    title = '暂无数据',
    message = '',
    actionText = '',
    onAction = null,
  } = options;

  const container = createElement('div', {
    className: 'empty-state',
  });

  container.style.cssText = `
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px 24px;
    text-align: center;
    color: var(--muted);
  `;

  // 图标
  const iconElement = createElement('div', {
    className: 'empty-state-icon',
    textContent: icon,
  });
  iconElement.style.cssText = 'font-size: 48px; margin-bottom: 16px;';
  container.appendChild(iconElement);

  // 标题
  const titleElement = createElement('h3', {
    textContent: title,
  });
  titleElement.style.cssText = 'margin: 0 0 8px 0; color: var(--ink);';
  container.appendChild(titleElement);

  // 消息
  if (message) {
    const messageElement = createElement('p', {
      textContent: message,
    });
    messageElement.style.cssText = 'margin: 0 0 24px 0; max-width: 400px;';
    container.appendChild(messageElement);
  }

  // 操作按钮
  if (actionText && onAction) {
    const button = createElement('button', {
      className: 'primary-button',
      textContent: actionText,
      attributes: {
        type: 'button',
      },
    });
    button.addEventListener('click', onAction);
    container.appendChild(button);
  }

  return container;
}

/**
 * 显示空状态
 * @param {string} selector - 容器选择器
 * @param {Object} options - 空状态选项
 */
export function showEmptyState(selector, options = {}) {
  const container = $(selector);
  if (!container) return;

  clearChildren(container);
  container.appendChild(createEmptyState(options));
}
