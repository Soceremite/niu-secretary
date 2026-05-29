
// fitness/src/js/features/nutrition.js
import { addNutritionLog, clearNutritionLogs, getProfile, listAssessmentLogs, listNutritionLogs, listTrainingLogs } from '../lib/db.js';
import { summarizeNutrition } from '../lib/nutrition.js';
import { calculateTdee, progressPercent } from '../lib/calculator.js';
import { estimateMealLocally, recognizeMealWithAgent } from '../lib/agentClient.js';

let selectedPhoto = null;
let pendingMeal = null;
let currentTargets = { calories: 2100, proteinG: 150, carbsG: 240, fatG: 70 };

export async function initNutrition() {
  const form = document.getElementById('nutrition-form');
  form.elements.date.value = new Date().toISOString().slice(0, 10);
  form.addEventListener('submit', saveNutrition);
  document.getElementById('photo-form').addEventListener('submit', recognizeMeal);
  document.getElementById('meal-photo').addEventListener('change', previewPhoto);
  document.getElementById('confirm-meal').addEventListener('click', confirmMeal);
  document.getElementById('local-estimate').addEventListener('click', estimateCurrentMeal);
  document.getElementById('manual-from-photo').addEventListener('click', fillManualFromPhoto);
  document.getElementById('clear-nutrition').addEventListener('click', async () => {
    await clearNutritionLogs();
    await render();
  });
  setRecognitionState('idle', '上传照片后可以调用 Agent 识别，结果会先等待确认。');
  await render();
}

async function saveNutrition(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  await addMeal({
    date: data.date,
    mealType: data.mealType,
    food: data.food.trim(),
    calories: Number(data.calories || 0),
    proteinG: Number(data.proteinG || 0),
    carbsG: Number(data.carbsG || 0),
    fatG: Number(data.fatG || 0),
    source: 'manual'
  });
  event.currentTarget.reset();
  event.currentTarget.elements.date.value = new Date().toISOString().slice(0, 10);
  document.getElementById('nutrition-toast').textContent = '手动记录已保存。';
}

async function recognizeMeal(event) {
  event.preventDefault();
  const description = new FormData(event.currentTarget).get('description');
  if (!selectedPhoto) {
    setRecognitionState('failed', '先上传餐食图片。');
    return;
  }
  pendingMeal = null;
  setRecognitionState('loading', '识别中，正在把图片交给 Agent...');
  try {
    pendingMeal = await recognizeMealWithAgent({ file: selectedPhoto, description });
    renderPendingMeal(pendingMeal, 'success', 'Agent 已返回结果，请确认或编辑后保存。');
  } catch (error) {
    setRecognitionState('failed', error.message || 'Agent 接口暂未响应，可改用本地估算或手动补录。');
  }
}

async function estimateCurrentMeal() {
  const description = new FormData(document.getElementById('photo-form')).get('description');
  if (!selectedPhoto && !description) {
    setRecognitionState('failed', '需要图片或描述才能估算。');
    return;
  }
  pendingMeal = estimateMealLocally({ file: selectedPhoto, description });
  renderPendingMeal(pendingMeal, 'estimate', '已生成本地估算。该结果未经过视觉模型，请确认后保存。');
}

async function confirmMeal() {
  if (!pendingMeal) return;
  const form = document.getElementById('recognized-meal-form');
  const data = Object.fromEntries(new FormData(form));
  await addMeal({
    date: new Date().toISOString().slice(0, 10),
    mealType: inferMealType(),
    imageName: selectedPhoto?.name || '',
    food: data.food.trim(),
    calories: Number(data.calories || 0),
    proteinG: Number(data.proteinG || 0),
    carbsG: Number(data.carbsG || 0),
    fatG: Number(data.fatG || 0),
    items: pendingMeal.items || [],
    confidence: pendingMeal.confidence,
    warnings: pendingMeal.warnings || [],
    source: pendingMeal.source
  });
  pendingMeal = null;
  document.getElementById('recognized-meal').hidden = true;
  setRecognitionState('idle', '已保存到饮食日志。');
}

function fillManualFromPhoto() {
  const description = new FormData(document.getElementById('photo-form')).get('description');
  const form = document.getElementById('nutrition-form');
  form.elements.food.value = description || selectedPhoto?.name || '';
  setRecognitionState('idle', '已把描述带到手动补录表单。');
}

async function addMeal(meal) {
  await addNutritionLog(meal);
  await render();
}

function previewPhoto(event) {
  selectedPhoto = event.target.files?.[0] || null;
  pendingMeal = null;
  document.getElementById('recognized-meal').hidden = true;
  const preview = document.getElementById('photo-preview');
  if (!selectedPhoto) {
    preview.innerHTML = '<span>照片预览区</span>';
    setRecognitionState('idle', '上传照片后可以调用 Agent 识别，结果会先等待确认。');
    return;
  }
  const url = URL.createObjectURL(selectedPhoto);
  preview.innerHTML = `<img src="${url}" alt="餐食照片预览"><span>${escapeHtml(selectedPhoto.name)}</span>`;
  setRecognitionState('idle', '照片已就绪，可以识别。');
}

async function render() {
  const logs = (await listNutritionLogs()).sort((a, b) => b.date.localeCompare(a.date));
  const today = summarizeNutrition(logs);
  currentTargets = await calculateNutritionTargets();
  const energy = await calculateEnergy(today.calories);
  renderDeficit(energy);
  renderMacros(today);
  renderList(logs);
}

async function calculateNutritionTargets() {
  const [profile, assessments] = await Promise.all([getProfile(), listAssessmentLogs()]);
  const latestAssessment = assessments.sort((a, b) => b.date.localeCompare(a.date))[0];
  const weightKg = latestAssessment?.weightKg || profile?.weightKg || 80;
  const tdee = latestAssessment?.tdee || (profile?.heightCm ? calculateTdee(profile, weightKg) : 2300);
  const goal = latestAssessment?.goal || profile?.goal || 'recomposition';
  const calories = Math.round(tdee + ({ fat_loss: -450, muscle_gain: 250, posture: -150, recomposition: -250 }[goal] ?? -250));
  return {
    calories: Math.max(1200, calories),
    proteinG: Math.round(weightKg * (goal === 'muscle_gain' ? 2.0 : 1.8)),
    carbsG: Math.round(Math.max(90, (calories * 0.42) / 4)),
    fatG: Math.round(Math.max(45, (calories * 0.25) / 9))
  };
}

async function calculateEnergy(intake) {
  const [profile, assessments, trainingLogs] = await Promise.all([getProfile(), listAssessmentLogs(), listTrainingLogs()]);
  const latestAssessment = assessments.sort((a, b) => b.date.localeCompare(a.date))[0];
  const baseline = latestAssessment?.tdee || (profile?.weightKg ? calculateTdee(profile, profile.weightKg) : 2300);
  const today = new Date().toISOString().slice(0, 10);
  const todayTraining = trainingLogs.filter((log) => log.date === today);
  const volume = todayTraining.reduce((sum, log) => sum + Number(log.volume || 0), 0);
  const exercise = Math.min(650, Math.round(volume / 35 + todayTraining.length * 18));
  return { baseline, exercise, intake, deficit: baseline + exercise - intake };
}

function renderDeficit({ baseline, exercise, intake, deficit }) {
  const label = deficit >= 0 ? '缺口' : '盈余';
  const abs = Math.abs(Math.round(deficit));
  document.getElementById('deficit-number').textContent = `${abs} kcal ${label}`;
  document.getElementById('deficit-subtitle').textContent = deficit >= 0
    ? '今天还在减脂轨道上。'
    : '今天热量已经超出目标，明天需要更克制。';
  document.getElementById('energy-breakdown').innerHTML = [
    ['日常代谢', baseline, 'kcal'],
    ['运动消耗', exercise, 'kcal'],
    ['今日摄入', intake, 'kcal']
  ].map(([label, value, unit]) => `<div class="target-row"><span>${label}</span><div class="bar"><span style="width:${Math.min(100, value / 30)}%"></span></div><b>${Math.round(value)}${unit}</b></div>`).join('');
}

function renderMacros(today) {
  const pct = Math.min(100, progressPercent(today.calories, currentTargets.calories));
  document.getElementById('nutrition-percent').textContent = `${pct}%`;
  document.getElementById('nutrition-ring').style.setProperty('--progress', `${pct * 3.6}deg`);
  document.getElementById('nutrition-targets').innerHTML = rows().map(([label, key, unit]) => {
    const percent = Math.min(100, progressPercent(today[key], currentTargets[key]));
    return `<div class="target-row"><span>${label}</span><div class="bar"><span style="width:${percent}%"></span></div><b>${today[key]}/${currentTargets[key]}${unit}</b></div>`;
  }).join('');
}

function renderPendingMeal(meal, state, message) {
  setRecognitionState(state, message);
  const panel = document.getElementById('recognized-meal');
  panel.hidden = false;
  panel.querySelector('[name="food"]').value = meal.food;
  panel.querySelector('[name="calories"]').value = meal.calories;
  panel.querySelector('[name="proteinG"]').value = meal.proteinG;
  panel.querySelector('[name="carbsG"]').value = meal.carbsG;
  panel.querySelector('[name="fatG"]').value = meal.fatG;
  const sourceLabel = meal.source === 'local-estimate' ? '本地估算' : 'Agent 识别';
  document.getElementById('recognized-meta').textContent = `${sourceLabel} · 置信度 ${Math.round(meal.confidence * 100)}%`;
  document.getElementById('recognized-items').innerHTML = meal.items?.length
    ? meal.items.map((item) => `<li>${escapeHtml(item.name)} ${escapeHtml(item.portion || '')} · ${item.calories}kcal</li>`).join('')
    : '<li>未拆分具体食物。</li>';
  document.getElementById('recognized-warnings').innerHTML = meal.warnings?.length
    ? meal.warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join('')
    : '<li>无额外提醒。</li>';
}

function setRecognitionState(state, message) {
  const box = document.getElementById('recognition-state');
  box.dataset.state = state;
  box.textContent = message;
}

function renderList(logs) {
  document.getElementById('nutrition-list').innerHTML = logs.length ? logs.slice(0, 8).map((log) => `
    <div class="log-item"><span><strong>${escapeHtml(log.mealType)}</strong><br>${escapeHtml(log.date)} · ${escapeHtml(log.food)}${log.imageName ? `<br>图片：${escapeHtml(log.imageName)}` : ''}</span><span>${log.calories}kcal<br>${formatSource(log.source)}</span></div>
  `).join('') : '<div class="empty">暂无饮食记录。先拍一餐或手动补录。</div>';
}

function rows() {
  return [['热量', 'calories', ''], ['蛋白', 'proteinG', 'g'], ['碳水', 'carbsG', 'g'], ['脂肪', 'fatG', 'g']];
}

function inferMealType() {
  const hour = new Date().getHours();
  if (hour < 10) return '早餐';
  if (hour < 15) return '午餐';
  if (hour < 21) return '晚餐';
  return '加餐';
}

function formatSource(source) {
  if (source === 'agent') return 'Agent';
  if (source === 'local-estimate') return '本地估算';
  return '手动';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
