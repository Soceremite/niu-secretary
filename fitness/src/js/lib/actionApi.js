// fitness/src/js/lib/actionApi.js
const ACTION_API = '/niu-secretary/api/actions/execute';

// 默认拉取最近 180 天的营养记录，后端为唯一数据源
export async function fetchUnifiedNutritionLogs(options = {}) {
  const to = options.to || todayString();
  const from = options.from || daysAgoString(180);
  const result = await executeAction('fitness.nutrition.list', { from, to, limit: options.limit || 1000 });
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

async function executeAction(action, input) {
  const response = await fetch(ACTION_API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action,
      input,
      context: { client: 'fitness-page' }
    })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.message || `统一动作接口失败：${response.status}`);
  }
  return data;
}

function todayString() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoString(days) {
  return new Date(Date.now() - days * 86400000).toISOString().slice(0, 10);
}
