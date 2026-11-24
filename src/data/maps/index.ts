import type { ChapterMap } from './types'
import { SHARED_MAPS } from './shared'
import { CONQUEST_12 } from './conquest12'
import { CONQUEST_6_TO_11 } from './conquest'
import { CONQUEST_13_TO_ENDGAME } from './conquestLate'
import { BIRTHRIGHT_MAPS } from './birthright'
import { REVELATION_MAPS } from './revelation'
import { PARALOGUE_MAPS } from './paralogues'
import { DLC_MAPS } from './dlc'
import { GAME_TERRAIN } from './gameTerrain'
import { GAME_UNITS } from './gameUnits'
import { GAME_CHAPTERS } from './gameChapters'
import { FATES_CHALLENGES } from './fatesChallenges'
import type { ChallengeGroup } from './fatesChallenges'
import type { GameUnit } from './gameUnits'
import type { MapUnit, Tile } from './types'
import { rowCodes, terrainName, tileKey } from '../../logic/maps'
import { DIFFICULTIES } from './types'
import type { MapSet } from './mapSet'
import { MOVE_CLASSES, MOVE_CLASS_EXAMPLES } from './fatesTerrain'

/** Veins whose effect isn't a terrain change of their own (they undo or reverse the others). */
const OWN_EFFECT = new Set(['vein-sakura', 'vein-hinoka'])

/** Each Dragon Vein takes the tiles it reshapes from the game's own data, where the game has them. */
function withGameVeins(map: ChapterMap): ChapterMap {
  const game = GAME_TERRAIN[map.id]
  if (!game) return map
  const changes = map.changes.map((c) => {
    if (OWN_EFFECT.has(c.id) || c.trigger !== 'dragonVein' || c.noPreview || c.flips !== undefined) return c
    const tiles = [c.tile.default, c.tile.Normal, c.tile.Hard, c.tile.Lunatic].filter((t) => t !== undefined)
    const vein = game.veins.find((v) => tiles.some((t) => t[0] === v.tile[0] && t[1] === v.tile[1]))
    return vein && vein.patch.length ? { ...c, patch: vein.patch } : c
  })
  return { ...map, changes }
}

const same = (a: readonly number[], b: readonly number[]) => a[0] === b[0] && a[1] === b[1]

/**
 * Every chest and village from the game's terrain scripts. A hand-written one on the same tile wins,
 * since those add detail the files don't spell out (Conquest 8's event villages, Conquest 26's
 * Kaze-dependent chest).
 */
/** Each breakable wall or partition is a change of its own, previewed like a Dragon Vein. */
function withGameBreakables(map: ChapterMap): ChapterMap {
  const breakables = GAME_TERRAIN[map.id]?.breakables
  if (!breakables) return map
  const changes = breakables.map((b) => ({
    id: `break-${b.tile[0]}-${b.tile[1]}`,
    trigger: 'breakable' as const,
    tile: { default: b.tile },
    usableBy: 'Any unit that can attack it',
    effect: `${b.hp ? `${b.hp} HP. ` : ''}Attack it down and it becomes open ground${b.also?.some((a) => a.becomes === 'tb') ? ', falling across as a bridge' : ''}.`,
    patch: [{ tile: b.tile, becomes: b.becomes }, ...(b.also ?? [])],
    // A dead tree, drawn as a log as the GBA games' snags are (Conquest 19's: the user).
    ...(/dead tree/i.test(terrainName(map, b.tile)) ? { snag: true as const } : {}),
  }))
  return { ...map, changes: [...map.changes, ...changes] }
}

function withGameObjects(map: ChapterMap): ChapterMap {
  const game = GAME_CHAPTERS[map.id]
  if (!game) return map
  const extra = game.objects.filter((g) => !map.objects.some((o) => same(o.tile, g.tile)))
  return extra.length ? { ...map, objects: [...map.objects, ...extra] } : map
}

/**
 * Units, starting tiles and Corrin's tile come from the game's own placement files where we have them.
 * What the map file adds by hand (notes, a pair-up the game makes by script) carries over from the hand-written unit on the
 * same tile.
 */
function withGameUnits(map: ChapterMap): ChapterMap {
  const game = GAME_UNITS[map.id]
  if (!game) return map
  const toUnit = (g: GameUnit): MapUnit & { from?: Tile } => ({
    type: g.type,
    name: g.name,
    tile: g.tile,
    ...(g.paired ? { paired: true } : {}),
    ...(g.partner && g.partner !== g.name ? { partner: g.partner } : {}),
    ...(g.drops ? { drops: g.drops } : {}),
    ...(g.carries ? { carries: g.carries } : {}),
    ...(g.difficulties && g.difficulties.length < 3 ? { difficulties: g.difficulties } : {}),
    ...(g.talk ? { talk: g.talk } : {}),
    ...(g.capturable ? { capturable: true as const } : {}),
    ...(g.goesTo ? { goesTo: g.goesTo } : {}),
    ...(g.note ? { note: g.note } : {}),
    ...(g.from ? { from: g.from } : {}),
  })
  const reinforcements = game.waves.map((w) => ({
    id: w.group,
    label: w.label,
    units: w.units.map(toUnit),
    ...(w.when ? { when: w.when } : {}),
    ...(w.areas ? { areas: w.areas } : {}),
  }))
  const units = game.units.map((g): MapUnit => {
    const old = map.units.find((o) => same(o.tile, g.tile) && o.type !== 'enemy') ?? map.units.find((o) => same(o.tile, g.tile))
    const keepOld = old && old.type === g.type
    return {
      type: g.type,
      // The game's name: a generic unit's is its class, as the game shows it.
      name: g.name,
      tile: g.tile,
      ...(g.paired || (keepOld && old.paired && g.type === 'boss') ? { paired: true } : {}),
      ...(g.partner && g.partner !== g.name ? { partner: g.partner } : {}),
      ...(g.drops ? { drops: g.drops } : {}),
      ...(g.carries ? { carries: g.carries } : {}),
      ...(g.capturable ? { capturable: true as const } : {}),
      ...(g.goesTo ? { goesTo: g.goesTo } : {}),
      ...(g.type === 'ally' && g.generic ? { generic: true as const } : {}),
      ...(keepOld && old.note ? { note: old.note } : g.note ? { note: g.note } : {}),
      ...(g.talk ? { talk: g.talk } : {}),
      ...(g.difficulties && g.difficulties.length < 3 ? { difficulties: g.difficulties } : {}),
    }
  })
  return {
    ...map,
    units,
    starts: game.starts,
    ...(game.corrin ? { corrinStart: game.corrin } : {}),
    ...(game.forced?.length ? { forced: game.forced } : {}),
    ...(reinforcements.length ? { reinforcements } : {}),
    ...(game.joins.length ? { joiners: game.joins } : {}),
    ...(game.kit?.length ? { kit: game.kit } : {}),
    ...(game.grind ? { randomSpawns: true as const } : {}),
  }
}

/**
 * Foes under terrain a change clears a tile at a time (Revelation 10's snow) come in the game as groups the terrain's own event
 * brings out as it's dug: they're on the map from the start, hidden until their tile is cleared.
 */
function withBuried(map: ChapterMap): ChapterMap {
  const dug = new Set(map.changes.filter((c) => c.dig).flatMap((c) => (c.patch ?? []).map((p) => `${p.tile[0]},${p.tile[1]}`)))
  if (!dug.size) return map
  const under = (map.reinforcements ?? []).filter((g) => g.units.every((u) => dug.has(`${u.tile[0]},${u.tile[1]}`)))
  return {
    ...map,
    units: [...map.units, ...under.flatMap((g) => g.units.map(({ from: _from, ...u }) => ({ ...u, buried: true as const })))],
    reinforcements: (map.reinforcements ?? []).filter((g) => !under.includes(g)),
  }
}

/**
 * What the builder draws over the game's terrain reaches every map, the chapters written by hand too: its decor (the stairs its field
 * builds), its walls' looks, its ruins, its bridges' spans and its boats' ends. Every Fates bridge is read off the whole bridge
 * (`wideBridges`: the user's bridge notes, 2026-11-24: a bridge two tiles wide one bridge, its planks across its water).
 */
function withGameLooks(map: ChapterMap): ChapterMap {
  const game = GAME_TERRAIN[map.id]
  if (!game) return map
  return {
    ...map,
    wideBridges: true,
    ...(game.decor && !map.decor ? { decor: game.decor } : {}),
    ...(game.wallLooks && !map.wallLooks ? { wallLooks: game.wallLooks } : {}),
    ...(game.ruins && !map.ruins ? { ruins: game.ruins } : {}),
    ...(game.bridgeSpans ? { bridgeSpans: game.bridgeSpans } : {}),
    ...(game.boatEnds ? { boatEnds: game.boatEnds } : {}),
    ...(game.greyRoofs ? { greyRoofs: true as const } : {}),
    ...(game.muckAsBog ? { muckAsBog: true as const } : {}),
    ...(game.warps ? { warps: game.warps } : {}),
    ...(game.links && !map.links ? { links: game.links } : {}),
    ...(game.flameWalls ? { flameWalls: game.flameWalls } : {}),
  }
}

/** The chapters, paralogues and DLC maps: the shared chapters first, then each route in chapter order. */
const BASE_MAPS: ChapterMap[] = [
  ...SHARED_MAPS,
  ...BIRTHRIGHT_MAPS,
  ...CONQUEST_6_TO_11,
  CONQUEST_12,
  ...CONQUEST_13_TO_ENDGAME,
  ...REVELATION_MAPS,
  ...PARALOGUE_MAPS,
  ...DLC_MAPS,
].map(withGameVeins).map(withGameUnits).map(withGameObjects).map(withGameBreakables).map(withBuried).map(withGameLooks)

/**
 * How many foes a challenge group fields, its boss included (0x417b98): a tile each on Lunatic, two fewer on Normal and Hard
 * (three from 16 tiles), then up to a third of that fewer at random.
 */
function groupSize(tiles: number, lunatic: boolean): [number, number] {
  const most = Math.max(lunatic ? tiles : tiles - (tiles >= 16 ? 3 : 2), 1)
  return [Math.max(most - Math.floor(most / 3), 1), most]
}

/** A group's tiles, each once: the boss's first. */
const groupTiles = (g: ChallengeGroup): Tile[] => [g.boss, ...g.foes].filter((t, i, all) => all.findIndex((u) => same(u, t)) === i)

/**
 * A challenge group's units: its boss's tile, and the tiles its other foes can stand on. Two of a group's slots can share a
 * tile (Revelation 22's); a foe whose tile is taken stands on the nearest open one (0x39e8f4).
 */
function challengeUnits(g: ChallengeGroup, label: string): MapUnit[] {
  const twice = (t: Tile) => g.foes.filter((u) => same(u, t)).length > 1
  return groupTiles(g).map((tile, i) =>
    i === 0
      ? { type: 'boss', name: 'Boss', tile, generic: true, note: `${label}'s boss stands here, paired half the time.` }
      : {
          type: 'enemy',
          name: 'Random enemy',
          tile,
          note: twice(tile)
            ? `Two of ${label}'s foes can stand here, each paired a quarter of the time: when both come, the second stands on the nearest open tile.`
            : `One of ${label}'s foes can stand here, paired a quarter of the time.`,
        },
  )
}

/** A group's size in words: Normal's (and Hard's), with Lunatic's beside it. */
function sizeText(g: ChallengeGroup, label: string): string {
  const tiles = g.foes.length + 1
  const span = ([lo, hi]: [number, number]) => (lo === hi ? `${lo - 1}` : `${lo - 1} to ${hi - 1}`)
  return `${label}: its boss and ${span(groupSize(tiles, false))} more foes (Lunatic ${span(groupSize(tiles, true))}).`
}

/**
 * A challenge battle on a chapter's or paralogue's map. It has the map with every trick in it spent (read live in Revelation
 * 20's: every bridge down at once, every vein and village used): each tile in its second state (`spent`), so every Dragon
 * Vein's and the chapter's own changes are in place, every wall broken, every door and chest open, Revelation's darkness
 * lifted and Revelation 10's snow gone. The encounter's start tiles, its two foe groups and its shiny spots stand in for
 * the chapter's units.
 */
function challengeMap(base: ChapterMap): ChapterMap | undefined {
  const c = FATES_CHALLENGES[base.id]
  if (!c) return undefined
  const rows = base.grid.map(rowCodes)
  // A village spent (closed) has its house in ruins, and the village before it rubble-strewn (the user's call: a challenge's
  // villages as ruins).
  const at = ([x, y]: Tile) => (x >= 1 && y >= 1 && x <= base.width && y <= base.height ? rows[base.height - y][x - 1] : undefined)
  const ruins = new Set<string>()
  for (const { tile: [x, y], becomes } of GAME_TERRAIN[base.id]?.spent ?? []) {
    if (at([x, y]) === 'oc' && becomes === 'od' && /^r[a-r]$/.test(at([x, y + 1]) ?? '')) {
      ruins.add(tileKey([x, y]))
      const todo: Tile[] = [[x, y + 1]]
      while (todo.length) {
        const t = todo.pop()!
        if (ruins.has(tileKey(t)) || !/^r[a-r]$/.test(at(t) ?? '')) continue
        ruins.add(tileKey(t))
        todo.push([t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1])
      }
    }
  }
  // The buildings its snow buries (Revelation 10's houses: the user, roofs or ruins), uncovered once the snow is gone, stand in
  // ruins as a challenge's spent villages' houses do, with the corners of them the snow left uncovered; its walls in lines one tile
  // wide are a village's low walls (the user: the L-shaped lines).
  const uncovered = new Set<string>()
  for (const { tile: [x, y], becomes } of GAME_TERRAIN[base.id]?.spent ?? [])
    if (at([x, y]) === 'wr' && becomes === 'wa') uncovered.add(tileKey([x, y]))
  for (const { tile: [x, y], becomes } of GAME_TERRAIN[base.id]?.spent ?? []) rows[base.height - y][x - 1] = becomes
  // A ship whose floor is drawn as its deck keeps its deck where the challenge lays plain over the drained sea (Revelation 14's: the
  // user, wood not flagstones), and its sides there (the game's partitions) its ship's wooden walls.
  const deckWalls: Record<string, 'ship'> = {}
  if (base.grid.some((r) => rowCodes(r).includes('t3'))) {
    for (const { tile: [x, y], becomes } of GAME_TERRAIN[base.id]?.spent ?? []) {
      const was = at([x, y])
      const near = ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => at([x + dx, y + dy]) === 't3' || at([x + dx, y + dy]) === 'wg')
      if (becomes === 'ta' && was === 'we' && near) rows[base.height - y][x - 1] = 't3'
    }
    for (let y = 1; y <= base.height; y++)
      for (let x = 1; x <= base.width; x++)
        if (at([x, y]) === 'wg' && ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => at([x + dx, y + dy]) === 't3'))
          deckWalls[tileKey([x, y])] = 'ship'
  }
  const lowWalls: Record<string, 'wall'> = {}
  if (uncovered.size) {
    const key = (t: Tile) => tileKey(t)
    const near = (t: Tile): Tile[] => [[t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1]]
    const all = new Set(uncovered)
    for (const k of uncovered) {
      const [x, y] = k.split(',').map(Number)
      for (const n of near([x, y])) if (at(n) === 'wa') all.add(key(n))
    }
    const seen = new Set<string>()
    for (const start of all) {
      if (seen.has(start)) continue
      const group: Tile[] = []
      const todo: Tile[] = [start.split(',').map(Number) as Tile]
      while (todo.length) {
        const t = todo.pop()!
        if (seen.has(key(t)) || !all.has(key(t))) continue
        seen.add(key(t))
        group.push(t)
        todo.push(...near(t))
      }
      const inGroup = new Set(group.map(key))
      const block = group.some(([x, y]) => [[x + 1, y], [x, y + 1], [x + 1, y + 1]].every((t) => inGroup.has(key(t as Tile))))
      for (const t of group) {
        if (block) ruins.add(key(t))
        else lowWalls[key(t)] = 'wall'
      }
    }
  }
  for (const t of base.ruins ?? []) ruins.add(t)
  const labels = ['Group 1', 'Group 2']
  return {
    ...base,
    id: `${base.id}-challenge`,
    route: 'Challenge',
    availableIn: c.availableIn,
    challengeOf: base.id,
    heading: undefined,
    // A challenge goes by its scout name, the chapter's location ("Cemetery in a Deeprealm"), never the chapter's title.
    title: GAME_CHAPTERS[base.id]?.location ?? base.location ?? base.title,
    location: undefined,
    grid: rows.map((r) => r.join('')),
    ...(ruins.size ? { ruins: [...ruins] } : {}),
    ...(Object.keys(lowWalls).length || Object.keys(deckWalls).length ? { wallLooks: { ...(base.wallLooks ?? {}), ...lowWalls, ...deckWalls } } : {}),
    dark: undefined,
    fog: undefined,
    // The chapter's script doesn't run in a challenge battle (read live: Revelation 20's every trick spent at once), so nothing
    // in it moves the walls or works the rooms.
    switchWalls: undefined,
    rooms: undefined,
    victory: 'Rout the enemy.',
    defeat: 'Corrin dies, or your army is routed.',
    objectives: [],
    units: c.groups.flatMap((g, i) => challengeUnits(g, labels[i])),
    foeGroups: c.groups.map((g, i) => ({ label: labels[i], tiles: groupTiles(g) })),
    starts: c.starts,
    corrinStart: undefined,
    forced: undefined,
    reinforcements: undefined,
    joiners: undefined,
    kit: undefined,
    objects: [
      ...base.objects.filter((o) => o.type !== 'chest' && o.type !== 'village' && o.type !== 'door'),
      ...c.spots.map((tile) => ({ type: 'shiny' as const, tile })),
    ],
    changes: [],
    notes: [
      'A challenge battle: the game picks its foes each time, from two groups (outlined). A battle with one boss has one group, either one; a dual-boss battle has both.',
      "A group's boss always stands on its own tile; its other foes take the group's other tiles in a random order, so any of them can be filled together.",
      ...c.groups.map((g, i) => sizeText(g, labels[i])),
      "The map is the chapter's with everything spent: every Dragon Vein used and every change made at once, every wall broken, every door, chest and village open.",
    ],
    unconfirmed: undefined,
  }
}

/** Every map: the chapters, paralogues and DLC maps, then the challenge battles on them. */
export const ALL_MAPS: ChapterMap[] = [...BASE_MAPS, ...BASE_MAPS.flatMap((m) => challengeMap(m) ?? [])]

export function mapLabel(map: ChapterMap): string {
  if (map.route === 'Challenge') return `Challenge: ${map.title}`
  if (map.route === 'Story') return `${(map.heading ?? '').replace(/^Ch\./, 'Chapter ')}: ${map.title}`
  if (map.route === 'Shared') return `${map.chapter === 0 ? 'Prologue' : `Chapter ${map.chapter}`}: ${map.title}`
  if (map.route === 'Paralogue') return `Paralogue ${map.chapter}: ${map.title}`
  if (map.route === 'DLC') {
    if (map.heading === 'Heirs of Fate') return `Heirs of Fate ${map.title}`
    return map.heading === 'Hero Battle' ? `Hero Battle: ${map.title}` : map.title
  }
  return `${map.route} ${map.id.endsWith('-endgame') ? 'Endgame' : map.chapter}: ${map.title}`
}

/** The route buttons on the map page: the chapters before the split, each route, and the DLC. */
export const MAP_ROUTES = ['Prologue', 'Birthright', 'Conquest', 'Revelation', 'DLC'] as const
export type MapRoute = (typeof MAP_ROUTES)[number]

/** A route's own maps (not its paralogues), in order. */
export function routeMaps(route: MapRoute): ChapterMap[] {
  return ALL_MAPS.filter((m) => m.route === (route === 'Prologue' ? 'Shared' : route))
}

/** The paralogues a route can reach. */
export function routeParalogues(route: MapRoute): ChapterMap[] {
  return ALL_MAPS.filter((m) => m.route === 'Paralogue' && m.availableIn?.some((r) => r === route))
}

/** The challenge battles a route can scout: its chapters' (the shared ones too), then its paralogues'. */
export function routeChallenges(route: MapRoute): ChapterMap[] {
  return ALL_MAPS.filter((m) => m.route === 'Challenge' && m.availableIn?.some((r) => r === route))
}

/** A map's name within its own route's list ('Chapter 7: …' rather than 'Birthright 7: …'). */
export function chapterLabel(map: ChapterMap): string {
  if (map.route === 'Challenge') return map.title
  if (map.route === 'Birthright' || map.route === 'Conquest' || map.route === 'Revelation') {
    return `${map.id.endsWith('-endgame') ? 'Endgame' : `Chapter ${map.chapter}`}: ${map.title}`
  }
  return mapLabel(map)
}

/** The route a map is listed under (a paralogue: the first route that can reach it). */
export function mapRoute(map: ChapterMap): MapRoute {
  if (map.route === 'Shared' || map.route === 'Story' || map.route === 'Trial') return 'Prologue'
  // Fates' own: The Sacred Stones' skirmishes name their routes too, but never come here.
  if (map.route === 'Paralogue' || map.route === 'Challenge') return (map.availableIn?.[0] as MapRoute | undefined) ?? 'Revelation'
  if (map.route === 'Birthright' || map.route === 'Conquest' || map.route === 'Revelation' || map.route === 'DLC') return map.route
  // Another game's routes (The Blazing Blade's stories) aren't Fates' to list.
  return 'Prologue'
}

/** Fates on the map page: its routes, three difficulties and the Fire Emblem Wiki's movement classes. */
export const FATES_MAP_SET: MapSet = {
  maps: ALL_MAPS,
  routes: {
    list: MAP_ROUTES,
    maps: (route) => routeMaps(route as MapRoute),
    side: (route) => (route === 'Prologue' || route === 'DLC' ? [] : routeParalogues(route as MapRoute)),
    of: mapRoute,
    third: { label: 'Challenges', maps: (route) => (route === 'Prologue' || route === 'DLC' ? [] : routeChallenges(route as MapRoute)) },
  },
  difficulties: DIFFICULTIES.map((d) => ({ value: d, label: d })),
  moveClasses: MOVE_CLASSES,
  moveClassExamples: MOVE_CLASS_EXAMPLES,
  lord: 'Corrin',
  terrainNote: 'Fliers get no Def/Avo from terrain.',
  chapterLabel,
  mapLabel,
}
