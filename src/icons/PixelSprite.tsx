import type { Sprite } from './sprites'

/** One <rect> per horizontal run of same-coloured pixels, so a sprite is a handful of shapes. */
function runs(sprite: Sprite) {
  const out: { x: number; y: number; w: number; fill: string }[] = []
  sprite.rows.forEach((row, y) => {
    let x = 0
    while (x < row.length) {
      const ch = row[x]
      let end = x + 1
      while (end < row.length && row[end] === ch) end++
      if (ch !== '.') out.push({ x, y, w: end - x, fill: sprite.palette[ch] })
      x = end
    }
  })
  return out
}

/** Draws a sprite inside an existing <svg> at (x, y), `size` units square. */
export function SpriteG({ sprite, x, y, size = 10, opacity, className }: { sprite: Sprite; x: number; y: number; size?: number; opacity?: number; className?: string }) {
  const s = size / sprite.rows.length
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} opacity={opacity} className={className} shapeRendering="crispEdges" pointerEvents="none">
      {runs(sprite).map((r, i) => (
        <rect key={i} x={r.x} y={r.y} width={r.w} height={1} fill={r.fill} />
      ))}
    </g>
  )
}

/** A sprite as a standalone inline icon, e.g. in a legend or next to text. */
export function PixelIcon({ sprite, size = 16, title }: { sprite: Sprite; size?: number; title?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 10 10" className="inline-block shrink-0 align-[-3px]" role={title ? 'img' : undefined} aria-label={title} aria-hidden={title ? undefined : true}>
      {title && <title>{title}</title>}
      <SpriteG sprite={sprite} x={0} y={0} />
    </svg>
  )
}
