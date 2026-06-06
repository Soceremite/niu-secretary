const API_BASE = "/niu-secretary/api";

const form = document.querySelector("[data-assistant-form]");
const input = document.querySelector("[data-assistant-input]");
const messages = document.querySelector("[data-assistant-messages]");
const actions = document.querySelector("[data-assistant-actions]");
const statusLine = document.querySelector("[data-assistant-status]");
const progressEl = document.querySelector("[data-ai-progress]");

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
  });
}

async function confirmAction(proposal, button, editor) {
  let inputPayload;
  try {
    inputPayload = JSON.parse(editor.value || "{}");
  } catch (error) {
    addMessage("动作参数不是有效 JSON，请改好后再确认。", "assistant");
    setStatus("参数格式错误");
    return;
  }
  button.disabled = true;
  editor.disabled = true;
  button.textContent = "执行中...";

  // 显示执行动画
  const isProfile = proposal.action === "profile.update";
  const stepLabel = isProfile ? "更新画像" : "写入后端";
  const syncLabel = isProfile ? "生效到板块" : "同步板块";
  resetProgress();
  const dot = progressEl.querySelector(".ai-progress-dot");
  const steps = progressEl.querySelector(".ai-progress-steps");
  if (steps) steps.innerHTML = `<span class="ai-progress-step current">${stepLabel}</span>`;
  const spinner = progressEl.querySelector(".ai-spinner");

  setStatus(isProfile ? "正在更新画像..." : "正在写入...");
  try {
    const result = await postJson(`${API_BASE}/actions/execute`, {
      action: proposal.action,
      input: inputPayload,
      context: { client: "home-assistant" },
    });

    // 更新动画：写入成功
    if (steps) steps.innerHTML = `<span class="ai-progress-step done">${stepLabel} ✓</span><span class="ai-progress-arrow">→</span><span class="ai-progress-step current">${syncLabel}</span>`;

    // 后端为唯一数据源，无需额外同步

    // 动画完成
    if (steps) steps.innerHTML = `<span class="ai-progress-step done">${stepLabel} ✓</span><span class="ai-progress-arrow">→</span><span class="ai-progress-step done">${syncLabel} ✓</span>`;
    if (spinner) spinner.outerHTML = '<span class="ai-done-check">✓</span>';

    addMessage(result.message || "动作已完成。", "assistant");
    button.textContent = "已执行";
    setStatus(isProfile ? "画像已更新" : "已同步到所有板块");
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

function actionTitle(action, input) {
  const titles = {
    "fitness.nutrition.create": "写入：塑形馆 / 营养日志",
    "schedule.event.create": "写入：时务局 / 日程",
    "schedule.todo.create": "写入：时务局 / 待办",
  };
  if (action === "profile.update") {
    const mod = MODULE_LABELS[(input && input.module) || ""] || "";
    return mod ? `更新画像：${mod}` : "更新画像";
  }
  return titles[action] || `动作：${action}`;
}

const MODULE_LABELS = {
  fitness: "塑形馆",
  schedule: "时务局",
  news: "新闻社",
  leisure: "闲趣集",
};

function setStatus(text) {
  statusLine.textContent = text;
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
