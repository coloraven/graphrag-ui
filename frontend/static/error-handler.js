/**
 * 统一错误处理模块
 * 提供错误分类、日志记录、用户友好提示
 */

import { showToast } from './core.js';

/**
 * 错误类型枚举
 */
export const ErrorType = {
  NETWORK: 'network',
  VALIDATION: 'validation',
  SERVER: 'server',
  UNKNOWN: 'unknown',
};

/**
 * 错误信息映射
 */
const ERROR_MESSAGES = {
  [ErrorType.NETWORK]: '网络连接失败，请检查网络后重试',
  [ErrorType.VALIDATION]: '输入验证失败，请检查输入内容',
  [ErrorType.SERVER]: '服务器错误，请稍后重试',
  [ErrorType.UNKNOWN]: '未知错误，请联系管理员',
};

/**
 * 分类错误类型
 * @param {Error} error - 错误对象
 * @returns {string} 错误类型
 */
function classifyError(error) {
  if (!error) return ErrorType.UNKNOWN;

  const message = error.message || '';

  if (message.includes('网络') || message.includes('fetch') || message.includes('Network')) {
    return ErrorType.NETWORK;
  }

  if (message.includes('验证') || message.includes('validation') || message.includes('invalid')) {
    return ErrorType.VALIDATION;
  }

  if (message.includes('服务') || message.includes('server') || message.includes('500')) {
    return ErrorType.SERVER;
  }

  return ErrorType.UNKNOWN;
}

/**
 * 获取用户友好的错误消息
 * @param {Error} error - 错误对象
 * @returns {string} 用户友好的错误消息
 */
function getUserFriendlyMessage(error) {
  if (!error) return ERROR_MESSAGES[ErrorType.UNKNOWN];

  // 如果错误消息已经是中文且友好，直接使用
  const message = error.message || '';
  if (message && /[一-龥]/.test(message) && message.length < 100) {
    return message;
  }

  // 否则使用分类后的默认消息
  const errorType = classifyError(error);
  return ERROR_MESSAGES[errorType];
}

/**
 * 记录错误到控制台（开发环境）
 * @param {Error} error - 错误对象
 * @param {Object} context - 错误上下文
 */
function logError(error, context = {}) {
  const isProduction = typeof process !== 'undefined'
    && process.env
    && process.env.NODE_ENV === 'production';
  if (isProduction) return;

  console.group('Error Details');
  console.error('Error:', error);
  console.log('Type:', classifyError(error));
  console.log('Context:', context);
  console.log('Stack:', error?.stack);
  console.groupEnd();
}

/**
 * 统一错误处理函数
 * @param {Error} error - 错误对象
 * @param {Object} options - 处理选项
 * @param {string} options.context - 错误上下文描述
 * @param {boolean} options.showToast - 是否显示 Toast 提示
 * @param {Function} options.onError - 自定义错误处理回调
 */
export function handleError(error, options = {}) {
  const {
    context = '',
    showToast: shouldShowToast = true,
    onError = null,
  } = options;

  // 记录错误
  logError(error, { context });

  // 获取用户友好消息
  const message = getUserFriendlyMessage(error);

  // 显示 Toast
  if (shouldShowToast) {
    showToast(message, 'error');
  }

  // 执行自定义回调
  if (typeof onError === 'function') {
    onError(error, message);
  }
}

/**
 * 异步函数错误包装器
 * @param {Function} fn - 异步函数
 * @param {Object} options - 错误处理选项
 * @returns {Function} 包装后的函数
 */
export function withErrorHandler(fn, options = {}) {
  return async function(...args) {
    try {
      return await fn(...args);
    } catch (error) {
      handleError(error, options);
      throw error; // 重新抛出以便调用者处理
    }
  };
}

/**
 * 验证输入
 * @param {string} value - 输入值
 * @param {Object} rules - 验证规则
 * @returns {Object} { valid: boolean, message: string }
 */
export function validateInput(value, rules = {}) {
  const {
    required = false,
    minLength = 0,
    maxLength = Infinity,
    pattern = null,
    customValidator = null,
  } = rules;

  // 必填验证
  if (required && !value?.trim()) {
    return { valid: false, message: '此字段为必填项' };
  }

  // 长度验证
  const length = value?.length || 0;
  if (length < minLength) {
    return { valid: false, message: `最少需要 ${minLength} 个字符` };
  }
  if (length > maxLength) {
    return { valid: false, message: `最多允许 ${maxLength} 个字符` };
  }

  // 正则验证
  if (pattern && !pattern.test(value)) {
    return { valid: false, message: '输入格式不正确' };
  }

  // 自定义验证
  if (typeof customValidator === 'function') {
    const result = customValidator(value);
    if (result !== true) {
      return { valid: false, message: result || '验证失败' };
    }
  }

  return { valid: true, message: '' };
}
