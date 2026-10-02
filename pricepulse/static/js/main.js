/* PricePulse shared frontend utilities: theme, sidebar, toasts, fetch helper */

(function () {
  const root = document.documentElement;
  const saved = localStorage.getItem("pp-theme") || "light";
  applyTheme(saved);

  function applyTheme(mode) {
    if (mode === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.setAttribute("data-theme", prefersDark ? "dark" : "light");
    } else {
      root.setAttribute("data-theme", mode);
    }
    localStorage.setItem("pp-theme", mode);
  }
  window.ppSetTheme = applyTheme;

  document.addEventListener("DOMContentLoaded", () => {
    const themeToggle = document.getElementById("theme-toggle");
    if (themeToggle) {
      themeToggle.addEventListener("click", () => {
        const current = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(current);
      });
    }

    const hamburger = document.getElementById("hamburger");
    const sidebar = document.getElementById("sidebar");
    if (hamburger && sidebar) {
      hamburger.addEventListener("click", () => sidebar.classList.toggle("open"));
    }
  });
})();

/* ---- Toasts ---- */
function ppToast(message, type = "default") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

/* ---- CSRF-aware fetch wrapper for DRF/session auth ---- */
function ppGetCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

async function ppFetch(url, options = {}) {
  const opts = { credentials: "same-origin", headers: { ...(options.headers || {}) }, ...options };
  const method = (opts.method || "GET").toUpperCase();
  if (method !== "GET") {
    opts.headers["X-CSRFToken"] = ppGetCookie("csrftoken");
    if (opts.body && !(opts.body instanceof FormData)) {
      opts.headers["Content-Type"] = "application/json";
    }
  }
  const res = await fetch(url, opts);
  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const message = (data && (data.detail || JSON.stringify(data))) || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

/* ---- Formatting helpers ---- */
function ppINR(value) {
  const n = Number(value || 0);
  if (Math.abs(n) >= 1e7) return "₹" + (n / 1e7).toFixed(2) + "Cr";
  if (Math.abs(n) >= 1e5) return "₹" + (n / 1e5).toFixed(2) + "L";
  return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function ppSkeletonRows(cols, rows = 4) {
  let html = "";
  for (let r = 0; r < rows; r++) {
    html += "<tr>";
    for (let c = 0; c < cols; c++) html += `<td><div class="skeleton" style="height:14px;width:${60 + (c % 3) * 20}%"></div></td>`;
    html += "</tr>";
  }
  return html;
}
