import { FE15_SUPPORT_POINTS } from '../data/fe15/fe15Supports'

/**
 * Echoes' supports: each pair's bonus is the pair's own (who supports whom, and with what, is the Unit Planner's), so this says only
 * how a pair earns support points, read from the game's own tuning values (params.bin), and how the bonuses apply.
 */
export function Fe15Supports() {
  const p = FE15_SUPPORT_POINTS
  return (
    <section className="flex max-w-3xl flex-col gap-4 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">Support points</h2>
      <p>A pair earns points towards its next support conversation in battle (the game's tuning values, params.bin):</p>
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
        <li>A unit gets the bonus while its partner is within 3 tiles; a pair's ranks don't stack (only the current rank's bonus applies).</li>
      </ul>
      <p className="text-xs text-neutral-500">
        The bonuses' range and stacking are from Serenes Forest; not yet checked in the game's code. Who supports whom, and each pair's
        bonus, belong to the units, so they're in the Unit Planner.
      </p>
    </section>
  )
}
