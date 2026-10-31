import { useState } from 'react'
import { fe11ForgeCost, fe11ForgeRange } from '../logic/fe11Forge'
import type { ForgeStat } from '../logic/fe11Forge'
import type { ChapterWeapon } from './ChapterWeapons'

const CELL = 'py-1 pr-2 sm:pr-3'
const ROWS: { key: ForgeStat; label: string }[] = [
  { key: 'mt', label: 'Mt' },
  { key: 'hit', label: 'Hit' },
  { key: 'crit', label: 'Crit' },
  { key: 'wt', label: 'Wt' },
]
const FORGEABLE = new Set(['Sword', 'Lance', 'Axe', 'Bow', 'Tome'])

/** Shadow Dragon's forge for one weapon: set each stat and see the cost (src/logic/fe11Forge.ts). */
export function Fe11Forge({ weapon: w }: { weapon: ChapterWeapon }) {
  const [change, setChange] = useState<Record<ForgeStat, number>>({ mt: 0, hit: 0, crit: 0, wt: 0 })
  if (!w.worth || !FORGEABLE.has(w.category)) return null
  const price = w.worth
  const base: Record<ForgeStat, number> = { mt: w.mt ?? 0, hit: w.hit ?? 0, crit: w.crit ?? 0, wt: w.wt ?? 0 }
  const set = (key: ForgeStat, by: number) =>
    setChange((c) => {
      const [lo, hi] = fe11ForgeRange(key, base[key])
      return { ...c, [key]: Math.max(lo, Math.min(hi, base[key] + c[key] + by)) - base[key] }
    })
  const cost = fe11ForgeCost(price, change)
  const button = 'h-7 w-7 rounded border border-neutral-700 bg-neutral-900 text-neutral-200 disabled:opacity-30'
  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-semibold text-neutral-100">Forge</h3>
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
          {ROWS.map(({ key, label }) => {
            const [lo, hi] = fe11ForgeRange(key, base[key])
            const now = base[key] + change[key]
            return (
              <tr key={key} className="border-b border-neutral-800">
                <td className={`${CELL} text-neutral-100`}>{label}</td>
                <td className={CELL}>{base[key]}</td>
                <td className={`${CELL} ${change[key] ? 'text-emerald-300' : ''}`}>{now}</td>
                <td className={`${CELL} whitespace-nowrap`}>
                  <button className={button} onClick={() => set(key, -1)} disabled={now <= lo} aria-label={`Less ${label}`}>
                    −
                  </button>
                  <span className="inline-block w-12 text-center text-neutral-300">
                    {change[key] > 0 ? `+${change[key]}` : change[key]}
                  </span>
                  <button className={button} onClick={() => set(key, 1)} disabled={now >= hi} aria-label={`More ${label}`}>
                    +
                  </button>
                  <span className="ml-2 text-neutral-500">
                    {lo}–{hi}
                  </span>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="text-neutral-300">
        Cost: <span className="text-lg text-amber-200">{cost.toLocaleString()}G</span>
      </p>
      <ul className="list-disc space-y-1 pl-5 text-neutral-400">
        <li>Mt rises by up to 10 (to 30 at most), Hit by up to 50 (200), Crit by up to 30 (50); Wt moves up to 10 either way (1 to 30).</li>
        <li>
          Each stat costs the weapon's price ({price.toLocaleString()}G) times 1, 3, 6, 10... for its 1st, 2nd, 3rd, 4th... step (a step
          is 1 Mt, 5 Hit, 3 Crit or 1 Wt; a part step costs its share of the next). The forge charges half of all that plus half the price.
        </li>
        <li className="text-neutral-500">
          Serenes Forest: forging opens in Chapter 4 at the battle preparations' armory, one weapon per chapter (not checked in the game's
          code).
        </li>
      </ul>
    </div>
  )
}
