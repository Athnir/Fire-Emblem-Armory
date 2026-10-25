import { useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { TelliusWeapon } from '../data/fe9/types'
import type { StoryOrder } from '../data/maps/mapSet'
import { firstChapter, inChapter } from '../logic/spoilerWeapons'
import { useReach } from './Reach'
import { PixelIcon } from '../icons/PixelSprite'
import { ByDifficulty } from './ByDifficulty'
import type { Sprite } from '../icons/sprites'
import { ARMOR_HELM, BRAVE, DRAGON_HEAD, HORSE_HEAD, LION_HEAD, MAGIC, NO_CRIT, PAW, WING } from '../icons/sprites'

const MAGIC_CATEGORIES = new Set(['Fire', 'Thunder', 'Wind', 'Light', 'Dark'])
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

const isMagic = (w: TelliusWeapon) => MAGIC_CATEGORIES.has(w.category) || w.flags.includes('magsw')

/** What differs between the two Tellius games' weapon pages. */
export interface TelliusWeaponsConfig {
  weapons: TelliusWeapon[]
  categories: readonly string[]
  /** Against a unit it's effective on, the weapon's Mt is multiplied by this (each game's own battle code). */
  effectiveMultiplier: number
  /** Where the maps give an item (chests, villages, drops). */
  mapSources: (name: string) => { mapId: string; map: string; how: string; arrives?: true }[]
  /** The forge panel for a weapon, when the game's forge is in. */
  forge?: (weapon: TelliusWeapon) => ReactNode
  /** The chapters in order: what the spoiler block steps through, and what names a chapter. */
  story: StoryOrder
}

/** The small icons next to a weapon's name: what it's effective against and its special rules. */
function Markers({ weapon, multiplier }: { weapon: TelliusWeapon; multiplier: number }) {
  const icon = (sprite: Sprite, title: string, key: string) => (
    <span key={key} className="ml-1 inline-flex" title={title}>
      <PixelIcon sprite={sprite} size={14} title={title} />
    </span>
  )
  return (
    <>
      {isMagic(weapon) && weapon.category !== 'Staff' && icon(MAGIC, 'Deals magic damage', 'magic')}
      {weapon.effective.map((t) => icon(TARGET[t].sprite, `Effective against ${TARGET[t].label} (Mt ×${multiplier})`, t))}
      {weapon.flags.includes('twice') && icon(BRAVE, 'Strikes twice in a row, when attacking and when countering', 'brave')}
      {weapon.flags.includes('crit0') && icon(NO_CRIT, "Can't land critical hits", 'nocrit')}
    </>
  )
}

/** A Tellius game's weapons, read from its own item table: a filterable list and a detail panel. */
export function TelliusWeapons({ config }: { config: TelliusWeaponsConfig }) {
  const reach = useReach()
  // With the spoiler block on, every weapon you've had a chance to get by this chapter stays listed (the weapons that turn
  // up for the first time get a "new" mark), and each says whether this chapter's base sells it, as a limited bargain or
  // not at all: a base's stock changes from chapter to chapter.
  const { weapons, fresh } = useMemo(() => {
    if (!reach.on) return { weapons: config.weapons, fresh: new Set<string>() }
    const shown: TelliusWeapon[] = []
    const fresh = new Set<string>()
    for (const w of config.weapons) {
      const first = firstChapter(w, config.mapSources, config.story)
      if (first > reach.at) continue
      shown.push(inChapter(w, reach.at, config.story))
      if (reach.at > 0 && first === reach.at) fresh.add(w.id)
    }
    return { weapons: shown, fresh }
  }, [config, reach])
  // Radiant Dawn's bases also hold limited stock (bargains); a game without any has no such choice.
  const hasLimited = config.weapons.some((w) => w.bargainAt)
  const categories = config.categories.filter((c) => !reach.on || weapons.some((w) => w.category === c))
  const [pickedCategory, setCategory] = useState('all')
  const category = categories.includes(pickedCategory) ? pickedCategory : 'all'
  const [search, setSearch] = useState('')
  const [forgeableOnly, setForgeableOnly] = useState(false)
  const [stock, setStock] = useState<'all' | 'sale' | 'limited' | 'no'>('all')
  const [selectedId, setSelectedId] = useState(config.weapons[0]?.id ?? null)
  const detailRef = useRef<HTMLDivElement>(null)

  const filtered = useMemo(
    () =>
      weapons.filter(
        (w) =>
          (category === 'all' || w.category === category) &&
          (!forgeableOnly || w.forge) &&
          (stock === 'all' || (stock === 'sale' ? !!w.shop : stock === 'limited' ? !!w.bargain : !w.shop && !w.bargain)) &&
          (!search || w.name.toLowerCase().includes(search.toLowerCase())),
      ),
    [weapons, category, search, forgeableOnly, stock],
  )
  const selected = weapons.find((w) => w.id === selectedId) ?? weapons[0] ?? null

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
          {['all', ...categories].map((c) => (
            <option key={c} value={c}>
              {c === 'all' ? 'All categories' : c}
            </option>
          ))}
        </select>
        {reach.on && (
          <select
            value={stock}
            onChange={(e) => setStock(e.target.value as typeof stock)}
            aria-label="Stock at this chapter's base"
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
          >
            <option value="all">Any stock</option>
            <option value="sale">For sale here</option>
            {hasLimited && <option value="limited">Limited stock here</option>}
            <option value="no">Not for sale here</option>
          </select>
        )}
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search weapon name..."
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        />
        {config.forge && (
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" checked={forgeableOnly} onChange={(e) => setForgeableOnly(e.target.checked)} />
            Forgeable only
          </label>
        )}
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
                  className={`cursor-pointer border-b border-neutral-800 hover:bg-neutral-800 ${selected?.id === w.id ? 'bg-neutral-800' : ''}`}
                >
                  <td className="py-1 pl-2 pr-1 text-neutral-100 sm:pr-3">
                    {w.name}
                    <Markers weapon={w} multiplier={config.effectiveMultiplier} />
                    {fresh.has(w.id) && <span className="ml-2 rounded bg-emerald-900 px-1 text-[10px] uppercase text-emerald-200">new</span>}
                    {reach.on && w.shop && <span className="ml-2 rounded bg-sky-900 px-1 text-[10px] uppercase text-sky-200">for sale</span>}
                    {reach.on && w.bargain && <span className="ml-2 rounded bg-amber-900 px-1 text-[10px] uppercase text-amber-200">limited</span>}
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
          {selected ? <Detail key={selected.id} weapon={selected} config={config} /> : <p className="p-4 text-neutral-500">Select a weapon to see its details.</p>}
        </div>
      </div>
    </>
  )
}

/** Where to get it: the base's shops (and bargains) by difficulty, then every chest, village, buried spot and drop on the maps. */
function Sources({ weapon: w, config }: { weapon: TelliusWeapon; config: TelliusWeaponsConfig }) {
  const reach = useReach()
  // Under the spoiler block: the maps you've reached, and not the foes that arrive later, whose drops would give them away.
  const found = config.mapSources(w.name).filter((s) => reach.has(s.mapId) && !(reach.on && s.arrives))
  const shop = w.category === 'Staff' ? 'item shop' : 'armory'
  const chapters = (ids: string[]) => {
    const byId = new Map(config.story.maps.map((m) => [m.id, m]))
    return ids.map((id) => config.story.name(byId.get(id)!)).join(', ')
  }
  return (
    <div className="flex flex-col gap-1">
      <h3 className="font-semibold text-neutral-100">Where to get it</h3>
      {w.shop ? (
        <p className="text-neutral-400">
          Bought at the base's {shop}: <ByDifficulty value={w.shop} none="not sold" />.
        </p>
      ) : (
        // Under the block the same words cover "never sold" and "not sold yet", so they can't hint at a later base.
        <p className="text-neutral-500">{reach.on ? "Not sold at this chapter's base." : 'Not regular stock at any base.'}</p>
      )}
      {w.bargain && (
        <p className="text-neutral-400">
          A bargain (limited stock, one to buy) at the base: <ByDifficulty value={w.bargain} none="none" />.
        </p>
      )}
      {w.baseAt && <p className="text-neutral-400">Given in a base conversation before {chapters(w.baseAt)}.</p>}
      {w.giftAt && <p className="text-neutral-400">Handed over by the story in {chapters(w.giftAt)}.</p>}
      {found.length > 0 && (
        <ul className="list-disc space-y-0.5 pl-5 text-neutral-300">
          {found.map((s) => (
            <li key={s.mapId + s.how}>
              <span className="text-neutral-200">{s.map}</span> <span className="text-neutral-400">· {s.how}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Detail({ weapon: w, config }: { weapon: TelliusWeapon; config: TelliusWeaponsConfig }) {
  const reach = useReach()
  const stat = (label: string, value: string | number) => (
    <div className="rounded bg-neutral-900 px-2 py-1 text-center">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-neutral-100">{value}</p>
    </div>
  )
  const bonuses = Object.entries(w.stats)
  const m = config.effectiveMultiplier
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
          Effective against {w.effective.map((t) => TARGET[t].label).join(' and ')}: Mt ×{m} ({w.mt} → {w.mt * m})
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
      <Sources weapon={w} config={config} />
      {/* Under the spoiler block a weapon the forge doesn't take yet says nothing, so it can't give away that it will. */}
      {config.forge && (w.forge ? config.forge(w) : !reach.on && <p className="text-neutral-500">Can't be used as a base at the forge.</p>)}
    </div>
  )
}
