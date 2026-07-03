// ---- CSRF helper ----
// flask-jwt-extended menaruh csrf_access_token di cookie yang BISA dibaca JS
// (hanya access_token_cookie yang HttpOnly). Ini wajib dikirim untuk request non-GET.
function getCookie(name) {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

const API_BASE = "/api";

async function apiFetch(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers = options.headers ? { ...options.headers } : {};

  // Jangan set Content-Type manual jika body FormData (biar browser set boundary)
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = getCookie("csrf_access_token");
    if (csrf) headers["X-CSRF-TOKEN"] = csrf;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include", // WAJIB: kirim HttpOnly cookie
  });

  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    // response tanpa body (misal 204)
  }

  if (!res.ok) {
    const message = (data && data.error) || `Request gagal (${res.status})`;
    throw new Error(message);
  }
  return data;
}

// ---- Auth guard untuk halaman yang butuh login ----
async function requireAuth() {
  try {
    const data = await apiFetch("/auth/me");
    return data.user;
  } catch (err) {
    window.location.href = "/login";
    return null;
  }
}

function showAlert(elementId, message, isError = true) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.textContent = message;
  el.classList.remove("hidden");
  el.className = `mt-4 p-3 rounded-lg text-sm ${
    isError ? "bg-red-500/10 text-red-400 border border-red-500/30"
            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
  }`;
}

function formatBytes(bytes) {
  if (!bytes) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let val = bytes;
  while (val >= 1024 && i < units.length - 1) {
    val /= 1024;
    i++;
  }
  return `${val.toFixed(1)} ${units[i]}`;
}

function formatDate(iso) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("id-ID", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit"
  });
}