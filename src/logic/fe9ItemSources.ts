import { FE9_MAP_SET } from '../data/fe9/fe9MapSet'
import type { MapUnit } from '../data/maps/types'

/** One place on Path of Radiance's maps an item comes from. */
export interface Fe9ItemSource {
  mapId: string
  /** 'Chapter 7: Shades of Evil'. */
  map: string
  /** 'Chest at (2, 22)', 'Village at (8, 13)', 'Dropped by Ikanau', 'Buried near (12, 17)'. */
  how: string
}

/** 'Coin, Physic' -> each item; a note in brackets is dropped. */
const itemNames = (text: string) =>
  text
    .split(/, | or /)
    .map((t) => t.replace(/\s*\(.*\)\s*/, '').trim())
    .filter(Boolean)

function dropText(u: MapUnit, reinforcement: boolean): string {
  const extras = [reinforcement ? 'reinforcement' : '', u.difficulties?.length === 1 ? `${u.difficulties[0] === 'Normal' ? 'Easy/Normal' : u.difficulties[0]} only` : '']
  const shown = extras.filter(Boolean)
  return `Dropped by ${u.name}${shown.length ? ` (${shown.join('; ')})` : ''}`
}

function buildIndex(): Map<string, Fe9ItemSource[]> {
  const index = new Map<string, Fe9ItemSource[]>()
  for (const map of FE9_MAP_SET.maps) {
    const add = (item: string, how: string) => {
      for (const name of itemNames(item)) {
        const list = index.get(name) ?? []
        if (!list.some((s) => s.mapId === map.id && s.how === how)) list.push({ mapId: map.id, map: FE9_MAP_SET.mapLabel(map), how })
        index.set(name, list)
      }
    }
    for (const o of map.objects) {
      if (o.type === 'chest') add(o.contents, `Chest at (${o.tile[0]}, ${o.tile[1]})`)
      if (o.type === 'village' && o.reward) add(o.reward, `Village at (${o.tile[0]}, ${o.tile[1]})`)
      if (o.type === 'hidden' && !o.note) add(o.contents, `Buried near (${o.tile[0]}, ${o.tile[1]})`)
    }
    for (const u of map.units) for (const d of u.drops ?? []) add(d, dropText(u, false))
    for (const g of map.reinforcements ?? []) for (const u of g.units) for (const d of u.drops ?? []) add(d, dropText(u, true))
  }
  return index
}

let index: Map<string, Fe9ItemSource[]> | undefined

/** Every chest, village, buried spot and enemy drop on Path of Radiance's maps that gives this item. */
export function fe9ItemSources(item: string): Fe9ItemSource[] {
  index ??= buildIndex()
  return index.get(item) ?? []
}
