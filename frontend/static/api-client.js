import { encodeQuery, requestJson } from './core.js';

export const apiClient = {
  getHealth() {
    return requestJson('/api/health');
  },
  getIndexStatus() {
    return requestJson('/api/index/status');
  },
  getCurrentIndexTask() {
    return requestJson('/api/index/task');
  },
  getLatestIndexTask() {
    return requestJson('/api/index/task/latest');
  },
  getIndexTask(taskId) {
    return requestJson(`/api/index/task/${encodeQuery(taskId)}`);
  },
  listIndexTasks(limit = 8) {
    return requestJson(`/api/history/index-tasks?limit=${limit}`);
  },
  listInteractions(limit = 8) {
    return requestJson(`/api/history/interactions?limit=${limit}`);
  },
  listDocuments() {
    return requestJson('/api/documents');
  },
  uploadDocument(filename, file) {
    return requestJson(`/api/documents/upload?filename=${encodeQuery(filename)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: file,
    });
  },
  previewDocument(filename) {
    return requestJson(`/api/documents/preview?filename=${encodeQuery(filename)}`);
  },
  rebuildIndex() {
    return requestJson('/api/index/rebuild', { method: 'POST' });
  },
  runWorkflow(task, submittedMaterials = [], context = '') {
    return requestJson('/api/workflow/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task, submitted_materials: submittedMaterials, context }),
    });
  },
};
