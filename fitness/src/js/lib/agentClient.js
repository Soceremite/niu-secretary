
// fitness/src/js/lib/agentClient.js
const NUTRITION_AGENT_ENDPOINT = 'api/agent/nutrition-recognize';

export async function recognizeMealWithAgent({ file, description }) {
  if (!file) throw new Error('missing-photo');
  const body = new FormData();
  body.append('photo', file);
  body.append('description', description || '');
  const response = await fetch(NUTRITION_AGENT_ENDPOINT, { method: 'POST', body });
  const data = await safeJson(response);
  if (!response.ok) {
    const error = new Error(data?.message || `agent-http-${response.status}`);
    error.code = data?.error || `agent-http-${response.status}`;
    error.status = response.status;
    throw error;
  }
  return normalizeAgentMeal(data, data.source || 'agent');
}

export function estimateMealLocally({ file, description }) {
  const text = String(description || '').toLowerCase();
  let calories = 520;
  let proteinG = 28;
  let carbsG = 62;
  let fatG = 18;
  const items = [];

  if (/奶茶|甜品|炸|薯|burger|pizza/.test(text)) {
    calories += 260; carbsG += 34; fatG += 12;
    items.push({ name: '高热量配餐线索', portion: '按描述估算', calories: 260, proteinG: 0, carbsG: 34, fatG: 12 });
  }
  if (/鸡|牛|鱼|蛋|protein|肉/.test(text)) {
    calories += 120; proteinG += 22; fatG += 4;
    items.push({ name: '蛋白质食物线索', portion: '按描述估算', calories: 120, proteinG: 22, carbsG: 0, fatG: 4 });
  }
  if (/米饭|面|粉|粥|bread|rice/.test(text)) {
    calories += 170; carbsG += 42;
    items.push({ name: '主食线索', portion: '按描述估算', calories: 170, proteinG: 0, carbsG: 42, fatG: 0 });
  }
  if (/沙拉|蔬菜|青菜/.test(text)) {
    calories -= 90; carbsG -= 18; fatG -= 3;
    items.push({ name: '蔬菜线索', portion: '按描述估算', calories: 60, proteinG: 2, carbsG: 8, fatG: 1 });
  }
  if (file?.size > 2_000_000) calories += 80;

  return normalizeAgentMeal({
    food: description || file?.name || '图片餐食',
    items,
    calories,
    proteinG,
    carbsG,
    fatG,
    confidence: 0.42,
    warnings: ['未调用视觉模型，仅根据描述关键词和图片大小估算。']
  }, 'local-estimate');
}

function normalizeAgentMeal(data, source) {
  return {
    food: data.food || data.name || '图片餐食',
    items: Array.isArray(data.items) ? data.items.map((item) => ({
      name: item.name || item.food || '食物',
      portion: item.portion || item.amount || '',
      calories: clampNumber(item.calories, 0, 3000),
      proteinG: clampNumber(item.proteinG ?? item.protein, 0, 200),
      carbsG: clampNumber(item.carbsG ?? item.carbs, 0, 400),
      fatG: clampNumber(item.fatG ?? item.fat, 0, 200)
    })) : [],
    calories: clampNumber(data.calories, 0, 5000),
    proteinG: clampNumber(data.proteinG ?? data.protein, 0, 300),
    carbsG: clampNumber(data.carbsG ?? data.carbs, 0, 600),
    fatG: clampNumber(data.fatG ?? data.fat, 0, 300),
    confidence: Math.max(0, Math.min(1, Number(data.confidence || 0))),
    warnings: Array.isArray(data.warnings) ? data.warnings.map(String) : [],
    source
  };
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function clampNumber(value, min, max) {
  const n = Number(value || 0);
  return Math.max(min, Math.min(max, Math.round(n)));
}
