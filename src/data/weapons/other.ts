import type { Weapon } from '../types'

/**
 * "Other Weapons" from Serenes Forest's Miscellaneous page
 * (https://serenesforest.net/fire-emblem-fates/inventory/miscellaneous/): Dragonstones, Beaststones,
 * and dragon-transformation "breath" weapons. Not Hoshido- or Nohr-specific (both the Staff Store
 * and Rod Store sell the base Dragonstone/Beaststone) — faction 'Neutral'. Explicitly excluded from
 * Smithy forging by the Smithy's own stated example ("non-standard weapons, e.g. dragonstones").
 *
 * The weapons only foes use (Dark Breath, the Faceless's fists, the Stoneborn's rocks, the Automatons' saws) aren't here:
 * the player can never acquire them (no steal/disarm in Fates), so foeOnly.ts lists them from the game's item table,
 * marked as foe-only. Astral Breath and Astral Blessing are Lilith's, an NPC the player never controls, so they're left out
 * of every list.
 *
 * Draconic Rage is left out of every list, for a different reason: it's not enemy-only, but
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
    effects: 'Cannot make follow-up attacks. Usable only by dragon-lineage classes (Corrin, Nohr Prince/Princess, Manaketes)',
    canCrit: true,
    canFollowUp: false,
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
    effects: 'Cannot make follow-up attacks; after combat, Magic and Skill -2 (stacks; recovers 1 a turn)',
    canCrit: true,
    canFollowUp: false,
    isMagic: true,
    forgeable: false,
    availability: {
      routes: ['all'],
      source: '',
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
    effects: 'Usable only by beast-lineage classes (Kitsune, Wolfskin, and their promotions)',
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
    effects: '',
    canCrit: true,
    forgeable: false,
    availability: {
      routes: ['all'],
      source: '',
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
    effects: 'After combat, Strength and Skill -2 (stacks; recovers 1 a turn)',
    canCrit: true,
    forgeable: false,
    availability: {
      routes: ['all'],
      source: '',
    },
    iconId: 'beaststone-plus',
  },
]
