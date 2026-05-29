// fitness/src/js/lib/calculator.js
export function calculateBmi(weightKg, heightCm) {
  const heightM = Number(heightCm) / 100;
  if (!weightKg || !heightM) return null;
  return round(Number(weightKg) / (heightM * heightM), 1);
}

export function classifyAsianBmi(bmi) {
  if (bmi == null) return '--';
  if (bmi < 18.5) return '偏瘦';
  if (bmi < 23) return '正常';
  if (bmi < 25) return '超重';
  if (bmi < 30) return '肥胖 I';
  return '肥胖 II';
}

export function calculateBmr({ sex = 'male', weightKg, heightCm, age }) {
  const base = 10 * Number(weightKg) + 6.25 * Number(heightCm) - 5 * Number(age);
  return Math.round(base + (String(sex).toLowerCase() === 'female' ? -161 : 5));
}

export function calculateTdee(profile, weightKg) {
  const bmr = calculateBmr({ ...profile, weightKg });
  return Math.round(bmr * Number(profile.activity || 1.45));
}

export function progressPercent(value, target) {
  if (!target || target <= 0) return 0;
  return Math.max(0, Math.min(160, Math.round((Number(value) / Number(target)) * 100)));
}

export function summarizeWeight(logs) {
  const sorted = [...logs].sort((a, b) => a.date.localeCompare(b.date));
  const latest = sorted.at(-1);
  const recent = sorted.slice(-7);
  const firstRecent = recent.at(0);
  const delta = latest && firstRecent ? round(latest.weightKg - firstRecent.weightKg, 1) : null;
  return { latest, delta, sorted };
}

export function round(value, digits = 0) {
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
}
