let ppSelectedFile = null;

async function loadSales() {
  const tbody = document.getElementById("sales-body");
  tbody.innerHTML = ppSkeletonRows(6, 6);
  const params = new URLSearchParams();
  const product = document.getElementById("filter-product").value;
  const from = document.getElementById("filter-from").value;
  const to = document.getElementById("filter-to").value;
  if (product) params.set("product", product);
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  try {
    const data = await ppFetch(`/api/sales/?${params.toString()}`);
    const rows = data.results || data;
    tbody.innerHTML = rows.length ? rows.map(r => `
      <tr><td>${r.sale_date}</td><td>${r.product_name}</td><td>${r.quantity_sold}</td>
      <td>${ppINR(r.selling_price)}</td><td>${r.discount_percentage}%</td><td>${ppINR(r.revenue)}</td></tr>
    `).join("") : `<tr><td colspan="6" class="text-muted">No sales data yet. Import your historical sales data to generate demand forecasts.</td></tr>`;
  } catch (e) { ppToast(e.message, "error"); }
}

document.getElementById("sale-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    product: document.getElementById("s-product").value,
    sale_date: document.getElementById("s-date").value,
    quantity_sold: document.getElementById("s-qty").value,
    selling_price: document.getElementById("s-price").value,
    discount_percentage: document.getElementById("s-discount").value || 0,
  };
  try {
    await ppFetch("/api/sales/", { method: "POST", body: JSON.stringify(payload) });
    ppToast("Sale added successfully", "success");
    e.target.reset();
    loadSales();
  } catch (err) { ppToast(err.message, "error"); }
});

const dropZone = document.getElementById("drop-zone");
const csvInput = document.getElementById("csv-input");
dropZone.addEventListener("click", () => csvInput.click());
dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.style.borderColor = "var(--accent)"; });
dropZone.addEventListener("dragleave", () => { dropZone.style.borderColor = "var(--border)"; });
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.style.borderColor = "var(--border)";
  if (e.dataTransfer.files.length) setSelectedFile(e.dataTransfer.files[0]);
});
csvInput.addEventListener("change", () => { if (csvInput.files.length) setSelectedFile(csvInput.files[0]); });

function setSelectedFile(file) {
  ppSelectedFile = file;
  document.getElementById("drop-label").textContent = `Selected: ${file.name}`;
  document.getElementById("import-btn").disabled = false;
}

document.getElementById("import-btn").addEventListener("click", async () => {
  if (!ppSelectedFile) return;
  const formData = new FormData();
  formData.append("file", ppSelectedFile);
  try {
    const result = await ppFetch("/api/sales/import/", { method: "POST", body: formData });
    document.getElementById("import-result").innerHTML = `
      <div class="card" style="padding:12px;">
        <div class="text-sm"><strong>${result.rows_detected}</strong> rows detected · 
        <span style="color:var(--success)">${result.valid_records} valid</span> · 
        <span style="color:var(--danger)">${result.invalid_records} invalid</span></div>
        ${result.errors.length ? `<div class="text-sm text-muted" style="margin-top:8px;max-height:120px;overflow-y:auto;">${
          result.errors.map(e => `Row ${e.row}: ${e.errors.join(", ")}`).join("<br>")}</div>` : ""}
      </div>`;
    ppToast("Sales data imported successfully", "success");
    loadSales();
  } catch (e) { ppToast(e.message, "error"); }
});

["filter-product", "filter-from", "filter-to"].forEach(id =>
  document.getElementById(id).addEventListener("change", loadSales));

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("s-date").valueAsDate = new Date();
  loadSales();
});
