import { useState } from 'react'
import { FE4_BONUSES } from '../data/fe4/fe4Bonuses'

const CELL = 'py-1 pr-2 sm:pr-3'
const plus = (n: number) => (n ? `+${n}` : '—')

/**
 * Genealogy of the Holy War has no support levels. What stands in for them is the bonus a unit gets from the units around it
 * (leadership, Charisma, a lover) and from the weapon triangle, all read from the game's battle code (scripts/build-fe4-bonuses.py).
 */
export function Fe4Supports() {
  const b = FE4_BONUSES
  const [stars, setStars] = useState(0)
  const [charisma, setCharisma] = useState(0)
  const [lover, setLover] = useState(false)
  const [triangle, setTriangle] = useState<'none' | 'advantage' | 'disadvantage'>('none')
  const near = b.leadership[stars] + charisma * b.charisma + (lover ? b.lover : 0)
  const own = near + (triangle === 'advantage' ? b.triangle : 0)
  const foe = triangle === 'disadvantage' ? b.triangle : 0
  const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">How the bonuses work</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>There are no support levels. Each bonus below is added to <span className="text-neutral-100">both hit and avoid</span>.</li>
          <li>
            Units of the same army within {b.reach} tiles (counting steps, |x| + |y|) give a unit:
            <ul className="list-[circle] pl-5">
              <li>{plus(b.charisma)} for each one with Charisma (two Charisma units in range give {plus(2 * b.charisma)});</li>
              <li>{plus(b.lover)} if one is its lover;</li>
              <li>its commander's leadership, by stars (table).</li>
            </ul>
          </li>
          <li>The lord (Sigurd, then Seliph) gets their own leadership bonus wherever they are.</li>
          <li>
            Weapon triangle: the side whose weapon has the advantage gets {plus(b.triangle)} to hit and avoid; the other side gets nothing,
            so the loser's hit against it falls by {b.triangle} too.
          </li>
          <li>All of these add together; nothing is rounded.</li>
        </ul>
        <table className="w-full border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-neutral-700 text-left text-neutral-400">
              <th className={CELL}>Leadership stars</th>
              {b.leadership.map((_, i) => (
                <th key={i} className={CELL}>
                  {i}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-neutral-800">
              <td className={`${CELL} text-neutral-100`}>Hit and avoid</td>
              {b.leadership.map((v, i) => (
                <td key={i} className={CELL}>
                  {plus(v)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
        <table className="w-full border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="border-b border-neutral-700 text-left text-neutral-400">
              <th className={CELL}>Weapon</th>
              <th className={CELL}>Beats</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(b.beats).map(([w, list]) => (
              <tr key={w} className="border-b border-neutral-800">
                <td className={`${CELL} text-neutral-100`}>{w}</td>
                <td className={CELL}>{list.join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-xs text-neutral-500">Read in the game's battle code; bows and staves are outside the triangle.</p>
      </section>

      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">A unit's bonus</h2>
        <label className="flex items-center gap-2">
          Commander's leadership within {b.reach} tiles
          <select value={stars} onChange={(e) => setStars(Number(e.target.value))} className={select}>
            {b.leadership.map((_, i) => (
              <option key={i} value={i}>
                {i} {i === 1 ? 'star' : 'stars'}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          Charisma units within {b.reach} tiles
          <select value={charisma} onChange={(e) => setCharisma(Number(e.target.value))} className={select}>
            {[0, 1, 2, 3].map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={lover} onChange={(e) => setLover(e.target.checked)} />
          Lover within {b.reach} tiles
        </label>
        <label className="flex items-center gap-2">
          Weapon triangle
          <select value={triangle} onChange={(e) => setTriangle(e.target.value as typeof triangle)} className={select}>
            <option value="none">Neutral</option>
            <option value="advantage">Advantage</option>
            <option value="disadvantage">Disadvantage</option>
          </select>
        </label>
        <p className="text-3xl font-bold text-emerald-400">
          +{own} <span className="text-base font-normal text-neutral-400">hit and avoid</span>
        </p>
        {foe > 0 && <p className="text-amber-300">The foe gets {plus(foe)} hit and avoid from the triangle.</p>}
      </section>
    </div>
  )
}
