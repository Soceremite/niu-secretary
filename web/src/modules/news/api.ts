import { getPublicData } from '@/app/api/actions'

export interface NewsItem {
  id?: string
  openId?: string
  date?: string
  section?: string
  sectionName?: string
  sectionLabel?: string
  title: string
  summary?: string
  sourceName?: string
  sourceUrl?: string
  url?: string
  dateText?: string
  imagePath?: string
  detailHtml?: string
  tag?: string
  tags?: string[]
  matchScore?: number
}

export interface NewsRecommendResponse {
  ok?: boolean
  profile?: Record<string, unknown>
  researchProfile?: Record<string, unknown>
  personalized?: boolean
  items: NewsItem[]
  count: number
  message?: string
}

interface NewsSearchResponse {
  ok?: boolean
  items?: NewsItem[]
  count?: number
  message?: string
}

export interface NewsSnapshot {
  recommendations: NewsItem[]
  profile: Record<string, unknown>
  researchProfile: Record<string, unknown>
  message: string
  personalized: boolean
}

export async function fetchNewsSnapshot(limit = 10): Promise<NewsSnapshot> {
  const result = await getPublicData<NewsRecommendResponse>(`/news/recommend?limit=${limit}`)
  return {
    recommendations: result.items || [],
    profile: result.profile || {},
    researchProfile: result.researchProfile || {},
    message: result.message || '',
    personalized: Boolean(result.personalized)
  }
}

export async function searchNews(q: string, section = '', limit = 20) {
  const params = new URLSearchParams({ q, limit: String(limit) })
  if (section) params.set('section', section)
  const result = await getPublicData<NewsSearchResponse>(`/news/search?${params.toString()}`)
  return result.items || []
}
