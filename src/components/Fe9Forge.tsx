import { useState } from 'react'
import type { Fe9Weapon } from '../data/fe9/types'
import type { Fe9ForgeSteps } from '../logic/fe9Forge'
import { fe9ForgeCost, fe9ForgedStats, fe9ForgeMaxSteps, NO_FORGE } from '../logic/fe9Forge'

const CELL = 'py-1 pr-2 sm:pr-3'
const ROWS: { key: keyof Fe9ForgeSteps; label: string; per: string }[] = [
  { key: 'mt', label: 'Mt', per: '+1' },
  { key: 'hit', label: 'Hit', per: '+5' },
  { key: 'crit', label: 'Crit', per: '+3' },
  { key: 'wt', label: 'Wt', per: '−1' },
]

/** Path of Radiance's forge for one base weapon: pick how far to push each stat and see the price. */
export function Fe9Forge({ weapon }: { weapon: Fe9Weapon }) {
  const [steps, setSteps] = useState<Fe9ForgeSteps>(NO_FORGE)
  const max = fe9ForgeMaxSteps(weapon)
  const forged = fe9ForgedStats(weapon, steps)
  const cost = fe9ForgeCost(weapon, steps)
  const step = (key: keyof Fe9ForgeSteps, by: number) =>
    setSteps((s) => ({ ...s, [key]: Math.max(0, Math.min(max[key], s[key] + by)) }))
  const button = 'h-7 w-7 rounded border border-neutral-700 bg-neutral-900 text-neutral-200 disabled:opacity-30'

  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-semibold text-neutral-100">Forge</h3>
      {weapon.forge && (
        <p className="text-neutral-400">
          At the base's forge: <span className="text-neutral-200">{weapon.forge.normal}</span> on Easy and Normal,{' '}
          <span className="text-neutral-200">{weapon.forge.hard}</span> on Hard.
        </p>
      )}
      <table className="w-full border-collapse text-xs sm:text-sm">
        <thead>
          <tr className="border-b border-neutral-700 text-left text-neutral-400">
            <th className={CELL}>Stat</th>
            <th className={CELL}>Base</th>
            <th className={CELL}>Forged</th>
            <th className={CELL}>Steps</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map(({ key, label, per }) => (
            <tr key={key} className="border-b border-neutral-800">
              <td className={`${CELL} text-neutral-100`}>{label}</td>
              <td className={CELL}>{weapon[key]}</td>
              <td className={`${CELL} ${steps[key] ? 'text-emerald-300' : ''}`}>{forged[key]}</td>
              <td className={`${CELL} whitespace-nowrap`}>
                <button className={button} onClick={() => step(key, -1)} disabled={!steps[key]} aria-label={`Less ${label}`}>
                  −
                </button>
                <span className="inline-block w-14 text-center text-neutral-300">
                  {steps[key]}/{max[key]}
                </span>
                <button className={button} onClick={() => step(key, 1)} disabled={steps[key] >= max[key]} aria-label={`More ${label}`}>
                  +
                </button>
                <span className="ml-2 text-neutral-500">{per} each</span>
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
        <li>Each stat costs more the further you push it, and more on a weapon whose stat starts low.</li>
        <li>Wt can't go below 1. Uses, rank and range stay the same as the base weapon's.</li>
        <li>You name the weapon and pick its colour. One forged weapon per base visit.</li>
      </ul>
    </div>
  )
}
