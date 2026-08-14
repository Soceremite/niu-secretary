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
const apiPort = Number(process.env.NIU_SECRETARY_AIRESEARCH_SMOKE_API_PORT || 5203)
const webPort = Number(process.env.NIU_SECRETARY_AIRESEARCH_SMOKE_WEB_PORT || 4180)
const apiBase = `http://127.0.0.1:${apiPort}/niu-secretary/api`
const webBase = `http://127.0.0.1:${webPort}/niu-secretary/`
const dbDir = await mkdtemp(join(tmpdir(), 'niu-secretary-airesearch-smoke-'))
const dbPath = join(dbDir, 'smoke.sqlite3')

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

  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  await page.goto(`${webBase}airesearch/`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '牛秘书研知库')
  await expectVisibleText(page, 'AIResearch 研知库')
  await expectVisibleText(page, '论文搜索')
  await expectVisibleText(page, '最新论文')
  await expectVisibleText(page, '主题聚类')
  await expectVisibleText(page, '研究报告')
  await expectVisibleText(page, '论文索引')
  await expectVisibleText(page, '公共页展示可读索引和报告入口')
  await assertNoLegacyEnglishNav(page)
  await assertPublicResearchNav(page)
  await assertNoHorizontalOverflow(page)

  await page.getByRole('tab', { name: '论文搜索' }).click({ force: true })
  await page.locator('.research-search-panel .el-button').click({ force: true })
  await expectVisibleText(page, '论文检索')
  await expectVisibleText(page, '已返回')
  const rawPaperTableCount = await page.locator('.research-compact-table').count()
  if (rawPaperTableCount) throw new Error('AIResearch public paper search should use research cards, not a raw table')
  await assertResearchCards(page)
  await assertNoHorizontalOverflow(page)

  await page.getByRole('tab', { name: '新增候选' }).click({ force: true })
  await expectVisibleText(page, '提交预览')
  await page.locator('input[placeholder="例如：Agent memory benchmark"]').fill('Smoke 研究主题')
  await page.getByRole('button', { name: '加入队列' }).click({ force: true })
  await expectVisibleText(page, '已加入研知库候选队列')
  await page.getByRole('tab', { name: '候选评审' }).click({ force: true })
  await expectVisibleText(page, 'Smoke 研究主题')
  await page.waitForSelector('.research-candidate-card')
  await assertNoHorizontalOverflow(page)

  await page.setViewportSize({ width: 390, height: 844 })
  await assertNoHorizontalOverflow(page)
  await assertResearchMobileLayout(page)

  console.log(JSON.stringify({ ok: true, apiBase, webBase, dbPath, route: '/airesearch/' }, null, 2))
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
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  if (overflow > 2) throw new Error(`horizontal overflow: ${overflow}px`)
}

async function assertNoLegacyEnglishNav(page) {
  const navText = await page.locator('.research-topbar nav').innerText()
  for (const word of ['Dashboard', 'Papers', 'Digest', 'Clusters', 'Gaps']) {
    if (navText.includes(word)) throw new Error(`AIResearch public nav still exposes legacy English/Admin label: ${word}`)
  }
}

async function assertPublicResearchNav(page) {
  const labels = await page.locator('.research-topbar nav button').evaluateAll((buttons) => buttons.map((button) => button.textContent?.trim()))
  const expected = ['总览', '论文搜索', '候选评审', '新增候选']
  for (const label of expected) {
    if (!labels.includes(label)) throw new Error(`missing public AIResearch nav label: ${label}`)
  }
  const staticHrefCount = await page.locator('.research-topbar nav a[href*="index.html"], .research-topbar nav a[href*="/admin/"]').count()
  if (staticHrefCount) throw new Error('AIResearch public top nav should switch Vue sections instead of linking to static/admin pages')
}

async function assertResearchCards(page) {
  const cardCount = await page.locator('.research-paper-card').count()
  if (cardCount < 1) throw new Error('AIResearch public paper search did not render card-based results')
  const malformed = await page.locator('.research-paper-card').evaluateAll((cards) => cards.some((card) => {
    const rect = card.getBoundingClientRect()
    if (rect.width === 0 || rect.height === 0) return false
    const cover = card.querySelector('.paper-cover')?.getBoundingClientRect()
    const kicker = card.querySelector('.paper-card-kicker')
    return rect.height < 92 || !cover || cover.width < 80 || !kicker
  }))
  if (malformed) throw new Error('AIResearch paper cards are missing cover/kicker structure or have collapsed sizing')
}

async function assertResearchMobileLayout(page) {
  const metrics = await page.evaluate(() => {
    const nav = document.querySelector('.research-topbar nav')?.getBoundingClientRect()
    const actions = document.querySelector('.research-topbar-actions')?.getBoundingClientRect()
    const portalMap = document.querySelector('.research-portal-map')?.getBoundingClientRect()
    const metricsGrid = document.querySelector('.research-metrics')?.getBoundingClientRect()
    const cards = Array.from(document.querySelectorAll('.research-paper-card, .research-candidate-card')).map((element) => {
      const rect = element.getBoundingClientRect()
      return { left: rect.left, right: rect.right }
    })
    return {
      viewportWidth: document.documentElement.clientWidth,
      nav: nav ? { left: nav.left, right: nav.right } : null,
      actions: actions ? { left: actions.left, right: actions.right } : null,
      portalMap: portalMap ? { left: portalMap.left, right: portalMap.right, height: portalMap.height } : null,
      metricsGrid: metricsGrid ? { left: metricsGrid.left, right: metricsGrid.right, height: metricsGrid.height } : null,
      cards
    }
  })
  for (const [name, rect] of Object.entries({ nav: metrics.nav, actions: metrics.actions, portalMap: metrics.portalMap, metricsGrid: metrics.metricsGrid })) {
    if (!rect) throw new Error(`missing AIResearch ${name}`)
    if (rect.left < -1 || rect.right > metrics.viewportWidth + 1) {
      throw new Error(`AIResearch ${name} overflows mobile viewport: ${JSON.stringify(rect)}`)
    }
  }
  if (metrics.portalMap.height > 270) throw new Error(`AIResearch mobile portal map is too tall: ${metrics.portalMap.height}px`)
  if (metrics.metricsGrid.height > 260) throw new Error(`AIResearch mobile metric grid is too tall: ${metrics.metricsGrid.height}px`)
  const overflowingCard = metrics.cards.find((rect) => rect.left < -1 || rect.right > metrics.viewportWidth + 1)
  if (overflowingCard) throw new Error(`AIResearch card overflows mobile viewport: ${JSON.stringify(overflowingCard)}`)
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
