(function () {
  "use strict";

  const AI_API_ENDPOINT = "http://localhost:8001/api/chat";
  const BOT_NAME = "Rythu AI";
  const PLACEHOLDER = "Ask me about crops, soil, weather…";
  const WELCOME_MSG =
    "I'm your farming assistant. Ask me anything about crops.";

  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Lora:wght@600&display=swap');
      #rl-bot-fab {
        position: fixed; bottom: 28px; right: 28px; z-index: 99999;
        width: 52px; height: 52px; border-radius: 50%;
        background: linear-gradient(135deg, #2d6a2d 0%, #52a84e 100%);
        border: none; cursor: pointer;
        box-shadow: 0 4px 20px rgba(45,106,45,0.45);
        display: flex; align-items: center; justify-content: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease; outline: none;
      }
      #rl-bot-fab:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(45,106,45,0.55); }
      #rl-bot-fab::before {
        content: ''; position: absolute; inset: -4px; border-radius: 50%;
        border: 2px solid rgba(82,168,78,0.5);
        animation: rl-pulse 2.4s ease-out infinite;
      }
      @keyframes rl-pulse { 0%{opacity:1;transform:scale(1)} 70%{opacity:0;transform:scale(1.55)} 100%{opacity:0} }
      #rl-bot-panel {
        position: fixed; bottom: 92px; right: 28px; z-index: 99999;
        width: 340px; max-height: 520px; border-radius: 18px;
        background: #fff; box-shadow: 0 12px 48px rgba(0,0,0,0.18);
        display: flex; flex-direction: column; overflow: hidden;
        font-family: 'DM Sans', sans-serif;
        transform: scale(0.88) translateY(16px); opacity: 0; pointer-events: none;
        transition: opacity 0.22s ease, transform 0.22s cubic-bezier(.34,1.46,.64,1);
      }
      #rl-bot-panel.rl-open { opacity: 1; transform: scale(1) translateY(0); pointer-events: all; }
      #rl-bot-header {
        background: linear-gradient(135deg, #2d6a2d 0%, #52a84e 100%);
        padding: 14px 16px; display: flex; align-items: center; gap: 10px; color: #fff;
      }
      #rl-bot-header .rl-avatar {
        width: 34px; height: 34px; background: rgba(255,255,255,0.2);
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-size: 16px; flex-shrink: 0;
      }
      #rl-bot-header .rl-info { flex: 1; }
      #rl-bot-header .rl-name { font-family: 'Lora', serif; font-size: 14px; font-weight: 600; line-height: 1.2; }
      #rl-bot-header .rl-status { font-size: 11px; opacity: 0.8; display: flex; align-items: center; gap: 4px; }
      #rl-bot-header .rl-dot { width: 6px; height: 6px; border-radius: 50%; background: #a8ffb0; animation: rl-blink 1.8s ease-in-out infinite; }
      @keyframes rl-blink { 0%,100%{opacity:1} 50%{opacity:0.4} }
      #rl-bot-close {
        background: rgba(255,255,255,0.15); border: none; color: #fff;
        width: 26px; height: 26px; border-radius: 50%; cursor: pointer;
        font-size: 14px; display: flex; align-items: center; justify-content: center;
        transition: background 0.15s;
      }
      #rl-bot-close:hover { background: rgba(255,255,255,0.3); }
      #rl-bot-messages {
        flex: 1; overflow-y: auto; padding: 14px 14px 8px;
        display: flex; flex-direction: column; gap: 10px; scroll-behavior: smooth;
      }
      #rl-bot-messages::-webkit-scrollbar { width: 4px; }
      #rl-bot-messages::-webkit-scrollbar-thumb { background: #d4e8d4; border-radius: 4px; }
      .rl-msg {
        max-width: 82%; padding: 9px 12px; border-radius: 14px;
        font-size: 13px; line-height: 1.5; word-break: break-word;
        animation: rl-msgIn 0.2s ease;
      }
      @keyframes rl-msgIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
      .rl-msg.rl-bot { background: #f0f7f0; color: #1a3a1a; border-bottom-left-radius: 4px; align-self: flex-start; }
      .rl-msg.rl-user { background: linear-gradient(135deg,#2d6a2d,#52a84e); color:#fff; border-bottom-right-radius:4px; align-self:flex-end; }
      .rl-typing {
        display:flex; gap:4px; align-items:center; background:#f0f7f0;
        padding:10px 14px; border-radius:14px; border-bottom-left-radius:4px;
        align-self:flex-start; width:fit-content;
      }
      .rl-typing span { width:7px; height:7px; border-radius:50%; background:#52a84e; animation:rl-bounce 1.2s ease-in-out infinite; }
      .rl-typing span:nth-child(2){animation-delay:0.18s} .rl-typing span:nth-child(3){animation-delay:0.36s}
      @keyframes rl-bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-6px)} }
      #rl-bot-input-area {
        padding:10px 12px 12px; border-top:1px solid #eaf3ea;
        display:flex; gap:8px; align-items:flex-end; background:#fff;
      }
      #rl-bot-input {
        flex:1; border:1.5px solid #d4e8d4; border-radius:12px;
        padding:8px 12px; font-family:'DM Sans',sans-serif; font-size:13px;
        color:#1a3a1a; resize:none; outline:none; max-height:90px;
        overflow-y:auto; background:#fafff8; transition:border-color 0.15s; line-height:1.4;
      }
      #rl-bot-input:focus { border-color:#52a84e; }
      #rl-bot-input::placeholder { color:#9ab89a; }
      #rl-bot-send {
        width:36px; height:36px; border-radius:50%; flex-shrink:0;
        background:linear-gradient(135deg,#2d6a2d,#52a84e); border:none;
        cursor:pointer; display:flex; align-items:center; justify-content:center;
        transition:transform 0.15s,box-shadow 0.15s; box-shadow:0 2px 8px rgba(45,106,45,0.3);
      }
      #rl-bot-send:hover { transform:scale(1.08); }
      #rl-bot-send:disabled { opacity:0.5; cursor:not-allowed; transform:none; }
      #rl-bot-chips { display:flex; flex-wrap:wrap; gap:6px; padding:0 14px 10px; }
      .rl-chip {
        font-family:'DM Sans',sans-serif; font-size:11px; padding:4px 10px;
        border-radius:20px; border:1.5px solid #c2dfc2; background:#f5fdf5;
        color:#2d6a2d; cursor:pointer; transition:background 0.15s,border-color 0.15s; white-space:nowrap;
      }
      .rl-chip:hover { background:#e0f3e0; border-color:#52a84e; }
      @media(max-width:480px) {
        #rl-bot-panel { right:12px; left:12px; width:auto; bottom:80px; }
        #rl-bot-fab { right:16px; bottom:16px; }
      }
    `;
    document.head.appendChild(style);
  }

  function createWidget() {
    const fab = document.createElement("button");
    fab.id = "rl-bot-fab";
    fab.title = "Ask Rythu AI";
    fab.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.03 2 11c0 2.62 1.19 4.98 3.07 6.63L4 22l4.67-1.56A10.1 10.1 0 0 0 12 21c5.52 0 10-4.03 10-9S17.52 2 12 2z" fill="white"/><circle cx="8.5" cy="11" r="1.2" fill="#52a84e"/><circle cx="12" cy="11" r="1.2" fill="#52a84e"/><circle cx="15.5" cy="11" r="1.2" fill="#52a84e"/></svg>`;

    const panel = document.createElement("div");
    panel.id = "rl-bot-panel";
    panel.innerHTML = `
      <div id="rl-bot-header">
        <div class="rl-avatar">🌾</div>
        <div class="rl-info">
          <div class="rl-name">${BOT_NAME}</div>
          <div class="rl-status"><span class="rl-dot"></span> Online</div>
        </div>
        <button id="rl-bot-close" title="Close">✕</button>
      </div>
      <div id="rl-bot-messages"></div>
      <div id="rl-bot-chips">
        <span class="rl-chip">Best crops for clay soil</span>
        <span class="rl-chip">Pest control tips</span>
        <span class="rl-chip">Water requirements</span>
        <span class="rl-chip">Intercropping ideas</span>
      </div>
      <div id="rl-bot-input-area">
        <textarea id="rl-bot-input" rows="1" placeholder="${PLACEHOLDER}"></textarea>
        <button id="rl-bot-send" title="Send"><svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M2 21L23 12 2 3v7l15 2-15 2v7z" fill="white"/></svg></button>
      </div>`;

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    const messagesEl = panel.querySelector("#rl-bot-messages");
    const inputEl = panel.querySelector("#rl-bot-input");
    const sendBtn = panel.querySelector("#rl-bot-send");
    const closeBtn = panel.querySelector("#rl-bot-close");
    let isOpen = false, isLoading = false, conversationHistory = [];

    function togglePanel() {
      isOpen = !isOpen;
      panel.classList.toggle("rl-open", isOpen);
      if (isOpen && messagesEl.children.length === 0) addMessage("bot", WELCOME_MSG);
      if (isOpen) setTimeout(() => inputEl.focus(), 250);
    }

    function addMessage(role, text) {
      const msg = document.createElement("div");
      msg.className = `rl-msg rl-${role}`;
      msg.textContent = text;
      messagesEl.appendChild(msg);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function showTyping() {
      const el = document.createElement("div");
      el.className = "rl-typing"; el.id = "rl-typing-indicator";
      el.innerHTML = "<span></span><span></span><span></span>";
      messagesEl.appendChild(el);
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function removeTyping() { const el = document.getElementById("rl-typing-indicator"); if (el) el.remove(); }

    async function sendMessage(text) {
      if (!text.trim() || isLoading) return;
      isLoading = true; sendBtn.disabled = true;
      addMessage("user", text);
      conversationHistory.push({ role: "user", content: text });
      inputEl.value = ""; inputEl.style.height = "auto";
      showTyping();
      try {
        const response = await fetch(AI_API_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, history: conversationHistory }),
        });
        if (!response.ok) throw new Error();
        const data = await response.json();
        const reply = data.reply || data.message || data.answer || "No response received.";
        removeTyping(); addMessage("bot", reply);
        conversationHistory.push({ role: "assistant", content: reply });
      } catch {
        removeTyping();
        addMessage("bot", "Backend not connected yet. Update AI_API_ENDPOINT in the JS file to activate me! 🌿");
      }
      isLoading = false; sendBtn.disabled = false; inputEl.focus();
    }

    fab.addEventListener("click", togglePanel);
    closeBtn.addEventListener("click", togglePanel);
    sendBtn.addEventListener("click", () => sendMessage(inputEl.value));
    inputEl.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(inputEl.value); } });
    inputEl.addEventListener("input", () => { inputEl.style.height = "auto"; inputEl.style.height = Math.min(inputEl.scrollHeight, 90) + "px"; });
    panel.querySelectorAll(".rl-chip").forEach(chip => chip.addEventListener("click", () => { if (!isOpen) togglePanel(); sendMessage(chip.textContent); }));
    document.addEventListener("click", (e) => { if (isOpen && !panel.contains(e.target) && e.target !== fab) togglePanel(); });
  }

  function init() { injectStyles(); createWidget(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
