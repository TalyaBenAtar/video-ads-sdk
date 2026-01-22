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
      </tr>
    </thead>
    <tbody>
      ${ads
        .map(
          (a) => `
        <tr>
          <td>${escapeHtml(a.id)}</td>
          <td>${escapeHtml(a.title)}</td>
          <td>${escapeHtml(a.type)}</td>
          <td>${a.enabled ? "✅" : "❌"}</td>
          <td>${escapeHtml((a.categories || []).join(", "))}</td>
        </tr>
      `
        )
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

  logoutBtn?.addEventListener("click", () => {
    clearToken();
    window.location.href = "login.html";
  });

  // Health
  try {
    const health = await apiRequest("/health");
    statusEl.textContent = `API: ${health.status} | DB: ${health.db}`;
  } catch (e) {
    statusEl.textContent = `Status error: ${e.message || "Failed"}`;
  }

  // Ads list
  try {
    const ads = await apiRequest("/ads");
    renderAds(ads, adsEl);
  } catch (e) {
    adsEl.textContent = `Failed to load ads: ${e.message || "Failed"}`;
  }
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
