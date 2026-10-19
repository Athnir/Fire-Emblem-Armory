import { useState } from 'react'
import { FE9_AFFINITIES, FE9_LEVELS, fe9SupportBonus } from '../data/supports/fe9Supports'

const plus = (n: number) => (n ? `+${n}` : '—')
const half = (n: number) => (n ? `+${n}` : '—')
const CELL = 'py-1 pr-2 sm:pr-3'

/** Path of Radiance's supports: the affinity table, how it adds up and rounds, and a pair calculator. */
export function Fe9Supports() {
  const [a, setA] = useState('Fire')
  const [b, setB] = useState('Earth')
  const first = FE9_AFFINITIES.find((x) => x.name === a)!
  const second = FE9_AFFINITIES.find((x) => x.name === b)!
  const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">How supports work</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Both units get the bonus while they're within 3 tiles of each other.</li>
          <li>Support levels are C, B and A. A unit can hold up to five support levels in total across all its partners.</li>
          <li>
            Each unit has an affinity. A pair's bonus is <span className="text-neutral-100">both affinities added together, times the support level</span>{' '}
            (C = 1, B = 2, A = 3), <span className="text-neutral-100">rounded down</span>. So half points only count once they add up to a whole one.
          </li>
          <li>Bonuses from different partners in range add together.</li>
          <li>
            Some pairs also have a hidden bonus while standing next to each other: +5 or +10 crit for both, or one unit
            becoming immune to enemy crits.
          </li>
        </ul>
        <table className="w-full border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-neutral-700 text-left text-neutral-400">
              <th className={CELL}>Affinity</th>
              <th className={CELL}>Atk</th>
              <th className={CELL}>Def</th>
              <th className={CELL}>Hit</th>
              <th className={CELL}>Avo</th>
            </tr>
          </thead>
          <tbody>
            {FE9_AFFINITIES.map((x) => (
              <tr key={x.name} className="border-b border-neutral-800">
                <td className={`${CELL} text-neutral-100`}>{x.name}</td>
                <td className={CELL}>{half(x.atk)}</td>
                <td className={CELL}>{half(x.def)}</td>
                <td className={CELL}>{half(x.hit)}</td>
                <td className={CELL}>{half(x.avoid)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-neutral-500">Per support level, for each unit's own affinity.</p>
      </section>

      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">A pair's bonus</h2>
        <div className="flex flex-wrap items-center gap-2">
          <select value={a} onChange={(e) => setA(e.target.value)} className={select} aria-label="First unit's affinity">
            {FE9_AFFINITIES.map((x) => (
              <option key={x.name}>{x.name}</option>
            ))}
          </select>
          <span className="text-neutral-500">and</span>
          <select value={b} onChange={(e) => setB(e.target.value)} className={select} aria-label="Second unit's affinity">
            {FE9_AFFINITIES.map((x) => (
              <option key={x.name}>{x.name}</option>
            ))}
          </select>
        </div>
        <table className="w-full border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-neutral-700 text-left text-neutral-400">
              <th className={CELL}>Level</th>
              <th className={CELL}>Atk</th>
              <th className={CELL}>Def</th>
              <th className={CELL}>Hit</th>
              <th className={CELL}>Avo</th>
            </tr>
          </thead>
          <tbody>
            {FE9_LEVELS.map((level, i) => {
              const r = fe9SupportBonus(first, second, i + 1)
              return (
                <tr key={level} className="border-b border-neutral-800">
                  <td className={`${CELL} text-neutral-100`}>{level}</td>
                  <td className={CELL}>{plus(r.atk)}</td>
                  <td className={CELL}>{plus(r.def)}</td>
                  <td className={CELL}>{plus(r.hit)}</td>
                  <td className={CELL}>{plus(r.avoid)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="text-xs text-neutral-500">Both units get these, already rounded down.</p>
      </section>
    </div>
  )
}
