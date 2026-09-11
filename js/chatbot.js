/* RevenueForge Assistant — real AI chatbot */
(function () {
  const CONTACT_EMAIL = 'adeolaayodeji4666@gmail.com';

  const fab = document.createElement('button');
  fab.className = 'bot-fab';
  fab.innerHTML = '<i class="fa-solid fa-comments"></i>';
  fab.setAttribute('aria-label', 'Open chat');

  const panel = document.createElement('div');
  panel.className = 'bot-panel';
  panel.innerHTML =
    '<div class="bot-head"><span><i class="fa-solid fa-robot"></i> RevenueForge Assistant</span>' +
    '<button id="botClose" style="background:none;border:none;color:#fff;font-size:16px;cursor:pointer" aria-label="Close chat"><i class="fa-solid fa-xmark"></i></button></div>' +
    '<div class="bot-body" id="botBody"></div>' +
    '<div class="bot-chips" id="botChips"></div>' +
    '<div class="bot-input"><input id="botIn" placeholder="Ask anything..." autocomplete="off"><button id="botSend"><i class="fa-solid fa-paper-plane"></i></button></div>';

  document.body.appendChild(fab);
  document.body.appendChild(panel);

  const body = panel.querySelector('#botBody');
  const chips = panel.querySelector('#botChips');
  const inp = panel.querySelector('#botIn');
  const sendBtn = panel.querySelector('#botSend');

  function addMsg(text, who) {
    const d = document.createElement('div');
    d.className = 'msg ' + who;
    if (who === 'bot') d.innerHTML = text.replace(/\n/g, '<br>');
    else d.textContent = text;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
    return d;
  }

  function thinking() {
    const d = document.createElement('div');
    d.className = 'msg bot thinking';
    d.innerHTML = '<i>RevenueForge Assistant is thinking...</i>';
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
    return d;
  }

  async function ask(q) {
    addMsg(q, 'user');
    const wait = thinking();
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q })
      });
      const data = await res.json();
      wait.remove();
      addMsg(data.reply || "I'm not sure. Try rephrasing your question.", 'bot');
    } catch (e) {
      wait.remove();
      addMsg('Connection issue. Please try again.', 'bot');
    }
  }

  // Smart chips
  const quickQs = [
    'How does it work?',
    'Show me pricing',
    'How many job sources?',
    'Is it spam-safe?',
    'How do proposals work?',
    'Talk to a human'
  ];
  quickQs.forEach(q => {
    const b = document.createElement('button');
    b.textContent = q;
    b.onclick = function () {
      if (q === 'Talk to a human') {
        addMsg(q, 'user');
        addMsg('You can email the founder directly at <b>' + CONTACT_EMAIL + '</b> — the button below opens your mail app.', 'bot');
        const mb = document.createElement('button');
        mb.className = 'btn btn-primary btn-sm bot-mail';
        mb.innerHTML = '<i class="fa-solid fa-envelope"></i> Email the founder';
        mb.onclick = function () {
          window.location.href = 'mailto:' + CONTACT_EMAIL +
            '?subject=' + encodeURIComponent('Question from RevenueForge website') +
            '&body=' + encodeURIComponent('Hi,\n\n(Paste your question here)\n\n— sent from RevenueForge website');
        };
        body.appendChild(mb);
        body.scrollTop = body.scrollHeight;
      } else {
        ask(q);
      }
    };
    chips.appendChild(b);
  });

  sendBtn.onclick = function () {
    const q = inp.value.trim();
    if (!q) return;
    inp.value = '';
    ask(q);
  };
  inp.onkeypress = function (e) { if (e.key === 'Enter') sendBtn.click(); };

  fab.onclick = function () {
    panel.classList.toggle('open');
    if (panel.classList.contains('open')) {
      setTimeout(function () { inp.focus(); }, 200);
    }
  };
  panel.querySelector('#botClose').onclick = function () { panel.classList.remove('open'); };
})();
