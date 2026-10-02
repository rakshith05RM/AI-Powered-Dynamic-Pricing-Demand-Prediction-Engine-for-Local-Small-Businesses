let currentFilter = "all";
const severityBadge = { critical: "critical", warning: "low", info: "info" };

async function loadAlerts() {
  const list = document.getElementById("alerts-list");
  const empty = document.getElementById("alerts-empty");
  const url = currentFilter === "unread" ? "/api/alerts/?unread=true" : "/api/alerts/";
  try {
    const alerts = await ppFetch(url);
    if (!alerts.length) {
      list.innerHTML = "";
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";
    list.innerHTML = alerts.map(a => `
      <li class="flex-between" style="padding:14px 0; border-bottom:1px solid var(--border);">
        <div class="flex gap-12" style="align-items:flex-start;">
          <span class="badge badge-${severityBadge[a.severity] || 'info'}" style="margin-top:2px;">${a.severity}</span>
          <div>
            <strong>${a.title}</strong>
            <div class="text-sm text-muted" style="margin-top:4px;">${a.message}</div>
            <div class="text-sm text-muted" style="margin-top:4px;">${new Date(a.created_at).toLocaleString()}${a.product_name ? " · " + a.product_name : ""}</div>
          </div>
        </div>
        ${a.is_read ? `<span class="text-sm text-muted">Read</span>` : `<button class="btn btn-secondary btn-sm" onclick="markRead(${a.id})">Mark as read</button>`}
      </li>
    `).join("");
  } catch (e) { ppToast(e.message, "error"); }
}

async function markRead(id) {
  try {
    await ppFetch(`/api/alerts/${id}/read/`, { method: "POST" });
    loadAlerts();
  } catch (e) { ppToast(e.message, "error"); }
}

document.querySelectorAll("#alert-filter-tabs button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#alert-filter-tabs button").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    loadAlerts();
  });
});

document.addEventListener("DOMContentLoaded", loadAlerts);
