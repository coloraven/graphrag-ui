import { apiClient } from './api-client.js';
import { $, formatBytes, showToast } from './core.js';
import { renderDocumentRows } from './dashboard.js';

export function createDocumentController() {
  async function previewDocument(name) {
    try {
      const data = await apiClient.previewDocument(name);
      $('#document-preview-title').textContent = data.name || '文档预览';
      $('#document-preview-meta').textContent = `${data.type || '-'} · ${formatBytes(data.size || 0)} · ${data.character_count || 0} 字`;
      $('#document-preview-content').textContent = data.truncated
        ? `${data.content || ''}\n\n... 预览已截断`
        : (data.content || '暂无可预览文本。');
      $('#document-preview-panel').classList.remove('hidden');
    } catch (error) {
      showToast(error.message || '文档预览失败', 'error');
    }
  }

  async function loadDocuments() {
    try {
      const data = await apiClient.listDocuments();
      const items = Array.isArray(data.items) ? data.items : [];
      renderDocumentRows(items, previewDocument);
      $('#document-summary').textContent = `${items.length} 个文件`;
    } catch (error) {
      renderDocumentRows([], previewDocument);
      $('#document-summary').textContent = '加载失败';
      showToast(error.message || '资料列表加载失败', 'error');
    }
  }

  async function uploadDocument() {
    const input = $('#document-upload-input');
    const file = input.files?.[0];
    if (!file) {
      showToast('请先选择 txt、md 或 pdf 文件', 'error');
      return;
    }

    const button = $('#upload-document');
    button.disabled = true;
    button.textContent = '上传中';

    try {
      await apiClient.uploadDocument(file.name, file);
      input.value = '';
      await loadDocuments();
      showToast('上传成功，请重建索引');
    } catch (error) {
      showToast(error.message || '上传失败', 'error');
    } finally {
      button.disabled = false;
      button.textContent = '上传资料';
    }
  }

  return {
    loadDocuments,
    previewDocument,
    uploadDocument,
  };
}
