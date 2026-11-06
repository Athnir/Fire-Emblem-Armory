import type { Fe16Gambit } from '../data/fe16/fe16BattalionTypes'

const AREA_FILL: Record<Fe16Gambit['kind'], string> = { physical: '#f59e0b', magic: '#c084fc', support: '#34d399' }

/**
 * A gambit's area, drawn small: the user's tile (blue), the tiles it can be aimed at (dashed), the target (ringed) and every tile the
 * area covers (shaded), as the game's area builder lays them out for a target straight ahead at the gambit's shortest range. The
 * user's own tile shows only the user.
 */
export function GambitArea({ gambit, cell = 20 }: { gambit: Fe16Gambit; cell?: number }) {
  const [lo, hi] = gambit.range
  const key = (x: number, y: number) => `${x},${y}`
  const area = new Set(gambit.area.map(([x, y]) => key(x, y)))
  const aim: [number, number][] = []
  for (let x = -hi; x <= hi; x++)
    for (let y = -hi; y <= hi; y++) {
      const d = Math.abs(x) + Math.abs(y)
      if (d >= lo && d <= hi) aim.push([x, y])
    }
  const aimed = new Set(aim.map(([x, y]) => key(x, y)))
  const all = [...gambit.area, ...aim, [0, 0] as [number, number]]
  // At least five tiles across and a row behind the user, so a narrow area still reads as a place on a map.
  const x0 = Math.min(-2, ...all.map((t) => t[0]))
  const x1 = Math.max(2, ...all.map((t) => t[0]))
  const y0 = Math.min(...all.map((t) => t[1]))
  const y1 = Math.max(1, ...all.map((t) => t[1]))
  const w = (x1 - x0 + 1) * cell
  const h = (y1 - y0 + 1) * cell
  const target: [number, number] = [0, -lo]
  const tiles: [number, number][] = []
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) tiles.push([x, y])
  const px = (x: number) => (x - x0) * cell
  const py = (y: number) => (y - y0) * cell
  return (
    <svg
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      role="img"
      aria-label={`${gambit.name}'s area: ${gambit.area.length} tiles`}
      className="shrink-0"
      shapeRendering="crispEdges"
    >
      {tiles.map(([x, y]) => {
        const user = x === 0 && y === 0
        return (
          <rect
            key={key(x, y)}
            x={px(x) + 0.5}
            y={py(y) + 0.5}
            width={cell - 1}
            height={cell - 1}
            fill={user ? '#2563eb' : area.has(key(x, y)) ? AREA_FILL[gambit.kind] : '#171717'}
            fillOpacity={user ? 1 : area.has(key(x, y)) ? 0.75 : 1}
            stroke="#404040"
          />
        )
      })}
      {aim.map(([x, y]) => (
        <rect
          key={`aim-${key(x, y)}`}
          x={px(x) + 2}
          y={py(y) + 2}
          width={cell - 4}
          height={cell - 4}
          fill="none"
          stroke="#e5e5e5"
          strokeWidth={1}
          strokeDasharray="2 2"
          opacity={aimed.has(key(x, y)) ? 0.7 : 0}
        />
      ))}
      <circle cx={px(target[0]) + cell / 2} cy={py(target[1]) + cell / 2} r={cell / 2 - 2.5} fill="none" stroke="#fafafa" strokeWidth={1.5} />
    </svg>
  )
}

/** What the area picture's marks mean. */
export function GambitAreaLegend() {
  return (
    <p className="text-xs text-neutral-500">
      <span className="text-blue-400">Blue</span>: the user. Ringed: the target, straight ahead at the shortest range. Shaded: the tiles the
      gambit covers. Dashed: the tiles it can be aimed at. The area turns with the direction it's aimed in.
    </p>
  )
}
