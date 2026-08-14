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
const apiPort = Number(process.env.NIU_SECRETARY_LEISURE_SMOKE_API_PORT || 5201)
const webPort = Number(process.env.NIU_SECRETARY_LEISURE_SMOKE_WEB_PORT || 4178)
const apiBase = `http://127.0.0.1:${apiPort}/niu-secretary/api`
const webBase = `http://127.0.0.1:${webPort}/niu-secretary/`
const dbDir = await mkdtemp(join(tmpdir(), 'niu-secretary-leisure-smoke-'))
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
  await page.goto(`${webBase}leisure/`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '牛秘书闲趣集')
  await expectVisibleText(page, '闲趣集')
  await expectVisibleText(page, '今晚首推')
  await expectVisibleText(page, '今日候选')
  await expectVisibleText(page, '口味档案')
  await expectVisibleText(page, '画像建议')
  await expectVisibleText(page, '收藏')
  await expectSearchPlaceholder(page)
  await assertNoMissingChineseStaticLinks(page)
  await assertNoHorizontalOverflow(page)
  await assertActiveCategory(page, '首页')
  await assertLeisureSearch(page)

  await clickFeaturedAction(page, '收藏')
  await expectFeedbackStrip(page, '已收藏')
  await clickFeaturedAction(page, '忽略')
  await expectFeedbackStrip(page, '已忽略')

  await page.getByRole('button', { name: '查看详情' }).first().click({ force: true })
  await page.waitForSelector('.leisure-detail-sheet', { state: 'visible' })
  await expectVisibleText(page, '提交评分')
  await assertDetailSheet(page)
  await page.getByRole('button', { name: '最小化详情' }).click({ force: true })
  await page.waitForSelector('.leisure-detail-dock', { state: 'visible' })
  await expectVisibleText(page, '继续查看')
  await page.locator('.leisure-detail-dock').click({ force: true })
  await page.waitForSelector('.leisure-detail-sheet', { state: 'visible' })
  await page.getByRole('button', { name: '提交评分' }).click({ force: true })
  await expectVisibleText(page, '评分已提交')
  await expectVisibleText(page, '已写入后端画像')
  await expectVisibleText(page, '应用')
  await page.getByRole('button', { name: '应用' }).first().click({ force: true })
  await expectVisibleText(page, '画像建议已应用')

  await page.getByRole('button', { name: '影视' }).first().click({ force: true })
  await assertActiveCategory(page, '影视')
  await page.getByRole('tab', { name: '已存条目' }).click({ force: true })
  await expectSavedRow(page)

  await page.setViewportSize({ width: 390, height: 844 })
  await assertNoHorizontalOverflow(page)
  await assertLeisureMobileLayout(page)
  await page.getByRole('button', { name: '详情' }).first().click({ force: true })
  await page.waitForSelector('.leisure-detail-sheet', { state: 'visible' })
  await assertDetailSheet(page)

  console.log(JSON.stringify({ ok: true, apiBase, webBase, dbPath, route: '/leisure/' }, null, 2))
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

async function expectSavedRow(page) {
  const deadline = Date.now() + 10000
  let body = ''
  while (Date.now() < deadline) {
    body = await page.locator('body').innerText().catch(() => '')
    if (body.includes('vue-leisure')) return
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`missing saved leisure row\n${body.slice(0, 1000)}`)
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

async function assertNoMissingChineseStaticLinks(page) {
  const badLinks = await page.$$eval('a[href]', (links) =>
    links
      .map((link) => link.getAttribute('href') || '')
      .filter((href) => /影视\.html|音乐\.html|播客\.html|小说\.html|%E5%BD%B1%E8%A7%86\.html/.test(href))
  )
  if (badLinks.length) throw new Error(`unexpected missing static Chinese links: ${badLinks.join(', ')}`)
}

async function assertNoHorizontalOverflow(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  if (overflow > 2) throw new Error(`horizontal overflow: ${overflow}px`)
}

async function assertActiveCategory(page, label) {
  const isActive = await page.$$eval('.leisure-nav button', (buttons, expected) =>
    buttons.some((button) => button.textContent?.includes(expected) && button.classList.contains('active')),
    label
  )
  if (!isActive) throw new Error(`leisure category is not active: ${label}`)
}

async function expectSearchPlaceholder(page) {
  const placeholder = await page.locator('.leisure-search input').first().getAttribute('placeholder')
  if (placeholder !== '搜索片名、音乐、播客、小说') {
    throw new Error(`unexpected leisure search placeholder: ${placeholder}`)
  }
}

async function clickFeaturedAction(page, label) {
  await page.locator('.featured-choice .leisure-actions button').filter({ hasText: label }).first().click({ force: true })
}

async function expectFeedbackStrip(page, label) {
  const deadline = Date.now() + 10000
  let text = ''
  while (Date.now() < deadline) {
    text = await page.locator('.leisure-feedback-strip').innerText().catch(() => '')
    if (text.includes(label)) return
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`missing leisure feedback strip state: ${label}\n${text}`)
}

async function assertLeisureSearch(page) {
  const title = await page.locator('.feature-copy h3').first().innerText()
  const keyword = title.slice(0, Math.min(2, title.length))
  if (!keyword) throw new Error('missing leisure feature title for search smoke')
  await page.locator('.leisure-search input').fill(keyword)
  await expectVisibleText(page, title)
  await page.locator('.leisure-search input').fill('')
}

async function assertDetailSheet(page) {
  const metrics = await page.evaluate(() => {
    const sheet = document.querySelector('.leisure-detail-sheet')?.getBoundingClientRect()
    const actions = document.querySelector('.detail-actions')?.getBoundingClientRect()
    const media = document.querySelector('.detail-media')?.getBoundingClientRect()
    const controls = document.querySelector('.detail-controls')?.getBoundingClientRect()
    return {
      viewportWidth: document.documentElement.clientWidth,
      viewportHeight: document.documentElement.clientHeight,
      sheet: sheet ? { width: sheet.width, height: sheet.height, left: sheet.left, right: sheet.right, bottom: sheet.bottom } : null,
      actions: actions ? { right: actions.right } : null,
      media: media ? { width: media.width, height: media.height, left: media.left, right: media.right } : null,
      controls: controls ? { right: controls.right } : null
    }
  })
  if (!metrics.sheet) throw new Error('missing leisure detail sheet')
  if (!metrics.media || metrics.media.width < 120 || metrics.media.height < 160) {
    throw new Error(`leisure detail media is not usable: ${JSON.stringify(metrics.media)}`)
  }
  if (metrics.sheet.width > metrics.viewportWidth || metrics.sheet.right > metrics.viewportWidth + 1 || metrics.sheet.left < -1) {
    throw new Error(`leisure detail sheet overflows horizontally: ${JSON.stringify(metrics.sheet)}`)
  }
  if (metrics.sheet.height > metrics.viewportHeight * 0.9 || metrics.sheet.bottom > metrics.viewportHeight + 1) {
    throw new Error(`leisure detail sheet is not contained: ${JSON.stringify(metrics.sheet)}`)
  }
  if (metrics.actions && metrics.actions.right > metrics.viewportWidth + 1) {
    throw new Error(`leisure detail actions overflow: ${JSON.stringify(metrics.actions)}`)
  }
  if (metrics.controls && metrics.controls.right > metrics.viewportWidth + 1) {
    throw new Error(`leisure detail controls overflow: ${JSON.stringify(metrics.controls)}`)
  }
}

async function assertLeisureMobileLayout(page) {
  const metrics = await page.evaluate(() => {
    const nav = document.querySelector('.leisure-nav')?.getBoundingClientRect()
    const note = document.querySelector('.leisure-note')?.getBoundingClientRect()
    const candidates = Array.from(document.querySelectorAll('.candidate')).map((element) => {
      const rect = element.getBoundingClientRect()
      return { right: rect.right, left: rect.left }
    })
    return {
      viewportWidth: document.documentElement.clientWidth,
      nav: nav ? { right: nav.right, left: nav.left } : null,
      note: note ? { right: note.right, left: note.left } : null,
      candidates
    }
  })
  for (const [name, rect] of Object.entries({ nav: metrics.nav, note: metrics.note })) {
    if (!rect) throw new Error(`missing leisure ${name}`)
    if (rect.right > metrics.viewportWidth + 1 || rect.left < -1) {
      throw new Error(`leisure ${name} overflows mobile viewport: ${JSON.stringify(rect)}`)
    }
  }
  const overflowing = metrics.candidates.find((rect) => rect.right > metrics.viewportWidth + 1 || rect.left < -1)
  if (overflowing) throw new Error(`leisure candidate overflows mobile viewport: ${JSON.stringify(overflowing)}`)
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
