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
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-semibold text-neutral-100">{weapon.name}</h2>
          {weapon.isMagic && (
            <span className="rounded bg-indigo-900 px-2 py-0.5 text-xs text-indigo-200">
              Magic — hits Resistance, not Defence
            </span>
          )}
        </div>
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
            ['Dodge', weapon.stats.dodge],
            ['Rng', weapon.stats.range],
            ...(weapon.stats.uses !== undefined ? ([['Uses', weapon.stats.uses]] as const) : []),
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded bg-neutral-800 px-2 py-1 text-center">
            <div className="text-neutral-500">{label}</div>
            <div className="text-neutral-100">{value}</div>
          </div>
        ))}
      </div>
      <p className="-mt-2 text-xs text-neutral-600">Avoid: chance to be missed entirely · Dodge: chance to avoid being critically hit</p>

      {weapon.effects && <p className="text-sm text-neutral-300">{weapon.effects}</p>}

      {weapon.effectiveness && (
        <div className="rounded bg-neutral-800 px-3 py-2 text-sm">
          <div className="text-neutral-200">
            Effective vs. {weapon.effectiveness.vs}: Might ×{weapon.effectiveness.multiplier} (
            {weapon.stats.mt} → {weapon.stats.mt * weapon.effectiveness.multiplier})
          </div>
          <div className="text-neutral-500">
            {weapon.effectiveness.nonEffectivePenalty ? (
              <>
                Otherwise: Might {weapon.effectiveness.nonEffectivePenalty.mt}, Hit{' '}
                {weapon.effectiveness.nonEffectivePenalty.hit} ({weapon.stats.mt} →{' '}
                {weapon.stats.mt + weapon.effectiveness.nonEffectivePenalty.mt}, {weapon.stats.hit} →{' '}
                {weapon.stats.hit + weapon.effectiveness.nonEffectivePenalty.hit})
              </>
            ) : (
              'Otherwise: no penalty — keeps its listed stats, just without the bonus'
            )}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-1">
        {weapon.availability.routes.length === 0 && !weapon.isAmiibo && !weapon.isDlc && (
          <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-500">Not player-obtainable</span>
        )}
        {/* Amiibo-scan/DLC items with no routes aren't unobtainable — they're just not gated by story
            route at all (any save works), which is a different thing from the route-tally feature
            this badge set otherwise reports on. */}
        {weapon.availability.routes.length === 0 && (weapon.isAmiibo || weapon.isDlc) && (
          <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-500">Not route-gated</span>
        )}
        {weapon.availability.routes.map((route) => (
          <span key={route} className={`rounded px-2 py-0.5 text-xs ${ROUTE_COLORS[route]}`}>
            {route === 'all' ? 'All routes' : route}
          </span>
        ))}
        {weapon.isDlc && <span className="rounded bg-amber-900 px-2 py-0.5 text-xs text-amber-200">DLC</span>}
        {weapon.isAmiibo && <span className="rounded bg-amber-900 px-2 py-0.5 text-xs text-amber-200">Amiibo</span>}
        {weapon.isMyCastle && (
          <span className="rounded bg-cyan-900 px-2 py-0.5 text-xs text-cyan-200">My Castle</span>
        )}
        {weapon.isPersonal && (
          <span className="rounded bg-emerald-900 px-2 py-0.5 text-xs text-emerald-200">
            Personal{weapon.personalTo ? ` · ${weapon.personalTo}` : ''}
          </span>
        )}
      </div>
      <p className="text-sm text-neutral-500">{weapon.availability.source}</p>

      <div className="text-sm">
        <span className="text-neutral-500">Shop price: </span>
        {weapon.purchase ? (
          <span className="text-neutral-200">
            Buy {weapon.purchase.buy}
            {weapon.purchase.sell !== undefined ? ` · Sell ${weapon.purchase.sell}` : ' · sell price not verified'}
          </span>
        ) : (
          <span className="text-neutral-500">Not sold in any shop</span>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold text-neutral-300">Smithy forging</h3>
        <ForgeTable weapon={weapon} />
      </div>
    </div>
  )
}
