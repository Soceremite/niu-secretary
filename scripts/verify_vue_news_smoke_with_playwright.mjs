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
const apiPort = Number(process.env.NIU_SECRETARY_NEWS_SMOKE_API_PORT || 5202)
const webPort = Number(process.env.NIU_SECRETARY_NEWS_SMOKE_WEB_PORT || 4179)
const apiBase = `http://127.0.0.1:${apiPort}/niu-secretary/api`
const webBase = `http://127.0.0.1:${webPort}/niu-secretary/`
const dbDir = await mkdtemp(join(tmpdir(), 'niu-secretary-news-smoke-'))
const dbPath = join(dbDir, 'smoke.sqlite3')
const forbiddenQueueLabel = '送' + '研知库'

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
  await page.goto(`${webBase}news/`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '牛秘书新闻社')
  await expectVisibleText(page, '今日要闻')
  await expectVisibleText(page, '阅读全文')
  await expectVisibleText(page, '国内')
  await expectVisibleText(page, '国际')
  await expectVisibleText(page, '财经')
  await expectVisibleText(page, '科技')
  await expectVisibleText(page, 'AI')
  await assertNoHorizontalOverflow(page)
  await assertActiveSection(page, '全部')

  const bodyBefore = await page.locator('body').innerText()
  if (bodyBefore.includes(forbiddenQueueLabel)) throw new Error('news reader page must not expose queue-research action')

  await page.locator('.news-card').first().click({ force: true })
  await page.waitForSelector('.news-detail-panel')
  await expectVisibleText(page, '原文链接')
  await expectVisibleText(page, '原文追溯')
  await assertDetailPanel(page)
  await page.getByLabel('切换全屏详情').click({ force: true })
  await page.waitForSelector('.news-detail-panel.is-fullscreen')
  await assertDetailPanel(page)
  await page.getByLabel('缩小详情').click({ force: true })
  await page.waitForSelector('.news-detail-panel.is-minimized')
  await expectVisibleText(page, '恢复阅读')
  await page.getByLabel('关闭详情').click({ force: true })
  await page.waitForSelector('.news-detail-panel', { state: 'detached' })

  await page.locator('.news-section-tab[data-section="tech"]').click({ force: true })
  await assertActiveSection(page, '科技')
  await page.getByRole('button', { name: '搜索' }).click({ force: true })
  await expectVisibleText(page, '搜索结果')
  await page.waitForSelector('.news-search-card')
  const hasSearchTable = await page.locator('.news-search-results .el-table').count()
  if (hasSearchTable) throw new Error('news search results should render themed cards, not a raw table')
  await expectVisibleText(page, '原文')
  await page.locator('.news-search-card').first().click({ force: true })
  await page.waitForSelector('.news-detail-panel')
  await expectVisibleText(page, '原文追溯')
  await assertDetailPanel(page)
  await page.getByLabel('关闭详情').click({ force: true })
  await page.waitForSelector('.news-detail-panel', { state: 'detached' })

  await page.setViewportSize({ width: 390, height: 844 })
  await assertNoHorizontalOverflow(page)
  await assertNewsMobileLayout(page)

  console.log(JSON.stringify({ ok: true, apiBase, webBase, dbPath, route: '/news/' }, null, 2))
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
  const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth))
  if (overflow > 2) throw new Error(`news page has horizontal overflow: ${overflow}`)
}

async function assertActiveSection(page, label) {
  const isActive = await page.$$eval('.news-section-tab', (buttons, expected) =>
    buttons.some((button) => button.textContent?.includes(expected) && button.classList.contains('active')),
    label
  )
  if (!isActive) throw new Error(`news section is not active: ${label}`)
}

async function assertDetailPanel(page) {
  const metrics = await page.evaluate(() => {
    const panel = document.querySelector('.news-detail-panel')?.getBoundingClientRect()
    const body = document.querySelector('.news-detail-body')?.getBoundingClientRect()
    return {
      viewportWidth: document.documentElement.clientWidth,
      viewportHeight: document.documentElement.clientHeight,
      panel: panel ? { width: panel.width, height: panel.height, left: panel.left, right: panel.right, top: panel.top, bottom: panel.bottom } : null,
      body: body ? { width: body.width, height: body.height, right: body.right } : null
    }
  })
  if (!metrics.panel) throw new Error('missing news detail panel')
  if (metrics.panel.left < -1 || metrics.panel.right > metrics.viewportWidth + 1) {
    throw new Error(`news detail panel overflows horizontally: ${JSON.stringify(metrics.panel)}`)
  }
  if (metrics.panel.top < -1 || metrics.panel.bottom > metrics.viewportHeight + 1) {
    throw new Error(`news detail panel overflows vertically: ${JSON.stringify(metrics.panel)}`)
  }
  if (metrics.body && metrics.body.right > metrics.viewportWidth + 1) {
    throw new Error(`news detail body overflows: ${JSON.stringify(metrics.body)}`)
  }
}

async function assertNewsMobileLayout(page) {
  const metrics = await page.evaluate(() => {
    const nav = document.querySelector('.news-section-nav')?.getBoundingClientRect()
    const search = document.querySelector('.news-search')?.getBoundingClientRect()
    const firstCard = document.querySelector('.news-card')?.getBoundingClientRect()
    const cards = Array.from(document.querySelectorAll('.news-card, .news-search-card')).map((element) => {
      const rect = element.getBoundingClientRect()
      return { left: rect.left, right: rect.right }
    })
    return {
      viewportWidth: document.documentElement.clientWidth,
      viewportHeight: document.documentElement.clientHeight,
      nav: nav ? { left: nav.left, right: nav.right } : null,
      navHeight: nav?.height || 0,
      search: search ? { left: search.left, right: search.right } : null,
      firstCardTop: firstCard?.top || 0,
      cards
    }
  })
  for (const [name, rect] of Object.entries({ nav: metrics.nav, search: metrics.search })) {
    if (!rect) throw new Error(`missing news ${name}`)
    if (rect.left < -1 || rect.right > metrics.viewportWidth + 1) {
      throw new Error(`news ${name} overflows mobile viewport: ${JSON.stringify(rect)}`)
    }
  }
  if (metrics.navHeight > 280) throw new Error(`news mobile section nav is too tall: ${metrics.navHeight}`)
  if (metrics.firstCardTop > 980) throw new Error(`news first card starts too low on mobile: ${metrics.firstCardTop}`)
  const overflowingCard = metrics.cards.find((rect) => rect.left < -1 || rect.right > metrics.viewportWidth + 1)
  if (overflowingCard) throw new Error(`news card overflows mobile viewport: ${JSON.stringify(overflowingCard)}`)
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
