// The watched games' maps as pictures, and what changed (src/logic/__tests__/frozenMaps.test.tsx keeps their fingerprints; the
// user's call, 2026-11-26: approved maps are watched, a change that reaches another game's maps is asked about first).
//
//   node scripts/frozen-maps.mjs freeze <game>   freeze a game whose maps the user has all marked good: fingerprints into frozenMaps.json,
//                                                and each map's approved picture (data-raw/frozen-maps/<game>/baseline/<id>.png)
//   node scripts/frozen-maps.mjs check <game>    draw the game's maps as they are now and compare each with its approved picture:
//                                                lists the maps that look different, with a picture of each difference
//                                                (data-raw/frozen-maps/<game>/diff/<id>.png: the changed pixels in magenta)
//
// The drawings come from the test (the map page's own MapGrid, every icon inline); headless Edge turns them into pictures and compares
// them pixel by pixel. A fingerprint can change while nothing looks different (the drawing's markup reordered): check says so, and the
// game can be frozen again.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const OUT = join(ROOT, 'data-raw', 'frozen-maps')
const EDGE = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
const SCALE = 4 // picture pixels per SVG unit (a tile is 10 units: 40 pixels)
const [cmd, game] = process.argv.slice(2)
if (!['freeze', 'check'].includes(cmd) || !game) {
  console.log('node scripts/frozen-maps.mjs freeze|check <game>')
  process.exit(1)
}

function vitest(env) {
  const r = spawnSync('npx vitest run src/logic/__tests__/frozenMaps.test.tsx', { cwd: ROOT, env: { ...process.env, ...env }, shell: true, encoding: 'utf8' })
  return r.stdout + r.stderr
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function browser() {
  const port = 9411
  // Its profile outside the repository: the dev server watches the repository, and Edge holds its files locked while it runs.
  const profile = join(tmpdir(), 'fe-armory-frozen-maps-edge')
  const edge = spawn(EDGE, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' })
  let targets
  for (let i = 0; i < 200; i++) {
    try {
      targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json()
      if (targets.some((t) => t.type === 'page')) break
    } catch {}
    await sleep(150)
  }
  const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl)
  await new Promise((r) => (ws.onopen = r))
  let id = 0
  const pending = new Map()
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data)
    if (m.id && pending.has(m.id)) {
      pending.get(m.id)(m)
      pending.delete(m.id)
    }
  }
  const send = (method, params = {}) => new Promise((r) => {
    const i = ++id
    pending.set(i, r)
    ws.send(JSON.stringify({ id: i, method, params }))
  })
  const run = async (expr) => {
    const r = await send('Runtime.evaluate', { expression: `(async () => { ${expr} })()`, awaitPromise: true, returnByValue: true })
    if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 300))
    return r.result?.result?.value
  }
  // Edge's helpers outlive its first process: end the whole tree.
  const close = () => { ws.close(); spawnSync('taskkill', ['/PID', String(edge.pid), '/T', '/F'], { stdio: 'ignore' }) }
  return { run, close }
}

// In the page: a picture's pixels from a data URL, drawn at SCALE.
const HELPERS = `
  const load = (src) => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = src });
  const pixels = (im, w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d');
    g.fillStyle = '#000'; g.fillRect(0, 0, w, h); g.drawImage(im, 0, 0, w, h); return [c, g.getImageData(0, 0, w, h)] };
  const size = (svg) => { const v = svg.match(/viewBox="0 0 ([0-9.]+) ([0-9.]+)"/); return [Math.round(+v[1] * ${SCALE}), Math.round(+v[2] * ${SCALE})] };
`

const svgUrl = (path) => 'data:image/svg+xml;base64,' + readFileSync(path).toString('base64')

async function picture(b, svgPath) {
  const svg = readFileSync(svgPath, 'utf8')
  const data = await b.run(`${HELPERS}
    const svg = ${JSON.stringify(svg.slice(0, 400))};
    const [w, h] = size(svg);
    const [c] = pixels(await load(${JSON.stringify(svgUrl(svgPath))}), w, h);
    return c.toDataURL('image/png').split(',')[1];`)
  return Buffer.from(data, 'base64')
}

async function compare(b, svgPath, pngPath) {
  const svg = readFileSync(svgPath, 'utf8')
  return JSON.parse(await b.run(`${HELPERS}
    const svg = ${JSON.stringify(svg.slice(0, 400))};
    const [w, h] = size(svg);
    const [, now] = pixels(await load(${JSON.stringify(svgUrl(svgPath))}), w, h);
    const [c, was] = pixels(await load('data:image/png;base64,' + ${JSON.stringify(readFileSync(pngPath).toString('base64'))}), w, h);
    let n = 0;
    const g = c.getContext('2d'); const out = g.createImageData(w, h);
    for (let i = 0; i < now.data.length; i += 4) {
      const d = Math.abs(now.data[i] - was.data[i]) + Math.abs(now.data[i + 1] - was.data[i + 1]) + Math.abs(now.data[i + 2] - was.data[i + 2]);
      const k = d > 24;
      if (k) n++;
      out.data[i] = k ? 255 : now.data[i] * 0.45; out.data[i + 1] = k ? 0 : now.data[i + 1] * 0.45;
      out.data[i + 2] = k ? 255 : now.data[i + 2] * 0.45; out.data[i + 3] = 255;
    }
    g.putImageData(out, 0, 0);
    return JSON.stringify({ changed: n, total: w * h, diff: n ? c.toDataURL('image/png').split(',')[1] : null });`))
}

const dir = (kind) => join(OUT, game, kind)

if (cmd === 'freeze') {
  console.log(vitest({ FROZEN_FREEZE: game }).split('\n').filter((l) => /Tests|FAIL|Error/.test(l)).join('\n'))
  const b = await browser()
  mkdirSync(dir('baseline'), { recursive: true })
  const svgs = readdirSync(dir('baseline')).filter((f) => f.endsWith('.svg'))
  for (const f of svgs) writeFileSync(join(dir('baseline'), f.replace('.svg', '.png')), await picture(b, join(dir('baseline'), f)))
  b.close()
  console.log(`${game}: ${svgs.length} maps frozen, their approved pictures in ${dir('baseline')}`)
} else {
  if (!existsSync(dir('baseline'))) {
    console.log(`${game} has no approved pictures: freeze it first`)
    process.exit(1)
  }
  const test = vitest({ FROZEN_SVG: 'current' })
  const b = await browser()
  mkdirSync(dir('diff'), { recursive: true })
  const looks = []
  for (const f of readdirSync(dir('current')).filter((f) => f.endsWith('.svg'))) {
    const png = join(dir('baseline'), f.replace('.svg', '.png'))
    if (!existsSync(png)) continue
    const r = await compare(b, join(dir('current'), f), png)
    if (r.changed) {
      writeFileSync(join(dir('diff'), f.replace('.svg', '.png')), Buffer.from(r.diff, 'base64'))
      looks.push(`${f.replace('.svg', '')}: ${r.changed} pixels (${((100 * r.changed) / r.total).toFixed(2)}%) look different`)
    }
  }
  b.close()
  const failed = /watched maps changed/.test(test)
  if (looks.length) console.log(`${game}: maps that look different (the differences in ${dir('diff')}):\n  ` + looks.join('\n  '))
  else if (failed) console.log(`${game}: the fingerprints changed but every map looks the same: freeze it again (node scripts/frozen-maps.mjs freeze ${game})`)
  else console.log(`${game}: every frozen map is as it was approved`)
  process.exit(looks.length ? 1 : 0)
}
