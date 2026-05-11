const state = {
  token: localStorage.getItem("token") || "",
  mineOffset: 0,
  mineLimit: 10,
  mineNextOffset: null,
};

const el = {
  sessionState: document.getElementById("sessionState"),
  logoutBtn: document.getElementById("logoutBtn"),
  registerForm: document.getElementById("registerForm"),
  loginForm: document.getElementById("loginForm"),
  shortenForm: document.getElementById("shortenForm"),
  summarizeForm: document.getElementById("summarizeForm"),
  shortenOutput: document.getElementById("shortenOutput"),
  aiOutput: document.getElementById("aiOutput"),
  mineMeta: document.getElementById("mineMeta"),
  mineList: document.getElementById("mineList"),
  prevPageBtn: document.getElementById("prevPageBtn"),
  nextPageBtn: document.getElementById("nextPageBtn"),
  eventLog: document.getElementById("eventLog"),
};

function logEvent(message, data) {
  const line = `[${new Date().toLocaleTimeString()}] ${message}`;
  const payload = data ? `\n${JSON.stringify(data, null, 2)}` : "";
  el.eventLog.textContent = `${line}${payload}\n\n${el.eventLog.textContent}`.slice(0, 6000);
}

function authHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
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
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!response.ok) throw new Error(typeof data === "object" ? JSON.stringify(data) : String(data));
  return data;
}

function setSession(token) {
  state.token = token || "";
  if (state.token) localStorage.setItem("token", state.token);
  else localStorage.removeItem("token");
  el.sessionState.textContent = state.token ? "Signed in" : "Signed out";
}

async function refreshMine() {
  if (!state.token) {
    el.mineMeta.textContent = "Sign in to load your URLs.";
    el.mineList.innerHTML = "";
    return;
  }
  const data = await api(`/urls/mine?limit=${state.mineLimit}&offset=${state.mineOffset}`, {
    headers: authHeaders(),
  });
  el.mineMeta.textContent = `total=${data.total_count} limit=${data.limit} offset=${data.offset} has_more=${data.has_more}`;
  el.mineList.innerHTML = data.items
    .map((item) => `<div class="item"><strong>${item.short_code}</strong><br>${item.original_url}</div>`)
    .join("");
  state.mineNextOffset = data.next_offset;
}

el.logoutBtn.addEventListener("click", async () => {
  setSession("");
  await refreshMine();
  logEvent("Logged out");
});

el.registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(el.registerForm);
  const payload = { email: fd.get("email"), password: fd.get("password") };
  try {
    const data = await api("/auth/register", { method: "POST", body: JSON.stringify(payload) });
    logEvent("Registered user", data);
  } catch (err) {
    logEvent("Register failed", { error: String(err) });
  }
});

el.loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(el.loginForm);
  const payload = { email: fd.get("email"), password: fd.get("password") };
  try {
    const data = await api("/auth/login", { method: "POST", body: JSON.stringify(payload) });
    setSession(data.access_token);
    await refreshMine();
    logEvent("Logged in");
  } catch (err) {
    logEvent("Login failed", { error: String(err) });
  }
});

el.shortenForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(el.shortenForm);
  const payload = {
    original_url: fd.get("original_url"),
    custom_alias: fd.get("custom_alias") || null,
  };
  try {
    const data = await api("/urls", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    el.shortenOutput.textContent = JSON.stringify(data, null, 2);
    await refreshMine();
    logEvent("Created short URL", data);
  } catch (err) {
    el.shortenOutput.textContent = String(err);
    logEvent("Create short URL failed", { error: String(err) });
  }
});

el.summarizeForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(el.summarizeForm);
  const payload = {
    original_url: fd.get("original_url"),
    short_code: fd.get("short_code") || null,
  };
  try {
    const data = await api("/ai/summarize", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    el.aiOutput.textContent = JSON.stringify(data, null, 2);
    logEvent("AI summarize", data);
  } catch (err) {
    el.aiOutput.textContent = String(err);
    logEvent("AI summarize failed", { error: String(err) });
  }
});

el.prevPageBtn.addEventListener("click", async () => {
  state.mineOffset = Math.max(0, state.mineOffset - state.mineLimit);
  await refreshMine();
});
el.nextPageBtn.addEventListener("click", async () => {
  if (state.mineNextOffset == null) return;
  state.mineOffset = state.mineNextOffset;
  await refreshMine();
});

(async () => {
  setSession(state.token);
  await refreshMine();
})();
