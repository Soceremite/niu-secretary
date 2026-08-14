import { getJson, postJson } from './http'

export interface AdminLoginResult {
  ok: boolean
  token: string
  expiresIn: number
}

export function loginAdmin(username: string, password: string) {
  return postJson<AdminLoginResult>('/admin/session', { username, password })
}

export function checkAdminSession(token: string) {
  return getJson<{ ok: boolean; authenticated: boolean }>('/admin/session', token)
}

export function fetchAdminData<T>(resource: string, token: string, params: Record<string, string | number | boolean> = {}) {
  const query = new URLSearchParams({ resource })
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value !== undefined && value !== null) query.set(key, String(value))
  })
  return getJson<T>(`/admin/data?${query.toString()}`, token)
}

export function executeAdminAction<T>(token: string, action: string, input: Record<string, unknown>) {
  return postJson<T>('/admin/actions/execute', {
    action,
    input,
    context: { confirmed: true }
  }, token)
}
