const API_BASE = '/niu-secretary/api'

export interface ApiError extends Error {
  status?: number
  payload?: unknown
}

export async function getJson<T>(path: string, token = ''): Promise<T> {
  return requestJson<T>('GET', path, undefined, token)
}

export async function postJson<T>(path: string, body: unknown, token = ''): Promise<T> {
  return requestJson<T>('POST', path, body, token)
}

async function requestJson<T>(method: string, path: string, body?: unknown, token = ''): Promise<T> {
  const response = await fetch(API_BASE + path, {
    method,
    headers: {
      ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body === undefined ? undefined : JSON.stringify(body)
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok || payload?.ok === false) {
    const error = new Error(payload?.message || `${method} ${path} failed`) as ApiError
    error.status = response.status
    error.payload = payload
    throw error
  }
  return payload as T
}
