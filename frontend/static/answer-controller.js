import { $, $$ } from './core.js';

export function createAnswerController() {
  function highlightCitation(index) {
    $$('.evidence-card.active').forEach((card) => card.classList.remove('active'));
    const target = $(`.evidence-card[data-citation-index="${index}"]`);
    if (!target) return;
    target.classList.add('active');
    target.setAttribute('tabindex', '-1');
    target.focus({ preventScroll: true });
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function bindAnswerEvents() {
    $('#answer-text').addEventListener('click', (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.classList.contains('citation-ref')) {
        highlightCitation(target.dataset.citationIndex);
      }
    });
  }

  return {
    bindAnswerEvents,
  };
}
