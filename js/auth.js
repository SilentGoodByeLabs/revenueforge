var API = window.RF_API || 'http://localhost:8502';
var CAP_ID = '';

function fillCC(id) {
  var s = document.getElementById(id);
  if (!s || !window.RF_COUNTRIES) return;
  s.innerHTML = '<option value="">🌍</option>' + window.RF_COUNTRIES.map(function (c) {
    return '<option value="' + c[2] + '">' + c[0] + ' +' + c[2] + '</option>';
  }).join('');
}
fillCC('su_cc'); fillCC('li_cc');

function loadCaptcha() {
  var q = document.getElementById('cap_q');
  if (!q) return;
  fetch(API + '/api/captcha').then(function (r) { return r.json(); }).then(function (d) {
    CAP_ID = d.id; q.textContent = d.question + ' =';
  }).catch(function () { setTimeout(loadCaptcha, 3000); });
}
if (document.getElementById('cap_q')) loadCaptcha();

function composeIdent(raw, cc) {
  raw = raw.trim();
  if (!raw) return { err: 'Enter your email or phone number.' };
  if (raw.indexOf('@') > -1) return { val: raw };
  var digits = raw.replace(/\D/g, '');
  if (digits.length < 7) return { err: 'That phone number looks too short.' };
  if (!cc) return { err: 'Select your country  for phone signup, or type an email instead.' };
  return { val: '+' + cc + digits };
}

function rfSignup() {
  var c = composeIdent(document.getElementById('su_id').value, document.getElementById('su_cc').value);
  var pass = document.getElementById('su_pass').value;
  var msg = document.getElementById('su_msg');
  var btn = document.getElementById('su_btn');
  if (c.err) { msg.textContent = c.err; return; }
  if (pass.length < 6) { msg.textContent = 'Password must be 6+ characters.'; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Creating your account…';
  fetch(API + '/api/join', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier: c.val, password: pass,
      captcha_id: CAP_ID, captcha_answer: document.getElementById('cap_a').value,
      website: document.getElementById('su_web').value }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; loadCaptcha(); document.getElementById('cap_a').value = ''; btn.disabled = false; btn.textContent = 'Create my account →'; }
    })
    .catch(function () { msg.textContent = 'Connection problem — check your internet and try again.'; btn.disabled = false; btn.textContent = 'Create my account →'; });
}

function rfLogin() {
  var c = composeIdent(document.getElementById('li_id').value, document.getElementById('li_cc').value);
  var pass = document.getElementById('li_pass').value;
  var msg = document.getElementById('li_msg');
  var btn = document.getElementById('li_btn');
  if (c.err) { msg.textContent = c.err; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Logging in…';
  fetch(API + '/api/member-login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier: c.val, password: pass }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; btn.disabled = false; btn.textContent = 'Log in →'; }
    })
    .catch(function () { msg.textContent = 'Connection problem — check your internet and try again.'; btn.disabled = false; btn.textContent = 'Log in →'; });
}
