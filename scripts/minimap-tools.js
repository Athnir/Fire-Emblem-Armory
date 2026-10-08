// Helpers for transcribing Fire Emblem Wiki minimaps (6 px per tile) into map grids.
//
// Usage: open a cdn.fireemblemwiki.org minimap URL in a browser tab (the CDN blocks cross-origin
// fetches, so the page must be on that origin), paste this file into the console, then e.g.
//
//   const r = await show([NORMAL_URL, DV_URL], 20)  // side by side, numbered grid; r.diff = tiles a vein changes
//   classify(window.__imgs[0])                       // letter grid guess, top row first
//   probe(window.__imgs[0], [[17, 5], [6, 6]])       // edge / corner / centre colours of tiles
//   region(window.__imgs, 11, 20, 1, 12, 34)         // zoom into columns 11-20, rows 1-12
//
// Coordinates are bottom-left (1, 1). Find a file's URL from its name via MediaWiki's hashing:
// md5(name) -> https://cdn.fireemblemwiki.org/<h[0]>/<h[0..1]>/<name>.
//
// Reading the colours:
// - Unit dots (red enemy, blue player, green ally) and pots cover the tile centre, so judge the
//   terrain under them from the tile EDGE midpoints: a woods/pillar diamond's points stick out past a
//   dot, plain ground doesn't.
// - A boss has a soft red glow that tints its neighbours equally in the normal and after-vein images,
//   so a diff can miss changed tiles under it. Check those by eye.

const INNER = [[1, 1], [4, 1], [1, 4], [4, 4], [2, 1], [3, 1], [1, 2], [1, 3], [4, 2], [4, 3], [2, 4], [3, 4]]
const CENTER = [[2, 2], [3, 2], [2, 3], [3, 3]]
const EDGE = [[0, 2], [0, 3], [5, 2], [5, 3], [2, 0], [3, 0], [2, 5], [3, 5]]
const CORNER = [[0, 0], [5, 0], [0, 5], [5, 5]]

async function loadImg(url) {
  const bmp = await createImageBitmap(await (await fetch(url)).blob())
  const c = new OffscreenCanvas(bmp.width, bmp.height)
  const x = c.getContext('2d')
  x.drawImage(bmp, 0, 0)
  return { bmp, w: bmp.width, h: bmp.height, d: x.getImageData(0, 0, bmp.width, bmp.height).data }
}

/** Average colour of the given pixel offsets inside tile (tx, ty), counted from the TOP-left, 0-based. */
function tileAvg(img, tx, ty, pts) {
  const a = pts.map(([x, y]) => {
    const i = ((ty * 6 + y) * img.w + tx * 6 + x) * 4
    return [img.d[i], img.d[i + 1], img.d[i + 2]]
  })
  return a.reduce((s, p) => s.map((v, i) => v + p[i] / a.length), [0, 0, 0]).map(Math.round)
}

function drawGrid(ctx, off, L, T, cols, rows, x0, yTop) {
  ctx.strokeStyle = 'rgba(255,255,255,0.3)'
  for (let x = 0; x <= cols; x++) { ctx.beginPath(); ctx.moveTo(off + L + x * T + 0.5, 0); ctx.lineTo(off + L + x * T + 0.5, rows * T); ctx.stroke() }
  for (let y = 0; y <= rows; y++) { ctx.beginPath(); ctx.moveTo(off + L, y * T + 0.5); ctx.lineTo(off + L + cols * T, y * T + 0.5); ctx.stroke() }
  ctx.fillStyle = '#fff'
  ctx.font = '10px monospace'
  ctx.textAlign = 'center'
  for (let x = 0; x < cols; x++) ctx.fillText(String(x0 + x), off + L + x * T + T / 2, rows * T + 11)
  ctx.textAlign = 'right'
  for (let y = 0; y < rows; y++) ctx.fillText(String(yTop - y), off + L - 2, y * T + T / 2 + 3)
}

/** Draws the images side by side with a numbered grid; returns the tiles that differ between the first two. */
async function show(urls, T = 18) {
  const imgs = []
  for (const u of urls) imgs.push(await loadImg(u))
  window.__imgs = imgs
  const L = 18
  const W = imgs[0].w / 6
  const H = imgs[0].h / 6
  document.body.innerHTML = ''
  document.body.style.cssText = 'margin:0;background:#222'
  const c = document.createElement('canvas')
  c.width = imgs.length * (W * T + L + 8)
  c.height = H * T + 14
  const ctx = c.getContext('2d')
  ctx.imageSmoothingEnabled = false
  imgs.forEach((im, k) => {
    const off = k * (W * T + L + 8)
    ctx.drawImage(im.bmp, off + L, 0, W * T, H * T)
    drawGrid(ctx, off, L, T, W, H, 1, H)
  })
  document.body.appendChild(c)
  const diff = []
  if (imgs[1]) {
    for (let ty = 0; ty < H; ty++) {
      for (let tx = 0; tx < W; tx++) {
        const a = tileAvg(imgs[0], tx, ty, INNER)
        const b = tileAvg(imgs[1], tx, ty, INNER)
        if (Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1]) + Math.abs(a[2] - b[2]) > 30) diff.push([tx + 1, H - ty])
      }
    }
  }
  return { W, H, diff }
}

/** Zoomed view of columns x0..x1 and rows y0..y1 of each image. */
function region(imgs, x0, x1, y0, y1, T = 34) {
  const H = imgs[0].h / 6
  const L = 18
  const cols = x1 - x0 + 1
  const rows = y1 - y0 + 1
  document.body.innerHTML = ''
  const c = document.createElement('canvas')
  c.width = imgs.length * (cols * T + L + 10)
  c.height = rows * T + 14
  const ctx = c.getContext('2d')
  ctx.imageSmoothingEnabled = false
  imgs.forEach((im, k) => {
    const off = k * (cols * T + L + 10)
    ctx.drawImage(im.bmp, (x0 - 1) * 6, (H - y1) * 6, cols * 6, rows * 6, off + L, 0, cols * T, rows * T)
    drawGrid(ctx, off, L, T, cols, rows, x0, y1)
  })
  document.body.appendChild(c)
}

function probe(img, tiles) {
  const H = img.h / 6
  return tiles
    .map(([x, y]) => `(${x},${y}) edge ${tileAvg(img, x - 1, H - y, EDGE).join('.')} corner ${tileAvg(img, x - 1, H - y, CORNER).join('.')} center ${tileAvg(img, x - 1, H - y, CENTER).join('.')}`)
    .join('\n')
}

/**
 * First-pass letter grid (top row first). Calibrated on the shared chapters and Conquest 12; always
 * check it by eye against the image. w = pale (water OR chasm, by chapter), f = woods, p = pillar,
 * b = bridge, F = fort/gate, B = building, ? = unrecognised dark tile, . = plain/floor. Orange blocks
 * (snow, buildings) aren't classified here; find them from a vein diff or by colour.
 */
function classify(img) {
  const W = img.w / 6
  const H = img.h / 6
  const rows = []
  for (let ty = 0; ty < H; ty++) {
    let s = ''
    for (let tx = 0; tx < W; tx++) {
      const e = tileAvg(img, tx, ty, EDGE)
      const k = tileAvg(img, tx, ty, CORNER)
      const c = tileAvg(img, tx, ty, CENTER)
      const i = tileAvg(img, tx, ty, INNER)
      const ring = tileAvg(img, tx, ty, [[1, 1], [4, 1], [1, 4], [4, 4]])
      const unit = (c[0] > 215 && c[1] < 70) || (c[2] > 200 && c[0] < 70) || (c[1] > 180 && c[0] < 120 && c[2] < 30)
      const pale = (p) => p[2] > 160 && p[1] > 185 && p[0] < 200
      let ch = '.'
      if (pale(i) || pale(e)) ch = 'w'
      else if (!unit && c[0] > 240 && c[2] > 150) ch = 'B'
      // A fort is a bright inner square with a dark rim; under a unit only the ring and rim show.
      else if ((e[0] < 115 && e[2] < 50) || (e[0] < 125 && ring[0] > 235)) ch = 'F'
      else if (!unit && Math.abs(c[0] - 166) < 6 && Math.abs(c[1] - 133) < 6 && k[0] < 140) ch = '?'
      else if (!unit && c[1] > c[0] + 5 && c[2] < 90 && c[0] < 140) ch = 'f'
      else if (!unit && c[0] < 125 && c[1] < 108 && c[2] < 80 && c[2] > 60) ch = 'p'
      else if (unit && e[1] / e[0] > 0.84 && e[2] < 100 && e[0] < 185) ch = 'f'
      else if (k[0] < 128 && k[1] / k[0] < 0.8) ch = 'b'
      s += ch
    }
    rows.push(String(H - ty).padStart(2) + ' ' + s)
  }
  return rows.join('\n')
}

Object.assign(window, { loadImg, tileAvg, show, region, probe, classify, INNER, CENTER, EDGE, CORNER })
