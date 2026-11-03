import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeaponsConfig } from '../components/ChapterWeapons'
import { Fe17Supports } from '../components/Fe17Supports'
import { MapViewer } from '../components/MapViewer'
import { onDifficulty } from '../components/Difficulty'
import { FE17_ITEM_SOURCES } from '../data/fe17/fe17ItemSources'
import { FE17_LISTED } from '../data/fe17/fe17Listed'
import { FE17_ALL, FE17_MAP_SET, FE17_STORY } from '../data/fe17/fe17MapSet'
import { turnsUpAt } from '../logic/spoiler'
import type { GameParts } from '.'

const WEAPONS: ChapterWeaponsConfig = {
  weapons: FE17_LISTED,
  sources: FE17_ITEM_SOURCES,
  story: FE17_ALL,
  categories: ['Sword', 'Lance', 'Axe', 'Bow', 'Knife', 'Tome', 'Staff', 'Arts', 'Special'],
  magic: new Set(['Tome']),
  statNames: { hp: 'HP', str: 'Str', dex: 'Dex', spd: 'Spd', lck: 'Lck', def: 'Def', mag: 'Mag', res: 'Res', bld: 'Bld', mov: 'Mov',
    avo: 'Avo', ddg: 'Ddg' },
  /** Against a unit it's effective on, the weapon's effectiveness skill multiplies by its EfficacyValue: 3 (skill.xml). */
  effectiveMultiplier: 3,
  rankLabel: (w) => (w.rank ? `Rank ${w.rank}` : 'No weapon rank'),
  shopName: 'the Somniel',
  routeName: (m) => (m.route === 'Fell Xenologue' ? 'Fell Xenologue' : m.route === 'Paralogue' ? 'Paralogues' : undefined),
}

/** Fire Emblem Engage's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE17_MAP_SET }),
  supports: Fe17Supports,
  // Who beats whom: item.xml's 相性 (each weapon kind's bits); what it's worth: calculator.xml's 相性補正, 0 either way. Its effect
  // is Break, as the game's own tutorial puts it (MID_TUT_BMAP_BREAK_*).
  triangle: {
    beats: { Sword: ['Axe'], Axe: ['Lance'], Lance: ['Sword'], Arts: ['Bow', 'Knife', 'Tome'] },
    outside: 'Staves and Special weapons are outside the triangle.',
    advantage: [{ mt: 0, hit: 0 }],
    loser: 'mirror',
    mtLabel: 'Mt',
    reaver: 'flip',
    rules: [
      "The triangle changes no numbers (the game's battle formulas give advantage and disadvantage +0).",
      "Break: a unit hit by a weapon its own is weak to is broken, and a broken unit can't counterattack until after its next combat.",
      "A reaver weapon (the item's InvertInteract flag: Emblem Roy's Lancereaver, Emblem Corrin's Dual Katana) turns the triangle around for it: a reaver sword beats lances and loses to axes.",
    ],
  },
  story: FE17_STORY,
  newWeapons: (mapId, _route, difficulty = 'Normal') => {
    const at = FE17_STORY.maps.findIndex((m) => m.id === mapId)
    return FE17_LISTED.filter((w) => {
      const sources = (FE17_ITEM_SOURCES[w.name] ?? []).filter((s) => onDifficulty(difficulty, s.difficulties))
      const first = Math.min(Infinity, ...sources.map((s) => turnsUpAt(FE17_STORY, s.mapId, s.kind.endsWith('-later'))))
      return first === at
    }).length
  },
  difficulties: FE17_MAP_SET.difficulties,
}

export default parts
