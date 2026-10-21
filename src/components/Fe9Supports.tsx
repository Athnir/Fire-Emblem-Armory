import { FE9_AFFINITIES, fe9SupportBonus } from '../data/supports/fe9Supports'
import { TelliusSupports } from './TelliusSupports'

/** Path of Radiance's supports: the affinity table, how it adds up and rounds, and a pair calculator. */
export function Fe9Supports() {
  return (
    <TelliusSupports
      affinities={FE9_AFFINITIES}
      bonus={fe9SupportBonus}
      rounding="Both units get these, already rounded down."
      rules={
        <>
          <li>Both units get the bonus while they're within 3 tiles of each other.</li>
          <li>Support levels are C, B and A. A unit can hold up to five support levels in total across all its partners.</li>
          <li>
            Each unit has an affinity. A pair's bonus is <span className="text-neutral-100">both affinities added together, times the support level</span>{' '}
            (C = 1, B = 2, A = 3), <span className="text-neutral-100">rounded down</span>. So half points only count once they add up to a whole one.
          </li>
          <li>Bonuses from different partners in range add together.</li>
          <li>
            Some pairs also have a hidden bonus while standing next to each other: +5 or +10 crit for both, or one unit
            becoming immune to enemy crits.
          </li>
        </>
      }
    />
  )
}
