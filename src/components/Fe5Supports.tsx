import { FE5_SUPPORTS } from '../data/fe5/fe5Supports'

/** Thracia 776's supports: no levels, one fixed bonus per partner in range (read from the battle code and the supports table). */
export function Fe5Supports() {
  const s = FE5_SUPPORTS
  return (
    <section className="flex max-w-2xl flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">How supports work</h2>
      <ul className="list-disc space-y-1 pl-5">
        <li>There are no support levels or conversations: a support is there from the start.</li>
        <li>
          A partner counts while it's alive, on the map and within {s.reach} tiles (counting steps). Each partner in range adds its bonus,
          which is <span className="text-neutral-100">+{s.bonuses.join(' or +')}</span> ({s.bonuses.length > 1 ? 'a few pairs give the higher one' : 'every pair'}).
        </li>
        <li>
          The bonus goes to <span className="text-neutral-100">hit, avoid, crit and crit avoid</span> alike. Bonuses from several partners
          add up, with nothing rounded or capped.
        </li>
        <li>
          A support can go one way: of the game's {s.entries} pairings, {s.oneWay} give a bonus to one side only.
        </li>
        <li>It adds to the weapon triangle, leadership, Charm and terrain bonuses.</li>
      </ul>
      <p className="text-xs text-neutral-500">Who supports whom belongs to the unit, so it's in the Unit Planner.</p>
    </section>
  )
}
