var API = window.RF_API || 'http://localhost:8502';
var CAP_OK = false, SLIDE_MS = 0;

(function warmup() { fetch(API + '/health').catch(function () {}); })();

(function initSlider() {
  var wrap = document.getElementById('cap_wrap');
  if (!wrap) return;
  var track = wrap.querySelector('.slide-track'), handle = document.getElementById('cap_handle'),
      fill = document.getElementById('cap_fill'), label = document.getElementById('cap_label');
  var dragging = false, startX = 0, x = 0, max = 0, t0 = 0;
  handle.addEventListener('pointerdown', function (e) {
    if (CAP_OK) return;
    dragging = true; startX = e.clientX; t0 = Date.now();
    max = track.clientWidth - handle.offsetWidth - 8;
    handle.setPointerCapture(e.pointerId);
  });
  handle.addEventListener('pointermove', function (e) {
    if (!dragging) return;
    x = Math.min(Math.max(e.clientX - startX, 0), max);
    handle.style.left = (x + 4) + 'px';
    fill.style.width = (x + handle.offsetWidth) + 'px';
  });
  handle.addEventListener('pointerup', function () {
    if (!dragging) return;
    dragging = false;
    if (x >= max - 6) {
      CAP_OK = true; SLIDE_MS = Date.now() - t0;
      label.textContent = '✔ Verified'; wrap.classList.add('ok');
    } else { handle.style.left = '4px'; fill.style.width = '0'; }
    x = 0;
  });
})();

function rfSignup() {
  var email = document.getElementById('su_email').value.trim().toLowerCase();
  var pass = document.getElementById('su_pass').value;
  var msg = document.getElementById('su_msg');
  var btn = document.getElementById('su_btn');
  if (!email || email.indexOf('@') < 0) { msg.textContent = 'Enter your email address.'; return; }
  if (pass.length < 6) { msg.textContent = 'Password must be 6+ characters.'; return; }
  if (!CAP_OK) { msg.textContent = 'Slide the bar to verify you are human.'; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Creating your account…';
  fetch(API + '/api/join-get?email=' + encodeURIComponent(email) +
        '&password=' + encodeURIComponent(pass) +
        '&slide_ms=' + Math.max(SLIDE_MS, 500))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; btn.disabled = false; btn.textContent = 'Create my account →'; }
    })
    .catch(function (e) { msg.textContent = 'Failed: ' + e.name + ' ' + e.message; btn.disabled = false; btn.textContent = 'Create my account →'; });
}

function rfLogin() {
  var email = document.getElementById('li_email').value.trim().toLowerCase();
  var pass = document.getElementById('li_pass').value;
  var msg = document.getElementById('li_msg');
  var btn = document.getElementById('li_btn');
  if (!email || email.indexOf('@') < 0) { msg.textContent = 'Enter your email address.'; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Logging in…';
  fetch(API + '/api/login-get?email=' + encodeURIComponent(email) + '&password=' + encodeURIComponent(pass))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; btn.disabled = false; btn.textContent = 'Log in →'; }
    })
    .catch(function (e) { msg.textContent = 'Failed: ' + e.name + ' ' + e.message; btn.disabled = false; btn.textContent = 'Log in →'; });
}
