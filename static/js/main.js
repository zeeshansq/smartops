/**
 * SmartOps Platform — Interactive Client Application JS
 * Handles UI events, sidebar toggles, password visibility, and clipboard actions.
 */

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
