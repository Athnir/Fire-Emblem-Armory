import type { Faction, Weapon, WeaponCategory } from '../types'
import { HOSHIDO_CATEGORIES, NOHR_CATEGORIES } from '../types'
import { GAME_ITEMS } from './gameItems'

const TARGET: Record<string, string> = {
  flying: 'Flying units', dragon: 'Dragon units', armour: 'Armoured units', beast: 'Horse/Beast units', monster: 'Monster units',
  sword: 'Sword-wielding units', lance: 'Lance-wielding units', axe: 'Axe-wielding units', tome: 'Tome-wielding units',
}

const signed = (n: number) => (n > 0 ? `+${n}` : `${n}`)

/**
 * What the weapon does, in the wording the other weapons use: follow-up speed and crit rules from the item's own fields, and
 * the game's sentences about who may use it and what it does on a hit. Its flavour lines are left out.
 */
function effectsOf(g: (typeof GAME_ITEMS)[string]): { text: string; noFollowUp: boolean } {
  const noFollowUp = /cannot make follow-up/i.test(g.help)
  const parts: string[] = []
  if (noFollowUp) parts.push('Cannot make follow up attacks')
  if (g.followUpSpd) parts.push(`Follow up attack speed ${signed(g.followUpSpd)}`)
  if (g.guardSpd) parts.push(`Enemy's follow up attack speed ${signed(-g.guardSpd)}`)
  if (g.noCritOrSkills) parts.push('Cannot trigger critical hits or special skills')
  const sentences = g.help.split(/(?<=\.)\s+/)
  for (const t of sentences) {
    if (/^\w+ only\.$/i.test(t)) parts.push(`${t.slice(0, -1).replace(/ only$/i, '')} only`)
    else if (/after use in combat|on a hit|^restores/i.test(t)) parts.push(t.replace(/\.$/, ''))
  }
  return { text: parts.join(', '), noFollowUp }
}

/** In the item table but not a foe's weapon: Lilith's (an NPC the player never controls), and the automatic dragon-form attack Corrin and Kana use. */
const NOT_FOE_WEAPONS = new Set(['Draconic Rage', 'Astral Breath', 'Astral Blessing'])

const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'item'

/**
 * The weapons in the game's item table that no list of the player's weapons has: the ones only enemy units carry (Kukris,
 * Javelins, Bölverk, Skadi, breaths, rocks, saws). They're read straight from the item record and marked `foeOnly`; the maps
 * say which foes carry each one.
 */
export function foeOnlyWeapons(known: Set<string>): Weapon[] {
  return Object.entries(GAME_ITEMS)
    .filter(([name]) => !known.has(name) && !NOT_FOE_WEAPONS.has(name))
    .map(([name, g]) => {
      const category = g.category as WeaponCategory
      const faction: Faction = HOSHIDO_CATEGORIES.includes(category) ? 'Hoshido' : NOHR_CATEGORIES.includes(category) ? 'Nohr' : 'Neutral'
      const { text, noFollowUp } = effectsOf(g)
      const vs = g.effective.map((t) => TARGET[t]).filter(Boolean)
      return {
        id: slug(name),
        name,
        category,
        faction,
        rank: g.rank,
        stats: { mt: g.mt, hit: g.hit, crit: g.crit, avoid: g.avoid, dodge: g.dodge, range: g.range[0] === g.range[1] ? `${g.range[0]}` : `${g.range[0]}~${g.range[1]}` },
        effects: text,
        canCrit: !g.noCritOrSkills,
        ...(noFollowUp ? { canFollowUp: false } : {}),
        forgeable: false,
        ...(vs.length ? { effectiveness: { vs: vs.join(' and '), multiplier: 3, ...(g.weakVsOthers ? { nonEffectivePenalty: { mt: -4, hit: -10 } } : {}) } } : {}),
        availability: { routes: [], source: '' },
        foeOnly: true as const,
        iconId: slug(name),
      }
    })
}
