import { useMemo, useState } from 'react'
import {
  FATES_CLASS_PAIR_UP,
  FATES_PAIR_UP,
  FATES_PAIR_UP_AVATAR,
  FATES_TAG_TEAM,
  FATES_TAG_TEAM_AVATAR,
} from '../data/supports/fatesSupports'
import type { CombatBonus, StatBonus } from '../data/supports/types'

const AVATAR = 'Corrin (Avatar)'
const BOONS = ['Robust', 'Strong', 'Clever', 'Deft', 'Quick', 'Lucky', 'Sturdy', 'Calm']
const BANES = ['Sickly', 'Weak', 'Dull', 'Clumsy', 'Slow', 'Unlucky', 'Fragile', 'Excitable']
/** A boon and a bane can't hit the same stat. */
const SAME_STAT: Record<string, string> = {
  Robust: 'Sickly', Strong: 'Weak', Clever: 'Dull', Deft: 'Clumsy', Quick: 'Slow', Lucky: 'Unlucky', Sturdy: 'Fragile', Calm: 'Excitable',
}
const TAG_KEYS: [keyof CombatBonus, string][] = [['hit', 'Hit'], ['avoid', 'Avo'], ['crit', 'Crit'], ['dodge', 'Ddg']]
const STAT_KEYS: [keyof StatBonus, string][] = [
  ['str', 'Str'], ['mag', 'Mag'], ['skl', 'Skl'], ['spd', 'Spd'], ['lck', 'Lck'], ['def', 'Def'], ['res', 'Res'], ['mov', 'Mov'],
]
const CELL = 'py-1 pr-2 sm:pr-3'

function add<T extends Record<string, number | undefined>>(a: T, b: T): T {
  const out = { ...a }
  for (const [k, v] of Object.entries(b)) (out as Record<string, number>)[k] = ((out[k] as number | undefined) ?? 0) + (v ?? 0)
  return out
}

/** Running totals: the bonuses build up level by level. */
function cumulative<T extends Record<string, number | undefined>>(levels: T[]): T[] {
  return levels.map((_, i) => levels.slice(0, i + 1).reduce((acc, x) => add(acc, x), {} as T))
}

const show = (d: Record<string, number | undefined>, keys: [string, string][]) =>
  keys.filter(([k]) => d[k]).map(([k, label]) => `${label} +${d[k]}`).join(', ') || '—'

/** Fates' supports: how Attack Stance and Guard Stance bonuses work and stack, and what each partner gives. */
export function FatesSupports() {
  const names = useMemo(() => [AVATAR, ...Object.keys(FATES_TAG_TEAM).sort()], [])
  const classes = useMemo(() => Object.keys(FATES_CLASS_PAIR_UP).sort(), [])
  const [partner, setPartner] = useState('Ryoma')
  const [boon, setBoon] = useState('Strong')
  const [bane, setBane] = useState('Unlucky')
  const [cls, setCls] = useState('Swordmaster')
  const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'
  const avatar = partner === AVATAR

  const tag = cumulative((avatar ? FATES_TAG_TEAM_AVATAR[boon]?.[bane] : FATES_TAG_TEAM[partner]) ?? [])
  const pair = cumulative((avatar ? FATES_PAIR_UP_AVATAR[boon]?.[bane] : FATES_PAIR_UP[partner]) ?? [])
  const classStats = FATES_CLASS_PAIR_UP[cls] ?? {}

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">How supports work</h2>
        <div>
          <p className="text-neutral-100">Attack Stance: fighting next to an ally</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            <li>The ally may join in with a Dual Strike, and gives you Hit, Avoid, Crit and Dodge bonuses.</li>
            <li>The bonuses depend on who the ally is and your support level with them. Even with no support you get Hit +10.</li>
            <li>They build up: your total at a level is everything from No support up to that level added together.</li>
            <li>
              <span className="text-neutral-100">Several allies next to you stack, but not fully:</span> add all their bonuses together,
              divide by 2.5 and round down. Two allies each giving Hit +10 add to 20, which becomes Hit +8.
            </li>
          </ul>
        </div>
        <div>
          <p className="text-neutral-100">Guard Stance: paired up</p>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            <li>The partner may block a hit with a Dual Guard once the guard gauge is full.</li>
            <li>
              You get <span className="text-neutral-100">stat bonuses</span>: the partner's class pair-up stats plus their own support stats for
              your support level, which also build up from C to S.
            </li>
            <li>The partner's Attack Stance bonuses don't apply; you get a flat Dodge +5 instead.</li>
            <li>Only your one partner counts: Pair Up bonuses don't stack with anyone else's.</li>
          </ul>
        </div>
        <p className="text-xs text-neutral-500">
          Children give their parents' bonuses: their mother's at C and A, their father's at B and S (Tag Team), and the other way round
          for Pair Up stats.
        </p>
      </section>

      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
        <h2 className="font-semibold text-neutral-100">What a partner gives you</h2>
        <div className="flex flex-wrap items-center gap-2">
          <select value={partner} onChange={(e) => setPartner(e.target.value)} className={select} aria-label="Support partner">
            {names.map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
          {avatar && (
            <>
              <select
                value={boon}
                onChange={(e) => {
                  setBoon(e.target.value)
                  if (SAME_STAT[e.target.value] === bane) setBane(BANES.find((x) => x !== SAME_STAT[e.target.value])!)
                }}
                className={select}
                aria-label="Boon"
              >
                {BOONS.map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
              <select value={bane} onChange={(e) => setBane(e.target.value)} className={select} aria-label="Bane">
                {BANES.filter((x) => x !== SAME_STAT[boon]).map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </>
          )}
        </div>

        <p className="text-neutral-400">Next to you (Attack Stance), in total</p>
        <table className="w-full border-collapse text-xs sm:text-sm">
          <tbody>
            {['None', 'C', 'B', 'A', 'S'].map((level, i) => (
              <tr key={level} className="border-b border-neutral-800">
                <td className={`${CELL} w-10 text-neutral-100`}>{level}</td>
                <td className={CELL}>{tag[i] ? show(tag[i], TAG_KEYS) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="flex flex-wrap items-center gap-2">
          <p className="text-neutral-400">Paired up (Guard Stance), in total, with their class as</p>
          <select value={cls} onChange={(e) => setCls(e.target.value)} className={select} aria-label="Partner's class">
            {classes.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>
        <table className="w-full border-collapse text-xs sm:text-sm">
          <tbody>
            {['None', 'C', 'B', 'A', 'S'].map((level, i) => {
              const support = i === 0 ? {} : pair[i - 1] ?? {}
              return (
                <tr key={level} className="border-b border-neutral-800">
                  <td className={`${CELL} w-10 text-neutral-100`}>{level}</td>
                  <td className={CELL}>{show(add(classStats, support), STAT_KEYS)}, Ddg +5</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="text-xs text-neutral-500">Of that, the class gives: {show(classStats, STAT_KEYS)}.</p>
      </section>
    </div>
  )
}
