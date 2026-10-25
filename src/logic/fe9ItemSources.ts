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

/** The items a unit's note lists: 'Lv 20 General: Wishblade, Elixir. Stands on the throne.' -> Wishblade, Elixir. */
function noteItems(note: string | undefined): string[] {
  const list = note?.split(': ')[1]
  return list ? list.split('. ')[0].replace(/\s*\(.*?\)/g, '').split(', ').map((t) => t.trim()) : []
}

function buildIndex(set: MapSet, foeOnly: ReadonlySet<string>): Map<string, Fe9ItemSource[]> {
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
    // A foe's own weapon, seen on whoever carries it when the chapter starts (a unit who arrives later isn't there to see).
    for (const u of map.units) {
      if (u.type === 'ally') continue
      for (const item of noteItems(u.note)) if (foeOnly.has(item)) add(item, `Carried by ${u.name}`)
    }
    for (const g of map.reinforcements ?? []) for (const u of g.units) for (const d of u.drops ?? []) add(d, dropText(u, true), true)
  }
  return index
}

/**
 * Every chest, village, buried spot and enemy drop on a game's maps that gives an item: `itemSourcesFor(FE9_MAP_SET, foeOnly)('Iron Sword')`.
 * For a foe's own weapon (`foeOnly`, named in the set), the foes who carry it when the chapter starts.
 */
export function itemSourcesFor(set: MapSet, foeOnly: ReadonlySet<string> = new Set()): (item: string) => Fe9ItemSource[] {
  let index: Map<string, Fe9ItemSource[]> | undefined
  return (item) => {
    index ??= buildIndex(set, foeOnly)
    return index.get(item) ?? []
  }
}
