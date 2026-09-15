import { getJson, postJson } from '@/app/api/http'
import { fetchAdminData, executeAdminAction } from '@/app/api/admin'

export interface LLMRouteRow {
  name: string
  endpoint: string
  model: string
  style?: string
  maxRetries?: number
  timeout?: number
  fallbacks: { endpoint: string; model: string }[]
}

export interface LLMEndpointRow {
  name: string
  baseUrl: string
  api_key_env: string
  apiKeySet: boolean
  style: string
  timeout: number
}

export function fetchLLMRoutes(token: string) {
  return executeAdminAction<any>(token, 'llm.routes.list', {})
}

export function testLLMEndpoint(token: string, input: {
  endpoint: string; baseUrl?: string; apiKeyEnv?: string; apiKey?: string; timeout_s?: number
}) {
  return executeAdminAction<any>(token, 'llm.endpoint.test', input)
}

export function upsertLLMEndpoint(token: string, input: Record<string, unknown>) {
  return executeAdminAction<any>(token, 'llm.endpoint.upsert', input)
}

export function deleteLLMEndpoint(token: string, endpoint: string) {
  return executeAdminAction<any>(token, 'llm.endpoint.delete', { endpoint })
}

export function updateLLMRoute(token: string, input: Record<string, unknown>) {
  return executeAdminAction<any>(token, 'llm.route.update', input)
}

export function probeLLMRoute(token: string, route: string, prompt?: string) {
  return executeAdminAction<any>(token, 'llm.probe.live', { route, prompt })
}

export { fetchAdminData, executeAdminAction }
export { getJson, postJson }
