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

// ---- File preview / thumbnail helpers ----
const EXT_ICON_MAP = {
  pdf:  { label: "PDF",  color: "bg-red-500/10 text-red-400" },
  doc:  { label: "DOC",  color: "bg-blue-500/10 text-blue-400" },
  docx: { label: "DOC",  color: "bg-blue-500/10 text-blue-400" },
  ppt:  { label: "PPT",  color: "bg-orange-500/10 text-orange-400" },
  pptx: { label: "PPT",  color: "bg-orange-500/10 text-orange-400" },
  xls:  { label: "XLS",  color: "bg-emerald-500/10 text-emerald-400" },
  xlsx: { label: "XLS",  color: "bg-emerald-500/10 text-emerald-400" },
  zip:  { label: "ZIP",  color: "bg-purple-500/10 text-purple-400" },
  rar:  { label: "RAR",  color: "bg-purple-500/10 text-purple-400" },
  txt:  { label: "TXT",  color: "bg-gray-500/10 text-gray-400" },
};

function getExtension(filename) {
  if (!filename || !filename.includes(".")) return "";
  return filename.split(".").pop().toLowerCase();
}

function isImageMime(mimeType) {
  return typeof mimeType === "string" && mimeType.startsWith("image/");
}

function fileIconBadge(originalFilename, sizeClass) {
  const ext = getExtension(originalFilename);
  const meta = EXT_ICON_MAP[ext] || {
    label: ext ? ext.toUpperCase().slice(0, 4) : "FILE",
    color: "bg-white/5 text-gray-400",
  };
  return `<div class="${sizeClass} rounded-lg border border-border flex items-center justify-center ${meta.color} text-[10px] font-semibold shrink-0">${meta.label}</div>`;
}

// Render thumbnail: <img> untuk gambar (dengan fallback ke badge jika gagal load), badge untuk file lain
function fileThumbHtml(f, sizeClass = "w-12 h-12") {
  if (isImageMime(f.mime_type)) {
    const fallback = fileIconBadge(f.original_filename, sizeClass);
    return `
      <div class="relative ${sizeClass} shrink-0">
        <img src="/api/files/${f.id}/preview" alt="${f.title}"
          class="${sizeClass} rounded-lg object-cover border border-border bg-base"
          loading="lazy"
          onerror="this.classList.add('hidden'); this.nextElementSibling.classList.remove('hidden');" />
        <div class="hidden absolute inset-0">${fallback}</div>
      </div>`;
  }
  return fileIconBadge(f.original_filename, sizeClass);
}

// ---- Reusable search + username filter ----
function buildFilterBarHtml(searchInputId, filterSelectId, opts = {}) {
  const searchPlaceholder = opts.searchPlaceholder || "Cari judul, deskripsi, atau nama file...";
  const filterAllLabel = opts.filterAllLabel || "Semua user";
  return `
    <div class="flex flex-col sm:flex-row gap-2 mb-4">
      <div class="relative flex-1">
        <svg class="w-4 h-4 text-gray-500 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-4.35-4.35M17 10a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input type="text" id="${searchInputId}" placeholder="${searchPlaceholder}"
          class="w-full bg-surface border border-border rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent" />
      </div>
      <select id="${filterSelectId}"
        class="bg-surface border border-border rounded-lg px-3 py-2 text-sm sm:w-56 focus:outline-none focus:ring-2 focus:ring-accent">
        <option value="">${filterAllLabel}</option>
      </select>
    </div>`;
}

function populateUsernameFilter(selectId, usernames, allLabel) {
  const select = document.getElementById(selectId);
  const currentValue = select.value;
  const unique = Array.from(new Set(usernames.filter(Boolean))).sort((a, b) => a.localeCompare(b));
  select.innerHTML =
    `<option value="">${allLabel}</option>` +
    unique.map((u) => `<option value="${u}">${u}</option>`).join("");
  if (unique.includes(currentValue)) select.value = currentValue;
}

function textMatches(query, ...fields) {
  if (!query) return true;
  const q = query.trim().toLowerCase();
  return fields.some((f) => (f || "").toLowerCase().includes(q));
}