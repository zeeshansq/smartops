/**
 * SmartOps Platform — Interactive Client Application JS
 * Handles theme switching (Dark, Light, System), UI events, sidebar toggles, and clipboard actions.
 */

// Immediate Theme Initialization (prevents flash of unstyled content)
(function initSmartOpsTheme() {
  const savedTheme = localStorage.getItem('smartops-theme') || 'system';
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  if (savedTheme === 'dark' || (savedTheme === 'system' && prefersDark)) {
    document.documentElement.classList.add('dark');
    document.documentElement.classList.remove('light');
  } else {
    document.documentElement.classList.add('light');
    document.documentElement.classList.remove('dark');
  }
})();

// Listen for system theme preference changes dynamically
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  const savedTheme = localStorage.getItem('smartops-theme') || 'system';
  if (savedTheme === 'system') {
    if (e.matches) {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    }
  }
});

// Alpine.js Theme Manager Component
document.addEventListener('alpine:init', () => {
  Alpine.data('themeManager', () => ({
    mode: localStorage.getItem('smartops-theme') || 'system',
    themeDropdownOpen: false,

    setTheme(newMode) {
      this.mode = newMode;
      localStorage.setItem('smartops-theme', newMode);
      
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (newMode === 'dark' || (newMode === 'system' && prefersDark)) {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.add('light');
        document.documentElement.classList.remove('dark');
      }
    }
  }));
});

document.addEventListener('DOMContentLoaded', () => {
  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      
      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        e.preventDefault();
        targetElement.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  // Global keyboard shortcuts (e.g. Esc to close mobile sidebar)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const sidebarToggle = document.getElementById('sidebar-toggle');
      if (sidebarToggle && window.innerWidth < 1024) {
        sidebarToggle.dispatchEvent(new Event('click'));
      }
    }
  });
});
