import { useState } from 'react'
import type { TriangleBonus, TriangleRules } from '../logic/triangle'
import { triangleOutcome } from '../logic/triangle'

const CELL = 'py-1 pr-2 sm:pr-3'
const signed = (n: number) => (n > 0 ? `+${n}` : n < 0 ? `−${-n}` : '0')
const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'

/** "+10 hit, +1 Mt": the parts that change, or "No change". */
function describe(b: TriangleBonus, mtLabel: string) {
  const parts = []
  if (b.hit) parts.push(`${signed(b.hit)} hit`)
  if (b.mt) parts.push(`${signed(b.mt)} ${mtLabel}`)
  if (b.avoid) parts.push(`${signed(b.avoid)} avoid`)
  return parts.length ? parts.join(', ') : 'No change'
}

/**
 * The weapon triangle tab, the same for every game: who beats whom, what the advantage is worth (by rank where the game scales it),
 * the game's special rules, its weapon rank bonuses and leadership where it has them, and a calculator. The game passes its rules in.
 */
export function TriangleTab({ rules }: { rules: TriangleRules }) {
  const types = Object.keys(rules.beats)
  const byRank = rules.advantage.length > 1
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="flex flex-col gap-4">
        <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
          <h2 className="font-semibold text-neutral-100">Who beats whom</h2>
          <table className="w-full border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-neutral-700 text-left text-neutral-400">
                <th className={CELL}>Weapon</th>
                <th className={CELL}>Beats</th>
              </tr>
            </thead>
            <tbody>
              {types.map((w) => (
                <tr key={w} className="border-b border-neutral-800">
                  <td className={`${CELL} text-neutral-100`}>{w}</td>
                  <td className={CELL}>{rules.beats[w].join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-neutral-400">{rules.outside}</p>
        </section>

        <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
          <h2 className="font-semibold text-neutral-100">What it's worth</h2>
          {byRank ? (
            <table className="w-full border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-neutral-700 text-left text-neutral-400">
                  <th className={CELL}>Advantaged weapon's rank</th>
                  <th className={CELL}>Advantage</th>
                  <th className={CELL}>Disadvantage</th>
                </tr>
              </thead>
              <tbody>
                {rules.advantage.map((a) => (
                  <tr key={a.rank} className="border-b border-neutral-800">
                    <td className={`${CELL} text-neutral-100`}>{a.rank}</td>
                    <td className={CELL}>{describe(a, rules.mtLabel)}</td>
                    <td className={CELL}>{describe({ hit: -a.hit, mt: a.mt === undefined ? undefined : -a.mt }, rules.mtLabel)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <ul className="list-disc space-y-1 pl-5">
              <li>
                Advantage: <span className="text-emerald-300">{describe(rules.advantage[0], rules.mtLabel)}</span>
              </li>
              {rules.loser === 'mirror' && (
                <li>
                  Disadvantage:{' '}
                  <span className="text-amber-300">
                    {describe(
                      {
                        hit: -rules.advantage[0].hit,
                        ...(rules.advantage[0].mt !== undefined && { mt: -rules.advantage[0].mt }),
                        ...(rules.advantage[0].avoid !== undefined && { avoid: -rules.advantage[0].avoid }),
                      },
                      rules.mtLabel,
                    )}
                  </span>
                </li>
              )}
            </ul>
          )}
          <ul className="list-disc space-y-1 pl-5">
            {rules.rules.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>

        {rules.rankBonus && (
          <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
            <h2 className="font-semibold text-neutral-100">Weapon rank bonuses</h2>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-xs sm:text-sm">
                <thead>
                  <tr className="border-b border-neutral-700 text-left text-neutral-400">
                    <th className={CELL}>Type</th>
                    {Object.keys(rules.rankBonus.rows[0].byRank).map((r) => (
                      <th key={r} className={CELL}>
                        {r}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rules.rankBonus.rows.map((row) => (
                    <tr key={row.types} className="border-b border-neutral-800 align-top">
                      <td className={`${CELL} text-neutral-100`}>{row.types}</td>
                      {Object.entries(row.byRank).map(([r, [first, hit]]) => (
                        <td key={r} className={CELL}>
                          {first || hit ? (
                            <>
                              {first !== 0 && <div>{`${signed(first)} ${row.first}`}</div>}
                              {hit !== 0 && <div>{`${signed(hit)} hit`}</div>}
                            </>
                          ) : (
                            <span className="text-neutral-600">—</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <ul className="list-disc space-y-1 pl-5">
              {rules.rankBonus.rules.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </section>
        )}

        {rules.leadership && (
          <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
            <h2 className="font-semibold text-neutral-100">Leadership stars</h2>
            <table className="w-full border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-neutral-700 text-left text-neutral-400">
                  <th className={CELL}>Stars</th>
                  {rules.leadership.byStars.map((_, i) => (
                    <th key={i} className={CELL}>
                      {i}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-neutral-800">
                  <td className={`${CELL} text-neutral-100`}>Hit and avoid</td>
                  {rules.leadership.byStars.map((b, i) => (
                    <td key={i} className={CELL}>
                      {b.hit ? signed(b.hit) : '—'}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
            <ul className="list-disc space-y-1 pl-5">
              {rules.leadership.rules.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <Calculator rules={rules} />
    </div>
  )
}

function Calculator({ rules }: { rules: TriangleRules }) {
  const types = [...Object.keys(rules.beats), 'Other']
  const byRank = rules.advantage.length > 1
  const [you, setYou] = useState(types[0])
  const [foe, setFoe] = useState(types[1] ?? types[0])
  const [rank, setRank] = useState(rules.advantage[0].rank ?? '')
  const [yourReaver, setYourReaver] = useState(false)
  const [foeReaver, setFoeReaver] = useState(false)
  const [off, setOff] = useState(false)
  const [stars, setStars] = useState(0)
  const out = triangleOutcome(rules, you, foe, { rank, yourReaver, foeReaver, off })
  const lead = rules.leadership?.byStars[stars]
  const standing = out.level > 0 ? 'advantage' : out.level < 0 ? 'disadvantage' : 'neither side has the advantage'

  return (
    <section className="flex h-fit flex-col gap-3 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h2 className="font-semibold text-neutral-100">Calculator</h2>
      <label className="flex flex-wrap items-center gap-2">
        Your weapon
        <select value={you} onChange={(e) => setYou(e.target.value)} className={select}>
          {types.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </label>
      <label className="flex flex-wrap items-center gap-2">
        Foe's weapon
        <select value={foe} onChange={(e) => setFoe(e.target.value)} className={select}>
          {types.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </label>
      {byRank && (
        <label className="flex flex-wrap items-center gap-2">
          Rank of the advantaged unit's weapon
          <select value={rank} onChange={(e) => setRank(e.target.value)} className={select}>
            {rules.advantage.map((a) => (
              <option key={a.rank}>{a.rank}</option>
            ))}
          </select>
        </label>
      )}
      {rules.reaver && (
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={yourReaver} onChange={(e) => setYourReaver(e.target.checked)} />
            Your weapon is a reaver
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={foeReaver} onChange={(e) => setFoeReaver(e.target.checked)} />
            Foe's is a reaver
          </label>
        </div>
      )}
      {rules.offOn && (
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={off} onChange={(e) => setOff(e.target.checked)} />
          {rules.offOn}
        </label>
      )}

      <p className="text-neutral-400">
        {out.level === 0 ? (off ? 'The triangle is off.' : 'Neither side has the advantage.') : `You have the ${standing}${Math.abs(out.level) > 1 ? ', doubled' : ''}.`}
      </p>
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded border border-neutral-800 p-2">
          <p className="text-xs text-neutral-500">You</p>
          <p className={out.level > 0 ? 'text-emerald-300' : out.level < 0 ? 'text-amber-300' : ''}>{describe(out.you, rules.mtLabel)}</p>
          {out.youLoseRankBonus && <p className="text-xs text-amber-300">No weapon rank bonus.</p>}
        </div>
        <div className="rounded border border-neutral-800 p-2">
          <p className="text-xs text-neutral-500">Foe</p>
          <p className={out.level < 0 ? 'text-emerald-300' : out.level > 0 ? 'text-amber-300' : ''}>{describe(out.foe, rules.mtLabel)}</p>
          {out.foeLoseRankBonus && <p className="text-xs text-amber-300">No weapon rank bonus.</p>}
        </div>
      </div>

      {rules.leadership && lead && (
        <>
          <label className="flex flex-wrap items-center gap-2 border-t border-neutral-800 pt-3">
            Your commander's leadership
            <select value={stars} onChange={(e) => setStars(Number(e.target.value))} className={select}>
              {rules.leadership.byStars.map((_, i) => (
                <option key={i} value={i}>
                  {i} {i === 1 ? 'star' : 'stars'}
                </option>
              ))}
            </select>
          </label>
          <p>
            Leadership adds <span className="text-emerald-300">{signed(lead.hit)} hit</span> and{' '}
            <span className="text-emerald-300">{signed(lead.avoid ?? 0)} avoid</span>
            {out.you.hit || out.you.avoid ? (
              <>
                , so with the triangle you get{' '}
                <span className="text-neutral-100">
                  {signed(lead.hit + out.you.hit)} hit and {signed((lead.avoid ?? 0) + (out.you.avoid ?? 0))} avoid
                </span>
              </>
            ) : null}
            .
          </p>
        </>
      )}
    </section>
  )
}
