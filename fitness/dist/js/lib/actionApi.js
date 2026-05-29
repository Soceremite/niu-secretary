// fitness/src/js/lib/actionApi.js
const ACTION_API = '/niu-secretary/api/actions/execute';

export async function fetchUnifiedNutritionLogs(date = todayString()) {
  const result = await executeAction('fitness.nutrition.today_summary', { date });
  return (result.summary?.items || []).map((item) => ({
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
