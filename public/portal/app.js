// This file handles page-specific logic (login now, dashboard later)

function isLoginPage() {
    return window.location.pathname.endsWith("login.html");
}

function isIndexPage() {
    return window.location.pathname.endsWith("index.html") || window.location.pathname.endsWith("/portal/") || window.location.pathname.endsWith("/portal");
}

document.addEventListener("DOMContentLoaded", async () => {
    // ---- Login page ----
    if (isLoginPage()) {
        const form = document.getElementById("login-form");
        const errorEl = document.getElementById("error");

        form.addEventListener("submit", async (e) => {
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
        // Guard: must be logged in
        if (!getToken()) {
            window.location.href = "login.html";
            return;
        }

        // Logout
        const logoutBtn = document.getElementById("logout-btn");
        logoutBtn.addEventListener("click", () => {
            clearToken();
            window.location.href = "login.html";
        });

        // Tiny “status” check: call a protected endpoint? (we’ll keep it safe and do public /health)
        const statusEl = document.getElementById("status");
        try {
            const data = await fetch(`${API_BASE_URL}/health`).then(r => r.json());
            statusEl.textContent = `API: ${data.status} | DB: ${data.db}`;
        } catch (e) {
            statusEl.textContent = "Could not reach API.";
        }
    }
});
