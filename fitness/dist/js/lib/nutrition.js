// fitness/src/js/lib/nutrition.js
export function macroCalories({ proteinG = 0, carbsG = 0, fatG = 0 }) {
  return Math.round(Number(proteinG) * 4 + Number(carbsG) * 4 + Number(fatG) * 9);
}

export function summarizeNutrition(logs) {
  const today = new Date().toISOString().slice(0, 10);
  const todayLogs = logs.filter((log) => log.date === today);
  return todayLogs.reduce((sum, log) => ({
    calories: sum.calories + Number(log.calories || 0),
    proteinG: sum.proteinG + Number(log.proteinG || 0),
    carbsG: sum.carbsG + Number(log.carbsG || 0),
    fatG: sum.fatG + Number(log.fatG || 0)
  }), { calories: 0, proteinG: 0, carbsG: 0, fatG: 0 });
}
