import { useState } from 'react'
import type { Fe9Weapon } from '../data/fe9/types'
import { useDifficulty } from './Difficulty'
import { telliusKey } from '../logic/spoilerWeapons'
import type { Fe9ForgeSteps } from '../logic/fe9Forge'
import { fe9ForgeCost, fe9ForgedStats, fe9ForgeMaxSteps, fe9ForgeMinSteps, NO_FORGE } from '../logic/fe9Forge'

const CELL = 'py-1 pr-2 sm:pr-3'
/** `by`: how far one step moves the stat (a Wt step lightens it, so the stat's own buttons run the steps the other way). */
const ROWS: { key: keyof Fe9ForgeSteps; label: string; by: number }[] = [
  { key: 'mt', label: 'Mt', by: 1 },
  { key: 'hit', label: 'Hit', by: 5 },
  { key: 'crit', label: 'Crit', by: 3 },
  { key: 'wt', label: 'Wt', by: -1 },
]
const signed = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : '0')

/** Path of Radiance's forge for one base weapon: pick how far to push each stat and see the price. */
export function Fe9Forge({ weapon }: { weapon: Fe9Weapon }) {
  // The bases whose forge offers it, on the difficulty picked in the bar.
  const offered = weapon.forge?.[telliusKey(useDifficulty())]
  const [steps, setSteps] = useState<Fe9ForgeSteps>(NO_FORGE)
  const max = fe9ForgeMaxSteps(weapon)
  const min = fe9ForgeMinSteps(weapon)
  const forged = fe9ForgedStats(weapon, steps)
  const lowest = fe9ForgedStats(weapon, min)
  const highest = fe9ForgedStats(weapon, max)
  const cost = fe9ForgeCost(weapon, steps)
  const step = (key: keyof Fe9ForgeSteps, by: number) =>
    setSteps((s) => ({ ...s, [key]: Math.max(min[key], Math.min(max[key], s[key] + by)) }))
  const button = 'h-7 w-7 rounded border border-neutral-700 bg-neutral-900 text-neutral-200 disabled:opacity-30'

  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-semibold text-neutral-100">Forge</h3>
      {offered && (
        <p className="text-neutral-400">
          At the base's forge: <span className="text-neutral-200">{offered}</span>.
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
          {ROWS.map(({ key, label, by }) => {
            // The buttons move the stat itself: on the Wt row, − is a lightening step and + a heavier one.
            const down = by > 0 ? -1 : 1
            const atLow = by > 0 ? steps[key] <= min[key] : steps[key] >= max[key]
            const atHigh = by > 0 ? steps[key] >= max[key] : steps[key] <= min[key]
            const low = (by > 0 ? lowest : highest)[key] - weapon[key]
            const high = (by > 0 ? highest : lowest)[key] - weapon[key]
            return (
              <tr key={key} className="border-b border-neutral-800">
                <td className={`${CELL} text-neutral-100`}>{label}</td>
                <td className={CELL}>{weapon[key]}</td>
                <td className={`${CELL} ${steps[key] ? (forged[key] > weapon[key] === by > 0 ? 'text-emerald-300' : 'text-rose-300') : ''}`}>
                  {forged[key]}
                </td>
                <td className={CELL}>
                  <span className="mr-2 inline-block whitespace-nowrap">
                    <button className={button} onClick={() => step(key, down)} disabled={atLow} aria-label={`Lower ${label}`}>
                      −
                    </button>
                    <span className="inline-block w-12 text-center text-neutral-300">{signed(forged[key] - weapon[key])}</span>
                    <button className={button} onClick={() => step(key, -down)} disabled={atHigh} aria-label={`Raise ${label}`}>
                      +
                    </button>
                  </span>
                  <span className="inline-block whitespace-nowrap text-neutral-500">
                    {Math.abs(by)} a step, {signed(low)} to {signed(high)}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-neutral-300">
          Cost: <span className="text-lg text-amber-200">{cost.toLocaleString()}G</span>{' '}
          <span className="text-neutral-500">
            ({weapon.worth.toLocaleString()}G for the weapon + {(cost - weapon.worth).toLocaleString()}G forging)
          </span>
        </p>
        <div className="ml-auto flex gap-2">
          <button className="rounded border border-neutral-700 px-2 py-1 text-neutral-300" onClick={() => setSteps(max)}>
            Max all
          </button>
          <button className="rounded border border-neutral-700 px-2 py-1 text-neutral-300" onClick={() => setSteps(NO_FORGE)}>
            Reset
          </button>
        </div>
      </div>
      <ul className="list-disc space-y-1 pl-5 text-neutral-400">
        <li>
          Each stat can be raised or lowered: Mt and Wt never go below 1, and Crit only drops while it's above 0. Lowering costs
          gold as raising does. Uses, rank and range stay the same as the base weapon's.
        </li>
        <li>You name the weapon and pick its colour. One forged weapon per base visit.</li>
      </ul>
    </div>
  )
}
