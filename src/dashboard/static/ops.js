// atmina ops — theme toggle + toast queue + small client-side glue.
//
// Theme cycles through three states: auto (no class, respects prefers-color-scheme)
// → light (force light) → dark (force dark) → auto again. The flash-blocker
// script in <head> applies the saved theme before first paint; this file
// owns the toggle button + persistence cycle.
//
// Toasts: server-side action handlers emit `HX-Trigger: {"showToast":{...}}`;
// HTMX dispatches a 'showToast' custom event on document.body which is wired
// here. Success auto-dismisses after 3 s; warnings/errors require a click so
// the operator notices them.

(function () {
  'use strict';

  const STORAGE_KEY = 'ops:theme';
  const ORDER = ['auto', 'light', 'dark'];
  const GLYPH = { auto: '◐', light: '☀', dark: '☾' };
  const TOAST_AUTO_DISMISS_MS = 3000;
  const TOAST_LEVEL_GLYPH = { success: '✓', warning: '⚠', danger: '✗', info: 'ⓘ' };

  function currentMode() {
    const saved = localStorage.getItem(STORAGE_KEY);
    return ORDER.includes(saved) ? saved : 'auto';
  }

  function apply(mode) {
    const root = document.documentElement;
    if (mode === 'dark') {
      root.classList.add('dark');
    } else if (mode === 'light') {
      root.classList.remove('dark');
    } else {
      // auto — defer to media query
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }
    const label = document.querySelector('[data-theme-label]');
    if (label) label.textContent = GLYPH[mode] || GLYPH.auto;
  }

  function cycle() {
    const next = ORDER[(ORDER.indexOf(currentMode()) + 1) % ORDER.length];
    if (next === 'auto') {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, next);
    }
    apply(next);
  }

  function appendToast(level, message) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const safeLevel = TOAST_LEVEL_GLYPH[level] ? level : 'info';
    const toast = document.createElement('div');
    toast.setAttribute('role', 'status');
    toast.className =
      'toast status-' + safeLevel +
      ' rounded shadow-lg px-4 py-2 text-sm border border-current border-opacity-20 ' +
      'pointer-events-auto min-w-[16rem] max-w-md flex items-start gap-3 ' +
      'transition-opacity duration-200';
    toast.innerHTML =
      '<span aria-hidden="true">' + TOAST_LEVEL_GLYPH[safeLevel] + '</span>' +
      '<span class="flex-1"></span>' +
      '<button type="button" class="ml-2 text-xs opacity-60 hover:opacity-100" ' +
              'aria-label="Aizvērt">✕</button>';
    // textContent on the message span — prevents HTML injection from server data
    toast.querySelector('.flex-1').textContent = message || '';
    toast.querySelector('button').addEventListener('click', () => toast.remove());
    container.appendChild(toast);
    if (safeLevel === 'success' || safeLevel === 'info') {
      setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 200);
      }, TOAST_AUTO_DISMISS_MS);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    apply(currentMode());
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.addEventListener('click', cycle);

    // React to system preference change while in 'auto' mode.
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
      if (currentMode() === 'auto') apply('auto');
    });

    // HTMX HX-Trigger: {"showToast": {"level": "...", "message": "..."}}
    document.body.addEventListener('showToast', function (e) {
      const payload = (e && e.detail) || {};
      appendToast(payload.level || 'info', payload.message || '');
    });

    // Global keyboard shortcut dispatcher. Elements opt in by setting
    // data-shortcut="<KEY>" — a keystroke matching that key clicks the
    // element. Skipped when typing inside <input>/<textarea>/<select> or
    // a contentEditable element, so the reject-reason textarea doesn't
    // fire the deploy modal on every 'D' the operator types.
    document.addEventListener('keydown', function (e) {
      const target = e.target;
      if (!target) return;
      const tag = (target.tagName || '').toUpperCase();
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
      if (target.isContentEditable) return;
      // Ignore when modifier keys are held — Ctrl+R should still reload the page.
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const key = e.key;
      if (!key) return;
      // Map convenience aliases
      let lookup = key;
      if (lookup.length === 1) lookup = lookup.toUpperCase();
      const el = document.querySelector('[data-shortcut="' + lookup + '"]');
      if (el) {
        e.preventDefault();
        el.click();
      }
    });
  });
})();
