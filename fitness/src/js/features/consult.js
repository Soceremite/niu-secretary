
// fitness/src/js/features/consult.js
import { addConsultLog, listConsultLogs } from '../lib/db.js';
import { assessConsult } from '../lib/consult.js';
import { createUnifiedConsultLog, fetchUnifiedConsultLogs } from '../lib/actionApi.js';

export async function initConsult() {
  const form = document.getElementById('consult-form');
  form.elements.date.value = new Date().toISOString().slice(0, 10);
  form.addEventListener('submit', saveConsult);
  await render();
}

async function saveConsult(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  const result = assessConsult(`${data.area} ${data.text}`);
  const log = {
    date: data.date,
    area: data.area.trim(),
    text: data.text.trim(),
    result
  };
  let synced = false;
  let serverId = '';
  try {
    const record = await createUnifiedConsultLog(log);
    serverId = record?.id || '';
    synced = true;
  } catch (error) {
    console.warn('[fitness] unified consult sync failed', error);
  }
  await addConsultLog({
    ...log,
    serverId,
    source: synced ? 'unified-api' : 'fitness-page',
    syncStatus: synced ? 'synced' : 'pending'
  });
  renderResult(result);
  document.getElementById('consult-toast').textContent = synced ? '咨询记录已同步到统一动作接口，并保留离线缓存' : '统一动作接口暂不可用，咨询记录已保留在本地缓存';
  await render();
}

async function render() {
  const [localLogs, unified] = await Promise.all([
    listConsultLogs(),
    loadUnifiedConsults()
  ]);
  const logs = mergeOfflineCache(localLogs, unified.items, unified.offline)
    .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
  if (logs[0]) renderResult(logs[0].result);
  document.getElementById('consult-list').innerHTML = logs.length ? logs.slice(0, 8).map((log) => `
    <div class="log-item"><span><strong>${escapeHtml(log.area || '未标注')}</strong><br>${escapeHtml(log.date)} · ${escapeHtml(log.text)}</span><span>${escapeHtml(log.result.title)}</span></div>
  `).join('') : '<div class="empty">暂无咨询记录。</div>';
}

async function loadUnifiedConsults() {
  try {
    return { items: await fetchUnifiedConsultLogs(), offline: false };
  } catch {
    return { items: [], offline: true };
  }
}

function mergeOfflineCache(localLogs, unifiedLogs, includeLocalCache = false) {
  const rows = [];
  const seenServerIds = new Set();
  const visibleLocalLogs = includeLocalCache ? localLogs : localLogs.filter((log) => log.syncStatus === 'pending');
  for (const log of visibleLocalLogs) {
    rows.push(log);
    if (log.serverId) seenServerIds.add(log.serverId);
    if (log.id && String(log.id).startsWith('con_')) seenServerIds.add(log.id);
  }
  for (const log of unifiedLogs) {
    if (!seenServerIds.has(log.id)) rows.push(log);
  }
  return rows;
}

function renderResult(result) {
  document.getElementById('consult-result').innerHTML = `
    <div class="result-grid safety-result">
      <div><b>${escapeHtml(result.level.toUpperCase())}</b><span>风险级别</span></div>
      <div><b>${escapeHtml(result.title)}</b><span>${escapeHtml(result.reason)}</span></div>
    </div>
    <div class="advice-box">${escapeHtml(result.advice)}</div>
    <div class="mini-columns">
      <div><strong>处理建议</strong><ul>${(result.actions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('') || '<li>记录变化并控制训练量。</li>'}</ul></div>
      <div><strong>动作替代</strong><ul>${(result.substitutions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('') || '<li>暂无特定替代动作。</li>'}</ul></div>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
