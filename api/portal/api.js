// Change this if your API base url changes:
const API_BASE_URL = "";

function getToken() {
    return localStorage.getItem("admin_token");
}

function setToken(token) {
    localStorage.setItem("admin_token", token);
}

function clearToken() {
    localStorage.removeItem("admin_token");
}

async function apiRegister(username, password, clientId) {
  return apiRequest("/auth/register", {
    method: "POST",
    body: { username, password, clientId },
  }).then((r) => r.token);
}


async function apiLogin(username, password) {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
        const msg = data.error || `Login failed (${res.status})`;
        throw new Error(msg);
    }

    if (!data.token) {
        throw new Error("Login response missing token");
    }

    return data.token;
}

async function apiAddApp(clientId) {
  return apiRequest("/apps", {
    method: "POST",
    body: { clientId },
  });
}

async function apiAddApp(clientId) {
  return apiRequest("/auth/add-app", {
    method: "POST",
    body: { clientId },
  });
}

async function apiRequest(path, { method = "GET", body } = {}) {
    const token = getToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_BASE_URL}${path}`, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        const msg = data.error || `Request failed (${res.status})`;
        throw new Error(msg);
    }
    return data;
}
