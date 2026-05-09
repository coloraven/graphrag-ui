/**
 * 统一状态管理模块
 * 提供响应式状态管理、状态持久化、状态订阅
 */

/**
 * 状态管理器类
 */
class StateManager {
  constructor(initialState = {}) {
    this._state = { ...initialState };
    this._listeners = new Map();
    this._history = [];
    this._maxHistorySize = 50;
  }

  /**
   * 获取状态值
   * @param {string} key - 状态键
   * @returns {*} 状态值
   */
  get(key) {
    return this._state[key];
  }

  /**
   * 设置状态值
   * @param {string} key - 状态键
   * @param {*} value - 状态值
   * @param {boolean} notify - 是否通知订阅者
   */
  set(key, value, notify = true) {
    const oldValue = this._state[key];

    // 值未变化则不更新
    if (oldValue === value) return;

    // 记录历史
    this._recordHistory(key, oldValue, value);

    // 更新状态
    this._state[key] = value;

    // 通知订阅者
    if (notify) {
      this._notifyListeners(key, value, oldValue);
    }
  }

  /**
   * 批量设置状态
   * @param {Object} updates - 状态更新对象
   */
  setMultiple(updates) {
    Object.entries(updates).forEach(([key, value]) => {
      this.set(key, value, false);
    });

    // 批量通知
    Object.keys(updates).forEach(key => {
      this._notifyListeners(key, this._state[key]);
    });
  }

  /**
   * 订阅状态变化
   * @param {string} key - 状态键
   * @param {Function} callback - 回调函数
   * @returns {Function} 取消订阅函数
   */
  subscribe(key, callback) {
    if (!this._listeners.has(key)) {
      this._listeners.set(key, new Set());
    }

    this._listeners.get(key).add(callback);

    // 返回取消订阅函数
    return () => {
      const listeners = this._listeners.get(key);
      if (listeners) {
        listeners.delete(callback);
      }
    };
  }

  /**
   * 通知订阅者
   * @private
   */
  _notifyListeners(key, newValue, oldValue) {
    const listeners = this._listeners.get(key);
    if (!listeners) return;

    listeners.forEach(callback => {
      try {
        callback(newValue, oldValue);
      } catch (error) {
        console.error(`Error in state listener for "${key}":`, error);
      }
    });
  }

  /**
   * 记录状态历史
   * @private
   */
  _recordHistory(key, oldValue, newValue) {
    this._history.push({
      key,
      oldValue,
      newValue,
      timestamp: Date.now(),
    });

    // 限制历史记录大小
    if (this._history.length > this._maxHistorySize) {
      this._history.shift();
    }
  }

  /**
   * 获取状态历史
   * @param {string} key - 状态键（可选）
   * @returns {Array} 历史记录
   */
  getHistory(key = null) {
    if (key) {
      return this._history.filter(record => record.key === key);
    }
    return [...this._history];
  }

  /**
   * 清空状态历史
   */
  clearHistory() {
    this._history = [];
  }

  /**
   * 重置状态
   * @param {Object} newState - 新状态
   */
  reset(newState = {}) {
    this._state = { ...newState };
    this._listeners.clear();
    this._history = [];
  }

  /**
   * 获取所有状态
   * @returns {Object} 状态对象
   */
  getAll() {
    return { ...this._state };
  }
}

/**
 * 全局应用状态
 */
export const appState = new StateManager({
  // UI 状态
  busy: false,
  currentPage: 'workspace',

  // 定时器
  progressTimer: null,
  resetTimer: null,
  toastTimer: null,
  indexPollTimer: null,

  // 选中项
  selectedTaskId: null,
  selectedDocumentName: null,

  // 数据状态
  healthStatus: null,
  indexStatus: null,
  documents: [],
  interactions: [],
  indexTasks: [],

  // 当前任务
  currentQuestion: '',
  currentAnswer: null,
  currentSources: [],

  // 加载状态
  isLoadingHealth: false,
  isLoadingIndex: false,
  isLoadingDocuments: false,
  isLoadingQuestion: false,
});

const STORAGE_KEY_PREFIX = 'reggraph-assistant:';

function buildStorageKey(key) {
  return `${STORAGE_KEY_PREFIX}${key}`;
}

/**
 * 状态持久化工具
 */
export const StatePersistence = {
  /**
   * 保存状态到 localStorage
   * @param {string} key - 存储键
   * @param {*} value - 状态值
   */
  save(key, value) {
    try {
      const serialized = JSON.stringify(value);
      localStorage.setItem(buildStorageKey(key), serialized);
    } catch (error) {
      console.error('Failed to save state:', error);
    }
  },

  /**
   * 从 localStorage 加载状态
   * @param {string} key - 存储键
   * @param {*} defaultValue - 默认值
   * @returns {*} 状态值
   */
  load(key, defaultValue = null) {
    try {
      const serialized = localStorage.getItem(buildStorageKey(key));
      return serialized ? JSON.parse(serialized) : defaultValue;
    } catch (error) {
      console.error('Failed to load state:', error);
      return defaultValue;
    }
  },

  /**
   * 删除状态
   * @param {string} key - 存储键
   */
  remove(key) {
    try {
      localStorage.removeItem(buildStorageKey(key));
    } catch (error) {
      console.error('Failed to remove state:', error);
    }
  },

  /**
   * 清空项目状态
   */
  clear() {
    try {
      const scopedKeys = [];
      for (let index = 0; index < localStorage.length; index += 1) {
        const key = localStorage.key(index);
        if (key && key.startsWith(STORAGE_KEY_PREFIX)) {
          scopedKeys.push(key);
        }
      }
      scopedKeys.forEach((key) => localStorage.removeItem(key));
    } catch (error) {
      console.error('Failed to clear state:', error);
    }
  },
};

/**
 * 创建计算属性
 * @param {Function} getter - 计算函数
 * @param {Array<string>} dependencies - 依赖的状态键
 * @returns {Function} 获取计算值的函数
 */
export function createComputed(getter, dependencies = []) {
  let cachedValue = null;
  let isDirty = true;

  // 订阅依赖的状态变化
  dependencies.forEach(key => {
    appState.subscribe(key, () => {
      isDirty = true;
    });
  });

  return () => {
    if (isDirty) {
      cachedValue = getter();
      isDirty = false;
    }
    return cachedValue;
  };
}

/**
 * 创建状态观察器
 * @param {string} key - 状态键
 * @param {Function} callback - 回调函数
 * @param {Object} options - 选项
 * @returns {Function} 取消观察函数
 */
export function watch(key, callback, options = {}) {
  const { immediate = false } = options;

  // 立即执行一次
  if (immediate) {
    callback(appState.get(key), undefined);
  }

  // 订阅状态变化
  return appState.subscribe(key, callback);
}
