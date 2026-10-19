import { useMemo, useState } from 'react'
import { ALL_MAPS, MAP_ROUTES, chapterLabel, mapLabel, mapRoute, routeMaps, routeParalogues } from '../data/maps'
import type { MapRoute } from '../data/maps'
import { MOVE_CLASSES, MOVE_CLASS_EXAMPLES, POT_TERRAIN_NOTE } from '../data/maps/fatesTerrain'
import type { Arrival, ChapterMap, Difficulty, Joiner, MapObject, MapUnit, TerrainLetter, Tile } from '../data/maps/types'
import { DIFFICULTIES } from '../data/maps/types'
import { PixelIcon, SpriteG } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import {
  ALLY, CAPTURE_BADGE, CHEST, COMMON_ENEMY, COMMON_PAIR, DOOR, DROP_BADGE, DRAGON_VEIN, FORT, GATE, HEAL, HOUSE, JOINER, NAMED_ENEMY, PILLAR, REINFORCEMENT,
  RUBBLE, SKULL, SNOW_PEAK, STAIRS, TREE, VASE_MEDICINE, VASE_POISON,
} from '../icons/sprites'
import { applyChanges, describePotEffect, objectsAt, resolveTile, sameTile, terrainAt, terrainInfo, tileKey, tilesInRadius } from '../logic/maps'

const CELL = 10
const GUTTER = 7 // room for the axis numbers

/** The corner marks on a tile the game deploys one of your units to itself. */
const FORCED = '#f472b6'

const TERRAIN_FILL: Record<TerrainLetter, string> = {
  '.': '#b89a6a',
  '#': '#4a443e',
  p: '#b89a6a',
  f: '#b89a6a',
  w: '#5fa3bd',
  S: '#a08a64',
  c: '#b89a6a',
  d: '#b89a6a',
  t: '#8b4a8b',
  b: '#8a6a44',
  r: '#6e5a48',
  H: '#3fbfa8',
  x: '#2b2f38',
  F: '#b89a6a',
  G: '#b89a6a',
  B: '#d9c7a3',
  v: '#b89a6a',
  n: '#e8eef2',
  W: '#8a6d45',
  g: '#b89a6a',
  k: '#3f5a2c',
  a: '#2f6f9f',
  l: '#7a6a58',
  C: '#6b5a4a',
  L: '#9a6b3a',
  O: '#8a4f8f',
  U: '#6a6a7a',
  T: '#a08060',
  D: '#3a3550',
  e: '#c4a874',
  Q: '#c99a6a',
  V: '#bfa77e',
  z: '#5a6f80',
  j: '#c0a070',
  i: '#cfe3ea',
  s: '#e0c88a',
  P: '#6f7a3a',
  X: '#15121c',
  K: '#c9b0e0',
  u: '#a8d4de',
  Y: '#a070c0',
  M: '#5b4a3a',
  Z: '#7a5040',
  E: '#c8b088',
}

/** Terrain that gets a pixel-art icon on top of its fill; the rest (floor, wall, water, chasm,
 * bridge, building) reads fine as colour alone. */
const TERRAIN_SPRITE: Partial<Record<TerrainLetter, Sprite>> = {
  p: PILLAR, f: TREE, S: STAIRS, c: CHEST, d: DOOR, r: RUBBLE, H: HEAL, F: FORT, G: GATE, g: GATE, e: GATE, v: HOUSE, n: SNOW_PEAK, k: TREE,
}

/** Boss, named foes, allies and pairs get their own sprite; everyone else is a plain red marker. Drops are a badge on top. */
function unitSprite(u: MapUnit): Sprite {
  if (u.type === 'boss') return SKULL
  if (u.type === 'named') return NAMED_ENEMY
  if (u.type === 'ally') return ALLY
  if (u.paired) return COMMON_PAIR
  return COMMON_ENEMY
}
const UNIT_NAME: Record<MapUnit['type'], string> = { boss: 'Boss', named: 'Named enemy', enemy: 'Enemy', ally: 'Ally' }


type Pot = Extract<MapObject, { type: 'pot' }>

/** A reinforcement or joiner currently drawn on the map. */
type ShownArrival =
  | { kind: 'reinforcement'; group: string; when?: string; unit: MapUnit & { from?: Tile } }
  | { kind: 'joiner'; joiner: Joiner }

const onDifficulty = (d: Difficulty) => (u: MapUnit) => !u.difficulties || u.difficulties.includes(d)
const headcount = (units: MapUnit[]) => units.reduce((n, u) => n + (u.paired ? 2 : 1), 0)
const arrivalTile = (a: ShownArrival) => (a.kind === 'joiner' ? a.joiner.tile : a.unit.tile)
const arrivalFrom = (a: ShownArrival) => (a.kind === 'joiner' ? a.joiner.from : a.unit.from)

export function MapViewer() {
  const [mapId, setMapId] = useState(ALL_MAPS[0].id)
  const map = ALL_MAPS.find((m) => m.id === mapId) ?? ALL_MAPS[0]
  const [route, setRoute] = useState<MapRoute>(mapRoute(map))
  const mainMaps = routeMaps(route)
  const paralogues = route === 'Prologue' || route === 'DLC' ? [] : routeParalogues(route)
  const [difficulty, setDifficulty] = useState<Difficulty>('Normal')
  const [selected, setSelected] = useState<Tile | null>(null)
  // Each change previews on its own toggle, never all at once.
  const [previewing, setPreviewing] = useState<Set<string>>(new Set())
  // Reinforcement groups and joiners stay hidden until asked for, so the starting layout reads cleanly.
  const [groups, setGroups] = useState<Set<string>>(new Set())
  const [showJoiners, setShowJoiners] = useState(false)

  const potsBroken = map.changes.some((c) => c.breaksAllPots && previewing.has(c.id))
  // The map with every previewed change's terrain patch applied.
  // ...and with only the units present on the chosen difficulty.
  const shown = useMemo(() => {
    const patched = applyChanges(map, previewing)
    return { ...patched, units: patched.units.filter((u) => !u.difficulties || u.difficulties.includes(difficulty)) }
  }, [map, previewing, difficulty])
  const arrivals = useMemo((): ShownArrival[] => {
    const out: ShownArrival[] = []
    for (const g of map.reinforcements ?? []) {
      if (!groups.has(g.id)) continue
      const when = whenText(g, difficulty)
      for (const unit of g.units.filter(onDifficulty(difficulty))) out.push({ kind: 'reinforcement', group: g.label, when, unit })
    }
    if (showJoiners) for (const joiner of map.joiners ?? []) out.push({ kind: 'joiner', joiner })
    return out
  }, [map, groups, showJoiners, difficulty])
  // The map areas whose entry brings in a group that's being shown.
  const triggers = useMemo(() => {
    const seen = new Map<string, NonNullable<Arrival['areas']>[number]>()
    for (const g of map.reinforcements ?? []) {
      if (!groups.has(g.id)) continue
      for (const a of g.areas ?? []) seen.set(`${a.who}${a.rect.join(',')}`, a)
    }
    return [...seen.values()]
  }, [map, groups])
  const selectedPot = selected
    ?(objectsAt(map, selected).find((o) => o.type === 'pot') as Pot | undefined)
    : undefined
  const radius = useMemo(
    () => new Set(selectedPot && !potsBroken ? tilesInRadius(map, selectedPot.tile, selectedPot.radius).map(tileKey) : []),
    [map, selectedPot, potsBroken],
  )

  function togglePreview(id: string) {
    setPreviewing((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function choose(id: string) {
    setMapId(id)
    setSelected(null)
    setPreviewing(new Set())
    setGroups(new Set())
    setShowJoiners(false)
  }

  function chooseRoute(next: MapRoute) {
    setRoute(next)
    // A paralogue the new route can also reach stays open; anything else gives way to the route's first map.
    if (!(map.route === 'Paralogue' && map.availableIn?.some((r) => r === next))) choose(routeMaps(next)[0].id)
  }

  const onParalogue = map.route === 'Paralogue'
  const dlcGroups = [...new Set(mainMaps.map((m) => m.heading ?? ''))]
  const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-1" role="group" aria-label="Route">
        {MAP_ROUTES.map((r) => (
          <button
            key={r}
            onClick={() => chooseRoute(r)}
            aria-pressed={route === r}
            className={`rounded border px-3 py-1 text-sm ${
              route === r ? 'border-emerald-500 bg-emerald-950/60 text-emerald-100' : 'border-neutral-700 text-neutral-300 hover:bg-neutral-800'
            }`}
          >
            {r}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <select value={onParalogue ? '' : map.id} onChange={(e) => choose(e.target.value)} className={select} aria-label="Chapter">
          {onParalogue && (
            <option value="" disabled>
              Story chapters…
            </option>
          )}
          {route === 'DLC'
            ? dlcGroups.map((g) => (
                <optgroup key={g} label={g === 'Xenologue' ? 'Xenologues' : g === 'Hero Battle' ? 'amiibo Hero Battles' : g}>
                  {mainMaps
                    .filter((m) => (m.heading ?? '') === g)
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {chapterLabel(m)}
                      </option>
                    ))}
                </optgroup>
              ))
            : mainMaps.map((m) => (
                <option key={m.id} value={m.id}>
                  {chapterLabel(m)}
                </option>
              ))}
        </select>
        {paralogues.length > 0 && (
          <select value={onParalogue ? map.id : ''} onChange={(e) => choose(e.target.value)} className={select} aria-label="Paralogue">
            {!onParalogue && (
              <option value="" disabled>
                Paralogues ({paralogues.length})…
              </option>
            )}
            {paralogues.map((m) => (
              <option key={m.id} value={m.id}>
                {chapterLabel(m)}
              </option>
            ))}
          </select>
        )}
        <select
          value={difficulty}
          onChange={(e) => setDifficulty(e.target.value as Difficulty)}
          className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        >
          {DIFFICULTIES.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,560px)_1fr]">
        <div className="flex flex-col gap-2">
          <MapGrid
            map={shown}
            difficulty={difficulty}
            selected={selected}
            radius={radius}
            potsBroken={potsBroken}
            arrivals={arrivals}
            triggers={triggers}
            onSelect={(t) => setSelected((prev) => (prev && sameTile(prev, t) ? null : t))}
          />
          <Legend map={shown} arrivals={arrivals} triggers={triggers} />
        </div>

        <div className="flex flex-col gap-4">
          <TileInfo
            map={shown}
            difficulty={difficulty}
            tile={selected}
            potsBroken={potsBroken}
            previewing={previewing}
            arrivals={arrivals}
            onTogglePreview={togglePreview}
            onReset={() => setPreviewing(new Set())}
          />
          <ArrivalsPanel
            map={map}
            difficulty={difficulty}
            groups={groups}
            showJoiners={showJoiners}
            onToggleGroup={(id) =>
              setGroups((prev) => {
                const next = new Set(prev)
                if (next.has(id)) next.delete(id)
                else next.add(id)
                return next
              })
            }
            onSetGroups={setGroups}
            onToggleJoiners={() => setShowJoiners((v) => !v)}
          />
          <ChapterInfo map={map} />
        </div>
      </div>

      <PotList map={map} onSelect={setSelected} selected={selected} broken={potsBroken} />
    </div>
  )
}

function MapGrid({
  map,
  difficulty,
  selected,
  radius,
  potsBroken,
  arrivals,
  triggers,
  onSelect,
}: {
  map: ChapterMap
  difficulty: Difficulty
  selected: Tile | null
  radius: Set<string>
  potsBroken: boolean
  arrivals: ShownArrival[]
  triggers: NonNullable<Arrival['areas']>
  onSelect: (t: Tile) => void
}) {
  // SVG y grows downward, map y grows upward: screen row = height - y.
  const px = (x: number) => GUTTER + (x - 1) * CELL
  const py = (y: number) => (map.height - y) * CELL
  const tiles: Tile[] = []
  for (let y = map.height; y >= 1; y--) for (let x = 1; x <= map.width; x++) tiles.push([x, y])
  const starts = new Set(map.starts.map(tileKey))
  const dark = new Set((map.dark ?? []).map(tileKey))
  const fixed = new Set((map.forced ?? []).flatMap((f) => (f.tile ? [tileKey(f.tile)] : [])))
  // Tile centre in SVG units; a unit walking in from off the map starts its arrow at the edge.
  const centre = ([x, y]: Tile) => {
    const cx = Math.min(Math.max(x, 0.5), map.width + 0.5)
    const cy = Math.min(Math.max(y, 0.5), map.height + 0.5)
    return [GUTTER + (cx - 1) * CELL + CELL / 2, (map.height - cy) * CELL + CELL / 2] as const
  }
  // One marker per tile even when several groups arrive on it; the tile panel lists them all.
  const arrivalMarkers = new Map<string, ShownArrival>()
  for (const a of arrivals) if (!arrivalMarkers.has(tileKey(arrivalTile(a)))) arrivalMarkers.set(tileKey(arrivalTile(a)), a)

  return (
    <svg
      viewBox={`0 0 ${GUTTER + map.width * CELL} ${map.height * CELL + GUTTER}`}
      className="w-full select-none rounded border border-neutral-800 bg-neutral-950"
      role="grid"
      aria-label={`${map.title} map`}
    >
      {tiles.map((t) => {
        const [x, y] = t
        const letter = terrainAt(map, t)
        const X = px(x)
        const Y = py(y)
        return (
          <g key={tileKey(t)} onClick={() => onSelect(t)} className="cursor-pointer">
            <rect x={X} y={Y} width={CELL} height={CELL} fill={TERRAIN_FILL[letter]} />
            {letter === 'b' && [2, 5, 8].map((o) => <line key={o} x1={X + o} x2={X + o} y1={Y} y2={Y + 10} stroke="#6b5033" strokeWidth={0.6} />)}
            {TERRAIN_SPRITE[letter] && <SpriteG sprite={TERRAIN_SPRITE[letter]} x={X} y={Y} />}
            {dark.has(tileKey(t)) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#0b0912" opacity={0.6} />}
            {radius.has(tileKey(t)) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#ffffff" opacity={0.22} />}
            {starts.has(tileKey(t)) && (
              <g fill={map.corrinStart && sameTile(map.corrinStart, t) ? '#facc15' : fixed.has(tileKey(t)) ? FORCED : '#3b82f6'}>
                <path d={`M${X} ${Y}h3l-3 3z`} />
                <path d={`M${X + 10} ${Y + 10}h-3l3 -3z`} />
              </g>
            )}
          </g>
        )
      })}

      {/* Grid lines, drawn once on top of the terrain. */}
      {Array.from({ length: map.width + 1 }, (_, i) => (
        <line key={`v${i}`} x1={GUTTER + i * CELL} x2={GUTTER + i * CELL} y1={0} y2={map.height * CELL} stroke="#000" strokeOpacity={0.15} strokeWidth={0.3} pointerEvents="none" />
      ))}
      {Array.from({ length: map.height + 1 }, (_, i) => (
        <line key={`h${i}`} x1={GUTTER} x2={GUTTER + map.width * CELL} y1={i * CELL} y2={i * CELL} stroke="#000" strokeOpacity={0.15} strokeWidth={0.3} pointerEvents="none" />
      ))}

      {map.objectives.flatMap((o) =>
        o.tiles.map((t) => (
          <rect key={`obj${tileKey(t)}`} x={px(t[0]) + 0.6} y={py(t[1]) + 0.6} width={CELL - 1.2} height={CELL - 1.2} fill="none" stroke="#38bdf8" strokeWidth={1.2} pointerEvents="none" />
        )),
      )}

      {map.objects.map((o) => {
        if (o.type !== 'pot') return null
        const X = px(o.tile[0])
        const Y = py(o.tile[1])
        return (
          <SpriteG
            key={`pot${tileKey(o.tile)}`}
            sprite={o.pot === 'medicine' ? VASE_MEDICINE : VASE_POISON}
            x={X}
            y={Y}
            opacity={potsBroken ? 0.2 : 1}
          />
        )
      })}

      {map.changes.map((c) => {
        const [x, y] = resolveTile(c.tile, difficulty)
        return (
          <SpriteG key={c.id} sprite={DRAGON_VEIN} x={px(x)} y={py(y)} className="animate-pulse" />
        )
      })}

      {map.units.map((u) => (
        <g key={tileKey(u.tile)}>
          <SpriteG sprite={unitSprite(u)} x={px(u.tile[0])} y={py(u.tile[1])} />
          {u.drops?.length ? <SpriteG sprite={DROP_BADGE} x={px(u.tile[0]) + 5.4} y={py(u.tile[1]) - 0.4} size={5} /> : null}
          {u.capturable && <SpriteG sprite={CAPTURE_BADGE} x={px(u.tile[0]) + 5.4} y={py(u.tile[1]) + 5.4} size={5} />}
        </g>
      ))}

      {triggers.map(({ who, rect: [l, b, r, t] }) => (
        <rect
          key={`trig${who}${l},${b},${r},${t}`}
          x={px(l) + 0.5}
          y={py(t) + 0.5}
          width={(r - l + 1) * CELL - 1}
          height={(t - b + 1) * CELL - 1}
          fill={who === 'enemy' ? '#ef4444' : '#f0883e'}
          fillOpacity={0.08}
          stroke={who === 'enemy' ? '#ef4444' : '#f0883e'}
          strokeWidth={0.7}
          strokeDasharray="2 1.2"
          pointerEvents="none"
        />
      ))}
      <defs>
        <marker id="arrival-head" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="3" markerHeight="3" orient="auto">
          <path d="M0 0L6 3L0 6z" fill="context-stroke" />
        </marker>
      </defs>
      {arrivals.map((a, i) => {
        const from = arrivalFrom(a)
        const to = arrivalTile(a)
        if (!from || sameTile(from, to)) return null
        const [x1, y1] = centre(from)
        const [x2, y2] = centre(to)
        return (
          <line
            key={`arrow${i}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke={a.kind === 'joiner' ? '#60a5fa' : '#f0883e'}
            strokeWidth={0.9}
            strokeDasharray="1.6 1"
            markerEnd="url(#arrival-head)"
            pointerEvents="none"
          />
        )
      })}
      {[...arrivalMarkers.values()].map((a) => {
        const [x, y] = arrivalTile(a)
        return (
          <g key={`arr${x},${y}`} pointerEvents="none">
            <SpriteG sprite={a.kind === 'joiner' ? JOINER : REINFORCEMENT} x={px(x)} y={py(y)} />
            {a.kind === 'reinforcement' && a.unit.drops?.length ? <SpriteG sprite={DROP_BADGE} x={px(x) + 5.4} y={py(y) - 0.4} size={5} /> : null}
          </g>
        )
      })}

      {selected && (
        <rect x={px(selected[0]) + 0.3} y={py(selected[1]) + 0.3} width={CELL - 0.6} height={CELL - 0.6} fill="none" stroke="#fff" strokeWidth={0.8} pointerEvents="none" />
      )}

      {Array.from({ length: map.width }, (_, i) => (
        <text key={`x${i}`} x={GUTTER + i * CELL + 5} y={map.height * CELL + 5} textAnchor="middle" fontSize={3.4} fill="#737373">
          {i + 1}
        </text>
      ))}
      {Array.from({ length: map.height }, (_, i) => (
        <text key={`y${i}`} x={GUTTER - 1.2} y={i * CELL + 6.2} textAnchor="end" fontSize={3.4} fill="#737373">
          {map.height - i}
        </text>
      ))}
    </svg>
  )
}

function Legend({ map, arrivals, triggers }: { map: ChapterMap; arrivals: ShownArrival[]; triggers: NonNullable<Arrival['areas']> }) {
  // Only what this map actually has, so small maps get a short legend.
  const letters = new Set([...map.grid.join(''), ...map.changes.flatMap((c) => (c.patch ?? []).map((p) => p.becomes))])
  const pots = map.objects.filter((o): o is Pot => o.type === 'pot')
  const items: { label: string; sprite?: Sprite; swatch?: string; outline?: boolean }[] = []
  if (pots.some((p) => p.pot === 'medicine')) items.push({ label: 'Medicine pot', sprite: VASE_MEDICINE })
  if (pots.some((p) => p.pot === 'poison')) items.push({ label: 'Poison pot', sprite: VASE_POISON })
  if (map.changes.length) items.push({ label: 'Dragon Vein', sprite: DRAGON_VEIN })
  const unitKinds = new Map<string, Sprite>()
  for (const u of map.units) {
    const label = u.type === 'enemy' ? (u.paired ? 'Paired enemies' : 'Enemy') : UNIT_NAME[u.type]
    unitKinds.set(label, unitSprite(u))
  }
  for (const [label, sprite] of unitKinds) items.push({ label, sprite })
  if (map.units.some((u) => u.drops?.length)) items.push({ label: 'Drops an item', sprite: DROP_BADGE })
  if (map.units.some((u) => u.capturable)) items.push({ label: 'Can be captured', sprite: CAPTURE_BADGE })
  if (arrivals.some((a) => a.kind === 'reinforcement')) items.push({ label: 'Reinforcement', sprite: REINFORCEMENT })
  if (arrivals.some((a) => a.kind === 'joiner')) items.push({ label: 'Joins your army', sprite: JOINER })
  if (triggers.length) items.push({ label: 'Area that brings a group in', swatch: '#f0883e', outline: true })
  if (map.objectives.length) items.push({ label: 'Objective', swatch: '#38bdf8', outline: true })
  if (map.starts.length) items.push({ label: 'Starting tile', swatch: '#3b82f6' })
  if (map.corrinStart) items.push({ label: "Corrin's start", swatch: '#facc15' })
  if (map.forced?.some((f) => f.tile)) items.push({ label: 'Forced unit (fixed tile)', swatch: FORCED })
  for (const l of letters as Set<TerrainLetter>) {
    if (l === '.') continue
    items.push({ label: terrainInfo(map, l).name, sprite: TERRAIN_SPRITE[l], swatch: TERRAIN_FILL[l] })
  }
  const unique = items.filter((it, i) => items.findIndex((o) => o.label === it.label) === i)
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-neutral-400">
      {unique.map((it) => (
        <span key={it.label} className="flex items-center gap-1">
          {it.sprite ? (
            <PixelIcon sprite={it.sprite} size={16} />
          ) : (
            <span
              className="inline-block h-3 w-3 rounded-sm"
              style={it.outline ? { border: `2px solid ${it.swatch}` } : { background: it.swatch }}
            />
          )}
          {it.label}
        </span>
      ))}
    </div>
  )
}

function TileInfo({
  map,
  difficulty,
  tile,
  potsBroken,
  previewing,
  arrivals,
  onTogglePreview,
  onReset,
}: {
  map: ChapterMap
  difficulty: Difficulty
  tile: Tile | null
  potsBroken: boolean
  previewing: Set<string>
  arrivals: ShownArrival[]
  onTogglePreview: (id: string) => void
  onReset: () => void
}) {
  if (!tile) {
    return (
      <section className="rounded border border-neutral-800 p-4 text-sm text-neutral-500">
        Tap a tile to see what's on it. Tapping a pot shades every tile its effect reaches.
      </section>
    )
  }

  const letter = terrainAt(map, tile)
  const terrain = terrainInfo(map, letter)
  const units = map.units.filter((u) => sameTile(u.tile, tile))
  const objectives = map.objectives.filter((o) => o.tiles.some((t) => sameTile(t, tile)))
  const objects = objectsAt(map, tile)
  const pot = objects.find((o) => o.type === 'pot') as Pot | undefined
  const chest = objects.find((o) => o.type === 'chest')
  const village = objects.find((o) => o.type === 'village')
  const changes = map.changes.filter((c) => sameTile(resolveTile(c.tile, difficulty), tile))
  const isStart = map.starts.some((t) => sameTile(t, tile))
  const fixedHere = map.forced?.find((f) => f.tile && sameTile(f.tile, tile))
  const here = arrivals.filter((a) => sameTile(arrivalTile(a), tile))

  return (
    <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm">
      <h3 className="font-semibold text-neutral-100">
        Tile ({tile[0]}, {tile[1]})
      </h3>

      {units.map((u, i) => (
        <div key={`${u.name}-${i}`}>
          <p className={u.type === 'ally' ? 'text-green-300' : 'text-red-300'}>
            <PixelIcon sprite={unitSprite(u)} /> {UNIT_NAME[u.type]}: <span className="font-medium">{u.name}</span>
            {u.paired && !u.partner && u.type === 'enemy' && ' (two, paired up)'}
          </p>
          {u.partner && <p className="text-neutral-300">Paired up with: {u.partner}</p>}
          {u.drops?.map((d) => (
            <p key={d} className="text-amber-300">
              <PixelIcon sprite={DROP_BADGE} /> Drops {d}
            </p>
          ))}
          {u.capturable && (
            <p className="text-neutral-300">
              <PixelIcon sprite={CAPTURE_BADGE} /> Can be captured
            </p>
          )}
          {u.note && <p className="text-neutral-400">{u.note}</p>}
        </div>
      ))}

      {here.map((a, i) =>
        a.kind === 'joiner' ? (
          <p key={`j${i}`} className="text-blue-300">
            <PixelIcon sprite={JOINER} /> Joins your army: <span className="font-medium">{a.joiner.name}</span>
            {!sameTile(a.joiner.from, a.joiner.tile) && <span className="text-neutral-400"> · walks in from {where(a.joiner.from, map)}</span>}
            {whenText(a.joiner, difficulty) && <span className="block text-neutral-400">{whenText(a.joiner, difficulty)}</span>}
          </p>
        ) : (
          <div key={`r${i}`}>
            <p className="text-orange-300">
              <PixelIcon sprite={REINFORCEMENT} /> Reinforcement ({a.group}): <span className="font-medium">{a.unit.name}</span>
              {a.unit.paired && !a.unit.partner && ' (two, paired up)'}
              {a.unit.from && !sameTile(a.unit.from, a.unit.tile) && (
                <span className="text-neutral-400"> · enters from {where(a.unit.from, map)}</span>
              )}
            </p>
            {a.when && <p className="text-neutral-400">Arrives: {a.when}</p>}
            {a.unit.partner && <p className="text-neutral-300">Paired up with: {a.unit.partner}</p>}
            {a.unit.drops?.map((d) => (
              <p key={d} className="text-amber-300">
                <PixelIcon sprite={DROP_BADGE} /> Drops {d}
              </p>
            ))}
          </div>
        ),
      )}

      {map.dark?.some((t) => sameTile(t, tile)) && (
        <p className="text-neutral-400">Under darkness: nothing can enter until the chapter lifts it.</p>
      )}

      {objectives.map((o) => (
        <p key={o.label} className="text-sky-300">
          Objective: {o.label}
        </p>
      ))}

      {pot && (
        <div>
          <p className={pot.pot === 'medicine' ? 'text-emerald-300' : 'text-fuchsia-300'}>
            {pot.pot === 'medicine' ? 'Medicine pot' : 'Poison pot'}
            {potsBroken && ' (broken by the vein preview)'}
          </p>
          <p className="text-neutral-200">{describePotEffect(pot.effect)}</p>
          <p className="text-neutral-400">
            Hits every unit, yours and the enemy's, within {pot.radius} tiles when broken.
          </p>
        </div>
      )}

      {chest?.type === 'chest' && <p className="text-amber-300">Chest: {chest.contents}</p>}
      {village?.type === 'village' && (
        <p className="text-amber-300">
          Village: {village.reward ? `visit for ${/^\d/.test(village.reward) ? '' : /^[AEIOU]/.test(village.reward) ? 'an ' : 'a '}${village.reward}` : 'a visit gives nothing'}
          {village.note && <span className="text-neutral-400"> {village.note}</span>}
        </p>
      )}

      {changes.map((c) => (
        <div key={c.id} className="rounded border border-cyan-900 bg-cyan-950/40 p-2">
          <p className="text-cyan-300">Dragon Vein, usable by: {c.usableBy}</p>
          <p className="text-neutral-300">{c.effect}</p>
          {c.tile.Lunatic && <p className="text-neutral-500">This vein's tile changes with difficulty; showing {difficulty}.</p>}
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => onTogglePreview(c.id)}
              className="rounded border border-cyan-700 px-2 py-0.5 text-cyan-200 hover:bg-cyan-900"
            >
              {previewing.has(c.id) ? 'Stop preview' : 'Preview'}
            </button>
            {previewing.size > 0 && (
              <button onClick={onReset} className="rounded border border-neutral-700 px-2 py-0.5 text-neutral-300 hover:bg-neutral-800">
                Reset map
              </button>
            )}
          </div>
        </div>
      ))}

      {isStart &&
        (map.corrinStart && sameTile(map.corrinStart, tile) ? (
          <p className="text-yellow-300">Corrin's starting tile</p>
        ) : fixedHere ? (
          <p className="text-pink-300">Forced deployment: {fixedHere.name}, placed here by the game</p>
        ) : (
          <p className="text-blue-300">Starting tile</p>
        ))}

      <div className="border-t border-neutral-800 pt-2">
        {pot && !potsBroken ? (
          <>
            <p className="text-neutral-200">Terrain: Pot</p>
            <p className="text-neutral-400">{POT_TERRAIN_NOTE}</p>
          </>
        ) : (
          <>
            <p className="text-neutral-200">
              Terrain: {terrain.name}
              <span className="text-neutral-400">
                {' '}
                · Def {fmt(terrain.def)} · Avo {fmt(terrain.avo)}
                {terrain.heal > 0 && ` · Heals ${terrain.heal}% per turn`}
              </span>
            </p>
            {terrain.note && <p className="text-neutral-400">{terrain.note}</p>}
            {(terrain.def !== 0 || terrain.avo !== 0) && <p className="text-neutral-500">Fliers get no Def/Avo from terrain.</p>}
            <details className="mt-1">
              <summary className="cursor-pointer text-neutral-400 hover:text-neutral-200">Movement cost by class type</summary>
              <table className="mt-1 w-full text-xs">
                <tbody>
                  {MOVE_CLASSES.map((mc) => {
                    const cost = terrain.move[mc]
                    return (
                      <tr key={mc} className="border-b border-neutral-900" title={MOVE_CLASS_EXAMPLES[mc]}>
                        <td className="py-0.5 pr-2 text-neutral-400">{mc}</td>
                        <td className={cost === null ? 'text-neutral-600' : 'text-neutral-200'}>{cost === null ? "Can't enter" : cost}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </details>
          </>
        )}
      </div>
    </section>
  )
}

const fmt = (n: number) => (n > 0 ? `+${n}` : String(n))

/** Tiles off the map (where a unit walks in from) read as "off the left edge, by (1, 16)". */
function where([x, y]: Tile, map: ChapterMap): string {
  const side = x < 1 ? 'left' : x > map.width ? 'right' : y < 1 ? 'bottom' : y > map.height ? 'top' : null
  if (!side) return `(${x}, ${y})`
  return `off the ${side} edge, by (${Math.min(Math.max(x, 1), map.width)}, ${Math.min(Math.max(y, 1), map.height)})`
}

/** A group's arrival sentence for the chosen difficulty, if the script gave one. */
function whenText(a: Arrival, difficulty: Difficulty): string | undefined {
  if (!a.when) return undefined
  return typeof a.when === 'string' ? a.when : a.when[difficulty]
}

/** Joiners who arrive together, as "Silas, Elise". */
function joinerGroups(joiners: Joiner[]) {
  const byGroup = new Map<string, Joiner[]>()
  for (const j of joiners) byGroup.set(j.group, [...(byGroup.get(j.group) ?? []), j])
  return [...byGroup.values()].map((js) => ({ names: js.map((j) => j.name).join(', '), joiner: js[0] }))
}

function ArrivalsPanel({
  map,
  difficulty,
  groups,
  showJoiners,
  onToggleGroup,
  onSetGroups,
  onToggleJoiners,
}: {
  map: ChapterMap
  difficulty: Difficulty
  groups: Set<string>
  showJoiners: boolean
  onToggleGroup: (id: string) => void
  onSetGroups: (ids: Set<string>) => void
  onToggleJoiners: () => void
}) {
  // Only the groups that bring anyone on this difficulty.
  const list = (map.reinforcements ?? [])
    .map((g) => ({ ...g, count: headcount(g.units.filter(onDifficulty(difficulty))) }))
    .filter((g) => g.count > 0)
  const joiners = map.joiners ?? []
  if (list.length === 0 && joiners.length === 0) return null
  const total = list.reduce((n, g) => n + g.count, 0)
  const chip = (on: boolean) =>
    `rounded border px-2 py-0.5 text-xs ${on ? 'border-orange-500 bg-orange-950/60 text-orange-200' : 'border-neutral-700 text-neutral-300 hover:bg-neutral-800'}`
  return (
    <section className="flex flex-col gap-2 rounded border border-neutral-800 p-4 text-sm">
      <h3 className="font-semibold text-neutral-100">Reinforcements & joiners</h3>
      {list.length > 0 && (
        <>
          <p className="text-neutral-400">
            {list.length} {list.length === 1 ? 'group' : 'groups'} on {difficulty}
            {list.length > 1 && <> ({total} units across them)</>}, timed by the chapter's own script. Some only come if a
            condition is met, so not every group arrives in one playthrough. Arrows run from where each unit enters to where it
            stops; dashed outlines mark the areas that bring a group in.
          </p>
          <ul className="flex flex-col gap-1">
            {list.map((g) => (
              <li key={g.id} className="flex items-start gap-2">
                <button onClick={() => onToggleGroup(g.id)} aria-pressed={groups.has(g.id)} className={`${chip(groups.has(g.id))} shrink-0`}>
                  {g.label} · {g.count}
                </button>
                <span className="text-xs text-neutral-400">{whenText(g, difficulty) ?? "Timing not found in the chapter's script."}</span>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <button onClick={() => onSetGroups(new Set(list.map((g) => g.id)))} className={chip(false)}>
              Show all
            </button>
            {groups.size > 0 && (
              <button onClick={() => onSetGroups(new Set())} className={chip(false)}>
                Hide all
              </button>
            )}
          </div>
        </>
      )}
      {joiners.length > 0 && (
        <div className="flex flex-col gap-1 border-t border-neutral-800 pt-2">
          <div>
            <button onClick={onToggleJoiners} aria-pressed={showJoiners} className={chip(showJoiners)}>
              {showJoiners ? 'Hide joiners' : 'Show joiners'}
            </button>
          </div>
          <ul className="text-xs text-neutral-400">
            {joinerGroups(joiners).map(({ names, joiner }) => (
              <li key={names}>
                <span className="text-blue-300">{names}</span>
                {whenText(joiner, difficulty) && <> · {whenText(joiner, difficulty)}</>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function ChapterInfo({ map }: { map: ChapterMap }) {
  return (
    <section className="flex flex-col gap-2 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h3 className="font-semibold text-neutral-100">
        {mapLabel(map)}
      </h3>
      {map.location && <p className="text-neutral-500">{map.location}</p>}
      <p>
        <span className="text-emerald-400">Win:</span> {map.victory}
      </p>
      <p>
        <span className="text-red-400">Lose:</span> {map.defeat}
      </p>
      {map.forced?.some((f) => !f.tile) && (
        <p>
          <span className="text-pink-300">Must deploy:</span>{' '}
          {map.forced.filter((f) => !f.tile).map((f) => f.name).join(', ')} <span className="text-neutral-500">(you choose the tile)</span>
        </p>
      )}
      {map.forced?.some((f) => f.tile) && (
        <p>
          <span className="text-pink-300">Placed by the game:</span>{' '}
          {map.forced
            .filter((f) => f.tile)
            .map((f) => `${f.name} (${f.tile![0]}, ${f.tile![1]})`)
            .join(', ')}
        </p>
      )}
      <ul className="list-disc space-y-1 pl-5 text-neutral-400">
        {map.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
      {map.unconfirmed && map.unconfirmed.length > 0 && (
        <div className="rounded border border-amber-900 bg-amber-950/30 p-2">
          <p className="text-amber-300">Not yet confirmed in-game</p>
          <ul className="list-disc space-y-1 pl-5 text-amber-200/80">
            {map.unconfirmed.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function PotList({ map, selected, broken, onSelect }: { map: ChapterMap; selected: Tile | null; broken: boolean; onSelect: (t: Tile) => void }) {
  const pots = map.objects.filter((o): o is Pot => o.type === 'pot')
  if (pots.length === 0) return null
  // Top of the map first, like reading the grid.
  const sorted = [...pots].sort((a, b) => b.tile[1] - a.tile[1] || a.tile[0] - b.tile[0])
  return (
    <section className="grid grid-cols-1 gap-4 rounded border border-neutral-800 p-4 text-sm md:grid-cols-2">
      {(['medicine', 'poison'] as const).map((kind) => {
        const list = sorted.filter((p) => p.pot === kind)
        return (
          <div key={kind}>
            <h3 className={`mb-1 font-semibold ${kind === 'medicine' ? 'text-emerald-300' : 'text-fuchsia-300'}`}>
              {kind === 'medicine' ? 'Medicine' : 'Poison'} pots ({list.length})
            </h3>
            <ul className={broken ? 'opacity-50' : ''}>
              {list.map((p) => (
                <li key={tileKey(p.tile)}>
                  <button
                    onClick={() => onSelect(p.tile)}
                    className={`w-full rounded px-1 text-left hover:bg-neutral-800 ${selected && sameTile(selected, p.tile) ? 'bg-neutral-800' : ''}`}
                  >
                    <span className="inline-block w-16 text-neutral-500">
                      ({p.tile[0]}, {p.tile[1]})
                    </span>
                    {describePotEffect(p.effect)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </section>
  )
}
