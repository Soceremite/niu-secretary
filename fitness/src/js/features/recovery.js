// fitness/src/js/features/recovery.js
import { addRecoveryLog, clearRecoveryLogs, listRecoveryLogs } from '../lib/db.js';
import { recoveryStatus, scoreRecovery } from '../lib/recovery.js';

export async function initRecovery() {
  const form = document.getElementById('recovery-form');
  form.elements.date.value = new Date().toISOString().slice(0, 10);
  form.addEventListener('submit', saveRecovery);
  document.getElementById('clear-recovery').addEventListener('click', async () => {
    await clearRecoveryLogs();
    await render();
  });
  await render();
}

async function saveRecovery(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  const log = {
    date: data.date,
    sleepHours: Number(data.sleepHours || 0),
    sleepQuality: Number(data.sleepQuality || 0),
    stress: Number(data.stress || 0),
    soreness: Number(data.soreness || 0),
    lastRpe: Number(data.lastRpe || 0)
  };
  log.score = scoreRecovery(log);
  log.status = recoveryStatus(log.score);
  await addRecoveryLog(log);
  document.getElementById('recovery-toast').textContent = '恢复状态已保存';
  await render();
}

async function render() {
  const logs = (await listRecoveryLogs()).sort((a, b) => b.date.localeCompare(a.date));
  if (logs[0]) renderResult(logs[0]);
  else document.getElementById('recovery-result').innerHTML = '<div class="empty">保存一次恢复状态后生成训练建议。</div>';
  document.getElementById('recovery-list').innerHTML = logs.length ? logs.slice(0, 8).map((log) => `
    <div class="log-item"><span><strong>${escapeHtml(log.date)}</strong><br>${escapeHtml(log.status.label)} · 睡眠 ${log.sleepHours}h</span><span>${log.score}/100</span></div>
  `).join('') : '<div class="empty">暂无恢复记录。</div>';
}

function renderResult(log) {
  document.getElementById('recovery-result').innerHTML = `
    <div class="result-grid readiness-result">
      <div><b>${log.score}</b><span>恢复分</span></div>
      <div><b>${escapeHtml(log.status.label)}</b><span>训练状态</span></div>
    </div>
    <div class="advice-box">${escapeHtml(log.status.advice)}</div>
  `;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
