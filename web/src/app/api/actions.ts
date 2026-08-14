import { getJson, postJson } from './http'

export interface ProposedAction {
  action: string
  title?: string
  input: Record<string, unknown>
  requiresConfirmation?: boolean
}

export interface AssistantResponse {
  ok?: boolean
  module: string
  reply: string
  source?: string
  proposedActions: ProposedAction[]
}

export interface ActionExecutionContext {
  [key: string]: unknown
}

export interface ActionExecutionResult {
  ok: boolean
  message?: string
  record?: unknown
  requiresConfirmation?: boolean
}

export function sendAssistantMessage(text: string) {
  return postJson<AssistantResponse>('/assistant/message', {
    text,
    context: { client: 'vue-home' }
  })
}

export function executeAction(
  action: string,
  input: Record<string, unknown>,
  client = 'vue-web',
  extraContext: ActionExecutionContext = {}
) {
  return postJson<ActionExecutionResult>('/actions/execute', {
    action,
    input,
    context: { ...extraContext, client, confirmed: true }
  })
}

export function getPublicData<T>(path: string) {
  return getJson<T>(path)
}
