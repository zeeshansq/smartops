/**
 * SmartOps Platform — Interactive Client Application JS
 * Handles theme switching (Dark, Light, System), UI events, sidebar toggles, and clipboard actions.
 */

// Global Theme Application Helper
window.applySmartOpsTheme = function(mode) {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (mode === 'dark' || (mode === 'system' && prefersDark)) {
    document.documentElement.classList.add('dark');
    document.documentElement.classList.remove('light');
  } else {
    document.documentElement.classList.add('light');
    document.documentElement.classList.remove('dark');
  }
};

// Immediate Theme Initialization (prevents flash of unstyled content)
(function initSmartOpsTheme() {
  const savedTheme = localStorage.getItem('smartops-theme') || 'system';
  window.applySmartOpsTheme(savedTheme);
})();

// Listen for system theme preference changes dynamically
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  const savedTheme = localStorage.getItem('smartops-theme') || 'system';
  if (savedTheme === 'system') {
    window.applySmartOpsTheme('system');
  }
});

// Global Theme Manager for Alpine.js x-data="themeManager()"
window.themeManager = function() {
  return {
    mode: localStorage.getItem('smartops-theme') || 'system',
    themeDropdownOpen: false,

    setTheme(newMode) {
      this.mode = newMode;
      localStorage.setItem('smartops-theme', newMode);
      window.applySmartOpsTheme(newMode);
    }
  };
};

// Register with Alpine.data if alpine:init hasn't fired yet
document.addEventListener('alpine:init', () => {
  if (window.Alpine) {
    Alpine.data('themeManager', window.themeManager);
  }
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
