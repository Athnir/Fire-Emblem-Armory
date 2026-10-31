import { ALL_MAPS, mapLabel } from '../data/maps'
import type { ChapterMap, MapUnit } from '../data/maps/types'

export type StoryRoute = 'Birthright' | 'Conquest' | 'Revelation'
const STORY_ROUTES: StoryRoute[] = ['Birthright', 'Conquest', 'Revelation']

/** One place on the maps an item comes from. */
export interface ItemSource {
  mapId: string
  /** The map's name as the map page lists it ('Conquest 10: Unhappy Reunion'). */
  map: string
  /** The routes that can play this map: chapters 1-5 and the DLC are on all three. */
  routes: StoryRoute[]
  dlc: boolean
  /** 'Chest at (2, 22)', 'Village at (8, 13)', 'Dropped by Haitaka (Hard, Lunatic)'. */
  how: string
  /** Dropped by a foe who only arrives mid-chapter: not on the map at the start. */
  arrives?: true
}

function mapRoutes(map: ChapterMap): StoryRoute[] {
  // Fates maps only ('Story' and 'Trial' are another game's chapters and side maps).
  if (map.route === 'Shared' || map.route === 'DLC' || map.route === 'Story' || map.route === 'Trial') return STORY_ROUTES
  if (map.route === 'Paralogue') return map.availableIn ?? STORY_ROUTES
  if (map.route === 'Birthright' || map.route === 'Conquest' || map.route === 'Revelation') return [map.route]
  return STORY_ROUTES
}

/** The generators' suffixes for items the game gives one name ('Ganglari (reward)', 'Dragon Breath (1-3)'): part of the name. */
const NAME_SUFFIXES = ['(reward)', '(Bronze form)', '(1-3)', '(Heirs of Fate)']

/** 'Spy's Shuriken or Spy's Yumi' -> both names; a hand note in brackets is dropped. */
function itemNames(text: string): string[] {
  return text
    .split(/ or /)
    .map((t) => (NAME_SUFFIXES.some((x) => t.trim().endsWith(x)) ? t.trim() : t.replace(/\s*\(.*\)\s*/, '').trim()))
    .filter(Boolean)
}

const ALL_DIFFICULTIES = ['Normal', 'Hard', 'Lunatic']

/** One foe's drop or carried item, before its line is written: the same foe on every difficulty is one line. */
interface FoeItem {
  map: ChapterMap
  verb: 'Dropped by' | 'Carried by'
  who: string
  /** Not on the map at the start: a reinforcement, or a foe hidden until dug out (Revelation 10's snow). */
  later: '' | 'reinforcement' | 'hidden until dug out'
  difficulties: Set<string>
  item: string
}

function foeText(f: FoeItem): string {
  const all = ALL_DIFFICULTIES.every((d) => f.difficulties.has(d))
  const extras = [f.later, all ? '' : ALL_DIFFICULTIES.filter((d) => f.difficulties.has(d)).join(', ')].filter(Boolean)
  return `${f.verb} ${f.who}${extras.length ? ` (${extras.join('; ')})` : ''}`
}

function buildIndex(): { index: Map<string, ItemSource[]>; carriers: Map<string, ItemSource[]>; kits: Map<string, ItemSource[]> } {
  const index = new Map<string, ItemSource[]>()
  const carriers = new Map<string, ItemSource[]>()
  const kits = new Map<string, ItemSource[]>()
  const add = (item: string, map: ChapterMap, how: string, arrives?: true, into = index) => {
    const source: ItemSource = { mapId: map.id, map: mapLabel(map), routes: mapRoutes(map), dlc: map.route === 'DLC', how, ...(arrives && { arrives }) }
    for (const name of itemNames(item)) {
      const list = into.get(name) ?? []
      if (!list.some((s) => s.mapId === source.mapId && s.how === source.how)) list.push(source)
      into.set(name, list)
    }
  }
  // A foe's drops and gear, gathered first so that one foe placed per difficulty (Birthright 26's) comes out as one line.
  const foes = new Map<string, FoeItem>()
  const foe = (u: MapUnit, map: ChapterMap, reinforcement: boolean, verb: FoeItem['verb'], item: string) => {
    const who = u.paired && u.partner ? `${u.name} & ${u.partner}` : u.name
    const later: FoeItem['later'] = reinforcement ? 'reinforcement' : u.buried ? 'hidden until dug out' : ''
    const key = [map.id, verb, who, later, item].join('|')
    const f = foes.get(key) ?? { map, verb, who, later, difficulties: new Set<string>(), item }
    for (const d of u.difficulties ?? ALL_DIFFICULTIES) f.difficulties.add(d)
    foes.set(key, f)
  }
  for (const map of ALL_MAPS) {
    for (const o of map.objects) {
      if (o.type === 'chest') add(o.contents, map, `Chest at (${o.tile[0]}, ${o.tile[1]})`)
      if (o.type === 'village' && o.reward) add(o.reward, map, `Village at (${o.tile[0]}, ${o.tile[1]})`)
    }
    for (const u of map.units) for (const d of u.drops ?? []) foe(u, map, false, 'Dropped by', d)
    for (const g of map.reinforcements ?? []) for (const u of g.units) for (const d of u.drops ?? []) foe(u, map, true, 'Dropped by', d)
    // What your own units start the chapter holding (Gunter's lance, Felicia's dagger, Corrin's Yato), kept apart too.
    for (const k of map.kit ?? []) for (const i of k.items) add(i, map, `Starts with ${k.name}`, undefined, kits)
    // What foes carry, kept apart: it only matters for the weapons no one but foes use.
    for (const u of map.units) for (const c of u.carries ?? []) foe(u, map, false, 'Carried by', c)
    for (const g of map.reinforcements ?? []) for (const u of g.units) for (const c of u.carries ?? []) foe(u, map, true, 'Carried by', c)
  }
  for (const f of foes.values()) add(f.item, f.map, foeText(f), f.later ? true : undefined, f.verb === 'Carried by' ? carriers : index)
  // In the order the maps come in, as the map page lists them.
  const order = new Map(ALL_MAPS.map((m, i) => [m.id, i]))
  for (const lists of [index, carriers, kits]) for (const list of lists.values()) list.sort((x, y) => order.get(x.mapId)! - order.get(y.mapId)!)
  return { index, carriers, kits }
}

let built: ReturnType<typeof buildIndex> | undefined

/** Every chest, village and enemy drop on the maps that gives this item, read from the game's files. */
export function itemSources(item: string): ItemSource[] {
  built ??= buildIndex()
  return built.index.get(item) ?? []
}

/** The units of your own army that start a chapter holding this item (a weapon you have from that chapter on). */
export function kitSources(item: string): ItemSource[] {
  built ??= buildIndex()
  return built.kits.get(item) ?? []
}

/** The foes on the maps who carry this item (for weapons the player never gets), read from the game's placement files. */
export function carrierSources(item: string): ItemSource[] {
  built ??= buildIndex()
  return built.carriers.get(item) ?? []
}
