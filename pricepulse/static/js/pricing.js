let simChart = null;
let pendingApply = null;

async function loadRecommendations() {
  const tbody = document.getElementById("recs-body");
  if (!tbody) return;
  tbody.innerHTML = ppSkeletonRows(7, 5);
  try {
    const recs = await ppFetch("/api/pricing/recommendations/");
    if (!recs.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-muted">Not enough sales history yet to generate recommendations.</td></tr>`;
      return;
    }
    tbody.innerHTML = recs.map(r => {
      const changeColor = r.price_change_percentage > 0 ? "var(--success)" : r.price_change_percentage < 0 ? "var(--danger)" : "var(--text-muted)";
      return `
      <tr>
        <td><strong>${r.product_name}</strong><div class="text-sm text-muted">${r.reason}</div></td>
        <td>${ppINR(r.current_price)}</td>
        <td>${r.predicted_demand} units</td>
        <td>${ppINR(r.recommended_price)}</td>
        <td style="color:${changeColor};font-weight:600;">${r.price_change_percentage > 0 ? "+" : ""}${r.price_change_percentage}%</td>
        <td>${ppINR(r.expected_revenue)}</td>
        <td><button class="btn btn-accent btn-sm" ${r.is_applied ? "disabled" : ""}
          onclick='openApplyModal(${r.id}, "${r.product_name.replace(/"/g, "")}", ${r.current_price}, ${r.recommended_price})'>
          ${r.is_applied ? "Applied" : "Apply Price"}</button></td>
      </tr>`;
    }).join("");
  } catch (e) { ppToast(e.message, "error"); }
}

function openApplyModal(id, name, current, recommended) {
  pendingApply = id;
  const direction = recommended > current ? "Increase" : recommended < current ? "Decrease" : "Keep";
  document.getElementById("apply-modal-text").textContent =
    `${direction} ${name} from ${ppINR(current)} to ${ppINR(recommended)}?`;
  document.getElementById("apply-modal").classList.add("open");
}

document.addEventListener("click", (e) => {
  if (e.target.id === "apply-cancel") document.getElementById("apply-modal").classList.remove("open");
});

document.addEventListener("DOMContentLoaded", () => {
  const applyConfirm = document.getElementById("apply-confirm");
  if (applyConfirm) {
    applyConfirm.addEventListener("click", async () => {
      try {
        const res = await ppFetch("/api/pricing/apply/", { method: "POST", body: JSON.stringify({ recommendation_id: pendingApply }) });
        ppToast(res.detail, "success");
        document.getElementById("apply-modal").classList.remove("open");
        loadRecommendations();
      } catch (e) { ppToast(e.message, "error"); }
    });
  }

  const refreshBtn = document.getElementById("refresh-recs");
  if (refreshBtn) refreshBtn.addEventListener("click", loadRecommendations);
  if (document.getElementById("recs-body")) loadRecommendations();

  initSimulator();
});

/* ---- Price Simulator ---- */
function initSimulator() {
  const productSelect = document.getElementById("sim-product");
  if (!productSelect) return;
  const slider = document.getElementById("sim-price-slider");

  function setupSliderForProduct() {
    const opt = productSelect.options[productSelect.selectedIndex];
    const min = parseFloat(opt.dataset.min), max = parseFloat(opt.dataset.max), current = parseFloat(opt.dataset.current);
    slider.min = min; slider.max = max; slider.step = Math.max((max - min) / 100, 1);
    slider.value = current;
    document.getElementById("sim-current-price").textContent = ppINR(current);
    updateSimCurve();
    runSimulation();
  }

  async function updateSimCurve() {
    const opt = productSelect.options[productSelect.selectedIndex];
    const min = parseFloat(opt.dataset.min), max = parseFloat(opt.dataset.max);
    const points = 10;
    const prices = Array.from({ length: points }, (_, i) => Math.round(min + (i * (max - min)) / (points - 1)));
    try {
      const results = await Promise.all(prices.map(p =>
        ppFetch("/api/pricing/simulate/", { method: "POST", body: JSON.stringify({ product: productSelect.value, price: p }) })
      ));
      if (simChart) simChart.destroy();
      simChart = new Chart(document.getElementById("simChart"), {
        type: "line",
        data: {
          labels: prices.map(p => `₹${p}`),
          datasets: [{ label: "Estimated Demand", data: results.map(r => r.estimated_demand), borderColor: "#2563eb", tension: .35, pointRadius: 3 }]
        },
        options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, title: { display: true, text: "Units" } }, x: { title: { display: true, text: "Price" } } } }
      });
    } catch (e) { /* non-fatal */ }
  }

  async function runSimulation() {
    const price = parseFloat(slider.value);
    document.getElementById("sim-price-label").textContent = ppINR(price);
    try {
      const result = await ppFetch("/api/pricing/simulate/", { method: "POST", body: JSON.stringify({ product: productSelect.value, price }) });
      document.getElementById("sim-demand").textContent = `${result.estimated_demand} units`;
      document.getElementById("sim-revenue").textContent = ppINR(result.estimated_revenue);
      document.getElementById("sim-current-revenue").textContent = ppINR(result.current_revenue);
      const change = result.revenue_change_percentage;
      const changeEl = document.getElementById("sim-revenue-change");
      changeEl.textContent = `${change > 0 ? "Potential increase of +" : change < 0 ? "Potential decrease of " : "No change: "}${change}%`;
      changeEl.style.color = change > 0 ? "var(--success)" : change < 0 ? "var(--danger)" : "var(--text-muted)";
    } catch (e) { ppToast(e.message, "error"); }
  }

  productSelect.addEventListener("change", setupSliderForProduct);
  slider.addEventListener("input", debounceSim(runSimulation, 250));
  setupSliderForProduct();
}

function debounceSim(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}
