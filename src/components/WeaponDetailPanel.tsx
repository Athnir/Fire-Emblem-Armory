import type { Weapon } from '../data/types'
import { ForgeTable } from './ForgeTable'

const ROUTE_COLORS: Record<string, string> = {
  Birthright: 'bg-sky-900 text-sky-200',
  Conquest: 'bg-rose-900 text-rose-200',
  Revelation: 'bg-violet-900 text-violet-200',
  all: 'bg-neutral-700 text-neutral-200',
}

export function WeaponDetailPanel({ weapon }: { weapon: Weapon }) {
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div>
        <h2 className="text-xl font-semibold text-neutral-100">{weapon.name}</h2>
        <p className="text-sm text-neutral-500">
          {weapon.category} · Rank {weapon.rank} · {weapon.faction}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm sm:grid-cols-6">
        {(
          [
            ['Mt', weapon.stats.mt],
            ['Hit', weapon.stats.hit],
            ['Crit', weapon.stats.crit],
            ['Avoid', weapon.stats.avoid],
            ['Rng', weapon.stats.range],
            ['Worth', weapon.stats.worth],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded bg-neutral-800 px-2 py-1 text-center">
            <div className="text-neutral-500">{label}</div>
            <div className="text-neutral-100">{value}</div>
          </div>
        ))}
      </div>

      <p className="text-sm text-neutral-300">{weapon.effects}</p>

      <div className="flex flex-wrap gap-1">
        {weapon.availability.routes.length === 0 && (
          <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-500">Not player-obtainable</span>
        )}
        {weapon.availability.routes.map((route) => (
          <span key={route} className={`rounded px-2 py-0.5 text-xs ${ROUTE_COLORS[route]}`}>
            {route === 'all' ? 'All routes' : route}
          </span>
        ))}
        {weapon.isDlc && <span className="rounded bg-amber-900 px-2 py-0.5 text-xs text-amber-200">DLC</span>}
        {weapon.isAmiibo && <span className="rounded bg-amber-900 px-2 py-0.5 text-xs text-amber-200">Amiibo</span>}
        {weapon.isPersonal && (
          <span className="rounded bg-emerald-900 px-2 py-0.5 text-xs text-emerald-200">
            Personal{weapon.personalTo ? ` · ${weapon.personalTo}` : ''}
          </span>
        )}
      </div>
      <p className="text-sm text-neutral-500">{weapon.availability.source}</p>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-neutral-300">Smithy forging</h3>
        <ForgeTable weapon={weapon} />
      </div>
    </div>
  )
}
