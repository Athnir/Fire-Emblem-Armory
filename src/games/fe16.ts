import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { MapViewer } from '../components/MapViewer'
import { onDifficulty } from '../components/Difficulty'
import { FE16_ITEM_SOURCES } from '../data/fe16/fe16ItemSources'
import { FE16_LISTED } from '../data/fe16/fe16Listed'
import { FE16_FORK, FE16_MAP_SET, FE16_STORY } from '../data/fe16/fe16MapSet'
import type { ChapterMap } from '../data/maps/types'
import { turnsUpAt, walkFork } from '../logic/spoiler'
import type { GameParts } from '.'

/** The house (White Clouds) or route (from Chapter 12) a map is its own, by its id's suffix; chapters every house plays have none. */
const ROUTE_NAMES: Record<string, string> = {
  be: 'Black Eagles', bl: 'Blue Lions', gd: 'Golden Deer', cf: 'Crimson Flower', ss: 'Silver Snow', am: 'Azure Moon',
  vw: 'Verdant Wind', cs: 'Cindered Shadows',
}
const routeName = (m: ChapterMap) =>
  m.route === 'Paralogue'
    ? 'Paralogues'
    : m.route === 'Auxiliary'
      ? 'Auxiliary battles'
      : ROUTE_NAMES[m.id.match(/-([a-z]{2})$/)?.[1] ?? '']

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE16_LISTED,
  sources: FE16_ITEM_SOURCES,
  story: FE16_STORY,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Gauntlets', 'Monster'],
  magic: new Set(),
  statNames: {},
  /** Against a unit it's effective on, the weapon's Mt is multiplied by 3 (the damage routine's effectiveness, 0xd99a0 and 0xc404c). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank ? `${w.category === 'Gauntlets' ? 'Brawling' : `${w.category}s`} ${w.rank}` : ''),
  shopName: 'armory',
  routeName,
}

/** Fire Emblem: Three Houses' screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE16_MAP_SET }),
  // Supports (what a support gives per level) come with the next step: their bonus code is found (0xd9330), its table isn't read yet.
  supports: undefined,
  // Three Houses has no weapon triangle: neither the hit (0xd9560) nor the damage routine (0xdb410) has a type-against-type term.
  triangle: null,
  fork: FE16_FORK,
  newWeapons: (mapId, route, difficulty = 'Normal') => {
    const story = walkFork(FE16_FORK, route).story
    const at = story.maps.findIndex((m) => m.id === mapId)
    return FE16_LISTED.filter((w) => {
      const sources = (FE16_ITEM_SOURCES[w.name] ?? []).filter((s) => onDifficulty(difficulty, s.difficulties))
      const first = Math.min(Infinity, ...sources.map((s) => turnsUpAt(story, s.mapId, s.kind.endsWith('-later'))))
      return first === at
    }).length
  },
  difficulties: FE16_MAP_SET.difficulties,
}

export default parts
