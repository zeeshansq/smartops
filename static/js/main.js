/**
 * SmartOps Platform — Interactive Client Application JS
 * Handles theme switching (Dark default, Light, System), UI events, sidebar toggles.
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

// Immediate Theme Initialization — DEFAULT IS DARK
(function initSmartOpsTheme() {
  // First visit defaults to 'dark'; returning visits use stored preference
  const savedTheme = localStorage.getItem('smartops-theme') || 'dark';
  window.applySmartOpsTheme(savedTheme);
})();

// Listen for OS-level system theme preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  const savedTheme = localStorage.getItem('smartops-theme') || 'dark';
  if (savedTheme === 'system') {
    window.applySmartOpsTheme('system');
  }
});

// Global Theme Manager for Alpine.js x-data="themeManager()"
window.themeManager = function() {
  return {
    mode: localStorage.getItem('smartops-theme') || 'dark',
    themeDropdownOpen: false,

    setTheme(newMode) {
      this.mode = newMode;
      localStorage.setItem('smartops-theme', newMode);
      window.applySmartOpsTheme(newMode);
    }
  };
};

// Register with Alpine.data on alpine:init as well
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
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Global keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const sidebarToggle = document.getElementById('sidebar-toggle');
      if (sidebarToggle && window.innerWidth < 1024) {
        sidebarToggle.dispatchEvent(new Event('click'));
      }
    }
  });
});
