/* Booking chat between traveler, guide and office: send via fetch, poll for new messages. */
(() => {
  const box = document.getElementById("chat");
  if (!box) return;
  const list = box.querySelector(".chat-box-body");
  const form = box.querySelector(".chat-box-form");
  const input = form?.querySelector("textarea");
  const csrf = document.cookie.split("; ").find((c) => c.startsWith("csrftoken="))?.split("=")[1] || box.dataset.csrf;
  let lastId = 0;
  let timer;

  const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function render(messages) {
    if (!messages.length) return;
    box.querySelector(".chat-empty")?.remove();
    const atBottom = list.scrollHeight - list.scrollTop - list.clientHeight < 60;
    for (const m of messages) {
      if (m.id <= lastId) continue;
      lastId = m.id;
      const el = document.createElement("div");
      el.className = `bubble-row ${m.mine ? "mine" : ""}`;
      el.innerHTML = `<div class="bubble" dir="auto">${esc(m.body).replace(/\n/g, "<br>")}</div>
        <div class="meta">${m.mine ? "You" : `${esc(m.sender)} · <span class="role">${m.role}</span>`} · ${m.time}</div>`;
      list.appendChild(el);
    }
    if (atBottom || messages.some((m) => m.mine)) list.scrollTop = list.scrollHeight;
  }

  async function poll() {
    try {
      const res = await fetch(`${box.dataset.pollUrl}?after=${lastId}`, { credentials: "same-origin" });
      if (res.ok) render((await res.json()).messages);
    } catch (e) { /* offline - try again next tick */ }
  }

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(async () => { if (!document.hidden) await poll(); schedule(); }, 5000);
  }

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = input.value.trim();
    if (!body) return;
    const btn = form.querySelector("button");
    btn.disabled = true;
    try {
      const res = await fetch(box.dataset.sendUrl, {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify({ body }),
      });
      const data = await res.json();
      if (res.ok) { input.value = ""; input.style.height = ""; render([data.message]); }
      else alert(data.error || "Message not sent.");
    } finally { btn.disabled = false; input.focus(); }
  });
  input?.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
  input?.addEventListener("input", () => { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 120) + "px"; });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) poll(); });

  poll().then(() => { list.scrollTop = list.scrollHeight; });
  schedule();
})();
