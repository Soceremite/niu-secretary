
// fitness/src/js/features/training.js
import { addTrainingLog, clearTrainingLogs, listAssessmentLogs, listRecoveryLogs, listTrainingLogs } from '../lib/db.js';
import { calculateSetVolume, estimateOneRepMax, summarizeTraining } from '../lib/training.js';
import { exercises, findExercise } from './exercise-db.js';

export async function initTraining() {
  const form = document.getElementById('training-form');
  form.elements.date.value = new Date().toISOString().slice(0, 10);
  fillExercises();
  form.addEventListener('submit', saveTraining);
  document.getElementById('seed-training').addEventListener('click', seedTraining);
  document.getElementById('clear-training').addEventListener('click', async () => {
    await clearTrainingLogs();
    await render();
  });
  await render();
}

function fillExercises() {
  const select = document.getElementById('exercise-select');
  select.innerHTML = exercises.map((item) => `<option value="${item.id}">${item.name} · ${item.pattern}</option>`).join('');
  select.addEventListener('change', () => {
    document.querySelector('#training-form [name="weightKg"]').value = findExercise(select.value).defaultWeight;
  });
  document.querySelector('#training-form [name="weightKg"]').value = exercises[0].defaultWeight;
}

async function saveTraining(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  const exercise = findExercise(data.exerciseId);
  const log = {
    date: data.date,
    exerciseId: data.exerciseId,
    exerciseName: exercise.name,
    pattern: exercise.pattern,
    weightKg: Number(data.weightKg),
    reps: Number(data.reps),
    sets: Number(data.sets),
    rpe: Number(data.rpe || 0),
    note: data.note.trim()
  };
  log.volume = calculateSetVolume(log);
  log.oneRepMax = estimateOneRepMax(log.weightKg, log.reps);
  await addTrainingLog(log);
  document.getElementById('training-toast').textContent = `已保存：${log.volume.toLocaleString()} kg 容量`;
  await render();
}

async function render() {
  const [logs, assessments, recoveryLogs] = await Promise.all([listTrainingLogs(), listAssessmentLogs(), listRecoveryLogs()]);
  const summary = summarizeTraining(logs);
  const latestAssessment = assessments.sort((a, b) => b.date.localeCompare(a.date))[0];
  const latestRecovery = recoveryLogs.sort((a, b) => b.date.localeCompare(a.date))[0];
  document.getElementById('training-volume').textContent = Math.round(summary.totalVolume).toLocaleString();
  document.getElementById('training-sets').textContent = summary.totalSets;
  document.getElementById('training-count').textContent = logs.length;
  renderSuggestion(logs, latestAssessment, latestRecovery);
  renderPlan(latestAssessment, latestRecovery);
  renderPatterns(summary.byPattern, summary.totalVolume);
  renderList(summary.latest, logs);
}

function renderSuggestion(logs, assessment, recovery) {
  const box = document.getElementById('training-suggestion');
  const restrictions = assessment?.trainingLimits || [];
  const redRecovery = recovery?.status?.label === '红色';
  const yellowRecovery = recovery?.status?.label === '黄色';
  const today = new Date().toISOString().slice(0, 10);
  const trainedToday = logs.some((log) => log.date === today);
  const lines = [];
  if (redRecovery) lines.push('恢复红色：今天建议主动恢复或休息，暂停高风险大重量。');
  else if (yellowRecovery) lines.push('恢复黄色：训练量降低 10-30%，RPE 控制在 7 左右。');
  else lines.push(trainedToday ? '今天已有训练记录，后续以拉伸和步行为主。' : '今天可以做全身力量训练，优先复合动作。');
  if (restrictions.length) lines.push(`评估限制：${restrictions.join('；')}`);
  box.innerHTML = `<div class="advice-box">${lines.map(escapeHtml).join('<br>')}</div>`;
}

function renderPlan(assessment, recovery) {
  const box = document.getElementById('training-plan');
  const deload = recovery?.status?.label === '红色';
  const goal = assessment?.goal || 'recomposition';
  const goalText = { fat_loss: '减脂保肌', muscle_gain: '增肌推进', posture: '体态改善', recomposition: '身体重组' }[goal] || '身体重组';
  const items = deload
    ? ['20-30 分钟低强度有氧', '髋胸椎活动度', '核心呼吸和拉伸']
    : ['下肢推或髋铰链 3-4 组', '上肢推拉各 3-4 组', '核心抗伸展/抗旋 2-3 组'];
  box.innerHTML = `
    <div class="mini-columns">
      <div><strong>今日主题</strong><p>${escapeHtml(goalText)} · ${deload ? '降载' : '正常训练'}</p></div>
      <div><strong>建议内容</strong><ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>
    </div>
  `;
}

function renderPatterns(byPattern, total) {
  const list = document.getElementById('pattern-list');
  const entries = Object.entries(byPattern).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    list.innerHTML = '<div class="empty">暂无容量分布。</div>';
    return;
  }
  list.innerHTML = entries.map(([pattern, volume]) => {
    const pct = total ? Math.round((volume / total) * 100) : 0;
    return `<div class="target-row"><span>${escapeHtml(pattern)}</span><div class="bar"><span style="width:${pct}%"></span></div><b>${pct}%</b></div>`;
  }).join('');
}

function renderList(logs, allLogs) {
  const list = document.getElementById('training-list');
  if (!logs.length) {
    list.innerHTML = '<div class="empty">暂无训练记录。</div>';
    return;
  }
  list.innerHTML = logs.map((log) => {
    const previous = [...allLogs]
      .filter((item) => item.exerciseId === log.exerciseId && item.date < log.date)
      .sort((a, b) => b.date.localeCompare(a.date))[0];
    const progress = previous && log.volume > previous.volume ? '容量上升' : previous ? '维持或回撤' : '首次记录';
    return `
      <div class="log-item">
        <span><strong>${escapeHtml(log.exerciseName)}</strong><br>${escapeHtml(log.date)} · ${log.sets}x${log.reps} · RPE ${log.rpe}<br>${escapeHtml(progress)}</span>
        <span>${Math.round(log.volume).toLocaleString()}kg<br>1RM ${log.oneRepMax}</span>
      </div>
    `;
  }).join('');
}

async function seedTraining() {
  await clearTrainingLogs();
  const today = new Date();
  const sample = [
    ['squat', 70, 6, 4, 8],
    ['bench-press', 55, 8, 4, 8],
    ['row', 50, 10, 4, 7.5],
    ['romanian-deadlift', 65, 8, 3, 8],
    ['lat-pulldown', 48, 10, 3, 7]
  ];
  for (let index = 0; index < sample.length; index++) {
    const [id, weightKg, reps, sets, rpe] = sample[index];
    const day = new Date(today);
    day.setDate(today.getDate() - index);
    const exercise = findExercise(id);
    const log = {
      date: day.toISOString().slice(0, 10),
      exerciseId: id,
      exerciseName: exercise.name,
      pattern: exercise.pattern,
      weightKg,
      reps,
      sets,
      rpe,
      note: ''
    };
    log.volume = calculateSetVolume(log);
    log.oneRepMax = estimateOneRepMax(weightKg, reps);
    await addTrainingLog(log);
  }
  await render();
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
