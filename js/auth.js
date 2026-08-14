var API = window.RF_API || 'http://localhost:8502';

(function warmup() { fetch(API + '/health').catch(function () {}); })();

/* Auto-retry: survives Render redeploys and sleep/wake (up to 3 retries) */
function getJSON(url, tries) {
  tries = tries || 0;
  return fetch(url).then(function (r) {
    if ((r.status === 502 || r.status === 503) && tries < 3) {
      return new Promise(function (res) { setTimeout(res, 6000); }).then(function () { return getJSON(url, tries + 1); });
    }
    return r.json();
  }).catch(function (e) {
    if (tries < 3) {
      return new Promise(function (res) { setTimeout(res, 6000); }).then(function () { return getJSON(url, tries + 1); });
    }
    throw e;
  });
}

function capToken() { return (window.grecaptcha && grecaptcha.getResponse) ? grecaptcha.getResponse() : ''; }

function rfSignup() {
  var email = document.getElementById('su_email').value.trim().toLowerCase();
  var pass = document.getElementById('su_pass').value;
  var msg = document.getElementById('su_msg');
  var btn = document.getElementById('su_btn');
  if (!email || email.indexOf('@') < 0) { msg.textContent = 'Enter your email address.'; return; }
  if (pass.length < 6) { msg.textContent = 'Password must be 6+ characters.'; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Creating your account…';
  getJSON(API + '/api/join-get?email=' + encodeURIComponent(email) +
          '&password=' + encodeURIComponent(pass) +
          '&captcha=' + encodeURIComponent(capToken()))
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; if (window.grecaptcha && grecaptcha.reset) grecaptcha.reset(); btn.disabled = false; btn.textContent = 'Create my account →'; }
    })
    .catch(function (e) { msg.textContent = 'Still waking the server — try again in 30s.'; btn.disabled = false; btn.textContent = 'Create my account →'; });
}

function rfLogin() {
  var email = document.getElementById('li_email').value.trim().toLowerCase();
  var pass = document.getElementById('li_pass').value;
  var msg = document.getElementById('li_msg');
  var btn = document.getElementById('li_btn');
  if (!email || email.indexOf('@') < 0) { msg.textContent = 'Enter your email address.'; return; }
  msg.textContent = ''; btn.disabled = true; btn.textContent = 'Logging in…';
  getJSON(API + '/api/login-get?email=' + encodeURIComponent(email) +
          '&password=' + encodeURIComponent(pass) +
          '&captcha=' + encodeURIComponent(capToken()))
    .then(function (d) {
      if (d.ok) { localStorage.setItem('rf_session', JSON.stringify({ email: d.key })); window.location.href = 'portal.html'; }
      else { msg.textContent = d.message; if (window.grecaptcha && grecaptcha.reset) grecaptcha.reset(); btn.disabled = false; btn.textContent = 'Log in →'; }
    })
    .catch(function (e) { msg.textContent = 'Still waking the server — try again in 30s.'; btn.disabled = false; btn.textContent = 'Log in →'; });
}
