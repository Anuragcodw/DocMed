/**
 * navbar.js - DocMed Premium Navbar Interaction
 * Handles smooth dropdown open/close animations and active link detection.
 * Works alongside Bootstrap 4 dropdowns without replacing their functionality.
 */

(function () {
  'use strict';

  /* ── Smooth dropdown animation (opacity + translateY) ── */
  // We listen to Bootstrap's show/hide events and toggle .show on our custom menus
  document.addEventListener('DOMContentLoaded', function () {

    // Mark active nav link based on current URL
    var currentPath = window.location.pathname;
    document.querySelectorAll('.animated-link-navbar').forEach(function (link) {
      if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
      }
    });

    // Handle Bootstrap dropdown events for .nav-dropdown-menu
    // Bootstrap 4 fires these events on the toggle element (.dropdown-toggle)
    var dropdowns = document.querySelectorAll('[data-toggle="dropdown"]');

    dropdowns.forEach(function (toggle) {
      var parent = toggle.closest('.dropdown') || toggle.parentElement;
      if (!parent) return;
      var menu = parent.querySelector('.nav-dropdown-menu');
      if (!menu) return;

      // When Bootstrap shows the dropdown
      $(toggle).on('show.bs.dropdown', function () {
        // Let Bootstrap add .show to the parent, then also add to menu
        requestAnimationFrame(function () {
          menu.classList.add('show');
        });
      });

      // When Bootstrap hides the dropdown
      $(toggle).on('hide.bs.dropdown', function () {
        menu.classList.remove('show');
      });
    });

    /* ── Login button — prevent scale on click ── */
    var loginBtn = document.getElementById('loginDropdown');
    if (loginBtn) {
      loginBtn.addEventListener('mousedown', function (e) {
        // Prevent any active :focus scale effects
        e.currentTarget.blur();
      });
    }

    /* ── Responsive: close dropdown when clicking outside ── */
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.dropdown')) {
        document.querySelectorAll('.nav-dropdown-menu.show').forEach(function (m) {
          m.classList.remove('show');
        });
      }
    });

  });

})();
