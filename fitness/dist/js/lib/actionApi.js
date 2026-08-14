// fitness/src/js/lib/actionApi.js
const API_BASE = '/niu-secretary/api';
const ACTION_API = '/niu-secretary/api/actions/execute';

// 默认拉取最近 180 天的营养记录，后端为唯一数据源
export async function fetchUnifiedNutritionLogs(options = {}) {
  const to = options.to || todayString();
  const from = options.from || daysAgoString(180);
  const result = await getJson(`${API_BASE}/fitness/nutrition?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&limit=${encodeURIComponent(options.limit || 1000)}`);
  return (result.items || []).map((item) => ({
    id: item.id,
    date: item.date,
    mealType: item.mealType || 'AI记录',
    food: item.food,
    calories: Number(item.calories || 0),
    proteinG: Number(item.proteinG || 0),
    carbsG: Number(item.carbsG || 0),
    fatG: Number(item.fatG || 0),
    source: item.source || 'unified-api',
    createdAt: item.createdAt,
    syncStatus: 'synced'
  }));
}

export async function deleteUnifiedNutritionLog(id) {
  await executeAction('fitness.nutrition.delete', { id });
  return true;
}

export async function createUnifiedNutritionLog(meal) {
  const result = await executeAction('fitness.nutrition.create', {
    food: meal.food,
    date: meal.date || todayString(),
    calories: Number(meal.calories || 0),
    proteinG: Number(meal.proteinG || 0),
    carbsG: Number(meal.carbsG || 0),
    fatG: Number(meal.fatG || 0),
    source: meal.source || 'fitness-page'
  });
  return result.record;
}

export async function createUnifiedWorkoutLog(log) {
  const result = await executeAction('fitness.workout.create', {
    name: log.exerciseName || log.name || '训练',
    date: log.date || todayString(),
    durationMin: Number(log.durationMin || log.duration || 0),
    intensity: intensityFromRpe(log.rpe),
    calories: Number(log.calories || 0),
    note: [
      log.pattern ? `模式：${log.pattern}` : '',
      log.sets && log.reps ? `${log.sets}x${log.reps}` : '',
      log.weightKg ? `${log.weightKg}kg` : '',
      log.note || ''
    ].filter(Boolean).join(' · '),
    source: log.source || 'fitness-page'
  });
  return result.record;
}

export async function fetchUnifiedWorkoutLogs(options = {}) {
  const to = options.to || todayString();
  const from = options.from || daysAgoString(180);
  const result = await getJson(`${API_BASE}/fitness/workouts?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&limit=${encodeURIComponent(options.limit || 1000)}`);
  return (result.items || []).map((item) => {
    const parsed = parseWorkoutNote(item.note || '');
    const weightKg = optionalNumber(parsed.weightKg);
    const reps = optionalNumber(parsed.reps);
    const sets = optionalNumber(parsed.sets);
    const volume = weightKg && reps && sets ? weightKg * reps * sets : 0;
    return {
      id: item.id,
      serverId: item.id,
      date: item.date,
      exerciseId: slugExerciseName(item.name || '训练'),
      exerciseName: item.name || '训练',
      pattern: parsed.pattern || intensityLabel(item.intensity),
      weightKg: weightKg || 0,
      reps: reps || 0,
      sets: sets || 0,
      rpe: intensityToRpe(item.intensity),
      note: parsed.note || item.note || '',
      volume,
      oneRepMax: weightKg && reps ? Math.round(weightKg * (1 + reps / 30)) : 0,
      source: item.source || 'unified-api',
      createdAt: item.createdAt,
      syncStatus: 'synced'
    };
  });
}

export async function createUnifiedBodyMetric(log) {
  const result = await executeAction('fitness.body_metric.create', {
    date: log.date || todayString(),
    weightKg: optionalNumber(log.weightKg),
    bodyFatPct: optionalNumber(log.bodyFatPct),
    waistCm: optionalNumber(log.waistCm),
    note: log.note || '',
    source: log.source || 'fitness-page'
  });
  return result.record;
}

export async function fetchUnifiedBodyMetrics(options = {}) {
  const to = options.to || todayString();
  const from = options.from || daysAgoString(180);
  const result = await getJson(`${API_BASE}/fitness/body-metrics?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&limit=${encodeURIComponent(options.limit || 1000)}`);
  return (result.items || []).map((item) => ({
    id: item.id,
    serverId: item.id,
    date: item.date,
    weightKg: Number(item.weightKg || 0),
    bodyFatPercent: optionalNumber(item.bodyFatPct),
    waistCm: optionalNumber(item.waistCm),
    note: item.note || '',
    source: item.source || 'unified-api',
    createdAt: item.createdAt,
    syncStatus: 'synced'
  }));
}

export async function createUnifiedRecoveryLog(log) {
  const result = await executeAction('fitness.recovery.create', {
    date: log.date || todayString(),
    sleepHours: Number(log.sleepHours || 0),
    sleepQuality: Number(log.sleepQuality || 0),
    stress: Number(log.stress || 0),
    soreness: Number(log.soreness || 0),
    lastRpe: Number(log.lastRpe || 0),
    score: Number(log.score || 0),
    statusLabel: log.status?.label || log.statusLabel || '',
    statusAdvice: log.status?.advice || log.statusAdvice || '',
    source: log.source || 'fitness-page'
  });
  return result.record;
}

export async function fetchUnifiedRecoveryLogs(options = {}) {
  const to = options.to || todayString();
  const from = options.from || daysAgoString(180);
  const result = await getJson(`${API_BASE}/fitness/recovery?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&limit=${encodeURIComponent(options.limit || 1000)}`);
  return (result.items || []).map((item) => ({
    id: item.id,
    serverId: item.id,
    date: item.date,
    sleepHours: Number(item.sleepHours || 0),
    sleepQuality: Number(item.sleepQuality || 0),
    stress: Number(item.stress || 0),
    soreness: Number(item.soreness || 0),
    lastRpe: Number(item.lastRpe || 0),
    score: Number(item.score || 0),
    status: {
      label: item.statusLabel || '未知',
      advice: item.statusAdvice || ''
    },
    source: item.source || 'unified-api',
    createdAt: item.createdAt,
    syncStatus: 'synced'
  }));
}

export async function createUnifiedAssessmentLog(log) {
  const result = await executeAction('fitness.assessment.create', {
    date: log.date || todayString(),
    goal: log.goal || '',
    weightKg: optionalNumber(log.weightKg),
    waistCm: optionalNumber(log.waistCm),
    bmi: optionalNumber(log.bmi),
    fmsTotal: Number(log.fmsTotal || 0),
    payload: log,
    source: log.source || 'fitness-page'
  });
  return result.record;
}

export async function fetchUnifiedAssessmentLogs(options = {}) {
  const to = options.to || todayString();
  const from = options.from || daysAgoString(180);
  const result = await getJson(`${API_BASE}/fitness/assessments?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&limit=${encodeURIComponent(options.limit || 1000)}`);
  return (result.items || []).map((item) => ({
    ...item,
    serverId: item.id,
    source: item.source || 'unified-api',
    syncStatus: 'synced'
  }));
}

export async function createUnifiedConsultLog(log) {
  const result = await executeAction('fitness.consult.create', {
    date: log.date || todayString(),
    area: log.area || '',
    text: log.text || '',
    level: log.result?.level || log.level || '',
    title: log.result?.title || log.title || '',
    payload: log,
    source: log.source || 'fitness-page'
  });
  return result.record;
}

export async function fetchUnifiedConsultLogs(options = {}) {
  const to = options.to || todayString();
  const from = options.from || daysAgoString(180);
  const result = await getJson(`${API_BASE}/fitness/consults?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}&limit=${encodeURIComponent(options.limit || 1000)}`);
  return (result.items || []).map((item) => ({
    ...item,
    serverId: item.id,
    result: item.result || {
      level: item.level || '',
      title: item.title || '',
      reason: '',
      advice: '',
      actions: [],
      substitutions: []
    },
    source: item.source || 'unified-api',
    syncStatus: 'synced'
  }));
}

export async function updateUnifiedFitnessProfile(profile) {
  const patch = {
    ...profile,
    targetCalories: Number(profile.targetCalories || profile.calorieTarget || 0),
    proteinTarget: Number(profile.proteinTarget || 0)
  };
  const result = await executeAction('profile.update', {
    module: 'fitness',
    patch,
    summary: 'fitness page profile update',
    source: 'fitness-page'
  });
  return result.profile;
}

export async function fetchUnifiedFitnessProfile() {
  const result = await getJson(`${API_BASE}/profile?module=fitness`);
  return result.profile || {};
}

async function executeAction(action, input) {
  const response = await fetch(ACTION_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action,
      input,
      context: { client: 'fitness-page', confirmed: true }
    })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `统一动作接口失败：${response.status}`);
  }
  return data;
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `统一读取接口失败：${response.status}`);
  }
  return data;
}

function todayString() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoString(days) {
  return new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
}

function optionalNumber(value) {
  if (value === '' || value === null || value === undefined) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseWorkoutNote(note) {
  const parts = String(note || '').split(' · ').map((part) => part.trim()).filter(Boolean);
  const parsed = { pattern: '', sets: 0, reps: 0, weightKg: 0, note: '' };
  const rest = [];
  for (const part of parts) {
    if (part.startsWith('模式：')) {
      parsed.pattern = part.slice(3).trim();
    } else if (/^\d+x\d+$/i.test(part)) {
      const [sets, reps] = part.toLowerCase().split('x').map(Number);
      parsed.sets = sets;
      parsed.reps = reps;
    } else if (/^\d+(\.\d+)?kg$/i.test(part)) {
      parsed.weightKg = Number(part.replace(/kg$/i, ''));
    } else {
      rest.push(part);
    }
  }
  parsed.note = rest.join(' · ');
  return parsed;
}

function intensityFromRpe(rpe) {
  const value = Number(rpe || 0);
  if (value >= 8) return 'high';
  if (value > 0 && value <= 5) return 'low';
  return 'medium';
}

function intensityToRpe(intensity) {
  if (intensity === 'high') return 8;
  if (intensity === 'low') return 5;
  return 7;
}

function intensityLabel(intensity) {
  if (intensity === 'high') return '高强度';
  if (intensity === 'low') return '低强度';
  return '中强度';
}

function slugExerciseName(name) {
  return String(name || 'training')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9\u4e00-\u9fa5-]/g, '') || 'training';
}
