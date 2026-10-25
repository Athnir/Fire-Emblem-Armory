import { useMemo, useRef, useState } from 'react'
import { FE4_WEAPONS } from '../data/fe4/fe4Weapons'
import type { Fe4Weapon } from '../data/fe4/types'
import { PixelIcon } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import { ARMOR_HELM, BRAVE, HORSE_HEAD, MAGIC, WING } from '../icons/sprites'

const CATEGORIES = ['Sword', 'Lance', 'Axe', 'Bow', 'Fire', 'Thunder', 'Wind', 'Light', 'Dark', 'Staff'] as const
const MAGIC_CATEGORIES = new Set(['Fire', 'Thunder', 'Wind', 'Light', 'Dark'])
const TARGET: Record<string, { sprite: Sprite; label: string }> = {
  horseback: { sprite: HORSE_HEAD, label: 'horseback units' },
  flying: { sprite: WING, label: 'fliers' },
  armour: { sprite: ARMOR_HELM, label: 'armoured units' },
}
const STAT_NAME: Record<string, string> = { str: 'Str', mag: 'Mag', skl: 'Skl', spd: 'Spd', lck: 'Lck', def: 'Def', mdf: 'Mdf', mov: 'Mov' }
const NUM = 'w-0 py-1 pr-2 sm:pr-3'

const strikesTwice = (w: Fe4Weapon) => !!w.rules?.includes('Strikes twice in a row')

/** The small icons next to a weapon's name: what it's effective against and its special rules. */
function Markers({ weapon: w }: { weapon: Fe4Weapon }) {
  const icon = (sprite: Sprite, title: string, key: string) => (
    <span key={key} className="ml-1 inline-flex" title={title}>
      <PixelIcon sprite={sprite} size={14} title={title} />
    </span>
  )
  return (
    <>
      {MAGIC_CATEGORIES.has(w.category) && icon(MAGIC, 'Deals magic damage', 'magic')}
      {w.effective?.map((t) => icon(TARGET[t].sprite, `Effective against ${TARGET[t].label}`, t))}
      {strikesTwice(w) && icon(BRAVE, 'Strikes twice in a row', 'brave')}
    </>
  )
}

/** Genealogy of the Holy War's weapons, read from the game's own item table: a filterable list and a detail panel. */
export function Fe4Weapons() {
  const [category, setCategory] = useState('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(FE4_WEAPONS[0].id)
  const detailRef = useRef<HTMLDivElement>(null)
  const filtered = useMemo(
    () => FE4_WEAPONS.filter((w) => (category === 'all' || w.category === category) && (!search || w.name.toLowerCase().includes(search.toLowerCase()))),
    [category, search],
  )
  const selected = FE4_WEAPONS.find((w) => w.id === selectedId) ?? FE4_WEAPONS[0]

  function select(id: string) {
    setSelectedId(id)
    const panel = detailRef.current
    if (!panel) return
    const top = panel.getBoundingClientRect().top
    if (top < 0 || top > window.innerHeight * 0.5) panel.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <>
      <div className="flex flex-wrap gap-3">
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1">
          {['all', ...CATEGORIES].map((c) => (
            <option key={c} value={c}>
              {c === 'all' ? 'All categories' : c}
            </option>
          ))}
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search weapon name..."
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        />
      </div>
      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded border border-neutral-800">
          <table className="w-full border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-neutral-700 text-left text-neutral-400">
                <th className="py-1 pl-2 pr-1 sm:pr-3">Name</th>
                <th className={NUM}>Rank</th>
                <th className={NUM}>Mt</th>
                <th className={NUM}>Hit</th>
                <th className={NUM}>Wt</th>
                <th className={NUM}>Rng</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((w) => (
                <tr
                  key={w.id}
                  onClick={() => select(w.id)}
                  className={`cursor-pointer border-b border-neutral-800 hover:bg-neutral-800 ${selected.id === w.id ? 'bg-neutral-800' : ''}`}
                >
                  <td className="py-1 pl-2 pr-1 text-neutral-100 sm:pr-3">
                    {w.name}
                    <Markers weapon={w} />
                  </td>
                  <td className={`${NUM} text-neutral-400`}>{w.rank}</td>
                  <td className={NUM}>{w.mt ?? '—'}</td>
                  <td className={NUM}>{w.hit ?? '—'}</td>
                  <td className={NUM}>{w.wt ?? '—'}</td>
                  <td className={`${NUM} whitespace-nowrap`}>{w.range}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-neutral-500">
                    No weapons match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div
          ref={detailRef}
          className="scroll-mt-4 rounded border border-neutral-800 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto"
        >
          <Detail key={selected.id} weapon={selected} />
        </div>
      </div>
    </>
  )
}

function Detail({ weapon: w }: { weapon: Fe4Weapon }) {
  const stat = (label: string, value: string | number) => (
    <div className="rounded bg-neutral-900 px-2 py-1 text-center">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-neutral-100">{value}</p>
    </div>
  )
  const bonuses = Object.entries(w.stats ?? {})
  return (
    <div className="flex flex-col gap-3 p-4 text-sm">
      <div>
        <h2 className="text-xl font-semibold text-neutral-100">{w.name}</h2>
        <p className="text-neutral-500">
          {w.category} · {w.rank === 'Holy' ? 'Holy weapon' : `Rank ${w.rank}`}
          {MAGIC_CATEGORIES.has(w.category) ? ' · magic damage' : ''}
        </p>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {w.category !== 'Staff' && stat('Mt', w.mt ?? '—')}
        {w.category !== 'Staff' && stat('Hit', w.hit ?? '—')}
        {w.category !== 'Staff' && stat('Wt', w.wt ?? '—')}
        {stat('Rng', w.range)}
        {stat('Uses', w.uses)}
        {stat('Price', w.worth ? w.worth.toLocaleString() : '—')}
        {w.exp !== undefined && stat('EXP', w.exp)}
      </div>
      {w.effective && w.effective.length > 0 && (
        <p className="text-amber-200">
          {w.effective.map((t) => (
            <PixelIcon key={t} sprite={TARGET[t].sprite} size={14} />
          ))}{' '}
          Effective against {w.effective.map((t) => TARGET[t].label).join(' and ')}
        </p>
      )}
      {w.effect && <p className="text-neutral-300">{w.effect}</p>}
      {w.rules && w.rules.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-neutral-300">
          {w.rules.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      {w.skills && w.skills.length > 0 && <p className="text-neutral-300">Gives the {w.skills.join(' and ')} skill while it is equipped.</p>}
      {bonuses.length > 0 && (
        <p className="text-neutral-300">
          <span className="text-neutral-500">While equipped: </span>
          {bonuses.map(([k, v]) => `${STAT_NAME[k]} +${v}`).join(', ')}
        </p>
      )}
    </div>
  )
}
