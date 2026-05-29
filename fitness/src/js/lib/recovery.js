// fitness/src/js/lib/recovery.js
export function scoreRecovery({ sleepHours, sleepQuality, stress, soreness, lastRpe }) {
  let score = 50;
  score += Math.min(18, Number(sleepHours || 0) * 2.2);
  score += Number(sleepQuality || 0) * 3;
  score -= Number(stress || 0) * 4;
  score -= Number(soreness || 0) * 4;
  score -= Math.max(0, Number(lastRpe || 0) - 7) * 5;
  return Math.max(0, Math.min(100, Math.round(score)));
}

export function recoveryStatus(score) {
  if (score >= 75) return { label: '绿色', tone: 'good', advice: '按计划训练，可以正常推进强度。' };
  if (score >= 55) return { label: '黄色', tone: 'warn', advice: '建议降低训练量 10-30%，保留动作质量。' };
  return { label: '红色', tone: 'bad', advice: '建议主动恢复或 deload，暂停高风险大重量动作。' };
}
