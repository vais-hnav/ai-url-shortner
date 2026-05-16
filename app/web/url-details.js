if (!requireAuth()) {
  // Redirect already triggered by requireAuth.
} else {
  initShell();

  const el = {
    logoutBtn: document.getElementById("logoutBtn"),
    lookupForm: document.getElementById("lookupForm"),
    shortCodeInput: document.getElementById("shortCodeInput"),
    detailsError: document.getElementById("detailsError"),
    detailsMeta: document.getElementById("detailsMeta"),
    detailShortCode: document.getElementById("detailShortCode"),
    detailTotalClicks: document.getElementById("detailTotalClicks"),
    detailShortUrl: document.getElementById("detailShortUrl"),
    detailOriginalUrl: document.getElementById("detailOriginalUrl"),
    detailCreatedAt: document.getElementById("detailCreatedAt"),
    detailWindowClicks: document.getElementById("detailWindowClicks"),
    detailTopReferrer: document.getElementById("detailTopReferrer"),
    detailTopDevice: document.getElementById("detailTopDevice"),
    detailRecentEvents: document.getElementById("detailRecentEvents"),
    detailAiSummary: document.getElementById("detailAiSummary"),
    detailAiTags: document.getElementById("detailAiTags"),
    detailAiUpdatedAt: document.getElementById("detailAiUpdatedAt"),
    detailTopReferrersChart: document.getElementById("detailTopReferrersChart"),
    detailTrafficSplitChart: document.getElementById("detailTrafficSplitChart"),
    detailDeviceMixSummary: document.getElementById("detailDeviceMixSummary"),
    detailDeviceBreakdownChart: document.getElementById("detailDeviceBreakdownChart"),
    detailTrendLineChart: document.getElementById("detailTrendLineChart"),
    detailTrendBars: document.getElementById("detailTrendBars"),
    detailRecentClicksList: document.getElementById("detailRecentClicksList"),
  };

  function renderTags(tags) {
    const list = Array.isArray(tags) ? tags.filter(Boolean) : [];
    el.detailAiTags.innerHTML = "";
    if (!list.length) {
      el.detailAiTags.textContent = "No tags yet.";
      return;
    }
    const frag = document.createDocumentFragment();
    for (const tag of list) {
      const chip = document.createElement("span");
      chip.className = "tag";
      chip.textContent = String(tag);
      frag.appendChild(chip);
    }
    el.detailAiTags.appendChild(frag);
  }

  function renderBars(trend = []) {
    if (!trend.length) {
      el.detailTrendLineChart.innerHTML = `<div class="item">No daily traffic line yet.</div>`;
      el.detailTrendBars.innerHTML = `<div class="meta">No clicks in this period.</div>`;
      return;
    }
    renderTrendLineChart(trend);
    const max = Math.max(...trend.map((p) => p.clicks), 1);
    el.detailTrendBars.innerHTML = trend
      .map((point) => {
        const h = Math.max(3, Math.round((point.clicks / max) * 70));
        const label = escapeHTML(String(point.date).slice(5));
        return `<div><div class="bar"><div class="bar-fill" style="height:${h}px"></div></div><div class="bar-label">${label} · ${formatNumber(point.clicks)}</div></div>`;
      })
      .join("");
  }

  function renderTrendLineChart(trend = []) {
    if (!trend.length) {
      el.detailTrendLineChart.innerHTML = `<div class="item">No daily traffic line yet.</div>`;
      return;
    }

    const values = trend.map((point) => Number(point.clicks || 0));
    const max = Math.max(...values, 1);
    const min = Math.min(...values, 0);
    const width = 760;
    const height = 220;
    const paddingX = 22;
    const paddingTop = 18;
    const paddingBottom = 34;
    const graphHeight = height - paddingTop - paddingBottom;
    const graphWidth = width - paddingX * 2;
    const range = Math.max(max - min, 1);
    const steps = Math.max(trend.length - 1, 1);
    const points = trend.map((point, index) => {
      const value = Number(point.clicks || 0);
      const x = paddingX + (graphWidth * index) / steps;
      const y = paddingTop + ((max - value) / range) * graphHeight;
      return { ...point, value, x, y, shortLabel: String(point.date).slice(5) };
    });
    const linePath = points
      .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
      .join(" ");
    const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(2)} ${(height - paddingBottom).toFixed(2)} L ${points[0].x.toFixed(2)} ${(height - paddingBottom).toFixed(2)} Z`;

    el.detailTrendLineChart.innerHTML = `
      <svg class="trend-line-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-label="Per-link daily traffic line chart">
        <defs>
          <linearGradient id="detailTrendArea" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="rgba(255,77,46,0.38)"></stop>
            <stop offset="100%" stop-color="rgba(255,77,46,0.02)"></stop>
          </linearGradient>
        </defs>
        <path d="${areaPath}" fill="url(#detailTrendArea)"></path>
        <path d="${linePath}" class="trend-line-path"></path>
        ${points.map((point) => `<g><circle cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="4" class="trend-point"></circle><title>${escapeHTML(point.shortLabel)}: ${formatNumber(point.value)} clicks</title></g>`).join("")}
        ${points
          .filter((_, index) => index === 0 || index === points.length - 1 || index % Math.ceil(points.length / 6) === 0)
          .map((point) => `<text x="${point.x.toFixed(2)}" y="${(height - 10).toFixed(2)}" text-anchor="middle" class="trend-axis-label">${escapeHTML(point.shortLabel)}</text>`)
          .join("")}
      </svg>
    `;
  }

  function renderComparisonChart(container, items, valueKey, options = {}) {
    if (!container) return;
    const rows = Array.isArray(items) ? items : [];
    if (!rows.length) {
      container.innerHTML = `<div class="item">No data in this period.</div>`;
      return;
    }
    const max = Math.max(...rows.map((item) => Number(item[valueKey] || 0)), 1);
    const formatter = options.formatter || ((value) => formatNumber(value));
    container.innerHTML = rows
      .map((item) => {
        const value = Number(item[valueKey] || 0);
        const width = Math.max(6, Math.round((value / max) * 100));
        const label = item.label || "Unknown";
        return `<div class="chart-row">
          <div class="chart-row-head">
            <div class="chart-row-title">${escapeHTML(label)}</div>
            <div class="chart-row-value">${formatter(value)}</div>
          </div>
          <div class="chart-track"><div class="chart-fill ${options.accentClass || "warm"}" style="width:${width}%"></div></div>
        </div>`;
      })
      .join("");
  }

  function renderDeviceMix(items = []) {
    const rows = Array.isArray(items) ? items : [];
    if (!rows.length) {
      el.detailDeviceMixSummary.innerHTML = `<div class="item">No device data in this period.</div>`;
      return;
    }
    const total = rows.reduce((sum, item) => sum + Number(item.clicks || 0), 0);
    const segments = rows
      .map((item) => {
        const share = total ? (Number(item.clicks || 0) / total) * 100 : 0;
        return `<div class="mix-segment" style="width:${share}%"><span>${escapeHTML(item.label)}</span></div>`;
      })
      .join("");
    const legend = rows
      .map((item) => {
        const share = total ? (Number(item.clicks || 0) / total) * 100 : 0;
        return `<div class="mix-legend-item"><span class="mix-dot"></span><span>${escapeHTML(item.label)}</span><strong>${formatPercent(share)}</strong></div>`;
      })
      .join("");
    el.detailDeviceMixSummary.innerHTML = `<div class="mix-bar">${segments}</div><div class="mix-legend">${legend}</div>`;
  }

  function renderTrafficSplit(totalClicks, referrers = []) {
    const total = Math.max(0, Number(totalClicks || 0));
    if (!total) {
      el.detailTrafficSplitChart.innerHTML = `<div class="item">No traffic distribution yet.</div>`;
      return;
    }
    const rows = Array.isArray(referrers) ? referrers : [];
    const directClicks = rows.reduce(
      (sum, row) => sum + (String(row.label || "").toLowerCase() === "direct" ? Number(row.clicks || 0) : 0),
      0
    );
    const referredClicks = Math.max(0, total - directClicks);
    const directShare = total ? (directClicks / total) * 100 : 0;
    const referredShare = total ? (referredClicks / total) * 100 : 0;
    el.detailTrafficSplitChart.innerHTML = `
      <div class="focus-metric">
        <span>Direct traffic</span>
        <strong>${formatPercent(directShare)}</strong>
        <div class="chart-track"><div class="chart-fill lime" style="width:${directShare}%"></div></div>
      </div>
      <div class="focus-metric">
        <span>Referred traffic</span>
        <strong>${formatPercent(referredShare)}</strong>
        <div class="chart-track"><div class="chart-fill warm" style="width:${referredShare}%"></div></div>
      </div>
    `;
  }

  function renderRecentClicks(items = []) {
    const rows = Array.isArray(items) ? items : [];
    if (!rows.length) {
      el.detailRecentClicksList.innerHTML = `<div class="item">No recent click activity yet.</div>`;
      return;
    }
    el.detailRecentClicksList.innerHTML = rows
      .map((item) => {
        const when = item.created_at ? new Date(item.created_at).toLocaleString() : "-";
        const referrer = item.referrer || "direct";
        const device = item.user_agent ? (String(item.user_agent).match(/iphone|android|mobile/i) ? "mobile" : String(item.user_agent).match(/ipad|tablet/i) ? "tablet" : "desktop") : "unknown";
        return `<div class="item">
          <div class="url-head">
            <strong>${escapeHTML(when)}</strong>
            <span class="pill">${escapeHTML(device)}</span>
          </div>
          <div class="meta">Referrer</div>
          <div>${escapeHTML(referrer)}</div>
        </div>`;
      })
      .join("");
  }

  async function loadDetails(shortCode) {
    setFormError(el.detailsError, "");
    el.detailsMeta.textContent = "Loading URL details...";
    try {
      const tzOffsetMinutes = -new Date().getTimezoneOffset();
      const [details, analytics, daily] = await Promise.all([
        api(`/urls/${encodeURIComponent(shortCode)}/details`, { headers: authHeaders() }),
        api(`/urls/${encodeURIComponent(shortCode)}/analytics?recent_limit=20&top_referrers_limit=8`, {
          headers: authHeaders(),
        }),
        api(`/urls/${encodeURIComponent(shortCode)}/analytics/daily?days=7&tz_offset_minutes=${tzOffsetMinutes}`, {
          headers: authHeaders(),
        }),
      ]);

      el.detailShortCode.textContent = details.short_code || "-";
      el.detailTotalClicks.textContent = `${formatNumber(details.total_clicks || 0)} clicks`;
      el.detailShortUrl.textContent = details.short_url || "-";
      if (details.short_url) {
        el.detailShortUrl.setAttribute("href", details.short_url);
      } else {
        el.detailShortUrl.removeAttribute("href");
      }
      el.detailOriginalUrl.textContent = details.original_url || "-";
      el.detailCreatedAt.textContent = details.created_at ? new Date(details.created_at).toLocaleString() : "-";
      const dailyClicks = (daily.daily_clicks || []).reduce((sum, row) => sum + Number(row.clicks || 0), 0);
      const topReferrer = Array.isArray(analytics.top_referrers) && analytics.top_referrers.length ? analytics.top_referrers[0].label : "-";
      const topDevice = Array.isArray(analytics.device_breakdown) && analytics.device_breakdown.length ? analytics.device_breakdown[0].label : "-";
      el.detailWindowClicks.textContent = formatNumber(dailyClicks);
      el.detailTopReferrer.textContent = topReferrer;
      el.detailTopDevice.textContent = topDevice;
      el.detailRecentEvents.textContent = formatNumber((analytics.recent_clicks || []).length);
      el.detailAiSummary.textContent = details.ai_summary || "No AI summary available yet.";
      renderTags(details.ai_tags || []);
      el.detailAiUpdatedAt.textContent = details.ai_last_updated_at
        ? new Date(details.ai_last_updated_at).toLocaleString()
        : "-";
      renderBars(daily.daily_clicks || []);
      renderComparisonChart(el.detailTopReferrersChart, analytics.top_referrers || [], "clicks", {
        formatter: (value) => `${formatNumber(value)} clicks`,
        accentClass: "warm",
      });
      renderDeviceMix(analytics.device_breakdown || []);
      renderComparisonChart(el.detailDeviceBreakdownChart, analytics.device_breakdown || [], "clicks", {
        formatter: (value) => `${formatNumber(value)} clicks`,
        accentClass: "amber",
      });
      renderTrafficSplit(details.total_clicks || 0, analytics.top_referrers || []);
      renderRecentClicks(analytics.recent_clicks || []);
      el.detailsMeta.textContent = "URL details loaded.";
    } catch (err) {
      const message = userMessageFromError(err, "Unable to load URL details.");
      setFormError(el.detailsError, message);
      el.detailsMeta.textContent = "Failed to load URL details.";
      el.detailWindowClicks.textContent = "-";
      el.detailTopReferrer.textContent = "-";
      el.detailTopDevice.textContent = "-";
      el.detailRecentEvents.textContent = "-";
      renderBars([]);
      renderComparisonChart(el.detailTopReferrersChart, [], "clicks");
      renderDeviceMix([]);
      renderComparisonChart(el.detailDeviceBreakdownChart, [], "clicks");
      renderTrafficSplit(0, []);
      renderRecentClicks([]);
    }
  }

  el.lookupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const code = String(el.shortCodeInput.value || "").trim();
    if (!code) return;
    await loadDetails(code);
  });

  el.logoutBtn.addEventListener("click", () => {
    showToast("Signed out", "info");
    logoutAndRedirect();
  });

  (async () => {
    const params = new URLSearchParams(window.location.search);
    const codeFromQuery = String(params.get("code") || "").trim();
    if (codeFromQuery) {
      el.shortCodeInput.value = codeFromQuery;
      await loadDetails(codeFromQuery);
    }
  })();
}
