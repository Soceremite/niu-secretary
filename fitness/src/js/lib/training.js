// fitness/src/js/lib/training.js
export function calculateSetVolume({ weightKg, reps, sets }) {
  return Number(weightKg || 0) * Number(reps || 0) * Number(sets || 0);
}

export function estimateOneRepMax(weightKg, reps) {
  if (!weightKg || !reps) return 0;
  return Math.round(Number(weightKg) * (1 + Number(reps) / 30));
}

export function summarizeTraining(logs) {
  const totalVolume = logs.reduce((sum, log) => sum + Number(log.volume || 0), 0);
  const totalSets = logs.reduce((sum, log) => sum + Number(log.sets || 0), 0);
  const byPattern = logs.reduce((map, log) => {
    map[log.pattern] = (map[log.pattern] || 0) + Number(log.volume || 0);
    return map;
  }, {});
  const latest = [...logs].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 8);
  return { totalVolume, totalSets, byPattern, latest };
}
