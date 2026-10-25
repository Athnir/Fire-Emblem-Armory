import { useMemo, useRef, useState } from 'react'
import { useReach } from './Reach'
import { turnsUpAt } from '../logic/spoiler'
import { firstChapter, isVisitItem, maxForge, smithyLevel, stockedNow, whereLines } from '../logic/fatesWeapons'
import type { FatesChapter } from '../logic/fatesWeapons'
import type { BlockView } from './WeaponDetailPanel'
import { ALL_WEAPONS } from '../data/weapons'
import type { Route, WeaponCategory, Weapon } from '../data/types'
import { HOSHIDO_CATEGORIES, NOHR_CATEGORIES } from '../data/types'
import { WeaponList } from './WeaponList'
import { WeaponDetailPanel } from './WeaponDetailPanel'

const CATEGORIES: (WeaponCategory | 'all')[] = [
  'all',
  'Sword', 'Katana',
  'Lance', 'Naginata',
  'Axe', 'Club',
  'Bow', 'Yumi',
  'Tome', 'Scroll',
  'Dagger', 'Shuriken',
  'Staff', 'Rod',
  'Other',
]

const ROUTES: (Route | 'any')[] = ['any', 'Birthright', 'Conquest', 'Revelation']

type CategoryFilter = WeaponCategory | 'all' | 'Cross'

/** True if this weapon reached `route` only through a one-off cross-faction exception rather than
 * its category's own default — these get pulled out of their native category tab into "Cross". */
function isCrossException(weapon: Weapon, route: Route): boolean {
  return weapon.availability.crossRoutes?.includes(route) ?? false
}

/** Which category tabs make sense for a given route: a single-side route (Birthright/Conquest)
 * drops the opposite faction's categories (their normal stock never appears there) and gains a
 * "Cross" tab that gathers the opposite-faction items obtainable there via a one-off exception. */
function categoryOptionsForRoute(route: Route | 'any'): CategoryFilter[] {
  if (route === 'Conquest') {
    return ['all', 'Cross', ...CATEGORIES.filter((c) => c !== 'all' && !HOSHIDO_CATEGORIES.includes(c as WeaponCategory))]
  }
  if (route === 'Birthright') {
    return ['all', 'Cross', ...CATEGORIES.filter((c) => c !== 'all' && !NOHR_CATEGORIES.includes(c as WeaponCategory))]
  }
  return CATEGORIES
}

/** The marks next to a weapon's name under the block: new this chapter, in the shop now, or limited stock. */
function badgesFor(row: { sold?: { stock: number | null }; fresh: boolean } | undefined) {
  if (!row) return null
  return (
    <>
      {row.fresh && <span className="ml-2 rounded bg-emerald-900 px-1 text-[10px] uppercase text-emerald-200">new</span>}
      {row.sold && row.sold.stock === null && <span className="ml-2 rounded bg-sky-900 px-1 text-[10px] uppercase text-sky-200">shop</span>}
      {row.sold && row.sold.stock !== null && <span className="ml-2 rounded bg-amber-900 px-1 text-[10px] uppercase text-amber-200">limited</span>}
    </>
  )
}

/** Fates' weapon list: filter by category, route and name, with each weapon's details and forge table. */
export function FatesWeapons() {
  const reach = useReach()
  const [category, setCategory] = useState<CategoryFilter>('all')
  const [pickedRoute, setRoute] = useState<Route | 'any'>('any')
  const [search, setSearch] = useState('')
  const [stock, setStock] = useState<'all' | 'shop' | 'limited' | 'no'>('all')
  const [hideFoeOnly, setHideFoeOnly] = useState(false)
  const [hideVisit, setHideVisit] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(ALL_WEAPONS[0]?.id ?? null)

  // The spoiler block: the route you chose is the route, and only what the chapter you're on has opened.
  const chapter = useMemo<FatesChapter | null>(
    () => (reach.on && reach.story ? { story: reach.story, at: reach.at, route: reach.route as FatesChapter['route'] } : null),
    [reach],
  )
  const route: Route | 'any' = chapter ? (chapter.route ?? 'any') : pickedRoute

  const categoryOptions = useMemo(() => categoryOptionsForRoute(route), [route])

  function handleRouteChange(newRoute: Route | 'any') {
    setRoute(newRoute)
    if (!categoryOptionsForRoute(newRoute).includes(category)) setCategory('all')
  }

  // Under the block: each weapon from the first chapter it turns up in, with what this chapter's shops do with it.
  const open = useMemo(() => {
    if (!chapter) return null
    const rows = new Map<string, { sold?: ReturnType<typeof stockedNow>; fresh: boolean }>()
    for (const w of ALL_WEAPONS) {
      const first = firstChapter(w, chapter)
      if (first > chapter.at) continue
      rows.set(w.id, { sold: stockedNow(w, chapter), fresh: chapter.at > 0 && first === chapter.at })
    }
    return rows
  }, [chapter])

  const filtered = useMemo(() => {
    return ALL_WEAPONS.filter((w) => {
      if (open && !open.has(w.id)) return false
      if (hideFoeOnly && w.foeOnly) return false
      if (hideVisit && isVisitItem(w)) return false
      if (open) {
        const sold = open.get(w.id)!.sold
        if (stock === 'shop' && !sold) return false
        if (stock === 'limited' && (!sold || sold.stock === null)) return false
        if (stock === 'no' && sold) return false
      }
      if (category === 'Cross') {
        if (route !== 'Birthright' && route !== 'Conquest') return false
        if (!isCrossException(w, route)) return false
      } else {
        if (category !== 'all' && w.category !== category) return false
        if (route !== 'any') {
          const matchesRoute = w.availability.routes.includes(route) || w.availability.routes.includes('all')
          if (!matchesRoute && !open) return false
          // Cross-exception weapons live in the "Cross" tab instead of cluttering their native
          // category with a single oddball entry when a specific side is selected.
          if (isCrossException(w, route)) return false
        }
      }
      if (search && !w.name.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [category, route, search, open, stock, hideFoeOnly, hideVisit])

  const selected = (open ? ALL_WEAPONS.find((w) => w.id === selectedId && open.has(w.id)) ?? ALL_WEAPONS.find((w) => open.has(w.id)) : ALL_WEAPONS.find((w) => w.id === selectedId)) ?? null
  const detailRef = useRef<HTMLDivElement>(null)
  const block: BlockView | undefined =
    chapter && selected
      ? {
          lines: whereLines(selected, chapter),
          mapSources: (selected.mapSources ?? []).filter((s) => reach.has(s.mapId) && turnsUpAt(chapter.story, s.mapId, s.arrives) <= chapter.at),
          smithy: { level: smithyLevel(chapter), maxRank: maxForge(chapter) },
        }
      : undefined

  // Picking a weapon brings its details into view: below the list on a phone, and on a wide screen the
  // panel stays pinned beside the list, so it only scrolls if the panel's top is off-screen.
  function selectWeapon(id: string) {
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
          onChange={(e) => setCategory(e.target.value as CategoryFilter)}
          className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        >
          {categoryOptions.map((c) => (
            <option key={c} value={c}>
              {c === 'all' ? 'All categories' : c === 'Cross' ? 'Cross-route exceptions' : c}
            </option>
          ))}
        </select>
        {!chapter && (
          <select
            value={route}
            onChange={(e) => handleRouteChange(e.target.value as Route | 'any')}
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
          >
            {ROUTES.map((r) => (
              <option key={r} value={r}>
                {r === 'any' ? 'Any route' : r}
              </option>
            ))}
          </select>
        )}
        {chapter && (
          <select
            value={stock}
            onChange={(e) => setStock(e.target.value as typeof stock)}
            aria-label="Stock in your shops"
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
          >
            <option value="all">Any stock</option>
            <option value="shop">In the shop now</option>
            <option value="limited">Limited stock now</option>
            <option value="no">Not in the shop now</option>
          </select>
        )}
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input type="checkbox" checked={hideFoeOnly} onChange={(e) => setHideFoeOnly(e.target.checked)} /> Hide foe-only
        </label>
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input type="checkbox" checked={hideVisit} onChange={(e) => setHideVisit(e.target.checked)} /> Hide visit items
        </label>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search weapon name..."
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        />
      </div>

      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded border border-neutral-800">
          <WeaponList weapons={filtered} selectedId={selectedId} onSelect={selectWeapon} badges={open ? (w) => badgesFor(open.get(w.id)) : undefined} />
        </div>
        <div
          ref={detailRef}
          className="scroll-mt-4 rounded border border-neutral-800 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto"
        >
          {selected ? (
            <WeaponDetailPanel key={selected.id} weapon={selected} block={block} />
          ) : (
            <p className="p-4 text-neutral-500">Select a weapon to see its details.</p>
          )}
        </div>
      </div>
    </>
  )
}
