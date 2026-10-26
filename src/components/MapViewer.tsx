import { useMemo, useState } from 'react'
import { useReach } from './Reach'
import { POT_TERRAIN_NOTE } from '../data/maps/fatesTerrain'
import type { MapSet } from '../data/maps/mapSet'
import type { Arrival, ChapterMap, Difficulty, Joiner, MapObject, MapUnit, Tile } from '../data/maps/types'
import type { TerrainCode } from '../data/maps/terrainCodes'
import { PixelIcon, SpriteG } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import {
  ALLY, BALLISTA, BOULDER, BURIED, CAPTURE_BADGE, CASTLE, CHEST, COMMON_ALLY, COMMON_ENEMY, COMMON_PAIR, CRACK, DOOR, DROP_BADGE, DRAGON_VEIN, FORT, GATE, HEAL, HOUSE, JOINER, LEDGE, NAMED_ENEMY, PILLAR, PIT,
  REINFORCEMENT, RUBBLE, SKULL, SNOW_PEAK, STAIRS, SUPPLIES, TORCH, FLAME, HEAL_FLOOR, DEF_FLOOR, DEF2_FLOOR, RES_FLOOR, BURNING_GROUND, TREE, VASE_MEDICINE, VASE_POISON, ARMORY, VENDOR, ARENA, PEAK,
} from '../icons/sprites'
import { applyChanges, atStart, describePotEffect, objectsAt, resolveTile, rowCodes, sameTile, terrainAt, terrainInfo, tileKey, tilesInRadius, withStandIns } from '../logic/maps'

const CELL = 10
const GUTTER = 7 // room for the axis numbers

/** A fence along a tile side. */
const FENCE = '#7c4a1e'

/** The corner marks on a tile the game deploys one of your units to itself. */
const FORCED = '#f472b6'

/** The outline round supplies to burn. */
const BURN = '#ea580c'

/** Where a tapped unit is headed. */
const GOES_TO = '#4ade80'

/** Steps between two tiles. */
const distance = (a: Tile, b: Tile) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1])

const TERRAIN_FILL: Record<TerrainCode, string> = {
  ta: '#b89a6a',
  tb: '#8a6a44',
  tc: '#a08a64',
  td: '#e0c88a',
  te: '#8a6d45',
  tf: '#5fa3bd',
  tg: '#5fa3bd',
  th: '#6f7a3a',
  ti: '#5b4a3a',
  tj: '#a8d4de',
  tk: '#d9c9a0',
  tl: '#b08c56',
  ba: '#b89a6a',
  bb: '#b89a6a',
  bc: '#8b4a8b',
  bd: '#b89a6a',
  be: '#b89a6a',
  bf: '#c4a874',
  bg: '#c8b088',
  bh: '#b89a6a',
  bi: '#c99a6a',
  bj: '#c9b0e0',
  bk: '#c9b0e0',
  bl: '#8a6d45',
  bm: '#e8eef2',
  bn: '#f4f7fb',
  bo: '#9a9488',
  bp: '#9a9488',
  bq: '#9a9488',
  br: '#9a9488',
  bs: '#7a5040',
  bt: '#2f5a2c',
  bu: '#9a8f86',
  ha: '#3fbfa8',
  hb: '#3fbfa8',
  hc: '#c0a070',
  hd: '#b89a6a',
  he: '#b89a6a',
  hf: '#9a9488',
  da: '#6f7a3a',
  db: '#5b4a3a',
  dc: '#a08060',
  dd: '#5a2a14',
  wa: '#4a443e',
  wb: '#6b5a4a',
  wc: '#e8eef2',
  wd: '#2b2f38',
  we: '#2f6f9f',
  wf: '#7cb6ea',
  wg: '#7a6a58',
  wh: '#3f5a2c',
  wi: '#5a6f80',
  wj: '#6e5a48',
  wk: '#a8d4de',
  wl: '#5fa3bd',
  wm: '#3a3550',
  wn: '#4f4236',
  oa: '#b89a6a',
  ob: '#b89a6a',
  oc: '#b89a6a',
  od: '#bfa77e',
  oe: '#d9c7a3',
  of: '#9a6b3a',
  og: '#8a4f8f',
  oh: '#6a6a7a',
  oi: '#a070c0',
  oj: '#d9c7a3',
  ok: '#d9c7a3',
  ol: '#8a8378',
  om: '#d9c7a3',
  on: '#d9c7a3',
  oo: '#c9b48a',
  sa: '#cfe3ea',
  sb: '#15121c',
}

/** Terrain that gets a pixel-art icon on top of its fill; the rest (floor, wall, water, chasm,
 * bridge, building) reads fine as colour alone. */
const TERRAIN_SPRITE: Partial<Record<TerrainCode, Sprite>> = {
  tc: STAIRS, ba: TREE, bb: FORT, bd: GATE, be: GATE, bf: GATE, bg: LEDGE, bh: PILLAR, bm: SNOW_PEAK, bo: DEF_FLOOR,
  bp: DEF2_FLOOR, bq: RES_FLOOR, br: DEF_FLOOR, ha: HEAL, hb: HEAL, hd: VASE_MEDICINE, he: HEAL, hf: HEAL_FLOOR,
  dd: BURNING_GROUND, wc: SNOW_PEAK, wh: TREE, wj: RUBBLE, oa: CHEST, ob: DOOR, oc: HOUSE, of: BALLISTA, ol: CASTLE,
  bu: PEAK, om: ARMORY, on: VENDOR, oo: ARENA,
}

/** Terrain whose icon is a small top-left badge instead (the drop badge is top-right): the Tower's floors cover
 * most of the Endgame's maps, so full-size icons would hide the map. */
const BADGE_TERRAIN = new Set<TerrainCode>(['hf', 'bo', 'bp', 'bq', 'br'])

/** The map's terrain at one phase of a cloud map: the clouds drift one tile left each phase, wrapping round. */
function withClouds(map: ChapterMap, phase: number): ChapterMap {
  const c = map.clouds
  if (!c) return map
  const grid = map.grid.map((row, r) =>
    rowCodes(row)
      .map((code, x) => {
        if (code !== 'bn' && code !== 'wf') return code
        const pattern = c.pattern[r]
        return pattern[(c.left + x + phase) % pattern.length] === '#' ? 'bn' : 'wf'
      })
      .join(''),
  )
  return { ...map, grid }
}

/** A torch is lit when it starts lit and isn't being previewed as put out, or the other way round. */
const torchLit = (c: ChapterMap['changes'][number], previewing: Set<string>) => Boolean(c.lit) !== previewing.has(c.id)

/** Every tile the lit torches light (within each one's radius, counted in steps as Fire Emblem counts range). */
function torchLight(map: ChapterMap, previewing: Set<string>): Set<string> {
  const out = new Set<string>()
  for (const c of map.changes)
    if (c.trigger === 'torch' && torchLit(c, previewing)) for (const t of tilesInRadius(map, c.tile.default, c.radius ?? 0)) out.add(tileKey(t))
  return out
}

/** Boss, named foes, allies and pairs get their own sprite; everyone else is a plain red marker. Drops are a badge on top. */
function unitSprite(u: MapUnit): Sprite {
  if (u.type === 'boss') return SKULL
  if (u.type === 'named') return NAMED_ENEMY
  // The person icon is for named green units; generic ones are a plain green dot.
  if (u.type === 'ally') return u.generic ? COMMON_ALLY : ALLY
  if (u.paired) return COMMON_PAIR
  return COMMON_ENEMY
}
const UNIT_NAME: Record<MapUnit['type'], string> = { boss: 'Boss', named: 'Named enemy', enemy: 'Enemy', ally: 'Ally' }

/** A green joiner's marker: the person icon if it's named, a plain green dot if not. */
const joinerSprite = (j: Joiner) => (!j.ally ? JOINER : j.generic ? COMMON_ALLY : ALLY)


type Pot = Extract<MapObject, { type: 'pot' }>

/** A reinforcement or joiner currently drawn on the map. */
type ShownArrival =
  | { kind: 'reinforcement'; group: string; when?: string; unit: MapUnit & { from?: Tile } }
  | { kind: 'joiner'; joiner: Joiner }

const onDifficulty = (d: Difficulty) => (u: MapUnit) => !u.difficulties || u.difficulties.includes(d)
const headcount = (units: MapUnit[]) => units.reduce((n, u) => n + (u.paired ? 2 : 1), 0)
const arrivalTile = (a: ShownArrival) => (a.kind === 'joiner' ? a.joiner.tile : a.unit.tile)
const arrivalFrom = (a: ShownArrival) => (a.kind === 'joiner' ? a.joiner.from : a.unit.from)

const INFO_BELOW_KEY = 'fe-armory-map-info-below'

/** Whether this device last put the map's info panels below it. */
function savedInfoBelow() {
  try {
    return localStorage.getItem(INFO_BELOW_KEY) === '1'
  } catch {
    return false
  }
}

/** A game's maps: its route buttons (Fates) and chapter list, a grid per chapter, and the tile, arrival and chapter panels. */
export function MapViewer({ set }: { set: MapSet }) {
  const all = set.maps
  // Under the spoiler block only the chapters you've reached are listed, and the page opens on the newest.
  const reach = useReach()
  const newest = reach.now ? all.find((m) => m.id === reach.now) : undefined
  const [mapId, setMapId] = useState((newest ?? all[0]).id)
  const picked = all.find((m) => m.id === mapId && reach.has(m.id)) ?? newest ?? all[0]
  // The block shows a map as it starts: nobody arrives later, on either side.
  const map = useMemo(() => (reach.on ? atStart(picked) : picked), [picked, reach.on])
  const [route, setRoute] = useState(set.routes ? set.routes.of(map) : '')
  // The second dropdown: a route's paralogues (Fates), or the game's side maps (trial maps).
  const paralogues = (set.routes ? set.routes.side(route) : (set.extras?.maps ?? [])).filter((m) => reach.has(m.id))
  const mainMaps = (set.routes ? set.routes.maps(route) : all.filter((m) => !(set.extras?.maps ?? []).includes(m))).filter((m) => reach.has(m.id))
  const sideLabel = set.extras?.label ?? 'Paralogues'
  const [difficulty, setDifficulty] = useState<Difficulty>(set.difficulties[0].value)
  const [selected, setSelected] = useState<Tile | null>(null)
  // Each change previews on its own toggle, never all at once.
  const [previewing, setPreviewing] = useState<Set<string>>(new Set())
  // Reinforcement groups and joiners stay hidden until asked for, so the starting layout reads cleanly.
  const [groups, setGroups] = useState<Set<string>>(new Set())
  const [showJoiners, setShowJoiners] = useState(false)
  // A cloud map's phase: 0 is turn 1's player phase, 1 its enemy phase, and so on.
  const [phase, setPhase] = useState(0)
  // Everyone a stand-in can replace (a character who died or left earlier), swapped all at once.
  const [standIns, setStandIns] = useState(false)
  // The tile, arrival and chapter panels sit beside the map, or below it so a wide map (RD's bridges, FE4) gets the full width.
  const [infoBelow, setInfoBelow] = useState(savedInfoBelow)
  function toggleInfoBelow() {
    setInfoBelow((v) => {
      try {
        localStorage.setItem(INFO_BELOW_KEY, v ? '0' : '1')
      } catch {
        // Not remembered this time.
      }
      return !v
    })
  }
  const hasStandIns = [...map.units, ...(map.reinforcements ?? []).flatMap((g) => g.units)].some((u) => u.standIn)
  const cast = useMemo(() => (standIns ? withStandIns(map) : map), [map, standIns])

  const potsBroken = map.changes.some((c) => c.breaksAllPots && previewing.has(c.id))
  // The map with every previewed change's terrain patch applied.
  // ...and with only the units present on the chosen difficulty.
  const shown = useMemo(() => {
    const patched = withClouds(applyChanges(cast, previewing), phase)
    return { ...patched, units: patched.units.filter((u) => !u.difficulties || u.difficulties.includes(difficulty)) }
  }, [cast, previewing, difficulty, phase])
  const arrivals = useMemo((): ShownArrival[] => {
    const out: ShownArrival[] = []
    for (const g of cast.reinforcements ?? []) {
      if (!groups.has(g.id)) continue
      const when = whenText(g, difficulty)
      for (const unit of g.units.filter(onDifficulty(difficulty))) out.push({ kind: 'reinforcement', group: g.label, when, unit })
    }
    if (showJoiners) for (const joiner of (map.joiners ?? []).filter(joinsOn(difficulty))) out.push({ kind: 'joiner', joiner })
    return out
  }, [map, cast, groups, showJoiners, difficulty])
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

  // Proceeding to the next chapter takes the page to its map.
  const [openedTo, setOpenedTo] = useState(reach.at)
  if (newest && openedTo !== reach.at) {
    setOpenedTo(reach.at)
    choose(newest.id)
  }

  function choose(id: string) {
    setMapId(id)
    setSelected(null)
    setPreviewing(new Set())
    setGroups(new Set())
    setShowJoiners(false)
    setPhase(0)
  }

  function chooseRoute(next: string) {
    setRoute(next)
    // A paralogue the new route can also reach stays open; anything else gives way to the route's first map.
    if (!(map.route === 'Paralogue' && map.availableIn?.some((r) => r === next))) choose(set.routes!.maps(next)[0].id)
  }

  const onParalogue = paralogues.includes(picked)
  const dlcGroups = [...new Set(mainMaps.map((m) => m.heading ?? ''))]
  const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'

  return (
    <div className="flex flex-col gap-4">
      {set.routes && (
      <div className="flex flex-wrap gap-1" role="group" aria-label="Route">
        {set.routes.list.filter((r) => !reach.on || set.routes!.maps(r).some((m) => reach.has(m.id))).map((r) => (
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
      )}
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
                        {set.chapterLabel(m)}
                      </option>
                    ))}
                </optgroup>
              ))
            : mainMaps.map((m) => (
                <option key={m.id} value={m.id}>
                  {set.chapterLabel(m)}
                </option>
              ))}
        </select>
        {paralogues.length > 0 && (
          <select value={onParalogue ? map.id : ''} onChange={(e) => choose(e.target.value)} className={select} aria-label={sideLabel}>
            {!onParalogue && (
              <option value="" disabled>
                {sideLabel} ({paralogues.length})…
              </option>
            )}
            {paralogues.map((m) => (
              <option key={m.id} value={m.id}>
                {set.chapterLabel(m)}
              </option>
            ))}
          </select>
        )}
        {set.difficulties.length > 1 && (
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as Difficulty)}
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
          >
            {set.difficulties.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        )}
        {hasStandIns && (
          <button
            type="button"
            onClick={() => setStandIns((v) => !v)}
            aria-pressed={standIns}
            className={`rounded border px-2 py-1 ${standIns ? 'border-amber-500 bg-amber-950 text-amber-200' : 'border-neutral-700 bg-neutral-900'}`}
          >
            {standIns ? 'Showing stand-ins' : 'Show stand-ins'}
          </button>
        )}
        <button
          type="button"
          onClick={toggleInfoBelow}
          aria-pressed={infoBelow}
          title="Puts the tile and chapter panels under the map, so the map can use the full width."
          className={`rounded border px-2 py-1 ${infoBelow ? 'border-emerald-500 bg-emerald-950 text-emerald-200' : 'border-neutral-700 bg-neutral-900'}`}
        >
          {infoBelow ? 'Info below the map' : 'Info beside the map'}
        </button>
        {map.clouds && (
          <select value={phase} onChange={(e) => setPhase(Number(e.target.value))} className={select} aria-label="Clouds at">
            {Array.from({ length: map.clouds.turns * 2 }, (_, i) => (
              <option key={i} value={i}>
                Clouds on turn {Math.floor(i / 2) + 1}, {i % 2 ? 'enemy' : 'player'} phase
              </option>
            ))}
          </select>
        )}
      </div>

      <div className={infoBelow ? 'flex flex-col gap-4' : 'grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,560px)_1fr]'}>
        <div className="flex flex-col gap-2">
          <MapGrid
            map={shown}
            difficulty={difficulty}
            selected={selected}
            radius={radius}
            potsBroken={potsBroken}
            previewing={previewing}
            arrivals={arrivals}
            triggers={triggers}
            onSelect={(t) => setSelected((prev) => (prev && sameTile(prev, t) ? null : t))}
          />
          <Legend map={shown} arrivals={arrivals} triggers={triggers} />
        </div>

        <div className={infoBelow ? 'grid grid-cols-1 items-start gap-4 lg:grid-cols-2' : 'flex flex-col gap-4'}>
          <TileInfo
            set={set}
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
            difficultyLabel={set.difficulties.find((d) => d.value === difficulty)?.label ?? difficulty}
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
          <ChapterInfo map={map} label={set.mapLabel(map)} />
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
  previewing,
  arrivals,
  triggers,
  onSelect,
}: {
  map: ChapterMap
  difficulty: Difficulty
  selected: Tile | null
  radius: Set<string>
  potsBroken: boolean
  previewing: Set<string>
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
  const lit = map.fog ? torchLight(map, previewing) : null
  const roofed = new Set((map.roofed ?? []).map(tileKey))
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
            {letter === 'tb' && [2, 5, 8].map((o) => <line key={o} x1={X + o} x2={X + o} y1={Y} y2={Y + 10} stroke="#6b5033" strokeWidth={0.6} />)}
            {TERRAIN_SPRITE[letter] &&
              (BADGE_TERRAIN.has(letter) ? (
                <SpriteG sprite={TERRAIN_SPRITE[letter]} x={X} y={Y} size={5} />
              ) : (
                <SpriteG sprite={TERRAIN_SPRITE[letter]} x={X} y={Y} />
              ))}
            {dark.has(tileKey(t)) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#0b0912" opacity={0.6} />}
            {lit &&
              (lit.has(tileKey(t)) ? (
                <rect x={X} y={Y} width={CELL} height={CELL} fill="#facc15" opacity={0.14} />
              ) : (
                <rect x={X} y={Y} width={CELL} height={CELL} fill="#0b0912" opacity={0.5} />
              ))}
            {roofed.has(tileKey(t)) &&
              // Hatching: three diagonals across the tile.
              [
                [0, 5, 5, 0],
                [0, 10, 10, 0],
                [5, 10, 10, 5],
              ].map(([x1, y1, x2, y2]) => (
                <line key={`${x1}${y1}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke="#1f2937" strokeOpacity={0.75} strokeWidth={0.7} />
              ))}
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

      {(map.walls ?? []).map(({ tile: [x, y], side }) => {
        const X = px(x)
        const Y = py(y)
        const [x1, y1, x2, y2] =
          side === 'n' ? [X, Y, X + CELL, Y] : side === 's' ? [X, Y + CELL, X + CELL, Y + CELL] : side === 'w' ? [X, Y, X, Y + CELL] : [X + CELL, Y, X + CELL, Y + CELL]
        return <line key={`wall${x},${y}${side}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke={FENCE} strokeWidth={1.6} strokeLinecap="round" pointerEvents="none" />
      })}

      {map.objectives.flatMap((o) =>
        o.tiles.map((t) =>
          o.type === 'burn' ? (
            <g key={`burn${tileKey(t)}`} pointerEvents="none">
              <rect x={px(t[0]) + 0.6} y={py(t[1]) + 0.6} width={CELL - 1.2} height={CELL - 1.2} fill="#f97316" fillOpacity={0.18} stroke={BURN} strokeWidth={1} strokeDasharray="2 1" />
              <SpriteG sprite={SUPPLIES} x={px(t[0])} y={py(t[1])} />
            </g>
          ) : (
            <rect key={`obj${tileKey(t)}`} x={px(t[0]) + 0.6} y={py(t[1]) + 0.6} width={CELL - 1.2} height={CELL - 1.2} fill="none" stroke="#38bdf8" strokeWidth={1.2} pointerEvents="none" />
          ),
        ),
      )}

      {map.objects.map((o) => {
        if (o.type === 'hidden') {
          // The dig area, outlined, with a glint in its middle.
          const [l, b, r, t] = o.area
          return (
            <g key={`hid${tileKey(o.tile)}`} pointerEvents="none">
              <rect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} fill="#c2410c" fillOpacity={0.14} stroke="#9a3412" strokeWidth={0.8} strokeDasharray="1.5 1" />
              <SpriteG sprite={BURIED} x={px(o.tile[0])} y={py(o.tile[1])} />
            </g>
          )
        }
        if (o.type === 'pit') return <SpriteG key={`pit${tileKey(o.tile)}`} sprite={PIT} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'fire') {
          // The house, outlined, with a flame on its corner.
          const [l, b, r, t] = o.area
          return (
            <g key={`fire${tileKey(o.tile)}`} pointerEvents="none">
              <rect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} fill="#dc2626" fillOpacity={0.12} stroke="#dc2626" strokeWidth={0.8} strokeDasharray="1.5 1" />
              <SpriteG sprite={FLAME} x={px(o.tile[0])} y={py(o.tile[1])} />
            </g>
          )
        }
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
        if (c.trigger === 'boulder') {
          // The boulder, and while previewed, the path it rolls down.
          const path = c.path ?? []
          const at = (t: Tile) => centre(t)
          return (
            <g key={c.id} pointerEvents="none">
              {previewing.has(c.id) && path.length > 1 && (
                <polyline
                  points={path.map((t) => at(t).join(',')).join(' ')}
                  fill="none"
                  stroke="#f5f5f4"
                  strokeWidth={1.1}
                  strokeDasharray="2 1"
                  markerEnd="url(#arrival-head)"
                />
              )}
            </g>
          )
        }
        if (c.trigger === 'torch') {
          // Dim until it's previewed as lit.
          return <SpriteG key={c.id} sprite={TORCH} x={px(x)} y={py(y)} opacity={torchLit(c, previewing) ? 1 : 0.55} />
        }
        if (c.trigger === 'breakable') {
          // Once previewed as broken, the crack goes: the tile is open ground then.
          return previewing.has(c.id) ? null : <SpriteG key={c.id} sprite={CRACK} x={px(x)} y={py(y)} />
        }
        return <SpriteG key={c.id} sprite={DRAGON_VEIN} x={px(x)} y={py(y)} className="animate-pulse" />
      })}

      {/* Keyed by position in the list too: two units can share a tile (one per difficulty), and a repeated key
          leaves a stray sprite behind when the map changes. */}
      {map.units.map((u, i) => (
        <g key={`${i}:${tileKey(u.tile)}`}>
          <SpriteG sprite={unitSprite(u)} x={px(u.tile[0])} y={py(u.tile[1])} />
          {u.drops?.length ? <SpriteG sprite={DROP_BADGE} x={px(u.tile[0]) + 5.4} y={py(u.tile[1]) - 0.4} size={5} /> : null}
          {u.capturable && <SpriteG sprite={CAPTURE_BADGE} x={px(u.tile[0]) + 5.4} y={py(u.tile[1]) + 5.4} size={5} />}
        </g>
      ))}

      {/* Boulders on top of units: a rock-pusher often stands on one (Ch.25), so it shows as a corner badge then. */}
      {map.changes
        .filter((c) => c.trigger === 'boulder')
        .map((c) => {
          const [x, y] = resolveTile(c.tile, difficulty)
          const occupied = map.units.some((u) => sameTile(u.tile, [x, y]))
          return occupied ? (
            <SpriteG key={`rock${c.id}`} sprite={BOULDER} x={px(x) - 0.4} y={py(y) + 5.4} size={5} />
          ) : (
            <SpriteG key={`rock${c.id}`} sprite={BOULDER} x={px(x)} y={py(y)} />
          )
        })}

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
            <SpriteG sprite={a.kind === 'joiner' ? joinerSprite(a.joiner) : REINFORCEMENT} x={px(x)} y={py(y)} />
            {a.kind === 'reinforcement' && a.unit.drops?.length ? <SpriteG sprite={DROP_BADGE} x={px(x) + 5.4} y={py(y) - 0.4} size={5} /> : null}
          </g>
        )
      })}

      {map.units
        .filter((u) => u.goesTo?.length && selected && sameTile(u.tile, selected))
        .map((u, i) => {
          const goal = u.goesTo!
          const near = goal.reduce((a, b) => (distance(u.tile, b) < distance(u.tile, a) ? b : a))
          const [x1, y1] = centre(u.tile)
          const [x2, y2] = centre(near)
          return (
            <g key={`goes${i}`} pointerEvents="none">
              {goal.map((t) => (
                <rect key={tileKey(t)} x={px(t[0]) + 0.4} y={py(t[1]) + 0.4} width={CELL - 0.8} height={CELL - 0.8} fill={GOES_TO} fillOpacity={0.3} stroke={GOES_TO} strokeWidth={1.2} />
              ))}
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={GOES_TO} strokeWidth={0.9} strokeDasharray="1.6 1" markerEnd="url(#arrival-head)" />
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
  const codes = new Set([...map.grid.flatMap(rowCodes), ...map.changes.flatMap((c) => (c.patch ?? []).map((p) => p.becomes))])
  const pots = map.objects.filter((o): o is Pot => o.type === 'pot')
  const items: { label: string; sprite?: Sprite; swatch?: string; outline?: boolean; corners?: string }[] = []
  if (pots.some((p) => p.pot === 'medicine')) items.push({ label: 'Medicine pot', sprite: VASE_MEDICINE })
  if (pots.some((p) => p.pot === 'poison')) items.push({ label: 'Poison pot', sprite: VASE_POISON })
  if (map.changes.some((c) => c.trigger === 'dragonVein')) items.push({ label: 'Dragon Vein', sprite: DRAGON_VEIN })
  if (map.changes.some((c) => c.trigger === 'breakable')) items.push({ label: 'Breakable', sprite: CRACK })
  if (map.changes.some((c) => c.trigger === 'boulder')) items.push({ label: 'Boulder (tap to see its path)', sprite: BOULDER })
  if (map.walls?.length) items.push({ label: 'Fence (no crossing)', swatch: FENCE })
  if (map.objects.some((o) => o.type === 'hidden')) items.push({ label: 'Hidden item (dig area)', sprite: BURIED })
  if (map.objects.some((o) => o.type === 'pit')) items.push({ label: 'Pit trap', sprite: PIT })
  if (map.objects.some((o) => o.type === 'fire')) items.push({ label: 'House the arsonists can set alight', sprite: FLAME })
  if (map.changes.some((c) => c.trigger === 'torch')) items.push({ label: 'Torch (tap it to light it)', sprite: TORCH })
  if (map.fog) items.push({ label: 'Fog (hidden until seen)', swatch: '#3b3542' })
  if (map.roofed?.length) items.push({ label: 'Under a roof: check in-game', swatch: '#4b5563' })
  const unitKinds = new Map<string, Sprite>()
  for (const u of map.units) {
    const label =
      u.type === 'enemy' ? (u.paired ? 'Paired enemies' : 'Enemy') : u.type === 'ally' ? (u.generic ? 'Ally' : 'Named ally') : UNIT_NAME[u.type]
    unitKinds.set(label, unitSprite(u))
  }
  for (const [label, sprite] of unitKinds) items.push({ label, sprite })
  if (map.units.some((u) => u.drops?.length)) items.push({ label: 'Drops an item', sprite: DROP_BADGE })
  if (map.units.some((u) => u.capturable)) items.push({ label: 'Can be captured', sprite: CAPTURE_BADGE })
  if (arrivals.some((a) => a.kind === 'reinforcement')) items.push({ label: 'Reinforcement', sprite: REINFORCEMENT })
  if (arrivals.some((a) => a.kind === 'joiner' && !a.joiner.ally)) items.push({ label: 'Joins your army', sprite: JOINER })
  if (arrivals.some((a) => a.kind === 'joiner' && a.joiner.ally && !a.joiner.generic)) items.push({ label: 'Named green unit arrives', sprite: ALLY })
  if (arrivals.some((a) => a.kind === 'joiner' && a.joiner.ally && a.joiner.generic)) items.push({ label: 'Green unit arrives', sprite: COMMON_ALLY })
  if (triggers.length) items.push({ label: 'Area that brings a group in', swatch: '#f0883e', outline: true })
  if (map.objectives.some((o) => o.type !== 'burn')) items.push({ label: 'Objective', swatch: '#38bdf8', outline: true })
  if (map.objectives.some((o) => o.type === 'burn')) items.push({ label: 'Supplies to burn (objective)', sprite: SUPPLIES })
  if (map.units.some((u) => u.goesTo)) items.push({ label: 'Where the tapped unit is headed', swatch: GOES_TO, outline: true })
  if (map.starts.length) items.push({ label: 'Starting tile', corners: '#3b82f6' })
  if (map.corrinStart) items.push({ label: "Lord's start", corners: '#facc15' })
  if (map.forced?.some((f) => f.tile)) items.push({ label: 'Forced unit (fixed tile)', corners: FORCED })
  for (const l of codes) {
    if (l === 'ta') continue
    items.push({ label: terrainInfo(map, l).name, sprite: TERRAIN_SPRITE[l], swatch: TERRAIN_FILL[l] })
  }
  const unique = items.filter((it, i) => items.findIndex((o) => o.label === it.label) === i)
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-neutral-400">
      {unique.map((it) => (
        <span key={it.label} className="flex items-center gap-1">
          {it.sprite ? (
            <PixelIcon sprite={it.sprite} size={16} />
          ) : it.corners ? (
            // The same corner marks the map draws on a starting tile.
            <svg width={16} height={16} viewBox="0 0 10 10" className="inline-block shrink-0 rounded-sm bg-[#b89a6a]" aria-hidden>
              <g fill={it.corners}>
                <path d="M0 0h3l-3 3z" />
                <path d="M10 10h-3l3 -3z" />
              </g>
            </svg>
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
  set,
  map,
  difficulty,
  tile,
  potsBroken,
  previewing,
  arrivals,
  onTogglePreview,
  onReset,
}: {
  set: MapSet
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
        Tap a tile to see what's on it.{map.objects.some((o) => o.type === 'pot') && ' Tapping a pot shades every tile its effect reaches.'}
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
  const castle = objects.find((o) => o.type === 'castle')
  const shop = objects.find((o) => o.type === 'shop')
  const hidden = objects.filter((o) => o.type === 'hidden')
  // A ballista shows on its firing tile and on the machine beside it.
  const ballista = map.objects.find((o) => o.type === 'ballista' && (sameTile(o.tile, tile) || sameTile(o.machine, tile)))
  const pit = objects.find((o) => o.type === 'pit')
  const fire = objects.find((o) => o.type === 'fire')
  const inFog = map.fog && !torchLight(map, previewing).has(tileKey(tile))
  const underRoof = map.roofed?.some((t) => sameTile(t, tile))
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
          {u.carries?.length ? <p className="text-neutral-300">Carries {[...new Set(u.carries)].join(', ')}</p> : null}
          {u.talk && <p className="text-sky-300">{u.talk}</p>}
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
          {u.goesTo && <p className="text-green-300">Heads for {u.goesTo.map((t) => `(${t[0]}, ${t[1]})`).join(' / ')}, outlined in green.</p>}
        </div>
      ))}

      {here.map((a, i) =>
        a.kind === 'joiner' ? (
          <p key={`j${i}`} className={a.joiner.ally ? 'text-green-300' : 'text-blue-300'}>
            <PixelIcon sprite={joinerSprite(a.joiner)} /> {a.joiner.ally ? 'Arrives as a green unit' : 'Joins your army'}:{' '}
            <span className="font-medium">{a.joiner.name}</span>
            {!sameTile(a.joiner.from, a.joiner.tile) && <span className="text-neutral-400"> · walks in from {where(a.joiner.from, map)}</span>}
            {whenText(a.joiner, difficulty) && <span className="block text-neutral-400">{whenText(a.joiner, difficulty)}</span>}
            {a.joiner.talk && <span className="block text-sky-300">{a.joiner.talk}</span>}
            {a.joiner.note && <span className="block text-neutral-400">{a.joiner.note}</span>}
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
            {a.unit.carries?.length ? <p className="text-neutral-300">Carries {[...new Set(a.unit.carries)].join(', ')}</p> : null}
            {a.unit.drops?.map((d) => (
              <p key={d} className="text-amber-300">
                <PixelIcon sprite={DROP_BADGE} /> Drops {d}
              </p>
            ))}
          </div>
        ),
      )}

      {(map.walls ?? [])
        .filter((w) => sameTile(w.tile, tile))
        .map((w) => (
          <p key={w.side} className="text-amber-200">
            Fence on the {{ n: 'north', e: 'east', s: 'south', w: 'west' }[w.side]} side: no unit can cross it there.
          </p>
        ))}

      {map.dark?.some((t) => sameTile(t, tile)) && (
        <p className="text-neutral-400">Under darkness: nothing can enter until the chapter lifts it.</p>
      )}

      {objectives.map((o) =>
        o.type === 'burn' ? (
          <p key={o.label} className="text-orange-300">
            <PixelIcon sprite={SUPPLIES} /> {o.label}
          </p>
        ) : (
          <p key={o.label} className="text-sky-300">
            Objective: {o.label}
          </p>
        ),
      )}

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
      {ballista?.type === 'ballista' && (
        <p className="text-amber-300">
          <PixelIcon sprite={BALLISTA} /> {ballista.weapon}
          <span className="text-neutral-400">
            {' '}
            · {sameTile(ballista.tile, tile) ? `an archer or sniper standing here fires the machine beside them, at (${ballista.machine[0]}, ${ballista.machine[1]})` : `fired by an archer or sniper standing at (${ballista.tile[0]}, ${ballista.tile[1]})`}
          </span>
        </p>
      )}
      {inFog && <p className="text-neutral-400">In the fog: hidden unless one of your units, or a lit torch, can see it.</p>}
      {underRoof && (
        <p className="text-amber-200">Under a roof that lifts when what's inside is opened: check in-game what this tile holds.</p>
      )}
      {fire && (
        <p className="text-red-300">
          <PixelIcon sprite={FLAME} /> A house the enemy's arsonists can set alight
          <span className="text-neutral-400"> · a unit next to it once it burns can put it out.</span>
        </p>
      )}
      {pit && (
        <p className="text-amber-300">
          <PixelIcon sprite={PIT} /> Pit trap
          <span className="text-neutral-400">
            {' '}
            · a ground unit that moves onto it falls in and can't move again until next turn (it can still counterattack). A flier
            doesn't fall, and while one stands on it, others can cross.
          </span>
        </p>
      )}
      {hidden.map(
        (h) =>
          h.type === 'hidden' && (
            <div key={h.contents}>
              <p className="text-amber-300">
                <PixelIcon sprite={BURIED} /> Hidden: {h.contents}
              </p>
              <p className="text-neutral-400">
                {h.note ??
                  'Buried somewhere in the outlined area. A unit that moves into it has a (Skill + 1)% chance to dig it up; Thieves and Assassins always find it.'}
              </p>
            </div>
          ),
      )}
      {castle?.type === 'castle' && (
        <p className="text-sky-200">
          <PixelIcon sprite={CASTLE} /> Castle: <span className="font-medium">{castle.name}</span>
          {castle.note && <span className="block text-neutral-400">{castle.note}</span>}
        </p>
      )}
      {shop?.type === 'shop' && (
        <p className="text-amber-200">
          {shop.kind}: <span className="text-neutral-300">sells {shop.stock.join(', ')}</span>
        </p>
      )}
      {village?.type === 'village' && (
        <p className="text-amber-300">
          Village:{' '}
          {village.reward
            ? `visit for ${/^\d/.test(village.reward) ? '' : /^[AEIOU]/i.test(village.reward) ? 'an ' : 'a '}${village.reward}`
            : !village.note && 'a visit gives nothing'}
          {village.note && <span className="text-neutral-400"> {village.note}</span>}
        </p>
      )}

      {changes.map((c) => (
        <div key={c.id} className="rounded border border-cyan-900 bg-cyan-950/40 p-2">
          <p className="text-cyan-300">
            {c.trigger === 'breakable' ? 'Breakable' : c.trigger === 'boulder' ? 'Boulder' : c.trigger === 'torch' ? `Torch, lit by: ${c.usableBy}` : `Dragon Vein, usable by: ${c.usableBy}`}
          </p>
          <p className="text-neutral-300">{c.effect}</p>
          {c.tile.Lunatic && <p className="text-neutral-500">This vein's tile changes with difficulty; showing {difficulty}.</p>}
          <div className="mt-2 flex gap-2">
            <button
              onClick={() => onTogglePreview(c.id)}
              className="rounded border border-cyan-700 px-2 py-0.5 text-cyan-200 hover:bg-cyan-900"
            >
              {c.trigger === 'torch' ? (torchLit(c, previewing) ? 'Put it out' : 'Light it') : previewing.has(c.id) ? 'Stop preview' : c.trigger === 'boulder' ? 'Show its path' : 'Preview'}
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
          <p className="text-yellow-300">{map.lord ?? set.lord}'s starting tile</p>
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
                {!set.noTerrainDef && ` · Def ${fmt(terrain.def)}`}
                {terrain.res !== undefined && ` · Res ${fmt(terrain.res)}`} · Avo {fmt(terrain.avo)}
                {terrain.heal > 0 && ` · Heals ${terrain.heal}% per turn`}
              </span>
            </p>
            {terrain.note && <p className="text-neutral-400">{terrain.note}</p>}
            {set.terrainNote && (terrain.def !== 0 || terrain.avo !== 0) && <p className="text-neutral-500">{set.terrainNote}</p>}
            <details className="mt-1">
              <summary className="cursor-pointer text-neutral-400 hover:text-neutral-200">Movement cost by class type</summary>
              <table className="mt-1 w-full text-xs">
                <tbody>
                  {set.moveClasses.map((mc) => {
                    const cost = terrain.move[mc]
                    return (
                      <tr key={mc} className="border-b border-neutral-900" title={set.moveClassExamples[mc]}>
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

/** Whether a joiner comes on this difficulty: one timed per difficulty comes only on those listed. */
const joinsOn = (difficulty: Difficulty) => (j: Joiner) => !j.when || typeof j.when === 'string' || j.when[difficulty] !== undefined

/** Joiners who arrive together, as "Silas, Elise". */
function joinerGroups(joiners: Joiner[]) {
  const byGroup = new Map<string, Joiner[]>()
  for (const j of joiners) byGroup.set(j.group, [...(byGroup.get(j.group) ?? []), j])
  return [...byGroup.values()].map((js) => ({ names: js.map((j) => j.name).join(', '), joiner: js[0] }))
}

function ArrivalsPanel({
  map,
  difficulty,
  difficultyLabel,
  groups,
  showJoiners,
  onToggleGroup,
  onSetGroups,
  onToggleJoiners,
}: {
  map: ChapterMap
  difficulty: Difficulty
  difficultyLabel: string
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
  const joiners = (map.joiners ?? []).filter(joinsOn(difficulty))
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
            {list.length} {list.length === 1 ? 'group' : 'groups'} on {difficultyLabel}
            {list.length > 1 && <> ({total} units across them)</>}
            {map.randomSpawns
              ? ': enemies spawn at these points at random, on no set turn, so not every group arrives in one playthrough.'
              : ", timed by the chapter's own script."}{' '}
            Arrows run from where each unit enters to where it stops; dashed outlines mark the areas that bring a group in.
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

function ChapterInfo({ map, label }: { map: ChapterMap; label: string }) {
  return (
    <section className="flex flex-col gap-2 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h3 className="font-semibold text-neutral-100">
        {label}
      </h3>
      {map.location && <p className="text-neutral-500">{map.location}</p>}
      {map.victory && (
        <p>
          <span className="text-emerald-400">Win:</span> {map.victory}
        </p>
      )}
      {map.defeat && (
        <p>
          <span className="text-red-400">Lose:</span> {map.defeat}
        </p>
      )}
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
