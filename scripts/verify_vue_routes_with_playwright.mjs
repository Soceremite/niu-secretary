#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { fileURLToPath } from 'node:url'
import playwright from '../web/node_modules/playwright/index.js'

const { chromium } = playwright

const port = Number(process.env.NIU_SECRETARY_VUE_PREVIEW_PORT || 4174)
const base = `http://127.0.0.1:${port}/niu-secretary/`
const routes = [
  '/',
  '/admin/login',
  '/admin/fitness/nutrition',
  '/admin/schedule/events',
  '/admin/schedule/todos',
  '/admin/leisure/items',
  '/admin/news/recommendations',
  '/admin/airesearch/',
  '/admin/airesearch/queue',
  '/admin/airesearch/papers',
  '/admin/airesearch/discovery',
  '/admin/airesearch/profiles',
  '/admin/airesearch/jobs',
  '/fitness/',
  '/schedule/',
  '/leisure/',
  '/news/',
  '/airesearch/'
]
const viewports = [
  { key: 'desktop', width: 1280, height: 900 },
  { key: 'mobile', width: 390, height: 844 }
]

const viteBin = fileURLToPath(new URL('../web/node_modules/vite/bin/vite.js', import.meta.url))
const server = spawn(process.execPath, [viteBin, 'preview', '--host', '127.0.0.1', '--port', String(port)], {
  cwd: new URL('../web/', import.meta.url),
  stdio: ['ignore', 'pipe', 'pipe']
})

try {
  await waitForServer(base)
  const browser = await chromium.launch({ headless: true })
  const loaded = []
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport: { width: viewport.width, height: viewport.height } })
    for (const route of routes) {
      const routeUrl = new URL(route.replace(/^\//, ''), base).toString()
      const response = await page.goto(routeUrl, { waitUntil: 'domcontentloaded' })
      if (!response || !response.ok()) throw new Error(`route failed: ${route}`)
      await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {})
      const text = await page.locator('body').innerText({ timeout: 10000 })
      if (!text.includes('牛秘书')) throw new Error(`route missing brand text: ${route}`)
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2)
      if (overflow) throw new Error(`route has page-level horizontal overflow: ${viewport.key} ${route}`)
      loaded.push(`${viewport.key}:${route}`)
    }
    await page.close()
  }
  await browser.close()
  console.log(JSON.stringify({ ok: true, base, loaded }, null, 2))
} finally {
  server.kill('SIGTERM')
  await Promise.race([once(server, 'exit'), new Promise((resolve) => setTimeout(resolve, 1500))])
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
  throw new Error(`Vue preview did not start: ${lastError?.message || 'timeout'}`)
}
