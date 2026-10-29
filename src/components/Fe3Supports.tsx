import { FE3_SUPPORTS } from '../data/fe3/fe3Supports'

/** Mystery of the Emblem's supports: no levels, a fixed bonus per partner in reach, and the Geosphere's (read from the support code). */
export function Fe3Supports() {
  const s = FE3_SUPPORTS
  return (
    <section className="flex max-w-2xl flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">How supports work</h2>
      <ul className="list-disc space-y-1 pl-5">
        <li>There are no support levels or conversations: a support is there from the start.</li>
        <li>
          A partner counts while it's on the map and within {s.reach} tiles (counting steps, whatever the terrain). Each partner in reach
          adds its bonus, which is <span className="text-neutral-100">+{s.bonuses.join(' or +')}</span> (most pairs give the higher one).
        </li>
        <li>
          An ally carrying the Geosphere gives <span className="text-neutral-100">+{s.geosphere}</span> to every unit of its side within{' '}
          {s.reach} tiles, on top of any support.
        </li>
        <li>
          The bonus goes to <span className="text-neutral-100">hit, avoid, crit and crit avoid</span> alike. Bonuses from several partners
          add up, with nothing rounded or capped.
        </li>
        <li>
          A support can go one way: of the game's {s.entries} pairings, {s.oneWay} give a bonus to one side only.
        </li>
        <li>There's no weapon triangle to add it to: only terrain's avoid.</li>
      </ul>
      <p className="text-xs text-neutral-500">Who supports whom belongs to the unit, so it's in the Unit Planner.</p>
    </section>
  )
}
