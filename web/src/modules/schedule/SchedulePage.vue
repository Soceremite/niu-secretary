<template>
  <main class="schedule-workbench">
    <header class="schedule-topbar">
      <router-link class="schedule-brand" to="/">
        <span class="schedule-logo">牛</span>
        <span>
          <strong>牛秘书时务局</strong>
          <small>Schedule Bureau</small>
        </span>
      </router-link>
      <nav class="schedule-nav">
        <el-button class="schedule-action-button is-refresh" :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
        <el-button class="schedule-action-button is-home" type="primary" :icon="HomeFilled" @click="$router.push('/')">返回主页</el-button>
      </nav>
    </header>

    <el-alert v-if="error" :title="error" type="error" show-icon class="section-gap" />

    <section class="schedule-hero section-gap" aria-label="时务局今日概览">
      <div class="schedule-hero-copy">
        <p class="schedule-kicker">Schedule Bureau</p>
        <h1>时务局</h1>
        <p class="schedule-lead">排班、提醒、代办和目标，一夹搞定。在线数据由时务局统一保管，本地只记住当前页签。</p>
      </div>
      <div class="schedule-date-card" aria-label="今日日期">
        <span>{{ todayMonth }}</span>
        <strong>{{ todayDay }}</strong>
        <span>{{ todayWeekday }}</span>
      </div>
    </section>

    <section class="schedule-briefing-grid section-gap" aria-label="今日画像和建议">
      <article class="schedule-paper-panel profile-panel">
        <div class="schedule-panel-title">
          <h2>我的画像 · 今日建议</h2>
          <span>{{ selectedDate }}</span>
        </div>
        <div class="schedule-profile-grid">
          <div>
            <h3>今日概况</h3>
            <dl class="schedule-profile-list">
              <div>
                <dt>日程</dt>
                <dd>{{ todayEvents.length }} 项</dd>
              </div>
              <div>
                <dt>待办</dt>
                <dd>{{ openTodayTodos.length }} 项未完成</dd>
              </div>
              <div>
                <dt>冲突</dt>
                <dd>{{ conflicts.length }} 个</dd>
              </div>
              <div>
                <dt>完成率</dt>
                <dd>{{ completionRate }}%</dd>
              </div>
            </dl>
          </div>
          <div>
            <h3>秘书建议</h3>
            <ul class="schedule-recommend-list">
              <li v-for="tip in recommendationList" :key="tip">{{ tip }}</li>
            </ul>
          </div>
        </div>
      </article>

      <div class="schedule-metrics">
        <div>
          <strong>{{ conflicts.length }}</strong>
          <span>冲突</span>
        </div>
        <div>
          <strong>{{ completionRate }}%</strong>
          <span>完成率</span>
        </div>
        <div>
          <strong>{{ planBlocks.length }}</strong>
          <span>计划块</span>
        </div>
      </div>
    </section>

    <section class="schedule-cache-note section-gap" aria-label="数据同步状态">
      <div>
        <p>数据同步状态</p>
        <strong>当前内容来自时务局后端；断网时保留界面偏好，不在本地生成业务记录。</strong>
      </div>
      <span>在线 · 自动同步</span>
    </section>

    <el-tabs v-model="activeTab" class="section-gap">
      <el-tab-pane label="今日" name="today">
        <div class="schedule-grid schedule-desktop-grid">
          <el-card shadow="never" class="schedule-panel schedule-timeline-panel">
            <template #header>
              <div class="panel-title">
                <span>今日时间线</span>
                <el-tag type="info">{{ todayEvents.length }} 项</el-tag>
              </div>
            </template>
            <div class="schedule-list-frame timeline-frame" data-testid="schedule-event-frame">
              <el-timeline v-if="todayEvents.length">
                <el-timeline-item
                  v-for="event in orderedTodayEvents"
                  :key="event.id"
                  :timestamp="event.time || '全天'"
                  placement="top"
                >
                  <div class="timeline-item">
                    <div class="schedule-row-heading">
                      <strong>{{ event.title }}</strong>
                      <span class="schedule-date-chip">{{ event.date }}</span>
                    </div>
                    <p>{{ event.note || event.source || '未添加备注' }}</p>
                    <div class="row-actions schedule-row-tools">
                      <el-button size="small" text :icon="EditPen" @click="openEventEditor(event)">编辑</el-button>
                      <el-popconfirm title="确认删除这条日程？" @confirm="removeEvent(event.id)">
                        <template #reference>
                          <el-button size="small" text type="danger" :icon="Delete">删除</el-button>
                        </template>
                      </el-popconfirm>
                    </div>
                  </div>
                </el-timeline-item>
              </el-timeline>
              <el-empty v-else description="今天没有日程，去“录入”安排第一项" />
              <div v-if="eventPlaceholderCount" class="schedule-placeholder-rows" aria-hidden="true">
                <span v-for="index in eventPlaceholderCount" :key="index"></span>
              </div>
            </div>
          </el-card>

          <el-card shadow="never" class="schedule-panel">
            <template #header>
              <div class="panel-title">
                <span>待办推进</span>
                <el-tag>{{ openTodayTodos.length }} 未完成</el-tag>
              </div>
            </template>
            <div class="schedule-list-frame todo-frame" data-testid="schedule-todo-frame">
              <div v-if="todayTodos.length" class="todo-list">
                <div v-for="todo in todayTodos" :key="todo.id" class="todo-row" :class="{ done: todo.done }">
                  <el-checkbox :model-value="todo.done" @change="toggleTodo(todo)">
                    <span>{{ todo.title }}</span>
                  </el-checkbox>
                  <div class="row-actions">
                    <span class="schedule-priority-tag" :data-priority="todo.priority">{{ priorityLabel(todo.priority) }}</span>
                    <el-button size="small" text :icon="EditPen" @click="openTodoEditor(todo)">编辑</el-button>
                    <el-popconfirm title="确认删除这条待办？" @confirm="removeTodo(todo.id)">
                      <template #reference>
                        <el-button size="small" text type="danger" :icon="Delete">删除</el-button>
                      </template>
                    </el-popconfirm>
                  </div>
                </div>
              </div>
              <el-empty v-else description="今天没有待办，保持轻量也很好" />
              <div v-if="todoPlaceholderCount" class="schedule-placeholder-rows" aria-hidden="true">
                <span v-for="index in todoPlaceholderCount" :key="index"></span>
              </div>
            </div>
          </el-card>

          <aside class="schedule-side-stack">
            <el-card shadow="never" class="schedule-panel">
              <template #header>秘书提醒</template>
              <div class="priority-list">
                <article v-for="item in priorityCards" :key="item.index" class="priority-card">
                  <span>{{ item.index }}</span>
                  <div>
                    <strong>{{ item.title }}</strong>
                    <small>{{ item.description }}</small>
                  </div>
                </article>
              </div>
            </el-card>

            <el-card shadow="never" class="schedule-panel">
              <template #header>事务抽屉</template>
              <nav class="drawer-grid" aria-label="时务局模块">
                <button v-for="drawer in drawerItems" :key="drawer" type="button">{{ drawer }}</button>
              </nav>
            </el-card>
          </aside>
        </div>
      </el-tab-pane>

      <el-tab-pane label="录入" name="input">
        <div class="schedule-grid">
          <el-card shadow="never" class="schedule-panel">
            <template #header>新增日程</template>
            <el-form label-position="top" :model="eventForm" @submit.prevent>
              <el-form-item label="标题" required>
                <el-input v-model="eventForm.title" placeholder="例如：产品评审" />
              </el-form-item>
              <el-row :gutter="14">
                <el-col :xs="24" :md="12">
                  <el-form-item label="日期" required>
                    <el-date-picker v-model="eventForm.date" type="date" value-format="YYYY-MM-DD" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="时间">
                    <el-time-picker v-model="eventForm.time" value-format="HH:mm" format="HH:mm" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="备注">
                <el-input v-model="eventForm.note" type="textarea" :rows="4" />
              </el-form-item>
              <el-button class="schedule-submit-button" type="primary" :loading="savingEvent" @click="submitEvent">保存日程</el-button>
            </el-form>
          </el-card>

          <el-card shadow="never" class="schedule-panel">
            <template #header>新增待办</template>
            <el-form label-position="top" :model="todoForm" @submit.prevent>
              <el-form-item label="标题" required>
                <el-input v-model="todoForm.title" placeholder="例如：整理周报" />
              </el-form-item>
              <el-row :gutter="14">
                <el-col :xs="24" :md="12">
                  <el-form-item label="日期">
                    <el-date-picker v-model="todoForm.date" type="date" value-format="YYYY-MM-DD" />
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="12">
                  <el-form-item label="优先级">
                    <el-select v-model="todoForm.priority">
                      <el-option label="高" value="high" />
                      <el-option label="普通" value="normal" />
                      <el-option label="低" value="low" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              <el-button class="schedule-submit-button" type="primary" :loading="savingTodo" @click="submitTodo">保存待办</el-button>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="日计划" name="plan">
        <div class="schedule-grid">
          <el-card shadow="never" class="schedule-panel">
            <template #header>
              <div class="panel-title">
                <span>计划块</span>
                <el-button class="schedule-inline-button" size="small" type="primary" :loading="savingPlan" @click="createPlan">生成日计划</el-button>
              </div>
            </template>
            <div v-if="planBlocks.length" class="plan-list">
              <div v-for="(block, index) in planBlocks" :key="`${block.type}-${block.id || index}`" class="plan-row">
                <span>{{ block.time || String(index + 1).padStart(2, '0') }}</span>
                <strong>{{ block.title }}</strong>
                <el-tag size="small" :type="block.type === 'event' ? 'success' : 'warning'">
                  {{ block.type === 'event' ? '日程' : '待办' }}
                </el-tag>
              </div>
            </div>
            <el-empty v-else description="还没有生成日计划" />
          </el-card>

          <el-card shadow="never" class="schedule-panel">
            <template #header>日复盘</template>
            <el-form label-position="top" :model="reviewForm" @submit.prevent>
              <el-form-item label="完成数量">
                <el-input-number v-model="reviewForm.completed" :min="0" controls-position="right" />
              </el-form-item>
              <el-form-item label="阻塞项">
                <el-input v-model="blockedText" placeholder="多个阻塞项用逗号分隔" />
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="reviewForm.note" type="textarea" :rows="4" />
              </el-form-item>
              <el-button class="schedule-submit-button" type="primary" :loading="savingReview" @click="submitReview">保存复盘</el-button>
            </el-form>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="全局" name="all">
        <div class="schedule-grid">
          <el-card shadow="never" class="schedule-panel">
            <template #header>未来日程</template>
            <el-table :data="events" stripe height="430" class="schedule-events-table">
              <el-table-column prop="date" label="日期" width="116" />
              <el-table-column prop="time" label="时间" width="90" />
              <el-table-column prop="title" label="标题" show-overflow-tooltip />
              <el-table-column prop="source" label="来源" width="130" show-overflow-tooltip />
              <el-table-column label="操作" width="82" fixed="right">
                <template #default="scope">
                  <el-button text size="small" :icon="EditPen" @click="openEventEditor(scope.row)">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-card shadow="never" class="schedule-panel">
            <template #header>目标与纪念日</template>
            <div class="compact-list">
              <div v-for="item in importantDates" :key="item.id" class="compact-row important-date-row">
                <div>
                  <small>重要日期</small>
                  <strong>{{ item.title }}</strong>
                </div>
                <span class="schedule-date-chip">{{ item.date }}</span>
              </div>
              <div v-for="goal in goals" :key="goal.id" class="compact-row goal-row">
                <div>
                  <small>目标追踪</small>
                  <strong>{{ goal.title }}</strong>
                </div>
                <span>{{ goal.cadence || '持续目标' }} · {{ goal.streak || 0 }} 天</span>
              </div>
            </div>
            <el-empty v-if="!importantDates.length && !goals.length" description="暂无目标和重要日期" />
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="eventEditorVisible"
      class="schedule-editor-dialog"
      title="编辑日程"
      width="min(520px, calc(100vw - 32px))"
      append-to-body
      align-center
      destroy-on-close
      :close-on-click-modal="false"
      @closed="resetEventEditor"
    >
      <p class="schedule-dialog-lead">调整时间或说明，保存后今日时间线会立即重新排序。</p>
      <el-form label-position="top" :model="eventEditor" @submit.prevent>
        <el-form-item label="标题" required><el-input v-model="eventEditor.title" /></el-form-item>
        <el-row :gutter="14">
          <el-col :xs="24" :sm="12"><el-form-item label="日期" required><el-date-picker v-model="eventEditor.date" type="date" value-format="YYYY-MM-DD" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="时间"><el-time-picker v-model="eventEditor.time" value-format="HH:mm" format="HH:mm" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="备注"><el-input v-model="eventEditor.note" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="eventEditorVisible = false">取消</el-button>
        <el-button class="schedule-submit-button" type="primary" :loading="savingEventEdit" @click="saveEventEdit">保存修改</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="todoEditorVisible"
      class="schedule-editor-dialog"
      title="编辑待办"
      width="min(500px, calc(100vw - 32px))"
      append-to-body
      align-center
      destroy-on-close
      :close-on-click-modal="false"
      @closed="resetTodoEditor"
    >
      <p class="schedule-dialog-lead">让标题保持可执行，并重新确认日期和优先级。</p>
      <el-form label-position="top" :model="todoEditor" @submit.prevent>
        <el-form-item label="标题" required><el-input v-model="todoEditor.title" /></el-form-item>
        <el-row :gutter="14">
          <el-col :xs="24" :sm="12"><el-form-item label="日期"><el-date-picker v-model="todoEditor.date" type="date" value-format="YYYY-MM-DD" /></el-form-item></el-col>
          <el-col :xs="24" :sm="12"><el-form-item label="优先级"><el-select v-model="todoEditor.priority"><el-option label="高" value="high" /><el-option label="普通" value="normal" /><el-option label="低" value="low" /></el-select></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="todoEditorVisible = false">取消</el-button>
        <el-button class="schedule-submit-button" type="primary" :loading="savingTodoEdit" @click="saveTodoEdit">保存修改</el-button>
      </template>
    </el-dialog>
  </main>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useStorage } from '@vueuse/core'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { Delete, EditPen, HomeFilled, Refresh } from '@element-plus/icons-vue'
import {
  createScheduleEvent,
  createScheduleTodo,
  deleteScheduleEvent,
  deleteScheduleTodo,
  fetchScheduleSnapshot,
  generateDayPlan,
  saveDayReview,
  toggleScheduleTodo,
  updateScheduleEvent,
  updateScheduleTodo,
  type ImportantDate,
  type ScheduleDayPlan,
  type ScheduleEvent,
  type ScheduleGoal,
  type ScheduleTodo
} from './api'

const selectedDate = dayjs().format('YYYY-MM-DD')
const activeTab = useStorage('niu-vue-schedule-active-tab', 'today')
const loading = ref(false)
const error = ref('')
const savingEvent = ref(false)
const savingTodo = ref(false)
const savingPlan = ref(false)
const savingReview = ref(false)
const savingEventEdit = ref(false)
const savingTodoEdit = ref(false)
const eventEditorVisible = ref(false)
const todoEditorVisible = ref(false)

const todayEvents = ref<ScheduleEvent[]>([])
const todayTodos = ref<ScheduleTodo[]>([])
const events = ref<ScheduleEvent[]>([])
const todos = ref<ScheduleTodo[]>([])
const importantDates = ref<ImportantDate[]>([])
const goals = ref<ScheduleGoal[]>([])
const dayPlan = ref<ScheduleDayPlan>({ date: selectedDate })
const conflicts = ref<any[]>([])
const recommendationTips = ref<string[]>([])

const eventForm = reactive({
  title: '',
  date: selectedDate,
  time: '',
  note: ''
})

const todoForm = reactive({
  title: '',
  date: selectedDate,
  priority: 'normal'
})

const reviewForm = reactive({
  completed: 0,
  note: ''
})
const blockedText = ref('')
const eventEditor = reactive({ id: '', title: '', date: selectedDate, time: '', note: '' })
const todoEditor = reactive<{ id: string; title: string; date: string; priority: 'low' | 'normal' | 'high' }>({
  id: '', title: '', date: selectedDate, priority: 'normal'
})
const drawerItems = ['日程核心', '重要日期', '生活代办', '目标追踪', '阅读学习', '出行助手']
const weekdayNames = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

const orderedTodayEvents = computed(() =>
  [...todayEvents.value].sort((left, right) => (left.time || '99:99').localeCompare(right.time || '99:99'))
)
const openTodayTodos = computed(() => todayTodos.value.filter((todo) => !todo.done))
const planBlocks = computed(() => dayPlan.value.plan?.blocks || [])
const eventPlaceholderCount = computed(() => todayEvents.value.length ? Math.max(0, 3 - todayEvents.value.length) : 0)
const todoPlaceholderCount = computed(() => todayTodos.value.length ? Math.max(0, 4 - todayTodos.value.length) : 0)
const recommendationList = computed(() => {
  const tips = recommendationTips.value.filter(Boolean)
  return tips.length ? tips.slice(0, 4) : ['保持一个清晰的时间块，再把待办压缩到可执行的下一步。']
})
const completionRate = computed(() => {
  if (!todayTodos.value.length) return 0
  const done = todayTodos.value.filter((todo) => todo.done).length
  return Math.round((done / todayTodos.value.length) * 100)
})
const todayMonth = computed(() => `${dayjs(selectedDate).month() + 1}月`)
const todayDay = computed(() => dayjs(selectedDate).date())
const todayWeekday = computed(() => weekdayNames[dayjs(selectedDate).day()])
const priorityCards = computed(() => {
  const upcomingDateCount = importantDates.value.length
  const maxStreak = goals.value.reduce((max, goal) => Math.max(max, Number(goal.streak || 0)), 0)
  return [
    {
      index: '1',
      title: '今天只抓三件事',
      description: openTodayTodos.value.length ? `还有 ${openTodayTodos.value.length} 项待办，先保留最关键的。` : '优先级压缩，避免待办墙失控。'
    },
    {
      index: '2',
      title: '重要日期提前露出',
      description: upcomingDateCount ? `当前收录 ${upcomingDateCount} 个重要日期。` : '生日、缴费、证件、纪念日集中看。'
    },
    {
      index: '3',
      title: '长期目标拆到今天',
      description: maxStreak ? `当前最长连续打卡 ${maxStreak} 天。` : '目标不是口号，而是当天动作。'
    }
  ]
})

load()

async function load() {
  loading.value = true
  error.value = ''
  try {
    const snapshot = await fetchScheduleSnapshot(selectedDate)
    todayEvents.value = snapshot.todayEvents
    todayTodos.value = snapshot.todayTodos
    events.value = snapshot.events
    todos.value = snapshot.todos
    importantDates.value = snapshot.importantDates
    goals.value = snapshot.goals
    dayPlan.value = snapshot.dayPlan
    conflicts.value = snapshot.conflicts
    recommendationTips.value = snapshot.recommendation.tips || snapshot.recommendation.recommendations || []
    const review = snapshot.dayReview.review || {}
    reviewForm.completed = Number(review.completed || 0)
    reviewForm.note = String(review.note || '')
    blockedText.value = (review.blocked || []).join('，')
  } catch (err: any) {
    error.value = err.message || '时务局数据读取失败'
  } finally {
    loading.value = false
  }
}

async function submitEvent() {
  if (!eventForm.title.trim()) {
    ElMessage.warning('请填写日程标题')
    return
  }
  savingEvent.value = true
  try {
    await createScheduleEvent({ ...eventForm })
    ElMessage.success('日程已保存')
    eventForm.title = ''
    eventForm.note = ''
    await load()
    activeTab.value = 'today'
  } catch (err: any) {
    ElMessage.error(err.message || '保存日程失败')
  } finally {
    savingEvent.value = false
  }
}

async function submitTodo() {
  if (!todoForm.title.trim()) {
    ElMessage.warning('请填写待办标题')
    return
  }
  savingTodo.value = true
  try {
    await createScheduleTodo({ ...todoForm })
    ElMessage.success('待办已保存')
    todoForm.title = ''
    await load()
  } catch (err: any) {
    ElMessage.error(err.message || '保存待办失败')
  } finally {
    savingTodo.value = false
  }
}

async function toggleTodo(todo: ScheduleTodo) {
  try {
    await toggleScheduleTodo(todo.id, !todo.done)
    await load()
  } catch (err: any) {
    ElMessage.error(err.message || '更新待办失败')
  }
}

async function removeEvent(id: string) {
  try {
    await deleteScheduleEvent(id)
    ElMessage.success('日程已删除')
    await load()
  } catch (err: any) {
    ElMessage.error(err.message || '删除日程失败')
  }
}

async function removeTodo(id: string) {
  try {
    await deleteScheduleTodo(id)
    ElMessage.success('待办已删除')
    await load()
  } catch (err: any) {
    ElMessage.error(err.message || '删除待办失败')
  }
}

function openEventEditor(event: ScheduleEvent) {
  Object.assign(eventEditor, {
    id: event.id,
    title: event.title,
    date: event.date,
    time: event.time || '',
    note: event.note || ''
  })
  eventEditorVisible.value = true
}

function resetEventEditor() {
  Object.assign(eventEditor, { id: '', title: '', date: selectedDate, time: '', note: '' })
}

async function saveEventEdit() {
  if (!eventEditor.title.trim()) {
    ElMessage.warning('请填写日程标题')
    return
  }
  savingEventEdit.value = true
  try {
    await updateScheduleEvent({ ...eventEditor })
    eventEditorVisible.value = false
    ElMessage.success('日程已更新')
    await load()
  } catch (err: any) {
    ElMessage.error(err.message || '更新日程失败')
  } finally {
    savingEventEdit.value = false
  }
}

function openTodoEditor(todo: ScheduleTodo) {
  Object.assign(todoEditor, {
    id: todo.id,
    title: todo.title,
    date: todo.date || '',
    priority: todo.priority
  })
  todoEditorVisible.value = true
}

function resetTodoEditor() {
  Object.assign(todoEditor, { id: '', title: '', date: selectedDate, priority: 'normal' })
}

async function saveTodoEdit() {
  if (!todoEditor.title.trim()) {
    ElMessage.warning('请填写待办标题')
    return
  }
  savingTodoEdit.value = true
  try {
    await updateScheduleTodo({ ...todoEditor })
    todoEditorVisible.value = false
    ElMessage.success('待办已更新')
    await load()
  } catch (err: any) {
    ElMessage.error(err.message || '更新待办失败')
  } finally {
    savingTodoEdit.value = false
  }
}

async function createPlan() {
  savingPlan.value = true
  try {
    await generateDayPlan(selectedDate)
    ElMessage.success('日计划已生成')
    await load()
  } catch (err: any) {
    ElMessage.error(err.message || '生成日计划失败')
  } finally {
    savingPlan.value = false
  }
}

async function submitReview() {
  savingReview.value = true
  try {
    const blocked = blockedText.value.split(/[，,]/).map((item) => item.trim()).filter(Boolean)
    await saveDayReview({ date: selectedDate, completed: reviewForm.completed, blocked, note: reviewForm.note })
    ElMessage.success('复盘已保存')
    await load()
  } catch (err: any) {
    ElMessage.error(err.message || '保存复盘失败')
  } finally {
    savingReview.value = false
  }
}

function priorityLabel(priority: string) {
  return { high: '高', normal: '普通', low: '低' }[priority] || priority
}

</script>
