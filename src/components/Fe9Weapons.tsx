import { useMemo, useRef, useState } from 'react'
import { FE9_WEAPONS } from '../data/fe9/fe9Weapons'
import type { Fe9Weapon } from '../data/fe9/types'
import { Fe9Forge } from './Fe9Forge'
import { PixelIcon } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import { ARMOR_HELM, BRAVE, DRAGON_HEAD, HORSE_HEAD, LION_HEAD, MAGIC, NO_CRIT, PAW, WING } from '../icons/sprites'

const CATEGORIES = ['all', 'Sword', 'Lance', 'Axe', 'Bow', 'Knife', 'Fire', 'Thunder', 'Wind', 'Light', 'Staff'] as const
const MAGIC_CATEGORIES = new Set(['Fire', 'Thunder', 'Wind', 'Light'])
const TARGET: Record<string, { sprite: Sprite; label: string }> = {
  flying: { sprite: WING, label: 'fliers' },
  armour: { sprite: ARMOR_HELM, label: 'armoured units' },
  horseback: { sprite: HORSE_HEAD, label: 'horseback units' },
  beast: { sprite: LION_HEAD, label: 'beast laguz' },
  dragon: { sprite: DRAGON_HEAD, label: 'dragon laguz' },
  laguz: { sprite: PAW, label: 'laguz' },
}
const STAT_NAME: Record<string, string> = { hp: 'HP', str: 'Str', mag: 'Mag', skl: 'Skl', spd: 'Spd', lck: 'Lck', def: 'Def', res: 'Res' }
const NUM = 'w-0 py-1 pr-2 sm:pr-3'
/** Against a unit it's effective on, the weapon's Mt doubles (main.dol, 0x801a9084). */
const EFFECTIVE_MULTIPLIER = 2

const isMagic = (w: Fe9Weapon) => MAGIC_CATEGORIES.has(w.category) || w.flags.includes('magsw')

/** The small icons next to a weapon's name: what it's effective against and its special rules. */
function Markers({ weapon }: { weapon: Fe9Weapon }) {
  const icon = (sprite: Sprite, title: string, key: string) => (
    <span key={key} className="ml-1 inline-flex" title={title}>
      <PixelIcon sprite={sprite} size={14} title={title} />
    </span>
  )
  return (
    <>
      {isMagic(weapon) && weapon.category !== 'Staff' && icon(MAGIC, 'Deals magic damage', 'magic')}
      {weapon.effective.map((t) => icon(TARGET[t].sprite, `Effective against ${TARGET[t].label} (Mt ×${EFFECTIVE_MULTIPLIER})`, t))}
      {weapon.flags.includes('twice') && icon(BRAVE, 'Strikes twice in a row, when attacking and when countering', 'brave')}
      {weapon.flags.includes('crit0') && icon(NO_CRIT, "Can't land critical hits", 'nocrit')}
    </>
  )
}

/** Path of Radiance's weapons, read from the game's own item table. */
export function Fe9Weapons() {
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>('all')
  const [search, setSearch] = useState('')
  const [forgeableOnly, setForgeableOnly] = useState(false)
  const [selectedId, setSelectedId] = useState(FE9_WEAPONS[0]?.id ?? null)
  const detailRef = useRef<HTMLDivElement>(null)

  const filtered = useMemo(
    () =>
      FE9_WEAPONS.filter(
        (w) =>
          (category === 'all' || w.category === category) &&
          (!forgeableOnly || w.forge) &&
          (!search || w.name.toLowerCase().includes(search.toLowerCase())),
      ),
    [category, search, forgeableOnly],
  )
  const selected = FE9_WEAPONS.find((w) => w.id === selectedId) ?? null

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
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as (typeof CATEGORIES)[number])}
          className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        >
          {CATEGORIES.map((c) => (
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
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input type="checkbox" checked={forgeableOnly} onChange={(e) => setForgeableOnly(e.target.checked)} />
          Forgeable only
        </label>
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
                <th className={NUM}>Crit</th>
                <th className={NUM}>Wt</th>
                <th className={NUM}>Rng</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((w) => (
                <tr
                  key={w.id}
                  onClick={() => select(w.id)}
                  className={`cursor-pointer border-b border-neutral-800 hover:bg-neutral-800 ${selectedId === w.id ? 'bg-neutral-800' : ''}`}
                >
                  <td className="py-1 pl-2 pr-1 text-neutral-100 sm:pr-3">
                    {w.name}
                    <Markers weapon={w} />
                  </td>
                  <td className={`${NUM} text-neutral-400`}>{w.rank}</td>
                  <td className={NUM}>{w.category === 'Staff' ? '—' : w.mt}</td>
                  <td className={NUM}>{w.hit}</td>
                  <td className={NUM}>{w.crit}</td>
                  <td className={NUM}>{w.wt}</td>
                  <td className={`${NUM} whitespace-nowrap`}>{w.range}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div
          ref={detailRef}
          className="scroll-mt-4 rounded border border-neutral-800 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto"
        >
          {selected ? <Detail key={selected.id} weapon={selected} /> : <p className="p-4 text-neutral-500">Select a weapon to see its details.</p>}
        </div>
      </div>
    </>
  )
}

function Detail({ weapon: w }: { weapon: Fe9Weapon }) {
  const stat = (label: string, value: string | number) => (
    <div className="rounded bg-neutral-900 px-2 py-1 text-center">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-neutral-100">{value}</p>
    </div>
  )
  const bonuses = Object.entries(w.stats)
  return (
    <div className="flex flex-col gap-3 p-4 text-sm">
      <div>
        <h2 className="text-xl font-semibold text-neutral-100">{w.name}</h2>
        <p className="text-neutral-500">
          {w.category} · Rank {w.rank}
          {isMagic(w) && w.category !== 'Staff' ? ' · magic damage' : ''}
        </p>
      </div>
      <div className="grid grid-cols-4 gap-2">
        {stat('Mt', w.category === 'Staff' ? '—' : w.mt)}
        {stat('Hit', w.hit)}
        {stat('Crit', w.crit)}
        {stat('Wt', w.wt)}
        {stat('Rng', w.range)}
        {stat('Uses', w.uses ?? '∞')}
        {stat('Price', w.worth ? w.worth.toLocaleString() : '—')}
        {stat('WEx', w.wex)}
      </div>
      {w.effective.length > 0 && (
        <p className="text-amber-200">
          {w.effective.map((t) => (
            <PixelIcon key={t} sprite={TARGET[t].sprite} size={14} />
          ))}{' '}
          Effective against {w.effective.map((t) => TARGET[t].label).join(' and ')}: Mt ×{EFFECTIVE_MULTIPLIER} ({w.mt} →{' '}
          {w.mt * EFFECTIVE_MULTIPLIER})
        </p>
      )}
      {w.worth > 0 && !w.flags.includes('valuable') && (
        <p className="text-neutral-400">
          Sells for {Math.floor(w.worth / 2).toLocaleString()}G with full uses: half the price of the uses left.
        </p>
      )}
      {w.rules.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-neutral-300">
          {w.rules.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      {bonuses.length > 0 && (
        <p className="text-neutral-300">
          <span className="text-neutral-500">While equipped: </span>
          {bonuses.map(([k, v]) => `${STAT_NAME[k]} ${v! > 0 ? '+' : '−'}${Math.abs(v!)}`).join(', ')}
        </p>
      )}
      {w.uses === null && <p className="text-neutral-400">Never breaks.</p>}
      {w.forge ? <Fe9Forge weapon={w} /> : <p className="text-neutral-500">Can't be used as a base at the forge.</p>}
    </div>
  )
}
