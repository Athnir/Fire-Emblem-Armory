import { useMemo, useState } from 'react'
import { ALL_WEAPONS } from './data/weapons'
import type { Route, WeaponCategory } from './data/types'
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

function App() {
  const [category, setCategory] = useState<WeaponCategory | 'all'>('all')
  const [route, setRoute] = useState<Route | 'any'>('any')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(ALL_WEAPONS[0]?.id ?? null)

  const filtered = useMemo(() => {
    return ALL_WEAPONS.filter((w) => {
      if (category !== 'all' && w.category !== category) return false
      if (route !== 'any' && !w.availability.routes.includes(route) && !w.availability.routes.includes('all')) return false
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
          onChange={(e) => setCategory(e.target.value as WeaponCategory | 'all')}
          className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c === 'all' ? 'All categories' : c}
            </option>
          ))}
        </select>
        <select
          value={route}
          onChange={(e) => setRoute(e.target.value as Route | 'any')}
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
            <WeaponDetailPanel weapon={selected} />
          ) : (
            <p className="p-4 text-neutral-500">Select a weapon to see its details.</p>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
