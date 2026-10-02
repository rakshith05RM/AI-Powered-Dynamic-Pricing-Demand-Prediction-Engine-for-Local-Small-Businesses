let forecastChart = null;
let currentHorizon = 7;

async function loadForecast() {
  const productId = document.getElementById("f-product").value;
  if (!productId) return;

  document.getElementById("kpi-current").textContent = "…";
  document.getElementById("kpi-predicted").textContent = "…";
  document.getElementById("kpi-growth").textContent = "…";
  document.getElementById("kpi-confidence").textContent = "…";

  try {
    const data = await ppFetch(`/api/demand/forecast/?product=${productId}&days=${currentHorizon}`);

    document.getElementById("kpi-current").textContent = `${data.current_demand}/day`;
    document.getElementById("kpi-predicted").textContent = `${data.predicted_demand}/day`;
    const growthEl = document.getElementById("kpi-growth");
    growthEl.textContent = `${data.growth_percentage > 0 ? "+" : ""}${data.growth_percentage}%`;
    growthEl.style.color = data.growth_percentage > 0 ? "var(--success)" : data.growth_percentage < 0 ? "var(--danger)" : "inherit";
    document.getElementById("kpi-confidence").textContent = `${data.avg_confidence}%`;

    const histLabels = data.historical.map(h => h.date.slice(5));
    const histValues = data.historical.map(h => h.quantity);
    const foreLabels = data.forecast.map(f => f.prediction_date.slice(5));
    const foreValues = data.forecast.map(f => f.predicted_quantity);

    const labels = [...histLabels, ...foreLabels];
    const historicalSeries = [...histValues, ...Array(foreValues.length).fill(null)];
    const predictedSeries = [...Array(histValues.length - 1).fill(null), histValues[histValues.length - 1], ...foreValues];

    if (forecastChart) forecastChart.destroy();
    forecastChart = new Chart(document.getElementById("forecastChart"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Historical", data: historicalSeries, borderColor: "#14213d", backgroundColor: "transparent", tension: .3, pointRadius: 2 },
          { label: "Predicted", data: predictedSeries, borderColor: "#2563eb", borderDash: [6, 4], backgroundColor: "transparent", tension: .3, pointRadius: 2 },
        ]
      },
      options: { scales: { y: { beginAtZero: true } } }
    });

    const tbody = document.getElementById("forecast-body");
    tbody.innerHTML = data.forecast.map(f => `
      <tr><td>${f.prediction_date}</td><td>${f.predicted_quantity} units</td><td>${f.confidence_score}%</td></tr>
    `).join("");
  } catch (e) {
    ppToast(e.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const productSelect = document.getElementById("f-product");
  if (!productSelect) return;
  productSelect.addEventListener("change", loadForecast);

  document.querySelectorAll("#horizon-tabs button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#horizon-tabs button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentHorizon = parseInt(btn.dataset.days, 10);
      loadForecast();
    });
  });

  loadForecast();
});
