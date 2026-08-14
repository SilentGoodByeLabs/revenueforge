var API = window.RF_API || 'http://localhost:8502';
var CAP_ID = '';

function loadCaptcha() {
  var q = document.getElementById('cap_q');
  if (!q) return;
  fetch(API + '/api/captcha').then(function (r) { return r.json(); }).then(function (d) {
    CAP_ID = d.id; q.textContent = d.question + ' =';
  }).catch(function () { setTimeout(loadCaptcha, 3000); });
}
if (document.getElementById('cap_q')) loadCaptcha();

function suReset(btn) { btn.disabled = false; btn.textContent = 'Create my account →'; }

function rfSignup() {
  var ident = document.getElementById('su_id').value.trim();
  var pass = document.getElementById('su_pass').value;
  var msg = document.getElementById('su_msg');
  var btn = document.getElementById('su_btn');
  if (!ident) { msg.textContent = 'Enter your email or phone number.'; return; }
  if (pass.length < 6) { msg.textContent = 'Password must be 6+ characters.'; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Creating your account…';
  fetch(API + '/api/join', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier: ident, password: pass,
      captcha_id: CAP_ID, captcha_answer: document.getElementById('cap_a').value,
      website: document.getElementById('su_web').value }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; loadCaptcha(); document.getElementById('cap_a').value = ''; suReset(btn); }
    })
    .catch(function () { msg.textContent = 'Connection problem — wait a few seconds and try again.'; suReset(btn); });
}

function rfLogin() {
  var ident = document.getElementById('li_id').value.trim();
  var pass = document.getElementById('li_pass').value;
  var msg = document.getElementById('li_msg');
  var btn = document.querySelector('.auth-card .btn');
  if (!ident) { msg.textContent = 'Enter your email or phone.'; return; }
  if (btn) { btn.disabled = true; btn.textContent = 'Logging in…'; }
  fetch(API + '/api/member-login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier: ident, password: pass }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; if (btn) { btn.disabled = false; btn.textContent = 'Log in →'; } }
    })
    .catch(function () { msg.textContent = 'Connection problem — wait a few seconds and try again.'; if (btn) { btn.disabled = false; btn.textContent = 'Log in →'; } });
}
