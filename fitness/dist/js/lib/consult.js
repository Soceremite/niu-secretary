
// fitness/src/js/lib/consult.js
const RED_FLAGS = ['胸闷', '呼吸困难', '晕厥', '急性剧痛', '明显肿胀', '麻木', '放射痛', '术后', '血压失控', '血糖失控'];

export function assessConsult(text) {
  const matched = RED_FLAGS.filter((flag) => text.includes(flag));
  if (matched.length) {
    return {
      level: 'red',
      title: '停止训练并就医',
      reason: `触发红线：${matched.join('、')}`,
      advice: '该情况超出健身建议范围。请停止训练，优先联系医生或线下专业人员。',
      actions: ['停止相关训练', '尽快联系医生或线下专业人员', '不要用拉伸或止痛药硬压症状'],
      substitutions: []
    };
  }
  if (text.includes('膝')) {
    return {
      level: 'yellow',
      title: '膝部不适：先降级动作',
      reason: '常见关节不适但未触发红线。',
      advice: '降低负重和活动幅度，避免疼痛角度，记录诱发动作；若持续加重或肿胀再就医。',
      actions: ['深蹲改箱式深蹲或腿举', '加入臀中肌激活', 'RPE 控制在 6-7'],
      substitutions: ['箱式深蹲', '台阶上步', '臀桥']
    };
  }
  if (text.includes('腰')) {
    return {
      level: 'yellow',
      title: '腰部不适：减少轴向压力',
      reason: '腰背不适需要先排查动作和疲劳。',
      advice: '暂停疼痛动作，减少硬拉深蹲大重量，优先核心抗伸展和髋主导训练。',
      actions: ['硬拉改罗马尼亚硬拉或臀桥', '增加死虫和侧桥', '避免疲劳下冲重量'],
      substitutions: ['臀推', '死虫', '侧桥']
    };
  }
  if (text.includes('肩')) {
    return {
      level: 'yellow',
      title: '肩部不适：避开过顶刺激',
      reason: '肩部问题常和活动度、肩胛控制有关。',
      advice: '减少过顶推举和疼痛角度卧推，增加划船、面拉和胸椎活动。',
      actions: ['推举改地雷管推或上斜哑铃推', '增加面拉和划船', '疼痛超过 3/10 停止该动作'],
      substitutions: ['地雷管推', '面拉', '坐姿划船']
    };
  }
  if (text.includes('圆肩') || text.includes('久坐') || text.includes('骨盆')) {
    return {
      level: 'blue',
      title: '体态改善建议',
      reason: '更像长期姿势和活动度问题。',
      advice: '加入胸椎伸展、髋屈肌拉伸、臀腹强化，每工作 45-60 分钟起身活动。',
      actions: ['每天 8-12 分钟活动度', '每周至少 2 次上背训练', '减少久坐连续时长'],
      substitutions: ['胸椎伸展', '臀桥', '死虫']
    };
  }
  return {
    level: 'green',
    title: '可在健身范围内调整',
    reason: '未识别明显红线。',
    advice: '先从动作技术、训练量、恢复和疼痛变化四个角度排查。',
    actions: ['记录疼痛评分和诱发动作', '下一次训练降低 10-20% 负荷', '观察 48-72 小时变化'],
    substitutions: []
  };
}
