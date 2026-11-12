import { FE12_SUPPORTS } from '../data/fe12/fe12Supports'

const LEVELS = ['C', 'B', 'A'] as const
const CELL = 'py-1 pr-3'

/** New Mystery of the Emblem's supports: what each level adds in battle, who counts and how it adds up, read in the battle code
 * (scripts/build-fe12-supports.py). */
export function Fe12Supports() {
  const s = FE12_SUPPORTS
  return (
    <section className="flex max-w-2xl flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">How supports work</h2>
      <table className="w-fit text-left">
        <thead className="text-xs text-neutral-500">
          <tr>
            <th className={CELL}>Level</th>
            <th className={CELL}>Hit</th>
            <th className={CELL}>Avoid</th>
            <th className={CELL}>Crit</th>
            <th className={CELL}>Crit avoid</th>
          </tr>
        </thead>
        <tbody>
          {LEVELS.map((lv) => (
            <tr key={lv} className="border-t border-neutral-800">
              <td className={CELL}>{lv}</td>
              <td className={CELL}>+{s.levels[lv].hit}</td>
              <td className={CELL}>+{s.levels[lv].avoid}</td>
              <td className={CELL}>+{s.levels[lv].crit}</td>
              <td className={CELL}>+{s.levels[lv].critAvoid}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          A unit has up to {s.slots} partners, and a support goes one way: the unit gets the bonus from a partner on its own list, by
          the level its points with that partner have reached.
        </li>
        <li>
          A partner counts while it's in the unit's army and within {s.reach} tiles (counting steps, whatever the terrain) of the tile
          the unit fights from. Every partner in reach adds its level's bonus: several add up.
        </li>
        <li>
          Every ally within {s.reach} tiles carrying the Geosphere adds <span className="text-neutral-100">+{s.geosphere} crit</span>, on
          top of any support; several stack.
        </li>
        <li>None of it applies in the arena, and the foe's army gets none of it.</li>
        <li>Displayed hit and crit are held between 0 and 100 after everything is added.</li>
      </ul>
      <p className="text-xs text-neutral-500">Who supports whom belongs to the unit, so it's in the Unit Planner.</p>
    </section>
  )
}
