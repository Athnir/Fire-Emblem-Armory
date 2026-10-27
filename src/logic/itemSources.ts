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

/** 'Spy's Shuriken or Spy's Yumi' -> both names; a hand note in brackets is dropped. */
function itemNames(text: string): string[] {
  return text.split(/ or /).map((t) => t.replace(/\s*\(.*\)\s*/, '').trim()).filter(Boolean)
}

function dropText(u: MapUnit, reinforcement: boolean, verb = 'Dropped by'): string {
  const who = u.paired && u.partner ? `${u.name} & ${u.partner}` : u.name
  const extras = [reinforcement ? 'reinforcement' : '', u.difficulties ? u.difficulties.join(', ') : ''].filter(Boolean)
  return `${verb} ${who}${extras.length ? ` (${extras.join('; ')})` : ''}`
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
  for (const map of ALL_MAPS) {
    for (const o of map.objects) {
      if (o.type === 'chest') add(o.contents, map, `Chest at (${o.tile[0]}, ${o.tile[1]})`)
      if (o.type === 'village' && o.reward) add(o.reward, map, `Village at (${o.tile[0]}, ${o.tile[1]})`)
    }
    for (const u of map.units) for (const d of u.drops ?? []) add(d, map, dropText(u, false))
    for (const g of map.reinforcements ?? []) for (const u of g.units) for (const d of u.drops ?? []) add(d, map, dropText(u, true), true)
    // What your own units start the chapter holding (Gunter's lance, Felicia's dagger, Corrin's Yato), kept apart too.
    for (const k of map.kit ?? []) for (const i of k.items) add(i, map, `Starts with ${k.name}`, undefined, kits)
    // What foes carry, kept apart: it only matters for the weapons no one but foes use.
    for (const u of map.units) for (const c of u.carries ?? []) add(c, map, dropText(u, false, 'Carried by'), undefined, carriers)
    for (const g of map.reinforcements ?? []) for (const u of g.units) for (const c of u.carries ?? []) add(c, map, dropText(u, true, 'Carried by'), true, carriers)
  }
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
