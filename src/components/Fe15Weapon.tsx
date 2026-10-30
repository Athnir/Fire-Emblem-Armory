import type { Fe15Weapon } from '../data/fe15/fe15Types'

const CELL = 'py-1 pr-2 sm:pr-3'
const TARGETS: Record<string, string> = { horseback: 'horseback units', armour: 'armoured units', flying: 'fliers', terror: 'Terrors' }
const signed = (n: number) => (n > 0 ? `+${n}` : `${n}`)
const marks = (silver: number, gold: number) =>
  [silver ? `${silver} silver` : '', gold ? `${gold} gold` : ''].filter(Boolean).join(' and ') || 'free'

/** Echoes' extras for one weapon: the combat arts it teaches, its forge stars (cumulative costs, total bonuses) and what it evolves into. */
export function Fe15WeaponExtra({ weapon: w }: { weapon: Fe15Weapon }) {
  const arts = w.arts ?? []
  const forge = w.forge ?? []
  return (
    <div className="flex flex-col gap-3">
      {w.dlc && (
        <p className="text-xs text-neutral-500">
          Downloadable content. The Armory hasn't read the DLC's own files yet, so these numbers are Fire Emblem Wiki's (an art the base game
          also teaches uses the game's own numbers).
        </p>
      )}
      {arts.length > 0 && (
        <div>
          <h3 className="font-semibold text-neutral-100">Combat arts</h3>
          <p className="text-xs text-neutral-500">Learned once the unit's mastery of the weapon reaches the number shown.</p>
          <ul className="mt-1 space-y-1">
            {arts.map((a, i) =>
              a.name ? (
                <li key={i} className="text-neutral-300">
                  <span className="text-neutral-100">{a.name}</span>
                  <span className="text-neutral-500">
                    {' '}
                    · mastery {a.mastery}
                    {a.hp ? ` · ${a.hp} HP` : ''}
                  </span>
                  <br />
                  <span className="text-xs">
                    {[
                      a.mt ? `Mt ${signed(a.mt)}` : '',
                      a.hit ? `Hit ${signed(a.hit)}` : '',
                      a.avo ? `Avo ${signed(a.avo)}` : '',
                      a.crit ? `Crit ${signed(a.crit)}` : '',
                      a.range ? `Range ${signed(a.range)}` : '',
                      a.strikes ? `${a.strikes} hits` : '',
                      a.attack ? `${a.attack}% attack` : '',
                    ]
                      .filter(Boolean)
                      .join(', ')}
                    {a.effective?.length
                      ? `${a.mt ? '; its Mt bonus counts three times' : '; effective'} against ${a.effective.map((t) => TARGETS[t] ?? t).join(' and ')}`
                      : ''}
                    {a.effect ? `. ${a.effect}` : ''}
                  </span>
                </li>
              ) : (
                <li key={i} className="text-neutral-500">
                  An art the item names as <code>{a.id}</code>, which no skill has (see the notes below).
                </li>
              ),
            )}
          </ul>
        </div>
      )}
      {forge.length > 0 && (
        <div>
          <h3 className="font-semibold text-neutral-100">Forge</h3>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-xs sm:text-sm">
              <thead>
                <tr className="border-b border-neutral-700 text-left text-neutral-400">
                  <th className={CELL}>Stars</th>
                  <th className={CELL}>Cost</th>
                  <th className={CELL}>Mt</th>
                  <th className={CELL}>Hit</th>
                  <th className={CELL}>Crit</th>
                  <th className={CELL}>Wt</th>
                </tr>
              </thead>
              <tbody>
                {forge.map((s, i) => (
                  <tr key={i} className="border-b border-neutral-800">
                    <td className={`${CELL} text-neutral-100`}>{'★'.repeat(i + 1)}</td>
                    <td className={CELL}>{marks(s.silver, s.gold)}</td>
                    <td className={CELL}>{s.mt ? signed(s.mt) : '—'}</td>
                    <td className={CELL}>{s.hit ? signed(s.hit) : '—'}</td>
                    <td className={CELL}>{s.crit ? signed(s.crit) : '—'}</td>
                    <td className={CELL}>{s.wt ? signed(s.wt) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-neutral-500">Each star costs its own marks; the bonuses are the weapon's totals at that star.</p>
        </div>
      )}
      {w.evolve && w.evolve.length > 0 && (
        <div>
          <h3 className="font-semibold text-neutral-100">Evolves into</h3>
          <ul className="list-disc space-y-0.5 pl-5 text-neutral-300">
            {w.evolve.map((e, i) => (
              <li key={i}>
                {e.into}: {marks(e.silver, e.gold)} marks
                {e.stars ? `, once it has ${e.stars} star${e.stars === 1 ? '' : 's'}` : ''}
              </li>
            ))}
          </ul>
          {w.name.startsWith('Rusted') && (
            <p className="text-xs text-neutral-500">Each Rusted copy is one of these, fixed when the item is made.</p>
          )}
        </div>
      )}
      {w.markValue && (w.markValue.silver > 0 || w.markValue.gold > 0) && (
        <p className="text-xs text-neutral-500">
          Value in marks: {marks(w.markValue.silver, w.markValue.gold)} (
          {w.dlc ? "Fire Emblem Wiki's worth" : 'the first row of its forge list'}; a blacksmith trades it in for half, as Serenes Forest's
          exchange table gives).
        </p>
      )}
    </div>
  )
}
