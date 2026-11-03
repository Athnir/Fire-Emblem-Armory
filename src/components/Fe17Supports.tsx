import { FE17_SUPPORTS } from '../data/fe17/fe17Supports'

/**
 * Engage's supports: what an adjacent supporter gives by its own support type and the pair's level, read from the game's support table
 * and program (scripts/build-fe17-supports.py). Who has which type, and who supports whom, belong to the units: the Unit Planner's.
 */
export function Fe17Supports() {
  const cell = 'py-1 pr-4 text-right text-neutral-100'
  const sign = (n: number) => (n ? `+${n}` : '0')
  return (
    <section className="flex max-w-3xl flex-col gap-4 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">Support bonuses</h2>
      <p>
        Each ally standing on one of the four tiles beside a unit, with a support with it, adds the bonuses of the ally's own support type
        at their support level:
      </p>
      {FE17_SUPPORTS.map((t) => (
        <div key={t.type}>
          <h3 className="mb-1 text-neutral-100">{t.type}</h3>
          <table className="border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-neutral-800 text-neutral-400">
                <th className="py-1 pr-4 text-left font-normal">Level</th>
                <th className="py-1 pr-4 text-right font-normal">Hit</th>
                <th className="py-1 pr-4 text-right font-normal">Crit</th>
                <th className="py-1 pr-4 text-right font-normal">Avoid</th>
                <th className="py-1 pr-4 text-right font-normal">Dodge</th>
              </tr>
            </thead>
            <tbody>
              {t.levels.map((l) => (
                <tr key={l.level} className="border-b border-neutral-800">
                  <td className="py-1 pr-4">{l.level === 'Ring' ? 'Ring (pact ring)' : l.level}</td>
                  <td className={cell}>{sign(l.hit)}</td>
                  <td className={cell}>{sign(l.crit)}</td>
                  <td className={cell}>{sign(l.avoid)}</td>
                  <td className={cell}>{sign(l.dodge)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <ul className="list-disc space-y-1 pl-5">
        <li>Only the four tiles beside the unit count, so up to four allies add their bonuses, each its own, summed.</li>
        <li>An ally without a support with the unit (no rank yet) adds nothing.</li>
        <li>
          The types are the game's own, each named here by what it raises most: most playable characters have one of the last five, a few
          and every other unit the Default one. Who has which belongs to the units, so it's in the Unit Planner.
        </li>
      </ul>
    </section>
  )
}
