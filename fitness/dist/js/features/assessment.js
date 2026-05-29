
// fitness/src/js/features/assessment.js
import { addAssessmentLog, listAssessmentLogs, putProfile } from '../lib/db.js';
import { calculateBmi, calculateBmr, calculateTdee, classifyAsianBmi } from '../lib/calculator.js';

export async function initAssessment() {
  const form = document.getElementById('assessment-form');
  form.elements.date.value = new Date().toISOString().slice(0, 10);
  form.addEventListener('submit', saveAssessment);
  await renderHistory();
}

async function saveAssessment(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  const postures = new FormData(form).getAll('posture');
  const fms = {
    deepSquat: number(data.deepSquat),
    hurdleStep: number(data.hurdleStep),
    inlineLunge: number(data.inlineLunge),
    shoulderMobility: number(data.shoulderMobility),
    activeSlr: number(data.activeSlr),
    trunkStability: number(data.trunkStability),
    rotaryStability: number(data.rotaryStability)
  };
  const profile = {
    heightCm: number(data.heightCm),
    weightKg: number(data.weightKg),
    age: number(data.age),
    sex: data.sex || 'male',
    activity: number(data.activity),
    goal: data.goal
  };
  const bmi = calculateBmi(profile.weightKg, profile.heightCm);
  const girths = {
    waistCm: optionalNumber(data.waistCm),
    hipCm: optionalNumber(data.hipCm),
    chestCm: optionalNumber(data.chestCm),
    armCm: optionalNumber(data.armCm),
    thighCm: optionalNumber(data.thighCm)
  };
  const log = {
    date: data.date,
    goal: data.goal,
    heightCm: profile.heightCm,
    weightKg: profile.weightKg,
    waistCm: girths.waistCm,
    girths,
    bmi,
    bmiCategory: classifyAsianBmi(bmi),
    bmr: calculateBmr(profile),
    tdee: calculateTdee(profile, profile.weightKg),
    fms,
    fmsTotal: Object.values(fms).reduce((sum, value) => sum + value, 0),
    postures,
    trainingLimits: makeTrainingLimits(fms, postures),
    advice: makeAdvice(bmi, fms, postures)
  };
  await addAssessmentLog(log);
  await putProfile(profile);
  renderResult(log);
  document.getElementById('assessment-toast').textContent = '评估已保存到本地';
  await renderHistory();
}

async function renderHistory() {
  const logs = (await listAssessmentLogs()).sort((a, b) => b.date.localeCompare(a.date));
  const latest = logs[0];
  if (latest) renderResult(latest);
  const list = document.getElementById('assessment-list');
  if (!logs.length) {
    list.innerHTML = '<div class="empty">暂无评估记录。</div>';
    return;
  }
  list.innerHTML = logs.slice(0, 6).map((log) => `
    <div class="log-item">
      <span><strong>${escapeHtml(log.date)}</strong><br>${escapeHtml(log.goal)} · BMI ${escapeHtml(log.bmi)} · FMS ${escapeHtml(log.fmsTotal)}/21</span>
      <span>${escapeHtml(log.bmiCategory)}</span>
    </div>
  `).join('');
}

function renderResult(log) {
  const risk = log.fmsTotal < 12 ? '动作风险偏高' : log.fmsTotal < 16 ? '需要动作修正' : '可正常推进';
  const limits = log.trainingLimits?.length ? log.trainingLimits.join('；') : '暂无特殊限制';
  document.getElementById('assessment-result').innerHTML = `
    <div class="result-grid">
      <div><b>${escapeHtml(log.bmi)}</b><span>BMI · ${escapeHtml(log.bmiCategory)}</span></div>
      <div><b>${escapeHtml(log.bmr)}</b><span>BMR kcal</span></div>
      <div><b>${escapeHtml(log.tdee)}</b><span>TDEE kcal</span></div>
      <div><b>${escapeHtml(log.fmsTotal)}/21</b><span>FMS · ${risk}</span></div>
    </div>
    <div class="advice-box">${escapeHtml(log.advice)}<br>训练限制：${escapeHtml(limits)}</div>
  `;
}

function makeTrainingLimits(fms, postures) {
  const limits = [];
  if (fms.deepSquat <= 1 || fms.inlineLunge <= 1) limits.push('下肢大重量先降载，优先分腿蹲、箱式深蹲和动作控制');
  if (fms.shoulderMobility <= 1 || postures.includes('圆肩')) limits.push('减少过顶推举，增加胸椎伸展和水平拉');
  if (fms.activeSlr <= 1 || postures.includes('久坐髋紧')) limits.push('硬拉类动作改为罗马尼亚硬拉或臀桥');
  if (fms.trunkStability <= 1 || fms.rotaryStability <= 1) limits.push('核心抗伸展和抗旋转先补齐，避免疲劳下冲大重量');
  if (postures.includes('膝内扣')) limits.push('下肢训练前加入臀中肌激活，避免膝内扣疼痛动作');
  return limits;
}

function makeAdvice(bmi, fms, postures) {
  const notes = [];
  if (bmi >= 23) notes.push('优先控制热量缺口，力量训练用于保肌。');
  if (Object.values(fms).some((value) => value <= 1)) notes.push('存在低分动作，训练计划会加入限制和替代动作。');
  if (postures.includes('骨盆前倾')) notes.push('加入髋屈肌拉伸、臀桥和死虫。');
  if (postures.includes('膝内扣')) notes.push('下肢训练前加入臀中肌激活。');
  return notes.join(' ') || '当前基线稳定，可以从全身训练和中等热量控制开始。';
}

function number(value) {
  return Number(value || 0);
}

function optionalNumber(value) {
  return value === '' ? null : Number(value);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
