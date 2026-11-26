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

/** The water codes: drawn with ripples, and what a bridge's rails stand over (with a wall's drop). */
export const WATER_CODES = new Set<TerrainCode>(['we', 'wk', 'tg', 'wm', 'tf', 'tj', 'to', 'wl'])

/** A bridge of two tiles or more that is one solid rectangle, by tile: the way it spans its water, read off the whole bridge (its tiles
 * of one code joined side by side): water beyond its top and bottom rows, it runs east to west; beyond its ends, north to south; else
 * the longer way. Bridges joined in an L or a T (a road of bridges) go tile by tile. Only on a map that draws its bridges so
 * (`wideBridges`: Shadow Dragon and the Blade of Light's Chapter 13, the user's rails; Mystery of the Emblem's, whose short bridges two
 * tiles wide had their rails on the dry sides). */
const WIDE_BRIDGES = new WeakMap<ChapterMap, Map<string, 'ew' | 'ns'>>()
export function wideBridgeSpans(map: ChapterMap): Map<string, 'ew' | 'ns'> {
  const cached = WIDE_BRIDGES.get(map)
  if (cached) return cached
  const out = new Map<string, 'ew' | 'ns'>()
  WIDE_BRIDGES.set(map, out)
  if (!map.wideBridges) return out
  const at = (x: number, y: number) => (x >= 1 && y >= 1 && x <= map.width && y <= map.height ? terrainAt(map, [x, y]) : undefined)
  const water = (x: number, y: number) => {
    const c = at(x, y)
    return !!c && (WATER_CODES.has(c) || c[0] === 'w')
  }
  const seen = new Set<string>()
  for (let y = 1; y <= map.height; y++)
    for (let x = 1; x <= map.width; x++) {
      const code = at(x, y)
      if (!code || !['tb', 'ts', 'wo'].includes(code) || seen.has(tileKey([x, y]))) continue
      const part: Tile[] = []
      const todo: Tile[] = [[x, y]]
      while (todo.length) {
        const t = todo.pop()!
        if (seen.has(tileKey(t)) || at(t[0], t[1]) !== code) continue
        seen.add(tileKey(t))
        part.push(t)
        todo.push([t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1])
      }
      // A lone tile goes by the water round it, as every map's.
      if (part.length === 1) continue
      const xs = part.map((t) => t[0]), ys = part.map((t) => t[1])
      const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
      if (part.length !== (x1 - x0 + 1) * (y1 - y0 + 1)) continue
      let sides = 0, ends = 0
      for (const [px, py] of part) {
        if (py === y1 && water(px, py + 1)) sides++
        if (py === y0 && water(px, py - 1)) sides++
        if (px === x0 && water(px - 1, py)) ends++
        if (px === x1 && water(px + 1, py)) ends++
      }
      const span = sides > ends ? 'ew' : ends > sides ? 'ns' : x1 - x0 >= y1 - y0 ? 'ew' : 'ns'
      for (const t of part) out.set(tileKey(t), span)
    }
  return out
}

/** On a map whose bridges are read whole (`wholeBridges`), each bridge tile's bridge: the box round its bridge (x0, x1, y0, y1), or the
 * box the map gives it, and its span, by the water (or lava) along the box's sides against its ends, the longer way on a tie. */
const WHOLE_BRIDGES = new WeakMap<ChapterMap, Map<string, { span: 'ew' | 'ns'; box: [number, number, number, number] }>>()
export function wholeBridgeBoxes(map: ChapterMap): Map<string, { span: 'ew' | 'ns'; box: [number, number, number, number] }> {
  const cached = WHOLE_BRIDGES.get(map)
  if (cached) return cached
  const out = new Map<string, { span: 'ew' | 'ns'; box: [number, number, number, number] }>()
  WHOLE_BRIDGES.set(map, out)
  if (!map.wholeBridges) return out
  const at = (x: number, y: number) => (x >= 1 && y >= 1 && x <= map.width && y <= map.height ? terrainAt(map, [x, y]) : undefined)
  const water = (x: number, y: number) => {
    const c = at(x, y)
    return !!c && (WATER_CODES.has(c) || c[0] === 'w')
  }
  const spanOf = ([x0, x1, y0, y1]: [number, number, number, number]): 'ew' | 'ns' => {
    let sides = 0, ends = 0
    for (let px = x0; px <= x1; px++) sides += +water(px, y1 + 1) + +water(px, y0 - 1)
    for (let py = y0; py <= y1; py++) ends += +water(x0 - 1, py) + +water(x1 + 1, py)
    return sides > ends ? 'ew' : ends > sides ? 'ns' : x1 - x0 >= y1 - y0 ? 'ew' : 'ns'
  }
  if (Array.isArray(map.wholeBridges)) {
    // The boxes given: each bridge tile in one, a floor drawn as a bridge too (`bridgeFloors`).
    for (const box of map.wholeBridges) {
      const span = spanOf(box)
      for (let y = box[2]; y <= box[3]; y++)
        for (let x = box[0]; x <= box[1]; x++)
          if (['tb', 'ts', 'wo'].includes(at(x, y) ?? '') || map.bridgeFloors?.includes(tileKey([x, y]))) out.set(tileKey([x, y]), { span, box })
    }
    return out
  }
  const seen = new Set<string>()
  for (let y = 1; y <= map.height; y++)
    for (let x = 1; x <= map.width; x++) {
      const code = at(x, y)
      if (!code || !['tb', 'ts', 'wo'].includes(code) || seen.has(tileKey([x, y]))) continue
      const part: Tile[] = []
      const todo: Tile[] = [[x, y]]
      while (todo.length) {
        const t = todo.pop()!
        if (seen.has(tileKey(t)) || at(t[0], t[1]) !== code) continue
        seen.add(tileKey(t))
        part.push(t)
        todo.push([t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1])
      }
      if (part.length === 1) continue
      const xs = part.map((t) => t[0]), ys = part.map((t) => t[1])
      const box: [number, number, number, number] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
      const span = spanOf(box)
      for (const t of part) out.set(tileKey(t), { span, box })
    }
  return out
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
    forced: map.forced?.map((f) => (f.standIn ? { name: f.standIn.name, tile: f.tile, ...(f.difficulties ? { difficulties: f.difficulties } : {}) } : f)),
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
const ARRIVAL_NOTE = /(?:is|are)n't on the map at the start|arrives with Group|joins? your army:|appears on the map|keeps summoning|arrive on the next|foes come on|\bjoins? on turn\b|^Reinforcements\b|only the one you pick comes|brings enemy reinforcements/

/** A chapter note on what winning, a chapter's end or a boss's fall gives, and on what condition (Shadow Dragon and the Blade of
 * Light's seized castles, Awakening's "Clearing it adds Roy to your army", Three Houses' battalions, the GBA games' and Thracia's end
 * gifts, Fates' joins at a chapter's end and its Yato's forms). */
const REWARD_NOTE = /^(?:Seizing the (?:castle|throne) gives|Clearing it (?:gives|adds)|Routing two groups of Risen gets a reward|Winning it recruits|Battalions? given when the battle is won|When the battle is won:|Corrin's Yato becomes|Once [^,]+ is defeated, if your army holds)|: given to .+ at the end of the chapter|\bjoins? at the end of the chapter/

/** What a foe (or a green unit) will do: who it goes for, where it heads, what it waits for, what it loots and where it leaves. */
const BEHAVIOR = /\b(?:goes for|heads for|holds its ground|moves with|leaves the map|makes for|takes the Crest|never moves|never attacks|never attacking|advances on|waits until|targets the|raises the alarm|doesn't move|razing what)\b/i

/**
 * The map as it stands when the chapter starts, for the spoiler block: no reinforcement groups, no joiners, and no
 * note about either, the unconfirmed ones included. Who is placed on the map, the forced deployments and the objects stay.
 * Beyond that it's the map and nothing the game doesn't show at the start (the user's calls, 2026-11-26): no reward a chapter's end
 * or a boss's fall gives, no foe's behavior (who it goes for, where it heads, a looter's badge and targets), no loss condition naming
 * someone who comes later, no map change an arrival makes, no pot's effect and no boulder's path. Taps still preview a door, a vein
 * or a wall, and chests', villages' and talks' notes stay.
 */
export function atStart(map: ChapterMap): ChapterMap {
  // A unit's note keeps who it is and what it holds, losing the sentences, and the clauses after a semicolon, that give an arrival or
  // its behavior away (Genealogy of the Holy War's "Turns hostile when Group 1 arrives."; "Lv 2 Brigand; goes for the villages").
  const told = (note: string | undefined, behavior = false) => {
    if (!note) return note
    // Clause by clause, so a talk riding on an arrival's sentence stays ("Turns hostile when Group 1 arrives; turns friendly when
    // Creidne talks to Iucharba.").
    const kept = note
      .split(/(?<=\.)\s+/)
      .map((x) => {
        const clauses = x
          .split('; ')
          .filter((c) => !ARRIVAL_NOTE.test(c) && !/\bGroups? \d/.test(c) && !(behavior && BEHAVIOR.test(c)))
        const out = clauses.join('; ')
        // A sentence keeps its full stop, and a clause left first its capital.
        const whole = out && /\.$/.test(x) && !/[.!?)]$/.test(out) ? `${out}.` : out
        return whole && whole !== x ? whole[0].toUpperCase() + whole.slice(1) : whole
      })
      .filter(Boolean)
    return kept.length ? kept.join(' ') : undefined
  }
  // A village's note loses who can raze it (a looter's target); Thracia's rule that any foe standing on it can stays.
  const village = (note: string | undefined) => {
    const t = told(note)
    if (!t) return t
    const kept = t.split(/(?<=\.)\s+/).filter((x) => !/\bcan (?:raze|destroy) it\b/.test(x) || /\bA foe standing\b/.test(x))
    return kept.length ? kept.join(' ') : undefined
  }
  // Foes hidden under the snow (Revelation 10) aren't seen at the start either.
  const units = map.units.some((u) => u.buried) ? map.units.filter((u) => !u.buried) : map.units
  const trimmed = units.map((u) => {
    // One the game shows by another name until a talk (Mystery of the Emblem's Samuel as Navarre) goes by that name, and its note
    // loses the sentence that gives him away.
    const told2 = told(u.note, true)
    const note = u.shownAs && told2 ? told2.split(/(?<=\.)\s+/).filter((x) => !/^Shown as /.test(x)).join(' ') || undefined : told2
    if (note === u.note && !u.goesTo && !u.looter && !u.shownAs) return u
    return { ...u, name: u.shownAs ?? u.name, shownAs: undefined, note, goesTo: undefined, looter: undefined }
  })
  const objects = map.objects.map((o) => {
    if (!('note' in o) || !o.note) return o
    const note = o.type === 'village' ? village(o.note) : told(o.note)
    return note === o.note ? o : { ...o, note }
  })
  // Who's on the map at the start: a loss condition or an escape naming anyone else waits for them.
  const here = new Set([...units.map((u) => u.name), ...(map.forced ?? []).map((f) => f.name)])
  const heard = (n: string) => !ARRIVAL_NOTE.test(n) && !REWARD_NOTE.test(n)
  const said = (n: string) => n.replace(/: winning it gives [^.]+\./, '.')
  return {
    ...map,
    units: trimmed.every((u, i) => u === units[i]) ? units : trimmed,
    objects: objects.every((o, i) => o === map.objects[i]) ? map.objects : (objects as ChapterMap['objects']),
    // Where the groups aren't arrivals (Echoes: a dungeon's formations and fixed encounters, a cemetery's layouts), they're how
    // the battle starts, so they stay.
    reinforcements: map.groupsNote ? map.reinforcements : undefined,
    joiners: undefined,
    notes: map.notes.filter(heard).map(said),
    notesOn: map.notesOn?.filter((n) => heard(n.note)),
    unconfirmed: map.unconfirmed?.filter((n) => !ARRIVAL_NOTE.test(n)),
    // Radiant Dawn's "or Fiona dies (after arriving)".
    defeat: map.defeat && map.defeat.split(', or ').filter((p) => !/\(after arriving\)/.test(p)).join(', or '),
    // Radiant Dawn's "Where Heather escapes", while Heather has yet to come.
    objectives: map.objectives.filter((o) => {
      const who = o.label?.match(/^Where (.+?) escapes$/)?.[1]
      return !who || here.has(who)
    }),
    // A map change an arrival makes (Genealogy's "When Group 3 arrives: thicket becomes forest") waits for it; a boulder keeps its
    // path to itself.
    changes: map.changes
      .filter((c) => !/\bGroups? \d+ arrives?\b/.test(c.effect ?? ''))
      .map((c) => (c.trigger === 'boulder' && !c.noPreview ? { ...c, noPreview: true as const } : c)),
  }
}

/**
 * What your army sees on a map fogged at the start: every tile within its sight (`vision`, Thracia's `blackFog`) of the tiles it
 * starts on, the lord's and the fixed ones too, and of its allies' (green and yellow units share their sight: the user's call;
 * Thracia's black fog is filled from your army's alone, `$80:E626`), counted in steps as the game fills its visibility map. Null
 * where the fog isn't there at the start (it comes on a later turn) or no sight is known.
 */
export function startingSight(map: ChapterMap): Set<string> | null {
  const vision = map.vision ?? map.blackFog
  if (!map.fog || vision === undefined) return null
  const allies = map.blackFog === undefined ? map.units.filter((u) => u.type === 'ally').map((u) => u.tile) : []
  const seeds = [
    ...map.starts,
    ...(map.corrinStart ? [map.corrinStart] : []),
    ...(map.forced ?? []).flatMap((f) => (f.tile ? [f.tile] : [])),
    ...allies,
  ]
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
 * Tellius games'): drawn as its door mat, not a little house before the house, and the house's door over it (the user's call). An
 * army's tent (Radiant Dawn's camps) has its mat before it or at its side, where the game puts its visit. */
export const beforeBuilding = (map: ChapterMap, [x, y]: Tile) => {
  const at = (t: Tile) => t[0] >= 1 && t[1] >= 1 && t[0] <= map.width && t[1] <= map.height ? terrainAt(map, t) : ''
  return /^[rkp][a-i]$/.test(at([x, y + 1])) || [at([x, y + 1]), at([x - 1, y]), at([x + 1, y])].some((c) => /^u[a-i]$/.test(c))
}
/** Only where there's something to visit: a village tile before a house with nothing to visit there is no mat (Fates' Birthright 13:
 * the user, no door mat for the decorative ones), drawn as the ground before a house whose door is shut. */
export const doorMat = (map: ChapterMap, [x, y]: Tile) =>
  beforeBuilding(map, [x, y]) && map.objects.some((o) => (o.type === 'village' || o.type === 'shop') && sameTile(o.tile, [x, y]))

/** Digging a tile of a dig change (Revelation 10's snow) clears it and the four beside it, where the change covers them. */
export function digAt(change: MapChange, [x, y]: Tile): string[] {
  const covered = new Set((change.patch ?? []).map((p) => tileKey(p.tile)))
  return ([[x, y], [x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]] as Tile[]).map(tileKey).filter((k) => covered.has(k))
}
