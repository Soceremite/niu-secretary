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
const apiPort = Number(process.env.NIU_SECRETARY_FITNESS_SMOKE_API_PORT || 5199)
const webPort = Number(process.env.NIU_SECRETARY_FITNESS_SMOKE_WEB_PORT || 4176)
const apiBase = `http://127.0.0.1:${apiPort}/niu-secretary/api`
const webBase = `http://127.0.0.1:${webPort}/niu-secretary/`
const dbDir = await mkdtemp(join(tmpdir(), 'niu-secretary-fitness-smoke-'))
const dbPath = join(dbDir, 'smoke.sqlite3')
const today = '2026-06-16'

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
const browserErrors = []
const networkEvents = []

try {
  await waitForServer(`${apiBase}/health`)
  await waitForServer(webBase)
  await seedFitnessData()

  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  page.on('console', (message) => {
    browserErrors.push(`${message.type()}: ${message.text()}`)
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))
  page.on('requestfailed', (request) => {
    networkEvents.push({ type: 'failed', url: request.url(), error: request.failure()?.errorText || '' })
  })
  page.on('response', async (response) => {
    const url = response.url()
    if (!url.includes('/niu-secretary/api/fitness/')) return
    const event = { type: 'response', url, status: response.status(), body: '' }
    event.body = (await response.text().catch(() => '')).slice(0, 500)
    networkEvents.push(event)
  })
  await page.goto(`${webBase}fitness/`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '牛秘书塑形馆')
  await expectVisibleText(page, '今日摄入')
  await expectVisibleText(page, '趋势总览')
  await expectVisibleText(page, 'Smoke 牛奶')
  await expectVisibleText(page, 'Smoke 力量训练')
  await assertPairedPanelsAligned(page, '.dashboard-pair-nutrition .paired-card')
  await assertPairedPanelsAligned(page, '.dashboard-pair-trends .paired-card')
  await assertFitnessCardContrast(page)
  await assertNutritionTextFits(page)
  await assertNoHorizontalOverflow(page)

  await page.locator('.module-nav .nav-chip', { hasText: '恢复' }).click({ force: true })
  await expectVisibleText(page, '恢复趋势')

  await page.locator('.module-nav .nav-chip', { hasText: '营养' }).click({ force: true })
  await expectVisibleText(page, '拍照记一餐')
  await page.locator('input[placeholder="红烧肉、米饭、奶茶"]').fill('Smoke 鸡蛋')
  await page.getByRole('button', { name: '保存饮食' }).click({ force: true })
  await expectVisibleText(page, 'Smoke 鸡蛋')
  await page.locator('.fitness-operation-feedback.success').waitFor({ state: 'visible', timeout: 10000 })

  await page.locator('.module-nav .nav-chip', { hasText: '评估' }).click({ force: true })
  await expectVisibleText(page, '基础信息')
  await assertSingleAssessmentSection(page, 'baseline')
  await page.locator('[data-assessment-section-target="fms"]').click({ force: true })
  await expectVisibleText(page, 'FMS 动作评分')
  await assertSingleAssessmentSection(page, 'fms')
  await page.locator('[data-assessment-section-target="posture"]').click({ force: true })
  await expectVisibleText(page, '体态观察')
  await assertSingleAssessmentSection(page, 'posture')

  await page.locator('.module-nav .nav-chip', { hasText: '咨询' }).click({ force: true })
  await expectVisibleText(page, '身体问题咨询')
  await assertNoHorizontalOverflow(page)

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`${webBase}fitness/`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '牛秘书塑形馆')
  await expectVisibleText(page, '身体账本')
  await page.locator('.module-nav .nav-chip', { hasText: '总览' }).click({ force: true })
  await expectVisibleText(page, '今日营养')
  await assertNoHorizontalOverflow(page)
  await assertFitnessMobileLayout(page)

  console.log(JSON.stringify({ ok: true, apiBase, webBase, dbPath, route: '/fitness/' }, null, 2))
} catch (error) {
  if (browser) {
    const pages = browser.contexts().flatMap((context) => context.pages())
    const page = pages[0]
    if (page) {
      const text = await page.locator('body').innerText().catch(() => '')
      const html = await page.locator('body').evaluate((node) => node.innerHTML).catch(() => '')
      console.error(JSON.stringify({ url: page.url(), body: text.slice(0, 1000), html: html.slice(0, 1000), browserErrors, networkEvents }, null, 2))
    }
  }
  throw error
} finally {
  if (browser) await browser.close()
  await stop(api)
  await stop(web)
}

async function seedFitnessData() {
  await action('fitness.nutrition.create', {
    food: 'Smoke 牛奶',
    date: today,
    calories: 120,
    proteinG: 8,
    carbsG: 12,
    fatG: 4,
    source: 'vue-fitness-smoke'
  })
  await action('fitness.workout.create', {
    name: 'Smoke 力量训练',
    date: today,
    durationMin: 45,
    intensity: 'medium',
    calories: 260,
    source: 'vue-fitness-smoke'
  })
  await action('fitness.body_metric.create', {
    date: today,
    weightKg: 72.4,
    bodyFatPct: 18.5,
    waistCm: 82,
    source: 'vue-fitness-smoke'
  })
  await action('fitness.recovery.create', {
    date: today,
    sleepHours: 7,
    sleepQuality: 4,
    stress: 2,
    soreness: 2,
    lastRpe: 7,
    score: 76,
    statusLabel: '绿色',
    statusAdvice: '恢复良好，可以按计划训练。',
    source: 'vue-fitness-smoke'
  })
}

async function action(actionName, input) {
  return postJson(`${apiBase}/actions/execute`, {
    action: actionName,
    input,
    context: { client: 'vue-fitness-smoke', confirmed: true }
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
  let lastNonEmptyBody = ''
  while (Date.now() < deadline) {
    body = await page.locator('body').innerText().catch(() => '')
    if (body.trim()) lastNonEmptyBody = body
    if (body.includes(text)) return
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`missing text: ${text}\n${body.slice(0, 1000)}\nlast non-empty body:\n${lastNonEmptyBody.slice(0, 1000)}`)
}

async function assertPairedPanelsAligned(page, selector) {
  const heights = await page.locator(selector).evaluateAll((nodes) => nodes.map((node) => Math.round(node.getBoundingClientRect().height)))
  if (heights.length < 2) throw new Error(`expected paired panels for ${selector}`)
  const delta = Math.max(...heights) - Math.min(...heights)
  if (delta > 2) throw new Error(`panel height mismatch for ${selector}: ${heights.join(', ')}`)
}

async function assertFitnessCardContrast(page) {
  const result = await page.locator('.dashboard-grid .priority-card .glass-card-inner').first().evaluate((card) => {
    const text = card.querySelector('h2, h3, strong')
    const parse = (value) => (value.match(/[\d.]+/g) || []).slice(0, 3).map(Number)
    const luminance = (rgb) => {
      const channels = rgb.map((channel) => {
        const value = channel / 255
        return value <= .03928 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4
      })
      return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2]
    }
    const background = parse(getComputedStyle(card).backgroundColor)
    const foreground = parse(getComputedStyle(text).color)
    const light = Math.max(luminance(background), luminance(foreground))
    const dark = Math.min(luminance(background), luminance(foreground))
    return { background, foreground, contrast: (light + .05) / (dark + .05) }
  })
  if (result.contrast < 4.5) throw new Error(`fitness card contrast is too low: ${JSON.stringify(result)}`)
}

async function assertNutritionTextFits(page) {
  const overflow = await page.locator('.target-row b').evaluateAll((nodes) => nodes
    .filter((node) => node.scrollWidth > node.clientWidth + 2)
    .map((node) => ({ text: node.textContent, clientWidth: node.clientWidth, scrollWidth: node.scrollWidth })))
  if (overflow.length) throw new Error(`nutrition values overflow: ${JSON.stringify(overflow)}`)
}

async function assertSingleAssessmentSection(page, expected) {
  const visible = await page.locator('[data-assessment-section]').evaluateAll((nodes) => nodes
    .filter((node) => getComputedStyle(node).display !== 'none')
    .map((node) => node.getAttribute('data-assessment-section')))
  if (visible.length !== 1 || visible[0] !== expected) {
    throw new Error(`assessment should show only ${expected}: ${JSON.stringify(visible)}`)
  }
  const current = await page.locator('[data-assessment-section-target][aria-current="step"]').getAttribute('data-assessment-section-target')
  if (current !== expected) throw new Error(`assessment navigation current step mismatch: expected ${expected}, got ${current}`)
}

async function assertNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => {
    const documentWidth = document.documentElement.clientWidth
    const bodyOverflow = document.documentElement.scrollWidth - documentWidth
    const offenders = Array.from(document.querySelectorAll('body *'))
      .filter((node) => {
        const element = node
        const rect = element.getBoundingClientRect()
        return rect.width > 0 && rect.right > documentWidth + 2
      })
      .slice(0, 8)
      .map((node) => ({
        tag: node.tagName,
        className: node.className,
        text: (node.textContent || '').trim().slice(0, 80),
        right: Math.round(node.getBoundingClientRect().right),
        width: Math.round(node.getBoundingClientRect().width)
      }))
    return { bodyOverflow, offenders }
  })
  if (overflow.bodyOverflow > 2 || overflow.offenders.length) {
    throw new Error(`fitness page has horizontal overflow: ${JSON.stringify(overflow)}`)
  }
}

async function assertFitnessMobileLayout(page) {
  const metrics = await page.evaluate(() => {
    const nav = document.querySelector('.fitness-topbar .module-nav')
    const heroMetrics = Array.from(document.querySelectorAll('.hero-metric')).map((node) => {
      const rect = node.getBoundingClientRect()
      return { width: Math.round(rect.width), left: Math.round(rect.left), right: Math.round(rect.right) }
    })
    const targetRows = Array.from(document.querySelectorAll('.target-row')).map((node) => {
      const styles = window.getComputedStyle(node)
      return styles.gridTemplateColumns
    })
    return {
      navScrollWidth: nav?.scrollWidth || 0,
      navClientWidth: nav?.clientWidth || 0,
      heroMetrics,
      targetRows
    }
  })
  if (metrics.navScrollWidth > metrics.navClientWidth + 2) {
    throw new Error(`mobile module nav overflows instead of fitting or controlled scrolling: ${JSON.stringify(metrics)}`)
  }
  if (metrics.heroMetrics.length < 4) throw new Error(`expected four hero metrics on mobile: ${JSON.stringify(metrics)}`)
  if (metrics.heroMetrics.some((metric) => metric.right > 392 || metric.left < -2)) {
    throw new Error(`mobile hero metrics escape viewport: ${JSON.stringify(metrics.heroMetrics)}`)
  }
  if (metrics.targetRows.some((columns) => columns.split(' ').length > 3)) {
    throw new Error(`mobile nutrition target rows are too dense: ${JSON.stringify(metrics.targetRows)}`)
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
