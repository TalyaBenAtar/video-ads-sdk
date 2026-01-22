// This file handles page-specific logic (login + dashboard)

function isLoginPage() {
  // also treat /portal as login page because /portal serves login.html
  return (
    window.location.pathname.endsWith("login.html") ||
    window.location.pathname.endsWith("/portal") ||
    window.location.pathname.endsWith("/portal/")
  );
}

function isIndexPage() {
  return window.location.pathname.endsWith("index.html");
}

function requireTokenOrRedirect() {
  const token = getToken();
  if (!token) {
    window.location.href = "login.html";
    return false;
  }
  return true;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseCategories(input) {
  return String(input || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

/* ---------------- Modal helpers ---------------- */

function openModal(mode, ad) {
  const modal = document.getElementById("ad-modal");
  const title = document.getElementById("ad-modal-title");

  const idEl = document.getElementById("ad-id");
  const titleEl = document.getElementById("ad-title");
  const typeEl = document.getElementById("ad-type");
  const enabledEl = document.getElementById("ad-enabled");
  const catsEl = document.getElementById("ad-categories");
  const clickUrlEl = document.getElementById("ad-clickUrl");
  const videoUrlEl = document.getElementById("ad-videoUrl");
  const imageUrlEl = document.getElementById("ad-imageUrl");

  const videoRow = document.getElementById("videoUrl-row");
  const imageRow = document.getElementById("imageUrl-row");

  // Reset defaults
  title.textContent = mode === "edit" ? "Edit Ad" : "Create Ad";
  idEl.value = ad?.id || "";
  titleEl.value = ad?.title || "";
  typeEl.value = ad?.type || "video";
  enabledEl.checked = ad?.enabled !== false;
  catsEl.value = (ad?.categories || []).join(", ");
  clickUrlEl.value = ad?.clickUrl || "";
  videoUrlEl.value = ad?.videoUrl || "";
  imageUrlEl.value = ad?.imageUrl || "";

  // ID is editable only for create
  idEl.disabled = mode === "edit";

  // Toggle url fields based on type
  function syncType() {
    const t = typeEl.value;
    if (t === "video") {
      videoRow.style.display = "block";
      imageRow.style.display = "none";
    } else {
      videoRow.style.display = "none";
      imageRow.style.display = "block";
    }
  }
  typeEl.onchange = syncType;
  syncType();

  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");

  // store mode on form
  const form = document.getElementById("ad-form");
  form.dataset.mode = mode;
}

function closeModal() {
  const modal = document.getElementById("ad-modal");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

/* ---------------- Ads rendering + actions ---------------- */

function renderAds(ads, container) {
  if (!container) return;
  container.innerHTML = "";

  if (!ads || ads.length === 0) {
    container.textContent = "No ads found.";
    return;
  }

  const table = document.createElement("table");
  table.className = "table";

  table.innerHTML = `
    <thead>
      <tr>
        <th>ID</th>
        <th>Title</th>
        <th>Type</th>
        <th>Enabled</th>
        <th>Categories</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      ${ads
        .map((a) => {
          const checked = a.enabled ? "checked" : "";
          return `
            <tr>
              <td>${escapeHtml(a.id)}</td>
              <td>${escapeHtml(a.title)}</td>
              <td>${escapeHtml(a.type)}</td>
              <td>
                <input
                  type="checkbox"
                  class="enabled-toggle"
                  data-id="${escapeHtml(a.id)}"
                  ${checked}
                />
              </td>
              <td>${escapeHtml((a.categories || []).join(", "))}</td>
              <td>
                <button class="row-btn edit-btn" data-id="${escapeHtml(a.id)}">Edit</button>
                <button class="row-btn delete-btn" data-id="${escapeHtml(a.id)}">Delete</button>
              </td>
            </tr>
          `;
        })
        .join("")}
    </tbody>
  `;

  container.appendChild(table);
}

async function loadDashboard() {
  if (!requireTokenOrRedirect()) return;

  const statusEl = document.getElementById("status");
  const adsEl = document.getElementById("ads-list");
  const logoutBtn = document.getElementById("logout-btn");
  const createBtn = document.getElementById("create-ad-btn");

  // modal elements
  const modal = document.getElementById("ad-modal");
  const modalClose = document.getElementById("ad-modal-close");
  const modalCancel = document.getElementById("ad-cancel");
  const form = document.getElementById("ad-form");

  let cachedAds = [];

  logoutBtn?.addEventListener("click", () => {
    clearToken();
    window.location.href = "login.html";
  });

  // Open create modal
  createBtn?.addEventListener("click", () => openModal("create"));

  // Close modal
  modalClose?.addEventListener("click", closeModal);
  modalCancel?.addEventListener("click", closeModal);

  // Click outside modal-card closes modal
  modal?.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  // Health
  try {
    const health = await apiRequest("/health");
    statusEl.textContent = `API: ${health.status} | DB: ${health.db}`;
  } catch (e) {
    statusEl.textContent = `Status error: ${e.message || "Failed"}`;
  }

  async function refreshAds() {
    const ads = await apiRequest("/ads");
    cachedAds = ads || [];
    renderAds(cachedAds, adsEl);
  }

  // initial load
  try {
    await refreshAds();
  } catch (e) {
    adsEl.textContent = `Failed to load ads: ${e.message || "Failed"}`;
  }

  // Row actions + enabled toggle (event delegation)
  adsEl?.addEventListener("click", async (e) => {
    const btn = e.target?.closest("button");
    if (!btn) return;

    const id = btn.getAttribute("data-id");
    if (!id) return;

    if (btn.classList.contains("edit-btn")) {
      const ad = cachedAds.find((x) => x.id === id);
      openModal("edit", ad);
      return;
    }

    if (btn.classList.contains("delete-btn")) {
      if (!confirm(`Delete ad "${id}"?`)) return;
      try {
        await apiRequest(`/ads/${encodeURIComponent(id)}`, { method: "DELETE" });
        await refreshAds();
      } catch (err) {
        alert(err?.message || "Delete failed");
      }
    }
  });

  adsEl?.addEventListener("change", async (e) => {
    const toggle = e.target;
    if (!toggle?.classList?.contains("enabled-toggle")) return;

    const id = toggle.getAttribute("data-id");
    const enabled = !!toggle.checked;

    try {
      await apiRequest(`/ads/${encodeURIComponent(id)}`, {
        method: "PUT",
        body: { enabled },
      });
      // update cache locally
      const ad = cachedAds.find((x) => x.id === id);
      if (ad) ad.enabled = enabled;
    } catch (err) {
      // rollback UI if it failed
      toggle.checked = !enabled;
      alert(err?.message || "Failed to update enabled");
    }
  });

  // Create/Edit submit
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();

    const mode = form.dataset.mode || "create";

    const id = document.getElementById("ad-id").value.trim();
    const title = document.getElementById("ad-title").value.trim();
    const type = document.getElementById("ad-type").value;
    const enabled = document.getElementById("ad-enabled").checked;
    const categories = parseCategories(document.getElementById("ad-categories").value);
    const clickUrl = document.getElementById("ad-clickUrl").value.trim();
    const videoUrl = document.getElementById("ad-videoUrl").value.trim();
    const imageUrl = document.getElementById("ad-imageUrl").value.trim();

    const payload = {
      id,
      title,
      type,
      enabled,
      categories,
      clickUrl,
      videoUrl: type === "video" ? videoUrl : undefined,
      imageUrl: type === "image" ? imageUrl : undefined,
    };

    // Clean undefined fields
    Object.keys(payload).forEach((k) => payload[k] === undefined && delete payload[k]);

    try {
      if (mode === "edit") {
        await apiRequest(`/ads/${encodeURIComponent(id)}`, { method: "PUT", body: payload });
      } else {
        await apiRequest("/ads", { method: "POST", body: payload });
      }
      closeModal();
      await refreshAds();
    } catch (err) {
      alert(err?.message || "Save failed");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  // ---- Login page ----
  if (isLoginPage()) {
    const form = document.getElementById("login-form");
    const errorEl = document.getElementById("error");

    form?.addEventListener("submit", async (e) => {
      e.preventDefault();
      errorEl.textContent = "";

      const username = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value;

      try {
        const token = await apiLogin(username, password);
        setToken(token);
        window.location.href = "index.html";
      } catch (err) {
        errorEl.textContent = err?.message || "Login failed";
      }
    });

    return;
  }

  // ---- Dashboard page ----
  if (isIndexPage()) {
    loadDashboard();
  }
});
