const API_BASE = "/niu-secretary/api";
const TOKEN_KEY = "niu-secretary-admin-token";

const MODULES = {
  overview: {
    label: "平台总览",
    resource: "platform.ops",
    boundary: "查看模块健康、最近运行、待审核事件。写操作请进入具体模块。",
    tables: [],
  },
  news: {
    label: "新闻社",
    resource: "news.recommend",
    boundary: "新闻社当前支持推荐读取和研究主题入队，暂不直接编辑新闻内容。",
    createLabel: "入队主题",
    createAction: "news.topic.queue-research",
    fields: [
      field("title", "标题", "text", true),
      field("topic", "主题", "text", true),
      field("source", "来源", "text", false, "admin-console"),
    ],
    columns: [
      column("title", "标题"),
      column("summary", "摘要"),
      column("sectionLabel", "栏目"),
    ],
    normalize: (data) => data.items || [],
  },
  fitness: {
    label: "塑形馆",
    resource: "fitness.nutrition",
    boundary: "营养、训练、体征支持新增/编辑/删除；评估和恢复仍从业务页面录入。",
    tabs: [
      table("nutrition", "营养", "fitness.nutrition", "fitness.nutrition.create", "fitness.nutrition.update", "fitness.nutrition.delete", [
        field("food", "食物", "text", true),
        field("date", "日期", "date", true, today()),
        field("calories", "热量", "number", false, 0),
        field("proteinG", "蛋白 g", "number", false, 0),
        field("carbsG", "碳水 g", "number", false, 0),
        field("fatG", "脂肪 g", "number", false, 0),
      ], [column("food", "食物"), column("date", "日期"), column("calories", "热量"), column("source", "来源")]),
      table("workouts", "训练", "fitness.workouts", "fitness.workout.create", "fitness.workout.update", "fitness.workout.delete", [
        field("name", "训练", "text", true),
        field("date", "日期", "date", true, today()),
        field("durationMin", "分钟", "number", false, 0),
        field("intensity", "强度", "select", false, "medium", ["low", "medium", "high"]),
        field("calories", "消耗", "number", false, 0),
        field("note", "备注", "text"),
      ], [column("name", "训练"), column("date", "日期"), column("durationMin", "分钟"), column("intensity", "强度")]),
      table("metrics", "体征", "fitness.metrics", "fitness.body_metric.create", "fitness.body_metric.update", "fitness.body_metric.delete", [
        field("date", "日期", "date", true, today()),
        field("weightKg", "体重 kg", "number"),
        field("bodyFatPct", "体脂 %", "number"),
        field("waistCm", "腰围 cm", "number"),
        field("note", "备注", "text"),
      ], [column("date", "日期"), column("weightKg", "体重"), column("bodyFatPct", "体脂"), column("waistCm", "腰围")]),
    ],
  },
  schedule: {
    label: "时务局",
    resource: "schedule.events",
    boundary: "日程和待办支持新增/编辑/删除；待办完成状态可在表格中切换。",
    tabs: [
      table("events", "日程", "schedule.events", "schedule.event.create", "schedule.event.update", "schedule.event.delete", [
        field("title", "标题", "text", true),
        field("date", "日期", "date", true, today()),
        field("time", "时间", "time"),
        field("note", "备注", "text"),
      ], [column("title", "标题"), column("date", "日期"), column("time", "时间"), column("note", "备注")]),
      table("todos", "待办", "schedule.todos", "schedule.todo.create", "schedule.todo.update", "schedule.todo.delete", [
        field("title", "标题", "text", true),
        field("date", "日期", "date"),
        field("priority", "优先级", "select", false, "normal", ["low", "normal", "high"]),
      ], [column("title", "标题"), column("date", "日期"), column("priority", "优先级"), column("done", "完成")], "schedule.todo.toggle"),
    ],
  },
  leisure: {
    label: "闲趣集",
    resource: "leisure.items",
    boundary: "闲趣集支持条目编辑/删除；收藏、评分等互动继续通过推荐页写入。",
    updateAction: "leisure.item.update",
    deleteAction: "leisure.item.delete",
    fields: [
      field("category", "分类", "select", true, "movie", ["movie", "book", "game", "music", "video"]),
      field("title", "标题", "text", true),
      field("payloadText", "元数据 JSON", "textarea"),
    ],
    columns: [
      column("title", "标题"),
      column("category", "分类"),
      column("source", "来源"),
      column("updatedAt", "更新"),
    ],
    normalize: (data) => data.items || [],
    mapForAction: (values, record) => ({
      id: record.id,
      category: values.category,
      title: values.title,
      payload: safeJson(values.payloadText, record.payload || {}),
      source: "admin-console",
    }),
    prepare: (record) => ({ ...record, payloadText: JSON.stringify(record.payload || {}, null, 2) }),
  },
  airesearch: {
    label: "研知库",
    resource: "airesearch.overview",
    boundary: "研知库在统一管理台内提供概览、论文搜索和候选入队；深度流水线仍在研知库专属 Admin 中执行。",
    createLabel: "新增候选",
    createAction: "airesearch.queue.add",
    fields: [
      field("title", "标题", "text", true),
      field("note", "备注", "text"),
      field("source", "来源", "text", false, "admin-console"),
    ],
    columns: [
      column("title", "标题"),
      column("venue", "来源/状态"),
      column("year", "年份"),
      column("paperKey", "Key"),
    ],
    normalize: (data) => {
      const overview = data.overview || {};
      return [...(overview.papers || []), ...(overview.candidates || [])];
    },
  },
};

const loginScreen = document.querySelector("[data-login-screen]");
const loginForm = document.querySelector("[data-login-form]");
const loginMessage = document.querySelector("[data-login-message]");
const shell = document.querySelector("[data-admin-shell]");
const nav = document.querySelector("[data-admin-nav]");
const title = document.querySelector("[data-admin-title]");
const statusEl = document.querySelector("[data-admin-status]");
const summaryEl = document.querySelector("[data-admin-summary]");
const primaryTitle = document.querySelector("[data-primary-title]");
const primarySubtitle = document.querySelector("[data-primary-subtitle]");
const primaryEl = document.querySelector("[data-admin-primary]");
const toolbar = document.querySelector("[data-admin-toolbar]");
const auditEl = document.querySelector("[data-admin-audit]");
const boundaryEl = document.querySelector("[data-admin-boundary]");
const secondaryEl = document.querySelector("[data-admin-secondary]");
const refresh = document.querySelector("[data-admin-refresh]");
const createButton = document.querySelector("[data-create-button]");
const dialog = document.querySelector("[data-record-dialog]");
const recordForm = document.querySelector("[data-record-form]");
const recordFields = document.querySelector("[data-record-fields]");
const recordMessage = document.querySelector("[data-record-message]");
const dialogTitle = document.querySelector("[data-dialog-title]");

let currentModule = "overview";
let currentTable = "";
let currentRows = [];
let editorState = null;

init();

async function init() {
  loginForm.addEventListener("submit", login);
  document.querySelector("[data-logout]").addEventListener("click", logout);
  nav.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-module]");
    if (button) setModule(button.dataset.module);
  });
  refresh.addEventListener("click", () => loadModule());
  createButton.addEventListener("click", () => openEditor("create"));
  recordForm.addEventListener("submit", saveRecord);
  document.querySelectorAll("[data-dialog-close]").forEach((button) => button.addEventListener("click", () => dialog.close()));
  if (token()) {
    try {
      await adminGet("/admin/session");
      showShell();
      setModule("overview");
      return;
    } catch {
      localStorage.removeItem(TOKEN_KEY);
    }
  }
  showLogin();
}

async function login(event) {
  event.preventDefault();
  loginMessage.textContent = "登录中...";
  const data = Object.fromEntries(new FormData(loginForm));
  try {
    const result = await publicPost("/admin/session", data);
    localStorage.setItem(TOKEN_KEY, result.token);
    loginForm.password.value = "";
    showShell();
    setModule("overview");
  } catch (error) {
    loginMessage.textContent = error.message || "登录失败。";
  }
}

function logout() {
  localStorage.removeItem(TOKEN_KEY);
  showLogin();
}

function showLogin() {
  loginScreen.hidden = false;
  shell.hidden = true;
}

function showShell() {
  loginScreen.hidden = true;
  shell.hidden = false;
}

function setModule(moduleName) {
  currentModule = moduleName;
  currentTable = (MODULES[moduleName].tabs || [])[0]?.id || "";
  nav.querySelectorAll("button").forEach((button) => button.classList.toggle("active", button.dataset.module === moduleName));
  loadModule();
}

async function loadModule() {
  const config = activeConfig();
  title.textContent = MODULES[currentModule].label;
  primaryTitle.textContent = currentTable ? `${MODULES[currentModule].label} / ${config.label}` : `${MODULES[currentModule].label}数据`;
  primarySubtitle.textContent = config.createAction || config.updateAction ? "可管理记录表。新增、编辑、删除都会写入统一 Action 审计。" : "只读运营数据。";
  boundaryEl.textContent = MODULES[currentModule].boundary;
  renderToolbar();
  setStatus("读取中...");
  try {
    const [ops, data] = await Promise.all([adminData("platform.ops"), adminData(config.resource)]);
    renderSummary(ops);
    renderAudit(ops);
    currentRows = normalizeRows(config, data);
    renderRows(config, currentRows);
    renderSecondary();
    setStatus(`已刷新 ${new Date().toLocaleTimeString("zh-CN")}`);
  } catch (error) {
    if (error.status === 401) logout();
    primaryEl.innerHTML = `<div class="empty">${escapeHtml(error.message || "读取失败")}</div>`;
    setStatus("读取失败");
  }
}

function renderToolbar() {
  const tabs = MODULES[currentModule].tabs || [];
  toolbar.innerHTML = tabs.length ? tabs.map((tab) => `<button type="button" class="${tab.id === currentTable ? "active" : ""}" data-table="${tab.id}">${escapeHtml(tab.label)}</button>`).join("") : "";
  toolbar.querySelectorAll("button[data-table]").forEach((button) => {
    button.addEventListener("click", () => {
      currentTable = button.dataset.table;
      loadModule();
    });
  });
  const config = activeConfig();
  createButton.hidden = !(config.createAction);
  createButton.textContent = config.createLabel || "新增";
}

function renderSummary(ops) {
  const modules = ops.modules || [];
  const summary = ops.summary || {};
  summaryEl.innerHTML = [
    metric("模块", modules.length),
    metric("运行", summary.runCount || 0),
    metric("待办", summary.pendingWorkItemCount || 0),
    metric("审核", summary.pendingReviewCount || 0),
  ].join("");
}

function renderAudit(ops) {
  const rows = [
    ...(ops.runs || []).slice(0, 5).map((item) => ({ title: item.module || "run", detail: item.runType || "", meta: item.status || "" })),
    ...(ops.events || []).slice(0, 5).map((item) => ({ title: item.title || item.eventType, detail: item.module || "", meta: item.eventType || "" })),
  ];
  auditEl.innerHTML = rows.length ? rows.map(renderCompactRow).join("") : '<div class="empty">暂无运行与事件。</div>';
}

function renderRows(config, rows) {
  if (currentModule === "overview") {
    primaryEl.innerHTML = rows.map(renderCompactRow).join("");
    return;
  }
  if (!rows.length) {
    primaryEl.innerHTML = '<div class="empty">暂无数据。</div>';
    return;
  }
  primaryEl.innerHTML = `
    <div class="data-table" style="--cols:${config.columns.length + 1}">
      <div class="table-row table-head">${config.columns.map((item) => `<b>${escapeHtml(item.label)}</b>`).join("")}<b>操作</b></div>
      ${rows.map((row) => renderTableRow(config, row)).join("")}
    </div>
  `;
  primaryEl.querySelectorAll("[data-edit-id]").forEach((button) => button.addEventListener("click", () => openEditor("edit", findRow(button.dataset.editId))));
  primaryEl.querySelectorAll("[data-delete-id]").forEach((button) => button.addEventListener("click", () => deleteRecord(findRow(button.dataset.deleteId))));
  primaryEl.querySelectorAll("[data-toggle-id]").forEach((button) => button.addEventListener("click", () => toggleTodo(findRow(button.dataset.toggleId))));
}

function renderTableRow(config, row) {
  const controls = [
    config.toggleAction ? `<button type="button" data-toggle-id="${escapeHtml(row.id)}">${row.done ? "设为未完成" : "完成"}</button>` : "",
    config.updateAction ? `<button type="button" data-edit-id="${escapeHtml(row.id || "")}">编辑</button>` : "",
    config.deleteAction ? `<button type="button" class="danger" data-delete-id="${escapeHtml(row.id || "")}">删除</button>` : "",
  ].filter(Boolean).join("");
  return `
    <div class="table-row">
      ${config.columns.map((item) => `<span>${escapeHtml(readCell(row, item.key))}</span>`).join("")}
      <span class="row-actions">${controls || "<em>只读</em>"}</span>
    </div>
  `;
}

function renderSecondary() {
  const config = MODULES[currentModule];
  const rows = [
    { title: "读取", detail: activeConfig().resource, meta: "GET /api/admin/data" },
    { title: "写入", detail: activeConfig().createAction || activeConfig().updateAction || "只读", meta: "POST /api/admin/actions/execute" },
  ];
  if (currentModule === "airesearch") rows.push({ title: "专属流水线", detail: "/niu-secretary/airesearch/admin/", meta: "受保护子后台" });
  secondaryEl.innerHTML = rows.map(renderCompactRow).join("");
}

function openEditor(mode, record = {}) {
  const config = activeConfig();
  const prepared = config.prepare ? config.prepare(record) : record;
  editorState = { mode, config, record };
  dialogTitle.textContent = mode === "create" ? (config.createLabel || "新增记录") : "编辑记录";
  recordMessage.textContent = "";
  recordFields.innerHTML = config.fields.map((item) => renderField(item, prepared[item.key] ?? item.defaultValue ?? "")).join("");
  dialog.showModal();
}

async function saveRecord(event) {
  event.preventDefault();
  const { mode, config, record } = editorState || {};
  const values = Object.fromEntries(new FormData(recordForm));
  const action = mode === "create" ? config.createAction : config.updateAction;
  const input = config.mapForAction ? config.mapForAction(values, record) : buildInput(config.fields, values, mode === "edit" ? record.id : "");
  recordMessage.textContent = "保存中...";
  try {
    await adminPost("/admin/actions/execute", { action, input, context: { confirmed: true } });
    dialog.close();
    await loadModule();
  } catch (error) {
    recordMessage.textContent = error.message || "保存失败。";
  }
}

async function deleteRecord(record) {
  const config = activeConfig();
  if (!record?.id || !config.deleteAction || !window.confirm(`确认删除：${record.title || record.food || record.name || record.id}？`)) return;
  await adminPost("/admin/actions/execute", { action: config.deleteAction, input: { id: record.id, source: "admin-console" } });
  await loadModule();
}

async function toggleTodo(record) {
  if (!record?.id) return;
  await adminPost("/admin/actions/execute", { action: "schedule.todo.toggle", input: { id: record.id, done: !record.done, source: "admin-console" } });
  await loadModule();
}

function activeConfig() {
  const module = MODULES[currentModule];
  return (module.tabs || []).find((item) => item.id === currentTable) || module;
}

function normalizeRows(config, data) {
  if (currentModule === "overview") {
    return [
      ...(data.modules || []).map((item) => ({ title: MODULES[item.module]?.label || item.module, detail: `${item.capabilityCount || 0} 个能力`, meta: item.status || "unknown" })),
      ...(data.pendingWorkItems || []).slice(0, 10).map((item) => ({ title: item.title || item.action || "待处理", detail: item.module || "", meta: item.type || "work" })),
    ];
  }
  return config.normalize ? config.normalize(data) : (data.items || []);
}

function buildInput(fields, values, id = "") {
  const input = { source: "admin-console" };
  if (id) input.id = id;
  fields.forEach((item) => {
    const value = values[item.key];
    if (item.type === "number") input[item.key] = value === "" ? 0 : Number(value);
    else if (value !== "") input[item.key] = value;
  });
  return input;
}

function renderField(item, value) {
  if (item.type === "select") {
    return `<label>${escapeHtml(item.label)}<select name="${escapeHtml(item.key)}">${item.options.map((option) => `<option value="${escapeHtml(option)}" ${String(value) === option ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}</select></label>`;
  }
  if (item.type === "textarea") {
    return `<label class="wide">${escapeHtml(item.label)}<textarea name="${escapeHtml(item.key)}" rows="7">${escapeHtml(value)}</textarea></label>`;
  }
  return `<label>${escapeHtml(item.label)}<input name="${escapeHtml(item.key)}" type="${escapeHtml(item.type)}" value="${escapeHtml(value)}" ${item.required ? "required" : ""}></label>`;
}

async function adminData(resource) {
  return adminGet(`/admin/data?resource=${encodeURIComponent(resource)}&from=${daysAgo(30)}&to=${today()}&limit=100`);
}

async function adminGet(path) {
  const response = await fetch(API_BASE + path, { headers: authHeaders() });
  return parseResponse(response);
}

async function adminPost(path, payload) {
  const response = await fetch(API_BASE + path, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

async function publicPost(path, payload) {
  const response = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseResponse(response);
}

async function parseResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    const error = new Error(data.message || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

function authHeaders() {
  return { Authorization: `Bearer ${token()}` };
}

function token() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function metric(label, value) {
  return `<article class="metric-card"><b>${escapeHtml(value)}</b><span>${escapeHtml(label)}</span></article>`;
}

function renderCompactRow(item) {
  return `<div class="data-row"><span><b>${escapeHtml(item.title)}</b><small>${escapeHtml(item.detail)}</small></span><code>${escapeHtml(item.meta)}</code></div>`;
}

function readCell(row, key) {
  const value = row[key];
  if (typeof value === "boolean") return value ? "是" : "否";
  return value == null ? "" : value;
}

function findRow(id) {
  return currentRows.find((row) => String(row.id) === String(id)) || {};
}

function table(id, label, resource, createAction, updateAction, deleteAction, fields, columns, toggleAction = "") {
  return { id, label, resource, createAction, updateAction, deleteAction, fields, columns, toggleAction };
}

function field(key, label, type = "text", required = false, defaultValue = "", options = []) {
  return { key, label, type, required, defaultValue, options };
}

function column(key, label) {
  return { key, label };
}

function safeJson(value, fallback) {
  try {
    return JSON.parse(value || "{}");
  } catch {
    return fallback;
  }
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgo(days) {
  return new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
}

function setStatus(text) {
  statusEl.textContent = text;
}

function escapeHtml(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}
