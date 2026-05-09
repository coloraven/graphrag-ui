import { $, $$ } from './core.js';

export function createPageController() {
  function setPage(page) {
    $$('.page').forEach((node) => {
      const active = node.id === `${page}-page`;
      node.classList.toggle('active', active);
      node.setAttribute('aria-hidden', String(!active));
    });
    $$('[role="tab"].nav-button').filter((button) => button.dataset.page).forEach((button) => {
      const active = button.dataset.page === page;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
      button.setAttribute('tabindex', active ? '0' : '-1');
    });
  }

  function focusTab(buttons, nextIndex) {
    const target = buttons[nextIndex];
    if (!target) return;
    setPage(target.dataset.page);
    target.focus();
  }

  function bindTabKeyboardNavigation(buttons) {
    if (buttons.length < 2) return;

    buttons.forEach((button, index) => {
      button.addEventListener('keydown', (event) => {
        if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();

        if (event.key === 'Home') {
          focusTab(buttons, 0);
          return;
        }

        if (event.key === 'End') {
          focusTab(buttons, buttons.length - 1);
          return;
        }

        const direction = event.key === 'ArrowRight' ? 1 : -1;
        const nextIndex = (index + direction + buttons.length) % buttons.length;
        focusTab(buttons, nextIndex);
      });
    });
  }

  function bindNavigation() {
    const navButtons = $$('[role="tab"].nav-button').filter((button) => button.dataset.page);
    navButtons.forEach((button) => {
      button.addEventListener('click', () => setPage(button.dataset.page));
    });
    bindTabKeyboardNavigation(navButtons);

    $$('.shortcut-button').forEach((button) => {
      button.addEventListener('click', () => {
        $('#question-input').value = button.dataset.task || '';
        const materialsInput = $('#materials-input');
        if (materialsInput) {
          materialsInput.value = button.dataset.materials || '';
        }
        $('#question-input').focus();
      });
    });

    setPage('workspace');
  }

  return {
    bindNavigation,
    setPage,
  };
}
