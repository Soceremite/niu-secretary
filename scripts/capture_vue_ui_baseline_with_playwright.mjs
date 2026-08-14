#!/usr/bin/env node
import { existsSync } from 'node:fs'
import { mkdir, mkdtemp, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { fileURLToPath } from 'node:url'
import playwright from '../web/node_modules/playwright/index.js'

const { chromium } = playwright

const projectRoot = new URL('../', import.meta.url)
const apiPort = Number(process.env.NIU_SECRETARY_UI_BASELINE_API_PORT || 5215)
const webPort = Number(process.env.NIU_SECRETARY_UI_BASELINE_WEB_PORT || 4186)
const adminPassword = 'niu-secretary-baseline-password'
const apiBase = `http://127.0.0.1:${apiPort}/niu-secretary/api`
const webBase = `http://127.0.0.1:${webPort}/niu-secretary/`
const dbDir = await mkdtemp(join(tmpdir(), 'niu-secretary-ui-baseline-'))
const dbPath = join(dbDir, 'baseline.sqlite3')
const baselineDate = process.env.NIU_SECRETARY_UI_BASELINE_DATE || '2026-06-18'
const outputDir = new URL(`../docs/superpowers/artifacts/ui-polish-baseline/${baselineDate}/`, import.meta.url)

const routes = [
  { key: 'home', path: '', expected: '牛秘书' },
  { key: 'fitness', path: 'fitness/', expected: '牛秘书塑形馆' },
  { key: 'schedule', path: 'schedule/', expected: '牛秘书时务局' },
  { key: 'leisure', path: 'leisure/', expected: '牛秘书闲趣集' },
  { key: 'news', path: 'news/', expected: '牛秘书新闻社' },
  { key: 'airesearch', path: 'airesearch/', expected: '牛秘书研知库' },
  { key: 'admin-overview', path: 'admin/', expected: '运营总览', admin: true },
  { key: 'admin-fitness-nutrition', path: 'admin/fitness/nutrition', expected: '营养日志', admin: true },
  { key: 'admin-schedule-events', path: 'admin/schedule/events', expected: '日程', admin: true },
  { key: 'admin-schedule-todos', path: 'admin/schedule/todos', expected: '待办', admin: true },
  { key: 'admin-leisure-items', path: 'admin/leisure/items', expected: '闲趣条目', admin: true },
  { key: 'admin-news-recommendations', path: 'admin/news/recommendations', expected: '新闻推荐', admin: true },
  { key: 'admin-airesearch-overview', path: 'admin/airesearch/', expected: '研知库总览', admin: true },
  { key: 'admin-airesearch-papers', path: 'admin/airesearch/papers', expected: '论文管理', admin: true },
  { key: 'admin-airesearch-discovery', path: 'admin/airesearch/discovery', expected: '搜索入库', admin: true },
  { key: 'admin-airesearch-profiles', path: 'admin/airesearch/profiles', expected: '搜索配置', admin: true },
  { key: 'admin-airesearch-jobs', path: 'admin/airesearch/jobs', expected: '任务中心', admin: true }
]
const requestedRouteKeys = new Set((process.env.NIU_SECRETARY_UI_BASELINE_ROUTE_KEYS || '')
  .split(',')
  .map((key) => key.trim())
  .filter(Boolean))
const selectedRoutes = requestedRouteKeys.size
  ? routes.filter((route) => requestedRouteKeys.has(route.key))
  : routes

if (!selectedRoutes.length) {
  throw new Error(`No baseline routes matched: ${Array.from(requestedRouteKeys).join(', ')}`)
}

const viewports = [
  { key: 'desktop', width: 1440, height: 960 },
  { key: 'mobile', width: 390, height: 844, isMobile: true }
]

const api = spawn('python3', ['-m', 'server.niu_secretary_api'], {
  cwd: projectRoot,
  env: {
    ...process.env,
    NIU_SECRETARY_API_PORT: String(apiPort),
    NIU_SECRETARY_DB_PATH: dbPath,
    NIU_SECRETARY_ADMIN_USER: 'admin',
    NIU_SECRETARY_ADMIN_PASSWORD: adminPassword,
    NIU_SECRETARY_ADMIN_SESSION_SECRET: 'niu-secretary-baseline-session'
  },
  stdio: ['ignore', 'pipe', 'pipe']
})
const apiLogs = collectProcessLogs(api)

const viteBin = fileURLToPath(new URL('../web/node_modules/vite/bin/vite.js', import.meta.url))
const web = spawn(process.execPath, [viteBin, '--host', '127.0.0.1', '--port', String(webPort), '--strictPort'], {
  cwd: new URL('../web/', import.meta.url),
  env: { ...process.env, NIU_SECRETARY_API_PORT: String(apiPort) },
  stdio: ['ignore', 'pipe', 'pipe']
})
const webLogs = collectProcessLogs(web)

let browser

try {
  await mkdir(outputDir, { recursive: true })
  await waitForServer(`${apiBase}/health`)
  await waitForServer(webBase)

  const login = await postJson(`${apiBase}/admin/session`, { username: 'admin', password: adminPassword })
  await seedBaselineData(login.token)

  browser = await chromium.launch({
    headless: true,
    ...(existsSync('/usr/bin/google-chrome-stable') ? { executablePath: '/usr/bin/google-chrome-stable' } : {}),
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
  })
  const context = await browser.newContext()
  await context.addInitScript((token) => {
    localStorage.setItem('niu-secretary-admin-token', token)
  }, login.token)

  const results = []
  for (const viewport of viewports) {
    const page = await context.newPage()
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    for (const route of selectedRoutes) {
      const url = new URL(route.path, webBase).toString()
      await page.goto(url, { waitUntil: 'domcontentloaded' })
      await waitForText(page, route.expected)
      await page.waitForTimeout(route.admin ? 1800 : 1400)
      const screenshot = `${viewport.key}-${route.key}.png`
      await page.screenshot({ path: fileURLToPath(new URL(screenshot, outputDir)), fullPage: false })
      results.push({
        route: `/${route.path}`,
        viewport: viewport.key,
        screenshot: `docs/superpowers/artifacts/ui-polish-baseline/${baselineDate}/${screenshot}`,
        ...(await collectUiMetrics(page))
      })
    }
    await page.close()
  }

  const report = {
    ok: true,
    capturedAt: new Date().toISOString(),
    webBase,
    apiBase,
    dbPath,
    results
  }
  await writeFile(new URL('report.json', outputDir), `${JSON.stringify(report, null, 2)}\n`, 'utf8')
  console.log(JSON.stringify(report, null, 2))
} finally {
  if (browser) await browser.close()
  await stop(api)
  await stop(web)
}

function collectProcessLogs(processHandle) {
  const logs = []
  const push = (prefix, chunk) => {
    logs.push(`${prefix}: ${chunk.toString()}`)
    while (logs.length > 40) logs.shift()
  }
  processHandle.stdout?.on('data', (chunk) => push('stdout', chunk))
  processHandle.stderr?.on('data', (chunk) => push('stderr', chunk))
  return logs
}

async function seedBaselineData(token) {
  await publicAction('fitness.nutrition.create', {
    food: '基线 牛肉面',
    date: '2026-06-17',
    calories: 720,
    proteinG: 32,
    carbsG: 86,
    fatG: 22,
    source: 'ui-baseline'
  })
  await publicAction('fitness.workout.create', {
    name: '基线 力量训练',
    date: '2026-06-17',
    durationMin: 48,
    intensity: 'medium',
    calories: 310,
    source: 'ui-baseline'
  })
  await publicAction('fitness.body_metric.create', {
    date: '2026-06-17',
    weightKg: 72.6,
    bodyFatPct: 18.4,
    waistCm: 82,
    source: 'ui-baseline'
  })
  await publicAction('fitness.recovery.create', {
    date: '2026-06-17',
    sleepHours: 7.2,
    sleepQuality: 4,
    stress: 2,
    soreness: 2,
    score: 78,
    statusLabel: '绿色',
    statusAdvice: '恢复良好，可以按计划训练。',
    source: 'ui-baseline'
  })
  await publicAction('schedule.event.create', {
    title: '基线 产品复盘',
    date: '2026-06-17',
    time: '10:30',
    source: 'ui-baseline'
  })
  await publicAction('schedule.todo.create', {
    title: '基线 检查 Vue UI 精修计划',
    date: '2026-06-17',
    priority: 'high',
    source: 'ui-baseline'
  })
  await publicAction('airesearch.queue.add', {
    title: '基线 多模态检索评估',
    note: '用于 UI 基线截图',
    source: 'ui-baseline'
  })
  await adminAction(token, 'leisure.item.save', {
    itemId: 'baseline-movie-001',
    category: 'movie',
    title: '基线 电影收藏',
    source: 'ui-baseline'
  })
}

async function publicAction(action, input) {
  return postJson(`${apiBase}/actions/execute`, {
    action,
    input,
    context: { confirmed: true, client: 'ui-baseline' }
  })
}

async function adminAction(token, action, input) {
  return postJson(`${apiBase}/admin/actions/execute`, {
    action,
    input,
    context: { confirmed: true, client: 'ui-baseline' }
  }, token)
}

async function postJson(url, body, token = '') {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(body)
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok || payload.ok === false) {
    throw new Error(`${url} failed: ${response.status} ${JSON.stringify(payload)}`)
  }
  return payload
}

async function waitForText(page, expected) {
  const deadline = Date.now() + 12000
  while (Date.now() < deadline) {
    const body = await page.locator('body').innerText().catch(() => '')
    if (body.includes(expected)) return
    await page.waitForTimeout(200)
  }
  throw new Error(`missing expected text "${expected}" at ${page.url()}`)
}

async function collectUiMetrics(page) {
  return page.evaluate(() => {
    const clientWidth = document.documentElement.clientWidth
    const scrollWidth = document.documentElement.scrollWidth
    const clippedText = Array.from(document.querySelectorAll('body *'))
      .filter((node) => {
        const element = node
        const style = window.getComputedStyle(element)
        if (style.visibility === 'hidden' || style.display === 'none') return false
        const text = (element.textContent || '').trim()
        if (!text || text.length < 3) return false
        return element.scrollWidth > element.clientWidth + 2 && ['hidden', 'clip'].includes(style.overflowX)
      })
      .slice(0, 10)
      .map((node) => ({
        tag: node.tagName,
        className: String(node.className || '').slice(0, 120),
        text: (node.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120),
        clientWidth: node.clientWidth,
        scrollWidth: node.scrollWidth
      }))
    const rightOverflow = Array.from(document.querySelectorAll('body *'))
      .filter((node) => {
        const rect = node.getBoundingClientRect()
        return rect.width > 0 && rect.right > clientWidth + 2
      })
      .slice(0, 10)
      .map((node) => ({
        tag: node.tagName,
        className: String(node.className || '').slice(0, 120),
        text: (node.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120),
        right: Math.round(node.getBoundingClientRect().right),
        width: Math.round(node.getBoundingClientRect().width)
      }))
    return {
      url: window.location.href,
      title: document.title,
      clientWidth,
      scrollWidth,
      horizontalOverflowPx: Math.max(0, scrollWidth - clientWidth),
      scrollHeight: document.documentElement.scrollHeight,
      visibleTextChars: (document.body.innerText || '').length,
      clippedText,
      rightOverflow
    }
  })
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
  const logs = url.includes(String(webPort)) ? webLogs : apiLogs
  throw new Error(`server did not start: ${url} ${lastError?.message || 'timeout'}\n${logs.join('\n')}`)
}

async function stop(processHandle) {
  if (!processHandle || processHandle.killed) return
  processHandle.kill('SIGTERM')
  await Promise.race([once(processHandle, 'exit'), new Promise((resolve) => setTimeout(resolve, 1500))])
  if (!processHandle.killed) processHandle.kill('SIGKILL')
}
