import type { Weapon } from '../types'

/**
 * "Other Weapons" from Serenes Forest's Miscellaneous page
 * (https://serenesforest.net/fire-emblem-fates/inventory/miscellaneous/): Dragonstones, Beaststones,
 * and dragon-transformation "breath" weapons. Not Hoshido- or Nohr-specific (both the Staff Store
 * and Rod Store sell the base Dragonstone/Beaststone) — faction 'Neutral'. Explicitly excluded from
 * Smithy forging by the Smithy's own stated example ("non-standard weapons, e.g. dragonstones").
 *
 * Most of this page's entries are excluded from the dataset entirely, verified per-weapon on Fire
 * Emblem Wiki rather than assumed from the "cannot trade" flavor text alone:
 * - Dark Breath and both Dragon Breath variants are enemy-exclusive boss weapons — Garon's dragon
 *   form (Birthright) and Anankos's true form, respectively. Never player-usable.
 * - Astral Breath is Lilith's NPC-exclusive Conquest weapon (see staves.ts's Astral Blessing note —
 *   same character, same "never a controllable unit" reasoning).
 * - The entire Monster weapons (Shackled Fist, Gauntlet, Rock, Massive Rock) and Puppet weapons (Saw,
 *   Big Saw) sections are explicitly "Faceless only" / "Stoneborn only" / "Automatons only" — these
 *   are pure enemy monster classes with no playable member, so (per the no-steal-mechanic rule used
 *   throughout this project) the player can never actually acquire them.
 *
 * Draconic Rage is ALSO excluded, for a different reason than the above: it's not enemy-only, but
 * it's the same category as the already-removed Ganglari — an automatic, transient dragon-form
 * attack Corrin (and Kana) briefly uses before a real Dragonstone takes over, not a genuine
 * inventory item the player holds, keeps, or interacts with. This project's scope is weapons the
 * player actually keeps and controls after picking a route, not every automatic/story-triggered
 * attack a unit happens to use — a personal weapon like Ike's Backup still counts even though Ike
 * himself can't hand it to another unit, because the PLAYER can keep and use it; a transient
 * transformation attack like this doesn't clear that bar regardless of who's wielding it.
 */
export const OTHER: Weapon[] = [
  {
    id: 'dragonstone',
    name: 'Dragonstone',
    category: 'Other',
    faction: 'Neutral',
    rank: 'E',
    stats: { mt: 14, hit: 85, crit: 0, avoid: -10, dodge: 10, range: '1' },
    effects: 'Cannot make follow up attacks; Skill -3, Speed -2, Defence +4 and Resistance +3. Usable only by dragon-lineage classes (Corrin, Nohr Prince/Princess, Manaketes)',
    canCrit: true,
    isMagic: true,
    forgeable: false,
    purchase: { buy: 2000, sell: 0 },
    availability: { routes: ['all'], source: 'Staff Store or Rod Store (whichever your route builds)' },
    iconId: 'dragonstone',
  },
  {
    id: 'dragonstone-plus',
    name: 'Dragonstone+',
    category: 'Other',
    faction: 'Neutral',
    rank: 'C',
    stats: { mt: 25, hit: 75, crit: 0, avoid: -10, dodge: 10, range: '1' },
    effects: 'Cannot make follow up attacks; Skill -5, Speed -4, Defence +9 and Resistance +7; after battle, Magic and Skill -2 until next turn',
    canCrit: true,
    isMagic: true,
    forgeable: false,
    isMyCastle: true,
    availability: {
      routes: ['all'],
      source: 'Chapter 20 treasure chest (x2), or dropped by the enemy Camilla in Chapter 23; also a My Castle Battle Rank 3000 reward',
    },
    iconId: 'dragonstone-plus',
  },
  {
    id: 'beaststone',
    name: 'Beaststone',
    category: 'Other',
    faction: 'Neutral',
    rank: 'E',
    stats: { mt: 6, hit: 90, crit: 5, avoid: 10, dodge: 10, range: '1' },
    effects: 'Skill +5, Speed +3, Defence -2. Usable only by beast-lineage classes (Kitsune, Wolfskin, and their promotions)',
    canCrit: true,
    forgeable: false,
    purchase: { buy: 2000, sell: 0 },
    availability: { routes: ['all'], source: 'Staff Store or Rod Store (whichever your route builds)' },
    iconId: 'beaststone',
  },
  {
    id: 'beastrune',
    name: 'Beastrune',
    category: 'Other',
    faction: 'Neutral',
    rank: 'C',
    stats: { mt: 9, hit: 80, crit: 0, avoid: 0, dodge: 10, range: '1' },
    effects: 'Skill -2, Speed -1, Defence +4 and Resistance +5',
    canCrit: true,
    forgeable: false,
    availability: {
      routes: ['all'],
      source: "Starts in Keaton's or Velouria's inventory; also dropped by the enemy Wolfssegner in Chapter 15, or a Chapter 22 treasure chest",
    },
    iconId: 'beastrune',
  },
  {
    id: 'beaststone-plus',
    name: 'Beaststone+',
    category: 'Other',
    faction: 'Neutral',
    rank: 'B',
    stats: { mt: 12, hit: 90, crit: 5, avoid: 10, dodge: 10, range: '1' },
    effects: 'Skill +8, Speed +6, Defence -5, Resistance -3; after battle, Strength and Skill -2 until next turn',
    canCrit: true,
    forgeable: false,
    availability: {
      routes: ['all'],
      source: "Starts in Shura's inventory; also dropped by the enemy Kaden in Chapter 19, or a Chapter 26 treasure chest",
    },
    iconId: 'beaststone-plus',
  },
]
