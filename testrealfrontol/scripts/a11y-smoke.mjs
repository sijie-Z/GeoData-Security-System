#!/usr/bin/env node
/**
 * a11y-smoke.mjs — axe-core accessibility smoke gate (CI job `a11y`).
 *
 * 覆盖：
 *   公开页（无需后端）：/login、/register、/first_home —— 必测。
 *   认证页（需可登录的后端）：
 *     管理员：/admin、/admin/employee_management/information_list、/admin/watermark-quality
 *     员工：  /employee、/employee/data_viewing、/employee/chat
 *
 * 判定：任意页存在 impact ∈ {critical, serious} 的 axe violation（或页面加载 /
 * 登录失败）→ exit 1。moderate / minor 仅打印，不阻塞。
 *
 * 环境变量：
 *   BASE_URL            前端源（默认 http://localhost:4173）
 *   A11Y_SCOPE          all（默认，公开页+认证页）| public（仅公开页）|
 *                       逗号分隔的额外路径（公开页仍必测；路径默认按管理员登录，
 *                       可用 `employee:/path` 前缀指定员工角色）
 *   A11Y_REPORT         报告输出路径（默认 ./a11y-report.json）
 *   A11Y_ADMIN_USER     （默认 admin）/ A11Y_ADMIN_PASS（默认 admin123）
 *   A11Y_EMPLOYEE_USER  （默认 TEST001）/ A11Y_EMPLOYEE_PASS（默认 test123456）
 *   A11Y_SETTLE_MS      loading 遮罩消失后的固定等待毫秒数（默认 1500）
 *
 * 用法：
 *   BASE_URL=http://localhost:4173 A11Y_SCOPE=all node scripts/a11y-smoke.mjs
 *
 * 注意：默认认证页清单**不含** information_add —— 该页 `.el-upload-list` 的
 * axe `list`（serious）为 Element Plus 上游渲染缺陷（div[role=button] 直渲进
 * <ul>），DOM 重排实测会触发 Vue insertBefore 崩溃（见 CHANGELOG 留档）。
 * 解除条件：EP 修复渲染方式或我方安全重构上传列表后，再把该路由加回 ADMIN_PAGES。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import AxeBuilder from '@axe-core/playwright'
import { chromium } from 'playwright'

const HERE = path.dirname(fileURLToPath(import.meta.url))

const BASE_URL = (process.env.BASE_URL || 'http://localhost:4173').replace(/\/+$/, '')
const A11Y_SCOPE = (process.env.A11Y_SCOPE || 'all').trim()
const REPORT_PATH = path.resolve(process.env.A11Y_REPORT || path.join(process.cwd(), 'a11y-report.json'))
const SETTLE_MS = Number(process.env.A11Y_SETTLE_MS || 1500)
const VIEWPORT = { width: 1600, height: 1000 }

const CREDS = {
  admin: {
    user: process.env.A11Y_ADMIN_USER || 'admin',
    pass: process.env.A11Y_ADMIN_PASS || 'admin123',
    home: '/admin',
  },
  employee: {
    user: process.env.A11Y_EMPLOYEE_USER || 'TEST001',
    pass: process.env.A11Y_EMPLOYEE_PASS || 'test123456',
    home: '/employee',
  },
}

// 公开页：无需登录 / 后端即可渲染。
const PUBLIC_PAGES = ['/login', '/register', '/first_home']

// 认证页默认清单（information_add 按上方注释有意排除）。
const ADMIN_PAGES = ['/admin', '/admin/employee_management/information_list', '/admin/watermark-quality']
const EMPLOYEE_PAGES = ['/employee', '/employee/data_viewing', '/employee/chat']

const BLOCKING_IMPACTS = new Set(['critical', 'serious'])

/** @returns {{mode: string, admin: string[], employee: string[]}} */
function resolveScope(raw) {
  const value = (raw || 'all').trim()
  if (!value || value.toLowerCase() === 'all') {
    return { mode: 'all', admin: [...ADMIN_PAGES], employee: [...EMPLOYEE_PAGES] }
  }
  if (value.toLowerCase() === 'public') {
    return { mode: 'public', admin: [], employee: [] }
  }
  // 逗号分隔的自定义路径：默认管理员；`employee:/path` 指定员工角色。
  const admin = []
  const employee = []
  for (const entry of value.split(',').map((s) => s.trim()).filter(Boolean)) {
    const m = entry.match(/^(admin|employee)\s*:\s*(\/.*)$/i)
    if (m) {
      ;(m[1].toLowerCase() === 'employee' ? employee : admin).push(m[2])
    } else {
      admin.push(entry.startsWith('/') ? entry : `/${entry}`)
    }
  }
  return { mode: 'custom', admin, employee }
}

function axeVersion() {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(HERE, '..', 'node_modules', 'axe-core', 'package.json'), 'utf8'))
    return pkg.version || null
  } catch {
    return null
  }
}

function summarizeViolations(violations) {
  const counts = { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0, nodes: 0 }
  for (const v of violations) {
    const key = BLOCKING_IMPACTS.has(v.impact) || v.impact === 'moderate' || v.impact === 'minor' ? v.impact : 'unknown'
    counts[key] += 1
    counts.nodes += v.nodes.length
  }
  counts.blocking = counts.critical + counts.serious
  return counts
}

function mapViolation(v) {
  return {
    id: v.id,
    impact: v.impact,
    description: v.description,
    help: v.help,
    helpUrl: v.helpUrl,
    tags: v.tags,
    nodes: v.nodes.map((n) => ({
      target: n.target,
      html: (n.html || '').slice(0, 400),
      failureSummary: n.failureSummary,
    })),
  }
}

/** 等 loading 遮罩消失 + 固定等待，尽量让异步渲染稳定后再跑 axe。 */
async function settle(page) {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {})
  // `.el-loading-mask` 可能晚于 waitForSelector 出现，用轮询而非 detached 状态。
  await page
    .waitForFunction(() => !document.querySelector('.el-loading-mask'), null, { timeout: 20000 })
    .catch(() => {})
  await page.waitForTimeout(SETTLE_MS)
}

async function login(page, role) {
  const cred = CREDS[role]
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'load', timeout: 45000 })
  await page.waitForSelector('.auth-input input', { timeout: 30000 })
  // 角色胶囊：第 0 个 = 管理员，第 1 个 = 员工（login.vue 中顺序固定）。
  await page.locator('.role-option').nth(role === 'admin' ? 0 : 1).click()
  const inputs = page.locator('.auth-input input')
  await inputs.nth(0).fill(cred.user)
  await inputs.nth(1).fill(cred.pass)
  await page.locator('button.auth-submit').click()
  try {
    await page.waitForURL(new RegExp(`${cred.home.replace('/', '\\/')}`), { timeout: 30000 })
    await page.waitForFunction(() => !!sessionStorage.getItem('token'), null, { timeout: 15000 })
  } catch (err) {
    const bodyText = await page.locator('body').innerText().catch(() => '')
    throw new Error(
      `login as ${role} (${cred.user}) failed: ${err.message}; url=${page.url()}; body=${bodyText.slice(0, 300).replace(/\s+/g, ' ')}`
    )
  }
}

async function scanPage(page, routePath, role, log) {
  const start = Date.now()
  const consoleErrors = []
  const onConsole = (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text().slice(0, 500))
  }
  const onPageError = (err) => consoleErrors.push(`pageerror: ${String(err).slice(0, 500)}`)
  page.on('console', onConsole)
  page.on('pageerror', onPageError)

  let violations = []
  let incomplete = []
  let status = 'ok'
  let error = null
  try {
    await page.goto(`${BASE_URL}${routePath}`, { waitUntil: 'load', timeout: 45000 })
    await settle(page)
    const results = await new AxeBuilder({ page }).analyze()
    violations = results.violations.map(mapViolation)
    incomplete = results.incomplete.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }))
  } catch (err) {
    status = 'error'
    error = String(err && err.message ? err.message : err).slice(0, 800)
  } finally {
    page.off('console', onConsole)
    page.off('pageerror', onPageError)
  }

  const counts = summarizeViolations(violations)
  const durationMs = Date.now() - start
  const blocking = status !== 'ok' || counts.blocking > 0

  if (status === 'ok') {
    const impactText = `critical=${counts.critical} serious=${counts.serious} moderate=${counts.moderate} minor=${counts.minor}`
    log(
      `[${role.padEnd(8)}] ${routePath.padEnd(48)} ${blocking ? 'FAIL' : 'PASS'}  ` +
        `violations=${violations.length} (${impactText}) nodes=${counts.nodes} ${durationMs}ms`
    )
  } else {
    log(`[${role.padEnd(8)}] ${routePath.padEnd(48)} ERROR ${error}`)
  }
  for (const v of violations) {
    const firstTarget = v.nodes[0]?.target ? JSON.stringify(v.nodes[0].target) : '(no target)'
    log(`    - ${v.id} (${v.impact || 'n/a'}) x${v.nodes.length}  first target: ${firstTarget}`)
  }

  return {
    path: routePath,
    role,
    status,
    error,
    durationMs,
    blocking,
    counts,
    consoleErrors,
    incomplete,
    violations,
  }
}

function writeReport(report) {
  try {
    fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true })
    fs.writeFileSync(REPORT_PATH, JSON.stringify(report, null, 2) + '\n', 'utf8')
    console.log(`\n[report] written to ${REPORT_PATH}`)
  } catch (err) {
    console.error(`[report] failed to write ${REPORT_PATH}: ${err.message}`)
  }
}

async function runRole(browser, role, routes, report, log) {
  if (!routes.length) return
  const context = await browser.newContext({ viewport: VIEWPORT })
  const page = await context.newPage()
  try {
    log(`\n--- logging in as ${role} (${CREDS[role].user}) ---`)
    await login(page, role)
    log(`--- logged in as ${role} ---`)
    for (const routePath of routes) {
      const result = await scanPage(page, routePath, role, log)
      report.pages.push(result)
    }
  } catch (err) {
    const message = String(err && err.message ? err.message : err).slice(0, 800)
    log(`\n[${role}] AUTH/SETUP ERROR: ${message}`)
    // 登录失败视为整个角色门禁失败：为每个待测路径记一条错误，保证报告可诊断。
    for (const routePath of routes) {
      report.pages.push({
        path: routePath,
        role,
        status: 'error',
        error: `role setup failed: ${message}`,
        durationMs: 0,
        blocking: true,
        counts: { critical: 0, serious: 0, moderate: 0, minor: 0, unknown: 0, nodes: 0, blocking: 0 },
        consoleErrors: [],
        incomplete: [],
        violations: [],
      })
    }
  } finally {
    await context.close().catch(() => {})
  }
}

async function main() {
  const startedAt = new Date().toISOString()
  const scope = resolveScope(A11Y_SCOPE)
  const report = {
    tool: 'a11y-smoke.mjs (playwright + @axe-core/playwright)',
    axeVersion: axeVersion(),
    baseUrl: BASE_URL,
    scope: { raw: A11Y_SCOPE, mode: scope.mode, admin: scope.admin, employee: scope.employee },
    blockingImpacts: [...BLOCKING_IMPACTS],
    viewport: VIEWPORT,
    startedAt,
    finishedAt: null,
    pages: [],
    summary: null,
  }
  const log = (line) => console.log(line)

  log(`[a11y] base=${BASE_URL} scope=${A11Y_SCOPE} (mode=${scope.mode}) report=${REPORT_PATH}`)

  const browser = await chromium.launch({ headless: true })
  try {
    // Public pages: fresh context, no login needed.
    if (PUBLIC_PAGES.length) {
      const context = await browser.newContext({ viewport: VIEWPORT })
      const page = await context.newPage()
      try {
        for (const routePath of PUBLIC_PAGES) {
          const result = await scanPage(page, routePath, 'public', log)
          report.pages.push(result)
        }
      } finally {
        await context.close().catch(() => {})
      }
    }
    await runRole(browser, 'admin', scope.admin, report, log)
    await runRole(browser, 'employee', scope.employee, report, log)
  } finally {
    await browser.close().catch(() => {})
  }

  const sum = { pages: report.pages.length, blockingPages: 0, errorPages: 0, critical: 0, serious: 0, moderate: 0, minor: 0, nodes: 0 }
  for (const p of report.pages) {
    if (p.blocking) sum.blockingPages += 1
    if (p.status !== 'ok') sum.errorPages += 1
    sum.critical += p.counts.critical
    sum.serious += p.counts.serious
    sum.moderate += p.counts.moderate
    sum.minor += p.counts.minor
    sum.nodes += p.counts.nodes
  }
  report.summary = sum
  report.finishedAt = new Date().toISOString()

  log(
    `\n=== SUMMARY: pages=${sum.pages} blockingPages=${sum.blockingPages} errorPages=${sum.errorPages} ` +
      `critical=${sum.critical} serious=${sum.serious} moderate=${sum.moderate} minor=${sum.minor} ===`
  )

  writeReport(report)

  if (sum.blockingPages > 0) {
    log(
      `\nA11Y GATE FAILED: ${sum.blockingPages} page(s) with critical/serious violations or load/login errors ` +
        `(see ${REPORT_PATH}).`
    )
    process.exitCode = 1
  } else {
    log('\nA11Y GATE PASSED: no critical/serious violations.')
    process.exitCode = 0
  }
}

main().catch((err) => {
  console.error('[a11y] fatal:', err)
  process.exitCode = 1
})
