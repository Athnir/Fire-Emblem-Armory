import { useState } from 'react'
import { FE10_FORGE_CARDS } from '../data/fe10/fe10Weapons'
import type { TelliusWeapon } from '../data/fe9/types'
import type { Fe10ForgeChange } from '../logic/fe10Forge'
import { FE10_FORGE_LIMIT, FE10_FORGE_STEP, fe10CanLower, fe10ForgeCost, fe10ForgedStats, NO_CHANGE } from '../logic/fe10Forge'

const CELL = 'py-1 pr-2 sm:pr-3'
const ROWS: { key: keyof Fe10ForgeChange; label: string }[] = [
  { key: 'mt', label: 'Mt' },
  { key: 'hit', label: 'Hit' },
  { key: 'crit', label: 'Crit' },
  { key: 'wt', label: 'Wt' },
]
const signed = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : '0')

/** A Coin's card, in words: "Mt +1, Hit +10", "4 more Coins", "no bonus". */
function cardBonus(c: (typeof FE10_FORGE_CARDS)[number]) {
  const parts = [c.mt && `Mt +${c.mt}`, c.hit && `Hit +${c.hit}`, c.crit && `Crit +${c.crit}`, c.coins && `${c.coins} more Coins`].filter(Boolean)
  return parts.length ? parts.join(', ') : 'No bonus'
}

/** Radiant Dawn's forge for one base weapon: push each stat up or down and see the price. */
export function Fe10Forge({ weapon }: { weapon: TelliusWeapon }) {
  const [change, setChange] = useState<Fe10ForgeChange>(NO_CHANGE)
  const forged = fe10ForgedStats(weapon, change)
  const cost = fe10ForgeCost(weapon, change)
  const step = (key: keyof Fe10ForgeChange, by: number) => setChange((c) => ({ ...c, [key]: c[key] + by }))
  const button = 'h-7 w-7 rounded border border-neutral-700 bg-neutral-900 text-neutral-200 disabled:opacity-30'
  const cards = [...FE10_FORGE_CARDS].sort((a, b) => b.chance - a.chance)

  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-semibold text-neutral-100">Forge</h3>
      {weapon.forge && (
        <p className="text-neutral-400">
          At the base's forge: <span className="text-neutral-200">{weapon.forge.normal || 'not offered'}</span> on Easy and Normal,{' '}
          <span className="text-neutral-200">{weapon.forge.hard || 'not offered'}</span> on Hard.
        </p>
      )}
      <table className="w-full border-collapse text-xs sm:text-sm">
        <thead>
          <tr className="border-b border-neutral-700 text-left text-neutral-400">
            <th className={CELL}>Stat</th>
            <th className={CELL}>Base</th>
            <th className={CELL}>Forged</th>
            <th className={CELL}>Change</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(({ key, label }) => (
            <tr key={key} className="border-b border-neutral-800">
              <td className={`${CELL} text-neutral-100`}>{label}</td>
              <td className={CELL}>{weapon[key]}</td>
              <td className={`${CELL} ${change[key] ? 'text-emerald-300' : ''}`}>{forged[key]}</td>
              <td className={`${CELL} whitespace-nowrap`}>
                <button className={button} onClick={() => step(key, -1)} disabled={!fe10CanLower(weapon, change, key)} aria-label={`Less ${label}`}>
                  −
                </button>
                <span className="inline-block w-12 text-center text-neutral-300">{signed(change[key] * FE10_FORGE_STEP[key])}</span>
                <button className={button} onClick={() => step(key, 1)} disabled={change[key] >= FE10_FORGE_LIMIT} aria-label={`More ${label}`}>
                  +
                </button>
                <span className="ml-2 text-neutral-500">±{FE10_FORGE_STEP[key]} a step</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-neutral-300">
          Cost: <span className="text-lg text-amber-200">{cost.toLocaleString()}G</span>{' '}
          <span className="text-neutral-500">
            ({weapon.worth.toLocaleString()}G for the weapon + {(cost - weapon.worth).toLocaleString()}G forging)
          </span>
        </p>
        <button className="ml-auto rounded border border-neutral-700 px-2 py-1 text-neutral-300" onClick={() => setChange(NO_CHANGE)}>
          Reset
        </button>
      </div>
      <ul className="list-disc space-y-1 pl-5 text-neutral-400">
        <li>
          Each stat can go up or down by up to {FE10_FORGE_LIMIT} steps. Each one costs steps² × a tenth of the weapon's price, whichever way
          it goes. Mt, Hit and Wt can't drop below 1, Crit below 0.
        </li>
        <li>Uses, rank and range stay the same as the base weapon's. You name it and pick its colour, and you can forge as many as you like per visit.</li>
      </ul>
      <details className="text-neutral-400">
        <summary className="cursor-pointer text-neutral-300">Coin cards: a Coin adds a random bonus</summary>
        <table className="mt-1 w-full border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-neutral-700 text-left text-neutral-400">
              <th className={CELL}>Card</th>
              <th className={CELL}>Bonus</th>
              <th className={CELL}>Chance</th>
            </tr>
          </thead>
          <tbody>
            {cards.map((c) => (
              <tr key={c.name} className="border-b border-neutral-800">
                <td className={`${CELL} text-neutral-100`}>{c.name}</td>
                <td className={CELL}>{cardBonus(c)}</td>
                <td className={CELL}>{c.chance}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
}
