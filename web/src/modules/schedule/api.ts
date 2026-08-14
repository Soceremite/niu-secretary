import dayjs from 'dayjs'
import { executeAction, getPublicData } from '@/app/api/actions'

export interface ScheduleEvent {
  id: string
  title: string
  date: string
  time?: string
  note?: string
  source?: string
  createdAt?: string
}

export interface ScheduleTodo {
  id: string
  title: string
  date?: string
  priority: 'low' | 'normal' | 'high'
  done: boolean
  source?: string
  createdAt?: string
}

export interface ImportantDate {
  id: string
  title: string
  date: string
  note?: string
  source?: string
}

export interface ScheduleGoal {
  id: string
  title: string
  cadence?: string
  streak?: number
  note?: string
}

export interface ScheduleDayPlanBlock {
  id?: string
  type: 'event' | 'todo'
  time?: string
  title: string
  priority?: string
}

export interface ScheduleDayPlan {
  id?: string
  date: string
  plan?: {
    blocks?: ScheduleDayPlanBlock[]
    eventCount?: number
    todoCount?: number
    conflictCount?: number
  }
  source?: string
}

export interface ScheduleDayReview {
  id?: string
  date: string
  review?: {
    completed?: number
    blocked?: string[]
    note?: string
  }
}

export interface ScheduleConflict {
  date: string
  time: string
  events: ScheduleEvent[]
}

export interface ScheduleRecommendation {
  tips?: string[]
  recommendations?: string[]
  message?: string
}

interface ListResponse<T> {
  ok?: boolean
  items?: T[]
  count?: number
}

interface TodaySummaryResponse {
  ok?: boolean
  summary: {
    date: string
    events: ScheduleEvent[]
    todos: ScheduleTodo[]
  }
}

interface DayPlanResponse {
  ok?: boolean
  plan: ScheduleDayPlan
  found?: boolean
}

interface DayReviewResponse {
  ok?: boolean
  review: ScheduleDayReview
  found?: boolean
}

interface ConflictResponse {
  ok?: boolean
  conflicts: ScheduleConflict[]
  count?: number
}

export interface ScheduleSnapshot {
  date: string
  todayEvents: ScheduleEvent[]
  todayTodos: ScheduleTodo[]
  events: ScheduleEvent[]
  todos: ScheduleTodo[]
  importantDates: ImportantDate[]
  goals: ScheduleGoal[]
  dayPlan: ScheduleDayPlan
  dayReview: ScheduleDayReview
  conflicts: ScheduleConflict[]
  recommendation: ScheduleRecommendation
}

export function defaultScheduleRange(days = 30) {
  const from = dayjs().format('YYYY-MM-DD')
  const to = dayjs().add(days - 1, 'day').format('YYYY-MM-DD')
  return { from, to }
}

export async function fetchScheduleSnapshot(date = dayjs().format('YYYY-MM-DD')): Promise<ScheduleSnapshot> {
  const range = defaultScheduleRange(30)
  const query = new URLSearchParams({ from: range.from, to: range.to, limit: '120' }).toString()
  const [
    today,
    events,
    todos,
    importantDates,
    goals,
    dayPlan,
    dayReview,
    conflicts,
    recommendation
  ] = await Promise.all([
    getPublicData<TodaySummaryResponse>(`/schedule/summary/today?date=${encodeURIComponent(date)}`),
    getPublicData<ListResponse<ScheduleEvent>>(`/schedule/events?${query}`),
    getPublicData<ListResponse<ScheduleTodo>>('/schedule/todos?includeDone=true&limit=160'),
    getPublicData<ListResponse<ImportantDate>>('/schedule/important-dates?limit=30').catch(() => ({ items: [] })),
    getPublicData<ListResponse<ScheduleGoal>>('/schedule/goals?limit=30').catch(() => ({ items: [] })),
    getPublicData<DayPlanResponse>(`/schedule/day-plan?date=${encodeURIComponent(date)}`),
    getPublicData<DayReviewResponse>(`/schedule/day-review?date=${encodeURIComponent(date)}`),
    getPublicData<ConflictResponse>(`/schedule/conflicts?date=${encodeURIComponent(date)}`),
    getPublicData<ScheduleRecommendation>(`/schedule/recommend?date=${encodeURIComponent(date)}`).catch(() => ({ tips: [] }))
  ])

  return {
    date,
    todayEvents: today.summary?.events || [],
    todayTodos: today.summary?.todos || [],
    events: events.items || [],
    todos: todos.items || [],
    importantDates: importantDates.items || [],
    goals: goals.items || [],
    dayPlan: dayPlan.plan || { date },
    dayReview: dayReview.review || { date },
    conflicts: conflicts.conflicts || [],
    recommendation
  }
}

export function createScheduleEvent(input: Record<string, unknown>) {
  return executeAction('schedule.event.create', withSource(input), 'vue-schedule', actionContext('event'))
}

export function createScheduleTodo(input: Record<string, unknown>) {
  return executeAction('schedule.todo.create', withSource(input), 'vue-schedule', actionContext('todo'))
}

export function updateScheduleEvent(input: Record<string, unknown>) {
  return executeAction('schedule.event.update', withSource(input), 'vue-schedule', actionContext('event-edit'))
}

export function updateScheduleTodo(input: Record<string, unknown>) {
  return executeAction('schedule.todo.update', withSource(input), 'vue-schedule', actionContext('todo-edit'))
}

export function toggleScheduleTodo(id: string, done: boolean) {
  return executeAction('schedule.todo.toggle', { id, done, source: 'vue-schedule' }, 'vue-schedule', actionContext('todo-toggle'))
}

export function deleteScheduleEvent(id: string) {
  return executeAction('schedule.event.delete', { id, source: 'vue-schedule' }, 'vue-schedule', actionContext('event-delete'))
}

export function deleteScheduleTodo(id: string) {
  return executeAction('schedule.todo.delete', { id, source: 'vue-schedule' }, 'vue-schedule', actionContext('todo-delete'))
}

export function generateDayPlan(date: string) {
  return executeAction('schedule.day.plan', { date, source: 'vue-schedule' }, 'vue-schedule', actionContext('day-plan'))
}

export function saveDayReview(input: Record<string, unknown>) {
  return executeAction('schedule.day.review', withSource(input), 'vue-schedule', actionContext('day-review'))
}

function withSource(input: Record<string, unknown>) {
  return { ...input, source: 'vue-schedule' }
}

function actionContext(surface: string) {
  return { source: 'vue-schedule-page', surface }
}
