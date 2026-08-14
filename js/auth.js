var API = window.RF_API || 'http://localhost:8502';
var CAP_ID = '';

function loadCaptcha() {
  var q = document.getElementById('cap_q');
  if (!q) return;
  fetch(API + '/api/captcha').then(function (r) { return r.json(); }).then(function (d) {
    CAP_ID = d.id; q.textContent = d.question + ' =';
  });
}
if (document.getElementById('cap_q')) loadCaptcha();

function rfSignup() {
  var email = document.getElementById('su_email').value.trim();
  var phone = document.getElementById('su_phone').value.trim();
  var pass = document.getElementById('su_pass').value;
  var msg = document.getElementById('su_msg');
  if (!email && !phone) { msg.textContent = 'Enter your email OR your phone number.'; return; }
  if (pass.length < 6) { msg.textContent = 'Password must be 6+ characters.'; return; }
  fetch(API + '/api/join', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email, phone: phone, password: pass,
      captcha_id: CAP_ID, captcha_answer: document.getElementById('cap_a').value,
      website: document.getElementById('su_web').value }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; loadCaptcha(); document.getElementById('cap_a').value = ''; }
    });
}

function rfLogin() {
  var ident = document.getElementById('li_id').value.trim();
  var pass = document.getElementById('li_pass').value;
  var msg = document.getElementById('li_msg');
  if (!ident) { msg.textContent = 'Enter your email or phone.'; return; }
  fetch(API + '/api/member-login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier: ident, password: pass }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; }
    });
}
