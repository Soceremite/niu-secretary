export type FieldType = 'text' | 'number' | 'date' | 'time' | 'select' | 'textarea'

export interface AdminField {
  key: string
  label: string
  type: FieldType
  required?: boolean
  defaultValue?: string | number
  options?: string[]
}

export interface AdminColumn {
  key: string
  label: string
  width?: number
}

export interface AdminResourceConfig {
  key: string
  title: string
  module: string
  resource: string
  description: string
  columns: AdminColumn[]
  fields?: AdminField[]
  createAction?: string
  updateAction?: string
  deleteAction?: string
  toggleAction?: string
  normalize?: (payload: any) => Record<string, any>[]
  mapInput?: (values: Record<string, any>, record?: Record<string, any>) => Record<string, any>
}

const today = () => new Date().toISOString().slice(0, 10)

export const adminResources: Record<string, AdminResourceConfig> = {
  'platform.ops': {
    key: 'platform.ops',
    title: '运营总览',
    module: '平台',
    resource: 'platform.ops',
    description: '模块健康、最近运行、事件和待审核项。',
    columns: [
      { key: 'title', label: '项目' },
      { key: 'detail', label: '说明' },
      { key: 'meta', label: '状态' }
    ],
    normalize: (payload) => [
      ...((payload.modules || []).map((item: any) => ({
        id: item.module,
        title: item.module,
        detail: `${item.capabilityCount || 0} 个能力`,
        meta: item.status || 'unknown'
      }))),
      ...((payload.pendingWorkItems || []).map((item: any) => ({
        id: item.id || item.action || item.title,
        title: item.title || item.action || '待处理',
        detail: item.module || '',
        meta: item.type || 'work'
      })))
    ]
  },
  'fitness.nutrition': {
    key: 'fitness.nutrition',
    title: '营养日志',
    module: '塑形馆',
    resource: 'fitness.nutrition',
    description: '管理餐食、热量和三大营养素。',
    createAction: 'fitness.nutrition.create',
    updateAction: 'fitness.nutrition.update',
    deleteAction: 'fitness.nutrition.delete',
    columns: [
      { key: 'food', label: '食物' },
      { key: 'date', label: '日期', width: 120 },
      { key: 'calories', label: '热量', width: 100 },
      { key: 'proteinG', label: '蛋白', width: 100 },
      { key: 'source', label: '来源', width: 130 }
    ],
    fields: [
      { key: 'food', label: '食物', type: 'text', required: true },
      { key: 'date', label: '日期', type: 'date', required: true, defaultValue: today() },
      { key: 'calories', label: '热量', type: 'number', defaultValue: 0 },
      { key: 'proteinG', label: '蛋白 g', type: 'number', defaultValue: 0 },
      { key: 'carbsG', label: '碳水 g', type: 'number', defaultValue: 0 },
      { key: 'fatG', label: '脂肪 g', type: 'number', defaultValue: 0 }
    ]
  },
  'fitness.workouts': {
    key: 'fitness.workouts',
    title: '训练日志',
    module: '塑形馆',
    resource: 'fitness.workouts',
    description: '管理训练名称、时长、强度和消耗。',
    createAction: 'fitness.workout.create',
    updateAction: 'fitness.workout.update',
    deleteAction: 'fitness.workout.delete',
    columns: [
      { key: 'name', label: '训练' },
      { key: 'date', label: '日期', width: 120 },
      { key: 'durationMin', label: '分钟', width: 100 },
      { key: 'intensity', label: '强度', width: 100 }
    ],
    fields: [
      { key: 'name', label: '训练', type: 'text', required: true },
      { key: 'date', label: '日期', type: 'date', required: true, defaultValue: today() },
      { key: 'durationMin', label: '分钟', type: 'number', defaultValue: 0 },
      { key: 'intensity', label: '强度', type: 'select', defaultValue: 'medium', options: ['low', 'medium', 'high'] },
      { key: 'calories', label: '消耗', type: 'number', defaultValue: 0 },
      { key: 'note', label: '备注', type: 'textarea' }
    ]
  },
  'fitness.metrics': {
    key: 'fitness.metrics',
    title: '体征数据',
    module: '塑形馆',
    resource: 'fitness.metrics',
    description: '管理体重、体脂、腰围和备注。',
    createAction: 'fitness.body_metric.create',
    updateAction: 'fitness.body_metric.update',
    deleteAction: 'fitness.body_metric.delete',
    columns: [
      { key: 'date', label: '日期', width: 120 },
      { key: 'weightKg', label: '体重 kg', width: 110 },
      { key: 'bodyFatPct', label: '体脂 %', width: 110 },
      { key: 'waistCm', label: '腰围 cm', width: 110 },
      { key: 'note', label: '备注' }
    ],
    fields: [
      { key: 'date', label: '日期', type: 'date', required: true, defaultValue: today() },
      { key: 'weightKg', label: '体重 kg', type: 'number' },
      { key: 'bodyFatPct', label: '体脂 %', type: 'number' },
      { key: 'waistCm', label: '腰围 cm', type: 'number' },
      { key: 'note', label: '备注', type: 'textarea' }
    ]
  },
  'fitness.assessments': {
    key: 'fitness.assessments',
    title: '身体评估',
    module: '塑形馆',
    resource: 'fitness.assessments',
    description: '查看身体评估、BMI、FMS 和训练限制。',
    columns: [
      { key: 'date', label: '日期', width: 120 },
      { key: 'goal', label: '目标', width: 120 },
      { key: 'bmi', label: 'BMI', width: 100 },
      { key: 'fmsTotal', label: 'FMS', width: 100 },
      { key: 'bmiCategory', label: '分类' }
    ]
  },
  'schedule.events': {
    key: 'schedule.events',
    title: '日程',
    module: '时务局',
    resource: 'schedule.events',
    description: '管理日程标题、日期、时间和备注。',
    createAction: 'schedule.event.create',
    updateAction: 'schedule.event.update',
    deleteAction: 'schedule.event.delete',
    columns: [
      { key: 'title', label: '标题' },
      { key: 'date', label: '日期', width: 120 },
      { key: 'time', label: '时间', width: 100 },
      { key: 'note', label: '备注' }
    ],
    fields: [
      { key: 'title', label: '标题', type: 'text', required: true },
      { key: 'date', label: '日期', type: 'date', required: true, defaultValue: today() },
      { key: 'time', label: '时间', type: 'time' },
      { key: 'note', label: '备注', type: 'textarea' }
    ]
  },
  'schedule.todos': {
    key: 'schedule.todos',
    title: '待办',
    module: '时务局',
    resource: 'schedule.todos',
    description: '管理待办事项和完成状态。',
    createAction: 'schedule.todo.create',
    updateAction: 'schedule.todo.update',
    deleteAction: 'schedule.todo.delete',
    toggleAction: 'schedule.todo.toggle',
    columns: [
      { key: 'title', label: '标题' },
      { key: 'date', label: '日期', width: 120 },
      { key: 'priority', label: '优先级', width: 110 },
      { key: 'done', label: '完成', width: 90 }
    ],
    fields: [
      { key: 'title', label: '标题', type: 'text', required: true },
      { key: 'date', label: '日期', type: 'date' },
      { key: 'priority', label: '优先级', type: 'select', defaultValue: 'normal', options: ['low', 'normal', 'high'] }
    ]
  },
  'leisure.items': {
    key: 'leisure.items',
    title: '闲趣条目',
    module: '闲趣集',
    resource: 'leisure.items',
    description: '管理影视、书籍、游戏、音乐等条目。',
    updateAction: 'leisure.item.update',
    deleteAction: 'leisure.item.delete',
    columns: [
      { key: 'title', label: '标题' },
      { key: 'category', label: '分类', width: 110 },
      { key: 'source', label: '来源', width: 130 },
      { key: 'updatedAt', label: '更新' }
    ],
    fields: [
      { key: 'category', label: '分类', type: 'select', required: true, options: ['movie', 'book', 'game', 'music', 'video'] },
      { key: 'title', label: '标题', type: 'text', required: true },
      { key: 'payloadText', label: '元数据 JSON', type: 'textarea' }
    ],
    mapInput: (values, record) => ({
      id: record?.id,
      category: values.category,
      title: values.title,
      payload: safeJson(values.payloadText, record?.payload || {}),
      source: 'admin-console'
    }),
    normalize: (payload) => (payload.items || []).map((item: any) => ({
      ...item,
      payloadText: JSON.stringify(item.payload || {}, null, 2)
    }))
  },
  'leisure.recommendations': {
    key: 'leisure.recommendations',
    title: '推荐历史',
    module: '闲趣集',
    resource: 'leisure.recommendations',
    description: '查看闲趣推荐历史和上下文。',
    columns: [
      { key: 'date', label: '日期', width: 120 },
      { key: 'source', label: '来源', width: 130 },
      { key: 'createdAt', label: '创建时间' },
      { key: 'count', label: '数量', width: 90 }
    ],
    normalize: (payload) => (payload.items || []).map((item: any) => ({
      ...item,
      count: item.recommendations?.length || 0
    }))
  },
  'news.recommend': {
    key: 'news.recommend',
    title: '新闻推荐',
    module: '新闻社',
    resource: 'news.recommend',
    description: '查看新闻推荐，也可将主题送入研知库队列。',
    createAction: 'news.topic.queue-research',
    columns: [
      { key: 'title', label: '标题' },
      { key: 'summary', label: '摘要' },
      { key: 'sectionLabel', label: '栏目', width: 130 }
    ],
    fields: [
      { key: 'title', label: '标题', type: 'text', required: true },
      { key: 'topic', label: '主题', type: 'text', required: true },
      { key: 'source', label: '来源', type: 'text', defaultValue: 'admin-console' }
    ]
  },
  'airesearch.papers': {
    key: 'airesearch.papers',
    title: '论文搜索',
    module: '研知库',
    resource: 'airesearch.papers',
    description: '搜索研知库论文和候选成果。',
    columns: [
      { key: 'title', label: '标题' },
      { key: 'venue', label: '来源', width: 150 },
      { key: 'year', label: '年份', width: 90 },
      { key: 'paperKey', label: 'Key', width: 150 }
    ]
  },
  'airesearch.overview': {
    key: 'airesearch.overview',
    title: '候选队列',
    module: '研知库',
    resource: 'airesearch.overview',
    description: '查看研知库概览，并新增候选研究主题。',
    createAction: 'airesearch.queue.add',
    columns: [
      { key: 'title', label: '标题' },
      { key: 'status', label: '状态', width: 120 },
      { key: 'profile', label: '画像', width: 140 },
      { key: 'paperKey', label: 'Key', width: 150 }
    ],
    fields: [
      { key: 'title', label: '标题', type: 'text', required: true },
      { key: 'note', label: '备注', type: 'textarea' },
      { key: 'source', label: '来源', type: 'text', defaultValue: 'admin-console' }
    ],
    normalize: (payload) => {
      const overview = payload.overview || {}
      return [...(overview.candidates || []), ...(overview.papers || [])]
    }
  }
}

export const adminMenu = [
  { title: '总览', path: '/admin/', items: [{ title: '运营总览', path: '/admin/' }] },
  {
    title: '塑形馆',
    path: '/admin/fitness/nutrition',
    items: [
      { title: '营养日志', path: '/admin/fitness/nutrition' },
      { title: '训练日志', path: '/admin/fitness/training' },
      { title: '体征数据', path: '/admin/fitness/metrics' },
      { title: '身体评估', path: '/admin/fitness/assessment' }
    ]
  },
  {
    title: '时务局',
    path: '/admin/schedule/events',
    items: [
      { title: '日程', path: '/admin/schedule/events' },
      { title: '待办', path: '/admin/schedule/todos' }
    ]
  },
  {
    title: '闲趣集',
    path: '/admin/leisure/items',
    items: [
      { title: '条目', path: '/admin/leisure/items' },
      { title: '推荐历史', path: '/admin/leisure/recommendations' }
    ]
  },
  {
    title: '新闻社',
    path: '/admin/news/recommendations',
    items: [
      { title: '新闻推荐', path: '/admin/news/recommendations' },
      { title: '主题队列', path: '/admin/news/topics' }
    ]
  },
  {
    title: '研知库',
    path: '/admin/airesearch/',
    items: [
      { title: '总览', path: '/admin/airesearch/' },
      { title: '论文管理', path: '/admin/airesearch/papers' },
      { title: '博客生成', path: '/admin/airesearch/blogs' },
      { title: '搜索入库', path: '/admin/airesearch/discovery' },
      { title: '搜索配置', path: '/admin/airesearch/profiles' },
      { title: '任务中心', path: '/admin/airesearch/tasks' },
      { title: '重建部署', path: '/admin/airesearch/publish' }
    ]
  }
]

function safeJson(value: string, fallback: unknown) {
  try {
    return JSON.parse(value || '{}')
  } catch {
    return fallback
  }
}
