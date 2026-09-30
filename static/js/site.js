/* Public site behaviour. */
document.addEventListener("DOMContentLoaded", () => {
  // Navbar background on scroll (the home page starts transparent over the hero).
  const nav = document.querySelector(".site-nav");
  const backToTop = document.querySelector(".back-to-top");
  const onScroll = () => {
    const y = window.scrollY;
    if (nav && !nav.classList.contains("solid")) nav.classList.toggle("scrolled", y > 40);
    if (backToTop) backToTop.style.display = y > 600 ? "grid" : "none";
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  backToTop?.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

  // Auto-dismiss flash messages.
  document.querySelectorAll(".toast-stack .alert").forEach((el) => {
    setTimeout(() => bootstrap.Alert.getOrCreateInstance(el).close(), 6000);
  });

  // Live total on the booking form.
  const form = document.querySelector("[data-booking-form]");
  if (form) {
    const price = parseFloat(form.dataset.price);
    const symbol = form.dataset.currency;
    const travelers = form.querySelector("[name=travelers]");
    const out = form.querySelector("[data-total]");
    const count = form.querySelector("[data-count]");
    const update = () => {
      const n = Math.max(parseInt(travelers.value || "1", 10), 1);
      out.textContent = symbol + (price * n).toLocaleString(undefined, { maximumFractionDigits: 0 });
      count.textContent = n;
    };
    travelers.addEventListener("input", update);
    update();
  }

  // Star-rating picker in the review form.
  document.querySelectorAll("[data-star-picker]").forEach((picker) => {
    const select = picker.parentElement.querySelector("select[name=rating]");
    const stars = picker.querySelectorAll("i");
    const paint = (v) => stars.forEach((s, i) => { s.className = i < v ? "bi bi-star-fill" : "bi bi-star"; });
    stars.forEach((star, i) => {
      star.addEventListener("click", () => { select.value = i + 1; paint(i + 1); });
      star.addEventListener("mouseenter", () => paint(i + 1));
    });
    picker.addEventListener("mouseleave", () => paint(parseInt(select.value || 0, 10)));
    paint(parseInt(select.value || 5, 10));
    select.value = select.value || 5;
  });
});
