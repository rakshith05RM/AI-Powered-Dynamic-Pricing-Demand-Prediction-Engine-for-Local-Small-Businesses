const statusClass = { Critical: "critical", Low: "low", Healthy: "healthy", Overstocked: "overstocked" };

async function loadInventory() {
  const tbody = document.getElementById("inventory-body");
  try {
    const rows = await ppFetch("/api/inventory/");
    tbody.innerHTML = rows.length ? rows.map(r => `
      <tr>
        <td><strong>${r.product_name}</strong></td>
        <td>${r.stock}</td>
        <td>${r.daily_demand}</td>
        <td>${r.days_remaining !== null ? r.days_remaining + " days" : "—"}</td>
        <td><span class="badge badge-${statusClass[r.status] || 'info'}">${r.status}</span></td>
        <td class="text-sm">${r.recommendation}</td>
      </tr>
    `).join("") : `<tr><td colspan="6" class="text-muted">No products yet.</td></tr>`;
  } catch (e) { ppToast(e.message, "error"); }
}

document.addEventListener("DOMContentLoaded", loadInventory);
