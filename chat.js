/* Prahari Gemini chatbot widget – floating button + chat window */
(function () {
  const css = `
  #pc-btn{position:fixed;bottom:90px;left:18px;z-index:600;width:52px;height:52px;border-radius:50%;border:none;background:var(--pri,#1B4FD8);color:#fff;font-size:24px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.3)}
  #pc-box{position:fixed;bottom:150px;left:18px;z-index:600;width:min(340px,calc(100vw - 36px));height:420px;background:var(--card,#fff);color:var(--t1,#0F1F5C);border:1.5px solid var(--bdr,#ccd);border-radius:16px;display:none;flex-direction:column;box-shadow:0 8px 30px rgba(0,0,0,.3);overflow:hidden;font-family:inherit}
  #pc-box.open{display:flex}
  #pc-head{padding:12px 14px;font-weight:800;background:var(--pri,#1B4FD8);color:#fff;display:flex;justify-content:space-between;align-items:center}
  #pc-head span{cursor:pointer}
  #pc-msgs{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px;font-size:13px}
  .pc-m{max-width:85%;padding:8px 11px;border-radius:12px;white-space:pre-wrap;line-height:1.4}
  .pc-u{align-self:flex-end;background:var(--pri,#1B4FD8);color:#fff}
  .pc-b{align-self:flex-start;background:rgba(120,140,200,.18)}
  #pc-in{display:flex;border-top:1.5px solid var(--bdr,#ccd)}
  #pc-in input{flex:1;border:none;padding:12px;font-size:13px;background:transparent;color:inherit;outline:none}
  #pc-in button{border:none;background:none;padding:0 14px;font-size:18px;cursor:pointer;color:var(--pri,#1B4FD8)}`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  document.body.insertAdjacentHTML('beforeend', `
    <button id="pc-btn" title="Safety Assistant">🤖</button>
    <div id="pc-box">
      <div id="pc-head">Prahari Assistant <span id="pc-x">✕</span></div>
      <div id="pc-msgs"><div class="pc-m pc-b">Hi! Ask me any safety question. In danger, press SOS or call 112.</div></div>
      <div id="pc-in"><input id="pc-txt" placeholder="Type a message..." maxlength="500"><button id="pc-send">➤</button></div>
    </div>`);

  const box = document.getElementById('pc-box'),
        msgs = document.getElementById('pc-msgs'),
        txt = document.getElementById('pc-txt'),
        history = [];

  document.getElementById('pc-btn').onclick = () => box.classList.toggle('open');
  document.getElementById('pc-x').onclick   = () => box.classList.remove('open');

  function add(text, cls) {
    const d = document.createElement('div');
    d.className = 'pc-m ' + cls;
    d.textContent = text;
    msgs.appendChild(d);
    msgs.scrollTop = msgs.scrollHeight;
    return d;
  }

  async function send() {
    const text = txt.value.trim();
    if (!text) return;
    txt.value = '';
    add(text, 'pc-u');

    const token = localStorage.getItem('prahari_token');
    if (!token) {
      add('Please log in to use the assistant.', 'pc-b');
      return;
    }

    const wait = add('Thinking...', 'pc-b');
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ message: text, history })
      });
      const d = await r.json();
      wait.textContent = d.reply || d.error || 'Something went wrong.';
      if (d.reply) {
        history.push({ role: 'user', text }, { role: 'model', text: d.reply });
      }
    } catch (e) {
      wait.textContent = 'Server unreachable. Check if Flask is running.';
    }
    msgs.scrollTop = msgs.scrollHeight;
  }

  document.getElementById('pc-send').onclick = send;
  txt.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
})();