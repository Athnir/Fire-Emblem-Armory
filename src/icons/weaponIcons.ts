import type { Sprite } from './sprites'
import { ARMOR_HELM, AXE_ICON, DRAGON_HEAD, HORSE_HEAD, LANCE_ICON, MONSTER, SWORD_ICON, TOME_ICON, WING } from './sprites'

/** What a weapon's "effective against" text names, each with its own icon. */
const TARGETS: { match: RegExp; sprite: Sprite; label: string }[] = [
  { match: /armou?r/i, sprite: ARMOR_HELM, label: 'armoured units' },
  { match: /dragon/i, sprite: DRAGON_HEAD, label: 'dragons' },
  { match: /flying/i, sprite: WING, label: 'fliers' },
  { match: /horse|beast/i, sprite: HORSE_HEAD, label: 'mounted and beast units' },
  { match: /monster/i, sprite: MONSTER, label: 'monsters' },
  { match: /sword-wielding/i, sprite: SWORD_ICON, label: 'sword users' },
  { match: /lance-wielding/i, sprite: LANCE_ICON, label: 'lance users' },
  { match: /axe-wielding/i, sprite: AXE_ICON, label: 'axe users' },
  { match: /tome-wielding/i, sprite: TOME_ICON, label: 'tome users' },
]

/** The icons for a weapon's effectiveness ('Flying and Monster units' gets both a wing and a mask). */
export function effectivenessIcons(vs: string): { sprite: Sprite; label: string }[] {
  return TARGETS.filter((t) => t.match.test(vs))
}

/** What each kind of Might boost does (separate from effectiveness, which only boosts Might against one foe type). */
export const MIGHT_TEXT = {
  counter: 'Mt doubles on counterattacks',
  attack: 'Mt doubles when it starts the fight',
  skill: "Mt doubles when the wielder's Skill is higher than the foe's",
} as const
