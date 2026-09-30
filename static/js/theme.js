/* Light/dark theme: runs in <head> to avoid a flash, exposes window.toggleTheme(). */
(function () {
  const KEY = "gotrip-theme";
  const stored = (() => { try { return localStorage.getItem(KEY); } catch (e) { return null; } })();
  const preferred = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  document.documentElement.setAttribute("data-bs-theme", stored || (document.documentElement.dataset.defaultTheme || preferred));
  window.toggleTheme = function () {
    const next = document.documentElement.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-bs-theme", next);
    try { localStorage.setItem(KEY, next); } catch (e) { /* storage unavailable */ }
    document.dispatchEvent(new CustomEvent("themechange", { detail: next }));
  };
})();
