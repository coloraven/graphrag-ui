/**
 * 可访问性工具模块
 * 提供键盘导航、屏幕阅读器支持、焦点管理、ARIA 属性管理
 */

import { $, $$, on, off, addClass, removeClass } from './dom-utils.js';

/**
 * 键盘导航管理器
 */
export class KeyboardNavigationManager {
  constructor() {
    this.focusableElements = [];
    this.currentIndex = -1;
    this.trapFocus = false;
    this.trapContainer = null;
  }

  /**
   * 初始化键盘导航
   * @param {string} selector - 可聚焦元素选择器
   */
  init(selector = 'button, a, input, textarea, select, [tabindex]:not([tabindex="-1"])') {
    this.focusableElements = $$(selector).filter(el => !el.disabled && el.offsetParent !== null);
    this.currentIndex = this.focusableElements.findIndex(el => el === document.activeElement);
  }

  /**
   * 聚焦到下一个元素
   */
  focusNext() {
    if (this.focusableElements.length === 0) return;

    this.currentIndex = (this.currentIndex + 1) % this.focusableElements.length;
    this.focusableElements[this.currentIndex].focus();
  }

  /**
   * 聚焦到上一个元素
   */
  focusPrevious() {
    if (this.focusableElements.length === 0) return;

    this.currentIndex = (this.currentIndex - 1 + this.focusableElements.length) % this.focusableElements.length;
    this.focusableElements[this.currentIndex].focus();
  }

  /**
   * 聚焦到第一个元素
   */
  focusFirst() {
    if (this.focusableElements.length === 0) return;

    this.currentIndex = 0;
    this.focusableElements[0].focus();
  }

  /**
   * 聚焦到最后一个元素
   */
  focusLast() {
    if (this.focusableElements.length === 0) return;

    this.currentIndex = this.focusableElements.length - 1;
    this.focusableElements[this.currentIndex].focus();
  }

  /**
   * 启用焦点陷阱
   * @param {Element} container - 容器元素
   */
  enableFocusTrap(container) {
    this.trapFocus = true;
    this.trapContainer = container;

    const focusableInContainer = $$(
      'button, a, input, textarea, select, [tabindex]:not([tabindex="-1"])',
      container
    ).filter(el => !el.disabled && el.offsetParent !== null);

    if (focusableInContainer.length > 0) {
      focusableInContainer[0].focus();
    }

    this.handleFocusTrap = (event) => {
      if (event.key === 'Tab') {
        const firstElement = focusableInContainer[0];
        const lastElement = focusableInContainer[focusableInContainer.length - 1];

        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };

    container.addEventListener('keydown', this.handleFocusTrap);
  }

  /**
   * 禁用焦点陷阱
   */
  disableFocusTrap() {
    this.trapFocus = false;

    if (this.trapContainer && this.handleFocusTrap) {
      this.trapContainer.removeEventListener('keydown', this.handleFocusTrap);
    }

    this.trapContainer = null;
    this.handleFocusTrap = null;
  }
}

/**
 * 全局键盘导航管理器实例
 */
export const keyboardNav = new KeyboardNavigationManager();

/**
 * 屏幕阅读器公告
 * @param {string} message - 公告消息
 * @param {string} priority - 优先级（'polite' | 'assertive'）
 */
export function announceToScreenReader(message, priority = 'polite') {
  let announcer = $('#sr-announcer');

  if (!announcer) {
    announcer = document.createElement('div');
    announcer.id = 'sr-announcer';
    announcer.className = 'sr-only';
    announcer.setAttribute('role', 'status');
    announcer.setAttribute('aria-live', priority);
    announcer.setAttribute('aria-atomic', 'true');
    document.body.appendChild(announcer);
  }

  // 更新优先级
  announcer.setAttribute('aria-live', priority);

  // 清空后设置消息（触发屏幕阅读器）
  announcer.textContent = '';
  setTimeout(() => {
    announcer.textContent = message;
  }, 100);
}

/**
 * ARIA 属性管理器
 */
export class AriaManager {
  /**
   * 设置 ARIA 标签
   * @param {Element} element - 元素
   * @param {string} label - 标签文本
   */
  static setLabel(element, label) {
    if (!element) return;
    element.setAttribute('aria-label', label);
  }

  /**
   * 设置 ARIA 描述
   * @param {Element} element - 元素
   * @param {string} description - 描述文本
   */
  static setDescription(element, description) {
    if (!element) return;

    // 创建描述元素
    const descId = `desc-${Date.now()}`;
    const descElement = document.createElement('span');
    descElement.id = descId;
    descElement.className = 'sr-only';
    descElement.textContent = description;

    element.parentNode.insertBefore(descElement, element.nextSibling);
    element.setAttribute('aria-describedby', descId);
  }

  /**
   * 设置展开/折叠状态
   * @param {Element} element - 元素
   * @param {boolean} expanded - 是否展开
   */
  static setExpanded(element, expanded) {
    if (!element) return;
    element.setAttribute('aria-expanded', String(expanded));
  }

  /**
   * 设置选中状态
   * @param {Element} element - 元素
   * @param {boolean} selected - 是否选中
   */
  static setSelected(element, selected) {
    if (!element) return;
    element.setAttribute('aria-selected', String(selected));
  }

  /**
   * 设置禁用状态
   * @param {Element} element - 元素
   * @param {boolean} disabled - 是否禁用
   */
  static setDisabled(element, disabled) {
    if (!element) return;
    element.setAttribute('aria-disabled', String(disabled));

    if (disabled) {
      element.setAttribute('tabindex', '-1');
    } else {
      element.removeAttribute('tabindex');
    }
  }

  /**
   * 设置忙碌状态
   * @param {Element} element - 元素
   * @param {boolean} busy - 是否忙碌
   */
  static setBusy(element, busy) {
    if (!element) return;
    element.setAttribute('aria-busy', String(busy));
  }

  /**
   * 设置当前项
   * @param {Element} element - 元素
   * @param {string} current - 当前类型（'page' | 'step' | 'location' | 'date' | 'time' | 'true'）
   */
  static setCurrent(element, current = 'true') {
    if (!element) return;
    element.setAttribute('aria-current', current);
  }

  /**
   * 设置无效状态
   * @param {Element} element - 元素
   * @param {boolean} invalid - 是否无效
   * @param {string} errorMessage - 错误消息
   */
  static setInvalid(element, invalid, errorMessage = '') {
    if (!element) return;

    element.setAttribute('aria-invalid', String(invalid));

    if (invalid && errorMessage) {
      const errorId = `error-${Date.now()}`;
      const errorElement = document.createElement('span');
      errorElement.id = errorId;
      errorElement.className = 'error-message';
      errorElement.textContent = errorMessage;
      errorElement.setAttribute('role', 'alert');

      element.parentNode.insertBefore(errorElement, element.nextSibling);
      element.setAttribute('aria-describedby', errorId);
    } else {
      // 移除错误消息
      const errorId = element.getAttribute('aria-describedby');
      if (errorId) {
        const errorElement = $(`#${errorId}`);
        if (errorElement && errorElement.classList.contains('error-message')) {
          errorElement.remove();
          element.removeAttribute('aria-describedby');
        }
      }
    }
  }
}

/**
 * 焦点管理器
 */
export class FocusManager {
  constructor() {
    this.focusHistory = [];
  }

  /**
   * 保存当前焦点
   */
  saveFocus() {
    const activeElement = document.activeElement;
    if (activeElement && activeElement !== document.body) {
      this.focusHistory.push(activeElement);
    }
  }

  /**
   * 恢复焦点
   */
  restoreFocus() {
    const element = this.focusHistory.pop();
    if (element && element.offsetParent !== null) {
      element.focus();
    }
  }

  /**
   * 清除焦点历史
   */
  clearHistory() {
    this.focusHistory = [];
  }

  /**
   * 设置焦点到元素
   * @param {Element} element - 元素
   * @param {Object} options - 选项
   */
  setFocus(element, options = {}) {
    if (!element) return;

    const { preventScroll = false, savePrevious = true } = options;

    if (savePrevious) {
      this.saveFocus();
    }

    element.focus({ preventScroll });
  }

  /**
   * 移除焦点
   */
  removeFocus() {
    if (document.activeElement) {
      document.activeElement.blur();
    }
  }
}

/**
 * 全局焦点管理器实例
 */
export const focusManager = new FocusManager();

/**
 * 跳过导航链接
 * @param {string} targetId - 目标元素 ID
 */
export function createSkipLink(targetId) {
  const skipLink = document.createElement('a');
  skipLink.href = `#${targetId}`;
  skipLink.className = 'skip-link';
  skipLink.textContent = '跳转到主内容';

  skipLink.addEventListener('click', (event) => {
    event.preventDefault();
    const target = $(`#${targetId}`);
    if (target) {
      target.setAttribute('tabindex', '-1');
      target.focus();
      target.addEventListener('blur', () => {
        target.removeAttribute('tabindex');
      }, { once: true });
    }
  });

  document.body.insertBefore(skipLink, document.body.firstChild);
}

/**
 * 初始化可访问性功能
 */
export function initAccessibility() {
  // 添加键盘导航支持
  document.addEventListener('keydown', (event) => {
    // Tab 键导航
    if (event.key === 'Tab') {
      keyboardNav.init();
    }

    // Escape 键关闭模态框
    if (event.key === 'Escape') {
      const modal = $('.dialog-overlay');
      if (modal) {
        modal.dispatchEvent(new CustomEvent('close'));
      }
    }
  });

  // 添加焦点可见性指示器
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Tab') {
      document.body.classList.add('keyboard-nav');
    }
  });

  document.addEventListener('mousedown', () => {
    document.body.classList.remove('keyboard-nav');
  });

  // 为所有按钮添加 ARIA 标签（如果缺失）
  $$('button:not([aria-label])').forEach(button => {
    const text = button.textContent.trim();
    if (text) {
      AriaManager.setLabel(button, text);
    }
  });
}

/**
 * 检查可访问性问题
 * @returns {Array} 问题列表
 */
export function checkAccessibility() {
  const issues = [];

  // 检查图片 alt 属性
  $$('img:not([alt])').forEach(img => {
    issues.push({
      type: 'missing-alt',
      element: img,
      message: '图片缺少 alt 属性',
    });
  });

  // 检查表单标签
  $$('input:not([aria-label]):not([aria-labelledby])').forEach(input => {
    const label = $(`label[for="${input.id}"]`);
    if (!label) {
      issues.push({
        type: 'missing-label',
        element: input,
        message: '表单控件缺少标签',
      });
    }
  });

  // 检查按钮文本
  $$('button:not([aria-label])').forEach(button => {
    if (!button.textContent.trim()) {
      issues.push({
        type: 'empty-button',
        element: button,
        message: '按钮缺少文本内容',
      });
    }
  });

  // 检查链接文本
  $$('a:not([aria-label])').forEach(link => {
    if (!link.textContent.trim()) {
      issues.push({
        type: 'empty-link',
        element: link,
        message: '链接缺少文本内容',
      });
    }
  });

  // 检查标题层级
  const headings = $$('h1, h2, h3, h4, h5, h6');
  let prevLevel = 0;
  headings.forEach(heading => {
    const level = parseInt(heading.tagName[1]);
    if (level - prevLevel > 1) {
      issues.push({
        type: 'heading-skip',
        element: heading,
        message: `标题层级跳跃：从 h${prevLevel} 到 h${level}`,
      });
    }
    prevLevel = level;
  });

  return issues;
}
