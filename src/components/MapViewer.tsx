import { useMemo, useState } from 'react'
import { ALL_MAPS, mapLabel } from '../data/maps'
import { MOVE_CLASSES, MOVE_CLASS_EXAMPLES, POT_TERRAIN_NOTE } from '../data/maps/fatesTerrain'
import type { ChapterMap, Difficulty, MapObject, MapUnit, TerrainLetter, Tile } from '../data/maps/types'
import { DIFFICULTIES } from '../data/maps/types'
import { PixelIcon, SpriteG } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import {
  ALLY, CAPTURE_BADGE, CHEST, COMMON_DROPPER, COMMON_ENEMY, COMMON_PAIR, DOOR, DROP_BADGE, DRAGON_VEIN, FORT, GATE, HEAL, HOUSE, NAMED_ENEMY, PILLAR, RUBBLE, SKULL, SNOW_PEAK, STAIRS,
  TREE, VASE_MEDICINE, VASE_POISON,
} from '../icons/sprites'
import { applyChanges, describePotEffect, objectsAt, resolveTile, sameTile, terrainAt, terrainInfo, tileKey, tilesInRadius } from '../logic/maps'

const CELL = 10
const GUTTER = 7 // room for the axis numbers

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
  x: '#3b4a52',
  F: '#b89a6a',
  G: '#b89a6a',
  B: '#d9c7a3',
  v: '#b89a6a',
  n: '#e8eef2',
  W: '#8a6d45',
  g: '#b89a6a',
  k: '#3f5a2c',
  a: '#4f8fb0',
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
}

/** Terrain that gets a pixel-art icon on top of its fill; the rest (floor, wall, water, chasm,
 * bridge, building) reads fine as colour alone. */
const TERRAIN_SPRITE: Partial<Record<TerrainLetter, Sprite>> = {
  p: PILLAR, f: TREE, S: STAIRS, c: CHEST, d: DOOR, r: RUBBLE, H: HEAL, F: FORT, G: GATE, g: GATE, e: GATE, v: HOUSE, n: SNOW_PEAK, k: TREE,
}

/** Boss, named foes and item-droppers get attention; everyone else is a plain red marker. */
function unitSprite(u: MapUnit): Sprite {
  if (u.type === 'boss') return SKULL
  if (u.type === 'named') return NAMED_ENEMY
  if (u.type === 'ally') return ALLY
  if (u.paired) return COMMON_PAIR
  return u.drops?.length ? COMMON_DROPPER : COMMON_ENEMY
}
const UNIT_NAME: Record<MapUnit['type'], string> = { boss: 'Boss', named: 'Named enemy', enemy: 'Enemy', ally: 'Ally' }


type Pot = Extract<MapObject, { type: 'pot' }>

export function MapViewer() {
  const [mapId, setMapId] = useState(ALL_MAPS[0].id)
  const map = ALL_MAPS.find((m) => m.id === mapId) ?? ALL_MAPS[0]
  const [difficulty, setDifficulty] = useState<Difficulty>('Normal')
  const [selected, setSelected] = useState<Tile | null>(null)
  // Each change previews on its own toggle, never all at once.
  const [previewing, setPreviewing] = useState<Set<string>>(new Set())

  const potsBroken = map.changes.some((c) => c.breaksAllPots && previewing.has(c.id))
  // The map with every previewed change's terrain patch applied.
  // ...and with only the units present on the chosen difficulty.
  const shown = useMemo(() => {
    const patched = applyChanges(map, previewing)
    return { ...patched, units: patched.units.filter((u) => !u.difficulties || u.difficulties.includes(difficulty)) }
  }, [map, previewing, difficulty])
  const selectedPot = selected
    ? (objectsAt(map, selected).find((o) => o.type === 'pot') as Pot | undefined)
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

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={map.id}
          onChange={(e) => {
            setMapId(e.target.value)
            setSelected(null)
            setPreviewing(new Set())
          }}
          className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        >
          {ALL_MAPS.map((m) => (
            <option key={m.id} value={m.id}>
              {mapLabel(m)}
            </option>
          ))}
        </select>
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
            onSelect={(t) => setSelected((prev) => (prev && sameTile(prev, t) ? null : t))}
          />
          <Legend map={shown} />
        </div>

        <div className="flex flex-col gap-4">
          <TileInfo
            map={shown}
            difficulty={difficulty}
            tile={selected}
            potsBroken={potsBroken}
            previewing={previewing}
            onTogglePreview={togglePreview}
            onReset={() => setPreviewing(new Set())}
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
  onSelect,
}: {
  map: ChapterMap
  difficulty: Difficulty
  selected: Tile | null
  radius: Set<string>
  potsBroken: boolean
  onSelect: (t: Tile) => void
}) {
  // SVG y grows downward, map y grows upward: screen row = height - y.
  const px = (x: number) => GUTTER + (x - 1) * CELL
  const py = (y: number) => (map.height - y) * CELL
  const tiles: Tile[] = []
  for (let y = map.height; y >= 1; y--) for (let x = 1; x <= map.width; x++) tiles.push([x, y])
  const starts = new Set(map.starts.map(tileKey))

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
            {radius.has(tileKey(t)) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#ffffff" opacity={0.22} />}
            {starts.has(tileKey(t)) && (
              <g fill={map.corrinStart && sameTile(map.corrinStart, t) ? '#facc15' : '#3b82f6'}>
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

function Legend({ map }: { map: ChapterMap }) {
  // Only what this map actually has, so small maps get a short legend.
  const letters = new Set([...map.grid.join(''), ...map.changes.flatMap((c) => (c.patch ?? []).map((p) => p.becomes))])
  const pots = map.objects.filter((o): o is Pot => o.type === 'pot')
  const items: { label: string; sprite?: Sprite; swatch?: string; outline?: boolean }[] = []
  if (pots.some((p) => p.pot === 'medicine')) items.push({ label: 'Medicine pot', sprite: VASE_MEDICINE })
  if (pots.some((p) => p.pot === 'poison')) items.push({ label: 'Poison pot', sprite: VASE_POISON })
  if (map.changes.length) items.push({ label: 'Dragon Vein', sprite: DRAGON_VEIN })
  const unitKinds = new Map<string, Sprite>()
  for (const u of map.units) {
    const label = u.type === 'enemy' ? (u.paired ? 'Paired enemies' : u.drops?.length ? 'Enemy with a drop' : 'Enemy') : UNIT_NAME[u.type]
    unitKinds.set(label, unitSprite(u))
  }
  for (const [label, sprite] of unitKinds) items.push({ label, sprite })
  if (map.units.some((u) => u.drops?.length)) items.push({ label: 'Drops an item', sprite: DROP_BADGE })
  if (map.units.some((u) => u.capturable)) items.push({ label: 'Can be captured', sprite: CAPTURE_BADGE })
  if (map.objectives.length) items.push({ label: 'Objective', swatch: '#38bdf8', outline: true })
  if (map.starts.length) items.push({ label: 'Starting tile', swatch: '#3b82f6' })
  if (map.corrinStart) items.push({ label: "Corrin's start", swatch: '#facc15' })
  for (const l of letters as Set<TerrainLetter>) {
    if (l === '.') continue
    items.push({ label: terrainInfo(map, l).name, sprite: TERRAIN_SPRITE[l], swatch: TERRAIN_FILL[l] })
  }
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-neutral-400">
      {items.map((it) => (
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
  onTogglePreview,
  onReset,
}: {
  map: ChapterMap
  difficulty: Difficulty
  tile: Tile | null
  potsBroken: boolean
  previewing: Set<string>
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
      {village?.type === 'village' && <p className="text-amber-300">Village: visit for a {village.reward}</p>}

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
      <p className="text-xs text-neutral-500">
        Sources:{' '}
        {map.sources.map((s, i) => (
          <span key={s.label}>
            {i > 0 && ' · '}
            {s.url ? (
              <a href={s.url} target="_blank" rel="noreferrer" className="underline hover:text-neutral-300">
                {s.label}
              </a>
            ) : (
              s.label
            )}
          </span>
        ))}
      </p>
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
