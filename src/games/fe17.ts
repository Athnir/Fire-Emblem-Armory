import { createElement } from 'react'
import { ChapterWeapons } from '../components/ChapterWeapons'
import type { ChapterWeapon, ChapterWeaponsConfig, ItemSource } from '../components/ChapterWeapons'
import { Fe17Refine } from '../components/Fe17Refine'
import { Fe17Supports } from '../components/Fe17Supports'
import { MapViewer } from '../components/MapViewer'
import { onDifficulty } from '../components/Difficulty'
import { FE17_ENGRAVE_COST_RATE, FE17_ENGRAVINGS } from '../data/fe17/fe17Engrave'
import { FE17_ITEM_SOURCES } from '../data/fe17/fe17ItemSources'
import { FE17_LISTED } from '../data/fe17/fe17Listed'
import { FE17_ALL, FE17_MAP_SET, FE17_STORY } from '../data/fe17/fe17MapSet'
import { FE17_SMITHY_OPENS } from '../data/fe17/fe17Refine'
import { turnsUpAt } from '../logic/spoiler'
import type { GameParts } from '.'

/** An emblem's weapon: an engage weapon (the item's Engage flag) or a copy a foe's emblem carries (its id names the emblem). */
const engageWeapon = (w: ChapterWeapon) => {
  const x = w as ChapterWeapon & { engage?: true; emblem?: true }
  return !!(x.engage || x.emblem)
}
const engageSource = (s: ItemSource) => s.kind.startsWith('engage')
const signed = (v: number) => (v < 0 ? `${v}` : `+${v}`)

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
  // The emblems' own weapons (every emblem's, and the copies the foes' emblems carry) are many: off until ticked.
  optional: [{ label: 'Show emblem weapons', covers: engageSource, weapons: engageWeapon }],
  /** Engravings (src/data/fe17/fe17Engrave.ts): any weapon but a staff or a blast takes one at the smithy, from an emblem of yours. */
  modifiers: {
    label: 'Engraving',
    options: (w, reach) =>
      (w as ChapterWeapon & { engrave?: true }).engrave && !w.foeOnly && reach.has(FE17_SMITHY_OPENS)
        ? FE17_ENGRAVINGS.filter((e) => reach.has(e.from)).map((e) => ({ ...e, label: `${e.name} (${e.emblem})` }))
        : [],
    note: (w, m) => {
      const adds = (['mt', 'wt', 'hit', 'crit', 'avo', 'ddg'] as const)
        .filter((k) => m[k])
        .map((k) => `${{ mt: 'Mt', wt: 'Wt', hit: 'Hit', crit: 'Crit', avo: 'Avo', ddg: 'Ddg' }[k]} ${signed(m[k]!)}`)
      const cost = Math.floor((w.worth ?? 0) * FE17_ENGRAVE_COST_RATE)
      return `${adds.join(', ')}. Engraved at the Somniel's smithy for ${cost.toLocaleString()} Bond Fragments (a tenth of the weapon's price).`
    },
  },
  /** Each weapon's refine levels and their costs (item.xml's refine table), once the smithy is open, with the engraving picked. */
  extra: (w, engraving) => createElement(Fe17Refine, { weapon: w, engraving }),
}

/** Fire Emblem Engage's screens and data: loaded on their own the first time the game is picked. */
const parts: GameParts = {
  weapons: () => createElement(ChapterWeapons, { config: WEAPONS }),
  maps: () => createElement(MapViewer, { set: FE17_MAP_SET }),
  supports: Fe17Supports,
  // Who beats whom: item.xml's 相性 (each weapon kind's bits); what it's worth: calculator.xml's 相性補正, 0 either way. Its effect
  // is Break, as the game's own tutorial puts it (MID_TUT_BMAP_BREAK_*). A weapon flagged InvertInteract turns it around.
  triangle: {
    beats: { Sword: ['Axe'], Axe: ['Lance'], Lance: ['Sword'], Arts: ['Bow', 'Knife', 'Tome'] },
    outside: 'Staves and Special weapons are outside the triangle.',
    advantage: [{ mt: 0, hit: 0 }],
    loser: 'mirror',
    mtLabel: 'Mt',
    calculator: false,
    rules: [
      "Having the advantage changes no numbers: the game's battle formulas give both sides +0.",
      "Break: a unit hit by a weapon its own is weak to is broken, and a broken unit can't counterattack until after its next combat.",
      'Some weapons turn the triangle around for the one using them.',
    ],
  },
  story: FE17_STORY,
  // The new-weapon count counts only what the list shows by default: no emblem weapons.
  newWeapons: (mapId, _route, difficulty = 'Normal') => {
    const at = FE17_STORY.maps.findIndex((m) => m.id === mapId)
    return FE17_LISTED.filter((w) => {
      if (engageWeapon(w)) return false
      const sources = (FE17_ITEM_SOURCES[w.name] ?? []).filter((s) => !engageSource(s) && onDifficulty(difficulty, s.difficulties))
      const first = Math.min(Infinity, ...sources.map((s) => turnsUpAt(FE17_STORY, s.mapId, s.kind.endsWith('-later'))))
      return first === at
    }).length
  },
  difficulties: FE17_MAP_SET.difficulties,
}

export default parts
