#!/usr/bin/env node
import playwright from '../web/node_modules/playwright/index.js'

const baseUrl = (process.env.AIRESEARCH_PUBLIC_BASE_URL || 'http://127.0.0.1/niu-secretary/airesearch').replace(/\/$/, '')
const papers = (process.env.AIRESEARCH_PUBLIC_PAPERS || 'colavla,world2vlm,world-model-self-distillation')
  .split(',')
  .map((value) => value.trim())
  .filter(Boolean)
const viewports = [
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'mobile', width: 390, height: 844 }
]

const browser = await playwright.chromium.launch({ headless: true })
const results = []

try {
  for (const viewport of viewports) {
    for (const paper of papers) {
      const page = await browser.newPage({ viewport })
      const errors = []
      page.on('pageerror', (error) => errors.push(error.message))
      await page.goto(`${baseUrl}/papers/${paper}.html`, { waitUntil: 'domcontentloaded', timeout: 30_000 })
      await page.waitForTimeout(300)

      const metrics = await page.evaluate(() => {
        const tableShells = [...document.querySelectorAll('.paper-layout-table-scroll')]
        const images = [...document.images]
          .filter((img) => img.getBoundingClientRect().width > 0)
          .map((img) => ({
            width: Math.round(img.getBoundingClientRect().width),
            height: Math.round(img.getBoundingClientRect().height),
            naturalWidth: img.naturalWidth,
            naturalHeight: img.naturalHeight
          }))
        return {
          viewportWidth: window.innerWidth,
          documentOverflow: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
          formulas: document.querySelectorAll('.paper-layout-formula').length,
          tables: document.querySelectorAll('.paper-layout-data-table').length,
          qualityBadges: document.querySelectorAll('.paper-layout-quality').length,
          tableLeaks: tableShells.filter((element) => {
            const box = element.getBoundingClientRect()
            return box.left < 0 || box.right > window.innerWidth + 1
          }).length,
          locallyScrollableTables: tableShells.filter((element) => element.scrollWidth > element.clientWidth + 1).length,
          maxImageWidth: images.length ? Math.max(...images.map((image) => image.width)) : 0,
          maxImageHeight: images.length ? Math.max(...images.map((image) => image.height)) : 0,
          unloadedImages: images.filter((image) => !image.naturalWidth).length,
          externalLinkViolations: [...document.querySelectorAll('a[href^="http"]')]
            .filter((anchor) => anchor.target !== '_blank' || !(anchor.rel || '').includes('noopener'))
            .length
        }
      })

      const result = { paper, viewport: viewport.name, errors, ...metrics }
      results.push(result)
      if (
        errors.length || metrics.documentOverflow || metrics.tableLeaks || metrics.unloadedImages ||
        metrics.externalLinkViolations || !metrics.formulas || !metrics.qualityBadges
      ) {
        throw new Error(`public paper DOM verification failed: ${JSON.stringify(result)}`)
      }
      await page.close()
    }
  }
} finally {
  await browser.close()
}

console.log(JSON.stringify({ ok: true, baseUrl, results }, null, 2))
