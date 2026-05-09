import { apiClient } from './api-client.js';
import { $, showToast } from './core.js';
import { resetHealthStatus, setHealthStatus, setMetricStatus } from './status-renderers.js';

export function createStatusController() {
  async function loadHealth() {
    try {
      const data = await apiClient.getHealth();
      setHealthStatus(data);
    } catch (error) {
      resetHealthStatus();
      showToast(error.message || '系统健康状态加载失败', 'error');
    }
  }

  async function loadStatus() {
    try {
      const data = await apiClient.getIndexStatus();
      setMetricStatus(data);
    } catch (error) {
      $('#metric-ready').textContent = '加载失败';
      $('#metric-count').textContent = '-';
      $('#metric-time').textContent = '-';
      showToast(error.message || '索引状态加载失败', 'error');
    }
  }

  return {
    loadHealth,
    loadStatus,
  };
}
