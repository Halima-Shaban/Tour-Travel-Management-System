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
  const bookingForm = document.querySelector("[data-booking-form]");
  if (bookingForm) {
    const price = parseFloat(bookingForm.dataset.price);
    const symbol = bookingForm.dataset.currency;
    const travelers = bookingForm.querySelector("[name=travelers]");
    const out = bookingForm.querySelector("[data-total]");
    const count = bookingForm.querySelector("[data-count]");
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

  // ─── Dynamic newsletter subscribe button ──────────────────────────────────
  const newsletterForm = document.getElementById("newsletter-form");
  if (newsletterForm) {
    const btn      = document.getElementById("newsletter-btn");
    const btnLabel = document.getElementById("newsletter-btn-label");
    const spinner  = document.getElementById("newsletter-btn-spinner");
    const feedback = document.getElementById("newsletter-feedback");
    const emailInput = document.getElementById("newsletter-email");

    // Build the AJAX URL from the form's action: /newsletter/ -> /newsletter/ajax/
    const ajaxUrl = newsletterForm.action.replace(/\/newsletter\/$/, "/newsletter/ajax/");

    newsletterForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      btn.disabled = true;
      btnLabel.classList.add("d-none");
      spinner.classList.remove("d-none");
      feedback.className = "small fw-500 d-none";
      feedback.textContent = "";

      try {
        const res = await fetch(ajaxUrl, {
          method: "POST",
          headers: { "X-CSRFToken": newsletterForm.querySelector("[name=csrfmiddlewaretoken]").value },
          body: new FormData(newsletterForm),
        });
        const data = await res.json();
        const colourMap = { ok: "text-success", info: "text-info", error: "text-danger" };
        feedback.classList.remove("d-none");
        feedback.classList.add(colourMap[data.status] || "text-info");
        feedback.textContent = data.message;

        if (data.status === "ok") {
          btn.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Subscribed!';
          btn.classList.add("btn-success");
          btn.classList.remove("btn-accent");
          emailInput.disabled = true;
        } else {
          btn.disabled = false;
          btnLabel.classList.remove("d-none");
          spinner.classList.add("d-none");
        }
      } catch {
        feedback.classList.remove("d-none");
        feedback.classList.add("text-danger");
        feedback.textContent = "Network error \u2014 please try again.";
        btn.disabled = false;
        btnLabel.classList.remove("d-none");
        spinner.classList.add("d-none");
      }
    });
  }

  // ─── Loading spinner on all standard form submit buttons ──────────────────
  // Covers: contact form, booking "Book now", profile "Save changes",
  //         review "Submit review", forgot-password, sign-in, sign-up.
  // Excluded: newsletter (handled above), cancel-booking (handled below),
  //           sign-out (instant redirect — no feedback needed).
  const SPINNER_ICON = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>`;
  const LOADING_LABELS = {
    "Send message":            "Sending\u2026",
    "Book now":                "Booking\u2026",
    "Save changes":            "Saving\u2026",
    "Submit review":           "Submitting\u2026",
    "Send reset instructions": "Sending\u2026",
    "Save":                    "Saving\u2026",
    "Sign in":                 "Signing in\u2026",
    "Sign up":                 "Creating account\u2026",
    "Search":                  "Searching\u2026",
  };

  document.querySelectorAll("form:not(#newsletter-form) button[type=submit]").forEach((submitBtn) => {
    const frm = submitBtn.closest("form");
    // Skip cancel-booking and sign-out forms
    if (frm && (frm.action || "").includes("cancel")) return;
    if (frm && (frm.action || "").includes("logout")) return;

    frm?.addEventListener("submit", () => {
      if (submitBtn.disabled) return;
      const originalHTML = submitBtn.innerHTML;
      const label = submitBtn.textContent.trim();
      const loadingText = LOADING_LABELS[label] || "Loading\u2026";
      submitBtn.disabled = true;
      submitBtn.innerHTML = SPINNER_ICON + loadingText;
      // Safety: restore after 10 s (e.g. if server returns a validation error)
      setTimeout(() => {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHTML;
      }, 10000);
    });
  });

  // ─── Cancel booking — Bootstrap modal replaces browser confirm() ──────────
  const cancelForms = document.querySelectorAll("form[action*='cancel']");
  if (cancelForms.length) {
    if (!document.getElementById("cancelConfirmModal")) {
      const wrapper = document.createElement("div");
      wrapper.innerHTML = `
<div class="modal fade" id="cancelConfirmModal" tabindex="-1" aria-labelledby="cancelModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content border-0 shadow">
      <div class="modal-header border-0 pb-0">
        <h5 class="modal-title" id="cancelModalLabel">
          <i class="bi bi-exclamation-triangle-fill text-warning me-2"></i>Cancel booking?
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body pt-2">
        This will cancel your booking. Refund eligibility depends on how far in advance you cancel.
        Are you sure you want to proceed?
      </div>
      <div class="modal-footer border-0">
        <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Keep booking</button>
        <button type="button" class="btn btn-danger" id="cancelConfirmBtn">
          <i class="bi bi-x-circle me-1"></i>Yes, cancel
        </button>
      </div>
    </div>
  </div>
</div>`;
      document.body.appendChild(wrapper.firstElementChild);
    }

    const cancelModal = new bootstrap.Modal(document.getElementById("cancelConfirmModal"));
    const confirmBtn  = document.getElementById("cancelConfirmBtn");
    let pendingCancelForm = null;

    cancelForms.forEach((f) => {
      f.removeAttribute("onsubmit"); // drop old confirm()
      f.addEventListener("submit", (e) => {
        e.preventDefault();
        pendingCancelForm = f;
        cancelModal.show();
      });
    });

    confirmBtn.addEventListener("click", () => {
      if (!pendingCancelForm) return;
      cancelModal.hide();
      const cancelBtn = pendingCancelForm.querySelector("button");
      if (cancelBtn) {
        cancelBtn.disabled = true;
        cancelBtn.innerHTML = SPINNER_ICON + "Cancelling\u2026";
      }
      pendingCancelForm.submit();
      pendingCancelForm = null;
    });
  }

  // ─── Smooth scroll for in-page hash anchors (#book, #reviews, #chat) ─────
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", (e) => {
      const id = anchor.getAttribute("href");
      if (id === "#") return;
      const target = document.querySelector(id);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

  // ─── Dark-mode toggle: update icon to reflect current theme ──────────────
  document.addEventListener("themechange", (e) => {
    const themeBtn = document.querySelector("[onclick='toggleTheme()']");
    if (!themeBtn) return;
    const icon = themeBtn.querySelector("i");
    if (icon) icon.className = e.detail === "dark" ? "bi bi-sun-fill" : "bi bi-circle-half";
  });
});
