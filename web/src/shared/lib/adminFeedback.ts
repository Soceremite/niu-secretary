import { readonly, shallowRef } from 'vue'
import { ElMessageBox } from 'element-plus'

export type AdminFeedbackType = 'success' | 'warning' | 'error' | 'info'

export interface AdminFeedbackMessage {
  id: number
  type: AdminFeedbackType
  title: string
  message: string
}

const currentFeedback = shallowRef<AdminFeedbackMessage | null>(null)
let feedbackId = 0
let dismissTimer: ReturnType<typeof setTimeout> | undefined

export const adminFeedback = readonly(currentFeedback)

function show(type: AdminFeedbackType, message: string, title?: string) {
  clearTimeout(dismissTimer)
  const id = ++feedbackId
  currentFeedback.value = { id, type, title: title || typeTitle(type), message }
  dismissTimer = setTimeout(() => {
    if (currentFeedback.value?.id === id) currentFeedback.value = null
  }, type === 'error' ? 8000 : 4000)
}

export function clearAdminFeedback() {
  clearTimeout(dismissTimer)
  dismissTimer = undefined
  currentFeedback.value = null
}

export const adminToast = {
  success: (message: string, title?: string) => show('success', message, title),
  warning: (message: string, title?: string) => show('warning', message, title),
  error: (message: string, title?: string) => show('error', message, title),
  info: (message: string, title?: string) => show('info', message, title)
}

export function adminConfirm(message: string, title = '确认操作') {
  return ElMessageBox.confirm(message, title, {
    confirmButtonText: '确认',
    cancelButtonText: '取消',
    type: 'warning',
    customClass: 'admin-confirm-box',
    draggable: false,
    closeOnClickModal: false
  })
}

function typeTitle(type: AdminFeedbackType) {
  return {
    success: '已完成',
    warning: '需要确认',
    error: '操作失败',
    info: '提示'
  }[type]
}
