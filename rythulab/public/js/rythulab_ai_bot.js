(function () {
  "use strict";

  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
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
    `;
    document.head.appendChild(style);
  }

  function createWidget() {
    const fab = document.createElement("button");
    fab.id = "rl-bot-fab";
    fab.title = "Ask Rythu AI";
    fab.innerHTML = `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.03 2 11c0 2.62 1.19 4.98 3.07 6.63L4 22l4.67-1.56A10.1 10.1 0 0 0 12 21c5.52 0 10-4.03 10-9S17.52 2 12 2z" fill="white"/><circle cx="8.5" cy="11" r="1.2" fill="#52a84e"/><circle cx="15.5" cy="11" r="1.2" fill="#52a84e"/></svg>`;

    document.body.appendChild(fab);

    fab.addEventListener("click", function () {
      window.open("http://10.24.9.195:8501", "_blank");
    });
  }

  function init() { injectStyles(); createWidget(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
