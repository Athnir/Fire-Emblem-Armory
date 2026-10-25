import { FE9_MAP_SET } from '../data/fe9/fe9MapSet'
import { FE10_MAP_SET } from '../data/fe10/fe10MapSet'
import type { MapSet } from '../data/maps/mapSet'
import type { MapUnit } from '../data/maps/types'

/** One place on a Tellius game's maps an item comes from. */
export interface Fe9ItemSource {
  mapId: string
  /** 'Chapter 7: Shades of Evil'. */
  map: string
  /** 'Chest at (2, 22)', 'Village at (8, 13)', 'Dropped by Ikanau', 'Buried near (12, 17)'. */
  how: string
  /** Dropped by a foe that only arrives mid-chapter: not on the map at the start. */
  arrives?: true
}

/** 'Coin, Physic' -> each item; a note in brackets is dropped. */
const itemNames = (text: string) =>
  text
    .split(/, | or /)
    .map((t) => t.replace(/\s*\(.*\)\s*/, '').trim())
    .filter(Boolean)

function buildIndex(set: MapSet): Map<string, Fe9ItemSource[]> {
  const label = (d: string) => set.difficulties.find((x) => x.value === d)?.label.replace(/ \/ /g, '/') ?? d
  const dropText = (u: MapUnit, reinforcement: boolean): string => {
    const extras = [reinforcement ? 'reinforcement' : '', u.difficulties?.length === 1 ? `${label(u.difficulties[0])} only` : '']
    const shown = extras.filter(Boolean)
    return `Dropped by ${u.name}${shown.length ? ` (${shown.join('; ')})` : ''}`
  }
  const index = new Map<string, Fe9ItemSource[]>()
  for (const map of set.maps) {
    const add = (item: string, how: string, arrives?: true) => {
      for (const name of itemNames(item)) {
        const list = index.get(name) ?? []
        if (!list.some((s) => s.mapId === map.id && s.how === how))
          list.push({ mapId: map.id, map: set.mapLabel(map), how, ...(arrives && { arrives }) })
        index.set(name, list)
      }
    }
    for (const o of map.objects) {
      if (o.type === 'chest') add(o.contents, `Chest at (${o.tile[0]}, ${o.tile[1]})`)
      if (o.type === 'village' && o.reward) add(o.reward, `Village at (${o.tile[0]}, ${o.tile[1]})`)
      if (o.type === 'hidden' && !o.note) add(o.contents, `Buried near (${o.tile[0]}, ${o.tile[1]})`)
    }
    for (const u of map.units) for (const d of u.drops ?? []) add(d, dropText(u, false))
    for (const g of map.reinforcements ?? []) for (const u of g.units) for (const d of u.drops ?? []) add(d, dropText(u, true), true)
  }
  return index
}

const indexes = new Map<MapSet, Map<string, Fe9ItemSource[]>>()

/** Every chest, village, buried spot and enemy drop on a game's maps that gives this item. */
function itemSourcesIn(set: MapSet, item: string): Fe9ItemSource[] {
  if (!indexes.has(set)) indexes.set(set, buildIndex(set))
  return indexes.get(set)!.get(item) ?? []
}

/** Path of Radiance's maps. */
export const fe9ItemSources = (item: string) => itemSourcesIn(FE9_MAP_SET, item)
/** Radiant Dawn's maps. */
export const fe10ItemSources = (item: string) => itemSourcesIn(FE10_MAP_SET, item)
