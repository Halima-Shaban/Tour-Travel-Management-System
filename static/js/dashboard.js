/* Shared dashboard behaviour (admin + guide) and Chart.js helpers. */
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-sidebar-toggle]").forEach((btn) =>
    btn.addEventListener("click", () => document.body.classList.toggle("sidebar-open"))
  );
  document.querySelector(".sidebar-backdrop")?.addEventListener("click", () => document.body.classList.remove("sidebar-open"));
  document.querySelectorAll(".toast-stack .alert").forEach((el) =>
    setTimeout(() => bootstrap.Alert.getOrCreateInstance(el).close(), 5000)
  );
  document.querySelectorAll("[data-confirm]").forEach((el) =>
    el.addEventListener("submit", (e) => { if (!confirm(el.dataset.confirm)) e.preventDefault(); })
  );
  // Auto-submit filter selects.
  document.querySelectorAll("[data-autosubmit] select").forEach((s) => s.addEventListener("change", () => s.form.submit()));
});

window.Dash = (() => {
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const charts = [];
  const palette = () => [css("--brand"), css("--accent"), "#3b82f6", "#8b5cf6", "#f43f5e", "#14b8a6", "#64748b"];

  function baseOptions() {
    const dark = document.documentElement.getAttribute("data-bs-theme") === "dark";
    const grid = dark ? "rgba(148,163,184,.12)" : "rgba(15,23,42,.06)";
    const text = dark ? "#94a3b8" : "#64748b";
    return {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { labels: { color: text, usePointStyle: true, boxWidth: 8 } }, tooltip: { padding: 10, cornerRadius: 8 } },
      scales: {
        x: { grid: { display: false }, ticks: { color: text }, border: { display: false } },
        y: { grid: { color: grid }, ticks: { color: text }, border: { display: false }, beginAtZero: true },
      },
    };
  }

  function make(id, builder) {
    const el = document.getElementById(id);
    if (!el || !window.Chart) return;
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    const render = () => {
      const existing = Chart.getChart(el);
      if (existing) existing.destroy();
      new Chart(el, builder(baseOptions(), palette(), el.getContext("2d")));
    };
    render();
    charts.push(render);
  }

  function gradient(ctx, color) {
    const g = ctx.createLinearGradient(0, 0, 0, 300);
    g.addColorStop(0, color + "55");
    g.addColorStop(1, color + "00");
    return g;
  }

  document.addEventListener("themechange", () => charts.forEach((r) => r()));
  return { make, gradient, palette };
})();
