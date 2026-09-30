/* Floating travel assistant. Talks to /chatbot/message/ (Groq-backed, with an offline fallback). */
(() => {
  const root = document.getElementById("chatbot");
  if (!root) return;
  const panel = root.querySelector(".chat-panel");
  const body = root.querySelector(".chat-body");
  const input = root.querySelector("textarea");
  const sendBtn = root.querySelector("[data-send]");
  const suggestions = root.querySelector(".chat-suggestions");
  const { messageUrl, historyUrl, resetUrl, welcome } = root.dataset;
  const csrf = document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] || root.dataset.csrf;
  let loaded = false;
  let busy = false;

  const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // Minimal, safe markdown: escape first, then allow bold, links (relative or https) and bullet lists.
  function render(text) {
    let html = escapeHtml(text)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\[([^\]]+)\]\(((?:\/|https:\/\/)[^\s)]+)\)/g, '<a href="$2">$1</a>');
    const lines = html.split("\n");
    let out = "", inList = false;
    for (const line of lines) {
      const m = line.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)/);
      if (m) { if (!inList) { out += "<ul>"; inList = true; } out += `<li>${m[1]}</li>`; }
      else { if (inList) { out += "</ul>"; inList = false; } out += line ? `${line}<br>` : "<br>"; }
    }
    if (inList) out += "</ul>";
    return out.replace(/(<br>)+$/, "");
  }

  function add(role, text) {
    const el = document.createElement("div");
    el.className = `chat-msg ${role === "user" ? "user" : "bot"}`;
    if (/[؀-ۿ]/.test(text)) el.dir = "rtl";
    el.innerHTML = role === "user" ? escapeHtml(text) : render(text);
    body.appendChild(el);
    body.scrollTop = body.scrollHeight;
    return el;
  }

  function addCards(tours) {
    if (!tours || !tours.length) return;
    const wrap = document.createElement("div");
    wrap.className = "chat-cards";
    wrap.innerHTML = tours.map((t) => `
      <a class="chat-card" href="${escapeHtml(t.url)}">
        <img src="${escapeHtml(t.image)}" alt="" loading="lazy">
        <div><div class="t">${escapeHtml(t.title)}</div><div class="m">${escapeHtml(t.meta)}</div><div class="p">${escapeHtml(t.price)}</div></div>
      </a>`).join("");
    body.appendChild(wrap);
    body.scrollTop = body.scrollHeight;
  }

  async function loadHistory() {
    loaded = true;
    add("assistant", welcome);
    try {
      const res = await fetch(historyUrl, { credentials: "same-origin" });
      const data = await res.json();
      data.messages.forEach((m) => add(m.role, m.content));
      if (data.messages.length) suggestions.hidden = true;
    } catch (e) { /* history is optional */ }
  }

  async function send(text) {
    text = text.trim();
    if (!text || busy) return;
    busy = true; sendBtn.disabled = true; suggestions.hidden = true;
    add("user", text);
    input.value = ""; input.style.height = "";
    const typing = add("assistant", "");
    typing.innerHTML = '<span class="chat-typing"><span></span><span></span><span></span></span>';
    try {
      const res = await fetch(messageUrl, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      typing.remove();
      add("assistant", data.reply || data.error || "Sorry, something went wrong.");
      addCards(data.tours);
    } catch (e) {
      typing.remove();
      add("assistant", "I'm having trouble connecting right now. Please try again in a moment.");
    } finally {
      busy = false; sendBtn.disabled = false; input.focus();
    }
  }

  function toggle(open) {
    const willOpen = open ?? !panel.classList.contains("open");
    panel.classList.toggle("open", willOpen);
    root.querySelector(".chat-launcher i").className = willOpen ? "bi bi-x-lg" : "bi bi-chat-dots-fill";
    root.querySelector(".pulse")?.remove();
    if (willOpen) { if (!loaded) loadHistory(); setTimeout(() => input.focus(), 150); }
  }

  root.querySelector(".chat-launcher").addEventListener("click", () => toggle());
  root.querySelector("[data-close]").addEventListener("click", () => toggle(false));
  root.querySelector("[data-reset]").addEventListener("click", async () => {
    await fetch(resetUrl, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": csrf } });
    body.innerHTML = ""; suggestions.hidden = false; add("assistant", welcome);
  });
  sendBtn.addEventListener("click", () => send(input.value));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input.value); } });
  input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 110) + "px"; });
  suggestions.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => send(b.textContent)));
  document.querySelectorAll("[data-open-chat]").forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); toggle(true); }));
})();
