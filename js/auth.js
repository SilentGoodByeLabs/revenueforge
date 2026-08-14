var API = window.RF_API || 'http://localhost:8502';

function rfSignup() {
  var email = document.getElementById('su_email').value.trim();
  var phone = document.getElementById('su_phone').value.trim();
  var pass = document.getElementById('su_pass').value;
  var msg = document.getElementById('su_msg');
  if (!email || email.indexOf('@') < 0) { msg.textContent = 'Enter a valid email.'; return; }
  if (phone.replace(/\D/g, '').length < 7) { msg.textContent = 'Enter a valid phone number.'; return; }
  if (pass.length < 6) { msg.textContent = 'Password must be 6+ characters.'; return; }
  fetch(API + '/api/join', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email, phone: phone, password: pass }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: email })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message || 'Signup failed'; }
    });
}

function rfLogin() {
  var email = document.getElementById('li_email').value.trim();
  var pass = document.getElementById('li_pass').value;
  var msg = document.getElementById('li_msg');
  fetch(API + '/api/member-login', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: email, password: pass }) })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: email })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message || 'Wrong email or password'; }
    });
}
