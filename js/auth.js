var API = window.RF_API || 'http://localhost:8502';
var CAP_WIDGETS = [];

window.renderCaps = function () {
  if (!window.grecaptcha) return;
  ['captchaBoxSignup', 'captchaBoxLogin'].forEach(function (id) {
    var el = document.getElementById(id);
    if (el && window.RF_RECAPTCHA_SITE) {
      CAP_WIDGETS.push(grecaptcha.render(id, { sitekey: window.RF_RECAPTCHA_SITE }));
    }
  });
};

function capToken() {
  if (!window.grecaptcha || !CAP_WIDGETS.length) return '';
  try { return grecaptcha.getResponse(CAP_WIDGETS[0]) || ''; } catch (e) { return ''; }
}
function capReset() { if (window.grecaptcha) CAP_WIDGETS.forEach(function (w) { try { grecaptcha.reset(w); } catch (e) {} }); }

(function warmup() { fetch(API + '/health').catch(function () {}); })();

function rfSignup() {
  var email = document.getElementById('su_email').value.trim().toLowerCase();
  var pass = document.getElementById('su_pass').value;
  var msg = document.getElementById('su_msg');
  var btn = document.getElementById('su_btn');
  if (!email || email.indexOf('@') < 0) { msg.textContent = 'Enter your email address.'; return; }
  if (pass.length < 6) { msg.textContent = 'Password must be 6+ characters.'; return; }
  var token = capToken();
  if (!token) { msg.textContent = 'Please tick the "I\'m not a robot" box.'; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Creating your account…';
  fetch(API + '/api/join-get?email=' + encodeURIComponent(email) +
        '&password=' + encodeURIComponent(pass) + '&captcha=' + encodeURIComponent(token))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; capReset(); btn.disabled = false; btn.textContent = 'Create my account →'; }
    })
    .catch(function (e) { msg.textContent = 'Failed: ' + e.name + ' ' + e.message; btn.disabled = false; btn.textContent = 'Create my account →'; });
}

function rfLogin() {
  var email = document.getElementById('li_email').value.trim().toLowerCase();
  var pass = document.getElementById('li_pass').value;
  var msg = document.getElementById('li_msg');
  var btn = document.getElementById('li_btn');
  if (!email || email.indexOf('@') < 0) { msg.textContent = 'Enter your email address.'; return; }
  var token = capToken();
  if (!token) { msg.textContent = 'Please tick the "I\'m not a robot" box.'; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Logging in…';
  fetch(API + '/api/login-get?email=' + encodeURIComponent(email) +
        '&password=' + encodeURIComponent(pass) + '&captcha=' + encodeURIComponent(token))
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; capReset(); btn.disabled = false; btn.textContent = 'Log in →'; }
    })
    .catch(function (e) { msg.textContent = 'Failed: ' + e.name + ' ' + e.message; btn.disabled = false; btn.textContent = 'Log in →'; });
}
