import type { ReactNode } from 'react'
import type { Weapon } from '../data/types'
import { PixelIcon } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import { BRAVE, MAGIC, MIGHT_UP, NO_CRIT, NO_FOLLOW_UP, NOT_FOR_PLAYER, REVERSED_TRIANGLE } from '../icons/sprites'
import { effectivenessIcons } from '../icons/weaponIcons'

/** Compact pixel-art markers shown next to a weapon's name in the list. Each mirrors a badge in
 * WeaponDetailPanel; the effectiveness ones show what the weapon is effective against. */
function WeaponMarkers({ weapon }: { weapon: Weapon }) {
  const icon = (sprite: Sprite, title: string) => (
    <span className="ml-1 inline-flex" title={title}>
      <PixelIcon sprite={sprite} size={14} title={title} />
    </span>
  )
  return (
    <>
      {weapon.foeOnly && icon(NOT_FOR_PLAYER, 'Foe only: carried by enemy units, not available to the player')}
      {weapon.isMagic && icon(MAGIC, 'Uses Magic for damage, not Strength')}
      {weapon.effectiveness &&
        effectivenessIcons(weapon.effectiveness.vs).map((t) => (
          <span key={t.label}>{icon(t.sprite, `Effective vs. ${t.label} (×${weapon.effectiveness!.multiplier} Might)`)}</span>
        ))}
      {weapon.strikesTwice && icon(BRAVE, 'Strikes twice when it starts the fight')}
      {weapon.mightBoost && icon(MIGHT_UP, 'Mt boost (the condition is in its effect)')}
      {weapon.reversesTriangle && icon(REVERSED_TRIANGLE, 'Reverses the weapon triangle and doubles its effects')}
      {weapon.canCrit === false &&
        weapon.category !== 'Staff' &&
        weapon.category !== 'Rod' &&
        icon(NO_CRIT, 'Cannot land critical hits or trigger offensive skills')}
      {weapon.canFollowUp === false && icon(NO_FOLLOW_UP, 'Cannot make a follow-up attack')}
    </>
  )
}

/** A number column: just wide enough for its values, a little more room from 640px up. */
const NUM = 'w-0 py-1 pr-2 sm:pr-3'

export function WeaponList({
  weapons,
  selectedId,
  onSelect,
  badges,
}: {
  weapons: Weapon[]
  selectedId: string | null
  onSelect: (id: string) => void
  /** Extra marks after a weapon's name (the spoiler block's shop and new tags). */
  badges?: (weapon: Weapon) => ReactNode
}) {
  return (
    // Fits a phone: the name column takes the slack and wraps, the number columns stay narrow.
    <table className="w-full border-collapse text-xs sm:text-sm">
      <thead>
        <tr className="border-b border-neutral-700 text-left text-neutral-400">
          <th className="py-1 pl-2 pr-1 sm:pr-3">Name</th>
          <th className={NUM}>Rank</th>
          <th className={NUM}>Mt</th>
          <th className={NUM}>Hit</th>
          <th className={NUM}>Crit</th>
          <th className={NUM}>Rng</th>
        </tr>
      </thead>
      <tbody>
        {weapons.map((w) => (
          <tr
            key={w.id}
            onClick={() => onSelect(w.id)}
            className={`cursor-pointer border-b border-neutral-800 hover:bg-neutral-800 ${
              selectedId === w.id ? 'bg-neutral-800' : ''
            }`}
          >
            <td className="py-1 pl-2 pr-1 text-neutral-100 sm:pr-3">
              {w.name}
              <WeaponMarkers weapon={w} />
              {badges?.(w)}
            </td>
            <td className={`${NUM} text-neutral-400`}>{w.rank}</td>
            <td className={NUM}>{w.stats.mt}</td>
            <td className={NUM}>{w.stats.hit}</td>
            <td className={NUM}>{w.stats.crit}</td>
            <td className={`${NUM} whitespace-nowrap`}>{w.stats.range}</td>
          </tr>
        ))}
        {weapons.length === 0 && (
          <tr>
            <td colSpan={6} className="py-4 text-center text-neutral-500">
              No weapons match the current filters.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  )
}
