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
    effects: 'Cannot make follow up attacks; Skill -3, Speed -2, Defence +4 and Resistance +3. Usable only by dragon-lineage classes (Corrin, Nohr Prince/Princess, Manaketes)',
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
    effects: 'Cannot make follow up attacks; Skill -5, Speed -4, Defence +9 and Resistance +7; after battle, Magic and Skill -2 until next turn',
    canCrit: true,
    canFollowUp: false,
    isMagic: true,
    forgeable: false,
    availability: {
      routes: ['all'],
      source: 'Chapter 20 treasure chest (x2), or dropped by the enemy Camilla in Chapter 23',
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
