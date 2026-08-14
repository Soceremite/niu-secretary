#!/usr/bin/env node
import { mkdir, mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { fileURLToPath } from 'node:url'
import playwright from '../web/node_modules/playwright/index.js'

const { chromium } = playwright

const projectRoot = new URL('../', import.meta.url)
const apiPort = Number(process.env.NIU_SECRETARY_ADMIN_SMOKE_API_PORT || 5198)
const webPort = Number(process.env.NIU_SECRETARY_ADMIN_SMOKE_WEB_PORT || 4175)
const adminPassword = 'niu-secretary-smoke-password'
const apiBase = `http://127.0.0.1:${apiPort}/niu-secretary/api`
const webBase = `http://127.0.0.1:${webPort}/niu-secretary/`
const dbDir = await mkdtemp(join(tmpdir(), 'niu-secretary-admin-smoke-'))
const dbPath = join(dbDir, 'smoke.sqlite3')
const smokeProfileName = `smoke_profile_vue_${process.pid}`
const smokeDate = new Date().toISOString().slice(0, 10)
const screenshotDir = process.env.ADMIN_SMOKE_SCREENSHOT_DIR || ''

const api = spawn('python3', ['-m', 'server.niu_secretary_api'], {
  cwd: projectRoot,
  env: {
    ...process.env,
    NIU_SECRETARY_API_PORT: String(apiPort),
    NIU_SECRETARY_DB_PATH: dbPath,
    NIU_SECRETARY_ADMIN_USER: 'admin',
    NIU_SECRETARY_ADMIN_PASSWORD: adminPassword,
    NIU_SECRETARY_ADMIN_SESSION_SECRET: 'niu-secretary-smoke-session'
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

  const login = await postJson(`${apiBase}/admin/session`, { username: 'admin', password: adminPassword })
  const token = login.token
  await seedAdminData(token)

  browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } })
  await page.goto(`${webBase}admin/fitness/nutrition`, { waitUntil: 'networkidle' })
  await page.locator('input[autocomplete="username"]').fill('admin')
  await page.locator('input[autocomplete="current-password"]').fill('wrong-password')
  await page.getByRole('button', { name: '登录' }).click({ force: true, timeout: 5000 })
  await expectVisibleText(page, '用户名或密码错误')
  await page.locator('.admin-login-alert').waitFor({ state: 'visible', timeout: 5000 })
  await assertLoginErrorPlacement(page)
  const loginNotifications = await page.locator('.admin-feedback-notification').count()
  if (loginNotifications) throw new Error('login failure still uses global notification instead of inline form alert')
  await page.locator('input[autocomplete="current-password"]').fill(adminPassword)
  await page.getByRole('button', { name: '登录' }).click({ force: true, timeout: 5000 })
  await expectVisibleText(page, '营养日志')
  await waitForAdminIdle(page)
  await assertAdminShellPolished(page)
  await assertSidebarGroups(page)
  await expectVisibleText(page, 'Smoke 牛奶')
  await expectVisibleText(page, '筛选')
  await expectVisibleText(page, '显示')
  await exerciseNutritionCrud(page)
  await exerciseScheduleEditLayout(page)

  const checks = [
    ['/admin/', '运营总览', 'research queue: Smoke 研究主题'],
    ['/admin/schedule/events', '日程', 'Smoke 站会'],
    ['/admin/schedule/todos', '待办', 'Smoke 待办'],
    ['/admin/leisure/items', '闲趣条目', 'Smoke 电影'],
    ['/admin/airesearch/', '研知库总览', '研知库运行总览'],
    ['/admin/airesearch/queue', '研知库总览', '研知库运行总览'],
    ['/admin/airesearch/papers', '论文管理', '研究事实'],
    ['/admin/airesearch/blogs', '博客生成', '待解读论文'],
    ['/admin/airesearch/discovery', '搜索入库', '启动搜索入库任务'],
    ['/admin/airesearch/profiles', '搜索配置', '新增配置'],
    ['/admin/airesearch/review', '论文管理', '研究事实'],
    ['/admin/airesearch/pipeline', '重建部署', '重建并部署'],
    ['/admin/airesearch/publish', '重建部署', '加入发布队列'],
    ['/admin/airesearch/jobs', '任务中心', '任务队列'],
    ['/admin/airesearch/tasks', '任务中心', '任务队列']
  ]
  const loaded = ['/admin/fitness/nutrition']
  for (const [route, title, text] of checks) {
    await page.goto(new URL(route.replace(/^\//, ''), webBase).toString(), { waitUntil: 'networkidle' })
    await expectVisibleText(page, title)
    await waitForAdminIdle(page)
    await assertAdminShellPolished(page)
    await expectVisibleText(page, text)
    if (route === '/admin/schedule/events' || route === '/admin/schedule/todos') await assertFixedAdminTable(page, route)
    if (route === '/admin/airesearch/papers') {
      await assertPaperEditorSplit(page)
      await expectVisibleText(page, '前往博客生成')
      if (await page.getByRole('button', { name: '生成深度解读' }).count()) throw new Error('paper editor still contains blog generation controls')
    }
    if (route === '/admin/airesearch/discovery') await assertNoHorizontalOverflow(page, 'airesearch discovery')
    if (route === '/admin/airesearch/profiles') await exerciseAIResearchProfileCrud(page)
    if (route === '/admin/airesearch/publish') await assertAdminConfirmStyle(page)
    loaded.push(route)
  }
  await exerciseAIResearchBlogStatusContract(page)
  await assertMobileAdminLayout(page)

  console.log(JSON.stringify({ ok: true, apiBase, webBase, dbPath, loaded, crud: 'fitness.nutrition.create-update-delete', paperBlogStatus: 'completed-and-publish-failed' }, null, 2))
} catch (error) {
  if (browser) {
    const pages = browser.contexts().flatMap((context) => context.pages())
    const page = pages[0]
    if (page) {
      const text = await page.locator('body').innerText().catch(() => '')
      console.error(JSON.stringify({ url: page.url(), body: text.slice(0, 800) }, null, 2))
    }
  }
  throw error
} finally {
  if (browser) await browser.close()
  await stop(api)
  await stop(web)
}

async function seedAdminData(token) {
  await adminAction(token, 'fitness.nutrition.create', {
    food: 'Smoke 牛奶',
    date: smokeDate,
    calories: 120,
    proteinG: 8,
    source: 'vue-admin-smoke'
  })
  await adminAction(token, 'schedule.event.create', {
    title: 'Smoke 站会',
    date: smokeDate,
    time: '09:30',
    source: 'vue-admin-smoke'
  })
  await adminAction(token, 'schedule.todo.create', {
    title: 'Smoke 待办',
    date: smokeDate,
    priority: 'high',
    source: 'vue-admin-smoke'
  })
  await adminAction(token, 'leisure.item.save', {
    itemId: 'smoke-movie-001',
    category: 'movie',
    title: 'Smoke 电影',
    source: 'vue-admin-smoke'
  })
  await adminAction(token, 'airesearch.queue.add', {
    title: 'Smoke 研究主题',
    note: 'Vue admin smoke test',
    source: 'vue-admin-smoke'
  })
}

async function adminAction(token, action, input) {
  return postJson(`${apiBase}/admin/actions/execute`, {
    action,
    input,
    context: { confirmed: true }
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

async function expectVisibleText(page, text) {
  const deadline = Date.now() + 10000
  while (Date.now() < deadline) {
    const matches = await page.getByText(text, { exact: false }).all()
    for (const match of matches) {
      if (await match.isVisible().catch(() => false)) return
    }
    await new Promise((resolve) => setTimeout(resolve, 150))
  }
  await page.getByText(text, { exact: false }).first().waitFor({ state: 'visible', timeout: 1 })
}

async function exerciseNutritionCrud(page) {
  await page.getByRole('button', { name: '新增' }).first().click({ force: true })
  await expectVisibleText(page, '新增记录')
  await fillDialogInput(page, '食物', 'Smoke CRUD 酸奶')
  await fillDialogInput(page, '热量', '160')
  await fillDialogInput(page, '蛋白 g', '10')
  await page.locator('.el-dialog').getByRole('button', { name: '保存' }).click({ force: true })
  await page.locator('.el-dialog').waitFor({ state: 'hidden', timeout: 10000 })
  await assertInlineAdminFeedback(page, '保存成功')
  await waitForAdminIdle(page)
  await expectVisibleText(page, 'Smoke CRUD 酸奶')

  await page.getByRole('button', { name: '编辑' }).first().click({ force: true })
  await expectVisibleText(page, '编辑记录')
  await fillDialogInput(page, '食物', 'Smoke CRUD 酸奶 已编辑')
  await page.locator('.el-dialog').getByRole('button', { name: '保存' }).click({ force: true })
  await page.locator('.el-dialog').waitFor({ state: 'hidden', timeout: 10000 })
  await assertInlineAdminFeedback(page, '保存成功')
  await waitForAdminIdle(page)
  await expectVisibleText(page, 'Smoke CRUD 酸奶 已编辑')

  await page.getByRole('button', { name: '详情' }).first().click({ force: true })
  await expectVisibleText(page, '记录详情')
  await page.getByRole('button', { name: '关闭详情' }).click({ force: true })
  await page.locator('.el-drawer').waitFor({ state: 'hidden', timeout: 10000 })
  await page.getByRole('button', { name: '删除' }).first().click({ force: true })
  await expectVisibleText(page, '确认删除这条记录？')
  await page.getByRole('button', { name: '确认' }).click({ force: true })
  await waitForAdminIdle(page)
  await page.getByText('Smoke CRUD 酸奶 已编辑', { exact: false }).waitFor({ state: 'detached', timeout: 10000 })
}

async function exerciseScheduleEditLayout(page) {
  await page.goto(`${webBase}admin/schedule/events`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, 'Smoke 站会')
  await waitForAdminIdle(page)
  await assertFixedAdminTable(page, '/admin/schedule/events')
  await assertNoHorizontalOverflow(page, 'schedule events before edit')
  await page.getByRole('button', { name: '编辑' }).first().click({ force: true })
  await expectVisibleText(page, '编辑记录')
  await assertNoHorizontalOverflow(page, 'schedule events edit dialog')
  await page.locator('.el-dialog').getByRole('button', { name: '取消' }).click({ force: true })
  await page.locator('.el-dialog').waitFor({ state: 'hidden', timeout: 10000 })
}

async function exerciseAIResearchProfileCrud(page) {
  await assertNoHorizontalOverflow(page, 'airesearch profiles before crud')
  await cleanupSmokeProfile(page)
  await page.getByRole('button', { name: '新增配置' }).click({ force: true })
  await expectVisibleText(page, '新增搜索配置')
  await fillDialogInput(page, '方向 Key', smokeProfileName)
  await fillDialogInput(page, '描述', 'Smoke Vue 搜索配置')
  await fillDialogInput(page, '关键词，每行一个', 'agent memory\nretrieval')
  await page.locator('.el-dialog').getByRole('button', { name: '保存' }).click({ force: true })
  await page.locator('.el-dialog').waitFor({ state: 'hidden', timeout: 10000 })
  await waitForAdminIdle(page)
  await expectVisibleText(page, smokeProfileName)

  const row = page.locator('.airesearch-profile-card').filter({ hasText: smokeProfileName }).first()
  await row.getByRole('button', { name: '编辑' }).click({ force: true })
  await expectVisibleText(page, '编辑搜索配置')
  await fillDialogInput(page, '描述', 'Smoke Vue 搜索配置 已编辑')
  await page.locator('.el-dialog').getByRole('button', { name: '保存' }).click({ force: true })
  await page.locator('.el-dialog').waitFor({ state: 'hidden', timeout: 10000 })
  await waitForAdminIdle(page)
  await expectVisibleText(page, 'Smoke Vue 搜索配置 已编辑')

  const updatedRow = page.locator('.airesearch-profile-card').filter({ hasText: smokeProfileName }).first()
  await updatedRow.getByRole('button', { name: '删除' }).click({ force: true })
  await expectVisibleText(page, '确认删除这个搜索配置？')
  await page.getByRole('button', { name: '确认' }).click({ force: true })
  await waitForAdminIdle(page)
  await page.getByText(smokeProfileName, { exact: false }).waitFor({ state: 'detached', timeout: 10000 })
  await assertNoHorizontalOverflow(page, 'airesearch profiles after crud')
}

async function cleanupSmokeProfile(page) {
  const existing = page.locator('.airesearch-profile-card').filter({ hasText: smokeProfileName }).first()
  if (!(await existing.count())) return
  await existing.getByRole('button', { name: '删除' }).click({ force: true })
  await expectVisibleText(page, '确认删除这个搜索配置？')
  await page.getByRole('button', { name: '确认' }).click({ force: true })
  await waitForAdminIdle(page)
  await page.getByText(smokeProfileName, { exact: false }).waitFor({ state: 'detached', timeout: 10000 }).catch(() => {})
}

async function assertFixedAdminTable(page, label) {
  const box = await page.locator('.admin-data-table').first().boundingBox()
  if (!box) throw new Error(`${label} table is missing`)
  if (box.height < 540) throw new Error(`${label} table height collapsed: ${JSON.stringify(box)}`)
}

async function assertLoginErrorPlacement(page) {
  const card = await page.locator('.admin-login-card').boundingBox()
  const alert = await page.locator('.admin-login-alert').boundingBox()
  if (!card || !alert) throw new Error('login alert or card missing')
  if (alert.x < card.x - 2 || alert.x + alert.width > card.x + card.width + 2) {
    throw new Error(`login error is not inside login card: ${JSON.stringify({ card, alert })}`)
  }
  if (alert.y < card.y || alert.y > card.y + card.height * 0.72) {
    throw new Error(`login error is not near login form: ${JSON.stringify({ card, alert })}`)
  }
}

async function assertInlineAdminFeedback(page, expectedText) {
  const bar = page.locator('.admin-main .admin-feedback-bar').first()
  await bar.waitFor({ state: 'visible', timeout: 5000 })
  await bar.getByText(expectedText, { exact: false }).waitFor({ state: 'visible', timeout: 5000 })
  const placement = await page.evaluate(() => {
    const main = document.querySelector('.admin-main')?.getBoundingClientRect()
    const bar = document.querySelector('.admin-main .admin-feedback-bar')?.getBoundingClientRect()
    return main && bar ? {
      main: { x: main.x, y: main.y, right: main.right, bottom: main.bottom },
      bar: { x: bar.x, y: bar.y, right: bar.right, bottom: bar.bottom }
    } : null
  })
  if (!placement) throw new Error('admin feedback bar is missing from admin main')
  if (
    placement.bar.x < placement.main.x - 2 ||
    placement.bar.right > placement.main.right + 2 ||
    placement.bar.y < placement.main.y - 2 ||
    placement.bar.bottom > placement.main.bottom + 2
  ) {
    throw new Error(`admin feedback is not inside admin workspace: ${JSON.stringify(placement)}`)
  }
  const globalNotifications = await page.locator('body > .el-notification, .admin-feedback-notification').count()
  if (globalNotifications) throw new Error('admin feedback still renders a global Element Plus notification')
}

async function fillDialogInput(page, label, value) {
  const item = page.locator('.el-dialog .el-form-item').filter({ hasText: label }).first()
  const input = item.locator('input, textarea').first()
  await input.fill('')
  await input.fill(value)
}

async function assertAdminShellPolished(page) {
  const routeContextCount = await page.locator('.admin-route-context').count()
  if (routeContextCount) throw new Error('admin shell still renders technical route context')
  const body = await page.locator('body').innerText().catch(() => '')
  if (/\/admin\/[a-z]/.test(body)) throw new Error(`admin shell leaked route path in visible text: ${body.slice(0, 500)}`)
  await assertNoHorizontalOverflow(page, 'admin shell')
}

async function assertSidebarGroups(page) {
  for (const label of ['总览', '塑形馆', '时务局', '闲趣集', '新闻社', '研知库']) {
    await page.locator('.admin-menu').getByText(label, { exact: true }).first().waitFor({ state: 'visible', timeout: 5000 })
  }
  for (const label of ['论文管理', '博客生成', '搜索入库', '搜索配置', '任务中心', '重建部署']) {
    await page.locator('.admin-menu').getByText(label, { exact: true }).first().waitFor({ state: 'visible', timeout: 5000 })
  }
}

async function assertPaperEditorSplit(page) {
  await page.locator('.airesearch-paper-list-panel').waitFor({ state: 'visible', timeout: 10000 })
  await page.locator('.airesearch-editor-panel').waitFor({ state: 'visible', timeout: 10000 })
  const boxes = await page.evaluate(() => {
    const list = document.querySelector('.airesearch-paper-list-panel')?.getBoundingClientRect()
    const editor = document.querySelector('.airesearch-editor-panel')?.getBoundingClientRect()
    return list && editor ? {
      list: { top: list.top, left: list.left, right: list.right, width: list.width },
      editor: { top: editor.top, left: editor.left, width: editor.width }
    } : null
  })
  if (!boxes) throw new Error('missing AIResearch paper split boxes')
  if (boxes.editor.left <= boxes.list.right) throw new Error(`paper editor is not to the right of paper list: ${JSON.stringify(boxes)}`)
  if (Math.abs(boxes.editor.top - boxes.list.top) > 4) throw new Error(`paper editor dropped below paper list: ${JSON.stringify(boxes)}`)
  await expectVisibleText(page, '保存论文编辑')
  await expectVisibleText(page, '研究事实')
  await page.getByRole('button', { name: '证据检查器' }).click({ force: true })
  await page.locator('.airesearch-layout-inspector-dialog').waitFor({ state: 'visible', timeout: 10000 })
  await page.getByRole('tab', { name: '公式 OCR' }).waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('tab', { name: '表格结构' }).waitFor({ state: 'visible', timeout: 5000 })
  await page.getByRole('tab', { name: 'OCR / 读序' }).waitFor({ state: 'visible', timeout: 5000 })
  const inspectorBox = await page.locator('.airesearch-layout-inspector-dialog').evaluate((element) => {
    const box = element.getBoundingClientRect()
    return {
      x: box.x,
      y: box.y,
      width: box.width,
      height: box.height,
      viewportWidth: window.innerWidth,
      viewportHeight: window.innerHeight
    }
  })
  if (!inspectorBox || inspectorBox.width < 900 || inspectorBox.x < 8 || inspectorBox.y < 8) {
    throw new Error(`layout inspector is not stably framed: ${JSON.stringify(inspectorBox)}`)
  }
  if (
    inspectorBox.x + inspectorBox.width > inspectorBox.viewportWidth - 8 ||
    inspectorBox.y + inspectorBox.height > inspectorBox.viewportHeight - 8
  ) {
    const containingBlockAncestors = await page.locator('.airesearch-layout-inspector-dialog').evaluate((dialog) => {
      const rows = []
      for (let element = dialog.parentElement; element; element = element.parentElement) {
        const style = getComputedStyle(element)
        if (
          style.transform !== 'none' || style.filter !== 'none' || style.perspective !== 'none' ||
          style.contain !== 'none' || style.willChange.includes('transform')
        ) {
          const box = element.getBoundingClientRect()
          rows.push({
            tag: element.tagName,
            className: element.className,
            transform: style.transform,
            filter: style.filter,
            perspective: style.perspective,
            contain: style.contain,
            willChange: style.willChange,
            box: { x: box.x, y: box.y, width: box.width, height: box.height }
          })
        }
      }
      return rows
    })
    throw new Error(`layout inspector exceeds the desktop viewport: ${JSON.stringify(inspectorBox)} ancestors=${JSON.stringify(containingBlockAncestors)}`)
  }
  if (screenshotDir) {
    await mkdir(screenshotDir, { recursive: true })
    await page.screenshot({ path: join(screenshotDir, 'admin-layout-inspector.png'), timeout: 5000 }).catch((error) => {
      console.warn(`admin inspector screenshot skipped: ${error.message}`)
    })
  }
  const inspectorCloseButton = page.locator('.airesearch-layout-inspector-close')
  await inspectorCloseButton.waitFor({ state: 'visible', timeout: 5000 })
  const closeBox = await inspectorCloseButton.boundingBox()
  if (!closeBox) throw new Error('layout inspector close button has no clickable bounds')
  const closePoint = { x: closeBox.x + closeBox.width / 2, y: closeBox.y + closeBox.height / 2 }
  const closeButtonReceivesPointer = await page.evaluate(({ x, y }) => {
    return Boolean(document.elementFromPoint(x, y)?.closest('.airesearch-layout-inspector-close'))
  }, closePoint)
  if (!closeButtonReceivesPointer) throw new Error(`layout inspector close button is occluded: ${JSON.stringify(closePoint)}`)
  await inspectorCloseButton.click({ force: true })
  try {
    await page.locator('.airesearch-layout-inspector-dialog').waitFor({ state: 'hidden', timeout: 3000 })
  } catch (error) {
    const dialogState = await page.locator('.airesearch-layout-inspector-dialog').evaluate((dialog) => {
      const overlayDialog = dialog.closest('.el-overlay-dialog')
      const overlay = dialog.closest('.el-overlay')
      return {
        dialogDisplay: getComputedStyle(dialog).display,
        dialogVisibility: getComputedStyle(dialog).visibility,
        overlayDialogDisplay: overlayDialog ? getComputedStyle(overlayDialog).display : null,
        overlayDisplay: overlay ? getComputedStyle(overlay).display : null,
        overlayStyle: overlay?.getAttribute('style') || '',
        activeElement: document.activeElement?.className || document.activeElement?.tagName || ''
      }
    })
    throw new Error(`layout inspector did not close: ${JSON.stringify(dialogState)} (${error.message})`)
  }
}

async function exerciseAIResearchBlogStatusContract(page) {
  let generationAttempt = 0
  let stateReadsAfterGenerate = 0
  const submittedInputs = []
  const paperKey = 'smoke-paper-blog'
  const previousFailure = {
    id: 9899,
    job_type: 'paper_blog_generate',
    status: 'publish_failed',
    message: 'previous publish failure',
    params: { paperKey, targetWordCount: 4800 },
    created_at: '2026-06-19T07:50:00Z'
  }
  let mockLatestJob = {
    id: 9900,
    job_type: 'paper_blog_generate',
    status: 'completed',
    message: 'done',
    params: { paperKey, targetWordCount: 5000 },
    created_at: '2026-06-19T08:00:00Z'
  }
  const initialVersion = {
    id: 41,
    version_number: 1,
    status: 'published',
    title: 'Smoke 论文深度解读',
    word_count: 4680,
    created_at: '2026-06-19T08:00:00Z',
    generation_meta_json: JSON.stringify({ target_chars: 5000, cache_hits: 3, llm_calls: 5 })
  }
  const completedVersion = {
    ...initialVersion,
    id: 42,
    version_number: 2,
    word_count: 5275,
    created_at: '2026-06-19T08:10:00Z',
    generation_meta_json: JSON.stringify({ target_chars: 5500, cache_hits: 1, llm_calls: 7 })
  }

  const statePayload = () => {
    let job = mockLatestJob
    if (generationAttempt) {
      stateReadsAfterGenerate += 1
      const terminalStatus = generationAttempt === 1 ? 'completed' : 'publish_failed'
      const status = stateReadsAfterGenerate === 1 ? 'queued' : stateReadsAfterGenerate === 2 ? 'running' : terminalStatus
      job = {
        ...mockLatestJob,
        id: 9900 + generationAttempt,
        status,
        message: status === 'completed' ? 'done' : status === 'publish_failed' ? 'static publication failed' : status === 'running' ? 'generating paper blog' : 'waiting in queue',
        params: { paperKey, targetWordCount: 5500 }
      }
      mockLatestJob = job
    }
    return {
      state: {
        papers: [{
          paper_key: paperKey,
          title: 'Smoke Paper Blog',
          year: 2026,
          blog_status: 'published',
          blog_word_count: 4680,
          blog_current_version_id: 41
        }],
        profiles: [],
        jobs: [job, previousFailure],
        job_statuses: ['queued', 'running', 'completed', 'failed', 'publish_failed', 'canceled'],
        providers: [],
        fact_types: ['method'],
        stats: { paper_count: 1, visible_count: 1, hidden_count: 0, job_status_counts: { [job.status]: 1 } }
      }
    }
  }

  const blogPayload = () => {
    const complete = generationAttempt > 1 || (generationAttempt === 1 && stateReadsAfterGenerate >= 3)
    const version = complete ? completedVersion : initialVersion
    return {
      result: {
        post: {
          paper_key: paperKey,
          current_version_id: version.id,
          status: 'published',
          title: version.title,
          word_count: version.word_count,
          model: 'smoke-model',
          updated_at: version.created_at,
          markdown: '# Smoke Paper Blog'
        },
        versions: [version],
        latest_job: mockLatestJob,
        generation_meta: JSON.parse(version.generation_meta_json)
      }
    }
  }

  const dataPattern = '**/niu-secretary/api/admin/data*'
  const actionPattern = '**/niu-secretary/api/admin/actions/execute'
  await page.route(dataPattern, async (route) => {
    const resource = new URL(route.request().url()).searchParams.get('resource')
    if (resource === 'airesearch.admin.state') return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(statePayload()) })
    if (resource === 'airesearch.admin.paper') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ result: { paper_key: paperKey, title: 'Smoke Paper Blog', facts: [] } })
      })
    }
    if (resource === 'airesearch.admin.paper.blog.detail') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(blogPayload()) })
    }
    return route.fallback()
  })
  await page.route(actionPattern, async (route) => {
    const body = route.request().postDataJSON()
    if (body?.action !== 'airesearch.admin.paper.blog.generate') return route.fallback()
    submittedInputs.push(body.input)
    generationAttempt += 1
    stateReadsAfterGenerate = 0
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, message: '论文深度解读生成任务已加入队列。', result: { job_id: 9900 + generationAttempt, status: 'queued' } })
    })
  })

  try {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(`${webBase}admin/airesearch/blogs?paperKey=${paperKey}&status=published`, { waitUntil: 'networkidle' })
    await expectVisibleText(page, 'Smoke Paper Blog')
    await expectVisibleText(page, '缓存命中')
    await assertNoHorizontalOverflow(page, 'desktop airesearch blogs')
    await page.reload({ waitUntil: 'networkidle' })
    if (!page.url().includes(`paperKey=${paperKey}`) || !page.url().includes('status=published')) throw new Error(`paper blog query was not preserved: ${page.url()}`)
    const statusPanel = page.locator('[data-testid="paper-blog-status"]')
    await statusPanel.waitFor({ state: 'visible', timeout: 10000 })
    await expectVisibleText(page, '#9900 完成')
    await expectVisibleText(page, '4680 字')
    await statusPanel.getByText('LLM 调用', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
    await statusPanel.getByText('5', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
    await expectVisibleText(page, 'previous publish failure')

    const targetInput = page.locator('.airesearch-blog-command .el-input-number input').first()
    await targetInput.fill('5500')
    await targetInput.press('Enter')
    await page.getByRole('button', { name: '生成深度解读' }).click({ force: true })
    await expectVisibleText(page, '#9901 完成')
    await expectVisibleText(page, '5275 字')
    await statusPanel.getByText('7', { exact: true }).waitFor({ state: 'visible', timeout: 5000 })
    if (submittedInputs[0]?.paperKey !== paperKey || submittedInputs[0]?.targetWordCount !== 5500) {
      throw new Error(`paper blog generate action payload is incorrect: ${JSON.stringify(submittedInputs[0])}`)
    }
    if (stateReadsAfterGenerate < 3) throw new Error('paper blog generation status was not polled through completion')

    await page.getByRole('button', { name: '强制重新生成' }).click({ force: true })
    await expectVisibleText(page, '#9902 发布失败')
    await expectVisibleText(page, 'static publication failed')
    if (submittedInputs[1]?.force !== true) throw new Error(`paper blog force action is not wired: ${JSON.stringify(submittedInputs[1])}`)
    if (stateReadsAfterGenerate < 3) throw new Error('paper blog publish failure was not treated as a terminal status')
    await page.reload({ waitUntil: 'networkidle' })
    await expectVisibleText(page, 'static publication failed')
    await page.setViewportSize({ width: 390, height: 844 })
    await page.reload({ waitUntil: 'networkidle' })
    await assertNoHorizontalOverflow(page, 'mobile airesearch blogs')
    await page.setViewportSize({ width: 1366, height: 900 })
  } finally {
    await page.unroute(dataPattern)
    await page.unroute(actionPattern)
  }
}

async function assertAdminConfirmStyle(page) {
  await page.getByRole('button', { name: '加入重建队列' }).click({ force: true })
  await page.locator('.admin-confirm-box').waitFor({ state: 'visible', timeout: 10000 })
  const box = await page.locator('.admin-confirm-box').boundingBox()
  if (!box || box.x < 100 || box.y < 80) throw new Error(`admin confirm is poorly positioned: ${JSON.stringify(box)}`)
  await page.getByRole('button', { name: '取消' }).click({ force: true })
  await page.locator('.admin-confirm-box').waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {})
}

async function assertMobileAdminLayout(page) {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(`${webBase}admin/airesearch/discovery`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '搜索入库')
  await waitForAdminIdle(page)
  await assertNoHorizontalOverflow(page, 'mobile airesearch discovery')
  const aside = await page.locator('.admin-aside').boundingBox()
  if (!aside) throw new Error('mobile admin aside is missing')
  if (aside.height > 380) throw new Error(`mobile admin navigation is too tall: ${JSON.stringify(aside)}`)
  await page.goto(`${webBase}admin/airesearch/profiles`, { waitUntil: 'networkidle' })
  await expectVisibleText(page, '搜索配置')
  await waitForAdminIdle(page)
  await assertNoHorizontalOverflow(page, 'mobile airesearch profiles')
  await page.setViewportSize({ width: 1366, height: 900 })
}

async function assertNoHorizontalOverflow(page, label) {
  const overflow = await page.evaluate(() => Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth))
  if (overflow > 2) throw new Error(`${label} has horizontal overflow: ${overflow}`)
}

async function waitForAdminIdle(page) {
  await page.locator('.el-loading-mask').waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {})
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
