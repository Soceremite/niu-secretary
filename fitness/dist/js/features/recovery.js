// fitness/src/js/features/recovery.js
import { addRecoveryLog, clearRecoveryLogs, listRecoveryLogs } from '../lib/db.js';
import { recoveryStatus, scoreRecovery } from '../lib/recovery.js';
import { createUnifiedRecoveryLog, fetchUnifiedRecoveryLogs } from '../lib/actionApi.js';

export async function initRecovery() {
  const form = document.getElementById('recovery-form');
  form.elements.date.value = new Date().toISOString().slice(0, 10);
  form.addEventListener('submit', saveRecovery);
  document.getElementById('clear-recovery').addEventListener('click', async () => {
    await clearRecoveryLogs();
    document.getElementById('recovery-toast').textContent = '恢复离线缓存已清空，服务器记录不受影响';
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
  let saved = null;
  let synced = false;
  try {
    saved = await createUnifiedRecoveryLog(log);
    synced = true;
  } catch (error) {
    console.warn('Failed to sync recovery log to unified API', error);
  }
  await addRecoveryLog({
    ...log,
    serverId: saved?.id || '',
    source: synced ? 'unified-api' : 'fitness-page',
    syncStatus: synced ? 'synced' : 'pending'
  });
  document.getElementById('recovery-toast').textContent = synced
    ? '恢复状态已同步到统一动作接口，并保留本地缓存'
    : '统一动作接口暂不可用，恢复状态已保留在本地缓存';
  await render();
}

async function render() {
  const [localLogs, unified] = await Promise.all([
    listRecoveryLogs(),
    loadUnifiedRecoveryLogs()
  ]);
  const logs = mergeRecoveryLogs(localLogs, unified.items, { includeLocalCache: unified.offline });
  if (logs[0]) renderResult(logs[0]);
  else document.getElementById('recovery-result').innerHTML = '<div class="empty">保存一次恢复状态后生成训练建议。</div>';
  document.getElementById('recovery-list').innerHTML = logs.length ? logs.slice(0, 8).map((log) => `
    <div class="log-item"><span><strong>${escapeHtml(log.date)}</strong><br>${escapeHtml(log.status.label)} · 睡眠 ${log.sleepHours}h</span><span>${log.score}/100</span></div>
  `).join('') : '<div class="empty">暂无恢复记录。</div>';
  renderTrend(logs);
}

async function loadUnifiedRecoveryLogs() {
  try {
    return { items: await fetchUnifiedRecoveryLogs(), offline: false };
  } catch {
    return { items: [], offline: true };
  }
}

function mergeRecoveryLogs(localLogs, unifiedLogs, options = {}) {
  const merged = new Map();
  const visibleLocalLogs = options.includeLocalCache ? localLogs : localLogs.filter((log) => log.syncStatus === 'pending');
  [...unifiedLogs, ...visibleLocalLogs].forEach((log) => {
    const key = log.serverId || (String(log.id || '').startsWith('rec_') ? log.id : '');
    const fallback = `${log.date}-${log.score}-${log.createdAt || ''}-${log.sleepHours || 0}`;
    const id = key || fallback;
    if (!merged.has(id)) {
      merged.set(id, {
        ...log,
        status: log.status || { label: log.statusLabel || '未知', advice: log.statusAdvice || '' }
      });
    }
  });
  return [...merged.values()].sort((a, b) => {
    const byDate = String(b.date || '').localeCompare(String(a.date || ''));
    if (byDate) return byDate;
    return String(b.createdAt || '').localeCompare(String(a.createdAt || ''));
  });
}

function renderTrend(logs) {
  const container = document.getElementById('recovery-trend-chart');
  if (!container) return;
  
  const recent = logs.slice(0, 7).reverse();
  if (!recent.length) {
    container.innerHTML = '<div class="empty">暂无趋势数据。</div>';
    return;
  }
  
  container.innerHTML = recent.map((log) => {
    const height = log.score;
    const date = new Date(log.date);
    const dateStr = `${date.getMonth() + 1}/${date.getDate()}`;
    return `
      <div style="display: flex; flex-direction: column; align-items: center; flex: 1;">
        <div class="trend-bar" style="height: ${height}%; width: 100%;" data-score="${log.score}"></div>
        <div class="trend-date">${dateStr}</div>
      </div>
    `;
  }).join('');
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
