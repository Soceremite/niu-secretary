import dayjs from 'dayjs'
import { executeAction, getPublicData } from '@/app/api/actions'

export interface NutritionSummary {
  date: string
  count: number
  calories: number
  proteinG: number
  carbsG: number
  fatG: number
}

export interface FitnessNutritionLog {
  id: string
  date: string
  food: string
  calories: number
  proteinG: number
  carbsG: number
  fatG: number
  source?: string
  createdAt?: string
}

export interface FitnessWorkoutLog {
  id: string
  date: string
  name: string
  durationMin: number
  intensity: 'low' | 'medium' | 'high'
  calories: number
  note?: string
  source?: string
  createdAt?: string
}

export interface FitnessBodyMetric {
  id: string
  date: string
  weightKg?: number | null
  bodyFatPct?: number | null
  waistCm?: number | null
  note?: string
  source?: string
  createdAt?: string
}

export interface FitnessRecoveryLog {
  id: string
  date: string
  sleepHours: number
  sleepQuality: number
  stress: number
  soreness: number
  lastRpe: number
  score: number
  statusLabel: string
  statusAdvice: string
  source?: string
  createdAt?: string
}

export interface FitnessAssessmentLog {
  id: string
  date: string
  goal?: string
  weightKg?: number | null
  waistCm?: number | null
  bmi?: number | null
  fmsTotal?: number
  payload?: Record<string, unknown>
  source?: string
  createdAt?: string
}

export interface FitnessConsultLog {
  id: string
  date: string
  area?: string
  text: string
  level?: string
  title?: string
  payload?: Record<string, unknown>
  source?: string
  createdAt?: string
}

export interface FitnessRecommendationResult {
  recommendations?: string[]
  recentWorkoutMinutes?: number
  recentWorkoutCount?: number
}

interface ListResponse<T> {
  ok?: boolean
  items?: T[]
  count?: number
}

interface SummaryResponse {
  ok?: boolean
  summary: NutritionSummary
}

interface WeeklySummaryResponse {
  ok?: boolean
  summary: {
    from: string
    to: string
    nutritionCount: number
    calories: number
    proteinG: number
    workoutCount: number
    workoutMinutes: number
    workoutCalories: number
    latestMetric?: FitnessBodyMetric | null
    metricsCount: number
  }
}

interface ProfileResponse {
  ok?: boolean
  profile?: Record<string, unknown>
}

export interface FitnessSnapshot {
  today: NutritionSummary
  weekly: WeeklySummaryResponse['summary']
  profile: Record<string, unknown>
  nutrition: FitnessNutritionLog[]
  workouts: FitnessWorkoutLog[]
  metrics: FitnessBodyMetric[]
  recovery: FitnessRecoveryLog[]
  assessments: FitnessAssessmentLog[]
  consults: FitnessConsultLog[]
  workoutRecommendation: FitnessRecommendationResult
}

export function defaultRange(days = 30, toDate = dayjs().format('YYYY-MM-DD')) {
  const to = toDate
  const from = dayjs(to).subtract(days - 1, 'day').format('YYYY-MM-DD')
  return { from, to }
}

export async function fetchFitnessSnapshot(date = dayjs().format('YYYY-MM-DD')): Promise<FitnessSnapshot> {
  const range = defaultRange(30, date)
  const coreRequests: Record<string, () => Promise<unknown>> = {
    today: () => getPublicData<SummaryResponse>(`/fitness/summary/today?date=${encodeURIComponent(date)}`),
    weekly: () => getPublicData<WeeklySummaryResponse>(`/fitness/summary/weekly?date=${encodeURIComponent(date)}`),
    nutrition: () => getPublicData<ListResponse<FitnessNutritionLog>>(`/fitness/nutrition?${rangeQuery(range, 100)}`),
    workouts: () => getPublicData<ListResponse<FitnessWorkoutLog>>(`/fitness/workouts?${rangeQuery(range, 100)}`),
    metrics: () => getPublicData<ListResponse<FitnessBodyMetric>>(`/fitness/body-metrics?${rangeQuery(range, 100)}`),
    recovery: () => getPublicData<ListResponse<FitnessRecoveryLog>>(`/fitness/recovery?${rangeQuery(range, 100)}`)
  }
  const optionalRequests: Record<string, () => Promise<unknown>> = {
    profile: () => getPublicData<ProfileResponse>('/profile?module=fitness'),
    assessments: () => getPublicData<ListResponse<FitnessAssessmentLog>>(`/fitness/assessments?${rangeQuery(range, 50)}`),
    consults: () => getPublicData<ListResponse<FitnessConsultLog>>(`/fitness/consults?${rangeQuery(range, 50)}`),
    workoutRecommendation: () => getPublicData<FitnessRecommendationResult>(`/fitness/recommendations?date=${encodeURIComponent(date)}&type=workout&limit=3`)
  }
  const entries = [
    ...await loadRequestGroup(coreRequests, 3, 6000),
    ...await loadRequestGroup(optionalRequests, 2, 2000)
  ]
  const result = Object.fromEntries(entries) as {
    today?: SummaryResponse | null
    weekly?: WeeklySummaryResponse | null
    profile?: ProfileResponse | null
    nutrition?: ListResponse<FitnessNutritionLog> | null
    workouts?: ListResponse<FitnessWorkoutLog> | null
    metrics?: ListResponse<FitnessBodyMetric> | null
    recovery?: ListResponse<FitnessRecoveryLog> | null
    assessments?: ListResponse<FitnessAssessmentLog> | null
    consults?: ListResponse<FitnessConsultLog> | null
    workoutRecommendation?: FitnessRecommendationResult | null
  }

  return {
    today: result.today?.summary || emptyNutritionSummary(date),
    weekly: result.weekly?.summary || emptyWeeklySummary(date),
    profile: result.profile?.profile || {},
    nutrition: result.nutrition?.items || [],
    workouts: result.workouts?.items || [],
    metrics: result.metrics?.items || [],
    recovery: result.recovery?.items || [],
    assessments: result.assessments?.items || [],
    consults: result.consults?.items || [],
    workoutRecommendation: result.workoutRecommendation || { recommendations: [] }
  }
}

export function createNutritionLog(input: Record<string, unknown>) {
  return executeAction('fitness.nutrition.create', withSource(input), 'vue-fitness', actionContext('nutrition'))
}

export function createWorkoutLog(input: Record<string, unknown>) {
  return executeAction('fitness.workout.create', withSource(input), 'vue-fitness', actionContext('training'))
}

export function createBodyMetric(input: Record<string, unknown>) {
  return executeAction('fitness.body_metric.create', withSource(input), 'vue-fitness', actionContext('body-metric'))
}

export function createRecoveryLog(input: Record<string, unknown>) {
  return executeAction('fitness.recovery.create', withSource(input), 'vue-fitness', actionContext('recovery'))
}

export function createAssessmentLog(input: Record<string, unknown>) {
  return executeAction('fitness.assessment.create', withSource(input), 'vue-fitness', actionContext('assessment'))
}

export function createConsultLog(input: Record<string, unknown>) {
  return executeAction('fitness.consult.create', withSource(input), 'vue-fitness', actionContext('consult'))
}

function rangeQuery(range: { from: string; to: string }, limit: number) {
  return new URLSearchParams({ from: range.from, to: range.to, limit: String(limit) }).toString()
}

function loadRequestGroup(requests: Record<string, () => Promise<unknown>>, limit: number, timeoutMs: number) {
  return runLimited(
    Object.entries(requests).map(([key, run]) => async () => {
      try {
        return [key, await withTimeout(run(), timeoutMs, key)] as const
      } catch {
        return [key, null] as const
      }
    }),
    limit
  )
}

async function runLimited<T>(tasks: Array<() => Promise<T>>, limit: number) {
  const results: T[] = []
  let nextIndex = 0
  async function worker() {
    while (nextIndex < tasks.length) {
      const current = nextIndex
      nextIndex += 1
      results[current] = await tasks[current]()
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, tasks.length) }, () => worker()))
  return results
}

async function withTimeout<T>(promise: Promise<T>, ms: number, label: string) {
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(`fitness request timeout: ${label}`)), ms)
  })
  try {
    return await Promise.race([promise, timeout])
  } finally {
    if (timeoutId) clearTimeout(timeoutId)
  }
}

function emptyNutritionSummary(date: string): NutritionSummary {
  return { date, count: 0, calories: 0, proteinG: 0, carbsG: 0, fatG: 0 }
}

function emptyWeeklySummary(date: string): WeeklySummaryResponse['summary'] {
  return {
    from: dayjs(date).subtract(6, 'day').format('YYYY-MM-DD'),
    to: date,
    nutritionCount: 0,
    calories: 0,
    proteinG: 0,
    workoutCount: 0,
    workoutMinutes: 0,
    workoutCalories: 0,
    latestMetric: null,
    metricsCount: 0
  }
}

function withSource(input: Record<string, unknown>) {
  return { ...input, source: 'vue-fitness' }
}

function actionContext(surface: string) {
  return { source: 'vue-fitness-page', surface }
}
