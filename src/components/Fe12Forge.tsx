import { useState } from 'react'
import { fe11ForgeCost, fe11ForgeRange } from '../logic/fe11Forge'
import type { ForgeStat } from '../logic/fe11Forge'
import type { ChapterWeapon } from './ChapterWeapons'
import { useReach } from './Reach'

const CELL = 'py-1 pr-2 sm:pr-3'
/** New Mystery of the Emblem's forge moves Mt, Hit and Crit (shop::RefinePower, RefineHit, RefineCritical: no weight to forge). */
const ROWS: { key: ForgeStat; label: string }[] = [
  { key: 'mt', label: 'Mt' },
  { key: 'hit', label: 'Hit' },
  { key: 'crit', label: 'Crit' },
]
const FORGEABLE = new Set(['Sword', 'Lance', 'Axe', 'Bow', 'Tome'])

/** New Mystery of the Emblem's forge for one weapon: Shadow Dragon's limits and price (src/logic/fe11Forge.ts, the same code in
 * FE12's program, arm9 0x2068c70), less weight. Under the spoiler block it says nothing before the chapter the forge opens in. */
export function Fe12Forge({ weapon: w, opensAt }: { weapon: ChapterWeapon; opensAt: string }) {
  const [change, setChange] = useState<Record<ForgeStat, number>>({ mt: 0, hit: 0, crit: 0, wt: 0 })
  const reach = useReach()
  if (!w.worth || !FORGEABLE.has(w.category) || w.rules?.includes("Can't be forged") || !reach.has(opensAt)) return null
  const price = w.worth
  const base: Record<ForgeStat, number> = { mt: w.mt ?? 0, hit: w.hit ?? 0, crit: w.crit ?? 0, wt: 0 }
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
        <li>Each stat moves up to a set amount either way: Mt 10 (0 to 30), Hit 50 (0 to 200), Crit 30 (0 to 50).</li>
        <li>
          Each stat costs the weapon's price ({price.toLocaleString()}G) times 1, 3, 6, 10... for its 1st, 2nd, 3rd, 4th... step (a step
          is 1 Mt, 5 Hit or 3 Crit; a part step costs its share of the next). The forge charges half of all that plus half the price.
        </li>
        <li>
          Forging is done at the battle preparations' armory, from Chapter 1; the armories on the maps don't forge. At most 50 forged
          weapons can exist at once.
        </li>
      </ul>
      <div className="rounded border border-amber-900 bg-amber-950/30 p-2">
        <p className="text-amber-300">Not yet confirmed in-game</p>
        <p className="text-amber-200/80">One weapon per chapter: the option greys out after a forge, but where it's turned back on isn't traced.</p>
      </div>
    </div>
  )
}
