import type { MapSet } from '../data/maps/mapSet'
import type { MapUnit } from '../data/maps/types'

/** One place on a Tellius game's maps an item comes from. */
export interface Fe9ItemSource {
  mapId: string
  /** 'Chapter 7: Shades of Evil'. */
  map: string
  /** 'Chest at (2, 22)', 'Village at (8, 13)', 'Dropped by Ikanau', 'Buried near (12, 17)', 'Steal from Warrior'. */
  how: string
  /** Dropped by (or stolen from) a foe that only arrives mid-chapter: not on the map at the start. */
  arrives?: true
}

/** Which weapons a foe's steal lines are given for, and how to tell its weapons from its items (Path of Radiance). */
export interface StealRule {
  /** Every weapon's name and category. */
  categories: ReadonlyMap<string, string>
  /** The weapons a steal line is worth giving for: those no base sells or forges. */
  listed: ReadonlySet<string>
}

const TOMES = new Set(['Fire', 'Thunder', 'Wind', 'Light', 'Dark'])

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

/**
 * What a thief can take from a foe in Path of Radiance: Steal takes what isn't equipped. A foe with two weapons to fight with
 * unequips one whenever it uses the other, and a silenced foe's lone tome comes off once it uses an item; a lone weapon stays.
 */
function stealable(u: MapUnit, steal: StealRule): string[] {
  const carried = noteItems(u.note)
  const arms = carried.filter((n) => steal.categories.has(n) && steal.categories.get(n) !== 'Staff')
  const items = carried.filter((n) => !steal.categories.has(n))
  if (arms.length > 1) return arms
  return arms.length === 1 && TOMES.has(steal.categories.get(arms[0])!) && items.length ? arms : []
}

function buildIndex(set: MapSet, foeOnly: ReadonlySet<string>, steal?: StealRule): Map<string, Fe9ItemSource[]> {
  const label = (d: string) => set.difficulties.find((x) => x.value === d)?.label.replace(/ \/ /g, '/') ?? d
  const all = set.difficulties.map((d) => d.value)
  // One line per way of getting it on a map: a foe placed on both difficulties (two entries in the files) is said once.
  const lines = new Map<string, { item: string; mapId: string; map: string; base: string; reinforcement: boolean; diffs: Set<string> }>()
  const index = new Map<string, Fe9ItemSource[]>()
  for (const map of set.maps) {
    const add = (item: string, base: string, opts: { reinforcement?: boolean; diffs?: readonly string[] } = {}) => {
      for (const name of itemNames(item)) {
        const key = [name, map.id, base, !!opts.reinforcement].join('|')
        const line = lines.get(key) ?? { item: name, mapId: map.id, map: set.mapLabel(map), base, reinforcement: !!opts.reinforcement, diffs: new Set<string>() }
        for (const d of opts.diffs ?? all) line.diffs.add(d)
        lines.set(key, line)
      }
    }
    for (const o of map.objects) {
      if (o.type === 'chest') add(o.contents, `Chest at (${o.tile[0]}, ${o.tile[1]})`)
      if (o.type === 'village' && o.reward) add(o.reward, `Village at (${o.tile[0]}, ${o.tile[1]})`)
      if (o.type === 'hidden' && !o.note) add(o.contents, `Buried near (${o.tile[0]}, ${o.tile[1]})`)
    }
    const foeLines = (u: MapUnit, reinforcement: boolean) => {
      for (const d of u.drops ?? []) add(d, `Dropped by ${u.name}`, { reinforcement, diffs: u.difficulties })
      if (!steal || u.type === 'ally') return
      for (const w of stealable(u, steal))
        if (steal.listed.has(w) && !u.drops?.includes(w)) add(w, `Steal from ${u.name}`, { reinforcement, diffs: u.difficulties })
    }
    for (const u of map.units) foeLines(u, false)
    // A foe's own weapon, seen on whoever carries it when the chapter starts (a unit who arrives later isn't there to see).
    for (const u of map.units) {
      if (u.type === 'ally') continue
      for (const item of noteItems(u.note)) if (foeOnly.has(item)) add(item, `Carried by ${u.name}`, { diffs: u.difficulties })
    }
    for (const g of map.reinforcements ?? []) for (const u of g.units) foeLines(u, true)
  }
  for (const line of lines.values()) {
    const some = all.filter((d) => line.diffs.has(d))
    const extras = [line.reinforcement ? 'reinforcement' : '', some.length < all.length ? `${some.map(label).join(', ')} only` : '']
    const shown = extras.filter(Boolean)
    const how = `${line.base}${shown.length ? ` (${shown.join('; ')})` : ''}`
    const list = index.get(line.item) ?? []
    list.push({ mapId: line.mapId, map: line.map, how, ...(line.reinforcement && { arrives: true as const }) })
    index.set(line.item, list)
  }
  return index
}

/**
 * Every chest, village, buried spot and enemy drop on a game's maps that gives an item: `itemSourcesFor(FE9_MAP_SET, foeOnly)('Iron Sword')`.
 * For a foe's own weapon (`foeOnly`, named in the set), the foes who carry it when the chapter starts; with `steal`, the foes a
 * weapon no base sells can be stolen from.
 */
export function itemSourcesFor(set: MapSet, foeOnly: ReadonlySet<string> = new Set(), steal?: StealRule): (item: string) => Fe9ItemSource[] {
  let index: Map<string, Fe9ItemSource[]> | undefined
  return (item) => {
    index ??= buildIndex(set, foeOnly, steal)
    return index.get(item) ?? []
  }
}
