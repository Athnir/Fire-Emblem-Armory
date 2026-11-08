import { FE17_REFINE, FE17_SMITHY_OPENS } from '../data/fe17/fe17Refine'
import type { ChapterWeapon, WeaponModifier } from './ChapterWeapons'
import { useReach } from './Reach'

const CELL = 'py-1 pr-2 sm:pr-3'
const STATS = ['mt', 'hit', 'crit', 'wt'] as const
const LABEL = { mt: 'Mt', hit: 'Hit', crit: 'Crit', wt: 'Wt' } as const

type Level = (typeof FE17_REFINE)[string][number]

const cost = (l: Pick<Level, 'iron' | 'steel' | 'silver' | 'gold'>) =>
  [
    l.iron && `${l.iron.toLocaleString()} Iron`,
    l.steel && `${l.steel.toLocaleString()} Steel`,
    l.silver && `${l.silver.toLocaleString()} Silver`,
    `${l.gold.toLocaleString()}G`,
  ]
    .filter(Boolean)
    .join(', ')

/** Engage's refining for one weapon (item.xml's refine table): the stats at each of its five levels and what the step to it costs in
 * ore and gold at the Somniel's smithy, with an engraving picked on the datasheet added (App.UnitItem.GetPower...: the item's, its
 * refine level's and the engraving's numbers). Under the spoiler block it says nothing before the smithy opens; a weapon only foes
 * carry has none. */
export function Fe17Refine({ weapon: w, engraving }: { weapon: ChapterWeapon; engraving?: WeaponModifier }) {
  const reach = useReach()
  const table = FE17_REFINE[w.id]
  if (!table || w.foeOnly || !reach.has(FE17_SMITHY_OPENS)) return null
  const add = (l: Pick<Level, 'mt' | 'hit' | 'crit' | 'wt'>) => ({
    mt: l.mt + (engraving?.mt ?? 0),
    hit: l.hit + (engraving?.hit ?? 0),
    crit: l.crit + (engraving?.crit ?? 0),
    wt: l.wt + (engraving?.wt ?? 0),
  })
  const levels = table.map((l) => ({ ...l, ...add(l) }))
  const base = add({ mt: w.mt ?? 0, hit: w.hit ?? 0, crit: w.crit ?? 0, wt: w.wt ?? 0 })
  const all = levels.reduce(
    (t, l) => ({ iron: t.iron + l.iron, steel: t.steel + l.steel, silver: t.silver + l.silver, gold: t.gold + l.gold }),
    { iron: 0, steel: 0, silver: 0, gold: 0 },
  )
  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-semibold text-neutral-100">Refine</h3>
      <table className="w-full border-collapse text-xs sm:text-sm">
        <thead>
          <tr className="border-b border-neutral-700 text-left text-neutral-400">
            <th className={CELL}>Level</th>
            {STATS.map((k) => (
              <th key={k} className={CELL}>
                {LABEL[k]}
              </th>
            ))}
            <th className={CELL}>Step cost</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-b border-neutral-800 text-neutral-400">
            <td className={CELL}>Base</td>
            {STATS.map((k) => (
              <td key={k} className={CELL}>
                {base[k]}
              </td>
            ))}
            <td className={CELL} />
          </tr>
          {levels.map((l, k) => {
            const before = k ? levels[k - 1] : base
            return (
              <tr key={k} className="border-b border-neutral-800">
                <td className={`${CELL} text-neutral-100`}>+{k + 1}</td>
                {STATS.map((s) => (
                  <td key={s} className={`${CELL} ${l[s] !== before[s] ? 'text-emerald-300' : ''}`}>
                    {l[s]}
                  </td>
                ))}
                <td className={`${CELL} text-neutral-300`}>{cost(l)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="text-neutral-400">
        Refined one level at a time at the Somniel&apos;s smithy; all five steps cost {cost(all)}.
        {engraving && ` The numbers include the ${engraving.label} engraving.`}
      </p>
    </div>
  )
}
