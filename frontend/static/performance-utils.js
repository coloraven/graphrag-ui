/**
 * 前端性能优化工具
 * 提供性能监控、懒加载、缓存管理、资源优化
 */

/**
 * 性能监控器
 */
export class PerformanceMonitor {
  constructor() {
    this.marks = new Map();
    this.measures = new Map();
  }

  /**
   * 标记性能时间点
   * @param {string} name - 标记名称
   */
  mark(name) {
    if (window.performance && window.performance.mark) {
      window.performance.mark(name);
      this.marks.set(name, performance.now());
    }
  }

  /**
   * 测量两个时间点之间的性能
   * @param {string} name - 测量名称
   * @param {string} startMark - 开始标记
   * @param {string} endMark - 结束标记
   * @returns {number} 耗时（毫秒）
   */
  measure(name, startMark, endMark) {
    if (window.performance && window.performance.measure) {
      try {
        window.performance.measure(name, startMark, endMark);
        const measure = window.performance.getEntriesByName(name)[0];
        const duration = measure ? measure.duration : 0;
        this.measures.set(name, duration);
        return duration;
      } catch (error) {
        console.warn('Performance measure failed:', error);
        return 0;
      }
    }
    return 0;
  }

  /**
   * 获取页面加载性能指标
   * @returns {Object} 性能指标
   */
  getPageLoadMetrics() {
    if (!window.performance || !window.performance.timing) {
      return null;
    }

    const timing = window.performance.timing;
    const navigation = window.performance.navigation;

    return {
      // DNS 查询时间
      dnsTime: timing.domainLookupEnd - timing.domainLookupStart,
      // TCP 连接时间
      tcpTime: timing.connectEnd - timing.connectStart,
      // 请求时间
      requestTime: timing.responseEnd - timing.requestStart,
      // 响应时间
      responseTime: timing.responseEnd - timing.responseStart,
      // DOM 解析时间
      domParseTime: timing.domInteractive - timing.domLoading,
      // DOM 内容加载完成时间
      domContentLoadedTime: timing.domContentLoadedEventEnd - timing.navigationStart,
      // 页面完全加载时间
      loadTime: timing.loadEventEnd - timing.navigationStart,
      // 首次渲染时间
      firstPaintTime: this.getFirstPaintTime(),
      // 导航类型
      navigationType: navigation.type,
      // 重定向次数
      redirectCount: navigation.redirectCount,
    };
  }

  /**
   * 获取首次渲染时间
   * @private
   * @returns {number} 首次渲染时间（毫秒）
   */
  getFirstPaintTime() {
    if (window.performance && window.performance.getEntriesByType) {
      const paintEntries = window.performance.getEntriesByType('paint');
      const firstPaint = paintEntries.find(entry => entry.name === 'first-paint');
      return firstPaint ? firstPaint.startTime : 0;
    }
    return 0;
  }

  /**
   * 记录性能日志
   */
  logPerformance() {
    const metrics = this.getPageLoadMetrics();
    if (!metrics) return;

    console.group('📊 Performance Metrics');
    console.log('DNS Time:', `${metrics.dnsTime}ms`);
    console.log('TCP Time:', `${metrics.tcpTime}ms`);
    console.log('Request Time:', `${metrics.requestTime}ms`);
    console.log('DOM Parse Time:', `${metrics.domParseTime}ms`);
    console.log('DOM Content Loaded:', `${metrics.domContentLoadedTime}ms`);
    console.log('Page Load Time:', `${metrics.loadTime}ms`);
    console.log('First Paint:', `${metrics.firstPaintTime}ms`);
    console.groupEnd();
  }

  /**
   * 清除性能标记
   */
  clearMarks() {
    if (window.performance && window.performance.clearMarks) {
      window.performance.clearMarks();
    }
    this.marks.clear();
    this.measures.clear();
  }
}

/**
 * 全局性能监控器实例
 */
export const performanceMonitor = new PerformanceMonitor();

/**
 * 懒加载管理器
 */
export class LazyLoadManager {
  constructor(options = {}) {
    this.options = {
      rootMargin: '50px',
      threshold: 0.01,
      ...options,
    };

    this.observer = null;
    this.elements = new Set();

    this.init();
  }

  /**
   * 初始化 Intersection Observer
   */
  init() {
    if (!('IntersectionObserver' in window)) {
      console.warn('IntersectionObserver not supported');
      return;
    }

    this.observer = new IntersectionObserver(
      (entries) => this.handleIntersection(entries),
      this.options
    );
  }

  /**
   * 处理元素交叉
   * @private
   */
  handleIntersection(entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const element = entry.target;
        this.loadElement(element);
        this.observer.unobserve(element);
        this.elements.delete(element);
      }
    });
  }

  /**
   * 加载元素
   * @private
   */
  loadElement(element) {
    // 加载图片
    if (element.tagName === 'IMG' && element.dataset.src) {
      element.src = element.dataset.src;
      element.removeAttribute('data-src');
    }

    // 加载背景图
    if (element.dataset.bgSrc) {
      element.style.backgroundImage = `url(${element.dataset.bgSrc})`;
      element.removeAttribute('data-bg-src');
    }

    // 触发自定义加载事件
    if (element.dataset.lazyLoad) {
      const event = new CustomEvent('lazyload', { detail: { element } });
      element.dispatchEvent(event);
    }
  }

  /**
   * 观察元素
   * @param {Element} element - 要观察的元素
   */
  observe(element) {
    if (!this.observer || !element) return;

    this.elements.add(element);
    this.observer.observe(element);
  }

  /**
   * 取消观察元素
   * @param {Element} element - 要取消观察的元素
   */
  unobserve(element) {
    if (!this.observer || !element) return;

    this.elements.delete(element);
    this.observer.unobserve(element);
  }

  /**
   * 销毁懒加载管理器
   */
  destroy() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    this.elements.clear();
  }
}

/**
 * 全局懒加载管理器实例
 */
export const lazyLoadManager = new LazyLoadManager();

/**
 * 缓存管理器
 */
export class CacheManager {
  constructor(options = {}) {
    this.options = {
      maxSize: 50, // 最大缓存条目数
      maxAge: 5 * 60 * 1000, // 最大缓存时间（5分钟）
      ...options,
    };

    this.cache = new Map();
  }

  /**
   * 设置缓存
   * @param {string} key - 缓存键
   * @param {*} value - 缓存值
   * @param {number} maxAge - 最大缓存时间（可选）
   */
  set(key, value, maxAge = this.options.maxAge) {
    // 检查缓存大小
    if (this.cache.size >= this.options.maxSize) {
      // 删除最旧的条目
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }

    this.cache.set(key, {
      value,
      timestamp: Date.now(),
      maxAge,
    });
  }

  /**
   * 获取缓存
   * @param {string} key - 缓存键
   * @returns {*} 缓存值，如果不存在或已过期则返回 null
   */
  get(key) {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    // 检查是否过期
    const age = Date.now() - entry.timestamp;
    if (age > entry.maxAge) {
      this.cache.delete(key);
      return null;
    }

    return entry.value;
  }

  /**
   * 检查缓存是否存在
   * @param {string} key - 缓存键
   * @returns {boolean} 是否存在
   */
  has(key) {
    return this.get(key) !== null;
  }

  /**
   * 删除缓存
   * @param {string} key - 缓存键
   */
  delete(key) {
    this.cache.delete(key);
  }

  /**
   * 清空缓存
   */
  clear() {
    this.cache.clear();
  }

  /**
   * 获取缓存大小
   * @returns {number} 缓存条目数
   */
  size() {
    return this.cache.size;
  }

  /**
   * 清理过期缓存
   */
  cleanup() {
    const now = Date.now();
    const keysToDelete = [];

    this.cache.forEach((entry, key) => {
      const age = now - entry.timestamp;
      if (age > entry.maxAge) {
        keysToDelete.push(key);
      }
    });

    keysToDelete.forEach(key => this.cache.delete(key));
  }
}

/**
 * 全局缓存管理器实例
 */
export const cacheManager = new CacheManager();

/**
 * 资源预加载
 * @param {string} url - 资源 URL
 * @param {string} as - 资源类型（'script' | 'style' | 'image' | 'fetch'）
 */
export function preloadResource(url, as = 'fetch') {
  const link = document.createElement('link');
  link.rel = 'preload';
  link.href = url;
  link.as = as;

  if (as === 'fetch') {
    link.crossOrigin = 'anonymous';
  }

  document.head.appendChild(link);
}

/**
 * 资源预连接
 * @param {string} url - 资源 URL
 */
export function preconnect(url) {
  const link = document.createElement('link');
  link.rel = 'preconnect';
  link.href = url;
  document.head.appendChild(link);
}

/**
 * 批量 DOM 更新
 * @param {Function} callback - 更新回调函数
 */
export function batchDOMUpdate(callback) {
  if (window.requestAnimationFrame) {
    window.requestAnimationFrame(callback);
  } else {
    setTimeout(callback, 16); // ~60fps
  }
}

/**
 * 虚拟滚动
 */
export class VirtualScroller {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      itemHeight: 50,
      bufferSize: 5,
      ...options,
    };

    this.items = [];
    this.visibleItems = [];
    this.scrollTop = 0;

    this.init();
  }

  /**
   * 初始化
   */
  init() {
    this.container.style.position = 'relative';
    this.container.style.overflow = 'auto';

    this.container.addEventListener('scroll', () => {
      this.scrollTop = this.container.scrollTop;
      this.render();
    });
  }

  /**
   * 设置数据
   * @param {Array} items - 数据数组
   */
  setItems(items) {
    this.items = items;
    this.render();
  }

  /**
   * 渲染可见项
   */
  render() {
    const { itemHeight, bufferSize } = this.options;
    const containerHeight = this.container.clientHeight;

    // 计算可见范围
    const startIndex = Math.max(0, Math.floor(this.scrollTop / itemHeight) - bufferSize);
    const endIndex = Math.min(
      this.items.length,
      Math.ceil((this.scrollTop + containerHeight) / itemHeight) + bufferSize
    );

    // 更新可见项
    this.visibleItems = this.items.slice(startIndex, endIndex);

    // 触发渲染事件
    const event = new CustomEvent('render', {
      detail: {
        visibleItems: this.visibleItems,
        startIndex,
        endIndex,
      },
    });
    this.container.dispatchEvent(event);
  }
}

/**
 * 图片懒加载
 * @param {string} selector - 图片选择器
 */
export function lazyLoadImages(selector = 'img[data-src]') {
  const images = document.querySelectorAll(selector);
  images.forEach(img => lazyLoadManager.observe(img));
}

/**
 * 初始化性能监控
 */
export function initPerformanceMonitoring() {
  // 页面加载完成后记录性能
  if (document.readyState === 'complete') {
    performanceMonitor.logPerformance();
  } else {
    window.addEventListener('load', () => {
      performanceMonitor.logPerformance();
    });
  }

  // 定期清理缓存
  setInterval(() => {
    cacheManager.cleanup();
  }, 60000); // 每分钟清理一次
}
