/**
 * 通知系统
 * 提供 Toast、Alert、Confirm、Notification 等多种通知方式
 */

import { createElement, addClass, removeClass } from './dom-utils.js';

/**
 * 通知类型
 */
export const NotificationType = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
};

/**
 * 通知位置
 */
export const NotificationPosition = {
  TOP_LEFT: 'top-left',
  TOP_CENTER: 'top-center',
  TOP_RIGHT: 'top-right',
  BOTTOM_LEFT: 'bottom-left',
  BOTTOM_CENTER: 'bottom-center',
  BOTTOM_RIGHT: 'bottom-right',
};

/**
 * 活动的通知列表
 */
const activeNotifications = new Map();

/**
 * 通知 ID 计数器
 */
let notificationIdCounter = 0;

/**
 * 显示 Toast 通知
 * @param {string} message - 消息内容
 * @param {Object} options - 配置选项
 * @returns {string} 通知 ID
 */
export function showToast(message, options = {}) {
  const {
    type = NotificationType.INFO,
    duration = 3200,
    position = NotificationPosition.BOTTOM_CENTER,
    closable = false,
  } = options;

  const id = `toast-${notificationIdCounter++}`;

  // 创建 Toast 元素
  const toast = createElement('div', {
    className: `toast toast-${type}`,
    attributes: {
      id,
      role: 'status',
      'aria-live': type === NotificationType.ERROR ? 'assertive' : 'polite',
    },
  });

  // 消息内容
  const content = createElement('span', {
    className: 'toast-content',
    textContent: message,
  });
  toast.appendChild(content);

  // 关闭按钮
  if (closable) {
    const closeButton = createElement('button', {
      className: 'toast-close',
      textContent: '×',
      attributes: {
        type: 'button',
        'aria-label': '关闭',
      },
    });
    closeButton.addEventListener('click', () => hideToast(id));
    toast.appendChild(closeButton);
  }

  // 设置位置样式
  applyPositionStyles(toast, position);

  // 添加到 DOM
  document.body.appendChild(toast);

  // 触发动画
  setTimeout(() => removeClass(toast, 'hidden'), 10);

  // 自动关闭
  if (duration > 0) {
    const timer = setTimeout(() => hideToast(id), duration);
    activeNotifications.set(id, { element: toast, timer });
  } else {
    activeNotifications.set(id, { element: toast, timer: null });
  }

  return id;
}

/**
 * 隐藏 Toast 通知
 * @param {string} id - 通知 ID
 */
export function hideToast(id) {
  const notification = activeNotifications.get(id);
  if (!notification) return;

  const { element, timer } = notification;

  // 清除定时器
  if (timer) {
    clearTimeout(timer);
  }

  // 添加隐藏动画
  addClass(element, 'toast-hiding');

  // 移除元素
  setTimeout(() => {
    element.remove();
    activeNotifications.delete(id);
  }, 300);
}

/**
 * 显示 Alert 对话框
 * @param {string} message - 消息内容
 * @param {Object} options - 配置选项
 * @returns {Promise<void>}
 */
export function showAlert(message, options = {}) {
  const {
    title = '提示',
    type = NotificationType.INFO,
    confirmText = '确定',
  } = options;

  return new Promise((resolve) => {
    const id = `alert-${notificationIdCounter++}`;
    const overlay = createOverlay(id);
    let settled = false;

    const settle = () => {
      if (settled) return;
      settled = true;
      closeDialog(overlay);
      resolve();
    };

    overlay.addEventListener('close', settle, { once: true });

    const dialog = createElement('div', {
      className: `alert-dialog alert-${type}`,
      attributes: {
        role: 'alertdialog',
        'aria-labelledby': `${id}-title`,
        'aria-describedby': `${id}-message`,
      },
    });

    const titleElement = createElement('h3', {
      className: 'alert-title',
      textContent: title,
      attributes: {
        id: `${id}-title`,
      },
    });
    dialog.appendChild(titleElement);

    const messageElement = createElement('p', {
      className: 'alert-message',
      textContent: message,
      attributes: {
        id: `${id}-message`,
      },
    });
    dialog.appendChild(messageElement);

    const actions = createElement('div', {
      className: 'alert-actions',
    });

    const confirmButton = createElement('button', {
      className: 'primary-button',
      textContent: confirmText,
      attributes: {
        type: 'button',
      },
    });
    confirmButton.addEventListener('click', settle);
    actions.appendChild(confirmButton);

    dialog.appendChild(actions);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    setTimeout(() => confirmButton.focus(), 100);
  });
}

/**
 * 显示 Confirm 对话框
 * @param {string} message - 消息内容
 * @param {Object} options - 配置选项
 * @returns {Promise<boolean>} 用户是否确认
 */
export function showConfirm(message, options = {}) {
  const {
    title = '确认',
    type = NotificationType.WARNING,
    confirmText = '确定',
    cancelText = '取消',
  } = options;

  return new Promise((resolve) => {
    const id = `confirm-${notificationIdCounter++}`;
    const overlay = createOverlay(id);
    let settled = false;

    const settle = (result) => {
      if (settled) return;
      settled = true;
      document.removeEventListener('keydown', handleEscape);
      closeDialog(overlay);
      resolve(result);
    };

    const handleEscape = (event) => {
      if (event.key === 'Escape' && overlay === document.body.lastElementChild) {
        settle(false);
      }
    };

    overlay.addEventListener('close', () => settle(false), { once: true });

    const dialog = createElement('div', {
      className: `confirm-dialog confirm-${type}`,
      attributes: {
        role: 'alertdialog',
        'aria-labelledby': `${id}-title`,
        'aria-describedby': `${id}-message`,
      },
    });

    const titleElement = createElement('h3', {
      className: 'confirm-title',
      textContent: title,
      attributes: {
        id: `${id}-title`,
      },
    });
    dialog.appendChild(titleElement);

    const messageElement = createElement('p', {
      className: 'confirm-message',
      textContent: message,
      attributes: {
        id: `${id}-message`,
      },
    });
    dialog.appendChild(messageElement);

    const actions = createElement('div', {
      className: 'confirm-actions',
    });

    const cancelButton = createElement('button', {
      className: 'ghost-button',
      textContent: cancelText,
      attributes: {
        type: 'button',
      },
    });
    cancelButton.addEventListener('click', () => settle(false));
    actions.appendChild(cancelButton);

    const confirmButton = createElement('button', {
      className: 'primary-button',
      textContent: confirmText,
      attributes: {
        type: 'button',
      },
    });
    confirmButton.addEventListener('click', () => settle(true));
    actions.appendChild(confirmButton);

    dialog.appendChild(actions);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    setTimeout(() => cancelButton.focus(), 100);
    document.addEventListener('keydown', handleEscape);
  });
}

/**
 * 创建遮罩层
 * @private
 * @param {string} id - 对话框 ID
 * @returns {Element} 遮罩层元素
 */
function createOverlay(id) {
  const overlay = createElement('div', {
    className: 'dialog-overlay',
    attributes: {
      id: `${id}-overlay`,
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
    z-index: 9999;
    backdrop-filter: blur(4px);
    animation: fadeIn 0.2s ease-out;
  `;

  return overlay;
}

/**
 * 关闭对话框
 * @private
 * @param {Element} overlay - 遮罩层元素
 */
function closeDialog(overlay) {
  addClass(overlay, 'dialog-closing');
  setTimeout(() => overlay.remove(), 200);
}

/**
 * 应用位置样式
 * @private
 * @param {Element} element - 元素
 * @param {string} position - 位置
 */
function applyPositionStyles(element, position) {
  const styles = {
    [NotificationPosition.TOP_LEFT]: 'top: 24px; left: 24px;',
    [NotificationPosition.TOP_CENTER]: 'top: 24px; left: 50%; transform: translateX(-50%);',
    [NotificationPosition.TOP_RIGHT]: 'top: 24px; right: 24px;',
    [NotificationPosition.BOTTOM_LEFT]: 'bottom: 24px; left: 24px;',
    [NotificationPosition.BOTTOM_CENTER]: 'bottom: 24px; left: 50%; transform: translateX(-50%);',
    [NotificationPosition.BOTTOM_RIGHT]: 'bottom: 24px; right: 24px;',
  };

  element.style.cssText += styles[position] || styles[NotificationPosition.BOTTOM_CENTER];
}

/**
 * 清除所有通知
 */
export function clearAllNotifications() {
  activeNotifications.forEach((notification, id) => {
    hideToast(id);
  });
}
