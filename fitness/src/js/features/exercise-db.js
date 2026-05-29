
// fitness/src/js/features/exercise-db.js
export const exercises = [
  { id: 'squat', name: '深蹲', pattern: '下肢推', defaultWeight: 60, regression: '箱式深蹲' },
  { id: 'split-squat', name: '保加利亚分腿蹲', pattern: '下肢推', defaultWeight: 20, regression: '原地弓步' },
  { id: 'romanian-deadlift', name: '罗马尼亚硬拉', pattern: '髋铰链', defaultWeight: 55, regression: '哑铃臀桥' },
  { id: 'hip-thrust', name: '臀推', pattern: '髋铰链', defaultWeight: 60, regression: '臀桥' },
  { id: 'bench-press', name: '卧推', pattern: '上肢推', defaultWeight: 50, regression: '俯卧撑' },
  { id: 'incline-db-press', name: '上斜哑铃推', pattern: '上肢推', defaultWeight: 18, regression: '器械胸推' },
  { id: 'overhead-press', name: '推举', pattern: '上肢推', defaultWeight: 25, regression: '地雷管推' },
  { id: 'row', name: '俯身划船', pattern: '上肢拉', defaultWeight: 45, regression: '坐姿划船' },
  { id: 'lat-pulldown', name: '高位下拉', pattern: '上肢拉', defaultWeight: 45, regression: '弹力带下拉' },
  { id: 'face-pull', name: '面拉', pattern: '上肢拉', defaultWeight: 18, regression: '弹力带面拉' },
  { id: 'plank', name: '平板支撑', pattern: '核心', defaultWeight: 0, regression: '死虫' },
  { id: 'pallof-press', name: 'Pallof 抗旋', pattern: '核心', defaultWeight: 12, regression: '侧桥' }
];

export function findExercise(id) {
  return exercises.find((exercise) => exercise.id === id) || exercises[0];
}
