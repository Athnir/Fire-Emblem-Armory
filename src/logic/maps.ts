import type { ChapterMap, Difficulty, DifficultyTile, MapChange, MapObject, MapUnit, PotEffect, StatKey, Tile } from '../data/maps/types'
import type { TerrainCode } from '../data/maps/terrainCodes'
import { FATES_TERRAIN } from '../data/maps/fatesTerrain'
import type { TerrainInfo } from '../data/maps/fatesTerrain'

export const tileKey = ([x, y]: Tile) => `${x},${y}`
export const sameTile = (a: Tile, b: Tile) => a[0] === b[0] && a[1] === b[1]

/** Whether a unit stands on a tile: its own, or any of the square a unit of several tiles covers (`MapUnit.size`: its tile is the
 * square's top-left, the square running right and down from it). */
export const covers = (u: { tile: Tile; size?: number }, [x, y]: Tile) => {
  const s = u.size ?? 1
  return x >= u.tile[0] && x < u.tile[0] + s && y <= u.tile[1] && y > u.tile[1] - s
}

/** A grid row's tiles: two characters each. */
export function rowCodes(row: string): TerrainCode[] {
  const out: TerrainCode[] = []
  for (let i = 0; i < row.length; i += 2) out.push(row.slice(i, i + 2) as TerrainCode)
  return out
}

/** Terrain code at (x, y), bottom-left (1, 1). The grid is stored top row first, two characters a tile. */
export function terrainAt(map: ChapterMap, [x, y]: Tile): TerrainCode {
  return map.grid[map.height - y].slice(2 * (x - 1), 2 * x) as TerrainCode
}

/**
 * A unit's note as the picked difficulty has it. The data keeps one entry for a unit that differs between difficulties only by
 * level, its Normal level first and the others beside it: 'Lv 4 (Easy 6, Hard 5) Soldier' reads 'Lv 6 Soldier' on Easy.
 */
export function noteOn(note: string, difficulty: Difficulty): string {
  return note.replace(/^Lv (\d+) \(((?:(?:Easy|Normal|Hard|Lunatic|Maniac) \d+(?:, )?)+)\)/, (_, normal: string, others: string) => {
    const own = others.split(', ').find((x) => x.startsWith(`${difficulty} `))
    return `Lv ${own ? own.split(' ')[1] : normal}`
  })
}

/** A chapter's notes on the picked difficulty: those for every difficulty, then the ones that hold on it only; under the spoiler
 * block, a note that holds from a later map waits for it (`has`: whether a map is reached). */
export function notesOn(map: ChapterMap, difficulty: Difficulty, has: (mapId: string) => boolean = () => true): string[] {
  return [
    ...map.notes,
    ...(map.notesOn ?? []).filter((n) => n.difficulties.includes(difficulty) && (!n.from || has(n.from))).map((n) => n.note),
  ]
}

export function resolveTile(tile: DifficultyTile, difficulty: Difficulty): Tile {
  return tile[difficulty] ?? tile.default
}

/** Every on-map tile within `radius` steps (Fire Emblem's range: |dx| + |dy|), the centre included. */
export function tilesInRadius(map: ChapterMap, [cx, cy]: Tile, radius: number): Tile[] {
  const out: Tile[] = []
  for (let dx = -radius; dx <= radius; dx++) {
    for (let dy = -radius; dy <= radius; dy++) {
      const x = cx + dx
      const y = cy + dy
      if (Math.abs(dx) + Math.abs(dy) <= radius && x >= 1 && x <= map.width && y >= 1 && y <= map.height) out.push([x, y])
    }
  }
  return out
}

/** The map as it looks with the given changes applied (each one's terrain patch laid over the base grid): a turn's changes first,
 * in turn order, since each is made on the map as the turns before left it. */
export function applyChanges(map: ChapterMap, active: Set<string>, extra: NonNullable<MapChange['patch']> = []): ChapterMap {
  const order = (c: MapChange) => c.turn ?? Number.MAX_SAFE_INTEGER
  const made = map.changes.filter((c) => active.has(c.id)).sort((a, b) => order(a) - order(b))
  const patches = [...made.flatMap((c) => c.patch ?? []), ...extra]
  if (patches.length === 0) return map
  const rows = map.grid.map(rowCodes)
  for (const { tile: [x, y], becomes } of patches) rows[map.height - y][x - 1] = becomes
  return { ...map, grid: rows.map((r) => r.join('')) }
}

/**
 * Which switching walls are up (Revelation 16's flame walls): all of them, then the battle's start set down, then each turn's
 * flips up to `turn` (at the start of its player phase), then the flips of the veins in `flipped`.
 */
export function wallsUp(map: ChapterMap, start: number, turn: number, flipped: number[] = []): Set<number> {
  const sw = map.switchWalls
  if (!sw) return new Set()
  const up = new Set(sw.walls.map((w) => w.id))
  const flip = (id: number) => (up.has(id) ? up.delete(id) : up.add(id))
  for (const id of sw.starts[start] ?? []) flip(id)
  for (let t = 2; t <= turn; t++) for (const s of sw.turns) if (t >= s.from && t % s.every === 0) s.walls.forEach(flip)
  flipped.forEach(flip)
  return up
}

/** The map with its switching walls set by the battle's start set, the turn and the previewed veins: a wall tile stays as the
 * grid has it while any wall on it is up, and turns `down` once every one is. */
export function withSwitchWalls(map: ChapterMap, start: number, turn: number, previewing: Set<string>): ChapterMap {
  const sw = map.switchWalls
  if (!sw) return map
  const flipped = map.changes.filter((c) => c.flips !== undefined && previewing.has(c.id)).map((c) => c.flips!)
  const up = wallsUp(map, start, turn, flipped)
  const lit = new Set(sw.walls.filter((w) => up.has(w.id)).flatMap((w) => w.tiles.map(tileKey)))
  const rows = map.grid.map(rowCodes)
  for (const w of sw.walls) for (const [x, y] of w.tiles) if (!lit.has(tileKey([x, y]))) rows[map.height - y][x - 1] = sw.down
  return { ...map, grid: rows.map((r) => r.join('')) }
}

/** The map with every character who has a stand-in swapped for it, on the map and in the reinforcements. */
export function withStandIns(map: ChapterMap): ChapterMap {
  const swap = <U extends MapUnit>(u: U): U => {
    if (!u.standIn) return u
    const { when, ...s } = u.standIn
    const { standIn: _, talk: _t, goesTo: _g, partner: _p, paired: _q, capturable: _c, drops: _d, steal: _s, generic: _n, ...place } = u
    return { ...place, ...s, note: `${s.note}. Stands here if ${when}.` } as U
  }
  return {
    ...map,
    units: map.units.map(swap),
    reinforcements: map.reinforcements?.map((g) => ({ ...g, units: g.units.map(swap) })),
    // Joiners and units the game deploys can have stand-ins too (Genealogy of the Holy War's substitutes).
    joiners: map.joiners?.map((j) => {
      if (!j.standIn) return j
      const { when, name, note, talk, generic } = j.standIn
      const { standIn: _, talk: _t, generic: _n, ...place } = j
      return { ...place, name, ...(talk ? { talk } : {}), ...(generic ? { generic } : {}), note: `${note ? `${note}. ` : ''}Stands here if ${when}.` }
    }),
    forced: map.forced?.map((f) => (f.standIn ? { name: f.standIn.name, tile: f.tile } : f)),
  }
}

/** Terrain stats for a code on this map, with the map's own overrides applied. */
export function terrainInfo(map: ChapterMap, code: TerrainCode): TerrainInfo {
  const base = (map.terrain?.[code] ?? FATES_TERRAIN[code]) as TerrainInfo
  const o = map.terrainOverrides?.[code]
  return o ? { ...base, ...o } : base
}

/** A tile's own terrain name: where its code joins several of the game's names ("Plain / Sigil"), the one this tile has. */
export function terrainName(map: ChapterMap, tile: Tile): string {
  const info = terrainInfo(map, terrainAt(map, tile))
  const own = Object.entries(info.tileNames ?? {}).find(([, ts]) => ts.some((t) => t[0] === tile[0] && t[1] === tile[1]))
  return own ? own[0] : info.tileNames ? info.name.split(' / ')[0] : info.name
}

/** What's on a tile; a hidden item, or a house that can burn, counts on every tile of its area. */
export function objectsAt(map: ChapterMap, tile: Tile): MapObject[] {
  return map.objects.filter((o) =>
    o.type === 'hidden' || o.type === 'fire'
      ? tile[0] >= o.area[0] && tile[0] <= o.area[2] && tile[1] >= o.area[1] && tile[1] <= o.area[3]
      : sameTile(o.tile, tile),
  )
}

const STAT_LABEL: Record<StatKey, string> = { str: 'Str', mag: 'Mag', skl: 'Skl', spd: 'Spd', lck: 'Lck', def: 'Def', res: 'Res' }

export function describePotEffect(effect: PotEffect): string {
  switch (effect.type) {
    case 'heal':
      return `Heals ${effect.percent}% of max HP`
    case 'damage':
      return `Deals ${effect.percent}% of max HP as damage`
    case 'silence':
      return 'Silence for one turn (no staves or tomes)'
    case 'freeze':
      return 'Freeze for one turn (can\'t move)'
    case 'hex':
      return 'Hex: halves HP until the chapter ends'
    case 'stats': {
      const parts = Object.entries(effect.changes).map(([k, v]) => `${v > 0 ? '+' : ''}${v} ${STAT_LABEL[k as StatKey]}`)
      const kind = effect.kind === 'tonic' ? ' (tonic)' : effect.kind === 'status' ? ' (status)' : ''
      return parts.join(', ') + kind
    }
  }
}

/** A chapter note about who turns up later ("Greil isn't on the map at the start: arrives with Group 1"; Genealogy of the Holy
 * War's "Azelle and Lex join your army: turn 2", "Arvis appears on the map", and talks with someone who appears later; Anankos's
 * summons, and the groups the Heirs of Fate finale brings once his claws fall; Awakening's Endgame sigils' foes; Shadow Dragon's map
 * changes that wait on someone who comes later). */
const ARRIVAL_NOTE = /(?:is|are)n't on the map at the start|arrives with Group|joins? your army:|appears on the map|keeps summoning|arrive on the next|foes come on/

/**
 * The map as it stands when the chapter starts, for the spoiler block: no reinforcement groups, no joiners, and no
 * note about either, the unconfirmed ones included. Who is placed on the map, the forced deployments and the objects stay.
 */
export function atStart(map: ChapterMap): ChapterMap {
  // A unit's or an object's own note loses the sentences that give an arrival away (Genealogy of the Holy War's "Turns hostile when
  // Group 1 arrives.", "Visited by Laylea (once Laylea appears on the map)").
  const told = (note: string | undefined) => {
    if (!note) return note
    const kept = note.split(/(?<=\.)\s+/).filter((x) => !ARRIVAL_NOTE.test(x) && !/\bGroups? \d/.test(x))
    return kept.length ? kept.join(' ') : undefined
  }
  // Foes hidden under the snow (Revelation 10) aren't seen at the start either.
  const units = map.units.some((u) => u.buried) ? map.units.filter((u) => !u.buried) : map.units
  const trimmed = units.map((u) => (u.note && told(u.note) !== u.note ? { ...u, note: told(u.note) } : u))
  const objects = map.objects.map((o) => ('note' in o && o.note && told(o.note) !== o.note ? { ...o, note: told(o.note) } : o))
  return {
    ...map,
    units: trimmed.every((u, i) => u === units[i]) ? units : trimmed,
    objects: objects.every((o, i) => o === map.objects[i]) ? map.objects : (objects as ChapterMap['objects']),
    // Where the groups aren't arrivals (Echoes: a dungeon's formations and fixed encounters, a cemetery's layouts), they're how
    // the battle starts, so they stay.
    reinforcements: map.groupsNote ? map.reinforcements : undefined,
    joiners: undefined,
    notes: map.notes.filter((n) => !ARRIVAL_NOTE.test(n)),
    unconfirmed: map.unconfirmed?.filter((n) => !ARRIVAL_NOTE.test(n)),
  }
}

/**
 * What your army sees on a map fogged at the start: every tile within its sight (`vision`, Thracia's `blackFog`) of the tiles it
 * starts on, the lord's and the fixed ones too, counted in steps as the game fills its visibility map (Thracia's `$80:E626`). Null
 * where the fog isn't there at the start (it comes on a later turn) or no sight is known.
 */
export function startingSight(map: ChapterMap): Set<string> | null {
  const vision = map.vision ?? map.blackFog
  if (!map.fog || vision === undefined) return null
  const seeds = [...map.starts, ...(map.corrinStart ? [map.corrinStart] : []), ...(map.forced ?? []).flatMap((f) => (f.tile ? [f.tile] : []))]
  return new Set(seeds.flatMap((t) => tilesInRadius(map, t, vision).map(tileKey)))
}

/**
 * A map fogged at the start shows its ground, but a foe only where your army sees it (the user's call, spoiler block or not): within
 * its starting sight, or in what the lit torches light (`light`). Allies stay. `seen` is what the army sees. Under the spoiler
 * block (`black`) Thracia 776 draws what your units can't see black, the ground too (`blackFog`): `unseen` is every tile out of
 * sight, and what stands there is left off as well.
 */
export function inTheFog(map: ChapterMap, light: Set<string> = new Set(), black = false): { units: MapUnit[]; seen?: Set<string>; unseen?: Set<string> } {
  const sight = startingSight(map)
  if (!sight) return { units: map.units }
  const seen = new Set([...sight, ...light])
  let unseen: Set<string> | undefined
  if (black && map.blackFog !== undefined) {
    unseen = new Set()
    for (let x = 1; x <= map.width; x++) for (let y = 1; y <= map.height; y++) if (!seen.has(tileKey([x, y]))) unseen.add(tileKey([x, y]))
  }
  const units = map.units.filter((u) => (u.type === 'ally' && !unseen?.has(tileKey(u.tile))) || seen.has(tileKey(u.tile)))
  return { units, seen, unseen }
}

/** One state of a map its script changes on set turns (The Sacred Stones' Phantom Ship): the turn, its words ("Turn 2, your
 * phase"), and the changes made then. */
export interface MapStep {
  turn: number
  label: string
  ids: string[]
}

/** A map's states through its turns' changes, in turn order; the map at the start comes before them. */
export function mapSteps(map: ChapterMap): MapStep[] {
  const timed = map.changes.filter((c) => c.turn !== undefined)
  const turns = [...new Set(timed.map((c) => c.turn!))].sort((a, b) => a - b)
  return turns.map((turn) => {
    const at = timed.filter((c) => c.turn === turn)
    return { turn, label: at[0].effect.split(':')[0], ids: at.map((c) => c.id) }
  })
}

/** The first turn an arrival's words name ("Turn 5, your phase", "Every turn from 4 to 6", "Turn 3 (Hard: turn 2)"); 1 for
 * "Every turn"; undefined for an arrival set off another way (an area, a talk). */
export function arrivalTurn(when: string | undefined): number | undefined {
  if (!when) return undefined
  const n = /\bturns?(?: from)? (\d+)/i.exec(when)
  if (n) return Number(n[1])
  return /^every turn\b/i.test(when) ? 1 : undefined
}

/**
 * The tiles of the closed rooms no one can see into (`ws`: under a roof until a door into it opens), as the game draws them: what
 * stands in one, or lies in it, isn't shown until it opens. A room holding one of your starting tiles is open to you.
 */
export function closedRooms(map: ChapterMap): Set<string> {
  const closed = new Set<string>()
  const rows = map.grid.map(rowCodes)
  const isRoom = ([x, y]: Tile) => x >= 1 && y >= 1 && x <= map.width && y <= map.height && rows[map.height - y][x - 1] === 'ws'
  for (let y = 1; y <= map.height; y++) for (let x = 1; x <= map.width; x++) if (isRoom([x, y])) closed.add(tileKey([x, y]))
  if (closed.size === 0) return closed
  const ours = [...map.starts, ...(map.corrinStart ? [map.corrinStart] : []), ...(map.forced ?? []).flatMap((f) => (f.tile ? [f.tile] : []))]
  for (const start of ours.filter((t) => closed.has(tileKey(t)))) {
    const todo: Tile[] = [start]
    closed.delete(tileKey(start))
    while (todo.length) {
      const [x, y] = todo.pop()!
      for (const t of [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]] as Tile[]) {
        if (closed.has(tileKey(t))) {
          closed.delete(tileKey(t))
          todo.push(t)
        }
      }
    }
  }
  return closed
}

/** The tiles with something to visit: a village, a house with an event, a shop. */
export function visitable(map: ChapterMap): Set<string> {
  return new Set(map.objects.filter((o) => o.type === 'village' || o.type === 'shop').map((o) => tileKey(o.tile)))
}

/** A house with nothing to visit (the GBA games' house tiles, stood in for Avo 10): drawn as the village's scenery, so what can be
 * visited stands out (the user's call). */
export const sceneryHouse = (code: TerrainCode, key: string, visits: Set<string>) => code === 'ot' && !visits.has(key)

/** A village's visit tile in front of a building drawn whole in a town (a house's, a church's or a camp's front above it, the
 * Tellius games'): drawn as its door mat, not a little house before the house, and the house's door over it (the user's call). */
export const doorMat = (map: ChapterMap, [x, y]: Tile) =>
  y < map.height &&
  /^[rkp][a-i]$/.test(terrainAt(map, [x, y + 1])) &&
  (terrainAt(map, [x, y]) === 'oc' || map.objects.some((o) => o.type === 'village' && sameTile(o.tile, [x, y])))

/** Digging a tile of a dig change (Revelation 10's snow) clears it and the four beside it, where the change covers them. */
export function digAt(change: MapChange, [x, y]: Tile): string[] {
  const covered = new Set((change.patch ?? []).map((p) => tileKey(p.tile)))
  return ([[x, y], [x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]] as Tile[]).map(tileKey).filter((k) => covered.has(k))
}
