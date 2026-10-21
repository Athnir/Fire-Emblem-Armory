import { FE10_AFFINITIES, FE10_PAIR_OFFSETS, FE10_SUPPORT_ACTIONS, FE10_SUPPORT_TOTALS, fe10SupportBonus } from '../data/supports/fe10Supports'
import { TelliusSupports } from './TelliusSupports'

const CELL = 'py-1 pr-2 sm:pr-3'
const signed = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : '±0')

/** Radiant Dawn's supports: one partner at a time, the affinity table, support points, bonds and map affinity. */
export function Fe10Supports() {
  return (
    <TelliusSupports
      affinities={FE10_AFFINITIES}
      bonus={fe10SupportBonus}
      rounding="Both units get these; a half is rounded up."
      rules={
        <>
          <li>
            Each unit can have <span className="text-neutral-100">one support partner at a time</span>, and any two units can
            support. Ending a support at the base frees both units, but loses all the points the pair had built up.
          </li>
          <li>
            Support levels are C, B and A, each unlocked at the base once the pair has {FE10_SUPPORT_TOTALS.join(', ')} support
            points in total (50 a level).
          </li>
          <li>Both units get the bonus while they're within 3 tiles of each other.</li>
          <li>
            Each unit has an affinity. A pair's bonus is <span className="text-neutral-100">both affinities added together, times the support level</span>{' '}
            (C = 1, B = 2, A = 3), with <span className="text-neutral-100">a half rounded up</span> (Path of Radiance rounds down).
          </li>
        </>
      }
      extra={
        <>
          <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
            <h2 className="font-semibold text-neutral-100">Support points</h2>
            <p>
              A pair earns points for these. Some pairs build up faster than others: the game sorts every pair into one of
              five kinds, from {signed(FE10_PAIR_OFFSETS[0])} to {signed(FE10_PAIR_OFFSETS[FE10_PAIR_OFFSETS.length - 1])} points on each action.
            </p>
            <table className="w-full border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-neutral-700 text-left text-neutral-400">
                  <th className={CELL}>Action</th>
                  {FE10_PAIR_OFFSETS.map((o) => (
                    <th key={o} className={CELL}>
                      {signed(o)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {FE10_SUPPORT_ACTIONS.map((x) => (
                  <tr key={x.action} className="border-b border-neutral-800">
                    <td className={`${CELL} text-neutral-100`}>{x.action}</td>
                    {FE10_PAIR_OFFSETS.map((o) => (
                      <td key={o} className={CELL}>
                        {x.points + o}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-xs text-neutral-500">
              Points for each kind of pair, from the game's own support table. Raising a level at the base adds 1 point toward the
              next; a rescued unit doesn't get points for being next to someone.
            </p>
          </section>

          <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
            <h2 className="font-semibold text-neutral-100">Bonds and map affinity</h2>
            <ul className="list-disc space-y-1 pl-5">
              <li>
                <span className="text-neutral-100">Bonds</span> are built-in ties between certain characters, on top of any
                support. A unit next to someone it's bonded with gets +5 or +10 crit and dodge (crit avoid), whatever their
                affinities. Bonds can't be removed.
              </li>
              <li>Pairs with an A support in a Path of Radiance save you transfer start with a +5 bond.</li>
              <li>
                Every chapter has an affinity of its own. Any unit, on any side, whose affinity matches it gets{' '}
                <span className="text-neutral-100">+5 Hit and +5 Avoid</span> there, except on Hard.
              </li>
            </ul>
          </section>
        </>
      }
    />
  )
}
