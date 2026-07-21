/* -------------------------------------------------------------
 * AUTH.JS - Password Toggle, Strength, Loading, Caps Lock, Ripple
 * ------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', function() {

  /* ---- Password Eye Toggle ---- */
  document.querySelectorAll('.password-eye').forEach(function(eye) {
    eye.addEventListener('click', function() {
      var input = eye.closest('.form-floating-custom').querySelector('input');
      if (!input) return;
      if (input.type === 'password') {
        input.type = 'text';
        eye.classList.remove('fa-eye');
        eye.classList.add('fa-eye-slash');
      } else {
        input.type = 'password';
        eye.classList.remove('fa-eye-slash');
        eye.classList.add('fa-eye');
      }
    });
  });

  /* ---- Caps Lock Detection ---- */
  document.querySelectorAll('input[type="password"]').forEach(function(input) {
    var parent = input.closest('.form-floating-custom');
    if (!parent) return;
    var capsWarn = parent.querySelector('.caps-warn');
    if (!capsWarn) return;

    input.addEventListener('keyup', function(e) {
      if (e.getModifierState && e.getModifierState('CapsLock')) {
        capsWarn.style.display = 'block';
      } else {
        capsWarn.style.display = 'none';
      }
    });
  });

  /* ---- Password Strength Meter ---- */
  document.querySelectorAll('.password-strength-bar').forEach(function(bar) {
    var parent = bar.closest('.form-floating-custom');
    if (!parent) return;
    var input = parent.querySelector('input');
    if (!input) return;
    var fill = bar.querySelector('.strength-fill');
    var label = bar.querySelector('.strength-label');
    if (!fill || !label) return;

    input.addEventListener('input', function() {
      var val = input.value;
      var score = 0;
      if (val.length >= 6) score++;
      if (val.length >= 10) score++;
      if (/[A-Z]/.test(val)) score++;
      if (/[0-9]/.test(val)) score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;

      var map = [
        { w: '0%', c: '#E2E8F0', t: '' },
        { w: '20%', c: '#EF4444', t: 'Weak' },
        { w: '40%', c: '#F59E0B', t: 'Fair' },
        { w: '60%', c: '#F59E0B', t: 'Good' },
        { w: '80%', c: '#10B981', t: 'Strong' },
        { w: '100%', c: '#10B981', t: 'Excellent' }
      ];
      var s = map[Math.min(score, 5)];
      fill.style.width = s.w;
      fill.style.background = s.c;
      label.textContent = s.t;
      label.style.color = s.c;
    });
  });

  /* ---- Form Submit Loader ---- */
  document.querySelectorAll('form[data-loading]').forEach(function(form) {
    form.addEventListener('submit', function() {
      var btn = form.querySelector('button[type="submit"]');
      if (!btn) return;
      var textEl = btn.querySelector('.btn-text');
      var spinEl = btn.querySelector('.btn-spinner');
      if (textEl) textEl.style.display = 'none';
      if (spinEl) spinEl.style.display = 'inline-block';
      btn.disabled = true;
      btn.style.opacity = '0.7';
    });
  });

  /* ---- Ripple Effect on buttons ---- */
  document.querySelectorAll('.btn-premium').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      var circle = document.createElement('span');
      circle.classList.add('ripple-element');
      var d = Math.max(btn.clientWidth, btn.clientHeight);
      circle.style.width = circle.style.height = d + 'px';
      var rect = btn.getBoundingClientRect();
      circle.style.left = (e.clientX - rect.left - d / 2) + 'px';
      circle.style.top = (e.clientY - rect.top - d / 2) + 'px';
      btn.appendChild(circle);
      setTimeout(function() { circle.remove(); }, 600);
    });
  });

});
