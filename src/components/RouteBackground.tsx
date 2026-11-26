import type { Route } from '../data/types'

type FlowerVariant = 'blossom' | 'thorn'

/**
 * Per-route color theme, echoing Fates' own chapter title cards — each route has a distinct base
 * gradient, a flower/vine accent color, and its own flower silhouette(s) (not just a recolor of the
 * same shape — Birthright's cherry blossom, Conquest's twisting rose). Revelation, uniting both
 * kingdoms, splits the two edge strips between them instead of using a third shape of its own: the
 * left edge carries Hoshido's blossom in the route's gold, the right edge Nohr's rose, which keeps
 * its own dark wine color rather than picking up the gold (see ROSE_PETAL/ROSE_CENTER below). Purely
 * original vector art generated here (not extracted from the game), so unlike public/art or
 * public/skills this never needs to be git-ignored — safe to tweak or fully replace at any time.
 */
const ROUTE_THEME: Record<
  'Birthright' | 'Conquest' | 'Revelation',
  { gradientFrom: string; gradientTo: string; flower: string; flowerCenter: string; vine: string; edgeFlowerVariants: [FlowerVariant, FlowerVariant] }
> = {
  Birthright: { gradientFrom: '#aac7ad', gradientTo: '#7a9c7e', flower: '#f6dbe0', flowerCenter: '#e7a8b4', vine: '#5c7a56', edgeFlowerVariants: ['blossom', 'blossom'] },
  Conquest: { gradientFrom: '#9683ac', gradientTo: '#6a5580', flower: '#3d1a22', flowerCenter: '#6b2c38', vine: '#3d2a52', edgeFlowerVariants: ['thorn', 'thorn'] },
  Revelation: { gradientFrom: '#d9ac4a', gradientTo: '#6b7690', flower: '#fbf1d6', flowerCenter: '#e0b23e', vine: '#6b4f1c', edgeFlowerVariants: ['blossom', 'thorn'] },
}

interface Theme {
  flower: string
  flowerCenter: string
  vine: string
  edgeFlowerVariants: [FlowerVariant, FlowerVariant]
}

/** Birthright: rounded 5-petal cherry blossom — the original flower shape. */
function BlossomFlower({ cx, cy, scale, petal, center }: { cx: number; cy: number; scale: number; petal: string; center: string }) {
  const petals = Array.from({ length: 5 }, (_, i) => {
    const angle = (i * 72 * Math.PI) / 180
    const px = cx + Math.cos(angle) * 9 * scale
    const py = cy + Math.sin(angle) * 9 * scale
    return <ellipse key={i} cx={px} cy={py} rx={9 * scale} ry={6 * scale} fill={petal} opacity={0.85} transform={`rotate(${i * 72}, ${px}, ${py})`} />
  })
  return (
    <g>
      {petals}
      <circle cx={cx} cy={cy} r={4 * scale} fill={center} />
    </g>
  )
}

/**
 * Builds one spiral-wedge petal: an outer edge and an inner edge both sweeping the SAME rotational
 * direction around the flower center while their radius grows from a small base to the full petal
 * length, so the petal itself curls through an arc instead of just leaning. Several of these,
 * staggered across 3 depth layers (see ROSE_RINGS), overlap to read as one continuously curling rose
 * — earlier single-petal versions that swept most of a full circle read as a spinning blade/shuriken
 * instead of a flower, so each petal only covers a modest 75-130 degree arc.
 */
function spiralPetalPath(len: number, baseR: number, sweepDeg: number, startDeg: number, innerRatio: number): string {
  const steps = 14
  const points: [number, number][] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const angle = ((startDeg + t * sweepDeg) * Math.PI) / 180
    const r = baseR + (len - baseR) * t
    points.push([Math.cos(angle) * r, Math.sin(angle) * r])
  }
  for (let i = steps; i >= 0; i--) {
    const t = i / steps
    const angle = ((startDeg + t * sweepDeg + 16) * Math.PI) / 180
    const r = (baseR + (len - baseR) * t) * innerRatio
    points.push([Math.cos(angle) * r, Math.sin(angle) * r])
  }
  return 'M ' + points.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join(' L ') + ' Z'
}

const ROSE_RINGS = [
  { count: 6, len: 15, baseR: 5, sweep: 130, step: 60, start: 0, innerRatio: 0.78, opacity: 0.85, layer: 'petal' as const },
  { count: 6, len: 10.5, baseR: 3.5, sweep: 115, step: 60, start: 34, innerRatio: 0.72, opacity: 0.95, layer: 'center' as const },
  { count: 5, len: 6, baseR: 2, sweep: 100, step: 72, start: 60, innerRatio: 0.65, opacity: 1, layer: 'petal' as const },
]

/** Conquest: a twisting rose bud — 3 rings of curling spiral-wedge petals (see spiralPetalPath), same layered structure as the deleted lotus but with sharp curling petals instead of soft ellipses. */
function RoseFlower({ cx, cy, scale, petal, center }: { cx: number; cy: number; scale: number; petal: string; center: string }) {
  return (
    <g>
      {ROSE_RINGS.map((ring) =>
        Array.from({ length: ring.count }, (_, i) => {
          const start = i * ring.step + ring.start
          return (
            <path
              key={`${ring.start}-${i}`}
              d={spiralPetalPath(ring.len * scale, ring.baseR * scale, ring.sweep, start, ring.innerRatio)}
              fill={ring.layer === 'petal' ? petal : center}
              opacity={ring.opacity}
              transform={`translate(${cx}, ${cy})`}
            />
          )
        }),
      )}
      <circle cx={cx} cy={cy} r={1.6 * scale} fill={center} />
    </g>
  )
}

// Revelation's rose (right edge) keeps this same dark wine regardless of route rather than picking up
// the route's gold — only the blossom is meant to follow the per-route palette.
const ROSE_PETAL = '#3d1a22'
const ROSE_CENTER = '#6b2c38'

/** A small blob flower — silhouette varies per route/edge (see ROUTE_THEME's edgeFlowerVariants), not just a recolor of one shared shape. */
function Flower({ cx, cy, scale, petal, center, variant }: { cx: number; cy: number; scale: number; petal: string; center: string; variant: FlowerVariant }) {
  if (variant === 'thorn') return <RoseFlower cx={cx} cy={cy} scale={scale} petal={ROSE_PETAL} center={ROSE_CENTER} />
  return <BlossomFlower cx={cx} cy={cy} scale={scale} petal={petal} center={center} />
}

/** A curvy vine climbing one edge, with short thorn ticks branching off at intervals. */
function Vine({ d, thorns, color }: { d: string; thorns: { x: number; y: number; angle: number }[]; color: string }) {
  return (
    <g stroke={color} strokeWidth={3} fill="none" strokeLinecap="round">
      <path d={d} />
      {thorns.map((t, i) => (
        <line
          key={i}
          x1={t.x}
          y1={t.y}
          x2={t.x + Math.cos((t.angle * Math.PI) / 180) * 14}
          y2={t.y + Math.sin((t.angle * Math.PI) / 180) * 14}
          strokeWidth={2}
        />
      ))}
    </g>
  )
}

// One repeating tile of vine+flower motif, in a local 220×TILE_HEIGHT coordinate space. Earlier this
// was a single viewBox scaled with preserveAspectRatio="slice" to fill the strip — but "slice" scales
// UNIFORMLY to cover both dimensions, so on any window taller (relative to 220px width) than the
// viewBox's own aspect ratio, it scaled the width right along with the height to cover the extra
// vertical space, blowing the content past the 220px container and cropping it at the edges (worse
// the taller/more "fullscreen" the window). Tiling via an SVG <pattern> instead means the strip's
// coordinate system is a flat 1-unit-to-1px match to its own pixel box — width never scales, and any
// window height is simply covered by repeating the tile, so there is nothing left to crop.
const TILE_HEIGHT = 300
const VINE_TILE_D = 'M 30 300 C 5 240, 70 200, 35 150 C 8 110, 75 70, 40 20 C 25 5, 45 -10, 65 -25'
const TILE_THORNS = [
  { x: 45, y: 260, angle: -40 },
  { x: 20, y: 195, angle: 200 },
  { x: 52, y: 100, angle: -35 },
  { x: 20, y: 35, angle: 205 },
]
const TILE_FLOWERS = [
  { cx: 40, cy: 270, scale: 1.3 },
  { cx: 70, cy: 190, scale: 0.9 },
  { cx: 24, cy: 110, scale: 1.15 },
  { cx: 58, cy: 30, scale: 1.0 },
]

/** A repeating vine+flower strip, fixed to the true left or right screen edge — tiled via SVG <pattern> (see the TILE_HEIGHT comment above) so it covers any window height without scaling or cropping. */
function EdgeStrip({ side, theme }: { side: 'left' | 'right'; theme: Theme }) {
  const patternId = `vinePattern-${side}`
  const filterId = `edgeBlur-${side}`
  const variant = theme.edgeFlowerVariants[side === 'left' ? 0 : 1]
  return (
    <svg
      className={`route-bg pointer-events-none fixed top-0 -z-10 h-full w-[220px] ${side === 'left' ? 'left-0' : 'right-0'}`}
      style={side === 'right' ? { transform: 'scaleX(-1)' } : undefined}
      aria-hidden="true"
    >
      <defs>
        <filter id={filterId} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2.2" />
        </filter>
        <pattern id={patternId} patternUnits="userSpaceOnUse" width={220} height={TILE_HEIGHT}>
          <g opacity={0.9}>
            <Vine d={VINE_TILE_D} thorns={TILE_THORNS} color={theme.vine} />
            {/* Keyed by variant, not by route or color: a same-shape route change (e.g. Birthright's
                blossom to Revelation's blossom) still gets the plain color crossfade from index.css's
                .route-bg rule below (no remount needed) — but a blossom<->rose shape change can't be
                smoothly interpolated via CSS attribute transitions (different element types/counts
                entirely), so THAT case remounts this group fresh and fades it in via the
                .route-fade-in animation instead of popping in fully opaque. */}
            <g key={variant} className="route-fade-in">
              {TILE_FLOWERS.map((f, i) => (
                <Flower key={i} cx={f.cx} cy={f.cy} scale={f.scale} petal={theme.flower} center={theme.flowerCenter} variant={variant} />
              ))}
            </g>
          </g>
        </pattern>
      </defs>
      <rect x={0} y={0} width={220} height="100%" fill={`url(#${patternId})`} filter={`url(#${filterId})`} />
    </svg>
  )
}

// A repeating "stamped" scrollwork motif — tiled across the ENTIRE background so the center reads as
// a textured, embossed card (like Fates' own title cards) instead of a flat, nebulous gradient. Same
// reasoning as TILE_HEIGHT above for why a <pattern> and not a scaled viewBox image: the motif is
// uniform in all directions so slice-scaling the *outer* gradient svg is still safe (no directional
// edge content to crop), but tiling it directly avoids any distortion of the motif's own proportions
// regardless of window size.
const STAMP_TILE = 260

/**
 * A true mathematical spiral (radius grows with angle), sampled into a polyline, plus a few short
 * feather ticks perpendicular to the curve at chosen sample points so the spiral doesn't read as a
 * bare line — same spiral-sampling idea as spiralPetalPath above, but open/unfilled and much sparser.
 */
function spiralWithFeathers(
  cx: number,
  cy: number,
  turns: number,
  startR: number,
  endR: number,
  startAngle: number,
  clockwise: boolean,
  featherIndices: number[],
  featherLen: number,
): { path: string; feathers: string[] } {
  const steps = 28
  const dir = clockwise ? 1 : -1
  const totalTheta = turns * 2 * Math.PI * dir
  const points: [number, number][] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const theta = t * totalTheta
    const r = startR + (endR - startR) * t
    const angle = startAngle + theta
    points.push([cx + Math.cos(angle) * r, cy + Math.sin(angle) * r])
  }
  const path = 'M ' + points.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join(' L ')
  const feathers = featherIndices.map((idx) => {
    const [x, y] = points[idx]
    const [px, py] = points[Math.max(0, idx - 1)]
    const tangent = Math.atan2(y - py, x - px)
    const normal = tangent + (Math.PI / 2) * dir
    const x2 = x + Math.cos(normal) * featherLen
    const y2 = y + Math.sin(normal) * featherLen
    return `M ${x.toFixed(2)} ${y.toFixed(2)} L ${x2.toFixed(2)} ${y2.toFixed(2)}`
  })
  return { path, feathers }
}

// Fixed neutral dark tone rather than a per-route color: reads as a subtle darker etching of
// whatever the base gradient happens to be (matching the reference title cards, whose scrollwork
// isn't a distinct accent color) — and, unrelated bonus, sidesteps a real rendering bug where color
// transitions on content nested inside a <pattern> that's referenced from a viewBox-scaled parent
// SVG got stuck on whichever route painted first (verified: the DOM attribute updated correctly on
// each route change, but the browser's computed/painted color never moved off the first value).
//
// Two independent flowing S-shaped chains — one horizontal (left spiral, S-stem, right spiral) and
// one vertical (top spiral, S-stem, bottom spiral) — rather than everything radiating out of one
// shared hub. Each chain is a 90-degree rotation of the other, so they cross near the tile's center
// without being joined into a single hub-and-spoke shape.
function StampPattern({ id }: { id: string }) {
  const left = spiralWithFeathers(55, 130, 1.4, 5, 42, Math.PI, true, [6, 12, 18, 23], 12)
  const right = spiralWithFeathers(205, 130, 1.4, 5, 42, 0, false, [6, 12, 18, 23], 12)
  const top = spiralWithFeathers(130, 55, 1.4, 5, 42, -Math.PI / 2, true, [6, 12, 18, 23], 12)
  const bottom = spiralWithFeathers(130, 205, 1.4, 5, 42, Math.PI / 2, false, [6, 12, 18, 23], 12)
  const horizontalStem = 'M 50 130 C 90 80, 110 80, 130 130 C 150 180, 170 180, 210 130'
  const verticalStem = 'M 130 50 C 80 90, 80 110, 130 130 C 180 150, 180 170, 130 210'
  return (
    <pattern id={id} patternUnits="userSpaceOnUse" width={STAMP_TILE} height={STAMP_TILE}>
      <g stroke="#000000" fill="none" opacity={0.17} strokeLinecap="round">
        <path d={horizontalStem} strokeWidth={2.4} />
        <path d={verticalStem} strokeWidth={2.4} />
        {[left, right, top, bottom].map((spiral, i) => (
          <g key={i}>
            <path d={spiral.path} strokeWidth={2.4} />
            {spiral.feathers.map((f, fi) => (
              <path key={fi} d={f} strokeWidth={1.6} />
            ))}
          </g>
        ))}
      </g>
    </pattern>
  )
}

// A handful of loose petals drifting across the whole card, like the game's own title cards — not
// tied to any single flower cluster or the edge-strip tiling, scattered once across the full 1600x900
// gradient. Uniform/non-directional like the stamp texture, so slice-scaling the outer svg is safe.
const FALLING_PETALS = [
  { x: 213, y: 120, rot: 25, scale: 1.1 },
  { x: 113, y: 430, rot: -60, scale: 0.85 },
  { x: 325, y: 700, rot: 110, scale: 1.0 },
  { x: 538, y: 250, rot: -20, scale: 0.7 },
  { x: 700, y: 620, rot: 70, scale: 0.6 },
  { x: 900, y: 200, rot: -95, scale: 0.65 },
  { x: 1063, y: 520, rot: 40, scale: 0.75 },
  { x: 1263, y: 150, rot: -15, scale: 1.0 },
  { x: 1400, y: 400, rot: 95, scale: 0.9 },
  { x: 1475, y: 700, rot: -50, scale: 1.05 },
]

function FallingPetals({ color }: { color: string }) {
  return (
    <g>
      {FALLING_PETALS.map((p, i) => (
        <ellipse key={i} cx={p.x} cy={p.y} rx={13 * p.scale} ry={7 * p.scale} fill={color} opacity={0.5} transform={`rotate(${p.rot}, ${p.x}, ${p.y})`} />
      ))}
    </g>
  )
}

/**
 * Full-viewport route-themed backdrop — fixed behind all app content, swaps color/flower/vine/stamp
 * theme with the active route (see index.css's `.route-bg` rule for the 1s cross-fade between
 * themes), and scales to any window size. Three layers: a plain gradient (aspect-ratio agnostic, safe
 * to scale via "slice" since it has no edge-dependent content), a tiled scrollwork "stamp" texture on
 * top of it, a vignette on top of that, and two fixed-width edge strips carrying the actual
 * flower/vine art (see EdgeStrip's comment for why those can't share the same big viewBox as the
 * gradient without risking getting cropped off-screen).
 */
export function RouteBackground({ route }: { route: Route }) {
  const theme = ROUTE_THEME[route === 'all' ? 'Revelation' : route]

  return (
    <>
      <svg
        className="route-bg pointer-events-none fixed inset-0 -z-10 h-full w-full"
        viewBox="0 0 1600 900"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="bgGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={theme.gradientFrom} />
            <stop offset="100%" stopColor={theme.gradientTo} />
          </linearGradient>
          <radialGradient id="vignette" cx="50%" cy="50%" r="75%">
            <stop offset="0%" stopColor="#000000" stopOpacity="0.85" />
            <stop offset="55%" stopColor="#000000" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0.05" />
          </radialGradient>
          <StampPattern id="stampPattern" />
        </defs>
        <rect x="0" y="0" width="1600" height="900" fill="url(#bgGradient)" />
        <rect x="0" y="0" width="1600" height="900" fill="url(#stampPattern)" />
        <FallingPetals color={theme.flower} />
        <rect x="0" y="0" width="1600" height="900" fill="url(#vignette)" />
      </svg>
      <EdgeStrip side="left" theme={theme} />
      <EdgeStrip side="right" theme={theme} />
    </>
  )
}
