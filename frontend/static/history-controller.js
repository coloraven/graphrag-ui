import { apiClient } from './api-client.js';
import { showToast } from './core.js';
import { renderIndexHistory, renderInteractionHistory } from './dashboard.js';

export function createHistoryController({ onSelectTask }) {
  async function loadHistories() {
    try {
      const [interactionData, indexData] = await Promise.all([
        apiClient.listInteractions(8),
        apiClient.listIndexTasks(8),
      ]);
      renderInteractionHistory(interactionData.items);
      renderIndexHistory(indexData.items, onSelectTask);
    } catch (error) {
      renderInteractionHistory([]);
      renderIndexHistory([], onSelectTask);
      showToast(error.message || '历史记录加载失败', 'error');
    }
  }

  return { loadHistories };
}
