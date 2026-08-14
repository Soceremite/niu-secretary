(function () {
  "use strict";

  const API_BASE = "/niu-secretary/api";
  const MODULE_LABELS = {
    news: "新闻社",
    fitness: "塑形馆",
    schedule: "时务局",
    leisure: "闲趣集",
    airesearch: "研知库",
    platform: "平台",
    profile: "画像",
  };

  document.querySelectorAll("[data-platform-widget]").forEach((root) => {
    const moduleName = String(root.dataset.platformModule || "").trim();
    if (!moduleName) return;
    root.classList.add("niu-platform-widget");
    root.innerHTML = shellHtml(moduleName);
    const refresh = root.querySelector("[data-npw-refresh]");
    refresh?.addEventListener("click", () => loadWidget(root, moduleName));
    loadWidget(root, moduleName);
  });

  function shellHtml(moduleName) {
    const label = MODULE_LABELS[moduleName] || moduleName;
    return `
      <div class="npw-inner">
        <div class="npw-head">
          <h2 class="npw-title">${escapeHtml(label)}运行状态</h2>
          <button class="npw-refresh" type="button" data-npw-refresh>刷新</button>
        </div>
        <div class="npw-metrics" data-npw-metrics>
          <div class="npw-empty">正在读取运行状态...</div>
        </div>
        <div class="npw-grid">
          <div class="npw-column">
            <h3>待审核</h3>
            <div class="npw-stack" data-npw-reviews><div class="npw-empty">正在读取待审核项...</div></div>
          </div>
          <div class="npw-column">
            <h3>最近轨迹</h3>
            <div class="npw-stack" data-npw-timeline><div class="npw-empty">正在读取最近轨迹...</div></div>
          </div>
        </div>
      </div>
    `;
  }

  async function loadWidget(root, moduleName) {
    const refresh = root.querySelector("[data-npw-refresh]");
    if (refresh) refresh.disabled = true;
    try {
      const params = new URLSearchParams({ module: moduleName, limit: "8" });
      const data = await getJson(`${API_BASE}/platform/ops?${params.toString()}`);
      renderMetrics(root, data.summary || {});
      renderReviews(root, data.pendingReviews || []);
      renderTimeline(root, data);
    } catch (error) {
      renderError(root, error);
    } finally {
      if (refresh) refresh.disabled = false;
    }
  }

  async function getJson(url) {
    const response = await fetch(url);
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
      throw new Error(data.message || `请求失败：${response.status}`);
    }
    return data;
  }

  function renderMetrics(root, summary) {
    const el = root.querySelector("[data-npw-metrics]");
    if (!el) return;
    const statusCounts = summary.runStatusCounts || {};
    const failed = Number(statusCounts.failed || 0) + Number(statusCounts.blocked || 0);
    el.innerHTML = [
      ["待审核", summary.pendingReviewCount || 0],
      ["运行", summary.recentRunCount || 0],
      ["事件", summary.recentEventCount || 0],
      ["异常", failed],
    ].map(([label, value]) => `
      <div class="npw-metric"><b>${Number(value || 0)}</b><span>${escapeHtml(label)}</span></div>
    `).join("");
  }

  function renderReviews(root, items) {
    const el = root.querySelector("[data-npw-reviews]");
    if (!el) return;
    if (!items.length) {
      el.innerHTML = '<div class="npw-empty">暂无待审核项。</div>';
      return;
    }
    el.innerHTML = items.slice(0, 4).map((item) => rowHtml(
      item.title || item.eventType || "待审核事件",
      `${item.eventType || "event"} · ${formatTime(item.occurredAt)}`,
      "review",
    )).join("");
  }

  function renderTimeline(root, payload) {
    const el = root.querySelector("[data-npw-timeline]");
    if (!el) return;
    const rows = [
      ...(payload.runs || []).slice(0, 3).map((run) => ({
        title: run.runType || "module run",
        meta: `${run.status || "unknown"} · ${run.source || "source"} · ${formatTime(run.finishedAt || run.startedAt)}`,
        kind: "run",
      })),
      ...(payload.events || []).slice(0, 2).map((event) => ({
        title: event.title || event.eventType || "module event",
        meta: `${event.eventType || "event"} · ${formatTime(event.occurredAt)}`,
        kind: "event",
      })),
      ...(payload.modelCalls || []).slice(0, 1).map((call) => ({
        title: call.purpose || "model call",
        meta: `${call.status || "unknown"} · ${call.model || "model"} · ${Number(call.latencyMs || 0)}ms`,
        kind: "model",
      })),
    ];
    if (!rows.length) {
      el.innerHTML = '<div class="npw-empty">暂无运行轨迹。</div>';
      return;
    }
    el.innerHTML = rows.map((row) => rowHtml(row.title, row.meta, row.kind)).join("");
  }

  function rowHtml(title, meta, kind) {
    return `
      <article class="npw-row">
        <div class="npw-row-top">
          <b>${escapeHtml(title)}</b>
          <span class="npw-kind">${escapeHtml(kind)}</span>
        </div>
        <span>${escapeHtml(meta)}</span>
      </article>
    `;
  }

  function renderError(root, error) {
    const html = `<div class="npw-empty">${escapeHtml(error.message || "平台状态暂不可用。")}</div>`;
    ["[data-npw-metrics]", "[data-npw-reviews]", "[data-npw-timeline]"].forEach((selector) => {
      const el = root.querySelector(selector);
      if (el) el.innerHTML = html;
    });
  }

  function formatTime(value) {
    if (!value) return "未记录时间";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();
