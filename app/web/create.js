initShell();
if (!isAuthenticated()) {
  setGuestSession(true);
}

const el = {
  logoutBtn: document.getElementById("logoutBtn"),
  shortenForm: document.getElementById("shortenForm"),
  shortenError: document.getElementById("shortenError"),
  shortUrlActions: document.getElementById("shortUrlActions"),
  copyShortUrlBtn: document.getElementById("copyShortUrlBtn"),
  viewDetailsBtn: document.getElementById("viewDetailsBtn"),
  shortenOutput: document.getElementById("shortenOutput"),
  resultShortCode: document.getElementById("resultShortCode"),
  resultClicks: document.getElementById("resultClicks"),
  resultShortUrl: document.getElementById("resultShortUrl"),
  resultOriginalUrl: document.getElementById("resultOriginalUrl"),
  resultAiSection: document.getElementById("resultAiSection"),
  resultAiSummary: document.getElementById("resultAiSummary"),
  resultAiTags: document.getElementById("resultAiTags"),
};
let lastShortUrl = "";

function clearResult() {
  el.shortenOutput.classList.add("hidden");
  el.resultShortCode.textContent = "-";
  el.resultClicks.textContent = "0 clicks";
  el.resultShortUrl.textContent = "";
  el.resultShortUrl.removeAttribute("href");
  el.resultOriginalUrl.textContent = "";
  el.resultAiSummary.textContent = "";
  el.resultAiTags.innerHTML = "";
  el.resultAiSection.classList.add("hidden");
  if (el.viewDetailsBtn) {
    el.viewDetailsBtn.setAttribute("href", "#");
  }
}

function renderTags(tags) {
  const list = Array.isArray(tags) ? tags.filter(Boolean) : [];
  el.resultAiTags.innerHTML = "";
  if (!list.length) {
    el.resultAiTags.textContent = "No tags yet";
    return;
  }
  const frag = document.createDocumentFragment();
  for (const tag of list) {
    const chip = document.createElement("span");
    chip.className = "tag";
    chip.textContent = String(tag);
    frag.appendChild(chip);
  }
  el.resultAiTags.appendChild(frag);
}

function renderResult(data) {
  const shortUrl = data.short_url || "";
  const originalUrl = data.original_url || "";
  lastShortUrl = shortUrl;
  el.resultShortCode.textContent = data.short_code || "-";
  el.resultClicks.textContent = `${formatNumber(data.total_clicks || 0)} clicks`;
  el.resultShortUrl.textContent = shortUrl;
  if (shortUrl) {
    el.resultShortUrl.setAttribute("href", shortUrl);
  } else {
    el.resultShortUrl.removeAttribute("href");
  }
  el.resultOriginalUrl.textContent = originalUrl;

  const summary = (data.ai_summary || "").trim();
  const tags = Array.isArray(data.ai_tags) ? data.ai_tags : [];
  const hasAi = Boolean(summary) || tags.length > 0;
  el.resultAiSection.classList.toggle("hidden", !hasAi);
  if (hasAi) {
    el.resultAiSummary.textContent = summary || "Summary unavailable right now.";
    renderTags(tags);
  }

  el.shortUrlActions.classList.toggle("hidden", !shortUrl);
  if (el.viewDetailsBtn && data.short_code) {
    el.viewDetailsBtn.setAttribute("href", `/web/url-details.html?code=${encodeURIComponent(data.short_code)}`);
  }
  el.shortenOutput.classList.remove("hidden");
}

el.logoutBtn.addEventListener("click", () => {
  showToast("Signed out", "info");
  logoutAndRedirect();
});

el.shortenForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = el.shortenForm.querySelector("button[type='submit']");
  setFormError(el.shortenError, "");
  const fd = new FormData(el.shortenForm);
  const payload = {
    original_url: fd.get("original_url"),
    custom_alias: fd.get("custom_alias") || null,
  };
  try {
    setButtonLoading(submitBtn, true, "Creating...");
    clearResult();
    const data = await api("/urls", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    renderResult(data);
    if (isGuestSession() && data.short_code) {
      addGuestLink({
        short_code: data.short_code,
        short_url: data.short_url || "",
        original_url: data.original_url || "",
        created_at: data.created_at || new Date().toISOString(),
        total_clicks: data.total_clicks || 0,
        ai_summary: data.ai_summary || null,
        ai_tags: Array.isArray(data.ai_tags) ? data.ai_tags : [],
      });
    }
    showToast("Short URL created", "success");
  } catch (err) {
    const message = userMessageFromError(err, "Unable to create short URL.");
    setFormError(el.shortenError, message);
    el.shortUrlActions.classList.add("hidden");
    clearResult();
    showToast("Create failed", "error");
  } finally {
    setButtonLoading(submitBtn, false);
  }
});

el.copyShortUrlBtn.addEventListener("click", async () => {
  if (!lastShortUrl) return;
  try {
    await navigator.clipboard.writeText(lastShortUrl);
    showToast("Short URL copied", "success");
  } catch {
    showToast("Copy failed", "error");
  }
});
