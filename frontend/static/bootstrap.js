import { initAccessibility } from './accessibility.js';
import { $, showToast } from './core.js';
import { createAnswerController } from './answer-controller.js';
import { createDocumentController } from './document-controller.js';
import { createHistoryController } from './history-controller.js';
import { createIndexTaskController } from './index-task-controller.js';
import { createPageController } from './page-controller.js';
import { createStatusController } from './status-controller.js';
import { createWorkflowController } from './workflow-controller.js';


export function initializeApp() {
  const statusController = createStatusController();

  let historyController;
  let indexTaskController;
  let documentController;
  let workflowController;

  const loadTaskDetail = (taskId) => indexTaskController.loadTaskDetail(taskId);
  const loadDocuments = () => documentController.loadDocuments();
  const loadHistories = () => historyController.loadHistories();

  historyController = createHistoryController({ onSelectTask: loadTaskDetail });
  documentController = createDocumentController();
  indexTaskController = createIndexTaskController({
    refreshDocuments: loadDocuments,
    refreshStatus: () => statusController.loadStatus(),
    loadHistories,
  });
  workflowController = createWorkflowController({ loadHistories });
  const pageController = createPageController();
  const answerController = createAnswerController();

  async function refreshAll(showMessage = false) {
    await Promise.all([
      statusController.loadHealth(),
      statusController.loadStatus(),
      indexTaskController.loadLatestTaskStatus(),
      loadDocuments(),
      indexTaskController.loadCurrentTaskStatus(),
      loadHistories(),
    ]);
    if (showMessage) showToast('状态已刷新');
  }

  function bindEvents() {
    pageController.bindNavigation();
    answerController.bindAnswerEvents();

    $('#submit-question').addEventListener('click', () => workflowController.submitQuestion());
    $('#rebuild-index').addEventListener('click', () => indexTaskController.rebuildIndex());
    $('#refresh-all').addEventListener('click', () => refreshAll(true));
    $('#upload-document').addEventListener('click', () => documentController.uploadDocument());

    $('#question-input').addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        workflowController.submitQuestion();
      }
    });
  }

  bindEvents();
  initAccessibility();
  refreshAll(false);
}
