import { executeAction, getPublicData } from '@/app/api/actions'

export type LeisureCategory = 'movie' | 'music' | 'podcast' | 'novel'

export interface LeisureItem {
  id: string
  itemId?: string
  title: string
  category?: LeisureCategory
  genres?: string[]
  mood?: string
  reason?: string
  duration?: string
  durationMinutes?: number
  matchScore?: number
  url?: string
  externalUrl?: string
  doubanUrl?: string
  posterUrl?: string
  coverUrl?: string
  imageUrl?: string
  thumbnailUrl?: string
  year?: string | number
  region?: string
  director?: string
  actors?: string
  album?: string
  author?: string
  episode?: string
  score?: number
  payload?: Record<string, unknown>
  source?: string
  updatedAt?: string
}

export interface LeisureGroup {
  category: LeisureCategory
  label: string
  items: LeisureItem[]
}

export interface LeisureRecommendationResponse {
  ok?: boolean
  profile?: Record<string, unknown>
  personalized?: boolean
  context?: Record<string, unknown>
  groups: LeisureGroup[]
  count: number
  message?: string
}

export interface LeisureHistoryItem {
  id: string
  itemId: string
  category: LeisureCategory
  title: string
  interaction: 'save' | 'dismiss' | 'rate'
  rating?: number
  note?: string
  createdAt?: string
}

export interface LeisureProfileSuggestion {
  id: string
  title: string
  payload?: {
    item?: LeisureItem
    patch?: Record<string, unknown>
  }
  createdAt?: string
}

interface ListResponse<T> {
  ok?: boolean
  items?: T[]
  count?: number
}

interface ProfileResponse {
  ok?: boolean
  profile?: Record<string, unknown>
}

export interface LeisureSnapshot {
  recommendation: LeisureRecommendationResponse
  savedItems: LeisureItem[]
  history: LeisureHistoryItem[]
  profileSuggestions: LeisureProfileSuggestion[]
  profile: Record<string, unknown>
}

export async function fetchLeisureSnapshot(): Promise<LeisureSnapshot> {
  const [recommendation, savedItems, history, profileSuggestions, profile] = await Promise.all([
    getPublicData<LeisureRecommendationResponse>('/leisure/recommend?limit=10'),
    getPublicData<ListResponse<LeisureItem>>('/leisure/items?limit=80').catch(() => ({ items: [] })),
    getPublicData<ListResponse<LeisureHistoryItem>>('/leisure/history?limit=80').catch(() => ({ items: [] })),
    getPublicData<ListResponse<LeisureProfileSuggestion>>('/leisure/profile/suggestions?limit=5').catch(() => ({ items: [] })),
    getPublicData<ProfileResponse>('/profile?module=leisure').catch(() => ({ profile: {} }))
  ])
  return {
    recommendation,
    savedItems: savedItems.items || [],
    history: history.items || [],
    profileSuggestions: profileSuggestions.items || [],
    profile: profile.profile || {}
  }
}

export function saveLeisureItem(item: LeisureItem, category: LeisureCategory, note = '') {
  return executeAction('leisure.item.save', feedbackInput(item, category, { note }), 'vue-leisure', actionContext('save'))
}

export function dismissLeisureItem(item: LeisureItem, category: LeisureCategory, note = '') {
  return executeAction('leisure.item.dismiss', feedbackInput(item, category, { note }), 'vue-leisure', actionContext('dismiss'))
}

export function rateLeisureItem(item: LeisureItem, category: LeisureCategory, rating: number, note = '') {
  return executeAction(
    'leisure.item.rate',
    feedbackInput(item, category, { rating, note }),
    'vue-leisure',
    actionContext('rate')
  )
}

export function applyLeisureProfileSuggestion(eventId: string) {
  return executeAction(
    'leisure.profile.apply_suggestion',
    { eventId },
    'vue-leisure',
    actionContext('profile-suggestion')
  )
}

function feedbackInput(item: LeisureItem, category: LeisureCategory, extra: Record<string, unknown>) {
  return {
    itemId: item.id || item.itemId || `${category}:${item.title}`,
    category,
    title: item.title,
    payload: {
      ...item,
      category
    },
    source: 'vue-leisure',
    ...extra
  }
}

function actionContext(surface: string) {
  return { source: 'vue-leisure-page', surface }
}
