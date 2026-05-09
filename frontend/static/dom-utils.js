/**
 * DOM 工具函数模块
 * 提供常用的 DOM 操作、查询、事件处理工具
 */

/**
 * 查询单个元素
 * @param {string} selector - CSS 选择器
 * @param {Element} context - 查询上下文（默认为 document）
 * @returns {Element|null} DOM 元素
 */
export function $(selector, context = document) {
  return context.querySelector(selector);
}

/**
 * 查询多个元素
 * @param {string} selector - CSS 选择器
 * @param {Element} context - 查询上下文（默认为 document）
 * @returns {Array<Element>} DOM 元素数组
 */
export function $$(selector, context = document) {
  return Array.from(context.querySelectorAll(selector));
}

/**
 * 清空元素的所有子节点
 * @param {Element} node - DOM 元素
 */
export function clearChildren(node) {
  if (!node) return;
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

/**
 * 创建元素
 * @param {string} tag - 标签名
 * @param {Object} options - 选项
 * @param {string} options.className - 类名
 * @param {string} options.textContent - 文本内容
 * @param {Object} options.attributes - 属性对象
 * @param {Object} options.dataset - data-* 属性对象
 * @param {Array<Element>} options.children - 子元素数组
 * @returns {Element} 创建的元素
 */
export function createElement(tag, options = {}) {
  const element = document.createElement(tag);

  const {
    className = '',
    textContent = '',
    attributes = {},
    dataset = {},
    children = [],
  } = options;

  // 设置类名
  if (className) {
    element.className = className;
  }

  // 设置文本内容
  if (textContent) {
    element.textContent = textContent;
  }

  // 设置属性
  Object.entries(attributes).forEach(([key, value]) => {
    element.setAttribute(key, value);
  });

  // 设置 data-* 属性
  Object.entries(dataset).forEach(([key, value]) => {
    element.dataset[key] = value;
  });

  // 添加子元素
  children.forEach(child => {
    if (child) {
      element.appendChild(child);
    }
  });

  return element;
}

/**
 * 切换元素的类名
 * @param {Element} element - DOM 元素
 * @param {string} className - 类名
 * @param {boolean} force - 强制添加或移除
 */
export function toggleClass(element, className, force = undefined) {
  if (!element) return;
  element.classList.toggle(className, force);
}

/**
 * 添加类名
 * @param {Element} element - DOM 元素
 * @param {...string} classNames - 类名列表
 */
export function addClass(element, ...classNames) {
  if (!element) return;
  element.classList.add(...classNames);
}

/**
 * 移除类名
 * @param {Element} element - DOM 元素
 * @param {...string} classNames - 类名列表
 */
export function removeClass(element, ...classNames) {
  if (!element) return;
  element.classList.remove(...classNames);
}

/**
 * 显示元素
 * @param {Element} element - DOM 元素
 */
export function show(element) {
  if (!element) return;
  element.classList.remove('hidden');
}

/**
 * 隐藏元素
 * @param {Element} element - DOM 元素
 */
export function hide(element) {
  if (!element) return;
  element.classList.add('hidden');
}

/**
 * 切换元素显示/隐藏
 * @param {Element} element - DOM 元素
 * @param {boolean} visible - 是否显示
 */
export function toggleVisibility(element, visible = undefined) {
  if (!element) return;
  if (visible === undefined) {
    element.classList.toggle('hidden');
  } else {
    toggleClass(element, 'hidden', !visible);
  }
}

/**
 * 设置元素属性
 * @param {Element} element - DOM 元素
 * @param {Object} attributes - 属性对象
 */
export function setAttributes(element, attributes) {
  if (!element) return;
  Object.entries(attributes).forEach(([key, value]) => {
    if (value === null || value === undefined) {
      element.removeAttribute(key);
    } else {
      element.setAttribute(key, value);
    }
  });
}

/**
 * 添加事件监听器（支持事件委托）
 * @param {Element} element - DOM 元素
 * @param {string} eventType - 事件类型
 * @param {string|Function} selectorOrHandler - 选择器或处理函数
 * @param {Function} handler - 处理函数（当使用事件委托时）
 * @returns {Function} 移除监听器的函数
 */
export function on(element, eventType, selectorOrHandler, handler = null) {
  if (!element) return () => {};

  // 事件委托
  if (typeof selectorOrHandler === 'string' && handler) {
    const delegateHandler = (event) => {
      const target = event.target.closest(selectorOrHandler);
      if (target && element.contains(target)) {
        handler.call(target, event);
      }
    };

    element.addEventListener(eventType, delegateHandler);
    return () => element.removeEventListener(eventType, delegateHandler);
  }

  // 直接监听
  const directHandler = selectorOrHandler;
  element.addEventListener(eventType, directHandler);
  return () => element.removeEventListener(eventType, directHandler);
}

/**
 * 移除事件监听器
 * @param {Element} element - DOM 元素
 * @param {string} eventType - 事件类型
 * @param {Function} handler - 处理函数
 */
export function off(element, eventType, handler) {
  if (!element) return;
  element.removeEventListener(eventType, handler);
}

/**
 * 触发自定义事件
 * @param {Element} element - DOM 元素
 * @param {string} eventType - 事件类型
 * @param {*} detail - 事件详情
 */
export function trigger(element, eventType, detail = null) {
  if (!element) return;

  const event = new CustomEvent(eventType, {
    bubbles: true,
    cancelable: true,
    detail,
  });

  element.dispatchEvent(event);
}

/**
 * 获取元素的位置和尺寸
 * @param {Element} element - DOM 元素
 * @returns {Object} { top, left, width, height }
 */
export function getRect(element) {
  if (!element) return { top: 0, left: 0, width: 0, height: 0 };
  return element.getBoundingClientRect();
}

/**
 * 滚动到元素
 * @param {Element} element - DOM 元素
 * @param {Object} options - 滚动选项
 */
export function scrollToElement(element, options = {}) {
  if (!element) return;

  const defaultOptions = {
    behavior: 'smooth',
    block: 'start',
    inline: 'nearest',
  };

  element.scrollIntoView({ ...defaultOptions, ...options });
}

/**
 * 防抖函数
 * @param {Function} fn - 要防抖的函数
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {Function} 防抖后的函数
 */
export function debounce(fn, delay = 300) {
  let timer = null;

  return function(...args) {
    if (timer) clearTimeout(timer);

    timer = setTimeout(() => {
      fn.apply(this, args);
      timer = null;
    }, delay);
  };
}

/**
 * 节流函数
 * @param {Function} fn - 要节流的函数
 * @param {number} delay - 延迟时间（毫秒）
 * @returns {Function} 节流后的函数
 */
export function throttle(fn, delay = 300) {
  let lastTime = 0;

  return function(...args) {
    const now = Date.now();

    if (now - lastTime >= delay) {
      fn.apply(this, args);
      lastTime = now;
    }
  };
}

/**
 * 等待 DOM 加载完成
 * @returns {Promise<void>}
 */
export function ready() {
  return new Promise(resolve => {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', resolve, { once: true });
    } else {
      resolve();
    }
  });
}

/**
 * Parse HTML into a document fragment without sanitizing it.
 * @param {string} html - HTML string
 * @returns {DocumentFragment} Document fragment
 */
export function parseHTML(html) {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  return template.content;
}
