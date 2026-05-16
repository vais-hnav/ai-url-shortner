const TOKEN_KEY = "token";
const GUEST_MODE_KEY = "guest_mode";
const GUEST_LINKS_KEY = "guest_links";

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function isAuthenticated() {
  return Boolean(getToken());
}

function isGuestSession() {
  return sessionStorage.getItem(GUEST_MODE_KEY) === "1";
}

function setGuestSession(enabled) {
  if (enabled) {
    sessionStorage.setItem(GUEST_MODE_KEY, "1");
  } else {
    sessionStorage.removeItem(GUEST_MODE_KEY);
    sessionStorage.removeItem(GUEST_LINKS_KEY);
  }
  syncAuthUI();
}

function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    sessionStorage.removeItem(GUEST_MODE_KEY);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (response.status === 401) {
    setToken("");
    syncAuthUI();
  }
  if (!response.ok) {
    const detail =
      typeof data === "object" && data !== null
        ? data.detail || "Something went wrong. Please try again."
        : String(data);
    throw new Error(detail);
  }
  return data;
}

function requireAuth(redirectTo = "/web/auth.html") {
  if (!getToken() && !isGuestSession()) {
    window.location.href = redirectTo;
    return false;
  }
  return true;
}

function logoutAndRedirect(redirectTo = "/web/auth.html") {
  setToken("");
  window.location.href = redirectTo;
}

function initShell() {
  const path = window.location.pathname === "/web/" ? "/web/index.html" : window.location.pathname;
  document.querySelectorAll(".nav-link").forEach((link) => {
    const href = link.getAttribute("href") || "";
    if (href && path === href) {
      link.classList.add("active");
    }
  });
  syncAuthUI();
}

function syncAuthUI() {
  const authed = isAuthenticated() || isGuestSession();
  document.querySelectorAll(".requires-auth").forEach((node) => {
    node.classList.toggle("hidden", !authed);
  });
  document.querySelectorAll(".guest-only").forEach((node) => {
    node.classList.toggle("hidden", authed);
  });
}

function getGuestLinks() {
  const raw = sessionStorage.getItem(GUEST_LINKS_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item) => item && item.short_code && item.short_url);
  } catch {
    return [];
  }
}

function saveGuestLinks(links) {
  sessionStorage.setItem(GUEST_LINKS_KEY, JSON.stringify(links));
}

function addGuestLink(link) {
  const existing = getGuestLinks();
  const next = [link, ...existing.filter((item) => item.short_code !== link.short_code)].slice(0, 100);
  saveGuestLinks(next);
}

function ensureToastRoot() {
  let root = document.getElementById("toastRoot");
  if (!root) {
    root = document.createElement("div");
    root.id = "toastRoot";
    root.className = "toast-root";
    document.body.appendChild(root);
  }
  return root;
}

function showToast(message, tone = "info") {
  const root = ensureToastRoot();
  const item = document.createElement("div");
  item.className = `toast toast-${tone}`;
  item.textContent = message;
  root.appendChild(item);
  setTimeout(() => {
    item.classList.add("hide");
    setTimeout(() => item.remove(), 220);
  }, 2200);
}

function setButtonLoading(button, loading, loadingText = "Loading...") {
  if (!button) return;
  if (loading) {
    button.dataset.originalText = button.textContent || "";
    button.textContent = loadingText;
    button.disabled = true;
  } else {
    if (button.dataset.originalText) {
      button.textContent = button.dataset.originalText;
    }
    button.disabled = false;
  }
}

function setFormError(target, message = "") {
  if (!target) return;
  target.textContent = message;
}

function userMessageFromError(err, fallback = "Something went wrong. Please try again.") {
  const raw = String(err || "").replace(/^Error:\s*/, "").trim();
  if (!raw) return fallback;
  if (raw.includes("{") && raw.includes("}")) return fallback;
  if (/network|failed to fetch|load failed/i.test(raw)) {
    return "Unable to reach the server. Please check your connection and try again.";
  }
  return raw;
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}

function formatNumber(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(num);
}

function formatPercent(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "0%";
  const fixed = Math.abs(num) >= 10 ? num.toFixed(1) : num.toFixed(2);
  return `${fixed}%`;
}

function initGlobalShortcuts() {
  window.addEventListener("keydown", (event) => {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    const active = document.activeElement;
    if (active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA")) return;
    const searchInput = document.querySelector("input[name='q']");
    if (searchInput instanceof HTMLInputElement) {
      event.preventDefault();
      searchInput.focus();
      searchInput.select();
    }
  });
}
