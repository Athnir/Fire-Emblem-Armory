import { useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import type { StoryOrder } from '../data/maps/mapSet'
import type { ChapterMap } from '../data/maps/types'
import { PixelIcon } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import { ARMOR_HELM, AXE_ICON, BALLISTA, BRAVE, DRAGON_HEAD, GRIMA, HORSE_HEAD, MAGIC, MONSTER, NOT_FOR_PLAYER, SWORD_ICON, WING } from '../icons/sprites'
import { sourceRows } from '../logic/sourceRows'
import type { Reach } from '../logic/spoiler'
import { turnsUpAt } from '../logic/spoiler'
import { useReach } from './Reach'
import { onDifficulty, useDifficulty } from './Difficulty'

/** A weapon of a game whose items turn up chapter by chapter (FE4, FE6): read from the game's own item table. */
export interface ChapterWeapon {
  id: string
  name: string
  /** The item's id in the game's own table. */
  romId?: number
  category: string
  /** The weapon rank needed (E-S, C-A), or what stands in for one (Holy, Prf). */
  rank: string
  /** Absent on staves; null where Mt isn't a number (FE4's Hel). */
  mt?: number | null
  hit?: number
  crit?: number
  wt?: number
  range: string
  /** null: never breaks; absent: the game's weapons have no uses at all (Echoes). */
  uses?: number | null
  /** The full price; null or 0: not for sale; absent where the game sells nothing for gold (Echoes). */
  worth?: number | null
  effective?: string[]
  /** Deals magic damage though its category doesn't (Awakening's Levin Sword, Shockstick and Bolt Axe: the item's magic flag). */
  magic?: true
  skills?: string[]
  rules?: string[]
  stats?: Partial<Record<string, number>>
  exp?: number
  /** A staff's effect. */
  effect?: string
  /** Carried only by foes: nothing gives it to the player. */
  foeOnly?: boolean
  /** Where this weapon's Mt is multiplied by something other than the game's usual (The Sacred Stones' legendary weapons: ×2). */
  effectiveMultiplier?: number
  /** What a shop pays for it, where it isn't half its worth (Awakening's event-tile items: a quarter). */
  sell?: number
}

/** Where an item turns up: the chapter (a map id), how, and in words. A kind ending in '-later' came with a unit that arrives
 * mid-chapter ('drop-later', 'foe-later', 'kit-later'). */
export interface ItemSource {
  mapId: string
  kind: string
  text: string
  /** The difficulties the line holds on (a foe placed on some only); every difficulty when absent. */
  difficulties?: string[]
  /** A shop line that sells only so many (Shadow Dragon's limited stock): how many. */
  limited?: number
}

/** What differs between the games that use this page. */
export interface ChapterWeaponsConfig {
  weapons: ChapterWeapon[]
  sources: Record<string, ItemSource[]>
  story: StoryOrder
  categories: readonly string[]
  /** Categories that deal magic damage. */
  magic: ReadonlySet<string>
  statNames: Record<string, string>
  /** Against a unit it's effective on, Mt is multiplied by this; absent where effectiveness works otherwise (FE4: a critical hit). */
  effectiveMultiplier?: number
  /** "Rank C"; "Holy weapon". */
  rankLabel: (w: ChapterWeapon) => string
  /** What the game's shop is called ("the home castle", "an armory"). */
  shopName: string
  /** The story a chapter is in, where the game has more than one ("Eliwood's story"): sources are grouped by it. */
  routeName?: (map: ChapterMap) => string | undefined
  /**
   * Sources left out until a switch is ticked (Awakening's DLC maps and renown rewards): each switch's label and the sources it covers.
   * A weapon with no other source is listed only once its switch is on; one `weapons` names (Engage's engage weapons, the foes' too)
   * isn't listed at all until then.
   */
  optional?: { label: string; covers?: (s: ItemSource) => boolean; weapons?: (w: ChapterWeapon) => boolean }[]
  /**
   * Something the player adds to a weapon that changes its numbers (Engage's engravings): a picker on the datasheet, its pick added to
   * the stats shown and handed to `extra` (a refine table adds it too). `options` are what this weapon can take by this chapter.
   */
  modifiers?: {
    label: string
    options: (w: ChapterWeapon, reach: Reach) => WeaponModifier[]
    /** A line under the picker once one is picked (what it costs). */
    note?: (w: ChapterWeapon, m: WeaponModifier) => string
  }
  /** Anything the game adds below a weapon's sources (Awakening's forge); `modifier`, the pick from `modifiers`. */
  extra?: (w: ChapterWeapon, modifier?: WeaponModifier) => ReactNode
}

/** What a modifier adds to a weapon (Engage's engravings: Mt, Wt, Hit, Crit, Avoid, Dodge). */
export interface WeaponModifier {
  id: string
  label: string
  mt?: number
  hit?: number
  crit?: number
  wt?: number
  avo?: number
  ddg?: number
}

/** A weapon with a modifier's numbers added: Mt, Hit, Crit and Wt, and Avoid and Dodge among its bonuses while equipped. */
export function withModifier(w: ChapterWeapon, m?: WeaponModifier): ChapterWeapon {
  if (!m) return w
  const add = <T extends number | null | undefined>(v: T, by = 0): T => (typeof v === 'number' ? ((v + by) as T) : v)
  const stats: Partial<Record<string, number>> = { ...w.stats }
  for (const k of ['avo', 'ddg'] as const) {
    const v = (stats[k] ?? 0) + (m[k] ?? 0)
    if (v) stats[k] = v
    else delete stats[k]
  }
  return {
    ...w,
    mt: add(w.mt, m.mt),
    hit: add(w.hit, m.hit),
    crit: add(w.crit, m.crit),
    wt: add(w.wt, m.wt),
    stats: Object.keys(stats).length ? stats : undefined,
  }
}

const TARGET: Record<string, { sprite: Sprite; label: string }> = {
  horseback: { sprite: HORSE_HEAD, label: 'horseback units' },
  flying: { sprite: WING, label: 'fliers' },
  armour: { sprite: ARMOR_HELM, label: 'armoured units' },
  dragon: { sprite: DRAGON_HEAD, label: 'dragons' },
  wyvern: { sprite: DRAGON_HEAD, label: 'dragons and wyverns' },
  monster: { sprite: MONSTER, label: 'monsters' },
  swordfighter: { sprite: SWORD_ICON, label: 'myrmidons and swordmasters' },
  // Mystery of the Emblem's lists name their classes.
  'dragons-all': { sprite: DRAGON_HEAD, label: 'every dragon (a Manakete once changed) and Dragon Knights' },
  'dragons-most': { sprite: DRAGON_HEAD, label: 'dragons (not Earth or Shadow Dragons; a Manakete once changed) and Dragon Knights' },
  cavalier: { sprite: HORSE_HEAD, label: 'Cavaliers and Paladins' },
  icedragon: { sprite: DRAGON_HEAD, label: 'Ice Dragons' },
  firedragon: { sprite: DRAGON_HEAD, label: 'Fire Dragons' },
  brigand: { sprite: AXE_ICON, label: 'thieves, bandits, pirates and barbarians' },
  mercenary: { sprite: SWORD_ICON, label: 'mercenaries, heroes and berserkers' },
  // Awakening's class categories (a class's +90).
  'fe13-beast': { sprite: HORSE_HEAD, label: 'beasts and riders (horses, pegasi, griffons and Taguel)' },
  revenant: { sprite: MONSTER, label: 'Revenants and Entombed' },
  grima: { sprite: GRIMA, label: 'Grima' },
  // Echoes' monsters.
  terror: { sprite: MONSTER, label: 'Terrors' },
  // Engage's Corrupted (its effectiveness skills' bit 64).
  corrupted: { sprite: MONSTER, label: 'Corrupted' },
  // Shadow Dragon's class bits: its dragons, with Medeus (the Earth Dragon) apart, and its Manaketes in or out of dragon form.
  'fe11-dragons': { sprite: DRAGON_HEAD, label: 'dragons (not Medeus, the Earth Dragon)' },
  'fe11-dragons-all': { sprite: DRAGON_HEAD, label: 'every dragon, Medeus included' },
  manakete: { sprite: DRAGON_HEAD, label: 'Manaketes, in or out of dragon form' },
  'fe11-ballistician': { sprite: BALLISTA, label: 'Ballisticians' },
  // New Mystery of the Emblem's: Medeus is the Shadow Dragon there, and its Swordslayer reads a bit of its own.
  'fe12-dragons': { sprite: DRAGON_HEAD, label: 'dragons and wyverns (not Medeus, the Shadow Dragon)' },
  'fe12-dragons-all': { sprite: DRAGON_HEAD, label: 'every dragon and wyvern, Medeus included' },
  'fe12-swordfighter': { sprite: SWORD_ICON, label: 'Mercenaries, Heroes, Myrmidons and Swordmasters' },
  // Shadow Dragon and the Blade of Light's lists name classes too: the Earthstone (Medeus's) makes the one dragon class, the other stones
  // the other, and its Ridersbane leaves Paladins out.
  'fe1-dragons-wyverns': { sprite: DRAGON_HEAD, label: 'dragons (not Medeus, the Earth Dragon) and Wyvern Knights' },
  'fe1-medeus': { sprite: DRAGON_HEAD, label: 'Medeus in dragon form (the Earth Dragon)' },
  'cavaliers-only': { sprite: HORSE_HEAD, label: 'Cavaliers (not Paladins)' },
  // Gaiden's lists (15:$DAE4) name classes, and its monsters share theirs with your units: a foe's Blessed weapon is effective against
  // your Priestesses, Pegasus and Falcon Knights, Saints and Clerics, as yours is against the monsters of those classes.
  'fe2-fliers': { sprite: WING, label: 'Pegasus and Falcon Knights (and the Gargoyles and Necrodragons of their classes)' },
  'fe2-mounted': { sprite: HORSE_HEAD, label: 'Cavaliers, Paladins and Gold Knights' },
  'fe2-monsters': {
    sprite: MONSTER,
    label: "Revenants, Gargoyles, Necrodragons, Bonewalkers and Mogalls (a foe's: your Priestesses, Pegasus and Falcon Knights, Saints and Clerics)",
  },
}
const NUM = 'w-0 py-1 pr-2 sm:pr-3'
const strikesTwice = (w: ChapterWeapon) => !!w.rules?.some((r) => r.startsWith('Strikes twice'))

/** A game's weapons: a filterable list and a detail panel, with each weapon's sources by chapter for the spoiler block. */
export function ChapterWeapons({ config }: { config: ChapterWeaponsConfig }) {
  const { weapons: all, sources: bySource, categories: allCategories } = config
  const reach = useReach()
  const difficulty = useDifficulty()
  // Under the block, the story being walked (a route's, for a game that splits); otherwise the game's whole chapter list.
  const story = reach.story ?? config.story
  /** The story index a source counts from: a unit that arrives mid-chapter ('-later': a foe's drop or weapon, a joiner's gear) counts
   * from the next chapter, once it's been seen. A side map's (a paralogue's) counts from the chapter that opens it. */
  const sourceAt = (s: ItemSource) => turnsUpAt(story, s.mapId, s.kind.endsWith('-later'))
  const optional = config.optional ?? []
  const [shownOptional, setShownOptional] = useState<string[]>([])
  const hidden = (s: ItemSource) => optional.some((o) => o.covers?.(s) && !shownOptional.includes(o.label))
  const hiddenWeapon = (w: ChapterWeapon) => optional.some((o) => o.weapons?.(w) && !shownOptional.includes(o.label))
  // The modifier picked on the datasheet (an engraving), kept while you look from weapon to weapon.
  const [modifierId, setModifierId] = useState('')
  // Only the difficulty picked in the bar: a weapon none of whose sources hold on it isn't listed, like one behind a switch.
  const sourcesOf = (w: ChapterWeapon) => (bySource[w.name] ?? []).filter((s) => !hidden(s) && onDifficulty(difficulty, s.difficulties))
  /** The first chapter a weapon turns up in (its story index), or Infinity if no source has been read for it. */
  const firstAt = (w: ChapterWeapon) => Math.min(Infinity, ...sourcesOf(w).map(sourceAt))
  /** Whether this chapter's shop sells the weapon. */
  /** A shop that stays open once reached (The Sacred Stones' world map towns): kind 'town-shop-later'. */
  const townShop = (s: ItemSource) => s.kind.startsWith('town-shop')
  const soldIn = (w: ChapterWeapon, reach: Reach) =>
    sourcesOf(w).some((s) => (s.kind === 'shop' && reach.here(s.mapId)) || (townShop(s) && sourceAt(s) <= reach.at))
  /** Whether this chapter's shops sell it only in limited stock (every shop line here has a count). */
  const limitedIn = (w: ChapterWeapon, reach: Reach) => {
    const here = sourcesOf(w).filter((s) => s.kind === 'shop' && reach.here(s.mapId))
    return here.length > 0 && here.every((s) => s.limited) && !sourcesOf(w).some((s) => townShop(s) && sourceAt(s) <= reach.at)
  }
  const stockHere = (w: ChapterWeapon, reach: Reach) => (limitedIn(w, reach) ? 'limited' : soldIn(w, reach) ? 'sale' : 'no')

  // With the spoiler block on, a weapon is listed from the first chapter it turns up in (a shop, a village, a chest, a talk, a drop,
  // what a unit carries when it joins) and stays listed; the ones new this chapter get a mark. Weapons with no source read stay hidden.
  const { weapons, fresh } = useMemo(() => {
    // A weapon whose only sources are behind a switch that's off, or on other difficulties, isn't listed; nor is one a switch that's
    // off hides outright.
    const listed = all.filter((w) => !hiddenWeapon(w) && (!(bySource[w.name] ?? []).length || sourcesOf(w).length))
    if (!reach.on) return { weapons: listed, fresh: new Set<string>() }
    const shown = listed.filter((w) => firstAt(w) <= reach.at)
    return { weapons: shown, fresh: new Set(shown.filter((w) => reach.at > 0 && firstAt(w) === reach.at).map((w) => w.id)) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [all, reach, shownOptional, difficulty])
  const hasFoeOnly = weapons.some((w) => w.foeOnly)
  const hasCrit = all.some((w) => w.crit !== undefined)
  const hasWt = all.some((w) => w.wt !== undefined)
  const hasRank = all.some((w) => w.rank)
  // A game whose shops sell nothing (Echoes: no gold) has no stock to filter by.
  const hasShops = Object.values(bySource).some((l) => l.some((s) => s.kind === 'shop' || townShop(s)))
  const hasLimited = Object.values(bySource).some((l) => l.some((s) => s.limited))
  const categories = allCategories.filter((c) => !reach.on || weapons.some((w) => w.category === c))
  const [pickedCategory, setCategory] = useState('all')
  const category = categories.includes(pickedCategory) ? pickedCategory : 'all'
  const [search, setSearch] = useState('')
  const [stock, setStock] = useState<'all' | 'sale' | 'limited' | 'no'>('all')
  const [hideFoeOnly, setHideFoeOnly] = useState(false)
  const [selectedId, setSelectedId] = useState(all[0].id)
  const detailRef = useRef<HTMLDivElement>(null)
  const filtered = weapons.filter(
    (w) =>
      (category === 'all' || w.category === category) &&
      (stock === 'all' || stockHere(w, reach) === stock) &&
      !(hideFoeOnly && w.foeOnly) &&
      (!search || w.name.toLowerCase().includes(search.toLowerCase())),
  )
  const selected = weapons.find((w) => w.id === selectedId) ?? weapons[0] ?? null

  function select(id: string) {
    setSelectedId(id)
    const panel = detailRef.current
    if (!panel) return
    const top = panel.getBoundingClientRect().top
    if (top < 0 || top > window.innerHeight * 0.5) panel.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const markers = (w: ChapterWeapon) => {
    const icon = (sprite: Sprite, title: string, key: string) => (
      <span key={key} className="ml-1 inline-flex" title={title}>
        <PixelIcon sprite={sprite} size={14} title={title} />
      </span>
    )
    const by = w.effectiveMultiplier ?? config.effectiveMultiplier
    const times = by ? ` (Mt ×${by})` : ''
    return (
      <>
        {w.foeOnly && icon(NOT_FOR_PLAYER, 'Foe only: carried by enemy units, not available to the player', 'foe')}
        {(config.magic.has(w.category) || w.magic) && icon(MAGIC, 'Deals magic damage', 'magic')}
        {w.effective?.map((t) => icon(TARGET[t].sprite, `Effective against ${TARGET[t].label}${times}`, t))}
        {strikesTwice(w) && icon(BRAVE, 'Strikes twice in a row', 'brave')}
      </>
    )
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
        {reach.on && hasShops && (
          <select
            value={stock}
            onChange={(e) => setStock(e.target.value as typeof stock)}
            aria-label={`Stock at this chapter's ${config.shopName}`}
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
          >
            <option value="all">Any stock</option>
            <option value="sale">Shop here</option>
            {hasLimited && <option value="limited">Limited stock here</option>}
            <option value="no">Not in the shop here</option>
          </select>
        )}
        {hasFoeOnly && (
          <label className="flex items-center gap-1 text-sm text-neutral-300">
            <input type="checkbox" checked={hideFoeOnly} onChange={(e) => setHideFoeOnly(e.target.checked)} />
            Hide foe-only
          </label>
        )}
        {optional.map((o) => (
          <label key={o.label} className="flex items-center gap-1 text-sm text-neutral-300">
            <input
              type="checkbox"
              checked={shownOptional.includes(o.label)}
              onChange={(e) => setShownOptional(e.target.checked ? [...shownOptional, o.label] : shownOptional.filter((x) => x !== o.label))}
            />
            {o.label}
          </label>
        ))}
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search weapon name..."
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        />
      </div>
      {hasFoeOnly && !hideFoeOnly && (
        <p className="text-xs text-neutral-500">
          <PixelIcon sprite={NOT_FOR_PLAYER} size={12} /> marks weapons only foes carry; nothing gives them to you.
        </p>
      )}
      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded border border-neutral-800">
          <table className="w-full border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-neutral-700 text-left text-neutral-400">
                <th className="py-1 pl-2 pr-1 sm:pr-3">Name</th>
                {hasRank && <th className={NUM}>Rank</th>}
                <th className={NUM}>Mt</th>
                <th className={NUM}>Hit</th>
                {hasCrit && <th className={NUM}>Crit</th>}
                {hasWt && <th className={NUM}>Wt</th>}
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
                    {markers(w)}
                    {fresh.has(w.id) && <span className="ml-1 rounded bg-emerald-900 px-1 text-[10px] text-emerald-200">new</span>}
                    {reach.on && stockHere(w, reach) === 'sale' && <span className="ml-1 text-[10px] text-sky-300">shop</span>}
                    {reach.on && stockHere(w, reach) === 'limited' && (
                      <span className="ml-1 rounded bg-amber-900 px-1 text-[10px] uppercase text-amber-200">limited</span>
                    )}
                  </td>
                  {hasRank && <td className={`${NUM} text-neutral-400`}>{w.rank}</td>}
                  <td className={NUM}>{w.mt ?? '—'}</td>
                  <td className={NUM}>{w.hit ?? '—'}</td>
                  {hasCrit && <td className={NUM}>{w.crit ?? '—'}</td>}
                  {hasWt && <td className={NUM}>{w.wt ?? '—'}</td>}
                  <td className={`${NUM} whitespace-nowrap`}>{w.range}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-neutral-500">
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
          {selected ? (
            <Detail
              key={selected.id}
              weapon={selected}
              config={config}
              sources={sourcesOf(selected)
                .filter((s) => !reach.on || (s.kind === 'shop' ? reach.here(s.mapId) : sourceAt(s) <= reach.at))
                .sort((a, b) => sourceAt(a) - sourceAt(b))}
              modifierId={modifierId}
              onModifier={setModifierId}
            />
          ) : (
            <p className="p-4 text-neutral-500">Nothing to show yet.</p>
          )}
        </div>
      </div>
    </>
  )
}

function Detail({
  weapon: base,
  config,
  sources,
  modifierId,
  onModifier,
}: {
  weapon: ChapterWeapon
  config: ChapterWeaponsConfig
  sources: ItemSource[]
  modifierId: string
  onModifier: (id: string) => void
}) {
  const reach = useReach()
  // A modifier this weapon can take (an engraving), as picked; one it can't take shows the weapon as it is.
  const options = config.modifiers?.options(base, reach) ?? []
  const modifier = options.find((m) => m.id === modifierId)
  const w = withModifier(base, modifier)
  const delta = (k: 'mt' | 'hit' | 'crit' | 'wt') => (modifier?.[k] ? modifier[k]! : 0)
  // Under the spoiler block a buying price is only said while this chapter's shop stocks it.
  const soldNow = !reach.on || sources.some((s) => s.kind === 'shop' || s.kind.startsWith('town-shop'))
  const rows = sourceRows(sources, (id) => config.story.maps.find((x) => x.id === id), config.story.short, config.routeName)
  // A modifier's change beside the number: green where it helps, red where it hurts (more Wt hurts).
  const stat = (label: string, value: string | number, by = 0, lowerIsBetter = false) => (
    <div className="rounded bg-neutral-900 px-2 py-1 text-center">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className={!by ? 'text-neutral-100' : by > 0 !== lowerIsBetter ? 'text-emerald-300' : 'text-rose-300'}>
        {value}
        {by !== 0 && <span className="ml-1 text-[10px]">({by > 0 ? `+${by}` : by})</span>}
      </p>
    </div>
  )
  const bonuses = Object.entries(w.stats ?? {})
  const staff = w.category === 'Staff'
  const sells = w.sell ?? Math.floor((w.worth ?? 0) / 2)
  const price = w.worth ? (soldNow ? stat('Price', w.worth.toLocaleString()) : stat('Sells for', sells.toLocaleString())) : stat('Price', '—')
  const hasWt = config.weapons.some((x) => x.wt !== undefined)
  const hasUses = config.weapons.some((x) => x.uses !== undefined)
  const hasPrices = config.weapons.some((x) => x.worth !== undefined)
  const rankText = config.rankLabel(w)
  const signed = (v: number) => (v < 0 ? `${v}` : `+${v}`)
  return (
    <div className="flex flex-col gap-3 p-4 text-sm">
      <div>
        <h2 className="text-xl font-semibold text-neutral-100">{w.name}</h2>
        <p className="text-neutral-500">
          {w.category}
          {rankText ? ` · ${rankText}` : ''}
          {config.magic.has(w.category) || w.magic ? ' · magic damage' : ''}
        </p>
      </div>
      {w.foeOnly && (
        <p className="flex items-center gap-1 text-red-300">
          <PixelIcon sprite={NOT_FOR_PLAYER} size={14} /> Carried only by foes; you can't get it.
        </p>
      )}
      {config.modifiers && options.length > 0 && (
        <div className="flex flex-col gap-1">
          <label className="flex flex-wrap items-center gap-2 text-neutral-300">
            {config.modifiers.label}
            <select
              value={modifier?.id ?? ''}
              onChange={(e) => onModifier(e.target.value)}
              className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-100"
            >
              <option value="">None</option>
              {options.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.label}
                </option>
              ))}
            </select>
          </label>
          {modifier && config.modifiers.note && <p className="text-xs text-neutral-500">{config.modifiers.note(base, modifier)}</p>}
        </div>
      )}
      <div className="grid grid-cols-4 gap-2">
        {!staff && stat('Mt', w.mt ?? '—', delta('mt'))}
        {!staff && stat('Hit', w.hit ?? '—', delta('hit'))}
        {!staff && w.crit !== undefined && stat('Crit', w.crit, delta('crit'))}
        {!staff && hasWt && stat('Wt', w.wt ?? '—', delta('wt'), true)}
        {w.range && stat('Rng', w.range)}
        {hasUses && stat('Uses', w.uses ?? '∞')}
        {hasPrices && price}
        {w.exp !== undefined && stat('EXP', w.exp)}
      </div>
      {w.effective && w.effective.length > 0 && (
        <p className="text-amber-200">
          {w.effective.map((t) => (
            <PixelIcon key={t} sprite={TARGET[t].sprite} size={14} />
          ))}{' '}
          Effective against {w.effective.map((t) => TARGET[t].label).join(' and ')}
          {(w.effectiveMultiplier ?? config.effectiveMultiplier) && typeof w.mt === 'number' && ` (Mt ${w.mt * (w.effectiveMultiplier ?? config.effectiveMultiplier)!})`}
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
          {bonuses.map(([k, v]) => `${config.statNames[k] ?? k} ${signed(v ?? 0)}`).join(', ')}
        </p>
      )}
      {rows.length > 0 && (
        <div>
          <p className="text-neutral-500">Where it turns up</p>
          <ul className="list-disc space-y-0.5 pl-5 text-neutral-300">
            {rows.map((r, i) => (
              <li key={i}>
                {r.text}
                {r.route && ` (${r.route})`}
                {r.later && ', counted from the next chapter'}: <span className="text-neutral-400">{r.chapters.join(', ')}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {config.extra?.(base, modifier)}
    </div>
  )
}
