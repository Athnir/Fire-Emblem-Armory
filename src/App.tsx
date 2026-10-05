import { useMemo, useState } from 'react'
import { ALL_WEAPONS } from './data/weapons'
import type { Route, WeaponCategory, Weapon } from './data/types'
import { HOSHIDO_CATEGORIES, NOHR_CATEGORIES } from './data/types'
import { WeaponList } from './components/WeaponList'
import { WeaponDetailPanel } from './components/WeaponDetailPanel'

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

function App() {
  const [category, setCategory] = useState<CategoryFilter>('all')
  const [route, setRoute] = useState<Route | 'any'>('any')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(ALL_WEAPONS[0]?.id ?? null)

  const categoryOptions = useMemo(() => categoryOptionsForRoute(route), [route])

  function handleRouteChange(newRoute: Route | 'any') {
    setRoute(newRoute)
    if (!categoryOptionsForRoute(newRoute).includes(category)) setCategory('all')
  }

  const filtered = useMemo(() => {
    return ALL_WEAPONS.filter((w) => {
      if (category === 'Cross') {
        if (route !== 'Birthright' && route !== 'Conquest') return false
        if (!isCrossException(w, route)) return false
      } else {
        if (category !== 'all' && w.category !== category) return false
        if (route !== 'any') {
          const matchesRoute = w.availability.routes.includes(route) || w.availability.routes.includes('all')
          if (!matchesRoute) return false
          // Cross-exception weapons live in the "Cross" tab instead of cluttering their native
          // category with a single oddball entry when a specific side is selected.
          if (isCrossException(w, route)) return false
        }
      }
      if (search && !w.name.toLowerCase().includes(search.toLowerCase())) return false
      return true
    })
  }, [category, route, search])

  const selected = ALL_WEAPONS.find((w) => w.id === selectedId) ?? null

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 p-4 text-neutral-200">
      <header>
        <h1 className="text-2xl font-bold text-neutral-100">Fates Armory</h1>
        <p className="text-sm text-neutral-500">
          Weapon stats, Smithy forge planning, and route availability for Fire Emblem Fates.
        </p>
      </header>

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
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search weapon name..."
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        />
      </div>

      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded border border-neutral-800">
          <WeaponList weapons={filtered} selectedId={selectedId} onSelect={setSelectedId} />
        </div>
        <div className="rounded border border-neutral-800">
          {selected ? (
            <WeaponDetailPanel key={selected.id} weapon={selected} />
          ) : (
            <p className="p-4 text-neutral-500">Select a weapon to see its details.</p>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
