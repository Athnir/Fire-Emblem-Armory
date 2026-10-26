import { useState } from 'react'
import { FE6_SUPPORTS } from '../data/fe6/fe6Supports'
import { fe6SupportBonus } from '../logic/fe6Supports'
import type { Fe6Partner } from '../logic/fe6Supports'

const CELL = 'py-1 pr-2 sm:pr-3'
const STATS = [
  ['atk', 'Atk'],
  ['def', 'Def'],
  ['hit', 'Hit'],
  ['avoid', 'Avo'],
  ['crit', 'Crit'],
  ['dodge', 'Ddg'],
] as const
const LEVELS = ['C', 'B', 'A'] as const
const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'
const plus = (n: number) => (n ? `+${n}` : '—')
const half = (n: number) => (n ? `+${n / 2}` : '—')

/** The Binding Blade's supports: how the bonus is worked out (read from the battle code), the affinity table and a calculator. */
export function Fe6Supports() {
  const s = FE6_SUPPORTS
  const names = s.affinities.map((a) => a.name)
  const [own, setOwn] = useState<string>(names[0])
  const [partners, setPartners] = useState<Fe6Partner[]>([{ affinity: names[1], level: 1 }])
  const total = fe6SupportBonus(own, partners)
  const used = partners.reduce((n, p) => n + p.level, 0)

  function update(i: number, p: Partial<Fe6Partner>) {
    setPartners((list) => list.map((x, k) => (k === i ? { ...x, ...p } : x)))
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">How supports work</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>A partner counts while it's within {s.reach} tiles (counting steps) and on the map.</li>
          <li>
            Support levels are C, B and A ({s.levels.C}, {s.levels.B} and {s.levels.A} support points). A support only grows while both
            units hold {s.maxLevels - 1} levels or fewer in total, so {s.maxLevels} is the most a unit can have.
          </li>
          <li>
            For each partner in range, the unit adds <span className="text-neutral-100">its own affinity's row and its partner's</span>,
            each times the support level (C = 1, B = 2, A = 3).
          </li>
          <li>
            The totals over every partner in range are <span className="text-neutral-100">halved once, rounded down</span>. So half points
            from different partners can add up to a whole one.
          </li>
          <li>The partner works out its own bonus the same way, from its own partners.</li>
        </ul>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-neutral-700 text-left text-neutral-400">
                <th className={CELL}>Affinity, per level</th>
                {STATS.map(([, label]) => (
                  <th key={label} className={CELL}>
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {s.affinities.map((a) => (
                <tr key={a.name} className="border-b border-neutral-800">
                  <td className={`${CELL} text-neutral-100`}>{a.name}</td>
                  {STATS.map(([k]) => (
                    <td key={k} className={CELL}>
                      {half(a[k])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-neutral-500">Half the game's numbers, since the total is halved; fractions round down only at the end.</p>
      </section>

      <section className="flex h-fit flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">A unit's bonus</h2>
        <label className="flex flex-wrap items-center gap-2">
          Unit's affinity
          <select value={own} onChange={(e) => setOwn(e.target.value)} className={select}>
            {names.map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <p className="text-neutral-400">Partners within {s.reach} tiles:</p>
        {partners.map((p, i) => (
          <div key={i} className="flex flex-wrap items-center gap-2">
            <select value={p.affinity} onChange={(e) => update(i, { affinity: e.target.value })} className={select} aria-label="Partner's affinity">
              {names.map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
            <select value={p.level} onChange={(e) => update(i, { level: Number(e.target.value) })} className={select} aria-label="Support level">
              {LEVELS.map((l, k) => (
                <option key={l} value={k + 1}>
                  {l}
                </option>
              ))}
            </select>
            <button type="button" onClick={() => setPartners((list) => list.filter((_, k) => k !== i))} className="text-neutral-500 hover:text-neutral-300">
              Remove
            </button>
          </div>
        ))}
        {used < s.maxLevels && (
          <button
            type="button"
            onClick={() => setPartners((list) => [...list, { affinity: names[0], level: 1 }])}
            className="w-fit rounded border border-neutral-700 px-2 py-1 hover:bg-neutral-800"
          >
            Add a partner
          </button>
        )}
        {used > s.maxLevels && <p className="text-amber-300">That's more than {s.maxLevels} support levels; the game stops at {s.maxLevels}.</p>}
        <table className="w-full border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-neutral-700 text-left text-neutral-400">
              {STATS.map(([, label]) => (
                <th key={label} className={CELL}>
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {STATS.map(([k]) => (
                <td key={k} className={`${CELL} text-emerald-300`}>
                  {plus(total[k])}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  )
}
