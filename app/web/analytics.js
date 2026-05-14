if (!requireAuth()) {
  // Redirect already triggered by requireAuth.
} else {
  initShell();

const state = {
  overviewDays: 7,
};

function usingGuestMode() {
  return isGuestSession() && !isAuthenticated();
}

const el = {
  logoutBtn: document.getElementById("logoutBtn"),
  overviewForm: document.getElementById("overviewForm"),
  overviewError: document.getElementById("overviewError"),
  overviewMeta: document.getElementById("overviewMeta"),
  kpiLinks: document.getElementById("kpiLinks"),
  kpiClicks: document.getElementById("kpiClicks"),
  kpiPrevClicks: document.getElementById("kpiPrevClicks"),
  kpiChange: document.getElementById("kpiChange"),
  kpiActiveLinks: document.getElementById("kpiActiveLinks"),
  kpiAvgClicks: document.getElementById("kpiAvgClicks"),
  kpiDirectShare: document.getElementById("kpiDirectShare"),
  kpiTopShare: document.getElementById("kpiTopShare"),
  kpiBestDay: document.getElementById("kpiBestDay"),
  kpiBestDayClicks: document.getElementById("kpiBestDayClicks"),
  trendSummary: document.getElementById("trendSummary"),
  trendLineChart: document.getElementById("trendLineChart"),
  trendBars: document.getElementById("trendBars"),
  hourlyActivityChart: document.getElementById("hourlyActivityChart"),
  weekdayHeatmap: document.getElementById("weekdayHeatmap"),
  topLinksChart: document.getElementById("topLinksChart"),
  topReferrersChart: document.getElementById("topReferrersChart"),
  trafficSplitChart: document.getElementById("trafficSplitChart"),
  deviceMixSummary: document.getElementById("deviceMixSummary"),
  deviceBreakdownChart: document.getElementById("deviceBreakdownChart"),
  trafficConcentration: document.getElementById("trafficConcentration"),
};

function deviceLabelFromUserAgent(userAgent = "") {
  const ua = String(userAgent || "").toLowerCase();
  if (!ua) return "unknown";
  if (ua.includes("ipad") || ua.includes("tablet")) return "tablet";
  if (ua.includes("mobi") || ua.includes("android") || ua.includes("iphone")) return "mobile";
  return "desktop";
}

function renderBars(trend = []) {
  if (!trend.length) {
    if (el.trendLineChart) {
      el.trendLineChart.innerHTML = `<div class="item">No daily traffic line yet.</div>`;
    }
    el.trendBars.innerHTML = `<div class="item">No daily traffic yet.</div>`;
    if (el.trendSummary) {
      el.trendSummary.innerHTML = "";
    }
    return;
  }

  const total = trend.reduce((sum, point) => sum + Number(point.clicks || 0), 0);
  const average = total / trend.length;
  const peakPoint = trend.reduce(
    (best, current) => (Number(current.clicks || 0) > Number(best.clicks || 0) ? current : best),
    trend[0]
  );

  if (el.trendSummary) {
    el.trendSummary.innerHTML = `
      <div class="mini-kpi">
        <span>Average / day</span>
        <strong>${average.toFixed(1)}</strong>
      </div>
      <div class="mini-kpi">
        <span>Peak day</span>
        <strong>${String(peakPoint.date).slice(5)}</strong>
      </div>
      <div class="mini-kpi">
        <span>Peak clicks</span>
        <strong>${formatNumber(peakPoint.clicks)}</strong>
      </div>
    `;
  }

  renderTrendLineChart(trend, peakPoint, average);

  const max = Math.max(...trend.map((p) => p.clicks), 1);
  el.trendBars.innerHTML = trend
    .map((point) => {
      const clicks = Number(point.clicks || 0);
      const h = Math.max(10, Math.round((clicks / max) * 110));
      const label = String(point.date).slice(5);
      return `<div class="trend-day">
        <div class="trend-value">${formatNumber(clicks)}</div>
        <div class="bar"><div class="bar-fill" style="height:${h}px"></div></div>
        <div class="bar-label">${label}</div>
      </div>`;
    })
    .join("");
}

function renderTrendLineChart(trend = [], peakPoint = null, average = 0) {
  if (!el.trendLineChart) return;
  if (!trend.length) {
    el.trendLineChart.innerHTML = `<div class="item">No daily traffic line yet.</div>`;
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
    return {
      ...point,
      value,
      x,
      y,
      shortLabel: String(point.date).slice(5),
    };
  });

  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`)
    .join(" ");
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(2)} ${(height - paddingBottom).toFixed(2)} L ${points[0].x.toFixed(2)} ${(height - paddingBottom).toFixed(2)} Z`;

  const yTicks = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3;
    const value = Math.round(max - (max - min) * ratio);
    const y = paddingTop + graphHeight * ratio;
    return { value, y };
  });

  const lastPoint = points[points.length - 1];
  const changeFromStart = points.length > 1 ? lastPoint.value - points[0].value : 0;
  const directionLabel =
    changeFromStart > 0 ? `Up ${formatNumber(changeFromStart)}` : changeFromStart < 0 ? `Down ${formatNumber(Math.abs(changeFromStart))}` : "Flat";

  el.trendLineChart.innerHTML = `
    <div class="trend-line-header">
      <div class="trend-line-metric">
        <span>Latest day</span>
        <strong>${formatNumber(lastPoint.value)} clicks</strong>
      </div>
      <div class="trend-line-metric">
        <span>Direction</span>
        <strong>${directionLabel}</strong>
      </div>
      <div class="trend-line-metric">
        <span>Average</span>
        <strong>${average.toFixed(1)} clicks</strong>
      </div>
    </div>
    <svg class="trend-line-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-label="Daily traffic line chart">
      <defs>
        <linearGradient id="trendLineArea" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="rgba(255,77,46,0.38)"></stop>
          <stop offset="100%" stop-color="rgba(255,77,46,0.02)"></stop>
        </linearGradient>
      </defs>
      ${yTicks
        .map(
          (tick) => `<g>
            <line x1="${paddingX}" y1="${tick.y.toFixed(2)}" x2="${width - paddingX}" y2="${tick.y.toFixed(2)}" class="trend-grid-line"></line>
            <text x="${paddingX}" y="${(tick.y - 6).toFixed(2)}" class="trend-grid-label">${formatNumber(tick.value)}</text>
          </g>`
        )
        .join("")}
      <path d="${areaPath}" class="trend-area-path"></path>
      <path d="${linePath}" class="trend-line-path"></path>
      ${points
        .map((point) => {
          const isPeak = peakPoint && String(peakPoint.date) === String(point.date) && Number(peakPoint.clicks || 0) === point.value;
          return `<g>
            <circle cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="${isPeak ? 5.5 : 4}" class="${isPeak ? "trend-point peak" : "trend-point"}"></circle>
            <title>${point.shortLabel}: ${formatNumber(point.value)} clicks</title>
          </g>`;
        })
        .join("")}
      ${points
        .filter((_, index) => index === 0 || index === points.length - 1 || index % Math.ceil(points.length / 6) === 0)
        .map(
          (point) => `<text x="${point.x.toFixed(2)}" y="${(height - 10).toFixed(2)}" text-anchor="middle" class="trend-axis-label">${point.shortLabel}</text>`
        )
        .join("")}
    </svg>
  `;
}

function renderHourlyActivity(items = []) {
  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) {
    el.hourlyActivityChart.innerHTML = `<div class="item">No hourly activity yet.</div>`;
    return;
  }
  const max = Math.max(...rows.map((item) => Number(item.clicks || 0)), 1);
  el.hourlyActivityChart.innerHTML = rows
    .map((item) => {
      const clicks = Number(item.clicks || 0);
      const height = Math.max(8, Math.round((clicks / max) * 96));
      return `<div class="hour-block">
        <div class="hour-bar-wrap">
          <div class="hour-bar" style="height:${height}px"></div>
        </div>
        <div class="hour-value">${formatNumber(clicks)}</div>
        <div class="hour-label">${item.label.slice(0, 2)}</div>
      </div>`;
    })
    .join("");
}

function renderWeekdayHeatmap(items = []) {
  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) {
    el.weekdayHeatmap.innerHTML = `<div class="item">No weekday pattern yet.</div>`;
    return;
  }
  const max = Math.max(...rows.map((item) => Number(item.clicks || 0)), 1);
  el.weekdayHeatmap.innerHTML = rows
    .map((item) => {
      const clicks = Number(item.clicks || 0);
      const intensity = Math.max(0.12, clicks / max);
      return `<div class="weekday-cell" style="--heat:${intensity}">
        <span>${item.label}</span>
        <strong>${formatNumber(clicks)}</strong>
      </div>`;
    })
    .join("");
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
  const subtitle = options.subtitle || (() => "");
  const linkFor = options.linkFor || (() => "");
  const accentClass = options.accentClass || "warm";

  container.innerHTML = rows
    .map((item) => {
      const value = Number(item[valueKey] || 0);
      const width = Math.max(6, Math.round((value / max) * 100));
      const label = item.label || item.short_code || "Unknown";
      const href = linkFor(item);
      const secondary = subtitle(item);
      return `<div class="chart-row">
        <div class="chart-row-head">
          <div class="chart-row-title">${href ? `<a href="${href}" class="chart-link">${label}</a>` : label}</div>
          <div class="chart-row-value">${formatter(value)}</div>
        </div>
        ${secondary ? `<div class="chart-row-subtitle">${secondary}</div>` : ""}
        <div class="chart-track"><div class="chart-fill ${accentClass}" style="width:${width}%"></div></div>
      </div>`;
    })
    .join("");
}

function renderDeviceMix(items = []) {
  const rows = Array.isArray(items) ? items : [];
  if (!rows.length) {
    el.deviceMixSummary.innerHTML = `<div class="item">No device data in this period.</div>`;
    return;
  }
  const total = rows.reduce((sum, item) => sum + Number(item.clicks || 0), 0);
  const segments = rows
    .map((item) => {
      const share = total ? (Number(item.clicks || 0) / total) * 100 : 0;
      return `<div class="mix-segment" style="width:${share}%">
        <span>${item.label}</span>
      </div>`;
    })
    .join("");
  const legend = rows
    .map((item) => {
      const share = total ? (Number(item.clicks || 0) / total) * 100 : 0;
      return `<div class="mix-legend-item">
        <span class="mix-dot"></span>
        <span>${item.label}</span>
        <strong>${formatPercent(share)}</strong>
      </div>`;
    })
    .join("");
  el.deviceMixSummary.innerHTML = `<div class="mix-bar">${segments}</div><div class="mix-legend">${legend}</div>`;
}

function renderTrafficConcentration(topShare, directShare) {
  const safeTop = Math.max(0, Math.min(100, Number(topShare || 0)));
  const safeDirect = Math.max(0, Math.min(100, Number(directShare || 0)));
  el.trafficConcentration.innerHTML = `
    <div class="focus-metric">
      <span>Top link concentration</span>
      <strong>${formatPercent(safeTop)}</strong>
      <div class="chart-track"><div class="chart-fill warm" style="width:${safeTop}%"></div></div>
    </div>
    <div class="focus-metric">
      <span>Direct traffic share</span>
      <strong>${formatPercent(safeDirect)}</strong>
      <div class="chart-track"><div class="chart-fill lime" style="width:${safeDirect}%"></div></div>
    </div>
  `;
}

function renderTrafficSplit(totalClicks, referrers = []) {
  const total = Math.max(0, Number(totalClicks || 0));
  if (!el.trafficSplitChart) return;
  if (!total) {
    el.trafficSplitChart.innerHTML = `<div class="item">No traffic distribution yet.</div>`;
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

  const topSources = rows
    .map((row) => ({
      label: row.label || "Unknown",
      clicks: Number(row.clicks || 0),
      share: total ? (Number(row.clicks || 0) / total) * 100 : 0,
    }))
    .sort((a, b) => b.clicks - a.clicks)
    .slice(0, 4);

  const palette = ["var(--accent)", "var(--accent-2)", "var(--accent-3)", "#f8f2e7"];
  const slices = topSources.length
    ? topSources
        .map((source, index) => {
          const start = topSources
            .slice(0, index)
            .reduce((sum, item) => sum + item.share, 0);
          const end = start + source.share;
          return `${palette[index]} ${start}% ${end}%`;
        })
        .join(", ")
    : "rgba(255,250,240,0.1) 0% 100%";

  const sourceRows = topSources
    .map(
      (source, index) => `<div class="traffic-legend-row">
        <span class="traffic-legend-dot" style="--dot:${palette[index]}"></span>
        <span class="traffic-legend-label">${source.label}</span>
        <strong>${formatPercent(source.share)}</strong>
      </div>`
    )
    .join("");

  el.trafficSplitChart.innerHTML = `
    <div class="traffic-split-hero">
      <div class="traffic-ring" style="--traffic-conic:${slices}">
        <div class="traffic-ring-center">
          <span>Total traffic</span>
          <strong>${formatNumber(total)}</strong>
        </div>
      </div>
      <div class="traffic-summary">
        <div class="traffic-summary-card">
          <span>Direct</span>
          <strong>${formatNumber(directClicks)}</strong>
          <div class="chart-track"><div class="chart-fill lime" style="width:${directShare}%"></div></div>
          <small>${formatPercent(directShare)}</small>
        </div>
        <div class="traffic-summary-card">
          <span>Referred</span>
          <strong>${formatNumber(referredClicks)}</strong>
          <div class="chart-track"><div class="chart-fill warm" style="width:${referredShare}%"></div></div>
          <small>${formatPercent(referredShare)}</small>
        </div>
      </div>
    </div>
    <div class="traffic-legend">
      ${sourceRows || `<div class="item">No referral source breakdown yet.</div>`}
    </div>
  `;
}

async function refreshOverview() {
  setFormError(el.overviewError, "");
  el.overviewMeta.textContent = "Loading analytics...";
  const tzOffsetMinutes = -new Date().getTimezoneOffset();
  if (usingGuestMode()) {
    const links = getGuestLinks();
    if (!links.length) {
      el.overviewMeta.textContent = "No guest links yet. Create a short URL first.";
      el.kpiLinks.textContent = "0";
      el.kpiClicks.textContent = "0";
      el.kpiPrevClicks.textContent = "0";
      el.kpiChange.textContent = "0%";
      el.kpiActiveLinks.textContent = "0";
      el.kpiAvgClicks.textContent = "0";
      el.kpiDirectShare.textContent = "0%";
      el.kpiTopShare.textContent = "0%";
      el.kpiBestDay.textContent = "-";
      el.kpiBestDayClicks.textContent = "0";
      renderBars([]);
      renderHourlyActivity([]);
      renderWeekdayHeatmap([]);
      renderComparisonChart(el.topLinksChart, [], "clicks");
      renderComparisonChart(el.topReferrersChart, [], "clicks");
      renderTrafficSplit(0, []);
      renderDeviceMix([]);
      renderComparisonChart(el.deviceBreakdownChart, [], "clicks");
      renderTrafficConcentration(0, 0);
      return;
    }

    const refMap = new Map();
    const deviceMap = new Map();
    const trendMap = new Map();
    const hourlyMap = new Map(Array.from({ length: 24 }, (_, hour) => [`${hour.toString().padStart(2, "0")}:00`, 0]));
    const weekdayMap = new Map([
      ["Mon", 0],
      ["Tue", 0],
      ["Wed", 0],
      ["Thu", 0],
      ["Fri", 0],
      ["Sat", 0],
      ["Sun", 0],
    ]);
    const topLinks = [];
    let totalClicks = 0;
    const now = new Date();
    const windowStart = new Date(now.getTime() - state.overviewDays * 24 * 60 * 60 * 1000);

    for (const link of links) {
      let linkClicks = 0;
      try {
        const analytics = await api(
          `/urls/${encodeURIComponent(link.short_code)}/analytics?top_referrers_limit=20&recent_limit=100`,
          {
            headers: authHeaders(),
          }
        );
        for (const row of analytics.recent_clicks || []) {
          const clickAt = new Date(row.created_at);
          if (clickAt < windowStart) continue;
          const referrerLabel = row.referrer || "direct";
          const deviceLabel = deviceLabelFromUserAgent(row.user_agent);
          const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
          const weekday = weekdayLabels[clickAt.getDay()];
          const hourLabel = `${clickAt.getHours().toString().padStart(2, "0")}:00`;
          refMap.set(referrerLabel, (refMap.get(referrerLabel) || 0) + 1);
          deviceMap.set(deviceLabel, (deviceMap.get(deviceLabel) || 0) + 1);
          weekdayMap.set(weekday, (weekdayMap.get(weekday) || 0) + 1);
          hourlyMap.set(hourLabel, (hourlyMap.get(hourLabel) || 0) + 1);
        }
      } catch {}

      try {
        const daily = await api(
          `/urls/${encodeURIComponent(link.short_code)}/analytics/daily?days=${state.overviewDays}&tz_offset_minutes=${tzOffsetMinutes}`,
          { headers: authHeaders() }
        );
        for (const row of daily.daily_clicks || []) {
          trendMap.set(row.date, (trendMap.get(row.date) || 0) + Number(row.clicks || 0));
          linkClicks += Number(row.clicks || 0);
        }
      } catch {}

      totalClicks += linkClicks;
      topLinks.push({
        short_code: link.short_code,
        short_url: link.short_url,
        clicks: linkClicks,
      });
    }

    const sortedTrend = Array.from(trendMap.entries())
      .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
      .map(([date, clicks]) => ({ date, clicks }));
    const hourlyDistribution = Array.from(hourlyMap.entries()).map(([label, clicks]) => ({ label, clicks }));
    const weekdayOrder = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const weekdayDistribution = weekdayOrder.map((label) => ({ label, clicks: weekdayMap.get(label) || 0 }));

    const topReferrers = Array.from(refMap.entries())
      .map(([label, clicks]) => ({ label, clicks }))
      .sort((a, b) => b.clicks - a.clicks)
      .slice(0, 5);

    const deviceBreakdown = Array.from(deviceMap.entries())
      .map(([label, clicks]) => ({ label, clicks }))
      .sort((a, b) => b.clicks - a.clicks)
      .slice(0, 5);

    const topLinkRows = topLinks
      .sort((a, b) => b.clicks - a.clicks)
      .slice(0, 5);
    const activeLinks = topLinks.filter((item) => item.clicks > 0).length;
    const avgClicks = activeLinks ? totalClicks / activeLinks : 0;
    const topLinkShare = totalClicks && topLinkRows.length ? (topLinkRows[0].clicks / totalClicks) * 100 : 0;
    const directClicks = Array.from(refMap.entries()).reduce(
      (acc, [label, clicks]) => acc + (label === "direct" ? Number(clicks || 0) : 0),
      0
    );
    const directShare = totalClicks ? (directClicks / totalClicks) * 100 : 0;
    const bestTrendPoint = sortedTrend.length
      ? sortedTrend.reduce((best, current) => (current.clicks > best.clicks ? current : best), sortedTrend[0])
      : null;

    el.overviewMeta.textContent = `Guest analytics for last ${state.overviewDays} days`;
    el.kpiLinks.textContent = formatNumber(links.length);
    el.kpiClicks.textContent = formatNumber(totalClicks);
    el.kpiPrevClicks.textContent = "N/A";
    el.kpiChange.textContent = "N/A";
    el.kpiActiveLinks.textContent = formatNumber(activeLinks);
    el.kpiAvgClicks.textContent = avgClicks.toFixed(1);
    el.kpiDirectShare.textContent = formatPercent(directShare);
    el.kpiTopShare.textContent = formatPercent(topLinkShare);
    el.kpiBestDay.textContent = bestTrendPoint ? String(bestTrendPoint.date) : "-";
    el.kpiBestDayClicks.textContent = bestTrendPoint ? formatNumber(bestTrendPoint.clicks) : "0";
    renderBars(sortedTrend);
    renderHourlyActivity(hourlyDistribution);
    renderWeekdayHeatmap(weekdayDistribution);
    renderComparisonChart(el.topLinksChart, topLinkRows, "clicks", {
      formatter: (value) => `${formatNumber(value)} clicks`,
      subtitle: (item) => item.short_url || "",
      linkFor: (item) => `/web/url-details.html?code=${encodeURIComponent(item.short_code)}`,
      accentClass: "warm",
    });
    renderComparisonChart(el.topReferrersChart, topReferrers, "clicks", {
      formatter: (value) => `${formatNumber(value)} clicks`,
      accentClass: "lime",
    });
    renderTrafficSplit(totalClicks, topReferrers);
    renderDeviceMix(deviceBreakdown);
    renderComparisonChart(el.deviceBreakdownChart, deviceBreakdown, "clicks", {
      formatter: (value) => `${formatNumber(value)} clicks`,
      accentClass: "amber",
    });
    renderTrafficConcentration(topLinkShare, directShare);
    return;
  }

  const params = new URLSearchParams({
    days: String(state.overviewDays),
    tz_offset_minutes: String(tzOffsetMinutes),
    compare_previous: "true",
  });
  try {
    const data = await api(`/urls/analytics/overview?${params.toString()}`, {
      headers: authHeaders(),
    });
    el.overviewMeta.textContent = `${data.start_date} to ${data.end_date}`;
    el.kpiLinks.textContent = formatNumber(data.total_links ?? 0);
    el.kpiClicks.textContent = formatNumber(data.total_clicks ?? 0);
    el.kpiPrevClicks.textContent = formatNumber(data.previous_total_clicks ?? 0);
    el.kpiChange.textContent = formatPercent(data.click_change_percent ?? 0);
    el.kpiActiveLinks.textContent = formatNumber(data.active_links ?? 0);
    el.kpiAvgClicks.textContent = Number(data.average_clicks_per_active_link ?? 0).toFixed(1);
    el.kpiDirectShare.textContent = formatPercent(data.direct_traffic_share_percent ?? 0);
    el.kpiTopShare.textContent = formatPercent(data.top_link_share_percent ?? 0);
    el.kpiBestDay.textContent = data.best_day ? String(data.best_day) : "-";
    el.kpiBestDayClicks.textContent = formatNumber(data.best_day_clicks ?? 0);
    renderBars(data.trend || []);
    renderHourlyActivity(data.hourly_distribution || []);
    renderWeekdayHeatmap(data.weekday_distribution || []);
    renderComparisonChart(el.topLinksChart, data.top_links || [], "clicks", {
      formatter: (value) => `${formatNumber(value)} clicks`,
      subtitle: (item) => item.short_url || "",
      linkFor: (item) => `/web/url-details.html?code=${encodeURIComponent(item.short_code)}`,
      accentClass: "warm",
    });
    renderComparisonChart(el.topReferrersChart, data.top_referrers || [], "clicks", {
      formatter: (value) => `${formatNumber(value)} clicks`,
      accentClass: "lime",
    });
    renderTrafficSplit(data.total_clicks || 0, data.top_referrers || []);
    renderDeviceMix(data.device_breakdown || []);
    renderComparisonChart(el.deviceBreakdownChart, data.device_breakdown || [], "clicks", {
      formatter: (value) => `${formatNumber(value)} clicks`,
      accentClass: "amber",
    });
    renderTrafficConcentration(
      Number(data.top_link_share_percent || 0),
      Number(data.direct_traffic_share_percent || 0)
    );
  } catch (err) {
    if (usingGuestMode()) {
      return refreshOverview();
    }
    setFormError(el.overviewError, userMessageFromError(err, "Unable to load analytics."));
    el.overviewMeta.textContent = "Failed to load analytics.";
    el.kpiLinks.textContent = "-";
    el.kpiClicks.textContent = "-";
    el.kpiPrevClicks.textContent = "-";
    el.kpiChange.textContent = "-";
    el.kpiActiveLinks.textContent = "-";
    el.kpiAvgClicks.textContent = "-";
    el.kpiDirectShare.textContent = "-";
    el.kpiTopShare.textContent = "-";
    el.kpiBestDay.textContent = "-";
    el.kpiBestDayClicks.textContent = "-";
    renderBars([]);
    renderHourlyActivity([]);
    renderWeekdayHeatmap([]);
    renderComparisonChart(el.topLinksChart, [], "clicks");
    renderComparisonChart(el.topReferrersChart, [], "clicks");
    renderTrafficSplit(0, []);
    renderDeviceMix([]);
    renderComparisonChart(el.deviceBreakdownChart, [], "clicks");
    renderTrafficConcentration(0, 0);
  }
}

el.logoutBtn.addEventListener("click", () => {
  showToast("Signed out", "info");
  logoutAndRedirect();
});

el.overviewForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const submitBtn = el.overviewForm.querySelector("button[type='submit']");
  const fd = new FormData(el.overviewForm);
  const days = Number(fd.get("days") || 7);
  state.overviewDays = Math.min(90, Math.max(1, days));
  setButtonLoading(submitBtn, true, "Refreshing...");
  await refreshOverview();
  setButtonLoading(submitBtn, false);
  showToast("Analytics refreshed", "success");
});

  (async () => {
    try {
      await refreshOverview();
      showToast("Analytics ready", "success");
    } catch (err) {
      setFormError(el.overviewError, userMessageFromError(err, "Unable to load analytics."));
      showToast("Analytics failed to load", "error");
    }
  })();
}
