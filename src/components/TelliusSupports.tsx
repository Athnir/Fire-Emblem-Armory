import { useState } from 'react'
import type { ReactNode } from 'react'
import type { Affinity } from '../data/supports/fe9Supports'

const plus = (n: number) => (n ? `+${n}` : '—')
const CELL = 'py-1 pr-2 sm:pr-3'
const LEVELS = ['C', 'B', 'A'] as const

/**
 * Path of Radiance's and Radiant Dawn's supports: how they work, the affinity table, a pair calculator,
 * and whatever else the game adds (Radiant Dawn's support points, bonds and map affinity).
 */
export function TelliusSupports({
  rules,
  affinities,
  bonus,
  rounding,
  extra,
}: {
  /** The rules, as list items. */
  rules: ReactNode
  affinities: Affinity[]
  /** A pair's bonus at a support level (1-3), already rounded the game's way. */
  bonus: (a: Affinity, b: Affinity, level: number) => Record<'atk' | 'def' | 'hit' | 'avoid', number>
  /** Under the pair table: how the numbers were rounded. */
  rounding: string
  /** More sections, after the pair calculator. */
  extra?: ReactNode
}) {
  const [a, setA] = useState('Fire')
  const [b, setB] = useState('Earth')
  const first = affinities.find((x) => x.name === a)!
  const second = affinities.find((x) => x.name === b)!
  const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'
  const head = (first: string) => (
    <thead>
      <tr className="border-b border-neutral-700 text-left text-neutral-400">
        <th className={CELL}>{first}</th>
        <th className={CELL}>Atk</th>
        <th className={CELL}>Def</th>
        <th className={CELL}>Hit</th>
        <th className={CELL}>Avo</th>
      </tr>
    </thead>
  )

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">How supports work</h2>
        <ul className="list-disc space-y-1 pl-5">{rules}</ul>
        <table className="w-full border-collapse text-xs sm:text-sm">
          {head('Affinity')}
          <tbody>
            {affinities.map((x) => (
              <tr key={x.name} className="border-b border-neutral-800">
                <td className={`${CELL} text-neutral-100`}>{x.name}</td>
                <td className={CELL}>{plus(x.atk)}</td>
                <td className={CELL}>{plus(x.def)}</td>
                <td className={CELL}>{plus(x.hit)}</td>
                <td className={CELL}>{plus(x.avoid)}</td>
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
            {affinities.map((x) => (
              <option key={x.name}>{x.name}</option>
            ))}
          </select>
          <span className="text-neutral-500">and</span>
          <select value={b} onChange={(e) => setB(e.target.value)} className={select} aria-label="Second unit's affinity">
            {affinities.map((x) => (
              <option key={x.name}>{x.name}</option>
            ))}
          </select>
        </div>
        <table className="w-full border-collapse text-xs sm:text-sm">
          {head('Level')}
          <tbody>
            {LEVELS.map((level, i) => {
              const r = bonus(first, second, i + 1)
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
        <p className="text-xs text-neutral-500">{rounding}</p>
      </section>
      {extra}
    </div>
  )
}
