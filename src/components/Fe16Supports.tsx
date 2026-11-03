import { FE16_SUPPORTS } from '../data/fe16/fe16Supports'

/**
 * Three Houses' supports: what one ally gives by its support level with the attacker, read from the game's support tables and
 * program (scripts/build-fe16-supports.py). Who supports whom belongs to the units, so it's the Unit Planner's.
 */
export function Fe16Supports() {
  const s = FE16_SUPPORTS
  const plus = Object.entries(s.rankLevels)
    .filter(([rank, level]) => rank !== level)
    .map(([rank, level]) => `${rank} as ${level}`)
  const cell = 'py-1 pr-4 text-right text-neutral-100'
  return (
    <section className="flex max-w-3xl flex-col gap-4 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">Linked Attacks</h2>
      <p>Each ally that joins an attack adds, by its support level with the attacker:</p>
      <table className="border-collapse text-xs sm:text-sm">
        <thead>
          <tr className="border-b border-neutral-800 text-neutral-400">
            <th className="py-1 pr-4 text-left font-normal">Support level</th>
            <th className="py-1 pr-4 text-right font-normal">Hit</th>
            <th className="py-1 pr-4 text-right font-normal">Avoid</th>
            <th className="py-1 pr-4 text-right font-normal">Attack (certain pairs)</th>
          </tr>
        </thead>
        <tbody>
          {s.levels.map((level, k) => (
            <tr key={level} className="border-b border-neutral-800">
              <td className="py-1 pr-4">{level}</td>
              <td className={cell}>+{s.linked.hit[k]}</td>
              <td className={cell}>+{s.linked.avoid[k]}</td>
              <td className={cell}>+{s.linked.pairAttack[k]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          'None' is a pair that can support but hasn't unlocked a rank yet; a pair that can't support adds nothing. The + ranks count as
          the rank below them ({plus.join(', ')}).
        </li>
        <li>
          Attack comes only from the {s.linked.pairs} pairs the game's support table names; every other pair gives hit and avoid alone.
        </li>
        <li>Each ally's bonus is added on top of the others': up to three allies and the attacker's adjutant join one attack.</li>
      </ul>
      <h2 className="font-semibold text-neutral-100">Gambit Boosts</h2>
      <p>When the attack is a gambit, each ally that joins adds instead:</p>
      <table className="border-collapse text-xs sm:text-sm">
        <thead>
          <tr className="border-b border-neutral-800 text-neutral-400">
            <th className="py-1 pr-4 text-left font-normal">Support level</th>
            <th className="py-1 pr-4 text-right font-normal">Attack</th>
            <th className="py-1 pr-4 text-right font-normal">Hit</th>
          </tr>
        </thead>
        <tbody>
          {s.levels.map((level, k) => (
            <tr key={level} className="border-b border-neutral-800">
              <td className="py-1 pr-4">{level}</td>
              <td className={cell}>+{s.gambit.attack[k]}</td>
              <td className={cell}>+{s.gambit.hit[k]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-neutral-500">
        Not yet confirmed: which allies join (allies that could attack the target from where they stand, earlier-deployed ones first).
        Who supports whom belongs to the units, so it's in the Unit Planner.
      </p>
    </section>
  )
}
