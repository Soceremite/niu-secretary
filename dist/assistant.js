const API_BASE = "/niu-secretary/api";

const form = document.querySelector("[data-assistant-form]");
const input = document.querySelector("[data-assistant-input]");
const messages = document.querySelector("[data-assistant-messages]");
const actions = document.querySelector("[data-assistant-actions]");
const statusLine = document.querySelector("[data-assistant-status]");

if (form && input && messages && actions && statusLine) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    addMessage(text, "user");
    setStatus("处理中...");
    actions.hidden = true;
    actions.innerHTML = "";

    try {
      const response = await postJson(`${API_BASE}/assistant/message`, {
        text,
        context: {
          client: "home-assistant",
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Shanghai",
        },
      });
      addMessage(response.reply || "我已收到。", "assistant");
      renderActions(response.proposedActions || []);
      setStatus(response.proposedActions?.length ? "等待确认" : "");
    } catch (error) {
      addMessage(error.message || "助手服务暂时不可用。", "assistant");
      setStatus("连接失败");
    }
  });
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
    title.textContent = actionTitle(proposal.action);

    const details = document.createElement("pre");
    details.textContent = JSON.stringify(proposal.input || {}, null, 2);

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "确认执行";
    button.addEventListener("click", () => confirmAction(proposal, button));

    card.append(title, details, button);
    actions.appendChild(card);
  });
}

async function confirmAction(proposal, button) {
  button.disabled = true;
  button.textContent = "执行中...";
  setStatus("正在写入统一动作接口...");
  try {
    const result = await postJson(`${API_BASE}/actions/execute`, {
      action: proposal.action,
      input: proposal.input || {},
      context: { client: "home-assistant" },
    });
    addMessage(result.message || "动作已完成。", "assistant");
    button.textContent = "已执行";
    setStatus("已同步");
  } catch (error) {
    button.disabled = false;
    button.textContent = "重试";
    addMessage(error.message || "动作执行失败。", "assistant");
    setStatus("执行失败");
  }
}

function actionTitle(action) {
  const titles = {
    "fitness.nutrition.create": "写入：塑形馆 / 营养日志",
    "schedule.event.create": "写入：时务局 / 日程",
    "schedule.todo.create": "写入：时务局 / 待办",
  };
  return titles[action] || `动作：${action}`;
}

function setStatus(text) {
  statusLine.textContent = text;
}
