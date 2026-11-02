import { useState } from 'react'
import { FE13_SUPPORTS } from '../data/fe13/fe13Supports'

const LEVELS = ['none', 'C', 'B', 'A', 'S'] as const
type Level = (typeof LEVELS)[number]
const CELL = 'py-1 pr-3'
/** "20 with no support, 30 at C, 40 at B, 50 at A, 60 at S": a step for each support level. */
const steps = (by: Record<Level, number>) => LEVELS.map((l) => (l === 'none' ? `${by[l]} with no support` : `${by[l]} at ${l}`)).join(', ')

/**
 * Awakening's supports: dual support (the bonus a unit gets from the allies beside it and its pair-up partner, by their support levels),
 * read from the game's table and the code that sums it, plus what the support level does to dual strikes, dual guards and pair-up, all
 * read in the program (scripts/build-fe13-supports.py).
 */
export function Fe13Supports() {
  const s = FE13_SUPPORTS
  const [partners, setPartners] = useState<(Level | '')[]>(['C', ...Array<Level | ''>(s.supporters - 1).fill('')])
  const [skill, setSkill] = useState(false)
  const sum = partners.reduce((n, p) => n + (p ? s.perLevel[p] : 0), 0)
  // Dual Support+ only adds to a total already above 0 (0x2199b0): with nobody beside the unit it gives nothing.
  const total = Math.min(s.max, sum + (skill && sum > 0 ? s.skill : 0))
  const [hit, avoid, crit, critAvoid] = s.rows[total]
  return (
    <section className="flex max-w-3xl flex-col gap-4 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">Dual support</h2>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          A unit gets a bonus to hit, avoid, crit and crit avoid from the allies standing next to it (up, down, left and right) and from its
          pair-up partner: up to {s.supporters}.
        </li>
        <li>
          Each of them adds to a total by its support level with the unit: {LEVELS.map((l) => `${l} ${s.perLevel[l]}`).join(', ')}. The
          Dual Support+ skill on either adds {s.skill}, once someone counts. The total stops at {s.max}.
        </li>
        <li>The bonus is the table's row for the total, as it stands (nothing is rounded).</li>
      </ul>
      <div className="flex flex-wrap items-end gap-2">
        {partners.map((p, i) => (
          <label key={i} className="flex flex-col text-xs text-neutral-400">
            {i === 0 ? 'Pair-up partner' : `Beside ${i}`}
            <select
              value={p}
              onChange={(e) => setPartners(partners.map((q, k) => (k === i ? (e.target.value as Level | '') : q)))}
              className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-sm text-neutral-200"
            >
              <option value="">nobody</option>
              {LEVELS.map((l) => (
                <option key={l} value={l}>
                  support {l}
                </option>
              ))}
            </select>
          </label>
        ))}
        <label className="flex items-center gap-1 text-neutral-300">
          <input type="checkbox" checked={skill} onChange={(e) => setSkill(e.target.checked)} />
          Dual Support+
        </label>
      </div>
      <p className="text-neutral-200">
        Total {total}: hit +{hit}, avoid +{avoid}, crit +{crit}, crit avoid +{critAvoid}
      </p>
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-neutral-700 text-left text-neutral-400">
              <th className={CELL}>Total</th>
              <th className={CELL}>Hit</th>
              <th className={CELL}>Avoid</th>
              <th className={CELL}>Crit</th>
              <th className={CELL}>Crit avoid</th>
            </tr>
          </thead>
          <tbody>
            {s.rows.map((r, i) =>
              i === 0 ? null : (
                <tr key={i} className={`border-b border-neutral-800 ${i === total ? 'bg-emerald-950' : ''}`}>
                  <td className={`${CELL} text-neutral-100`}>{i}</td>
                  {r.map((v, k) => (
                    <td key={k} className={CELL}>
                      +{v}
                    </td>
                  ))}
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
      <h2 className="font-semibold text-neutral-100">Dual strikes, dual guards and pair-up</h2>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          Dual strike chance: the two units' Skill added and divided by 4, plus {steps(s.dualStrike.perLevel)}; plus{' '}
          {s.dualStrike.skill} if either has Dual Strike+. It stays between 0 and 100.
        </li>
        <li>
          Dual guard chance: the two units' Def (or Res, against magic) added and divided by 4, plus {steps(s.dualGuard.perLevel)}; plus{' '}
          {s.dualGuard.skill} if either has Dual Guard+. It stays between 0 and 100.
        </li>
        <li>
          Paired up, the lead unit gets in each stat from Strength to Resistance: the partner's own stat divided by {s.pairUp.statStep},{' '}
          {s.pairUp.statCap} at most; where the partner's class gives that stat a pair-up bonus, the bonus and{' '}
          {steps(s.pairUp.perLevel)}; and {s.pairUp.defender} more if the lead unit has Defender. Fractions are dropped.
        </li>
      </ul>
      <p className="text-xs text-neutral-500">Who supports whom belongs to the unit, so it's in the Unit Planner.</p>
    </section>
  )
}
