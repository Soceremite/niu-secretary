const API_BASE = "/niu-secretary/api";

const form = document.querySelector("[data-assistant-form]");
const input = document.querySelector("[data-assistant-input]");
const messages = document.querySelector("[data-assistant-messages]");
const actions = document.querySelector("[data-assistant-actions]");
const statusLine = document.querySelector("[data-assistant-status]");
const progressEl = document.querySelector("[data-ai-progress]");
const platformModules = document.querySelector("[data-platform-modules]");
const platformToday = document.querySelector("[data-platform-today]");
const platformAudit = document.querySelector("[data-platform-audit]");
const platformDate = document.querySelector("[data-platform-date]");
const platformRefresh = document.querySelector("[data-platform-refresh]");
const platformOpsSummary = document.querySelector("[data-platform-ops-summary]");
const platformMetrics = document.querySelector("[data-platform-metrics]");
const platformWorkQueue = document.querySelector("[data-platform-work-queue]");
const platformReviews = document.querySelector("[data-platform-reviews]");
const platformTimeline = document.querySelector("[data-platform-timeline]");
const platformProfileChanges = document.querySelector("[data-platform-profile-changes]");
const platformResearch = document.querySelector("[data-platform-research]");
const platformResearchSummary = document.querySelector("[data-platform-research-summary]");
const platformResearchSearchForm = document.querySelector("[data-platform-research-search]");
const platformResearchSearchInput = document.querySelector("[data-platform-research-query]");
const platformResearchSearchResults = document.querySelector("[data-platform-research-results]");
const platformModuleFilter = document.querySelector("[data-platform-module-filter]");
const platformStatusFilter = document.querySelector("[data-platform-status-filter]");
const platformReviewFilter = document.querySelector("[data-platform-review-filter]");
const platformFilterReset = document.querySelector("[data-platform-filter-reset]");

/** 流程步骤序列 */
const FLOW_STEPS = ["理解意图", "分析板块", "生成动作", "等待确认"];

if (form && input && messages && actions && statusLine) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMessage(text, "user");
    resetProgress();
    actions.hidden = true;
    actions.innerHTML = "";

    try {
      advanceProgress(0); // 理解意图
      await sleep(400);
      advanceProgress(1); // 分析板块
      await sleep(500);
      advanceProgress(2); // 生成动作

      setStatus("AI思考中...");
      const response = await postJson(`${API_BASE}/assistant/message`, {
        text,
        context: {
          client: "home-assistant",
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai",
        },
      });

      advanceProgress(3); // 等待确认
      completeProgress();

      addMessage(response.reply || "我已收到。", "assistant");
      renderActions(response.proposedActions || []);
      setStatus(response.proposedActions?.length ? "等待确认" : "完成");
    } catch (error) {
      addMessage(error.message || "助手服务暂时不可用。", "assistant");
      setStatus("连接失败");
      hideProgress();
    }
  });
}

if (platformModules || platformToday || platformAudit) {
  loadPlatform();
  platformRefresh?.addEventListener("click", () => loadPlatform());
  [platformModuleFilter, platformStatusFilter, platformReviewFilter].forEach((control) => {
    control?.addEventListener("change", () => loadPlatform());
  });
  platformFilterReset?.addEventListener("click", () => {
    if (platformModuleFilter) platformModuleFilter.value = "";
    if (platformStatusFilter) platformStatusFilter.value = "";
    if (platformReviewFilter) platformReviewFilter.value = "";
    loadPlatform();
  });
}

platformResearchSearchForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await searchResearchPapers();
});

function resetProgress() {
  progressEl.hidden = false;
  const steps = ["理解意图", "分析板块", "生成动作", "等待确认"];
  progressEl.innerHTML = `
    <span class="ai-progress-dot"></span>
    <span class="ai-progress-steps">
      ${steps.map((s, i) => `<span class="ai-progress-step" data-step="${i}">${s}</span>${i < steps.length - 1 ? '<span class="ai-progress-arrow">→</span>' : ''}`).join('')}
    </span>
    <span class="ai-spinner"></span>
  `;
}

function advanceProgress(index) {
  const dots = progressEl.querySelectorAll(".ai-progress-step");
  dots.forEach((d, i) => {
    if (i < index) d.className = "ai-progress-step done";
    else if (i === index) d.className = "ai-progress-step current";
  });
}

function completeProgress() {
  const dots = progressEl.querySelectorAll(".ai-progress-step");
  dots.forEach(d => d.className = "ai-progress-step done");
  const spinner = progressEl.querySelector(".ai-spinner");
  if (spinner) {
    spinner.outerHTML = '<span class="ai-done-check">✓</span>';
  }
  // 2 秒后自动隐藏
  setTimeout(hideProgress, 2000);
}

function hideProgress() {
  if (progressEl) progressEl.hidden = true;
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `请求失败：${response.status}`);
  }
  return data;
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `请求失败：${response.status}`);
  }
  return data;
}

async function loadPlatform() {
  if (platformRefresh) platformRefresh.disabled = true;
  try {
    const todayDate = localDateString();
    const opsParams = new URLSearchParams({ limit: "12" });
    if (platformModuleFilter?.value) opsParams.set("module", platformModuleFilter.value);
    if (platformStatusFilter?.value) opsParams.set("status", platformStatusFilter.value);
    if (platformReviewFilter?.value) opsParams.set("requiresReview", platformReviewFilter.value);
    const [ops, todayResponse, researchResponse] = await Promise.all([
      getJson(`${API_BASE}/platform/ops?${opsParams.toString()}`),
      getJson(`${API_BASE}/platform/today?date=${encodeURIComponent(todayDate)}&limit=3`),
      getJson(`${API_BASE}/airesearch/overview?limit=3`).catch((error) => ({ ok: false, error })),
    ]);
    renderPlatformModules(ops.modules || []);
    renderPlatformToday(todayResponse.context || {});
    renderPlatformAudit(ops.runs || [], ops.events || []);
    renderPlatformOps(ops);
    if (researchResponse.ok === false) {
      renderResearchOverviewError(researchResponse.error);
    } else {
      renderResearchOverview(researchResponse.overview || {});
    }
  } catch (error) {
    renderPlatformError(error);
  } finally {
    if (platformRefresh) platformRefresh.disabled = false;
  }
}

function renderPlatformModules(items) {
  if (!platformModules) return;
  if (!items.length) {
    platformModules.innerHTML = '<div class="platform-empty">暂无模块运行记录。</div>';
    return;
  }
  platformModules.innerHTML = items.map((item) => {
    const moduleName = MODULE_LABELS[item.module] || item.module || "模块";
    const status = item.status || "unknown";
    const lastRun = item.lastRun;
    const runText = lastRun
      ? `${lastRun.runType || "run"} · ${formatTime(lastRun.finishedAt || lastRun.startedAt)}`
      : "暂无运行记录";
    return `
      <article class="module-status">
        <div class="module-status-top">
          <b>${escapeHtml(moduleName)}</b>
          <span class="module-pill">${escapeHtml(status)}</span>
        </div>
        <span>${escapeHtml(runText)}</span>
        <span>${Number(item.capabilityCount || 0)} 个 Action 能力</span>
      </article>
    `;
  }).join("");
}

function renderPlatformToday(context) {
  if (!platformToday) return;
  if (platformDate && context.date) platformDate.textContent = context.date;
  const schedule = context.schedule || {};
  const fitness = context.fitness || {};
  const news = context.news || {};
  const leisure = context.leisure || {};
  const headline = firstTitle(news.items) || firstLeisureTitle(leisure.groups) || "暂无推荐条目";
  const newsRows = renderResearchQueueNewsItems(news.items || []);
  platformToday.innerHTML = `
    <div class="today-facts">
      <div class="today-fact"><b>${Number(schedule.eventCount || 0)}</b><span>日程</span></div>
      <div class="today-fact"><b>${Number(schedule.todoCount || 0)}</b><span>待办</span></div>
      <div class="today-fact"><b>${Number(fitness.calories || 0)}</b><span>千卡</span></div>
    </div>
    <div class="audit-row">
      <div class="audit-row-top">
        <b>跨模块摘要</b>
        <span>${Number(schedule.conflictCount || 0)} 个冲突</span>
      </div>
      <span>新闻 ${Number(news.count || 0)} 条，闲趣 ${Number(leisure.count || 0)} 组，餐食 ${Number(fitness.mealCount || 0)} 条。</span>
    </div>
    <div class="audit-row">
      <div class="audit-row-top"><b>当前推荐</b><span>Action API</span></div>
      <span>${escapeHtml(headline)}</span>
    </div>
    ${newsRows}
  `;
}

function renderResearchQueueNewsItems(items) {
  const rows = Array.isArray(items) ? items.slice(0, 3) : [];
  if (!rows.length) return "";
  return `
    <div class="today-news-list">
      ${rows.map((item) => {
        const title = item.title || item.tag || "新闻主题";
        const section = item.sectionLabel || item.section || "新闻社";
        const note = `from news recommendation${section ? ` · ${section}` : ""}`;
        return `
          <article class="today-news-item">
            <div>
              <b>${escapeHtml(title)}</b>
              <span>${escapeHtml(section)}${item.matchScore ? ` · ${Number(item.matchScore)} 分` : ""}</span>
            </div>
            <button
              type="button"
              class="profile-review-button"
              data-news-research-topic="${escapeAttr(title)}"
              data-news-research-url="${escapeAttr(item.url || "")}"
              data-news-research-note="${escapeAttr(note)}"
            >入研知库</button>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function renderPlatformAudit(runs, events) {
  if (!platformAudit) return;
  const rows = [
    ...runs.slice(0, 3).map((run) => ({
      kind: "run",
      title: `${MODULE_LABELS[run.module] || run.module || "模块"} · ${run.runType || "run"}`,
      meta: `${run.status || "unknown"} · ${formatTime(run.finishedAt || run.startedAt)}`,
    })),
    ...events.slice(0, 2).map((event) => ({
      kind: "event",
      title: event.title || event.eventType || "module event",
      meta: `${MODULE_LABELS[event.module] || event.module || "模块"} · ${formatTime(event.occurredAt)}`,
    })),
  ];
  if (!rows.length) {
    platformAudit.innerHTML = '<div class="platform-empty">暂无审计记录。</div>';
    return;
  }
  platformAudit.innerHTML = rows.map((row) => `
    <article class="audit-row">
      <div class="audit-row-top">
        <b>${escapeHtml(row.title)}</b>
        <span>${escapeHtml(row.kind)}</span>
      </div>
      <span>${escapeHtml(row.meta)}</span>
    </article>
  `).join("");
}

function renderPlatformOps(payload) {
  const summary = payload?.summary || {};
  const filters = payload?.filters || {};
  if (platformOpsSummary) {
    const filterText = filters.module
      ? MODULE_LABELS[filters.module] || filters.module
      : "全部模块";
    platformOpsSummary.textContent = `${filterText} · ${Number(summary.pendingWorkItemCount || 0)} 待办`;
  }
  if (platformMetrics) {
    const statusCounts = summary.runStatusCounts || {};
    platformMetrics.innerHTML = [
      ["统一待办", summary.pendingWorkItemCount || 0],
      ["待审核", summary.pendingReviewCount || 0],
      ["运行记录", summary.recentRunCount || 0],
      ["审计事件", summary.recentEventCount || 0],
      ["待处理画像", summary.pendingProfileChangeCount || 0],
      ["动作", summary.assistantActionCount || 0],
      ["模型调用", summary.modelCallCount || 0],
    ].map(([label, value]) => `
      <div class="ops-metric"><b>${Number(value || 0)}</b><span>${escapeHtml(label)}</span></div>
    `).join("") || '<div class="platform-empty">暂无运行中心摘要。</div>';
    if (statusCounts.failed || statusCounts.blocked) {
      platformMetrics.insertAdjacentHTML("beforeend", `
        <div class="ops-metric"><b>${Number(statusCounts.failed || 0) + Number(statusCounts.blocked || 0)}</b><span>失败/阻断</span></div>
      `);
    }
  }
  renderPendingWorkItems(payload?.pendingWorkItems || []);
  renderPendingReviews(payload?.pendingReviews || []);
  renderProfileChanges(payload?.profileChanges || []);
  renderExecutionTimeline(payload || {});
}

function renderResearchOverview(overview) {
  if (!platformResearch) return;
  const database = overview.database || {};
  const candidateReview = overview.candidateReview || {};
  const clusters = overview.clusters || {};
  const digest = overview.digest || {};
  const site = overview.site || {};
  const siteStats = site.stats || {};
  const siteReady = siteStats.found && site.api?.papers?.found && site.api?.searchIndex?.found;
  if (platformResearchSummary) {
    platformResearchSummary.textContent = siteReady ? "站点已生成" : "站点待检查";
  }
  const metrics = [
    ["论文", database.paperCount || siteStats.paperCount || digest.paperCount || 0],
    ["事实", database.factCount || siteStats.factCount || digest.factCount || 0],
    ["聚类", clusters.clusterCount || siteStats.clusterCount || 0],
    ["候选", candidateReview.count || database.candidateCount || 0],
    ["画像", database.profileCount || 0],
    ["站点", siteReady ? "OK" : "MISS"],
  ];
  const candidateRows = (candidateReview.items || []).slice(0, 3).map((item) => `
    <article class="audit-row review">
      <div class="audit-row-top">
        <b>${escapeHtml(item.title || "待评审候选")}</b>
        <span>${escapeHtml(item.status || "candidate")}</span>
      </div>
      <span>${escapeHtml(item.identifier || "无标识")} · score ${formatNumber(item.score)}</span>
    </article>
  `).join("") || '<div class="platform-empty">暂无候选评审条目。</div>';
  const clusterRows = (clusters.items || []).slice(0, 3).map((item) => `
    <article class="audit-row">
      <div class="audit-row-top">
        <b>${escapeHtml(item.label || item.clusterId || "研究聚类")}</b>
        <span>${escapeHtml(item.factType || "cluster")}</span>
      </div>
      <span>${Number(item.paperCount || 0)} 篇论文 · ${Number(item.factCount || 0)} 条事实</span>
    </article>
  `).join("") || '<div class="platform-empty">暂无研究聚类。</div>';
  platformResearch.innerHTML = `
    <div class="research-status-grid">
      ${metrics.map(([label, value]) => `
        <div class="research-status-item">
          <b>${escapeHtml(value)}</b>
          <span>${escapeHtml(label)}</span>
        </div>
      `).join("")}
    </div>
    <div class="research-columns">
      <div class="research-list">
        <div class="audit-row">
          <div class="audit-row-top">
            <b>发布站点</b>
            <span>${escapeHtml(siteStats.generatedAt ? formatTime(siteStats.generatedAt) : "未生成")}</span>
          </div>
          <span>${escapeHtml(siteStats.path || "site-current/api/stats.json")} · ${Number(siteStats.reportCount || 0)} 份报告</span>
        </div>
        ${candidateRows}
      </div>
      <div class="research-list">
        <div class="audit-row">
          <div class="audit-row-top">
            <b>Digest</b>
            <span>${escapeHtml(digest.generatedAt ? formatTime(digest.generatedAt) : "未生成")}</span>
          </div>
          <span>${Number(digest.paperCount || 0)} 篇论文 · ${Number(digest.factCount || 0)} 条事实</span>
        </div>
        ${clusterRows}
      </div>
    </div>
  `;
}

async function searchResearchPapers() {
  if (!platformResearchSearchInput || !platformResearchSearchResults) return;
  const query = platformResearchSearchInput.value.trim();
  if (!query) {
    platformResearchSearchResults.innerHTML = '<div class="platform-empty">输入论文题名、作者、venue 或 paper key。</div>';
    return;
  }
  const button = platformResearchSearchForm?.querySelector("button[type='submit']");
  if (button) button.disabled = true;
  platformResearchSearchResults.innerHTML = '<div class="platform-empty">正在检索论文库...</div>';
  try {
    const params = new URLSearchParams({ q: query, limit: "5" });
    const result = await getJson(`${API_BASE}/airesearch/papers/search?${params.toString()}`);
    renderResearchPaperResults(result.items || [], result.query || query);
  } catch (error) {
    platformResearchSearchResults.innerHTML = `<div class="platform-empty">${escapeHtml(error?.message || "论文搜索暂时不可用。")}</div>`;
  } finally {
    if (button) button.disabled = false;
  }
}

function renderResearchPaperResults(items, query) {
  if (!platformResearchSearchResults) return;
  if (!items.length) {
    platformResearchSearchResults.innerHTML = `<div class="platform-empty">没有匹配 “${escapeHtml(query)}” 的论文。</div>`;
    return;
  }
  platformResearchSearchResults.innerHTML = items.map((item) => {
    const authors = Array.isArray(item.authors) ? item.authors.slice(0, 3).join(", ") : "";
    const meta = [
      item.year || "",
      item.venue || "",
      authors,
    ].filter(Boolean).join(" · ");
    return `
      <article class="audit-row">
        <div class="audit-row-top">
          <b>${escapeHtml(item.title || item.paperKey || "未命名论文")}</b>
          <span>${escapeHtml(item.paperKey || "paper")}</span>
        </div>
        <span>${escapeHtml(meta || "暂无作者或 venue 信息")}</span>
      </article>
    `;
  }).join("");
}

function renderResearchOverviewError(error) {
  if (!platformResearch) return;
  platformResearch.innerHTML = `<div class="platform-empty">${escapeHtml(error?.message || "研知库概览暂时不可用。")}</div>`;
  if (platformResearchSummary) platformResearchSummary.textContent = "读取失败";
}

function renderPendingWorkItems(items) {
  if (!platformWorkQueue) return;
  if (!items.length) {
    platformWorkQueue.innerHTML = '<div class="platform-empty">暂无统一待办。</div>';
    return;
  }
  platformWorkQueue.innerHTML = items.slice(0, 8).map((item) => {
    const primary = item.primaryAction ? renderWorkActionButton(item.primaryAction, item.sourceId) : "";
    const secondary = item.secondaryAction ? renderWorkActionButton(item.secondaryAction, item.sourceId) : "";
    return `
      <article class="audit-row work-item ${escapeAttr(item.kind || "item")}">
        <div class="audit-row-top">
          <b>${escapeHtml(item.title || "待处理事项")}</b>
          <span>${escapeHtml(MODULE_LABELS[item.module] || item.module || "模块")}</span>
        </div>
        <span>${escapeHtml(item.detail || item.kind || "pending")} · ${formatTime(item.createdAt)} · ${escapeHtml(item.source || "system")}</span>
        ${primary || secondary ? `<div class="profile-change-actions">${primary}${secondary}</div>` : ""}
      </article>
    `;
  }).join("");
}

function renderWorkActionButton(action, sourceId) {
  const classes = `profile-review-button${action.danger ? " danger" : ""}`;
  const input = JSON.stringify(action.input || {});
  return `
    <button
      type="button"
      class="${classes}"
      data-work-action="${escapeAttr(action.action || "")}"
      data-work-input="${escapeAttr(input)}"
      data-work-source-id="${escapeAttr(sourceId || "")}"
      data-work-confirm="${action.confirm ? "true" : "false"}"
    >${escapeHtml(action.label || "处理")}</button>
  `;
}

function renderPendingReviews(items) {
  if (!platformReviews) return;
  if (!items.length) {
    platformReviews.innerHTML = '<div class="platform-empty">暂无待审核项。</div>';
    return;
  }
  platformReviews.innerHTML = items.slice(0, 6).map((item) => `
    <article class="audit-row review">
      <div class="audit-row-top">
        <b>${escapeHtml(item.title || item.eventType || "待审核事件")}</b>
        <span>${escapeHtml(MODULE_LABELS[item.module] || item.module || "模块")}</span>
      </div>
      <span>${escapeHtml(item.eventType || "event")} · ${formatTime(item.occurredAt)} · ${escapeHtml(item.source || "system")}</span>
    </article>
  `).join("");
}

function renderProfileChanges(items) {
  if (!platformProfileChanges) return;
  if (!items.length) {
    platformProfileChanges.innerHTML = '<div class="platform-empty">暂无画像变更。</div>';
    return;
  }
  platformProfileChanges.innerHTML = items.slice(0, 8).map((item) => {
    const status = item.reverted || item.review?.status === "reverted"
      ? "已回滚"
      : item.reviewed ? "已处理" : "待处理";
    const oldValue = formatProfileValue(item.oldValue);
    const newValue = formatProfileValue(item.newValue);
    const reviewMeta = item.reviewed && item.review
      ? ` · ${formatTime(item.review.reviewedAt)}`
      : "";
    const actionsHtml = item.reviewed
      ? ""
      : `
        <div class="profile-change-actions">
          <button type="button" class="profile-review-button" data-profile-change-review="${escapeAttr(item.id)}">标记处理</button>
          ${item.field === "*" ? "" : `<button type="button" class="profile-review-button danger" data-profile-change-revert="${escapeAttr(item.id)}">回滚字段</button>`}
        </div>
      `;
    return `
      <article class="audit-row profile-change ${item.reviewed ? "reviewed" : "pending"}">
        <div class="audit-row-top">
          <b>${escapeHtml(MODULE_LABELS[item.module] || item.module || "画像")} · ${escapeHtml(item.field || "field")}</b>
          <span>${escapeHtml(status)}</span>
        </div>
        <span>${escapeHtml(item.summary || "画像字段变更")} · ${escapeHtml(item.source || "action")} · ${formatTime(item.createdAt)}${escapeHtml(reviewMeta)}</span>
        <div class="profile-change-diff">
          <span title="${escapeAttr(oldValue)}">${escapeHtml(oldValue || "空")}</span>
          <span title="${escapeAttr(newValue)}">${escapeHtml(newValue || "空")}</span>
        </div>
        ${actionsHtml}
      </article>
    `;
  }).join("");
}

function renderExecutionTimeline(payload) {
  if (!platformTimeline) return;
  const rows = [
    ...(payload.runs || []).slice(0, 4).map((run) => ({
      kind: "run",
      title: `${MODULE_LABELS[run.module] || run.module || "模块"} · ${run.runType || "run"}`,
      meta: `${run.status || "unknown"} · ${run.source || "source"} · ${formatTime(run.finishedAt || run.startedAt)}`,
    })),
    ...(payload.assistantActions || []).slice(0, 3).map((action) => ({
      kind: "action",
      title: action.action || "assistant action",
      meta: `${action.status || "unknown"} · ${action.source || "api"} · ${formatTime(action.executedAt || action.createdAt)}`,
    })),
    ...(payload.modelCalls || []).slice(0, 2).map((call) => ({
      kind: "model",
      title: `${MODULE_LABELS[call.module] || call.module || "模块"} · ${call.purpose || "model"}`,
      meta: `${call.status || "unknown"} · ${call.model || "model"} · ${Number(call.latencyMs || 0)}ms`,
    })),
    ...(payload.profileChanges || []).slice(0, 2).map((change) => ({
      kind: "profile",
      title: `${MODULE_LABELS[change.module] || change.module || "画像"} · ${change.field || "field"}`,
      meta: `${change.source || "action"} · ${formatTime(change.createdAt)}`,
    })),
  ];
  if (!rows.length) {
    platformTimeline.innerHTML = '<div class="platform-empty">暂无执行轨迹。</div>';
    return;
  }
  platformTimeline.innerHTML = rows.map((row) => `
    <article class="audit-row">
      <div class="audit-row-top">
        <b>${escapeHtml(row.title)}</b>
        <span>${escapeHtml(row.kind)}</span>
      </div>
      <span>${escapeHtml(row.meta)}</span>
    </article>
  `).join("");
}

function renderPlatformError(error) {
  const message = escapeHtml(error.message || "平台 API 暂时不可用。");
  const html = `<div class="platform-empty">${message}</div>`;
  if (platformModules) platformModules.innerHTML = html;
  if (platformToday) platformToday.innerHTML = html;
  if (platformAudit) platformAudit.innerHTML = html;
  if (platformMetrics) platformMetrics.innerHTML = html;
  if (platformWorkQueue) platformWorkQueue.innerHTML = html;
  if (platformReviews) platformReviews.innerHTML = html;
  if (platformTimeline) platformTimeline.innerHTML = html;
  if (platformProfileChanges) platformProfileChanges.innerHTML = html;
  if (platformResearch) platformResearch.innerHTML = html;
  if (platformResearchSummary) platformResearchSummary.textContent = "读取失败";
}

platformToday?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-news-research-topic]");
  if (!button) return;
  const topic = button.getAttribute("data-news-research-topic") || "";
  if (!topic) return;
  if (!window.confirm("确认将这个新闻主题加入研知库候选队列？")) return;
  button.disabled = true;
  button.textContent = "入队中...";
  try {
    await postJson(`${API_BASE}/actions/execute`, {
      action: "news.topic.queue-research",
      input: {
        topic,
        url: button.getAttribute("data-news-research-url") || "",
        note: button.getAttribute("data-news-research-note") || "from news recommendation",
        source: "home-platform",
      },
      context: { client: "home-platform", confirmed: true },
    });
    button.textContent = "已加入";
    setStatus("已加入研知库候选队列");
    await loadPlatform();
  } catch (error) {
    button.disabled = false;
    button.textContent = "重试入队";
    setStatus(error.message || "研知库入队失败");
  }
});

platformWorkQueue?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-work-action]");
  if (!button) return;
  const action = button.getAttribute("data-work-action");
  if (!action) return;
  if (button.getAttribute("data-work-confirm") === "true" && !window.confirm("确认执行这个待办动作？")) return;
  let input = {};
  try {
    input = JSON.parse(button.getAttribute("data-work-input") || "{}");
  } catch {
    setStatus("待办动作参数解析失败");
    return;
  }
  if (action === "profile.change.review" || action === "profile.change.revert" || action === "platform.review.mark") {
    input.note = window.prompt(action === "profile.change.revert" ? "回滚备注（可留空）" : "处理备注（可留空）", "") || "";
  }
  input.source = input.source || "home-platform";
  button.disabled = true;
  button.textContent = "处理中...";
  try {
    await postJson(`${API_BASE}/actions/execute`, {
      action,
      input,
      context: { client: "home-platform", confirmed: true },
    });
    await loadPlatform();
  } catch (error) {
    button.disabled = false;
    button.textContent = "重试";
    setStatus(error.message || "待办动作执行失败");
  }
});

platformProfileChanges?.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-profile-change-review], [data-profile-change-revert]");
  if (!button) return;
  const isRevert = button.hasAttribute("data-profile-change-revert");
  const changeId = button.getAttribute(isRevert ? "data-profile-change-revert" : "data-profile-change-review");
  if (!changeId) return;
  if (isRevert && !window.confirm("确认把这个画像字段恢复到变更前的旧值？")) return;
  const note = window.prompt(isRevert ? "回滚备注（可留空）" : "处理备注（可留空）", "") || "";
  button.disabled = true;
  button.textContent = isRevert ? "回滚中..." : "处理中...";
  try {
    await postJson(`${API_BASE}/actions/execute`, {
      action: isRevert ? "profile.change.revert" : "profile.change.review",
      input: { changeId, note, source: "home-platform" },
      context: { client: "home-platform", confirmed: true },
    });
    await loadPlatform();
  } catch (error) {
    button.disabled = false;
    button.textContent = isRevert ? "重试回滚" : "重试处理";
    setStatus(error.message || (isRevert ? "画像变更回滚失败" : "画像变更处理失败"));
  }
});

function addMessage(text, role) {
  const node = document.createElement("div");
  node.className = `assistant-message ${role === "user" ? "user" : ""}`;
  node.textContent = text;
  messages.appendChild(node);
  messages.scrollTop = messages.scrollHeight;
}

function renderActions(proposedActions) {
  actions.innerHTML = "";
  if (!proposedActions.length) {
    actions.hidden = true;
    return;
  }
  actions.hidden = false;

  const actionEditors = [];
  if (proposedActions.length > 1) {
    const bulkCard = document.createElement("article");
    bulkCard.className = "assistant-action";

    const bulkTitle = document.createElement("b");
    bulkTitle.textContent = `确认全部执行（${proposedActions.length} 项）`;

    const bulkButton = document.createElement("button");
    bulkButton.type = "button";
    bulkButton.textContent = "确认全部";
    bulkButton.addEventListener("click", () => confirmAllActions(actionEditors, bulkButton));

    bulkCard.append(bulkTitle, bulkButton);
    actions.appendChild(bulkCard);
  }

  proposedActions.forEach((proposal) => {
    const card = document.createElement("article");
    card.className = "assistant-action";

    const title = document.createElement("b");
    title.textContent = actionTitle(proposal.action, proposal.input);

    const details = document.createElement("textarea");
    details.className = "assistant-action-editor";
    details.value = JSON.stringify(proposal.input || {}, null, 2);
    details.setAttribute("aria-label", "动作参数 JSON");

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "确认执行";
    button.addEventListener("click", () => confirmAction(proposal, button, details));

    card.append(title, details, button);
    actions.appendChild(card);
    actionEditors.push({ proposal, button, editor: details });
  });
}

async function confirmAllActions(actionEditors, bulkButton) {
  const pending = actionEditors.filter(({ button }) => button.textContent !== "已执行");
  if (!pending.length) {
    addMessage("这些动作已经执行过了。", "assistant");
    return;
  }
  bulkButton.disabled = true;
  bulkButton.textContent = "执行中...";
  showExecutionProgress("批量写入", "同步板块");
  setStatus(`正在执行 ${pending.length} 项...`);

  const completed = [];
  try {
    for (const item of pending) {
      const result = await executeActionFromEditor(item.proposal, item.editor);
      item.button.disabled = true;
      item.editor.disabled = true;
      item.button.textContent = "已执行";
      completed.push(result);
    }
    finishExecutionProgress("批量写入", "同步板块");
    addMessage(`已完成 ${completed.length} 项写入。`, "assistant");
    bulkButton.textContent = "已全部执行";
    setStatus("已同步到所有板块");
    loadPlatform();
    setTimeout(hideProgress, 2000);
  } catch (error) {
    bulkButton.disabled = false;
    bulkButton.textContent = "重试全部";
    pending.forEach(({ button, editor }) => {
      if (button.textContent !== "已执行") {
        button.disabled = false;
        editor.disabled = false;
      }
    });
    addMessage(error.message || "动作执行失败。", "assistant");
    setStatus("执行失败");
    hideProgress();
  }
}

async function confirmAction(proposal, button, editor) {
  button.disabled = true;
  editor.disabled = true;
  button.textContent = "执行中...";

  const isProfile = proposal.action === "profile.update";
  const stepLabel = isProfile ? "更新画像" : "写入后端";
  const syncLabel = isProfile ? "生效到板块" : "同步板块";
  showExecutionProgress(stepLabel, syncLabel);

  setStatus(isProfile ? "正在更新画像..." : "正在写入...");
  try {
    const result = await executeActionFromEditor(proposal, editor);
    finishExecutionProgress(stepLabel, syncLabel);

    addMessage(result.message || "动作已完成。", "assistant");
    button.textContent = "已执行";
    setStatus(isProfile ? "画像已更新" : "已同步到所有板块");
    loadPlatform();
    setTimeout(hideProgress, 2000);

  } catch (error) {
    button.disabled = false;
    editor.disabled = false;
    button.textContent = "重试";
    addMessage(error.message || "动作执行失败。", "assistant");
    setStatus("执行失败");
    hideProgress();
  }
}

async function executeActionFromEditor(proposal, editor) {
  let inputPayload;
  try {
    inputPayload = JSON.parse(editor.value || "{}");
  } catch (error) {
    throw new Error("动作参数不是有效 JSON，请改好后再确认。");
  }
  return postJson(`${API_BASE}/actions/execute`, {
    action: proposal.action,
    input: inputPayload,
    context: { client: "home-assistant", confirmed: true },
  });
}

function showExecutionProgress(stepLabel, syncLabel) {
  if (!progressEl) return;
  progressEl.hidden = false;
  progressEl.innerHTML = `
    <span class="ai-progress-dot"></span>
    <span class="ai-progress-steps">
      <span class="ai-progress-step current">${stepLabel}</span>
      <span class="ai-progress-arrow">→</span>
      <span class="ai-progress-step">${syncLabel}</span>
    </span>
    <span class="ai-spinner"></span>
  `;
}

function finishExecutionProgress(stepLabel, syncLabel) {
  if (!progressEl) return;
  const steps = progressEl.querySelector(".ai-progress-steps");
  const spinner = progressEl.querySelector(".ai-spinner");
  if (steps) {
    steps.innerHTML = `<span class="ai-progress-step done">${stepLabel} ✓</span><span class="ai-progress-arrow">→</span><span class="ai-progress-step done">${syncLabel} ✓</span>`;
  }
  if (spinner) spinner.outerHTML = '<span class="ai-done-check">✓</span>';
}

function actionTitle(action, input) {
  const titles = {
    "fitness.nutrition.create": "写入：塑形馆 / 营养日志",
    "fitness.nutrition.update": "更正：塑形馆 / 营养日志",
    "fitness.nutrition.delete": "删除：塑形馆 / 营养日志",
    "fitness.workout.update": "更正：塑形馆 / 训练日志",
    "fitness.workout.delete": "删除：塑形馆 / 训练日志",
    "fitness.body_metric.update": "更正：塑形馆 / 身体指标",
    "fitness.body_metric.delete": "删除：塑形馆 / 身体指标",
    "schedule.event.create": "写入：时务局 / 日程",
    "schedule.event.update": "更正：时务局 / 日程",
    "schedule.event.delete": "删除：时务局 / 日程",
    "schedule.todo.create": "写入：时务局 / 待办",
    "schedule.todo.update": "更正：时务局 / 待办",
    "schedule.todo.delete": "删除：时务局 / 待办",
    "leisure.item.update": "更正：闲趣集 / 条目",
    "leisure.item.delete": "删除：闲趣集 / 条目",
    "news.topic.queue-research": "写入：新闻社 / 研知库候选",
    "platform.review.mark": "处理：平台 / 审核项",
  };
  if (action === "profile.update") {
    const mod = MODULE_LABELS[(input && input.module) || ""] || "";
    return mod ? `更新画像：${mod}` : "更新画像";
  }
  const base = titles[action] || `动作：${action}`;
  const subject = actionSubject(action, input);
  return subject ? `${base}：${subject}` : base;
}

function actionSubject(action, input) {
  if (!input || typeof input !== "object") return "";
  if (action === "fitness.nutrition.create") return String(input.food || "").trim();
  if (action.startsWith("schedule.")) return String(input.title || "").trim();
  if (action.startsWith("leisure.")) return String(input.title || input.itemId || "").trim();
  if (action.startsWith("news.")) return String(input.title || input.topic || "").trim();
  return "";
}

const MODULE_LABELS = {
  fitness: "塑形馆",
  schedule: "时务局",
  news: "新闻社",
  leisure: "闲趣集",
  airesearch: "研知库",
  platform: "平台",
  profile: "画像",
};

function setStatus(text) {
  statusLine.textContent = text;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function firstTitle(items) {
  const item = Array.isArray(items) ? items.find((entry) => entry && entry.title) : null;
  return item ? item.title : "";
}

function formatProfileValue(value) {
  if (value === null || value === undefined || value === "") return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch (error) {
    return String(value);
  }
}

function firstLeisureTitle(groups) {
  if (!groups) return "";
  const candidates = Array.isArray(groups) ? groups : Object.values(groups);
  for (const group of candidates) {
    const entries = Array.isArray(group) ? group : group?.items;
    const item = Array.isArray(entries) ? entries.find((entry) => entry && entry.title) : null;
    if (item) return item.title;
  }
  return "";
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

function formatNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0";
  return Math.round(number * 1000) / 1000;
}

function localDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}
