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
const apiPort = Number(process.env.NIU_SECRETARY_HOME_SMOKE_API_PORT || 5206)
const webPort = Number(process.env.NIU_SECRETARY_HOME_SMOKE_WEB_PORT || 4183)
const apiBase = `http://127.0.0.1:${apiPort}/niu-secretary/api`
const webBase = `http://127.0.0.1:${webPort}/niu-secretary/`
const dbDir = await mkdtemp(join(tmpdir(), 'niu-secretary-home-smoke-'))
const dbPath = join(dbDir, 'smoke.sqlite3')
const mealPrompt = '我今天中午吃了牛肉面和瑞幸的橙C美式'

const api = spawn('python3', ['-m', 'server.niu_secretary_api'], {
  cwd: projectRoot,
  env: {
    ...process.env,
    NIU_SECRETARY_API_PORT: String(apiPort),
    NIU_SECRETARY_DB_PATH: dbPath,
    NIU_ASSISTANT_API_KEY: '',
    VOLCENGINE_API_KEY: ''
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

  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1366, height: 920 } })
  await page.goto(webBase, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '牛秘书')
  await expectVisibleText(page, '你私人 AI 管家')
  await expectVisibleText(page, '开始识别一句话')
  await expectVisibleText(page, '营养日志')
  await expectVisibleText(page, '五个板块')
  await expectVisibleText(page, '平台运行')
  await page.locator('#home-assistant').waitFor({ state: 'visible', timeout: 10000 })
  const moduleIcons = await page.locator('.module-card-icon').count()
  if (moduleIcons !== 5) throw new Error(`expected five module icons, got ${moduleIcons}`)

  await page.locator('.assistant-composer input').fill(mealPrompt)
  await page.locator('.assistant-composer button').click({ force: true })
  await page.waitForSelector('.action-card', { timeout: 15000 })
  await expectVisibleText(page, '写入：塑形馆/营养日志')

  const actionCards = await page.locator('.action-card').count()
  const nutritionCards = await page.locator('.action-card', { hasText: '写入：塑形馆/营养日志' }).count()
  if (nutritionCards !== 1) throw new Error(`expected one nutrition action card, got ${nutritionCards}`)
  await assertUniqueActionCards(page)
  await assertModuleCtaAlignment(page)

  await page.locator('.assistant-actions button', { hasText: '确认全部执行' }).click({ force: true })
  await expectVisibleText(page, '已完成')
  await expectVisibleText(page, '已记录到塑形馆营养')

  const nutritionResponse = await fetch(`${apiBase}/fitness/nutrition?limit=20`)
  const nutrition = await nutritionResponse.json()
  const found = (nutrition.items || []).some((item) => String(item.food || '').includes('牛肉面'))
  if (!found) throw new Error(`nutrition log not found after assistant execution: ${JSON.stringify(nutrition).slice(0, 500)}`)

  const assistantPattern = '**/niu-secretary/api/assistant/message'
  const duplicateAction = {
    action: 'fitness.nutrition.create',
    title: '写入：塑形馆/营养日志',
    input: { food: '去重验收餐', calories: 320, protein_g: 18 }
  }
  await page.route(assistantPattern, (route) => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      ok: true,
      module: 'fitness',
      reply: '已生成营养动作。',
      proposedActions: [duplicateAction, { ...duplicateAction, input: { protein_g: 18, calories: 320, food: '去重验收餐' } }]
    })
  }))
  await page.locator('.assistant-composer input').fill('去重测试')
  await page.locator('.assistant-composer button').click()
  await page.waitForSelector('.assistant-feedback.info', { timeout: 10000 })
  if (await page.locator('.action-card').count() !== 1) throw new Error('duplicate assistant actions were not merged')
  await assertUniqueActionCards(page)
  await page.unroute(assistantPattern)

  await page.route(assistantPattern, (route) => route.fulfill({
    status: 503,
    contentType: 'application/json',
    body: JSON.stringify({ ok: false, message: 'AI 服务暂时不可用' })
  }))
  await page.locator('.assistant-composer input').fill('失败反馈测试')
  await page.locator('.assistant-composer button').click()
  await page.waitForSelector('.assistant-feedback.error', { timeout: 10000 })
  await assertAssistantFeedbackPlacement(page)
  await page.unroute(assistantPattern)

  const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth))
  if (overflow > 1) throw new Error(`home page has horizontal overflow: ${overflow}`)
  await assertNoClippedHomeText(page)

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } })
  await mobile.goto(webBase, { waitUntil: 'networkidle' })
  await assertNoPageOverflow(mobile, 'mobile home')
  await assertNoClippedHomeText(mobile)
  const mobileModuleCards = await mobile.locator('.home-service-card').count()
  if (mobileModuleCards !== 5) throw new Error(`expected five mobile module cards, got ${mobileModuleCards}`)
  await mobile.close()

  console.log(JSON.stringify({ ok: true, apiBase, webBase, dbPath, actionCards, nutritionCards }, null, 2))
} catch (error) {
  if (browser) {
    const pages = browser.contexts().flatMap((context) => context.pages())
    const page = pages[0]
    if (page) {
      const text = await page.locator('body').innerText().catch(() => '')
      console.error(JSON.stringify({ url: page.url(), body: text.slice(0, 1200) }, null, 2))
    }
  }
  throw error
} finally {
  if (browser) await browser.close()
  await stop(api)
  await stop(web)
}

async function expectVisibleText(page, text) {
  const deadline = Date.now() + 15000
  let body = ''
  while (Date.now() < deadline) {
    body = await page.locator('body').innerText().catch(() => '')
    if (body.includes(text)) return
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`missing text: ${text}\n${body.slice(0, 1000)}`)
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

async function assertNoClippedHomeText(page) {
  const clipped = await page.evaluate(() => Array.from(document.querySelectorAll('.home-brand-shell *'))
    .filter((node) => {
      const element = node
      const style = window.getComputedStyle(element)
      if (style.visibility === 'hidden' || style.display === 'none') return false
      const text = (element.textContent || '').trim()
      if (!text || text.length < 3) return false
      return element.scrollWidth > element.clientWidth + 2 && ['hidden', 'clip'].includes(style.overflowX)
    })
    .slice(0, 8)
    .map((node) => ({
      tag: node.tagName,
      className: String(node.className || '').slice(0, 100),
      text: (node.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 120),
      clientWidth: node.clientWidth,
      scrollWidth: node.scrollWidth
    })))
  if (clipped.length) throw new Error(`home page has clipped text: ${JSON.stringify(clipped)}`)
}

async function assertUniqueActionCards(page) {
  const keys = await page.locator('.action-card').evaluateAll((cards) => cards.map((card) => card.getAttribute('data-action-key')))
  if (keys.some((key) => !key)) throw new Error(`action card missing identity: ${JSON.stringify(keys)}`)
  if (new Set(keys).size !== keys.length) throw new Error(`duplicate action identities rendered: ${JSON.stringify(keys)}`)
}

async function assertModuleCtaAlignment(page) {
  const rows = await page.locator('.home-service-card').evaluateAll((cards) => {
    const grouped = new Map()
    for (const card of cards) {
      const cardRect = card.getBoundingClientRect()
      const ctaRect = card.querySelector('.module-card-cta')?.getBoundingClientRect()
      const rowKey = Math.round(cardRect.top / 8) * 8
      const bottoms = grouped.get(rowKey) || []
      if (ctaRect) bottoms.push(ctaRect.bottom)
      grouped.set(rowKey, bottoms)
    }
    return Array.from(grouped.values()).filter((bottoms) => bottoms.length > 1)
  })
  for (const bottoms of rows) {
    if (Math.max(...bottoms) - Math.min(...bottoms) > 3) {
      throw new Error(`module card CTAs are not aligned: ${JSON.stringify(bottoms)}`)
    }
  }
}

async function assertAssistantFeedbackPlacement(page) {
  const feedback = page.locator('.assistant-feedback.error')
  await feedback.scrollIntoViewIfNeeded()
  const placement = await feedback.evaluate((element) => {
    const rect = element.getBoundingClientRect()
    const panel = element.closest('.assistant-panel-inner')?.getBoundingClientRect()
    return {
      top: rect.top,
      bottom: rect.bottom,
      left: rect.left,
      right: rect.right,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight,
      panel: panel ? { left: panel.left, right: panel.right, top: panel.top, bottom: panel.bottom } : null
    }
  })
  if (!placement.panel) throw new Error('assistant feedback is outside the assistant panel')
  if (placement.left < placement.panel.left - 1 || placement.right > placement.panel.right + 1) {
    throw new Error(`assistant feedback escapes panel: ${JSON.stringify(placement)}`)
  }
  if (placement.top < 0 || placement.bottom > placement.viewportHeight) {
    throw new Error(`assistant feedback is not visible in viewport: ${JSON.stringify(placement)}`)
  }
}

async function assertNoPageOverflow(page, label) {
  const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth))
  if (overflow > 1) throw new Error(`${label} has horizontal overflow: ${overflow}`)
}

async function stop(child) {
  if (child.exitCode !== null || child.signalCode !== null) return
  child.kill('SIGTERM')
  await Promise.race([once(child, 'exit'), new Promise((resolve) => setTimeout(resolve, 1500))])
  if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL')
}
