
// fitness/src/js/features/dashboard.js
import { addWeightLog, clearWeightLogs, countRealPending, exportAllData, getProfile, listNutritionLogs, listRecoveryLogs, listWeightLogs, putProfile } from '../lib/db.js';
import { calculateBmi, calculateTdee, classifyAsianBmi, progressPercent, summarizeWeight } from '../lib/calculator.js';
import { summarizeNutrition } from '../lib/nutrition.js';
import { createUnifiedBodyMetric, fetchUnifiedBodyMetrics, fetchUnifiedFitnessProfile, fetchUnifiedNutritionLogs, fetchUnifiedRecoveryLogs, updateUnifiedFitnessProfile } from '../lib/actionApi.js';

const API_BASE = '/niu-secretary/api';

const defaultProfile = {
  heightCm: 175,
  age: 32,
  sex: 'male',
  activity: 1.45,
  calorieTarget: 2100,
  proteinTarget: 150,
  carbsTarget: 240,
  fatTarget: 70
};

let profile = { ...defaultProfile };

export async function initDashboard() {
  profile = await loadProfileForDashboard();
  bindForms();
  fillProfileForm();
  loadFitnessProfileAndRecommend();
  await render();
}

async function loadProfileForDashboard() {
  try {
    const unifiedProfile = normalizeProfile(await fetchUnifiedFitnessProfile());
    await putProfile({ ...unifiedProfile, syncStatus: 'synced', source: 'unified-api' });
    return unifiedProfile;
  } catch (error) {
    console.warn('[fitness] unified profile read failed, using offline cache', error);
    return normalizeProfile(await getProfile());
  }
}

async function loadFitnessProfileAndRecommend() {
  const fieldsContainer = document.getElementById('fitness-profile-fields');
  const listEl = document.getElementById('fitness-recommend-list');

  // 启动两个请求，互不阻塞
  const profilePromise = loadFitnessProfile(fieldsContainer);
  const recommendPromise = loadFitnessRecommend(listEl);
  await Promise.allSettled([profilePromise, recommendPromise]);
}

async function loadFitnessProfile(container) {
  try {
    const data = await getJson(`${API_BASE}/profile?module=fitness`);
    const p = data.profile;
    const fields = [
      ['目标', goalLabel(p?.goal)],
      ['饮食风格', p?.dietStyle || '--'],
      ['饮食限制', Array.isArray(p?.restrictions) && p.restrictions.length ? p.restrictions.join('、') : '无'],
      ['训练水平', trainingLevelLabel(p?.trainingLevel)],
      ['目标热量', p?.targetCalories ? `${p.targetCalories} kcal` : '--'],
      ['蛋白目标', p?.proteinTarget ? `${p.proteinTarget} g` : '--'],
      ['备注', p?.notes || '--']
    ];
    container.innerHTML = fields.map(([label, value]) =>
      `<div class="profile-row" data-profile-${label}"><span class="profile-label">${label}</span><span class="profile-value">${escapeHtml(String(value))}</span></div>`
    ).join('');
  } catch {
    container.innerHTML = '<p class="profile-placeholder">暂无画像，去首页和牛秘书 AI 聊聊就能生成</p>';
  }
}

async function loadFitnessRecommend(container) {
  const today = new Date().toISOString().slice(0, 10);
  try {
    const data = await getJson(`${API_BASE}/platform/today?date=${encodeURIComponent(today)}&limit=1`);
    const recs = data.context?.fitness?.workoutRecommendations || [];
    if (!recs.length) {
      container.innerHTML = '<li class="recommend-placeholder">今日暂无推荐</li>';
      return;
    }
    container.innerHTML = recs.map(r => `<li>${escapeHtml(r)}</li>`).join('');
  } catch {
    container.innerHTML = '<li class="recommend-placeholder">暂无推荐，去首页和牛秘书 AI 聊聊就能生成</li>';
  }
}

function goalLabel(g) {
  const map = { fat_loss: '减脂', muscle_gain: '增肌', recomp: '身体重组', maintain: '维持' };
  return map[g] || g || '--';
}

function trainingLevelLabel(l) {
  const map = { beginner: '新手', intermediate: '进阶', advanced: '高阶' };
  return map[l] || l || '--';
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `读取接口失败：${response.status}`);
  }
  return data;
}

function bindForms() {
  const today = new Date().toISOString().slice(0, 10);
  document.querySelector('#weight-form [name="date"]').value = today;

  document.getElementById('weight-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const log = {
      date: data.date,
      weightKg: Number(data.weightKg),
      bodyFatPercent: optionalNumber(data.bodyFatPercent),
      waistCm: optionalNumber(data.waistCm),
      note: data.note.trim()
    };
    let synced = false;
    let serverId = '';
    try {
      const record = await createUnifiedBodyMetric({
        ...log,
        bodyFatPct: log.bodyFatPercent
      });
      synced = true;
      serverId = record?.id || '';
    } catch (error) {
      console.warn('[fitness] unified body metric sync failed', error);
    }
    await addWeightLog({
      ...log,
      serverId,
      source: synced ? 'unified-api' : 'fitness-page',
      syncStatus: synced ? 'synced' : 'pending'
    });
    event.currentTarget.reset();
    document.querySelector('#weight-form [name="date"]').value = today;
    showToast(synced ? '体征已同步到统一动作接口，并保留本地缓存' : '体征已保存到本地，统一动作接口暂不可用');
    await render();
  });

  document.getElementById('profile-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    profile = {
      ...profile,
      heightCm: Number(data.heightCm),
      age: Number(data.age),
      sex: data.sex,
      activity: Number(data.activity),
      calorieTarget: Number(data.calorieTarget),
      proteinTarget: Number(data.proteinTarget),
      carbsTarget: Number(data.carbsTarget),
      fatTarget: Number(data.fatTarget)
    };
    try {
      const savedProfile = normalizeProfile(await updateUnifiedFitnessProfile(profile));
      profile = { ...profile, ...savedProfile };
      await putProfile({ ...profile, syncStatus: 'synced', source: 'unified-api' });
      showToast('画像已保存，并同步到统一动作接口');
    } catch (error) {
      console.warn('[fitness] unified profile sync failed', error);
      await putProfile({ ...profile, syncStatus: 'pending', source: 'offline-cache' });
      showToast('统一动作接口暂不可用，画像仅保留在离线缓存');
    }
    await render();
  });

  document.getElementById('clear-logs').addEventListener('click', async () => {
    await clearWeightLogs();
    showToast('体征离线缓存已清空，服务器记录不受影响');
    await render();
  });

  document.getElementById('export-json').addEventListener('click', exportJson);
}

async function render() {
  const [localWeightLogs, unifiedWeight, localNutritionLogs, unifiedNutrition, pending, localRecoveryLogs, unifiedRecovery] = await Promise.all([
    listWeightLogs(),
    loadUnified(fetchUnifiedBodyMetrics),
    listNutritionLogs(),
    loadUnified(fetchUnifiedNutritionLogs),
    countRealPending(),
    listRecoveryLogs(),
    loadUnified(fetchUnifiedRecoveryLogs)
  ]);
  const logs = mergeWeightLogs(localWeightLogs, unifiedWeight.items, { includeLocalCache: unifiedWeight.offline });
  const nutritionLogs = mergeNutritionLogs(localNutritionLogs, unifiedNutrition.items, { includeLocalCache: unifiedNutrition.offline });
  const recoveryLogs = mergeRecoveryLogs(localRecoveryLogs, unifiedRecovery.items, { includeLocalCache: unifiedRecovery.offline });
  const summary = summarizeWeight(logs);
  const latestWeight = summary.latest?.weightKg || profile.weightKg || 80;
  const bmi = calculateBmi(latestWeight, profile.heightCm);
  const tdee = calculateTdee(profile, latestWeight);
  const todayNutrition = summarizeNutrition(nutritionLogs);

  setText('stat-weight', summary.latest ? summary.latest.weightKg.toFixed(1) : '--');
  setText('stat-delta', summary.delta == null ? '--' : `${summary.delta > 0 ? '+' : ''}${summary.delta.toFixed(1)}`);
  setText('stat-bmi', bmi ? `${bmi} ${classifyAsianBmi(bmi)}` : '--');
  setText('hero-weight', summary.latest ? summary.latest.weightKg.toFixed(1) : '--');
  setText('hero-sync', String(pending));
  
  // 恢复信号：从真实的 recovery logs 读取
  const latestRecovery = recoveryLogs.sort((a, b) => b.date.localeCompare(a.date))[0];
  if (latestRecovery) {
    setText('hero-recovery', `${latestRecovery.score}`);
  } else {
    setText('hero-recovery', '--');
  }

  const calorieTarget = profile.calorieTarget || tdee;
  const caloriePct = progressPercent(todayNutrition.calories, calorieTarget);
  setText('hero-calories', `${Math.min(100, caloriePct)}%`);
  setText('calorie-percent', `${Math.min(100, caloriePct)}%`);
  document.getElementById('calorie-ring').style.setProperty('--progress', `${Math.min(100, caloriePct) * 3.6}deg`);
  updateTargets(todayNutrition, calorieTarget);
  renderLogList(summary.sorted);
  drawWeightChart(summary.sorted);
}

async function loadUnified(loader) {
  try {
    return { items: await loader(), offline: false };
  } catch {
    return { items: [], offline: true };
  }
}

function mergeWeightLogs(localLogs, unifiedLogs, options = {}) {
  const rows = [];
  const seenServerIds = new Set();
  const visibleLocalLogs = options.includeLocalCache ? localLogs : localLogs.filter((log) => log.syncStatus === 'pending');
  for (const log of visibleLocalLogs) {
    rows.push(log);
    if (log.serverId) seenServerIds.add(log.serverId);
    if (log.id && String(log.id).startsWith('bm_')) seenServerIds.add(log.id);
  }
  for (const log of unifiedLogs) {
    if (!seenServerIds.has(log.id)) rows.push(log);
  }
  return rows;
}

function mergeNutritionLogs(localLogs, unifiedLogs, options = {}) {
  const rows = [];
  const seenServerIds = new Set();
  const visibleLocalLogs = options.includeLocalCache ? localLogs : localLogs.filter((log) => log.syncStatus === 'pending');
  for (const log of visibleLocalLogs) {
    rows.push(log);
    if (log.serverId) seenServerIds.add(log.serverId);
    if (log.id && String(log.id).startsWith('nut_')) seenServerIds.add(log.id);
  }
  for (const log of unifiedLogs) {
    if (!seenServerIds.has(log.id)) rows.push(log);
  }
  return rows;
}

function mergeRecoveryLogs(localLogs, unifiedLogs, options = {}) {
  const rows = [];
  const seenServerIds = new Set();
  const visibleLocalLogs = options.includeLocalCache ? localLogs : localLogs.filter((log) => log.syncStatus === 'pending');
  for (const log of visibleLocalLogs) {
    rows.push(log);
    if (log.serverId) seenServerIds.add(log.serverId);
    if (log.id && String(log.id).startsWith('rec_')) seenServerIds.add(log.id);
  }
  for (const log of unifiedLogs) {
    if (!seenServerIds.has(log.id)) rows.push(log);
  }
  return rows;
}

function updateTargets(todayNutrition, calorieTarget) {
  const rows = [
    ['calories', todayNutrition.calories, calorieTarget, 'kcal'],
    ['protein', todayNutrition.proteinG, profile.proteinTarget, 'g'],
    ['carbs', todayNutrition.carbsG, profile.carbsTarget, 'g'],
    ['fat', todayNutrition.fatG, profile.fatTarget, 'g']
  ];
  for (const [key, value, target, unit] of rows) {
    const pct = Math.min(100, progressPercent(value, target));
    const barEl = document.getElementById(`bar-${key}`);
    const textEl = document.getElementById(`text-${key}`);
    
    barEl.style.width = `${pct}%`;
    setText(`text-${key}`, `${Math.round(value)}/${target}${unit}`);
    
    // 超标警告：当实际值超过目标值时添加视觉提示
    const isOverLimit = value > target && target > 0;
    barEl.parentElement.classList.toggle('over-limit', isOverLimit);
    textEl.classList.toggle('over-limit', isOverLimit);
  }
}

function normalizeProfile(value = {}) {
  const raw = value && typeof value === 'object' ? value : {};
  const targetCalories = Number(raw.targetCalories || raw.calorieTarget || defaultProfile.calorieTarget);
  return {
    ...defaultProfile,
    ...raw,
    calorieTarget: targetCalories,
    proteinTarget: Number(raw.proteinTarget || defaultProfile.proteinTarget),
    carbsTarget: Number(raw.carbsTarget || defaultProfile.carbsTarget),
    fatTarget: Number(raw.fatTarget || defaultProfile.fatTarget),
    heightCm: Number(raw.heightCm || defaultProfile.heightCm),
    age: Number(raw.age || defaultProfile.age),
    activity: Number(raw.activity || defaultProfile.activity),
    sex: raw.sex || defaultProfile.sex
  };
}

function renderLogList(logs) {
  const list = document.getElementById('log-list');
  const recent = [...logs].reverse().slice(0, 8);
  if (!recent.length) {
    list.innerHTML = '<div class="empty">暂无记录。手动录入后会同步到统一 API，并保留本地缓存。</div>';
    return;
  }
  list.innerHTML = recent.map((log) => `
    <div class="log-item">
      <span><strong>${escapeHtml(log.weightKg.toFixed(1))} kg</strong><br>${escapeHtml(log.date)} ${escapeHtml(log.note || '')}</span>
      <span>${log.bodyFatPercent ? `${escapeHtml(log.bodyFatPercent)}%` : ''}</span>
    </div>
  `).join('');
}

function drawWeightChart(logs) {
  const canvas = document.getElementById('weight-chart');
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = 'rgba(255,255,255,0.04)';
  roundRect(ctx, 20, 20, width - 40, height - 48, 18);
  ctx.fill();

  if (logs.length < 2) {
    ctx.fillStyle = 'rgba(255,244,247,0.58)';
    ctx.font = '18px sans-serif';
    ctx.fillText('至少 2 条记录后显示趋势', 44, 180);
    return;
  }

  const values = logs.map((log) => log.weightKg);
  const min = Math.min(...values) - 0.6;
  const max = Math.max(...values) + 0.6;
  const plot = { x: 48, y: 40, w: width - 92, h: height - 100 };

  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i++) {
    const y = plot.y + (plot.h / 3) * i;
    ctx.beginPath();
    ctx.moveTo(plot.x, y);
    ctx.lineTo(plot.x + plot.w, y);
    ctx.stroke();
  }

  const points = logs.map((log, index) => ({
    x: plot.x + (plot.w / Math.max(1, logs.length - 1)) * index,
    y: plot.y + plot.h - ((log.weightKg - min) / (max - min)) * plot.h
  }));

  ctx.beginPath();
  points.forEach((point, index) => index ? ctx.lineTo(point.x, point.y) : ctx.moveTo(point.x, point.y));
  ctx.strokeStyle = '#74d99f';
  ctx.lineWidth = 4;
  ctx.lineJoin = 'round';
  ctx.stroke();

  for (const point of points) {
    ctx.beginPath();
    ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#f5f7f1';
    ctx.fill();
  }
}

async function exportJson() {
  const snapshot = await exportAllData();
  const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `niu-fitness-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
  showToast('离线缓存 JSON 已导出');
}

function fillProfileForm() {
  const form = document.getElementById('profile-form');
  for (const [key, value] of Object.entries(profile)) {
    if (form.elements[key]) form.elements[key].value = value;
  }
}

function showToast(message) {
  setText('form-toast', message);
  window.setTimeout(() => setText('form-toast', ''), 2600);
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function optionalNumber(value) {
  return value === '' ? null : Number(value);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + width, y, x + width, y + height, radius);
  ctx.arcTo(x + width, y + height, x, y + height, radius);
  ctx.arcTo(x, y + height, x, y, radius);
  ctx.arcTo(x, y, x + width, y, radius);
  ctx.closePath();
}
