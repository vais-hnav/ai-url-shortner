if (!requireAuth()) {
  // Redirect already triggered by requireAuth.
} else {
  initShell();

const state = {
  mineOffset: 0,
  mineLimit: 10,
  mineNextOffset: null,
  mineFilters: {
    q: "",
    start_date: "",
    end_date: "",
  },
};
const FILTERS_KEY = "dashboard_filters_v1";

function usingGuestMode() {
  return isGuestSession() && !isAuthenticated();
}

const el = {
  logoutBtn: document.getElementById("logoutBtn"),
  mineFiltersForm: document.getElementById("mineFiltersForm"),
  mineError: document.getElementById("mineError"),
  mineMeta: document.getElementById("mineMeta"),
  mineList: document.getElementById("mineList"),
  dashLinks: document.getElementById("dashLinks"),
  dashClicks: document.getElementById("dashClicks"),
  dashWindow: document.getElementById("dashWindow"),
  dashChange: document.getElementById("dashChange"),
  prevPageBtn: document.getElementById("prevPageBtn"),
  nextPageBtn: document.getElementById("nextPageBtn"),
};

async function refreshMine() {
  setFormError(el.mineError, "");
  el.mineMeta.textContent = "Loading URLs...";
  if (usingGuestMode()) {
    const allGuestLinks = getGuestLinks();
    const q = state.mineFilters.q.toLowerCase();
    let filtered = allGuestLinks.filter((item) => {
      if (!q) return true;
      return (
        String(item.short_code || "").toLowerCase().includes(q) ||
        String(item.original_url || "").toLowerCase().includes(q)
      );
    });
    if (state.mineFilters.start_date) {
      filtered = filtered.filter((item) => String(item.created_at || "").slice(0, 10) >= state.mineFilters.start_date);
    }
    if (state.mineFilters.end_date) {
      filtered = filtered.filter((item) => String(item.created_at || "").slice(0, 10) <= state.mineFilters.end_date);
    }

    const total = filtered.length;
    const slice = filtered.slice(state.mineOffset, state.mineOffset + state.mineLimit);
    state.mineNextOffset = state.mineOffset + slice.length < total ? state.mineOffset + state.mineLimit : null;
    el.mineMeta.textContent = `Showing ${formatNumber(slice.length)} of ${formatNumber(total)} guest links`;
    if (!slice.length) {
      el.mineList.innerHTML = `<div class="item">No URLs found for this filter.</div>`;
      return;
    }
    el.mineList.innerHTML = slice
      .map(
        (item) => `<div class="item url-item">
          <div class="url-head">
            <strong>${item.short_code}</strong>
            <span class="pill">${formatNumber(item.total_clicks ?? 0)} clicks</span>
          </div>
          <a href="${item.short_url}" target="_blank" rel="noopener noreferrer">${item.short_url}</a><br>
          ${item.original_url}
          <div class="item-actions">
            <button class="ghost copy-url-btn" data-short-url="${item.short_url}">Copy</button>
            <a class="ghost nav-link" href="/web/url-details.html?code=${encodeURIComponent(item.short_code)}">Details</a>
          </div>
        </div>`
      )
      .join("");
    return;
  }

  const params = new URLSearchParams({
    limit: String(state.mineLimit),
    offset: String(state.mineOffset),
  });
  if (state.mineFilters.q) params.set("q", state.mineFilters.q);
  if (state.mineFilters.start_date) params.set("start_date", state.mineFilters.start_date);
  if (state.mineFilters.end_date) params.set("end_date", state.mineFilters.end_date);

  try {
    const data = await api(`/urls/mine?${params.toString()}`, {
      headers: authHeaders(),
    });
    const loadedCount = Array.isArray(data.items) ? data.items.length : 0;
    el.mineMeta.textContent = `Showing ${formatNumber(loadedCount)} of ${formatNumber(data.total_count || 0)} links`;
    if (!data.items.length) {
      el.mineList.innerHTML = `<div class="item">No URLs found for this filter.</div>`;
    } else {
      el.mineList.innerHTML = data.items
        .map(
          (item) => `<div class="item url-item">
            <div class="url-head">
              <strong>${item.short_code}</strong>
              <span class="pill">${formatNumber(item.total_clicks ?? 0)} clicks</span>
            </div>
            <a href="${item.short_url}" target="_blank" rel="noopener noreferrer">${item.short_url}</a><br>
            ${item.original_url}
            <div class="item-actions">
              <button class="ghost copy-url-btn" data-short-url="${item.short_url}">Copy</button>
              <a class="ghost nav-link" href="/web/url-details.html?code=${encodeURIComponent(item.short_code)}">Details</a>
            </div>
          </div>`
        )
        .join("");
    }
    state.mineNextOffset = data.next_offset;
  } catch (err) {
    if (usingGuestMode()) {
      return refreshMine();
    }
    setFormError(el.mineError, userMessageFromError(err, "Unable to load links."));
    el.mineMeta.textContent = "Failed to load URLs.";
    el.mineList.innerHTML = "";
  }
}

async function refreshQuickOverview() {
  if (usingGuestMode()) {
    const links = getGuestLinks();
    const results = await Promise.all(
      links.map(async (item) => {
        try {
          const data = await api(`/urls/${encodeURIComponent(item.short_code)}/analytics`, {
            headers: authHeaders(),
          });
          return Number(data.total_clicks || 0);
        } catch {
          return Number(item.total_clicks || 0);
        }
      })
    );
    const guestClicks = results.reduce((acc, value) => acc + value, 0);
    el.dashLinks.textContent = formatNumber(links.length);
    el.dashClicks.textContent = formatNumber(guestClicks);
    el.dashWindow.textContent = "guest";
    el.dashChange.textContent = "N/A";
    return;
  }
  try {
    const tzOffsetMinutes = -new Date().getTimezoneOffset();
    const params = new URLSearchParams({
      days: "7",
      tz_offset_minutes: String(tzOffsetMinutes),
      compare_previous: "true",
    });
    const data = await api(`/urls/analytics/overview?${params.toString()}`, {
      headers: authHeaders(),
    });
    el.dashLinks.textContent = formatNumber(data.total_links ?? 0);
    el.dashClicks.textContent = formatNumber(data.total_clicks ?? 0);
    el.dashWindow.textContent = `${data.window_days ?? 7}d`;
    el.dashChange.textContent = formatPercent(data.click_change_percent ?? 0);
  } catch {
    if (usingGuestMode()) {
      return refreshQuickOverview();
    }
    el.dashLinks.textContent = "-";
    el.dashClicks.textContent = "-";
    el.dashChange.textContent = "-";
  }
}

el.logoutBtn.addEventListener("click", () => {
  showToast("Signed out", "info");
  logoutAndRedirect();
});

el.mineFiltersForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = el.mineFiltersForm.querySelector("button[type='submit']");
  const fd = new FormData(el.mineFiltersForm);
  state.mineFilters.q = String(fd.get("q") || "").trim();
  state.mineFilters.start_date = String(fd.get("start_date") || "").trim();
  state.mineFilters.end_date = String(fd.get("end_date") || "").trim();
  localStorage.setItem(FILTERS_KEY, JSON.stringify(state.mineFilters));
  state.mineOffset = 0;
  setButtonLoading(submitBtn, true, "Applying...");
  await refreshMine();
  setButtonLoading(submitBtn, false);
  showToast("Filters applied", "success");
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

el.mineList.addEventListener("click", async (e) => {
  const target = e.target;
  if (!(target instanceof HTMLButtonElement)) return;
  if (!target.classList.contains("copy-url-btn")) return;
  const url = target.dataset.shortUrl || "";
  if (!url) return;
  try {
    await navigator.clipboard.writeText(url);
    showToast("Short URL copied", "success");
  } catch {
    showToast("Copy failed", "error");
  }
});

document.addEventListener("keydown", (e) => {
  const target = e.target;
  const isTyping = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
  if (!isTyping && e.key === "/") {
    e.preventDefault();
    const searchInput = el.mineFiltersForm.querySelector("input[name='q']");
    if (searchInput) searchInput.focus();
  }
  if (!isTyping && e.key.toLowerCase() === "n") {
    window.location.href = "/web/create.html";
  }
});

  (async () => {
    const saved = localStorage.getItem(FILTERS_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        state.mineFilters.q = parsed.q || "";
        state.mineFilters.start_date = parsed.start_date || "";
        state.mineFilters.end_date = parsed.end_date || "";
      } catch {}
    }
    const qInput = el.mineFiltersForm.querySelector("input[name='q']");
    const startInput = el.mineFiltersForm.querySelector("input[name='start_date']");
    const endInput = el.mineFiltersForm.querySelector("input[name='end_date']");
    if (qInput) qInput.value = state.mineFilters.q;
    if (startInput) startInput.value = state.mineFilters.start_date;
    if (endInput) endInput.value = state.mineFilters.end_date;

    await refreshQuickOverview();
    await refreshMine();
    showToast("Dashboard ready", "success");
  })();
}
