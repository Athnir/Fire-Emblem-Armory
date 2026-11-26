import { FE15_SUPPORT_POINTS } from '../data/fe15/fe15Supports'

const NUMBER_WORDS: Record<number, string> = { 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six' }

/**
 * Echoes' supports: each pair's bonus is the pair's own (who supports whom, and with what, is the Roster's), so this says only
 * how a pair earns support points, read from the game's own tuning values (params.bin), and how the bonuses apply, read from the
 * program (0x3111b0: scripts/build-fe15-supports.py).
 */
export function Fe15Supports() {
  const p = FE15_SUPPORT_POINTS
  return (
    <section className="flex max-w-3xl flex-col gap-4 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">Support points</h2>
      <p>A pair earns points towards its next support conversation in battle:</p>
      <table className="border-collapse text-xs sm:text-sm">
        <tbody>
          <tr className="border-b border-neutral-800">
            <td className="py-1 pr-4">Both deployed in the battle</td>
            <td className="py-1 text-neutral-100">+{p.deployed}</td>
          </tr>
          {p.distance.map((v, i) => (
            <tr key={i} className="border-b border-neutral-800">
              <td className="py-1 pr-4">
                Fighting with the partner {i + 1} tile{i ? 's' : ''} away
              </td>
              <td className="py-1 text-neutral-100">{v ? `+${v}` : 'nothing'}</td>
            </tr>
          ))}
          <tr className="border-b border-neutral-800">
            <td className="py-1 pr-4">Using a staff (white magic) on the partner</td>
            <td className="py-1 text-neutral-100">+{p.staff}</td>
          </tr>
          <tr>
            <td className="py-1 pr-4">The most a pair earns in one battle</td>
            <td className="py-1 text-neutral-100">{p.perBattle}</td>
          </tr>
        </tbody>
      </table>
      <h2 className="font-semibold text-neutral-100">Support bonuses</h2>
      <ul className="list-disc space-y-1 pl-5">
        <li>Each pair's bonus (to hit, crit, avoid and crit avoid) is that pair's own, by rank C, B and A; some pairs have one from the start.</li>
        <li>
          A unit gets a partner's bonus while that partner, in its own army, stands 1 to {p.reach} tiles (counted in steps) from the tile it
          fights from, attacking or defending (0x3111b0). Foes' pairs count too.
        </li>
        <li>Only the pair's current rank counts: each rank's row is the whole bonus at that rank, so ranks don't stack.</li>
        <li>
          Several partners in reach add up, with no cap; the forecast shows the {NUMBER_WORDS[p.forecast] ?? p.forecast} that give the
          most.
        </li>
      </ul>
      <p className="text-xs text-neutral-500">
        Who supports whom, and each pair's bonus, belong to the units, so they're in the Roster's Supports tab.
      </p>
    </section>
  )
}
