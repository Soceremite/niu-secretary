#!/usr/bin/env node
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { fileURLToPath } from 'node:url'
import playwright from '../web/node_modules/playwright/index.js'

const { chromium } = playwright

const projectRoot = new URL('../', import.meta.url)
const apiPort = Number(process.env.NIU_SECRETARY_SCHEDULE_SMOKE_API_PORT || 5200)
const webPort = Number(process.env.NIU_SECRETARY_SCHEDULE_SMOKE_WEB_PORT || 4177)
const apiBase = `http://127.0.0.1:${apiPort}/niu-secretary/api`
const webBase = `http://127.0.0.1:${webPort}/niu-secretary/`
const dbDir = await mkdtemp(join(tmpdir(), 'niu-secretary-schedule-smoke-'))
const dbPath = join(dbDir, 'smoke.sqlite3')
const today = new Date().toISOString().slice(0, 10)

const api = spawn('python3', ['-m', 'server.niu_secretary_api'], {
  cwd: projectRoot,
  env: {
    ...process.env,
    NIU_SECRETARY_API_PORT: String(apiPort),
    NIU_SECRETARY_DB_PATH: dbPath
  },
  stdio: ['ignore', 'pipe', 'pipe']
})

const viteBin = fileURLToPath(new URL('../web/node_modules/vite/bin/vite.js', import.meta.url))
const web = spawn(process.execPath, [viteBin, '--host', '127.0.0.1', '--port', String(webPort), '--strictPort'], {
  cwd: new URL('../web/', import.meta.url),
  env: { ...process.env, NIU_SECRETARY_API_PORT: String(apiPort) },
  stdio: ['ignore', 'pipe', 'pipe']
})

let browser

try {
  await waitForServer(`${apiBase}/health`)
  await waitForServer(webBase)
  await seedScheduleData()

  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  await page.goto(`${webBase}schedule/`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '牛秘书时务局')
  await expectVisibleText(page, '时务局')
  await expectVisibleText(page, '我的画像 · 今日建议')
  await expectVisibleText(page, '事务抽屉')
  await expectVisibleText(page, '数据同步状态')
  await expectVisibleText(page, 'Smoke 站会')
  await expectVisibleText(page, 'Smoke 周报')
  await assertNoHorizontalOverflow(page)
  await assertScheduleLayout(page)
  await assertStableScheduleFrames(page)

  await verifyEventEditor(page)
  await verifyTodoEditor(page)

  await page.getByRole('tab', { name: '录入' }).click()
  const eventTitleInput = page.locator('input[placeholder="例如：产品评审"]')
  await eventTitleInput.waitFor({ state: 'visible' })
  await eventTitleInput.fill('Smoke 页面新增日程')
  await page.getByRole('button', { name: '保存日程' }).click({ force: true })
  await page.getByRole('tab', { name: '今日' }).click({ force: true })
  await expectVisibleText(page, 'Smoke 页面新增日程')

  await page.getByRole('tab', { name: '日计划' }).click({ force: true })
  await page.getByRole('button', { name: '生成日计划' }).click({ force: true })
  await expectVisibleText(page, 'Smoke 站会')
  await assertNoHorizontalOverflow(page)

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } })
  await mobile.goto(`${webBase}schedule/`, { waitUntil: 'networkidle' })
  await expectVisibleText(mobile, '时务局')
  await expectVisibleText(mobile, '数据同步状态')
  await assertNoHorizontalOverflow(mobile)
  await assertScheduleLayout(mobile)
  await assertStableScheduleFrames(mobile)
  await verifyMobileStacking(mobile)
  await verifyMobileEditorPlacement(mobile)
  await mobile.close()

  console.log(JSON.stringify({ ok: true, apiBase, webBase, dbPath, route: '/schedule/' }, null, 2))
} catch (error) {
  if (browser) {
    const pages = browser.contexts().flatMap((context) => context.pages())
    const page = pages[0]
    if (page) {
      const text = await page.locator('body').innerText().catch(() => '')
      console.error(JSON.stringify({ url: page.url(), body: text.slice(0, 1000) }, null, 2))
    }
  }
  throw error
} finally {
  if (browser) await browser.close()
  await stop(api)
  await stop(web)
}

async function seedScheduleData() {
  await action('schedule.event.create', {
    title: 'Smoke 站会',
    date: today,
    time: '09:30',
    note: 'Vue schedule smoke test',
    source: 'vue-schedule-smoke'
  })
  await action('schedule.todo.create', {
    title: 'Smoke 周报',
    date: today,
    priority: 'high',
    source: 'vue-schedule-smoke'
  })
}

async function action(actionName, input) {
  return postJson(`${apiBase}/actions/execute`, {
    action: actionName,
    input,
    context: { client: 'vue-schedule-smoke', confirmed: true }
  })
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok || payload.ok === false) {
    throw new Error(`${url} failed: ${response.status} ${JSON.stringify(payload)}`)
  }
  return payload
}

async function expectVisibleText(page, text) {
  const deadline = Date.now() + 10000
  let body = ''
  while (Date.now() < deadline) {
    body = await page.locator('body').innerText().catch(() => '')
    if (body.includes(text)) return
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`missing text: ${text}\n${body.slice(0, 1000)}`)
}

async function assertNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth))
  if (overflow > 1) throw new Error(`schedule page has horizontal overflow: ${overflow}`)
}

async function assertScheduleLayout(page) {
  const metrics = await page.evaluate(() => {
    const readRect = (selector) => {
      const element = document.querySelector(selector)
      if (!element) return null
      const rect = element.getBoundingClientRect()
      return { width: rect.width, height: rect.height, left: rect.left, right: rect.right }
    }
    const bodyWidth = document.documentElement.clientWidth
    const hero = readRect('.schedule-hero')
    const cache = readRect('.schedule-cache-note')
    const cachePill = readRect('.schedule-cache-note > span')
    const rows = Array.from(document.querySelectorAll('.todo-row, .plan-row, .compact-row')).map((element) => {
      const rect = element.getBoundingClientRect()
      return { width: rect.width, right: rect.right }
    })
    return { bodyWidth, hero, cache, cachePill, rows }
  })

  if (!metrics.hero || metrics.hero.height > 300) {
    throw new Error(`schedule hero is too tall: ${metrics.hero?.height}`)
  }
  for (const [name, rect] of Object.entries({ cache: metrics.cache, cachePill: metrics.cachePill })) {
    if (!rect) throw new Error(`missing schedule ${name}`)
    if (rect.right > metrics.bodyWidth + 1 || rect.left < -1) {
      throw new Error(`schedule ${name} overflows viewport: ${JSON.stringify(rect)}`)
    }
  }
  const overflowingRow = metrics.rows.find((row) => row.right > metrics.bodyWidth + 1)
  if (overflowingRow) throw new Error(`schedule row overflows viewport: ${JSON.stringify(overflowingRow)}`)
}

async function assertStableScheduleFrames(page) {
  const frames = await page.evaluate(() => {
    const measure = (testId) => {
      const element = document.querySelector(`[data-testid="${testId}"]`)
      if (!element) return null
      const rect = element.getBoundingClientRect()
      return { height: rect.height, width: rect.width }
    }
    return {
      event: measure('schedule-event-frame'),
      todo: measure('schedule-todo-frame')
    }
  })
  if (!frames.event || !frames.todo) throw new Error(`missing stable schedule frames: ${JSON.stringify(frames)}`)
  const isMobile = await page.evaluate(() => window.innerWidth <= 760)
  const eventMinimum = isMobile ? 330 : 500
  const todoMinimum = isMobile ? 330 : 310
  if (frames.event.height < eventMinimum || frames.todo.height < todoMinimum) {
    throw new Error(`schedule frames collapsed with low data: ${JSON.stringify(frames)}`)
  }
}

async function verifyEventEditor(page) {
  const editButton = page.locator('.timeline-item').filter({ hasText: 'Smoke 站会' }).getByRole('button', { name: '编辑' })
  await editButton.scrollIntoViewIfNeeded()
  const before = await viewportMetrics(page)
  await editButton.click()
  await assertEditorPlacement(page, '编辑日程', before)
  const dialog = page.getByRole('dialog', { name: '编辑日程' })
  await dialog.getByLabel('标题').fill('Smoke 站会已调整')
  await dialog.getByRole('button', { name: '保存修改' }).click()
  await dialog.waitFor({ state: 'hidden' })
  await expectVisibleText(page, 'Smoke 站会已调整')
  await assertNoHorizontalOverflow(page)
}

async function verifyTodoEditor(page) {
  const editButton = page.locator('.todo-row').filter({ hasText: 'Smoke 周报' }).getByRole('button', { name: '编辑' })
  await editButton.scrollIntoViewIfNeeded()
  const before = await viewportMetrics(page)
  await editButton.click()
  await assertEditorPlacement(page, '编辑待办', before)
  const dialog = page.getByRole('dialog', { name: '编辑待办' })
  await dialog.getByLabel('标题').fill('Smoke 周报已调整')
  await dialog.getByRole('button', { name: '保存修改' }).click()
  await dialog.waitFor({ state: 'hidden' })
  await expectVisibleText(page, 'Smoke 周报已调整')
  await assertNoHorizontalOverflow(page)
}

async function verifyMobileStacking(page) {
  const layout = await page.evaluate(() => {
    const event = document.querySelector('[data-testid="schedule-event-frame"]')?.getBoundingClientRect()
    const todo = document.querySelector('[data-testid="schedule-todo-frame"]')?.getBoundingClientRect()
    return event && todo ? { eventBottom: event.bottom, todoTop: todo.top, leftDelta: Math.abs(event.left - todo.left) } : null
  })
  if (!layout || layout.todoTop < layout.eventBottom - 1 || layout.leftDelta > 2) {
    throw new Error(`schedule mobile panels are not stacked: ${JSON.stringify(layout)}`)
  }
}

async function verifyMobileEditorPlacement(page) {
  const editButton = page.locator('.timeline-item').first().getByRole('button', { name: '编辑' })
  await editButton.scrollIntoViewIfNeeded()
  const before = await viewportMetrics(page)
  await editButton.click()
  await assertEditorPlacement(page, '编辑日程', before)
  await page.getByRole('dialog', { name: '编辑日程' }).getByRole('button', { name: '取消' }).click()
}

async function viewportMetrics(page) {
  return page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    scrollY: window.scrollY
  }))
}

async function assertEditorPlacement(page, name, before) {
  const dialog = page.getByRole('dialog', { name })
  await dialog.waitFor({ state: 'visible' })
  await page.waitForTimeout(350)
  const metrics = await page.evaluate(() => {
    const element = document.querySelector('.schedule-editor-dialog')
    const rect = element?.getBoundingClientRect()
    return rect ? {
      top: rect.top,
      bottom: rect.bottom,
      left: rect.left,
      right: rect.right,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
      scrollY: window.scrollY
    } : null
  })
  if (!metrics) throw new Error(`missing ${name} dialog metrics`)
  if (metrics.top < 0 || metrics.bottom > metrics.viewportHeight + 1 || metrics.left < 0 || metrics.right > metrics.viewportWidth + 1) {
    throw new Error(`${name} dialog is outside viewport: ${JSON.stringify(metrics)}`)
  }
  if (metrics.scrollWidth - metrics.clientWidth > 1 || Math.abs(metrics.clientWidth - before.clientWidth) > 1) {
    throw new Error(`${name} dialog changed page width: before=${JSON.stringify(before)} after=${JSON.stringify(metrics)}`)
  }
  if (Math.abs(metrics.scrollY - before.scrollY) > 1) {
    throw new Error(`${name} dialog changed page scroll position: before=${before.scrollY} after=${metrics.scrollY}`)
  }
}

async function waitForServer(url) {
  const deadline = Date.now() + 15000
  let lastError
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url)
      if (response.ok) return
    } catch (error) {
      lastError = error
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`${url} did not become ready: ${lastError?.message || 'timeout'}`)
}

async function stop(child) {
  if (child.exitCode !== null || child.signalCode !== null) return
  child.kill('SIGTERM')
  await Promise.race([once(child, 'exit'), new Promise((resolve) => setTimeout(resolve, 1500))])
  if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL')
}
