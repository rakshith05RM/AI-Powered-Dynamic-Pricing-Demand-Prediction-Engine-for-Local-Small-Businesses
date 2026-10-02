let ppProducts = [];
let ppDeleteTargetId = null;

const catBadgeColor = { bakery: "warning", beverages: "info", dairy: "healthy", grocery: "healthy",
  snacks: "warning", clothing: "info", electronics: "critical", pharmacy: "overstocked", other: "low" };

async function loadProducts() {
  const tbody = document.getElementById("products-body");
  tbody.innerHTML = ppSkeletonRows(8, 5);
  try {
    const search = document.getElementById("search-input").value;
    const category = document.getElementById("category-filter").value;
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (category) params.set("category", category);
    const data = await ppFetch(`/api/products/?${params.toString()}`);
    ppProducts = data.results || data;
    renderProducts();
  } catch (e) {
    ppToast(e.message, "error");
  }
}

function renderProducts() {
  const tbody = document.getElementById("products-body");
  const empty = document.getElementById("products-empty");
  if (!ppProducts.length) {
    tbody.innerHTML = "";
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";
  tbody.innerHTML = ppProducts.map(p => `
    <tr>
      <td><strong>${p.product_name}</strong></td>
      <td><span class="badge badge-${catBadgeColor[p.category] || 'info'}">${p.category}</span></td>
      <td class="text-muted">${p.sku}</td>
      <td>${ppINR(p.cost_price)}</td>
      <td>${ppINR(p.current_price)}</td>
      <td>${p.stock_quantity}</td>
      <td>${p.reorder_level}</td>
      <td class="flex gap-8">
        <button class="btn btn-secondary btn-sm" onclick="openEditProduct(${p.id})">Edit</button>
        <button class="btn btn-danger btn-sm" onclick="openDeleteProduct(${p.id})">Delete</button>
      </td>
    </tr>
  `).join("");
}

function fillForm(p) {
  document.getElementById("p-id").value = p ? p.id : "";
  document.getElementById("p-name").value = p ? p.product_name : "";
  document.getElementById("p-category").value = p ? p.category : "other";
  document.getElementById("p-sku").value = p ? p.sku : "";
  document.getElementById("p-description").value = p ? p.description : "";
  document.getElementById("p-cost").value = p ? p.cost_price : "";
  document.getElementById("p-price").value = p ? p.current_price : "";
  document.getElementById("p-min").value = p ? p.minimum_price : "";
  document.getElementById("p-max").value = p ? p.maximum_price : "";
  document.getElementById("p-stock").value = p ? p.stock_quantity : "";
  document.getElementById("p-reorder").value = p ? p.reorder_level : "";
  document.getElementById("p-error").style.display = "none";
}

function openAddProduct() {
  document.getElementById("product-modal-title").textContent = "Add Product";
  fillForm(null);
  document.getElementById("product-modal").classList.add("open");
}

function openEditProduct(id) {
  const p = ppProducts.find(x => x.id === id);
  document.getElementById("product-modal-title").textContent = "Edit Product";
  fillForm(p);
  document.getElementById("product-modal").classList.add("open");
}

function openDeleteProduct(id) {
  ppDeleteTargetId = id;
  document.getElementById("delete-modal").classList.add("open");
}

document.getElementById("add-product-btn").addEventListener("click", openAddProduct);
document.getElementById("product-cancel").addEventListener("click", () => document.getElementById("product-modal").classList.remove("open"));
document.getElementById("delete-cancel").addEventListener("click", () => document.getElementById("delete-modal").classList.remove("open"));
document.getElementById("search-input").addEventListener("input", debounce(loadProducts, 350));
document.getElementById("category-filter").addEventListener("change", loadProducts);

document.getElementById("delete-confirm").addEventListener("click", async () => {
  try {
    await ppFetch(`/api/products/${ppDeleteTargetId}/`, { method: "DELETE" });
    ppToast("Product deleted successfully", "success");
    document.getElementById("delete-modal").classList.remove("open");
    loadProducts();
  } catch (e) { ppToast(e.message, "error"); }
});

document.getElementById("product-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("p-id").value;
  const payload = {
    product_name: document.getElementById("p-name").value,
    category: document.getElementById("p-category").value,
    sku: document.getElementById("p-sku").value,
    description: document.getElementById("p-description").value,
    cost_price: document.getElementById("p-cost").value,
    current_price: document.getElementById("p-price").value,
    minimum_price: document.getElementById("p-min").value,
    maximum_price: document.getElementById("p-max").value,
    stock_quantity: document.getElementById("p-stock").value,
    reorder_level: document.getElementById("p-reorder").value,
  };
  try {
    if (id) {
      await ppFetch(`/api/products/${id}/`, { method: "PUT", body: JSON.stringify(payload) });
      ppToast("Product updated successfully", "success");
    } else {
      await ppFetch(`/api/products/`, { method: "POST", body: JSON.stringify(payload) });
      ppToast("Product created successfully", "success");
    }
    document.getElementById("product-modal").classList.remove("open");
    loadProducts();
  } catch (e) {
    const err = document.getElementById("p-error");
    err.textContent = e.message;
    err.style.display = "block";
  }
});

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

document.addEventListener("DOMContentLoaded", loadProducts);
