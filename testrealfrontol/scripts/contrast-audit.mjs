#!/usr/bin/env node
/**
 * WCAG 对比度审计（可复跑）—— 深色 --text-3 根因修复轮
 *
 * 解析 src/assets/styles/design-system.css 的令牌定义：
 *   :root       → 浅色默认值
 *   html.dark   → 深色覆写（按 var() 链自动解析）
 * 计算 --text-1/2/3/4 对三层底（--bg-canvas / --bg-surface / --bg-raised）的
 * WCAG 2.x 对比度（相对亮度公式，sRGB）。
 *
 * 用法:
 *   node scripts/contrast-audit.mjs                 # 打印浅/深对照表
 *   node scripts/contrast-audit.mjs --eval "#94949f,#8a8a95"
 *                                                   # 评估候选色（对深色三层底）
 * 退出码: 表内存在 AA 正文（4.5:1）不达格时非 0（浅色占位/disabled 例外不算）。
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const CSS_PATH = path.resolve(here, '..', 'src', 'assets', 'styles', 'design-system.css')

/* ---------- CSS 解析 ---------- */
const stripComments = (css) => css.replace(/\/\*[\s\S]*?\*\//g, '')

/** 提取 selector 后第一个块（大括号配对）内的自定义属性定义 */
function collectBlock(css, selectorRe) {
  const m = selectorRe.exec(css)
  if (!m) return {}
  let i = css.indexOf('{', m.index + m[0].length - 1)
  if (i < 0) return {}
  let depth = 0
  let end = -1
  for (let j = i; j < css.length; j++) {
    if (css[j] === '{') depth++
    else if (css[j] === '}') {
      depth--
      if (depth === 0) { end = j; break }
    }
  }
  if (end < 0) return {}
  const body = css.slice(i + 1, end)
  const out = {}
  const re = /(--[\w-]+)\s*:\s*([^;]+);/g
  let mm
  while ((mm = re.exec(body))) out[mm[1]] = mm[2].trim()
  return out
}

/** :root 可能有多块（本文件集中在第一块）；html.dark 取定义 --slate-* 的那块 */
function collectRootBlocks(css) {
  const out = {}
  const re = /:root\s*\{/g
  let m
  while ((m = re.exec(css))) {
    const block = collectBlock(css.slice(m.index), /^:root\s*\{/)
    Object.assign(out, block)
  }
  return out
}

function collectDarkBlock(css) {
  // 找“纯 html.dark”块（后随 {），跳过 html.dark .foo 之类
  const re = /html\.dark\s*\{/g
  const out = {}
  let m
  while ((m = re.exec(css))) {
    const block = collectBlock(css.slice(m.index), /^html\.dark\s*\{/)
    Object.assign(out, block)
  }
  return out
}

/* ---------- 颜色与亮度 ---------- */
function parseColor(v) {
  const s = String(v).trim()
  let m = s.match(/^#([0-9a-f]{3})$/i)
  if (m) {
    const h = m[1]
    return [0, 2, 4].map(i => parseInt(h[i] + h[i], 16))
  }
  m = s.match(/^#([0-9a-f]{6})$/i)
  if (m) {
    const h = m[1]
    return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16))
  }
  m = s.match(/^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i)
  if (m) return [1, 2, 3].map(i => parseInt(m[i], 10))
  return null
}

function resolveVar(name, maps) {
  for (const map of maps) {
    if (name in map) {
      const v = map[name]
      const vm = v.match(/^var\(\s*(--[\w-]+)\s*\)$/)
      if (vm) return resolveVar(vm[1], maps)
      return v
    }
  }
  return null
}

const lum = ([r, g, b]) => {
  const f = (c) => {
    c /= 255
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
const ratio = (a, b) => {
  const [l1, l2] = [lum(a), lum(b)].sort((x, y) => y - x)
  return (l1 + 0.05) / (l2 + 0.05)
}
const hex = (rgb) => '#' + rgb.map(c => c.toString(16).padStart(2, '0')).join('')

/* ---------- 主流程 ---------- */
const css = stripComments(fs.readFileSync(CSS_PATH, 'utf8'))
const rootMap = collectRootBlocks(css)
const darkMap = { ...rootMap, ...collectDarkBlock(css) }

function tokenValue(name, map) {
  const v = resolveVar(name, [map])
  if (v == null) return { hex: null, css: '?' }
  const rgb = parseColor(v)
  return { hex: rgb ? hex(rgb) : v, css: v, rgb }
}

function table(label, map) {
  const bgs = ['--bg-canvas', '--bg-surface', '--bg-raised'].map(n => ({ n, ...tokenValue(n, map) }))
  console.log(`\n── ${label} ─────────────────────────────────────────────`)
  console.log('bg: ' + bgs.map(b => `${b.n.replace('--bg-', '')}=${b.hex}`).join(' | '))
  console.log('token      value      ' + bgs.map(b => b.n.replace('--bg-', '').padStart(8)).join('') + '   对 raised 判定 (AA 正文 4.5)')
  let fail = 0
  for (const t of ['--text-1', '--text-2', '--text-3', '--text-4']) {
    const tv = tokenValue(t, map)
    if (!tv.rgb) { console.log(`${t}  ${tv.css}  (无法解析)`); continue }
    const rs = bgs.map(b => (b.rgb ? ratio(tv.rgb, b.rgb) : NaN))
    const rRaised = rs[2]
    const verdict = rRaised >= 4.5 ? 'PASS' : 'FAIL(<4.5)'
    if (verdict !== 'PASS') fail++
    console.log(`${t.padEnd(10)} ${tv.hex}  ` + rs.map(r => r.toFixed(2).padStart(8)).join('') + `   ${verdict}`)
  }
  return fail
}

const evalIdx = process.argv.indexOf('--eval')
if (evalIdx >= 0) {
  const candidates = (process.argv[evalIdx + 1] || '').split(',').map(s => s.trim()).filter(Boolean)
  const darkBgs = ['--bg-canvas', '--bg-surface', '--bg-raised'].map(n => ({ n, ...tokenValue(n, darkMap) }))
  console.log('候选色评估（对深色三层底；AA 正文需 raised ≥ 4.5）')
  console.log('candidate  ' + darkBgs.map(b => b.n.replace('--bg-', '').padStart(8)).join('') + '   对 raised 判定')
  for (const c of candidates) {
    const rgb = parseColor(c)
    if (!rgb) { console.log(`${c}  (无法解析)`); continue }
    const rs = darkBgs.map(b => ratio(rgb, b.rgb))
    console.log(`${c.padEnd(10)} ` + rs.map(r => r.toFixed(2).padStart(8)).join('') + `   ${rs[2] >= 4.5 ? 'PASS' : 'FAIL(<4.5)'}`)
  }
  process.exit(0)
}

const failLight = table('LIGHT (:root)', rootMap)
const failDark = table('DARK (html.dark)', darkMap)
console.log('')
process.exit(failLight + failDark > 0 ? 1 : 0)
